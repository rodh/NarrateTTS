import plistlib

from app.shortcuts import build_shortcut_plist, serialize_plist, sign_shortcut


def test_plist_embeds_url_and_token():
    plist = build_shortcut_plist("https://narrate.example/api/shortcut", "abc123")
    assert plist["WFWorkflowTypes"] == ["ActionExtension"]
    # Text-only input (no URL content item) to avoid the per-site permission prompt.
    assert plist["WFWorkflowInputContentItemClasses"] == ["WFStringContentItem"]

    actions = plist["WFWorkflowActions"]
    url_action = actions[0]["WFWorkflowActionParameters"]["WFURLActionURL"]
    assert url_action == "https://narrate.example/api/shortcut"

    headers = actions[1]["WFWorkflowActionParameters"]["WFHTTPHeaders"]["Value"][
        "WFDictionaryFieldValueItems"
    ]
    auth_value = headers[0]["WFValue"]["Value"]["string"]
    assert auth_value == "Bearer abc123"


def test_serialize_roundtrips_to_binary_plist():
    plist = build_shortcut_plist("https://x/api/shortcut", "tok")
    data = serialize_plist(plist)
    assert isinstance(data, (bytes, bytearray))
    parsed = plistlib.loads(bytes(data))
    assert parsed["WFWorkflowActions"][0]["WFWorkflowActionParameters"]["WFURLActionURL"] == "https://x/api/shortcut"


def test_sign_falls_back_when_cli_unavailable(monkeypatch):
    import app.shortcuts as shortcuts

    def _boom(*args, **kwargs):
        raise FileNotFoundError("no shortcuts binary")

    monkeypatch.setattr(shortcuts.subprocess, "run", _boom)
    payload = b"unsigned-bytes"
    signed, did_sign = sign_shortcut(payload)
    assert signed == payload
    assert did_sign is False


def test_request_action_sets_url_explicitly():
    """The request action must name our endpoint explicitly (WFURL). Implicit
    action-output chaining does not work on-device, so without WFURL the request
    POSTs the shared URL instead and nothing saves."""
    plist = build_shortcut_plist("https://narrate.example/api/shortcut", "abc123")
    download = next(
        a for a in plist["WFWorkflowActions"]
        if a["WFWorkflowActionIdentifier"] == "is.workflow.actions.downloadurl"
    )
    assert download["WFWorkflowActionParameters"]["WFURL"] == "https://narrate.example/api/shortcut"
    assert download["WFWorkflowActionParameters"]["WFHTTPMethod"] == "POST"

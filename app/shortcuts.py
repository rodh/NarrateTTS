"""Build and sign a 'Send to NarrateTTS' iOS Shortcut.

Ports the buildShortcutPlist/sign logic from howlab-tools to Python: the workflow
is an ActionExtension (appears in the Share Sheet) that POSTs the shared input to
/api/shortcut with the API token baked in as a Bearer header. The request action
names the endpoint explicitly (WFURL) because implicit action-output chaining does
not work on-device here. The binary plist is produced with stdlib plistlib; signing
shells out to the macOS `shortcuts` CLI so the file installs without "Allow
Untrusted Shortcuts".
"""

import plistlib
import subprocess
import tempfile
from pathlib import Path


def build_shortcut_plist(api_url: str, token: str) -> dict:
    """Return the Shortcut workflow dict with the endpoint and token embedded."""
    extension_input = {
        "Value": {
            "string": "￼",  # Object Replacement Character = the shared input
            "attachmentsByRange": {"{0, 1}": {"Type": "ExtensionInput"}},
        },
        "WFSerializationType": "WFTextTokenString",
    }

    return {
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowIcon": {
            "WFWorkflowIconStartColor": 4282601983,
            "WFWorkflowIconGlyphNumber": 59765,
        },
        "WFWorkflowTypes": ["ActionExtension"],
        # Text only (no WFURLContentItem): if the shortcut accepts the shared item
        # as a URL, iOS prompts for that site's domain on every new site shared.
        # Receiving it as text avoids the per-site prompt; the URL still rides along
        # in the request body as a string.
        "WFWorkflowInputContentItemClasses": [
            "WFStringContentItem",
        ],
        "WFWorkflowActions": [
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.url",
                "WFWorkflowActionParameters": {"WFURLActionURL": api_url},
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
                "WFWorkflowActionParameters": {
                    # Explicit URL: implicit chaining from the url action does not
                    # work on-device here, so the request must name our endpoint
                    # directly or it POSTs the shared URL instead and nothing saves.
                    "WFURL": api_url,
                    "WFHTTPMethod": "POST",
                    "WFHTTPBodyType": "JSON",
                    "WFHTTPHeaders": {
                        "Value": {
                            "WFDictionaryFieldValueItems": [
                                {
                                    "WFItemType": 0,
                                    "WFKey": {
                                        "Value": {"string": "Authorization"},
                                        "WFSerializationType": "WFTextTokenString",
                                    },
                                    "WFValue": {
                                        "Value": {"string": f"Bearer {token}"},
                                        "WFSerializationType": "WFTextTokenString",
                                    },
                                }
                            ]
                        },
                        "WFSerializationType": "WFDictionaryFieldValue",
                    },
                    "WFJSONValues": {
                        "Value": {
                            "WFDictionaryFieldValueItems": [
                                {
                                    "WFItemType": 0,
                                    "WFKey": {
                                        "Value": {"string": "input"},
                                        "WFSerializationType": "WFTextTokenString",
                                    },
                                    "WFValue": extension_input,
                                }
                            ]
                        },
                        "WFSerializationType": "WFDictionaryFieldValue",
                    },
                },
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.notification",
                "WFWorkflowActionParameters": {
                    "WFNotificationActionBody": "Saved to NarrateTTS",
                    "WFNotificationActionTitle": "NarrateTTS",
                },
            },
        ],
    }


def serialize_plist(plist: dict) -> bytes:
    """Serialize the workflow dict to a binary plist (.shortcut payload)."""
    return plistlib.dumps(plist, fmt=plistlib.FMT_BINARY)


def sign_shortcut(unsigned: bytes) -> tuple[bytes, bool]:
    """Sign the shortcut via the macOS CLI. Returns (bytes, did_sign).

    Falls back to the unsigned bytes (did_sign=False) on any failure, e.g. when the
    server is not macOS or the CLI is unavailable.
    """
    tmp = Path(tempfile.mkdtemp(prefix="narrate-shortcut-"))
    unsigned_path = tmp / "unsigned.shortcut"
    signed_path = tmp / "signed.shortcut"
    try:
        unsigned_path.write_bytes(unsigned)
        subprocess.run(
            [
                "/usr/bin/shortcuts",
                "sign",
                "--mode",
                "anyone",
                "--input",
                str(unsigned_path),
                "--output",
                str(signed_path),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        return signed_path.read_bytes(), True
    except Exception:
        return unsigned, False
    finally:
        unsigned_path.unlink(missing_ok=True)
        signed_path.unlink(missing_ok=True)
        try:
            tmp.rmdir()
        except OSError:
            pass

def test_ensure_token_mints_and_is_stable(temp_db):
    from app.db import init_db, ensure_token
    init_db()
    t1 = ensure_token()
    t2 = ensure_token()
    assert t1 == t2
    assert len(t1) == 64  # secrets.token_hex(32)


def test_regenerate_changes_token_and_invalidates_old(temp_db):
    from app.db import init_db, ensure_token, regenerate_token, verify_token
    init_db()
    old = ensure_token()
    new = regenerate_token()
    assert new != old
    assert verify_token(new) is True
    assert verify_token(old) is False


def test_verify_token_rejects_empty_and_wrong(temp_db):
    from app.db import init_db, ensure_token, verify_token
    init_db()
    ensure_token()
    assert verify_token("") is False
    assert verify_token("not-the-token") is False

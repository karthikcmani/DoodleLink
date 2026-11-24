"""Unit tests for PairingManager."""

import time

from doodlelink.network.pairing import PairingManager


def test_pairing_code_generation():
    manager = PairingManager()
    code = manager.current_code
    assert len(code) == 6
    assert code.isdigit()
    assert manager.verify_code(code)


def test_pairing_code_verification_constant_time():
    manager = PairingManager()
    code = manager.current_code

    # Valid code
    assert manager.verify_code(code)
    assert manager.verify_code(f" {code} ")  # whitespace trimmed

    # Invalid codes
    assert not manager.verify_code("000000" if code != "000000" else "111111")
    assert not manager.verify_code("")
    assert not manager.verify_code("abc")


def test_pairing_code_expiration():
    # 0.1s TTL
    manager = PairingManager(code_ttl_seconds=0.1)
    code = manager.current_code
    assert manager.verify_code(code)

    time.sleep(0.15)
    assert manager.is_code_expired
    assert not manager.verify_code(code)


def test_pairing_code_single_use_consumption():
    manager = PairingManager()
    code = manager.current_code

    # First attempt: valid and consumed
    assert manager.verify_and_consume_code(code) is True
    assert manager.is_code_consumed is True

    # Replay attempt: rejected because code is already consumed
    assert manager.verify_and_consume_code(code) is False
    assert manager.verify_code(code) is False

    # After new code generation, fresh code is valid
    new_code = manager.generate_new_code()
    assert manager.is_code_consumed is False
    assert manager.verify_and_consume_code(new_code) is True


def test_session_verification_and_invalidation():
    manager = PairingManager()
    sess_id = manager.session_id
    assert manager.verify_session(sess_id) is True
    assert manager.verify_session("fake-session-uuid") is False
    assert manager.verify_session("") is False

    # Invalidate session
    manager.invalidate_session()
    assert manager.verify_session(sess_id) is False
    assert manager.verify_session(manager.session_id) is True


def test_local_ip_discovery():
    ips = PairingManager.get_local_ip_addresses()
    assert len(ips) > 0
    primary = PairingManager().get_primary_ip()
    assert primary in ips
    assert not primary.startswith("127.") or len(ips) == 1

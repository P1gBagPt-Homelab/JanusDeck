import pytest
from src.config import SecurityConfig
from src.security import SecurityGate


def test_valid_pin_verification():
    config = SecurityConfig(pin_required=True, master_pin="2070", max_failed_attempts=3, lockout_duration_seconds=10)
    gate = SecurityGate(config)

    valid, msg, detail = gate.verify_pin("2070", client_id="test_client")
    assert valid is True
    assert "successfully" in msg
    assert detail == 0


def test_invalid_pin_decrements_attempts():
    config = SecurityConfig(pin_required=True, master_pin="2070", max_failed_attempts=3, lockout_duration_seconds=10)
    gate = SecurityGate(config)

    valid, msg, remaining = gate.verify_pin("9999", client_id="test_client")
    assert valid is False
    assert remaining == 2
    assert "2 attempt(s) remaining" in msg

    valid, msg, remaining = gate.verify_pin("9998", client_id="test_client")
    assert valid is False
    assert remaining == 1


def test_lockout_after_max_failed_attempts():
    config = SecurityConfig(pin_required=True, master_pin="2070", max_failed_attempts=3, lockout_duration_seconds=5)
    gate = SecurityGate(config)

    # 3 failures
    gate.verify_pin("1111", client_id="client_a")
    gate.verify_pin("2222", client_id="client_a")
    valid, msg, lockout_sec = gate.verify_pin("3333", client_id="client_a")

    assert valid is False
    assert "Locked out" in msg
    assert lockout_sec <= 5

    # Subsequent attempt should be immediately rejected due to lockout
    is_locked, remaining = gate.is_locked_out("client_a")
    assert is_locked is True
    assert remaining > 0

    valid, msg, _ = gate.verify_pin("2070", client_id="client_a")
    assert valid is False
    assert "Locked out" in msg

    # Different client is not locked out
    valid_b, _, _ = gate.verify_pin("2070", client_id="client_b")
    assert valid_b is True


def test_pin_not_required():
    config = SecurityConfig(pin_required=False, master_pin="2070")
    gate = SecurityGate(config)

    valid, msg, _ = gate.verify_pin(None, client_id="client_any")
    assert valid is True
    assert "disabled" in msg


def test_reset_client():
    config = SecurityConfig(pin_required=True, master_pin="2070", max_failed_attempts=2, lockout_duration_seconds=30)
    gate = SecurityGate(config)

    gate.verify_pin("0000", client_id="locked_user")
    gate.verify_pin("0000", client_id="locked_user")
    assert gate.is_locked_out("locked_user")[0] is True

    gate.reset_client("locked_user")
    assert gate.is_locked_out("locked_user")[0] is False

"""Security and Authentication Gate for JanusDeck.

Provides constant-time PIN validation, brute-force rate limiting,
and client lockout safeguards for privileged power and system operations.
"""

from __future__ import annotations

import logging
import secrets
import time
from typing import Dict, Optional, Tuple

from src.config import AppConfig, SecurityConfig, get_config

logger = logging.getLogger("janus.security")


class ClientAttemptRecord:
    """Tracks failed attempts and lockout expiration for a single client."""

    def __init__(self) -> None:
        self.failed_attempts: int = 0
        self.first_failure_time: float = 0.0
        self.locked_until: float = 0.0

    def is_locked(self, now: float) -> Tuple[bool, int]:
        """Check if client is locked out and return remaining lockout seconds."""
        if now < self.locked_until:
            remaining = int(self.locked_until - now) + 1
            return True, remaining
        return False, 0

    def record_failure(self, now: float, max_attempts: int, lockout_seconds: int, window_seconds: int = 120) -> Tuple[bool, int, int]:
        """Record a failed attempt.
        
        Returns:
            Tuple[is_now_locked, remaining_attempts, remaining_lockout_seconds]
        """
        # If past attempt window, reset counter
        if self.failed_attempts > 0 and (now - self.first_failure_time) > window_seconds:
            self.failed_attempts = 0

        if self.failed_attempts == 0:
            self.first_failure_time = now

        self.failed_attempts += 1

        if self.failed_attempts >= max_attempts:
            self.locked_until = now + lockout_seconds
            logger.warning(
                "Client exceeded max PIN attempts (%d/%d). Locked out for %d seconds.",
                self.failed_attempts,
                max_attempts,
                lockout_seconds,
            )
            return True, 0, lockout_seconds

        remaining_attempts = max(0, max_attempts - self.failed_attempts)
        return False, remaining_attempts, 0

    def reset(self) -> None:
        """Reset failed attempts and unlock client."""
        self.failed_attempts = 0
        self.first_failure_time = 0.0
        self.locked_until = 0.0


class SecurityGate:
    """Master PIN authentication gate with rate limiting."""

    def __init__(self, config: Optional[SecurityConfig] = None) -> None:
        self.config = config or get_config().security
        self._clients: Dict[str, ClientAttemptRecord] = {}

    def _get_client_record(self, client_id: str) -> ClientAttemptRecord:
        if client_id not in self._clients:
            self._clients[client_id] = ClientAttemptRecord()
        return self._clients[client_id]

    def is_locked_out(self, client_id: str) -> Tuple[bool, int]:
        """Check if client is locked out.
        
        Returns:
            Tuple[is_locked, remaining_lockout_seconds]
        """
        record = self._clients.get(client_id)
        if not record:
            return False, 0
        return record.is_locked(time.time())

    def verify_pin(self, pin: Optional[str], client_id: str = "default") -> Tuple[bool, str, int]:
        """Verify the provided PIN against the master PIN in constant time.
        
        Returns:
            Tuple[is_valid, message, status_detail]
            where status_detail is remaining attempts (if invalid) or remaining lockout seconds (if locked).
        """
        now = time.time()
        record = self._get_client_record(client_id)

        # 1. Check if client is locked out
        is_locked, remaining_lockout = record.is_locked(now)
        if is_locked:
            return (
                False,
                f"Too many failed attempts. Locked out for {remaining_lockout} more second(s).",
                remaining_lockout,
            )

        # 2. Check if PIN is required
        if not self.config.pin_required:
            return True, "PIN authentication is disabled.", 0

        # 3. Handle missing PIN input
        if pin is None or pin == "":
            is_locked_now, remaining_attempts, lockout_sec = record.record_failure(
                now,
                max_attempts=self.config.max_failed_attempts,
                lockout_seconds=self.config.lockout_duration_seconds,
            )
            if is_locked_now:
                return (
                    False,
                    f"Too many failed attempts. Locked out for {lockout_sec} seconds.",
                    lockout_sec,
                )
            return (
                False,
                f"PIN required. {remaining_attempts} attempt(s) remaining.",
                remaining_attempts,
            )

        # 4. Constant-time comparison to prevent timing attacks
        target_pin = str(self.config.master_pin).strip()
        candidate_pin = str(pin).strip()

        # Compare using secrets.compare_digest
        is_valid = secrets.compare_digest(candidate_pin, target_pin)

        if is_valid:
            record.reset()
            return True, "PIN verified successfully.", 0

        # 5. Handle failure & rate limit increment
        is_locked_now, remaining_attempts, lockout_sec = record.record_failure(
            now,
            max_attempts=self.config.max_failed_attempts,
            lockout_seconds=self.config.lockout_duration_seconds,
        )

        if is_locked_now:
            return (
                False,
                f"Too many failed attempts. Locked out for {lockout_sec} seconds.",
                lockout_sec,
            )

        return (
            False,
            f"Invalid PIN. {remaining_attempts} attempt(s) remaining.",
            remaining_attempts,
        )

    def reset_client(self, client_id: str) -> None:
        """Clear lockout and attempt count for a client (useful in tests or admin reset)."""
        if client_id in self._clients:
            self._clients[client_id].reset()


_security_gate_instance: Optional[SecurityGate] = None


def get_security_gate(config: Optional[AppConfig] = None) -> SecurityGate:
    """Get or create singleton instance of SecurityGate."""
    global _security_gate_instance
    if _security_gate_instance is None or config is not None:
        cfg = config or get_config()
        _security_gate_instance = SecurityGate(cfg.security)
    return _security_gate_instance

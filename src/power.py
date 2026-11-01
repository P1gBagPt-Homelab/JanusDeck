"""Host Power & Dual-Boot Bridge for JanusDeck.

Interfaces with host systemd DBus (org.freedesktop.login1.Manager)
for graceful reboot and shutdown, coordinates one-shot dual-boot switching via GRUB,
and provides simulation mode for development and testing.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional

from src.config import AppConfig, OSTarget, PowerConfig, get_config
from src.grub import GrubManager, get_grub_manager
from src.security import SecurityGate, get_security_gate

logger = logging.getLogger("janus.power")


class PowerService:
    """Orchestrates system power actions, GRUB next_entry scheduling, and security."""

    def __init__(
        self,
        config: Optional[PowerConfig] = None,
        grub_manager: Optional[GrubManager] = None,
        security_gate: Optional[SecurityGate] = None,
    ) -> None:
        self.config = config or get_config().power
        self.grub_manager = grub_manager or get_grub_manager()
        self.security_gate = security_gate or get_security_gate()
        self.dbus_socket_path = Path(self.config.dbus_socket_path)
        self.action_history: List[Dict[str, Any]] = []

        # Auto-detect simulation mode if explicitly requested or if dbus socket is missing outside Linux
        self._simulate = self.config.simulate or not self.dbus_socket_path.exists()
        if self._simulate:
            self.grub_manager.simulate = True
            logger.info(
                "PowerService initialized in SIMULATION mode (socket '%s' found=%s, config.simulate=%s)",
                self.dbus_socket_path,
                self.dbus_socket_path.exists(),
                self.config.simulate,
            )
        else:
            logger.info("PowerService initialized with host DBus socket at %s", self.dbus_socket_path)

    @property
    def is_simulated(self) -> bool:
        return self._simulate

    def is_dbus_socket_available(self) -> bool:
        return self.dbus_socket_path.exists()

    async def get_power_status(self) -> Dict[str, Any]:
        """Returns the current state and capabilities of the power management bridge."""
        current_next_entry = await self.grub_manager.get_next_entry()
        return {
            "allow_shutdown": self.config.allow_shutdown,
            "allow_reboot": self.config.allow_reboot,
            "allow_os_switch": self.config.allow_os_switch,
            "simulate_mode": self._simulate,
            "dbus_socket_present": self.is_dbus_socket_available(),
            "dbus_socket_path": str(self.dbus_socket_path),
            "current_next_entry": current_next_entry,
            "os_targets": [t.model_dump() for t in self.config.os_targets],
            "last_action": self.action_history[-1] if self.action_history else None,
        }

    async def _execute_dbus_login1_method(self, method_name: str, interactive: bool = True) -> Dict[str, Any]:
        """Executes a login1 Manager DBus call (Reboot or PowerOff).
        
        Tries dbus-send, then busctl, then systemctl.
        In simulation mode, records the event and returns immediately.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        if self._simulate:
            record = {
                "action": method_name,
                "simulated": True,
                "timestamp": timestamp,
                "interactive": interactive,
                "success": True,
                "detail": f"[SIMULATION] Host {method_name} requested via DBus org.freedesktop.login1",
            }
            self.action_history.append(record)
            logger.info("[SIMULATION] %s", record["detail"])
            return record

        # 1. Strategy A: dbus-send
        dbus_send_bin = shutil.which("dbus-send")
        if dbus_send_bin:
            cmd = [
                dbus_send_bin,
                "--system",
                "--print-reply",
                "--dest=org.freedesktop.login1",
                "/org/freedesktop/login1",
                f"org.freedesktop.login1.Manager.{method_name}",
                f"boolean:{'true' if interactive else 'false'}",
            ]
            try:
                logger.info("Executing DBus command: %s", " ".join(cmd))
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode == 0:
                    record = {
                        "action": method_name,
                        "simulated": False,
                        "timestamp": timestamp,
                        "interactive": interactive,
                        "success": True,
                        "detail": f"Successfully invoked {method_name} via dbus-send",
                    }
                    self.action_history.append(record)
                    return record
                logger.warning(
                    "dbus-send returned code %d: %s. Trying fallback.",
                    proc.returncode,
                    stderr.decode().strip(),
                )
            except Exception as exc:
                logger.warning("dbus-send execution error: %s. Trying fallback.", exc)

        # 2. Strategy B: busctl
        busctl_bin = shutil.which("busctl")
        if busctl_bin:
            cmd = [
                busctl_bin,
                "call",
                "org.freedesktop.login1",
                "/org/freedesktop/login1",
                "org.freedesktop.login1.Manager",
                method_name,
                "b",
                "true" if interactive else "false",
            ]
            try:
                logger.info("Executing busctl command: %s", " ".join(cmd))
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode == 0:
                    record = {
                        "action": method_name,
                        "simulated": False,
                        "timestamp": timestamp,
                        "interactive": interactive,
                        "success": True,
                        "detail": f"Successfully invoked {method_name} via busctl",
                    }
                    self.action_history.append(record)
                    return record
            except Exception as exc:
                logger.warning("busctl execution error: %s", exc)

        # 3. Strategy C: systemctl
        systemctl_bin = shutil.which("systemctl")
        if systemctl_bin:
            subcommand = "reboot" if method_name == "Reboot" else "poweroff"
            cmd = [systemctl_bin, subcommand]
            try:
                logger.info("Executing systemctl fallback: %s", " ".join(cmd))
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode == 0:
                    record = {
                        "action": method_name,
                        "simulated": False,
                        "timestamp": timestamp,
                        "interactive": interactive,
                        "success": True,
                        "detail": f"Successfully invoked {method_name} via systemctl",
                    }
                    self.action_history.append(record)
                    return record
            except Exception as exc:
                logger.warning("systemctl execution error: %s", exc)

        # If all methods failed
        err_msg = (
            f"Failed to execute DBus {method_name}. Ensure dbus-send, busctl, or systemctl "
            f"is installed and /var/run/dbus/system_bus_socket is mounted."
        )
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    async def reboot(self, interactive: bool = True) -> Dict[str, Any]:
        """Issues host reboot via DBus."""
        if not self.config.allow_reboot:
            raise PermissionError("Host reboot action is disabled in server configuration.")
        return await self._execute_dbus_login1_method("Reboot", interactive=interactive)

    async def poweroff(self, interactive: bool = True) -> Dict[str, Any]:
        """Issues host graceful shutdown via DBus."""
        if not self.config.allow_shutdown:
            raise PermissionError("Host shutdown action is disabled in server configuration.")
        return await self._execute_dbus_login1_method("PowerOff", interactive=interactive)

    async def switch_os(
        self,
        target_id: Optional[str] = None,
        grub_entry: Optional[str] = None,
        interactive: bool = True,
    ) -> Dict[str, Any]:
        """Configures GRUB next_entry and triggers host reboot."""
        if not self.config.allow_os_switch:
            raise PermissionError("Dual-boot OS switching is disabled in server configuration.")

        entry_to_boot: Optional[str] = None
        target_name: str = "Unknown"

        # Resolve target
        if target_id:
            resolved = self.grub_manager.resolve_target(target_id)
            if resolved:
                entry_to_boot = resolved.grub_entry
                target_name = resolved.name
            else:
                # If target_id wasn't in config targets, treat as raw entry if permitted
                entry_to_boot = target_id
                target_name = target_id
        elif grub_entry:
            entry_to_boot = grub_entry
            target_name = grub_entry

        if not entry_to_boot:
            raise ValueError("Neither target_id nor grub_entry was provided.")

        # Set GRUB next_entry
        logger.info("Setting GRUB next_entry to '%s' for target '%s'", entry_to_boot, target_name)
        await self.grub_manager.set_next_entry(entry_to_boot)

        # Trigger reboot
        reboot_result = await self.reboot(interactive=interactive)

        return {
            "status": "switching_os",
            "target_id": target_id,
            "target_name": target_name,
            "grub_entry": entry_to_boot,
            "simulated": reboot_result.get("simulated", False),
            "reboot_result": reboot_result,
            "message": f"GRUB configured to boot '{target_name}'. Reboot initiated.",
        }


_power_service_instance: Optional[PowerService] = None


def get_power_service(config: Optional[AppConfig] = None) -> PowerService:
    """Get or create singleton instance of PowerService."""
    global _power_service_instance
    if _power_service_instance is None or config is not None:
        cfg = config or get_config()
        _power_service_instance = PowerService(
            config=cfg.power,
            grub_manager=get_grub_manager(cfg),
            security_gate=get_security_gate(cfg),
        )
    return _power_service_instance

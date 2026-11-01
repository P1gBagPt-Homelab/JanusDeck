"""GRUB Bootloader Configuration & Environment Manager.

Handles reading /boot/grub/grub.cfg menu entries, reading/writing
one-shot boot entries to /boot/grub/grubenv, and fallback simulation mode.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List, Optional

from src.config import AppConfig, OSTarget, PowerConfig, get_config

logger = logging.getLogger("janus.grub")

GRUBENV_HEADER = "# GRUB Environment Block\n"
GRUBENV_TOTAL_SIZE = 1024


def parse_grubenv_bytes(content: bytes) -> Dict[str, str]:
    """Parse GRUB environment block content into a key-value dictionary."""
    text = content.decode("utf-8", errors="replace")
    variables: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            variables[key.strip()] = val.strip()
    return variables


def serialize_grubenv_bytes(variables: Dict[str, str]) -> bytes:
    """Serialize key-value dictionary into 1024-byte GRUB environment block."""
    lines = [GRUBENV_HEADER]
    for key, val in variables.items():
        lines.append(f"{key}={val}\n")
    body = "".join(lines)
    encoded = body.encode("utf-8")
    if len(encoded) > GRUBENV_TOTAL_SIZE:
        raise ValueError(
            f"GRUB environment block content exceeds {GRUBENV_TOTAL_SIZE} bytes (is {len(encoded)} bytes)"
        )
    padding = b"#" * (GRUBENV_TOTAL_SIZE - len(encoded))
    return encoded + padding


class GrubManager:
    """Interface for inspecting GRUB configurations and updating boot targets."""

    def __init__(self, config: Optional[PowerConfig] = None) -> None:
        self.config = config or get_config().power
        self.grub_cfg_path = Path(self.config.grub_cfg_path)
        self.grubenv_path = Path(self.config.grubenv_path)
        self.simulate = self.config.simulate
        self._simulated_next_entry: Optional[str] = None

        # Auto-detect simulation mode if explicitly configured, or if grubenv cannot be written
        if not self.simulate:
            try:
                if self.grubenv_path.exists():
                    if not os.access(self.grubenv_path, os.W_OK):
                        self.simulate = True
                        logger.info(
                            "GrubManager auto-enabled SIMULATION mode (grubenv at %s is read-only)",
                            self.grubenv_path,
                        )
                else:
                    # Attempt to verify write access to parent directory
                    if not self.grubenv_path.parent.exists() or not os.access(self.grubenv_path.parent, os.W_OK):
                        self.simulate = True
                        logger.info(
                            "GrubManager auto-enabled SIMULATION mode (parent dir for %s not writable)",
                            self.grubenv_path,
                        )
            except Exception:
                self.simulate = True

    def is_grubenv_available(self) -> bool:
        """Checks if grubenv file is accessible or if grub-editenv is installed."""
        if self.simulate:
            return True
        return self.grubenv_path.exists() or shutil.which("grub-editenv") is not None

    def is_grub_cfg_available(self) -> bool:
        """Checks if grub.cfg exists on disk."""
        return self.grub_cfg_path.is_file()

    def parse_menu_entries(self) -> List[Dict[str, Any]]:
        """Parses grub.cfg to discover bootable menu entries.
        
        Returns a list of entry dicts containing:
        - title: display title
        - full_id: menuentry ID or title
        - classes: list of CSS/icon class hints (e.g. ['ubuntu', 'gnu-linux'])
        - submenu: parent submenu title if nested
        """
        if not self.is_grub_cfg_available():
            logger.debug("GRUB configuration not found at %s", self.grub_cfg_path)
            return []

        entries: List[Dict[str, Any]] = []
        try:
            content = self.grub_cfg_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.error("Failed to read GRUB config %s: %s", self.grub_cfg_path, exc)
            return []

        current_submenu: Optional[str] = None
        # Match lines like:
        # submenu 'Advanced options for Ubuntu' ... {
        # menuentry 'Ubuntu' --class ubuntu --class gnu-linux ... {
        submenu_regex = re.compile(r"^\s*submenu\s+['\"]([^'\"]+)['\"]")
        menuentry_regex = re.compile(
            r"^\s*menuentry\s+['\"]([^'\"]+)['\"](.*)$"
        )
        closing_brace_regex = re.compile(r"^\s*\}\s*$")

        for line in content.splitlines():
            # Check submenu
            if sub_match := submenu_regex.match(line):
                current_submenu = sub_match.group(1)
                continue

            # Check menuentry
            if entry_match := menuentry_regex.match(line):
                title = entry_match.group(1)
                remainder = entry_match.group(2)
                
                # Extract classes
                classes = re.findall(r"--class\s+([a-zA-Z0-9_\-]+)", remainder)
                
                # Extract id option if present
                id_match = re.search(r"--id\s+['\"]?([a-zA-Z0-9_\-]+)['\"]?", remainder)
                entry_id = id_match.group(1) if id_match else title

                entries.append({
                    "title": title,
                    "id": entry_id,
                    "classes": classes,
                    "submenu": current_submenu,
                    "full_path": f"{current_submenu}>{title}" if current_submenu else title,
                })

        return entries

    async def get_next_entry(self) -> Optional[str]:
        """Retrieve current next_entry from grubenv or simulated state."""
        if self.simulate:
            return self._simulated_next_entry

        # Try grub-editenv list CLI if available
        editenv_bin = shutil.which("grub-editenv")
        if editenv_bin and self.grubenv_path.exists():
            try:
                proc = await asyncio.create_subprocess_exec(
                    editenv_bin,
                    str(self.grubenv_path),
                    "list",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                if proc.returncode == 0:
                    parsed = parse_grubenv_bytes(stdout)
                    return parsed.get("next_entry")
            except Exception as exc:
                logger.debug("grub-editenv command failed: %s. Falling back to direct read.", exc)

        # Fallback to direct file read
        if self.grubenv_path.is_file():
            try:
                data = self.grubenv_path.read_bytes()
                parsed = parse_grubenv_bytes(data)
                return parsed.get("next_entry")
            except Exception as exc:
                logger.error("Failed to read grubenv file at %s: %s", self.grubenv_path, exc)

        return self._simulated_next_entry

    async def set_next_entry(self, entry: str) -> bool:
        """Sets GRUB next_entry to the specified boot entry name or ID."""
        if not entry:
            raise ValueError("GRUB boot entry cannot be empty")

        if self.simulate:
            self._simulated_next_entry = entry
            logger.info("[SIMULATION] GRUB next_entry set to '%s'", entry)
            return True

        # Try grub-editenv command first
        editenv_bin = shutil.which("grub-editenv")
        if editenv_bin:
            try:
                proc = await asyncio.create_subprocess_exec(
                    editenv_bin,
                    str(self.grubenv_path),
                    "set",
                    f"next_entry={entry}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode == 0:
                    logger.info("grub-editenv successfully set next_entry='%s'", entry)
                    return True
                logger.warning(
                    "grub-editenv failed with code %d: %s. Trying direct file update.",
                    proc.returncode,
                    stderr.decode().strip(),
                )
            except Exception as exc:
                logger.warning("Error running grub-editenv: %s. Trying direct file update.", exc)

        # Direct file writing fallback
        try:
            vars_dict: Dict[str, str] = {}
            if self.grubenv_path.is_file():
                raw = self.grubenv_path.read_bytes()
                vars_dict = parse_grubenv_bytes(raw)

            vars_dict["next_entry"] = entry
            serialized = serialize_grubenv_bytes(vars_dict)

            # Ensure parent directory exists
            self.grubenv_path.parent.mkdir(parents=True, exist_ok=True)
            self.grubenv_path.write_bytes(serialized)
            logger.info("Directly updated grubenv at %s with next_entry='%s'", self.grubenv_path, entry)
            return True
        except Exception as exc:
            logger.error("Failed to write grubenv at %s: %s", self.grubenv_path, exc)
            raise RuntimeError(f"Could not write GRUB next_entry to {self.grubenv_path}: {exc}") from exc

    async def clear_next_entry(self) -> bool:
        """Clears GRUB next_entry, ensuring default OS boots on next startup."""
        if self.simulate:
            self._simulated_next_entry = None
            logger.info("[SIMULATION] Cleared GRUB next_entry")
            return True

        editenv_bin = shutil.which("grub-editenv")
        if editenv_bin and self.grubenv_path.exists():
            try:
                proc = await asyncio.create_subprocess_exec(
                    editenv_bin,
                    str(self.grubenv_path),
                    "unset",
                    "next_entry",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                if proc.returncode == 0:
                    return True
            except Exception:
                pass

        if self.grubenv_path.is_file():
            try:
                raw = self.grubenv_path.read_bytes()
                vars_dict = parse_grubenv_bytes(raw)
                vars_dict.pop("next_entry", None)
                serialized = serialize_grubenv_bytes(vars_dict)
                self.grubenv_path.write_bytes(serialized)
                return True
            except Exception as exc:
                logger.error("Failed to clear next_entry from grubenv: %s", exc)
                return False

        return True

    def resolve_target(self, target_id_or_entry: str) -> Optional[OSTarget]:
        """Resolves target against configured os_targets in config."""
        for target in self.config.os_targets:
            if target.id.lower() == target_id_or_entry.lower() or target.grub_entry == target_id_or_entry:
                return target
        return None


_grub_manager_instance: Optional[GrubManager] = None


def get_grub_manager(config: Optional[AppConfig] = None) -> GrubManager:
    """Get or create singleton instance of GrubManager."""
    global _grub_manager_instance
    if _grub_manager_instance is None or config is not None:
        cfg = config or get_config()
        _grub_manager_instance = GrubManager(cfg.power)
    return _grub_manager_instance

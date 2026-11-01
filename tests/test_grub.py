from pathlib import Path
import pytest
from src.config import OSTarget, PowerConfig
from src.grub import (
    GRUBENV_TOTAL_SIZE,
    GrubManager,
    parse_grubenv_bytes,
    serialize_grubenv_bytes,
)

SAMPLE_GRUB_CFG = """
# GRUB configuration file
menuentry 'Ubuntu' --class ubuntu --class gnu-linux --class gnu --class os $menuentry_id_option 'gnulinux-simple-1234' {
    recordfail
    load_video
}
submenu 'Advanced options for Ubuntu' $menuentry_id_option 'gnulinux-advanced-1234' {
    menuentry 'Ubuntu, with Linux 6.8.0-45-generic' --class ubuntu --class gnu-linux {
        linux /boot/vmlinuz
    }
}
menuentry 'Windows Boot Manager (on /dev/nvme0n1p1)' --class windows --class os $menuentry_id_option 'osprober-efi-ABCD' {
    insmod part_gpt
    chainloader /EFI/Microsoft/Boot/bootmgfw.efi
}
"""


def test_grubenv_serialization_and_parsing():
    vars_in = {"saved_entry": "0", "next_entry": "Windows Boot Manager", "debug": "1"}
    raw_bytes = serialize_grubenv_bytes(vars_in)

    assert len(raw_bytes) == GRUBENV_TOTAL_SIZE
    assert raw_bytes.startswith(b"# GRUB Environment Block\n")
    assert raw_bytes.endswith(b"#")

    vars_out = parse_grubenv_bytes(raw_bytes)
    assert vars_out["saved_entry"] == "0"
    assert vars_out["next_entry"] == "Windows Boot Manager"
    assert vars_out["debug"] == "1"


def test_grub_cfg_parsing(tmp_path: Path):
    cfg_file = tmp_path / "grub.cfg"
    cfg_file.write_text(SAMPLE_GRUB_CFG, encoding="utf-8")

    power_cfg = PowerConfig(grub_cfg_path=str(cfg_file), grubenv_path=str(tmp_path / "grubenv"))
    manager = GrubManager(power_cfg)

    entries = manager.parse_menu_entries()
    assert len(entries) == 3

    assert entries[0]["title"] == "Ubuntu"
    assert "ubuntu" in entries[0]["classes"]
    assert entries[0]["submenu"] is None

    assert entries[1]["title"] == "Ubuntu, with Linux 6.8.0-45-generic"
    assert entries[1]["submenu"] == "Advanced options for Ubuntu"

    assert entries[2]["title"] == "Windows Boot Manager (on /dev/nvme0n1p1)"
    assert "windows" in entries[2]["classes"]


@pytest.mark.asyncio
async def test_grubenv_set_and_clear_file(tmp_path: Path):
    grubenv_file = tmp_path / "grubenv"
    initial_bytes = serialize_grubenv_bytes({"saved_entry": "0"})
    grubenv_file.write_bytes(initial_bytes)

    power_cfg = PowerConfig(
        grub_cfg_path=str(tmp_path / "nonexistent.cfg"),
        grubenv_path=str(grubenv_file),
        simulate=False,
    )
    manager = GrubManager(power_cfg)

    # Initially next_entry is None
    next_entry = await manager.get_next_entry()
    assert next_entry is None

    # Set next_entry
    await manager.set_next_entry("Windows 11")
    updated = await manager.get_next_entry()
    assert updated == "Windows 11"
    assert grubenv_file.stat().st_size == GRUBENV_TOTAL_SIZE

    # Clear next_entry
    await manager.clear_next_entry()
    cleared = await manager.get_next_entry()
    assert cleared is None
    assert grubenv_file.stat().st_size == GRUBENV_TOTAL_SIZE


@pytest.mark.asyncio
async def test_grubenv_clear_also_resets_target_saved_entry(tmp_path: Path):
    grubenv_file = tmp_path / "grubenv"
    initial_bytes = serialize_grubenv_bytes({
        "next_entry": "Windows Boot Manager (on /dev/nvme0n1p1)",
        "saved_entry": "Windows Boot Manager (on /dev/nvme0n1p1)",
    })
    grubenv_file.write_bytes(initial_bytes)

    power_cfg = PowerConfig(
        grubenv_path=str(grubenv_file),
        simulate=False,
        os_targets=[
            OSTarget(id="windows", name="Windows 11", grub_entry="Windows Boot Manager (on /dev/nvme0n1p1)"),
        ],
    )
    manager = GrubManager(power_cfg)

    await manager.clear_next_entry()
    assert await manager.get_next_entry() is None

    # Verify both next_entry and saved_entry were purged
    final_vars = parse_grubenv_bytes(grubenv_file.read_bytes())
    assert "next_entry" not in final_vars
    assert "saved_entry" not in final_vars


@pytest.mark.asyncio
async def test_grub_simulation_mode():
    power_cfg = PowerConfig(simulate=True)
    manager = GrubManager(power_cfg)

    await manager.set_next_entry("Bazzite OS")
    assert await manager.get_next_entry() == "Bazzite OS"

    await manager.clear_next_entry()
    assert await manager.get_next_entry() is None


def test_resolve_os_target():
    targets = [
        OSTarget(
            id="windows",
            name="Windows 11 (Gaming)",
            grub_entry="Windows Boot Manager (on /dev/nvme0n1p1)",
        ),
        OSTarget(
            id="bazzite",
            name="Bazzite Linux",
            grub_entry="Bazzite OS",
        ),
    ]
    power_cfg = PowerConfig(os_targets=targets)
    manager = GrubManager(power_cfg)

    resolved = manager.resolve_target("windows")
    assert resolved is not None
    assert resolved.grub_entry == "Windows Boot Manager (on /dev/nvme0n1p1)"

    resolved_entry = manager.resolve_target("Bazzite OS")
    assert resolved_entry is not None
    assert resolved_entry.id == "bazzite"

    assert manager.resolve_target("unknown_target") is None

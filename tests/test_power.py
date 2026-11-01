from unittest.mock import AsyncMock, patch
import pytest
from src.config import OSTarget, PowerConfig
from src.grub import GrubManager
from src.power import PowerService
from src.security import SecurityGate


@pytest.mark.asyncio
async def test_power_service_status_simulated():
    config = PowerConfig(
        allow_shutdown=True,
        allow_reboot=True,
        allow_os_switch=True,
        simulate=True,
        os_targets=[
            OSTarget(id="windows", name="Windows 11", grub_entry="Windows Boot Manager"),
        ],
    )
    grub = GrubManager(config)
    gate = SecurityGate()
    service = PowerService(config=config, grub_manager=grub, security_gate=gate)

    status = await service.get_power_status()
    assert status["allow_reboot"] is True
    assert status["allow_shutdown"] is True
    assert status["allow_os_switch"] is True
    assert status["simulate_mode"] is True
    assert len(status["os_targets"]) == 1


@pytest.mark.asyncio
async def test_power_service_simulated_actions():
    config = PowerConfig(simulate=True)
    grub = GrubManager(config)
    service = PowerService(config=config, grub_manager=grub)

    # Stage next_entry first
    await grub.set_next_entry("Windows 11")
    assert await grub.get_next_entry() == "Windows 11"

    # Reboot should clear next_entry so system reboots into default OS
    res_reboot = await service.reboot(interactive=True)
    assert res_reboot["action"] == "Reboot"
    assert res_reboot["simulated"] is True
    assert res_reboot["success"] is True
    assert await grub.get_next_entry() is None

    # Shutdown
    res_shutdown = await service.poweroff(interactive=True)
    assert res_shutdown["action"] == "PowerOff"
    assert res_shutdown["simulated"] is True

    # Check history
    assert len(service.action_history) == 2


@pytest.mark.asyncio
async def test_power_service_switch_os_simulated():
    config = PowerConfig(
        simulate=True,
        os_targets=[
            OSTarget(id="windows", name="Windows 11", grub_entry="Windows Boot Manager"),
        ],
    )
    grub = GrubManager(config)
    service = PowerService(config=config, grub_manager=grub)

    res = await service.switch_os(target_id="windows")
    assert res["status"] == "switching_os"
    assert res["target_name"] == "Windows 11"
    assert res["grub_entry"] == "Windows Boot Manager"
    assert res["simulated"] is True

    # Check that next_entry was updated
    assert await grub.get_next_entry() == "Windows Boot Manager"


@pytest.mark.asyncio
async def test_power_service_permission_checks():
    config = PowerConfig(
        allow_reboot=False,
        allow_shutdown=False,
        allow_os_switch=False,
        simulate=True,
    )
    service = PowerService(config=config)

    with pytest.raises(PermissionError, match="reboot"):
        await service.reboot()

    with pytest.raises(PermissionError, match="shutdown"):
        await service.poweroff()

    with pytest.raises(PermissionError, match="OS switching"):
        await service.switch_os(target_id="windows")


@pytest.mark.asyncio
async def test_real_dbus_execution_with_mocked_subprocess():
    # Force real execution mode
    config = PowerConfig(simulate=False, dbus_socket_path="/nonexistent/socket")
    grub = GrubManager(config)
    service = PowerService(config=config, grub_manager=grub)
    # Manually turn off simulation flag for this unit test
    service._simulate = False

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate.return_value = (b"method return sender=:1.0 -> dest=:1.1", b"")

    with patch("shutil.which", return_value="/usr/bin/dbus-send"), \
         patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        result = await service.reboot(interactive=True)
        assert result["success"] is True
        assert result["simulated"] is False
        mock_exec.assert_called_once()
        cmd_args = mock_exec.call_args[0]
        assert "/usr/bin/dbus-send" in cmd_args
        assert "org.freedesktop.login1.Manager.Reboot" in cmd_args
        assert "boolean:true" in cmd_args

# JanusDeck Technical Architecture

This document explains the technical mechanisms JanusDeck uses to control host power and switch operating systems from within a Docker container.

---

## 1. The Dual-Boot Bootloader Bridge

In dual-boot machines running GNU GRUB, the boot sequence can be temporarily altered without changing the default operating system permanently.

### Standard Headless Boot Sequence:
1. PC powers on (manually or via smart PCIe switch).
2. GRUB loads `/boot/grub/grub.cfg`.
3. GRUB reads `/boot/grub/grubenv`.
4. If `next_entry` is not set, GRUB boots entry `0` (Linux Server).

### One-Shot OS Switching:
When the user clicks "Switch to Windows" on JanusDeck:
1. JanusDeck verifies the master PIN.
2. JanusDeck writes to `/boot/grub/grubenv`:
   ```bash
   grub-editenv /boot/grub/grubenv set next_entry="Windows Boot Manager (on /dev/nvme0n1p1)"
   ```
3. JanusDeck issues a reboot request.
4. GRUB reads `next_entry`, clears `next_entry` so it won't repeat, and boots Windows.
5. Next time the user shuts down Windows, the next boot has no `next_entry`, so it automatically falls back to entry `0` (Linux Server).

---

## 2. Host Power Management via DBus

Rather than requiring full `root` host SSH or unconstrained container privileges, JanusDeck mounts the host system DBus socket:
```yaml
volumes:
  - /var/run/dbus/system_bus_socket:/var/run/dbus/system_bus_socket:ro
```

This permits sending standardized Freedesktop login1 manager signals:
* **Reboot**: `org.freedesktop.login1.Manager.Reboot(true)`
* **Poweroff**: `org.freedesktop.login1.Manager.PowerOff(true)`

These trigger graceful ACPI shutdowns with filesystem syncs and proper container teardowns.

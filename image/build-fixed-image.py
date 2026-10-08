#!/usr/bin/env python3
"""Offline, board-specific image customization; never flash a physical device."""
# SPDX-License-Identifier: GPL-2.0-only
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

REPO = Path(__file__).resolve().parents[1]
KERNEL_SHA = "e340675c1c70b3e215c6858bce42c1262a3a11d493d7cfbe4824f7460bd1b7a0"
SYSTEM_SHA = "e02890e8c360d4cfee77962b17f520716229892b0496211b8ed0742b21865b1b"
DTB_SHA = "2e725746f1a78732180a3d8f79cab4de0a3ef5814c3f62747b966e23eff99061"
MODULE_SHA = "598b4e4c1774710901ce2a6240e579af1ae31071f9c4ef56c619455c04fec84e"


def run(*args, capture=False):
    return subprocess.run([str(x) for x in args], check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def md5(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "md5").hexdigest()


def verify(path, expected):
    actual = sha(path)
    if actual != expected:
        raise RuntimeError(f"SHA256 mismatch: {path}: {actual}")


def customize(args):
    original, output = args.original.resolve(), args.output.resolve()
    if not original.is_file() or output.exists() or original == output:
        raise RuntimeError("Input must exist and output must be a new path")
    if not original.stat().st_size:
        raise RuntimeError("Invalid input image")
    layout = json.loads(run("sfdisk", "--json", original, capture=True))["partitiontable"]
    parts = layout["partitions"]
    if (layout["label"] != "dos" or layout["sectorsize"] != 512 or len(parts) != 2 or
            [(p["start"], p["size"], p["type"]) for p in parts] !=
            [(16384, 1048576, "c"), (1064960, 65536, "83")]):
        raise RuntimeError("Unsupported partition layout; use the pinned original image")
    verify(REPO / "boot/dtb.img", DTB_SHA)
    verify(REPO / "storage/.config/wifi-drivers/88x2cs-5.15.196.ko", MODULE_SHA)
    original_sha = sha(original)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(original, output)
    loop = None
    mounted = []
    with tempfile.TemporaryDirectory(prefix="s905x2-image-") as tmp:
        tmp = Path(tmp)
        boot, storage, payload = tmp / "boot", tmp / "storage", tmp / "payload"
        for directory in (boot, storage, payload):
            directory.mkdir()
        try:
            loop = run("losetup", "--find", "--show", "--partscan", output, capture=True).strip()
            run("udevadm", "settle")
            # Validate both partitions read-only before making any edits.
            run("mount", "-o", "ro", loop + "p1", boot)
            mounted.append(boot)
            verify(boot / "kernel.img", KERNEL_SHA)
            verify(boot / "SYSTEM", SYSTEM_SHA)
            preserved_files = {name: sha(boot / name) for name in (
                "config.ini", "cfgload", "cfgload_env", "aml_autoscript", "recovery.img",
                "kernel.img.md5", "SYSTEM.md5",
            )}
            if (boot / "mount-storage.sh").exists() or (boot / "dtb.img").exists():
                raise RuntimeError("Input boot partition is already customized")
            run("mount", "-o", "ro,noload", loop + "p2", storage)
            mounted.append(storage)
            if not (storage / ".please_resize_me").is_file():
                raise RuntimeError("Input has no first-boot resize marker")
            if any((storage / p).exists() for p in (".config", ".kodi", ".cache")):
                raise RuntimeError("Input storage is already initialized")
            run("umount", storage)
            mounted.remove(storage)
            run("mount", "-o", "remount,rw", boot)

            for relative in (
                ".config/wifi-drivers/88x2cs-5.15.196.ko",
                ".config/wifi-vendor-load.sh",
                ".config/system.d/wifi-vendor.service",
                ".config/modprobe.d/90-s905x2-rtl8822cs.conf",
            ):
                dest = payload / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(REPO / "storage" / relative, dest)
            shutil.copyfile(REPO / "scripts/restore-native-wifi.sh",
                            payload / ".config/restore-native-wifi.sh")
            wants = payload / ".config/system.d/multi-user.target.wants"
            wants.mkdir()
            (wants / "wifi-vendor.service").symlink_to("../wifi-vendor.service")
            target = boot / "s905x2-fixes"
            target.mkdir()
            files = sorted(p for p in payload.rglob("*") if p.is_file() and not p.is_symlink())
            checksums = "".join(f"{sha(p)}  {p.relative_to(payload)}\n" for p in files)
            (target / "storage-files.sha256").write_text(checksums)
            (target / "storage-files.md5").write_text("".join(
                f"{md5(p)}  {p.relative_to(payload)}\n" for p in files))
            with (target / "storage.tar.gz").open("wb") as f:
                with gzip.GzipFile(fileobj=f, mode="wb", filename="", mtime=0) as gz:
                    with tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as tar:
                        for p in files:
                            info = tar.gettarinfo(str(p), str(p.relative_to(payload)))
                            info.uid = info.gid = 0
                            info.uname = info.gname = "root"
                            info.mtime = 0
                            info.mode = 0o755 if p.suffix == ".sh" else 0o644
                            with p.open("rb") as source:
                                tar.addfile(info, source)
                        link = tarfile.TarInfo(".config/system.d/multi-user.target.wants/wifi-vendor.service")
                        link.type = tarfile.SYMTYPE
                        link.linkname = "../wifi-vendor.service"
                        link.mode = 0o777
                        link.uid = link.gid = 0
                        link.uname = link.gname = "root"
                        tar.addfile(link)
            (target / "payload.sha256").write_text(f"{sha(target / 'storage.tar.gz')}  storage.tar.gz\n")
            (target / "payload.md5").write_text(f"{md5(target / 'storage.tar.gz')}  storage.tar.gz\n")
            shutil.copyfile(REPO / "image/install-storage.sh", target / "install-storage.sh")
            shutil.copyfile(REPO / "image/mount-storage.sh", boot / "mount-storage.sh")
            shutil.copyfile(REPO / "boot/dtb.img", boot / "dtb.img")
            shutil.copyfile(REPO / "boot/hdmi-only.dtb", target / "hdmi-only.dtb")
            (target / "build-info.json").write_text(json.dumps({
                "original_sha256": original_sha,
                "kernel_sha256": KERNEL_SHA, "system_sha256": SYSTEM_SHA,
                "dtb_sha256": DTB_SHA, "module_sha256": MODULE_SHA,
                "cec": "stock, unchanged",
                "repository": "https://github.com/Jioyzen/s905x2-coreelec-no-fixes",
            }, indent=2) + "\n")
            verify(boot / "kernel.img", KERNEL_SHA)
            verify(boot / "SYSTEM", SYSTEM_SHA)
            for name, digest in preserved_files.items():
                verify(boot / name, digest)
            run("sync")
            run("umount", boot)
            mounted.remove(boot)
            run("fsck.fat", "-n", loop + "p1")
            run("e2fsck", "-f", "-n", loop + "p2")
        finally:
            for mountpoint in reversed(mounted):
                run("umount", mountpoint)
            if loop:
                run("losetup", "--detach", loop)
    if sha(original) != original_sha:
        raise RuntimeError("Original image changed unexpectedly")
    digest = sha(output)
    output.with_suffix(output.suffix + ".sha256").write_text(f"{digest}  {output.name}\n")
    if "SUDO_UID" in os.environ:
        for path in (output, output.with_suffix(output.suffix + ".sha256")):
            os.chown(path, int(os.environ["SUDO_UID"]), int(os.environ["SUDO_GID"]))
    print(f"Created: {output}\nSHA256: {digest}\nOriginal image unchanged: {original_sha}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Run with sudo; loop mounts are required")
    customize(options)

# 直接刷写的修复版镜像

可以在原版 `.img` 上离线集成这次修复，**无需重新编译或替换内核，也无需重新打包 `SYSTEM`**。厂商无线模块此前已经针对原版内核完成适配和编译，这里直接使用实机验证的二进制。

本镜像面向 README 中的 **S905X2 / G12A、2GB DDR3、RTL8822CS** 盒子，不是所有 S905X2 的通用镜像。写入 U 盘/SD 卡的方法与原版相同；它不是 Android 的 Amlogic USB Burning Tool 固件。

## 已生成的文件

```text
CoreELEC-Amlogic-no.aarch64-22.0-Piers_nightly_20261007-S905X2-2G-RTL8822CS-fixed.img
CoreELEC-Amlogic-no.aarch64-22.0-Piers_nightly_20261007-S905X2-2G-RTL8822CS-fixed.img.sha256
```

2026-10-08 生成的镜像 SHA256：

```text
148f0c39f3efe828f35597b30ec06e7a28df14d1a9b2e56853d3706ebf5ecacb
```

这是这一份产物的校验值。再次构建时，FAT 时间戳和目录分配可能不同，因此整镜像 SHA256 不保证相同；DTB、无线模块、内核和 `SYSTEM` 都有独立校验。

镜像位于生成它的本地工作目录，未将整镜像提交到 Git。仓库提供全部修复文件、构建脚本和说明。

## 镜像里改了什么

| 位置 | 内容 |
|---|---|
| 启动分区根目录 `dtb.img` | 最终板级 DTB：VPU 666.7MHz、framebuffer 与 U-Boot 地址对齐、SDIO SDR104 |
| 启动分区根目录 `mount-storage.sh` | 原版 initramfs 已支持的挂载钩子，完成正常挂载后调用一次性安装脚本 |
| 启动分区 `s905x2-fixes/storage.tar.gz` | 无线模块、加载脚本、服务、blacklist、回退脚本 |
| 启动分区 `s905x2-fixes/install-storage.sh` | 扩容完成后、systemd 启动前安装修复，并创建安装完成标记 |
| 启动分区 `s905x2-fixes/hdmi-only.dtb` | 撤销 SDR104 时的备用 DTB |
| 启动分区 `s905x2-fixes/*.md5`、`*.sha256`、`build-info.json` | 文件校验及构建来源 |

`kernel.img`、其内置 initramfs、`SYSTEM`、`cfgload`、`cfgload_env`、`aml_autoscript`、`recovery.img`、`config.ini` 均保持原版字节不变。**CEC 保持原版行为，不安装任何关闭 CEC 的配置，不修改 Kodi 的 CEC 设置。** 原版 boot 默认 1080p60；修复没有把 4K 锁定成低分辨率，进入 Kodi 后可以正常选择 2160p50/60。

没有导入原设备的 Wi-Fi 密码、NAS 凭据、Kodi 用户资料、影片或 SSH 密码。无线网络和 SMB 来源仍需按新装系统的常规流程配置一次；原设备上的 512MiB 缓存等 Kodi 设置也没有自动复制。

## 为什么不能直接预置 `/storage/.config`

原版镜像的数据分区只有 32MiB，包含 `.please_resize_me`。原版 `fs-resize` 的行为是：

1. 如果发现已有 `.config`、`.kodi` 或 `.cache`，拒绝扩容。
2. 否则把第二分区扩到介质末尾，并重新创建 ext4 文件系统。
3. 删除扩容标记，自动重启。

因此直接往数据分区复制配置会阻止扩容；把文件放在其他目录则会被重新格式化清掉。

本方案把安装包放在启动分区，保留原始数据分区：

```text
首次启动
  → 原版挂载 storage
  → 钩子检测 .please_resize_me，暂不安装
  → 原版扩容、创建文件系统、自动重启
第二次启动
  → 原版挂载已扩容的 storage
  → 校验安装包并安装无线文件
  → 创建服务启用链接和完成标记
  → 原版 systemd 启动，厂商驱动先于 ConnMan 加载
后续启动
  → 检测完成标记，直接跳过安装
```

首次安装创建 `/storage/.s905x2-no-fixes-v1-installed`。后续启动不会重写无线配置，因此手动回退原驱动后也不会被强制改回。可额外创建 `/storage/.s905x2-no-fixes-disabled` 阻止自动安装。

原版 initramfs 的精简 BusyBox 提供 `md5sum`，没有 `sha256sum`、`chmod` 和 `ln`。启动安装使用 MD5 检查意外损坏，并利用 tar/`cp -a` 保留脚本执行权限与服务链接；镜像及安装包另外提供 SHA256，供电脑或完整系统核对。MD5 不是防篡改签名。

## 刷写与第一次启动

1. **使用另一张 U 盘/SD 卡**，保留目前已验证可用的介质。
2. 核对 `.img.sha256`。Linux 在镜像所在目录执行 `sha256sum -c 文件名.img.sha256`；Windows 可用 `Get-FileHash -Algorithm SHA256 文件名.img`。
3. 用 balenaEtcher 或 Rufus 的 DD 镜像模式，把整个 `.img` 写入目标介质。刷写会清空所选介质；不用再手动选择和复制 DTB。
4. 盒子关机，断开其他 CoreELEC 启动介质，再插入新介质，沿用此前能成功进入 U 盘启动的方式。多个同名 `COREELEC` / `STORAGE` 分区同时连接可能造成挂载歧义。
5. 首次启动会执行原版扩容并自动重启，过程中不要断电。之后进入 Kodi，正常配置 Wi-Fi 和 SMB 来源。
6. 选择 4K50/60，并播放此前容易缓冲的原片，检查画面、缓存和 seek。

SSH/TTL 中可检查：

```sh
cat /storage/.s905x2-no-fixes-v1-installed
systemctl status wifi-vendor.service --no-pager
journalctl -b -u wifi-vendor.service
lsmod | grep 88x2cs
cat /sys/kernel/debug/mmc2/ios
cat /sys/class/amhdmitx/amhdmitx0/config
df -h /storage
```

预期 SDIO 为 200MHz / SDR104，加载 `88x2cs`，服务确认绑定 `rtl88x2cs`，storage 容量已扩到目标介质可用空间。MMC 编号可能因其他设备而变化。

## 重新生成镜像

Ubuntu/Debian 安装离线镜像工具；需要 root 权限挂载镜像，但脚本不会向物理磁盘刷写：

```sh
sudo apt install python3 util-linux udev dosfstools e2fsprogs
git clone https://github.com/Jioyzen/s905x2-coreelec-no-fixes.git
cd s905x2-coreelec-no-fixes
sha256sum -c SHA256SUMS
sudo python3 image/build-fixed-image.py \
  /path/to/CoreELEC-Amlogic-no.aarch64-22.0-Piers_nightly_20261007-Generic.img \
  /path/to/CoreELEC-Amlogic-no.aarch64-22.0-Piers_nightly_20261007-S905X2-2G-RTL8822CS-fixed.img
```

脚本要求 Python 3.11+，验证原版分区布局、内核与 `SYSTEM` 的 SHA256、空数据分区及扩容标记；输出路径必须尚不存在。它复制原镜像后，仅挂载和修改副本，最后执行 FAT/ext4 只读检查，确认原镜像未变，并生成 `.img.sha256`。只集成显示和无线修复。

如果工具中途失败，输出可能是未完成的副本。查明错误、确认相关 loop 挂载已释放后，删除该副本再重试；不要把失败产物用于刷写。

只有更换内核版本/ABI、换无线芯片或修改内核驱动实现时才需要重新编译相应模块，必要时构建内核。当前版本的构建说明见 [../source/BUILD.md](../source/BUILD.md)。

## 回退与验证范围

本镜像预置的无线回退脚本可以直接执行：

```sh
sh /storage/.config/restore-native-wifi.sh
```

若要只保留 HDMI 修复并撤销 SDR104，先回退无线驱动，再将 `/flash/s905x2-fixes/hdmi-only.dtb` 复制成 `/flash/dtb.img`，同步并重启。完整回退可重新刷写原版镜像，或继续使用此前保留的可用介质。详细手动回退见 [../README.md](../README.md)。

目前完成的是：镜像文件系统、产物校验、DTB 参数、扩容跳过、自动安装、服务链接、重复启动幂等及损坏包拒绝的离线验证；安装脚本还使用原镜像 ARM64 BusyBox 经 QEMU 执行验证。**新封装的整镜像尚未在另一张介质上进行首次实机启动。** DTB 和无线模块本身已经在该盒子的原版内核上实机验证。离线测试不能替代首次启动的扩容、实际驱动绑定及电视画面验证。

# S905X2 CoreELEC NO 修复文件

针对一台 **S905X2 / G12A、u212 接近板型、2GB DDR3、RTL8822CS SDIO Wi-Fi** 盒子，在原始 CoreELEC NO 系统上修复：

1. 4K 高刷新率 HDMI 花屏，恢复稳定的 2160p50/59.94/60 输出。
2. U-Boot 图标正常，但进入 CoreELEC 图标前短暂花屏的显示交接问题。
3. Wi-Fi 下载吞吐不足，导致 SMB 高码率 4K 播放缓冲、seek 后缓存迟迟无法填满。

实际只需要替换启动 DTB，并在可写的 `/storage` 添加无线驱动及加载配置。**没有替换 `kernel.img` 或 `SYSTEM`，没有刷写内部 eMMC，也没有拿 NG/kernel 4.9 的 DTB 给 NO/kernel 5.15 使用。**

修复在 2026-10-07 实机完成，随后验证重启和手动播放。用户确认快进快退流畅、缓冲很快、seek 后 cache 能迅速填满。

## 适用硬件与软件

| 项目 | 已验证环境 |
|---|---|
| SoC / 板型 | Amlogic S905X2，G12A，u212 接近板型 |
| 内存 | 2GB DDR3，U-Boot 训练频率 648MHz |
| 无线 | RTL8822CS，SDIO ID `024C:C822`，5GHz / 80MHz |
| 系统 | `CoreELEC 22.0-Piers_nightly_20261007`，`Amlogic-no.aarch64` |
| 内核 | `5.15.196` |
| CoreELEC commit | `b59c88dfb718465e04d7999fc31a31e57030552a` |
| linux-amlogic commit | `968a93c28223f72ff94e706eabb0277292bac878` |
| common_drivers commit | `d9ec1b3b91822e03fdbeb09305aa0f63fbbb4c17` |
| HDMI 链路 | 经 DENON 功放连接电视，EDID 宣告最大 TMDS 600MHz |

**本仓库不是所有 S905X2 盒子的通用固件。** 顶部 framebuffer 地址与 2GB 内存及该盒子的 U-Boot 行为有关；无线模块必须匹配内核 ABI，不能仅凭版本号相同认定兼容。其他内存容量、其他无线芯片或后续内核应重新核对并构建。

原始 `kernel.img` SHA256：`e340675c1c70b3e215c6858bce42c1262a3a11d493d7cfbe4824f7460bd1b7a0`。

原始 `SYSTEM` SHA256：`e02890e8c360d4cfee77962b17f520716229892b0496211b8ed0742b21865b1b`。

## 修复效果

测速时使用同一盒子、同一 AP、同一 iperf3 服务端和同一 NAS 影片；各轮大流量测试单独运行。

| 配置 | TCP 下载 | SMB2.1 原片读取 | SMB3 原片读取 | WebDAV 读取 |
|---|---:|---:|---:|---:|
| 原 NO：rtw88，SDR50 / 100MHz | 79.33Mbps | 11.52MB/s | 10.67MB/s | — |
| 只恢复 SDR104 / 200MHz | 97.05Mbps | 13.61MB/s | — | 13.42MB/s |
| SDR104 + 适配厂商驱动 | **578.76Mbps** | **71.75MB/s** | **74.37MB/s** | **73.31MB/s** |
| 完整修复后重启复测 | **580.27Mbps** | — | — | — |

`Mbps` 为兆比特/秒；`MB/s` 使用十进制兆字节/秒。iperf3 3.18 测 TCP 单连接反向下载，排除预热阶段；SMB/WebDAV 读取文件并丢弃数据。iperf 与 NAS 是不同局域网主机，速度不应视为完全等价。

测试影片《双子杀手》约 **81.39GB / 117 分钟**，全文件平均约 **92.71Mbps**。原来的无线下载连平均消耗都难以满足，等待很久也难以积累缓存。修复后网络读取具备明显余量。

HDMI 模式验证见 [validation/HDMI-MODES.md](validation/HDMI-MODES.md)。无线测量摘要见 [validation/measurements.json](validation/measurements.json)。没有上传包含设备凭据的原始日志或测试影片。

## 文件与安装路径

| 仓库内文件 | 盒子目标路径 | 操作 / 功能 |
|---|---|---|
| [`boot/dtb.img`](boot/dtb.img) | `/flash/dtb.img` | 替换；包含 VPU 666.7MHz、启动 framebuffer 对齐、SDIO SDR104 三项修复 |
| [`storage/.config/wifi-drivers/88x2cs-5.15.196.ko`](storage/.config/wifi-drivers/88x2cs-5.15.196.ko) | `/storage/.config/wifi-drivers/88x2cs-5.15.196.ko` | 新增；适配当前内核的 Realtek 厂商无线模块 |
| [`storage/.config/wifi-vendor-load.sh`](storage/.config/wifi-vendor-load.sh) | `/storage/.config/wifi-vendor-load.sh` | 新增；正常加载模块，失败时回退原驱动 |
| [`storage/.config/system.d/wifi-vendor.service`](storage/.config/system.d/wifi-vendor.service) | `/storage/.config/system.d/wifi-vendor.service` | 新增；在 ConnMan 前执行驱动加载 |
| [`storage/.config/modprobe.d/90-s905x2-rtl8822cs.conf`](storage/.config/modprobe.d/90-s905x2-rtl8822cs.conf) | `/storage/.config/modprobe.d/90-s905x2-rtl8822cs.conf` | 新增；阻止原 `rtw_8822cs` 自动抢占芯片 |

`/flash/dtb.img` 就是 U 盘/SD 卡 **启动分区根目录的 `dtb.img`**。若在电脑上操作启动分区，可直接备份原文件后复制并重命名；驱动与服务仍需放入 `/storage`。

另外提供：

- [`boot/hdmi-only.dtb`](boot/hdmi-only.dtb)：只包含 HDMI 两项修复，可用于撤销 SDR104 而保留显示修复。
- [`scripts/restore-native-wifi.sh`](scripts/restore-native-wifi.sh)：回退到系统自带 rtw88。
- [`source/board-final-source.dts`](source/board-final-source.dts)：基于 NO DTS 的板级修改配方。
- [`source/patches/`](source/patches/)：VPU 修复补丁和厂商驱动兼容补丁。
- [`source/rtl88x2cs-vendor.tar.gz`](source/rtl88x2cs-vendor.tar.gz)：构建模块所用的厂商驱动原始源码快照。
- [`source/running-kernel.config`](source/running-kernel.config)：从实机提取的完整内核配置。
- [`optional/cec/`](optional/cec/)：按本次用户需求关闭 CEC 的可选配置。

## 使用方法

### 1. 下载并传到盒子

在电脑上克隆仓库，或从 GitHub 下载 ZIP 并解压。将整个目录放到盒子 `/storage/s905x2-coreelec-no-fixes`。例如电脑终端：

```sh
git clone https://github.com/Jioyzen/s905x2-coreelec-no-fixes.git
scp -r s905x2-coreelec-no-fixes root@BOX_IP:/storage/
```

下面的命令均在 **盒子的 SSH root 终端**执行。先停止播放影片，避免无线切换时打断读取。

### 2. 核对文件并备份

```sh
cd /storage/s905x2-coreelec-no-fixes
sha256sum -c SHA256SUMS
uname -r
```

预编译模块对应 `5.15.196`。确认前文硬件和系统版本适用后，建立独立备份目录：

```sh
BACKUP_DIR=/storage/s905x2-no-fixes-backup-$(date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP_DIR"
cp /flash/dtb.img "$BACKUP_DIR/dtb.img"
cp /flash/config.ini "$BACKUP_DIR/config.ini"
tar -czf "$BACKUP_DIR/storage-config.tar.gz" -C /storage .config
echo "备份目录：$BACKUP_DIR"
```

备份中的配置可能包含个人设置，保留在自己的设备，不要上传公开仓库。记下备份目录以便回退。

### 3. 安装最终 DTB 和无线配置

```sh
cd /storage/s905x2-coreelec-no-fixes

mount -o remount,rw /flash
cp boot/dtb.img /flash/dtb.img
sync
mount -o remount,ro /flash

mkdir -p /storage/.config/wifi-drivers
mkdir -p /storage/.config/system.d
mkdir -p /storage/.config/modprobe.d

cp storage/.config/wifi-drivers/88x2cs-5.15.196.ko /storage/.config/wifi-drivers/
cp storage/.config/wifi-vendor-load.sh /storage/.config/
cp storage/.config/system.d/wifi-vendor.service /storage/.config/system.d/
cp storage/.config/modprobe.d/90-s905x2-rtl8822cs.conf /storage/.config/modprobe.d/

chmod 755 /storage/.config/wifi-vendor-load.sh
systemctl daemon-reload
systemctl enable wifi-vendor.service
sync
reboot
```

推荐完整复制四个无线文件后重启；不要只复制 blacklist 配置。原系统模块保留在只读系统中，新增模块从 `/storage` 加载。

### 4. 重启后确认

```sh
systemctl status wifi-vendor.service --no-pager
lsmod | grep 88x2cs
readlink /sys/bus/sdio/devices/mmc2:0001:1/driver
cat /sys/kernel/debug/mmc2/ios
cat /sys/kernel/debug/mmc2/err_stats
cat /sys/class/amhdmitx/amhdmitx0/config
```

这台盒子预期看到：

- 服务日志：`RTL8822CS vendor driver active: NAPI/GRO enabled, power saving off`。
- SDIO 绑定 `rtl88x2cs`，模块名 `88x2cs`。
- `clock: 200000000 Hz`、4-bit bus、`sd uhs SDR104`。
- CRC、timeout、ADMA 等控制器错误计数保持 0。
- 选择 4K60 后，HDMI 回读为实际要求的模式。本次长期使用的是 YUV422 / 10-bit。

不同设备的 MMC 编号可能不同；可通过 `/sys/bus/sdio/devices/*/uevent` 查找 `SDIO_ID=024C:C822`。若服务提示 fallback，检查 `journalctl -b -u wifi-vendor.service` 和 `dmesg`，不要强制忽略 ABI 校验。

最后手动播放 NAS 原片，并跳到以前容易缓冲的片段，观察缓存、seek 响应、画面和声音。

### 5. Kodi 设置

实测时保留了以下设置；它们不是本次速度提升的主要原因，无需覆盖整个 `guisettings.xml`：

| 设置 | 实测值 |
|---|---|
| SMB 最低 / 最高协议 | SMB2.1 / SMB2.1 |
| SMB chunk | 1024KiB |
| 缓存对象 | 所有网络文件系统，`filecache.buffermode=4` |
| 缓存内存 | 512MiB |
| 读取倍率 | 10x |
| 缓存 chunk | 1MiB |

SMB3 修复后同样能达到约 74MB/s，因此不用强制降级协议来获得本次提升。Kodi 22 应在对应设置页面调整缓存；不要加入旧版 `advancedsettings.xml` 的过时缓存节点。512MiB 是这台 2GB 设备上验证的设置，其他设备应结合可用内存选择。

## 故障点与修复原理

### A. 4K 高刷新率花屏：VPU 频率档位索引错位

旧 NG/kernel 4.9 正常，包括 4K60；NO/kernel 5.15 能启动，1080p 和 4K24/25 正常，更高刷新率花屏。

初始现象容易被理解为 HDMI 高 TMDS/PHY 故障，但进一步测试发现：**4K60 YCbCr 4:2:0 / 8bit 的 TMDS 只有 297MHz，仍然花屏；同模式 HDMI 编码器硬件 BIST 彩条却正常。保持 HDMI 模式不变，仅提高 VPU 时钟，Kodi 画面立即恢复。** 因此该盒子的主要故障发生在 VPU/OSD 显示链路。

根源位于 common_drivers 的频率表与 DTS 的索引不一致：[commit d3221487060c1023d50d5d533e1147db24b5c46b](https://github.com/CoreELEC/common_drivers/commit/d3221487060c1023d50d5d533e1147db24b5c46b) 在表头增加低频档，并更新 G12A 驱动默认档位，但 `mesong12a.dtsi` 仍用 `/vpu/clk_level=7` 覆盖默认值。

| 档位 | NG 4.9 | 本次 NO 5.15 |
|---|---:|---:|
| `clk_level=7` | 666.7MHz | **500MHz** |
| `clk_level=8` | 不直接沿用 | **666.7MHz** |

最终 DTB 将 `/vpu/clk_level` 改为 `<8>`。这恢复了原来所需的 666.7MHz，而非盲目提高 HDMI PHY 电压或降低分辨率。仓库提供最小 DTS 补丁；当前安装直接使用修改后的 DTB，不需要换内核。

### B. 启动短暂花屏：framebuffer 交接地址不同

VPU 修复后，Kodi 的全部已测刷新率正常，但 CoreELEC 图标出现前仍有约一两秒花屏。USB TTL 和实际内存检查确认：

- 该盒子 U-Boot 的 OSD canvas/framebuffer 位于 **`0x7f800000`**。
- NO 通用 2GB DTB 的 `linux,meson-fb` 却指向 **`0x3d800000`**。
- `meson_logo.c:am_meson_logo_init()` 通过 DTB 的 memory-region 建立图标 framebuffer，读取了不同的内存内容。

最终以该盒子实际地址修改：

```dts
&{/reserved-memory/linux,meson-fb} {
    reg = <0x0 0x7f800000 0x0 0x800000>;
};
```

即保留 2GB RAM 顶部 8MiB，与 U-Boot 对齐。重复启动后用户确认正常。没有使用 `logo_skip=1`，没有修改 `cfgload`，也没有用强制 1080p 隐藏问题。

### C. Wi-Fi 慢：SDIO 模式缺失与 rtw88 驱动路径

板载 RTL8822CS 支持 SDR104，但 NO 的 `coreelec_g12a_common.dtsi` 主动删除 `sd-uhs-sdr104`。恢复此布尔属性后，总线由 SDR50 / 100MHz 升为 SDR104 / 200MHz，下载 79→97Mbps，SMB 11.5→13.6MB/s；控制器错误为 0。

这个改善仍不足以提供高码率影片的峰值余量。进一步确认：

- 无线信号约 -18dBm，5GHz / 80MHz；不是弱信号位置。
- Wi-Fi 省电已关闭，CPU 没有整体满载。
- SDR104 下单向 UDP 接收约 295Mbps，但 TCP 下载约 97Mbps。
- 一秒 MMC trace 中约 3 万次 CMD53，约 2.2 万次只读写 4 字节寄存器，显示小事务开销明显。
- 调大接收聚合超时、固定 IRQ CPU、关闭波束成形没有明显改善，均撤回。
- 临时绕过 SD 卡共享控制器只提升到约 106Mbps，已撤回，保留 SD 卡能力。
- SMB2.1、SMB3、WebDAV 都慢，因此不是单个 SMB 协议版本导致。

原 NO 使用开源 **rtw88**；本仓库适配 [jethome-ru/rtl88x2cs](https://github.com/jethome-ru/rtl88x2cs) 的厂商驱动后，在相同 SDR104 状态下 TCP 下载 **97→579Mbps**，SMB 读取约 **72–74MB/s**，重启复测 580Mbps。

厂商驱动包含不同的 NAPI/GRO、TX/RX 聚合、固件和 PHY 处理。本次 A/B 实测把主要瓶颈定位到 **rtw88 驱动路径**；尚未把全部提升进一步分解到某一个函数或某一行代码，不应宣称只有 NAPI 或某个 ACK 参数是唯一根因。

### D. 为何厂商模块需要适配 NO 5.15

模块源代码版本为 `v5.9.0.7_37128.20200812_COEX20200103-1717`，源码 commit：[`f4263fc6ecd11465bf60ce142aa76e2e85e2cbf3`](https://github.com/jethome-ru/rtl88x2cs/commit/f4263fc6ecd11465bf60ce142aa76e2e85e2cbf3)。

CoreELEC 5.15 内核通过 [af6fc28081cdf1d93f81edb80afed5b6b1ffbd21](https://github.com/CoreELEC/linux-amlogic/commit/af6fc28081cdf1d93f81edb80afed5b6b1ffbd21) 回移了新 cfg80211/MLO 接口。驱动只按 `LINUX_VERSION_CODE` 选旧接口会编译失败，因此提供两个补丁：

1. `0001-rtl88x2cs-coreelec-515-cfg80211.patch`：为经核对的新 channel-switch、key、stop_ap、get_channel 回调参数及 roam/link 结构选择正确分支。通过 `-DRTW_CE_CFG80211_BACKPORT` 启用。
2. `0002-rtl88x2cs-coreelec-vfs-namespace.patch`：为厂商现有文件 I/O 包装代码导入内核要求的 VFS namespace，解决 modpost 错误。

构建使用实机配置和对应 NO 源码，保留 Clang **Shadow Call Stack 与 x18 保留**。原无线模块相关的 **487 个依赖符号 CRC 对照全部一致**；最终模块具有 210 个版本化依赖，实机使用正常 `insmod` 校验加载成功，没有修改 vermagic，也没有使用 force-load。

构建方法见 [source/BUILD.md](source/BUILD.md)。

## 开机加载与升级行为

`wifi-vendor.service` 在 ConnMan 前运行；脚本核对 SDIO ID 和内核版本，再用正常 ABI 校验加载模块，并验证驱动是否绑定。NAPI/GRO 开启，`rtw_power_mgnt=0`、`rtw_ips_mode=0`。

模块缺失、版本不符或加载被拒绝时，脚本显式加载系统自带 `rtw_8822cs`。Blacklist 只阻止自动加载，正常显式 `modprobe` 仍可用于恢复。**回退路径用于模块加载/绑定阶段；不是运行时故障监控器。**

CoreELEC 更新可能覆盖 DTB；内核 ABI 变化也可能使模块无法加载。升级后检查实际驱动和吞吐，必要时重新核对 DTS、重新编译模块。不要在新内核上强制加载旧模块。

## 回退方法

### 只撤销无线驱动

```sh
sh /storage/s905x2-coreelec-no-fixes/scripts/restore-native-wifi.sh
```

这会禁用服务、移除本仓库 blacklist、卸载厂商模块并加载原 rtw88。Wi-Fi 会重连；DTB 和 HDMI 修复保留。也可在 TTL 终端执行。

### 保留 HDMI 修复，但撤销 SDR104

先回退无线驱动，再使用仓库自带的 HDMI-only DTB：

```sh
cd /storage/s905x2-coreelec-no-fixes
mount -o remount,rw /flash
cp boot/hdmi-only.dtb /flash/dtb.img
sync
mount -o remount,ro /flash
reboot
```

### 恢复安装前 DTB

将下面备份目录替换为自己第 2 步记录的真实路径：

```sh
BACKUP_DIR=/storage/s905x2-no-fixes-backup-YYYYMMDD-HHMMSS
mount -o remount,rw /flash
cp "$BACKUP_DIR/dtb.img" /flash/dtb.img
sync
mount -o remount,ro /flash
reboot
```

如果设备无法启动，可在电脑上挂载 U 盘/SD 卡启动分区，恢复备份的 `dtb.img`；无线服务配置可通过 TTL 或可读写 storage 分区撤销。

## 可选：关闭 CEC

本次盒子经过功放，用户要求避免电视/功放因 CEC 联动关机，因此关闭了 CEC。这是独立设置，不是 HDMI 花屏的根因修复。

1. 将 `/flash/config.ini` 中的 `cec_func_config` 设置为 `'00'`（编辑前 remount 为 rw，编辑后同步并恢复 ro）。不要用其他设备的完整 config.ini 覆盖自己的设置。
2. Kodi「系统 → 输入 → 外设 → CEC Adapter」中禁用 CEC，关闭唤醒/关机联动。
3. 安装启动前关闭内核 CEC 的 drop-in：

```sh
cd /storage/s905x2-coreelec-no-fixes
mkdir -p /storage/.config/system.d/kodi.service.d
cp optional/cec/90-hdmi-diagnosis.conf /storage/.config/system.d/kodi.service.d/
systemctl daemon-reload
```

下次启动后 `cat /sys/class/aocec/fun_cfg` 应为 `0x0`。如需恢复 CEC，删除该 drop-in，并恢复自己的 config.ini 与 Kodi CEC 设置。

## 验证边界与已知情况

- 已测 2160p23.976/24/25/30/50/59.94/60，以及多种色彩格式；用户确认正常。
- 4K60 RGB/4:4:4 10bit 需要 742.5MHz，超出 HDMI 2.0 最大 600MHz，驱动正确拒绝；不能把这种拒绝当成此次修复失败。
- 手动高码率 HEVC 4K60 + TrueHD Atmos 播放、seek、重启后带宽已验证。未做整部影片无人值守长时间认证。
- 被动监测中起播/seek 后的两次 decoder error/drop 计数在连续观察段没有增加；不宣称全程零错误。
- 一次自动 JSONRPC 打开影片曾导致 Kodi 黑屏和控制无响应，重启 Kodi 后手动播放正常；该自动起播问题未单独修复。本仓库不包含自动播放脚本。
- 原日志中的 Bluetooth reset 和 `not support hdmitx_vout_set_vframe_rate_hint` 提示在修复前也存在；蓝牙服务与适配器保持启用。没有为消除提示随意关闭其他功能。
- 原系统百兆有线口不是本次测试路径；不宣称百兆网口能满足所有高码率峰值。

## 校验与源码授权

最终 DTB SHA256：`2e725746f1a78732180a3d8f79cab4de0a3ef5814c3f62747b966e23eff99061`。

无线模块 SHA256：`598b4e4c1774710901ce2a6240e579af1ae31071f9c4ef56c619455c04fec84e`。

完整部署文件和源码快照校验值见 [SHA256SUMS](SHA256SUMS)。

本仓库新增脚本、文档和补丁采用 GPL-2.0；上游源码保留原有作者、版权及各文件许可证。厂商模块对应源码快照、修改补丁、构建配置及说明一并提供；CoreELEC、linux-amlogic、common_drivers 和 Realtek 作者权利不变。详见 [LICENSE](LICENSE) 与 [source/BUILD.md](source/BUILD.md)。

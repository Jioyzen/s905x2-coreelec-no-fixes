# 修复版镜像离线及首次实机验证（2026-10-08）

产物：`CoreELEC-Amlogic-no.aarch64-22.0-Piers_nightly_20261007-S905X2-2G-RTL8822CS-fixed.img`

SHA256：`148f0c39f3efe828f35597b30ec06e7a28df14d1a9b2e56853d3706ebf5ecacb`

原版镜像 SHA256：`9cf7f9058a20dccdf0fe139ae5dab5dab7b8907e790be68c23d9159283216c54`

| 验证项 | 结果 |
|---|---|
| 原始镜像构建前后整文件校验 | 未变 |
| MBR 和首分区之前的启动区域 | 与原版逐字节一致 |
| 完整第二分区 | 与原版逐字节一致，保留 `.please_resize_me`，无 `.config` |
| `kernel.img`、`SYSTEM` 及其 MD5 文件 | 与原版逐字节一致 |
| `cfgload`、`cfgload_env`、`aml_autoscript`、`recovery.img` | 与原版逐字节一致 |
| `config.ini` | 与原版逐字节一致 |
| CEC 配置 | 无新增 CEC 覆盖文件，无 Kodi 用户设置 |
| DTB VPU 档位 | `clk_level=8` |
| DTB framebuffer | `<0 0x7f800000 0 0x800000>` |
| DTB SDIO | 有 `sd-uhs-sdr104` |
| FAT 只读检查 | `fsck.fat -n` 通过 |
| ext4 只读检查 | `e2fsck -f -n` 五阶段通过 |
| 扩容标记存在时运行安装脚本 | 不创建 `.config` |
| 扩容标记移除后运行安装脚本 | 模块校验正确，脚本可执行，服务启用链接正确 |
| 第二次运行安装脚本 | 保留手动修改过的加载脚本 |
| 显式禁用标记 | 跳过安装 |
| 安装包人为损坏 | 在写入配置/blacklist 前拒绝 |

最后五项以原版 initramfs 中的 **ARM64 BusyBox v1.38.0** 经 QEMU 执行。测试使用隔离临时目录，BusyBox 命令包装器处理 QEMU 下的子进程调用；没有操作盒子的实际 `/storage`。这是脚本与工具兼容性验证，不是整机仿真启动。

## 新 U 盘首次实机检查

用户刷写本镜像并完成初始化后，通过 SSH 检查：

| 验证项 | 结果 |
|---|---|
| 系统 / 内核 | 原版 nightly_20261007 / 5.15.196 |
| DTB、内核、厂商模块 SHA256 | 与仓库中的实机验证产物一致 |
| 数据分区 | `/dev/sda2`，约 28.2GiB，扩容完成 |
| 一次性安装标记 | 存在，值 `s905x2-no-fixes-v1` |
| 无线服务 | enabled / active (exited)，启动返回 SUCCESS |
| 实际加载的模块 / 绑定驱动 | `88x2cs` / `rtl88x2cs` |
| SDIO | 200MHz / 4-bit / SDR104 |
| 驱动参数 | NAPI/GRO 开启，power_mgnt=0、ips_mode=0 |
| SDIO 控制器错误 | 全部计数为 0，包括吞吐测试后 |
| HDMI 当前状态回读 | 3840×2160p60、YUV422、10-bit、HDR10 |

首次反馈 SMB 高码率播放缓存不足时，驱动已正确加载，但无线连接为 **2.4GHz / 20MHz**。在同一盒子、同一 AP、同一局域网 iperf3 服务端，仅切换至其 5GHz 网络后复测：

| 无线连接 | PHY TX 速率 | TCP 单连接反向下载 |
|---|---:|---:|
| 2.4GHz / 20MHz | 144.4Mbps | **96.33Mbps** |
| 5GHz / 80MHz | 867Mbps | **588.52Mbps** |

iperf3 为 3.18，2.4GHz 测试计时 15 秒、5GHz 20 秒，均 `-R -O 3` 排除预热。PHY 速率与 TCP 有效吞吐是不同指标。该影片全文件平均约 92.71Mbps，2.4GHz 连接几乎没有峰值和重传余量。

5GHz 网络配置已在实机保存，Favorite/AutoConnect 均为 true。本轮没有替换驱动、修改 DTB、改变 CEC、控制 Kodi 起播或重启盒子。没有上传网络密码或包含设备信息的原始日志。镜像首次安装链路及无线吞吐已获得实机验证；本轮不宣称整部影片无人值守播放或 CEC 联动认证。

切换后用户手动播放确认：“正常了，没问题”。

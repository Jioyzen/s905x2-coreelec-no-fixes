# 修复版镜像离线验证（2026-10-08）

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

新镜像尚未完成新介质首次实机启动验证。扩容实际执行、无线绑定、CEC 联动及电视画面仍需在盒子上核对。修复 DTB、厂商模块的既有实机验证见其他 validation 文件与主 README。

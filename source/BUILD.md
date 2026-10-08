# 源码来源与构建记录

预编译产物针对 README 中的准确版本。这里记录对应源码、修改与实际构建参数；构建目录里的内核用于生成兼容头文件和符号 CRC，**不需要将其内核镜像刷入盒子**。

## 1. 对应源码

| 项目 | 来源与版本 |
|---|---|
| CoreELEC | <https://github.com/CoreELEC/CoreELEC/tree/b59c88dfb718465e04d7999fc31a31e57030552a> |
| 内核 | <https://github.com/CoreELEC/linux-amlogic/tree/968a93c28223f72ff94e706eabb0277292bac878> |
| common_drivers | <https://github.com/CoreELEC/common_drivers/tree/d9ec1b3b91822e03fdbeb09305aa0f63fbbb4c17> |
| BL30 GPIO 数据 | <https://github.com/CoreELEC/bl30/tree/e08015a6b17fda21260c7a9c8bfd3c98ee2a61c1> |
| 厂商 Wi-Fi 驱动 | <https://github.com/jethome-ru/rtl88x2cs/tree/f4263fc6ecd11465bf60ce142aa76e2e85e2cbf3> |

`rtl88x2cs-vendor.tar.gz` 是实际使用的 `tune_for_jethub` 源码快照，SHA256：

```text
0968e6dd8f7807e97ff667e33b2f8c8828b041e6b5ddaa97bd4f038ad45a817d
```

源码声明版本 `v5.9.0.7_37128.20200812_COEX20200103-1717`，默认 RTL8822C + SDIO，NAPI/GRO 开启，省电关闭，内嵌厂商固件，无需单独部署新的 firmware 文件。

版权与许可证保留于各上游文件；厂商源码使用 GPLv2，见其源文件头及仓库根目录 LICENSE。

## 2. 内核构建环境

本次使用 Ubuntu Clang **18.1.8**、LLVM 工具和 `aarch64-linux-gnu-` 交叉工具链。实机内核由 Android Clang 17.0.2 构建；使用 Clang 18 重建后，相关原模块的 487 个依赖符号 CRC 对照一致。换编译器或配置后，必须重新验证，不能将本次结论自动套用。

实机配置提取方式（在盒子上）：

```sh
modprobe configs
zcat /proc/config.gz > /storage/running-kernel.config
```

仓库保存了这份配置。`CONFIG_SHADOW_CALL_STACK=y` 需要保留 Clang 编译；不能让 GCC 配置更新悄悄移除它。实际模块编译命令包含 `-ffixed-x18`、`-fsanitize=shadow-call-stack`。

构建所需工具包括 make、Clang/LLVM/lld、aarch64 GNU 交叉工具链、flex、bison、bc、OpenSSL 开发头、libelf 开发头、Python 3、dtc。工具包名称随发行版而异。

## 3. 重建内核符号信息

以下在 Linux 构建机执行，从仓库根目录开始。下载三个固定版本源码归档，不要换成对应分支的最新源码。

```sh
REPO_DIR=$(pwd)
mkdir -p build
cd build

curl -fL https://codeload.github.com/CoreELEC/linux-amlogic/tar.gz/968a93c28223f72ff94e706eabb0277292bac878 -o kernel.tar.gz
curl -fL https://codeload.github.com/CoreELEC/common_drivers/tar.gz/d9ec1b3b91822e03fdbeb09305aa0f63fbbb4c17 -o common.tar.gz
curl -fL https://codeload.github.com/CoreELEC/bl30/tar.gz/e08015a6b17fda21260c7a9c8bfd3c98ee2a61c1 -o bl30.tar.gz

tar -xzf kernel.tar.gz
tar -xzf common.tar.gz
tar -xzf bl30.tar.gz

KERNEL_DIR="$REPO_DIR/build/linux-amlogic-968a93c28223f72ff94e706eabb0277292bac878"
COMMON_DIR="$REPO_DIR/build/common_drivers-d9ec1b3b91822e03fdbeb09305aa0f63fbbb4c17"
BL30_DIR="$REPO_DIR/build/bl30-e08015a6b17fda21260c7a9c8bfd3c98ee2a61c1"

mkdir -p "$KERNEL_DIR/common_drivers"
cp -a "$COMMON_DIR/." "$KERNEL_DIR/common_drivers/"
cp "$REPO_DIR/source/running-kernel.config" "$KERNEL_DIR/.config"
touch "$KERNEL_DIR/.scmversion"

python3 "$REPO_DIR/source/generate_gpio_data.py" "$KERNEL_DIR" "$BL30_DIR"

make -C "$KERNEL_DIR" ARCH=arm64 LLVM=1 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
make -C "$KERNEL_DIR" ARCH=arm64 LLVM=1 CROSS_COMPILE=aarch64-linux-gnu- -j"$(nproc)" vmlinux modules
```

CoreELEC 的打包流程会生成 `common_drivers/drivers/bootloader/gpio_data.h`；直接构建其内核源码时需补上这个文件。`generate_gpio_data.py` 按固定 BL30 源码的 GPIO 数值生成等价表。

只有 `modules_prepare` 不会生成完整 `Module.symvers`；本次因此完成 `vmlinux modules` 构建。若拥有同版官方构建输出中的 `.config` 和 `Module.symvers`，可复用准确构建产物，但仍应检查 ABI。

## 4. 编译厂商驱动

继续上面的构建机终端：

```sh
cd "$REPO_DIR/build"
tar -xzf "$REPO_DIR/source/rtl88x2cs-vendor.tar.gz"
DRIVER_DIR="$REPO_DIR/build/rtl88x2cs-tune_for_jethub"

patch -d "$DRIVER_DIR" -p1 < "$REPO_DIR/source/patches/0001-rtl88x2cs-coreelec-515-cfg80211.patch"
patch -d "$DRIVER_DIR" -p1 < "$REPO_DIR/source/patches/0002-rtl88x2cs-coreelec-vfs-namespace.patch"

make -C "$DRIVER_DIR" \
  ARCH=arm64 LLVM=1 CROSS_COMPILE=aarch64-linux-gnu- \
  KSRC="$KERNEL_DIR" USER_ccflags-y=-DRTW_CE_CFG80211_BACKPORT \
  -j"$(nproc)"

cp "$DRIVER_DIR/88x2cs.ko" "$REPO_DIR/build/88x2cs-5.15.196.ko"
llvm-strip --strip-debug "$REPO_DIR/build/88x2cs-5.15.196.ko"
modinfo "$REPO_DIR/build/88x2cs-5.15.196.ko"
modprobe --dump-modversions "$REPO_DIR/build/88x2cs-5.15.196.ko"
```

最终 `modpost` 必须成功，依赖包含 `cfg80211`，版本化符号不能为空。不要部署缺少 `Module.symvers` 时虽产出 `.ko`、却充满 undefined symbol 警告的中间文件。

正常加载与绑定是最终兼容性验证。禁止编辑 vermagic 或使用强制忽略符号版本的加载参数。更换编译器后构建的字节校验值未必和本仓库相同，ABI 对照和实机测试仍然必要。

## 5. DTB 重建配方

`board-final-source.dts` 以 NO 的 `g12a_s905x2_2g.dts` 为基础，只增加/覆盖：

- model 名称；
- `/vpu/clk_level=<8>`；
- `/reserved-memory/linux,meson-fb/reg=<0 0x7f800000 0 0x800000>`；
- `/sd2@ffe05000/sd-uhs-sdr104`。

```sh
cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
  -I "$KERNEL_DIR/common_drivers/arch/arm64/boot/dts/amlogic" \
  -I "$KERNEL_DIR/common_drivers/include" \
  -I "$KERNEL_DIR/include" \
  "$REPO_DIR/source/board-final-source.dts" > "$REPO_DIR/build/board-final.pp.dts"

dtc -I dts -O dtb \
  -o "$REPO_DIR/build/board-final.dtb" "$REPO_DIR/build/board-final.pp.dts"
```

仓库 `boot/dtb.img` 是**官方 DTB 上最小修改后、已经实机验证的二进制**。源码重建验证过上述属性，但节点/属性顺序、padding 等会导致字节 SHA256 不同；源码重建产物不能因校验值不同就判定错误，也不能不经验证就宣称与部署产物完全等价。

`0001-g12a-restore-vpu-666mhz.patch` 是给 common_drivers 原始 `mesong12a.dtsi` 使用的全局 VPU 修复替代方案。使用 `board-final-source.dts` 已覆盖该属性，不必重复应用此补丁。启动 framebuffer 地址与 SDR104 的板级修改仍由该配方提供。

## 6. 校验信息

- `validation/kernel-abi-validation.txt` 保存本次 487 个原模块依赖 CRC 对照结果。
- `validation/vendor-module-versions.txt` 保存最终模块 210 个版本化依赖。
- 预编译模块 SHA256 位于根目录 `SHA256SUMS`。
- 发布前使用普通内核加载校验实测，重启后 iperf3 下载 580.27Mbps。

内核镜像、其他系统模块、旧 NG 驱动二进制均无需替换。该目录中的构建命令用于复现与继续维护，不会自动刷写设备。

# 编译与定制

## 版本与构建环境

`sources.lock.json` 固定 OpenWrt 提交、所用 feeds 提交和 NEC GPL 压缩包 SHA-256。原机用户态标识为 `r37744-7d0bf92bee`，内核为 Linux 6.18.55 加 OpenWrt 补丁；公开构建用固定的源码树重建整个系统，不把旧用户态和不匹配的内核模块拼在一起。它不会产生与原机磁盘逐字节相同的镜像。

推荐 Ubuntu 24.04，至少 4 核 / 8GB RAM / 40GB 空闲磁盘；首次构建可能需要更多下载空间。使用普通用户，文件系统必须区分大小写。标准依赖参考 [OpenWrt build system](https://openwrt.org/docs/guide-developer/toolchain/install-buildsystem)。

```sh
sudo apt update
sudo apt install build-essential clang flex bison g++ gawk gcc-multilib \
  gettext git libncurses-dev libssl-dev python3 python3-setuptools \
  python3-pyelftools rsync swig unzip zlib1g-dev file wget curl \
  subversion zstd device-tree-compiler u-boot-tools mtd-utils \
  gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu
```

ARM64 Linux 主机不必安装 `gcc-multilib`。macOS 默认 APFS 不适合作为 OpenWrt 源码编译目录；请在 Linux 虚拟机磁盘或 Docker 内部命名卷里操作，而不只是把同一个 Mac 目录映射到容器。

## 构建

```sh
python3 tools/prepare.py
JOBS=4 ./tools/build.sh --menuconfig
```

`prepare.py` 创建 `work/openwrt`、检出固定提交、复制设备树/本地软件包、加入 PHY 修复和只读 NMBM 防护，阻止此设备走普通 sysupgrade。它拒绝修改其他提交、已脏的源码树或重复套用补丁。

首次配置以 `configs/seed.config` 为基础。在菜单中保持 `MediaTek ARM → MT7622 → NEC Aterm WX3600HP`；可选 LuCI 语言、VPN、DDNS 等。默认包含 LuCI HTTPS、完整 wpad、IPv6、UPnP 与漫游相关软件；**软件安装不等于自动正确配置**。无线默认关闭，UPnP/漫游需按 [FEATURES](FEATURES.md) 启用。

重复构建沿用 `work/openwrt/.config`，不会每次覆盖你的选项。更新本移植仓库或升级 OpenWrt 源码时，应先保存 `.config` 再新建源码工作目录；现有准备标记不会自动重新覆盖旧补丁。升级源码时新建源码树，重新审查补丁，不要只改一个版本号就刷写。保留当前 `.config`、`scripts/diffconfig.sh` 输出及各 feeds 提交。

等效手工命令：

```sh
cd work/openwrt
./scripts/feeds update -a
./scripts/feeds install luci luci-ssl luci-i18n-base-zh-cn luci-app-upnp luci-app-usteer luci-app-ddns luci-app-wol iperf3
cp ../../configs/seed.config .config   # 仅首次；会覆盖已有配置
make defconfig
make menuconfig
make download -j4
make -j4 V=s
cd ../..
python3 tools/collect.py --source work/openwrt --out out/components
```

构建失败时先使用 `make -j1 V=s` 找到首个错误；不要忽略失败并打包上一次残留产物。GitHub Actions 提供检查与手动组件构建，产物不含任何人的原厂签名镜像或校准数据。

## 输出与校准

| 文件 | 用途 |
|---|---|
| `Image` | 同一构建生成的未压缩 ARM64 内核 |
| `initrd.cpio.gz` | 完整 RAM 根文件系统，与内核模块匹配 |
| `ram.dtb` | 禁用 NAND 的首轮内存测试 |
| `ro.dtb` | NAND/NMBM 只读，包括内部元数据擦写回调 |
| `install.dtb` | 仅 System2 可写的安装环境；不是只读模式 |
| `flash.dtb` | 自定义闪存布局，初始 UBI 限制在 System2 内 |
| `rootfs.squashfs` | 闪存只读根文件系统 |

通用 DTB **不嵌入任何 Factory 内容，两个 Wi-Fi 节点默认禁用**。每台设备必须使用自己的 1MiB 逻辑 Factory 备份：

```sh
mkdir -p private
python3 tools/personalize.py --dtb out/components/ram.dtb \
  --factory private/backup/mtd4-Factory.bin \
  --initrd out/components/initrd.cpio.gz --out private/ram.dtb
python3 tools/personalize.py --dtb out/components/flash.dtb \
  --factory private/backup/mtd4-Factory.bin --out private/flash.dtb
```

对 `ro.dtb`、`install.dtb` 同样使用 `--initrd`。输出的 DTB 已带 MAC 和两组 3584 字节 EEPROM，**不能共享给另一台机器**。`--single-core` 为第一级内存跳转加 `maxcpus=1`，正常功能测试使用不带该参数的 DTB，见安装文档。

## 启动工具与原厂内核模块

```sh
./tools/build-host-tools.sh
```

该命令在 Linux 上使用 ARM64 交叉编译器，生成 RAM loader、受限写入器、启动选择器、守护/面板/PHY 工具和 `boothelper.bundle`。它不连接路由器。可通过 `CC`、`OBJCOPY` 替换工具链；二进制均留在忽略目录 `out/`。

原厂 4.4.198 没有可直接使用的内置 kexec。`legacy/kexec/` 提供已使用过的回移植和 DMA 停止代码，必须针对**与本机原厂系统一致**的内核配置编译：

```sh
python3 tools/prepare_legacy.py
make -C work/legacy-kernel ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
make -C work/legacy-kernel ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- modules_prepare
make -C legacy/kexec KDIR="$PWD/work/legacy-kernel" \
  ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
```

示例配置只对应已验证的 stock 4.4.198，不能替代你保存的 `/proc/config.gz`。不要跨固件强制加载模块，不要用 `insmod -f`。NEC GPL 包的下载有哈希检查，并修正旧 dtc 与 GCC 10+ 的重复 `yylloc` 定义兼容问题；不在仓库重新分发整个厂商源码或专有 Wi-Fi 模块。

## 最终封装

必须先完成 [INSTALL](INSTALL.md) 的 RAM/只读验证，准备自己的原始 System2、bootseq、Factory、FIP 控制设备树，以及匹配构建的内核/根文件系统。`tools/pack.py --help` 列出全部显式输入；不会替你猜设备路径或下载别人的备份。

组件大小有限：根文件系统最多 `0xa80000`，ARM64 Image 最多 `0xbc0000`，DTB/启动辅助各 64KiB；原厂 CRC 覆盖窗口可能要求比上述最大值更小。打包器会按自己 bootseq 中的实际窗口拒绝过大的根文件系统。公开默认只内建本机所需的 SquashFS/UBIFS 等功能，关闭未使用的 EXT4/F2FS/JFFS2、SD/SATA 和新内核符号表，以符合原有 raw Image 槽位；原厂 kexec 模块所需的 stock KALLSYMS 不受影响。软件过多时应删减软件包，不能把边界扩大覆盖启动选择器或 NMBM 管理区。

运行 `python3 -m unittest discover -s tests -v` 和 `make test` 可检查离线格式/选择逻辑。离线成功不等于你的路由器已经通过 RAM 或冷启动验证。

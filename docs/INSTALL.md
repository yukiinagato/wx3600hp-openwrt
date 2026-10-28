# 免拆机安装：原厂 1.5.3 → RAM 验证 → System2

这条入口已在一台 WX3600HP / 原厂 1.5.3 上使用过；不是其他 Aterm、其他固件版本或所有板号的安装保证。公开脚本是整理后的版本，尚未在第二台设备上做完整首装复现。**先看完整流程并准备串口恢复能力；免拆机首装不意味着失败时永远不用拆机。**

整个过程分为三种性质：配置导入和 SSH 安装会修改原厂可写配置；首轮 RAM 与只读 NAND 校验不写 OpenWrt；最后显式的 System2 安装才擦写固件槽位。不要省略中间验证。

## 0. 准备与识别

- 一台专用电脑有线连接 LAN1，保持供电稳定；关闭会改变路由的 VPN，避免把管理面暴露到公网。
- 通过原厂管理页确认确切型号、固件 **1.5.3** 和当前系统槽；保存原始配置导出文件。不要为符合本文而盲目升级/降级原厂固件。
- 备好约 1GB 私有备份空间、自己的 SSH 密钥，以及 Linux 构建环境。
- 下文 `ROUTER` 是你自己路由器的管理地址；先在上级 DHCP 租约/ARP 中核对机身 MAC，不要照抄别人的地址。

```sh
mkdir -p private
ssh-keygen -t ed25519 -f private/admin_ed25519
python3 -m venv work/venv
work/venv/bin/pip install -r requirements-access.txt
```

## 1. 原厂认证入口与 Telnet

实机的原厂管理程序在认证后可读取指定本机文件；配置导入的数据本质上包含 shell 配置命令。工具仅连接明确指定的一台自有设备，不扫描网络，也不输出内置凭据。

先取得本机 form CGI 和 `/usr/sbin/clix`，保留在私有目录。网页 CGI 的路径应按本机文件布局核对，已知布局可能位于 `/www/cgi-bin/form.cgi` 或 `/usr/sbin/form.cgi`；拿到的必须是 ELF 文件，不能把登录页面当成程序继续处理。`stock_read.py` 每次交互输入原厂管理员密码，不将密码写入命令行或仓库。

```sh
python3 tools/stock_read.py --host http://ROUTER --stock-version 1.5.3 \
  --path /www/cgi-bin/form.cgi --out private/form.cgi
python3 tools/stock_read.py --host http://ROUTER --stock-version 1.5.3 \
  --path /usr/sbin/clix --out private/clix
file private/form.cgi private/clix
```

如果路径、认证或格式不符合，停在这里核对；不要换成未经确认的固件或猜测偏移。

从原厂网页下载原始配置 `private/config-original.bin` 后，离线生成 Telnet 开启版本：

```sh
python3 tools/stock_config.py --stock-version 1.5.3 \
  --export private/config-original.bin --form-cgi private/form.cgi \
  --out private/config-enable-telnet.bin
```

工具从你自己的 CGI 识别加密参数，验证解密 CRC，保留原 16 字节标识及全部原配置命令，追加 `TELNETS_ENABLED=1`，重新生成 CRC 并做加密往返及 shell 语法检查。原始导出、解密内容和修改版都包含私密配置，不要公开。

**这一步开始改原厂配置：**用原厂“配置恢复”页面上传生成的文件，再正常重启。不要把它放进“固件升级”页面。重启后：

```sh
work/venv/bin/python tools/stock_telnet.py --host ROUTER \
  --stock-version 1.5.3 --clix private/clix
```

使用本机 clix 中的控制台认证数据进入 `z_shell`；应看到 root shell。格式不匹配或无提示时不要继续自动化。Telnet 是明文恢复入口，后续只在隔离有线链路上使用，SSH 验证后关闭 Telnet。

## 2. 自己的密钥 SSH

```sh
python3 tools/stock_runtime.py --public-key private/admin_ed25519.pub \
  --out private/stock-runtime.tar.gz
```

工具下载有 SHA-256 锁定的官方 OpenWrt ARM64 Dropbear、musl、libgcc、nanddump 包，生成只包含你公钥的运行时。**不把 OpenWrt 包直接装进原厂包数据库，也不分发共同私钥。**

在电脑上只向直连 LAN 地址临时提供此文件，例如：

```sh
python3 -m http.server 8000 --bind PC_LAN_IP --directory private
```

在已获得的原厂 shell 中下载、展开并显式安装：

```sh
cd /tmp
wget http://PC_LAN_IP:8000/stock-runtime.tar.gz
tar -xzf stock-runtime.tar.gz
cd wx-stock-runtime
sh install-stock-ssh.sh --persistent
```

此步骤写入原厂 overlay 的 `/opt/nec-ssh` 与启动服务。主机私钥在设备本地生成，仅监听 br-lan，禁止密码登录和转发。先在直连环境核对 SSH 主机指纹，再保存到自己的 known_hosts；备份工具要求严格匹配，不能为了连通禁用主机密钥检查。首次连接可用 `ssh -i private/admin_ed25519 -o UserKnownHostsFile=private/known_hosts root@ROUTER`，核对指纹后保存。成功 SSH 后停止临时 HTTP 服务；不要把整个私有目录长期开放。

## 3. 备份，先读不写

```sh
python3 tools/backup.py --host ROUTER --identity private/admin_ed25519 \
  --known-hosts private/known_hosts --out private/backup --include-physical
```

包含：128MiB **ECC 主数据**、全部逻辑分区、设备树、内核配置、启动参数与日志。每个逻辑分区校验长度，并与设备端再读 SHA-256 比对；物理 ECC 数据独立读取两遍。只有全部完成才写 `COMPLETE`。

运行中的 overlay 可能变化，备份不是全芯片同一时刻的原子快照；如果校验变化，应保留不完整备份，在停止修改配置后重新读到新目录。至少另存两份，尤其是 BL2、FIP、Factory、bootseq、System1、System2。**禁止使用 OOB/noecc 路径：原厂驱动曾在 OOB 读取时挂死，不能把本备份称为含 OOB 的物理克隆。**

对照实际 `/proc/mtd` 和 sysfs 记录 NAND 页 2048、擦除块 128KiB、System2 32MiB、Factory 1MiB，以及 ECC/bad-block 计数。任一不符，停止，不按固定编号写入。

## 4. 先从内存启动

按 [BUILD](BUILD.md) 编译同一套 Image、initrd、DTB、RAM loader 与匹配 stock 4.4.198 的两个 kexec 模块。原厂模块加载顺序是架构模块 `arch/arm64/kexec_mod_arm64.ko`，然后主模块 `kexec_mod.ko`。首次不带 `allow_execute=1`，先验证模块能加载/卸载及镜像只装载不跳转。

使用自己的 Factory 给 `ram.dtb` 注入校准和准确 initrd 长度。第一级额外加 `--single-core`：

```sh
python3 tools/personalize.py --dtb out/components/ram.dtb \
  --factory private/backup/mtd4-Factory.bin --initrd out/components/initrd.cpio.gz \
  --single-core --out private/ram-single.dtb
```

将工具、Image、`ram-single.dtb`、initrd 和模块放进设备 `/tmp/wx-ramboot/`，逐个核对传输 SHA-256。目录中的固定名字为 `Image`、`board.dtb`、`initrd.cpio.gz`，并将架构模块复制为 `kexec_mod_arm64.ko`。所有文件都必须来自本次构建。

只装载（不跳转）：

```sh
cd /tmp/wx-ramboot
insmod kexec_mod_arm64.ko
insmod kexec_mod.ko
./ram_loader Image board.dtb initrd.cpio.gz
./ram_loader --unload
```

确认模块和地址布局无误后，在正常复位后的原厂环境进行真正跳转。此步骤会暂时中断管理连接，但不擦写 OpenWrt：

1. 将 `legacy/stop_vendor_runtime_v2.sh` 与 `legacy/execute_ramtest.sh` 放入相同临时目录，并核对它们引用的 initrd 文件名。
2. 运行 DMA 准备脚本，冻结会重新启用接口的原厂进程，关闭无线，卸载 mt_whnat/mtfwd，解绑 HNAT；**不要强卸载有引用泄漏的原厂 Wi-Fi 模块**。
3. 卸载主 kexec 模块，再以 `allow_execute=1` 加载；执行脚本会先将原厂 JFFS2 挂载改为只读，然后由模块停止/检查 DMA、关中断、清 PCI bus-master、走启动跳板。
4. 从直连 LAN1 的 `192.168.1.0/24` 管理候选 RAM 系统；电脑可临时设 `192.168.1.2/24`，默认 RAM 路由器为 `192.168.1.1`。首轮不连接上级 WAN，避免网段冲突。

示例执行顺序如下，**前提是所有上述检查已完成**：

```sh
cd /tmp/wx-ramboot
sh stop_vendor_runtime_v2.sh
rmmod kexec_mod
insmod kexec_mod.ko allow_execute=1
sh execute_ramtest.sh
```

公开执行脚本已统一使用 `initrd.cpio.gz`。所有传输、地址和 initrd 长度都必须对应这次构建。

第一级用 `maxcpus=1` 建立单核 RAM 基线，然后在这个原生内核里用 `ram_loader` 跳转至不带 `--single-core` 的同构建 RAM DTB，验证双核与无线。**不要从运行中的 SMP 候选直接再跳另一个 SMP 候选**；此路径 CPU1 未可靠启动，每次重新候选测试应回到正常复位后的基线。

## 5. NAND/NMBM 只读校验

从单核基线进入个机 `ro.dtb` 候选，根仍全部在 RAM。确认日志明确显示 NMBM 写/擦/标坏被禁用、所有关键分区只读、ECC 没有新增失败。重新读取 BL2/FIP/Factory/bootseq/System1，与原厂备份逐项 SHA-256 一致；记录 NMBM 管理区域边界。只比较当前 System2 的内核/只读根不能代替整个槽位新备份。

测试双核、LAN、WAN 协商/收发、两频段连接、IPv4/IPv6、负载和 LED。无线国家使用真实所在地 ISO 国家码；不能随意选另一个国家来绕过信道/功率限制。不要用一次测速成功代替稳定性测试。

## 6. 封装并安装至 System2

下面是**显式写入阶段**，不能在原厂正在挂载的 System2 或已安装的 OpenWrt 闪存根上执行。

先从自己的 FIP 提取验证公钥：

```sh
python3 tools/extract_control.py --fip private/backup/mtd2-FIP.bin \
  --out private/uboot-control.dtb
./tools/build-fit-tools.sh
./tools/make-ubi.sh private/rootfs_data.ubi
```

按 BUILD 为 flash DTB 注入自己的校准（不指定 initrd），再封装：

```sh
python3 tools/pack.py \
  --stock-system2 private/backup/mtd13-System2.bin \
  --bootseq private/backup/mtd5-bootseq.bin \
  --kernel out/components/Image --rootfs out/components/rootfs.squashfs \
  --dtb private/flash.dtb --helper out/tools/boothelper.bundle \
  --ubi private/rootfs_data.ubi --control-dtb private/uboot-control.dtb \
  --fit-check-sign work/fit-tools/tools/fit_check_sign \
  --out private/System2-openwrt.bin
```

**分区文件名是原厂实机示例，必须以自己备份清单为准。** 打包器要求测试布局、System2 选择、1.5.3 头、原厂 CRC 匹配、组件不越界及独立签名验证，否则拒绝输出。打包只操作电脑文件。

再次从单核基线进入 `install.dtb` 的纯 RAM 环境。此 DT 允许 NMBM 运作和 System2 写入，已不属于只读阶段。先重新备份此时的整个 System2，并对保护分区复查哈希。复制 32MiB 安装镜像和 32MiB 当前槽备份到 RAM，确认传输哈希、内存余量以及根没有挂载任何 flash/UBI 文件系统。

```sh
./write_system2 --check-only /tmp/System2-openwrt.bin
# 最后检查 /proc/mtd 中 mtd8 必须恰是 32MiB System2，页/块几何也必须匹配。
./write_system2 --write-system2 /tmp/System2-openwrt.bin /tmp/current-System2-backup.bin
```

写入器会在第一次擦除前逐块比较旧备份与实际目标，严格检查 mtd8 标签和几何，只处理 System2，数据区先写、启动载体最后写，并逐块回读。还须从设备重新读回**整个槽位**，在电脑上与安装镜像 SHA-256 一致；再次确认 BL2/FIP/Factory/bootseq/System1 未改变，再正常重启。

若原厂槽位选择/启动行为不符合，不要修改 bootseq、FIP 或盲目写其他分区来“修正”。改走串口读取日志并回到原厂系统。

## 7. 首次持久启动与日常使用

首次有 120 秒未确认回退计时。连通后先 `touch /tmp/ramtest-keep`，验证 `/rom` 为 SquashFS、`/overlay` 为 UBIFS、根为 overlay，检查双核、LAN/WAN、无线、ECC。创建一个普通配置测试文件，执行 `wx-confirm`；然后分别做软件重启和拔电至少 10 秒冷启动，确认系统选择、配置和无线均保留。

设置自己的 root 管理密码或密钥、实际无线国家、SSID 和加密。需要拨片自动切换时按 FEATURES 初始化独立 Br/Rt 配置。保守按钮的原厂侧服务需要另外部署，不能假设 OEM System1 自动带有它。

失败恢复见 [RECOVERY](RECOVERY.md)。没有官方 factory/sysupgrade 支持；后续更换内核仍需经过 RAM 验证和同样的受限封装/安装，不要用 LuCI“刷写新固件”直接上传这些组件。

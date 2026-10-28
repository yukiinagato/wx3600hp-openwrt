# NEC Aterm WX3600HP · OpenWrt

基于 OpenWrt / Linux 6.18 的 **WX3600HP 实验性移植**。整理了实机适配源码、编译入口、免拆机启动路径、System2 镜像封装、双系统选择与串口恢复资料。

**这是树外移植，尚未合入 OpenWrt 上游。没有可以直接上传原厂网页的“通刷固件”，也不支持普通 `sysupgrade`。** 本仓库的源码构建流程与原机运行版本分开记录：原机已完成内存验证、写入、软重启及断电冷启动；公开构建结果仍需使用者在自己的机器上先做内存验证。详见 [验证状态](docs/STATUS.md)。

> English: An experimental, out-of-tree OpenWrt port for the NEC Aterm WX3600HP. Includes source overlay, build instructions, owner-specific RAM/flash packaging and recovery notes. **Not an upstream-supported target or a universal factory/sysupgrade image.** Start with [BUILD](docs/BUILD.md), then [INSTALL](docs/INSTALL.md). Calibration, stock signed images and credentials are never redistributed.

## 已完成的实机成果

| 功能 | 原机验证结果 / 限制 |
|---|---|
| CPU / RAM | MT7622 双核、512 MiB；双核内存/原子操作压力测试通过 |
| 有线网络 | MT7531 DSA；四个物理千兆 LAN；RTL8221B WAN 协商 2.5Gbps 全双工 |
| 无线 | 两张 PCIe MT7915；2.4GHz / 5GHz、HE、手机连接与传输通过；使用各自 Factory 校准 |
| IPv4 / IPv6 | 路由、NAT、DHCP；IPv6 PD 服务与无 PD 上游的中继处理；Br 模式桥接 |
| 存储 / 启动 | NMBM + SquashFS + UBI/UBIFS；配置在重启、断电后保留；保留原厂 System1 |
| 操作 / 指示灯 | LuCI；Br/Rt 拨片；保守按钮持久切换系统；无线/端口灯及管理会话蓝灯 |
| 可选软件 | UPnP/PCP/NAT-PMP、漫游组件、DDNS、WOL 等；需按网络环境配置 |

2.5G 是 WAN 链路速率，不是单个 LAN 的可用速率；每个 LAN 只有 1G，交换机到 CPU 的总链路也是 2.5G。1.2Gbps Wi-Fi PHY 协商速率也不等于 TCP 有效吞吐。WED/硬件流量卸载默认关闭，未宣称长期老化通过或满速 2.5G NAT。

## 从哪里开始

1. [编译自己的 OpenWrt](docs/BUILD.md)：固定源码/feeds、选择软件、输出组件与校准注入。
2. [免拆机安装](docs/INSTALL.md)：**原厂 1.5.3 已验证的入口** → SSH → 完整备份 → RAM → 只读 NAND → System2。
3. [启动链与闪存布局](docs/BOOT.md)：为什么保留原厂签名、CRC、System1，以及为什么不能普通升级。
4. [TTL 接线与恢复](docs/RECOVERY.md)：3.3V 串口、R53/R54/R28、回环排查和启动中断。
5. [模式、灯、IPv6、漫游及 Guest VLAN](docs/FEATURES.md)：公开默认设置与原机个性化设置的区别。
6. [验证范围与待办](docs/STATUS.md)、[贡献方式](CONTRIBUTING.md)、[许可证与来源](NOTICE.md)。

## 快速编译

在 Linux 的大小写敏感文件系统中进行。macOS/Windows 建议使用 Linux 虚拟机或 Docker 内部卷，不能直接在默认大小写不敏感的共享目录里编译 OpenWrt。

```sh
git clone https://github.com/yukiinagato/wx3600hp-openwrt.git
cd wx3600hp-openwrt
python3 tools/prepare.py
JOBS=4 ./tools/build.sh --menuconfig
```

输出在 `out/components/`：Image、根文件系统、RAM/只读/安装/闪存四种 DTB。**这些是构建组件，不是可直接刷入的固件。** 无线默认关闭，须先用自己的 Factory 备份注入 EEPROM/MAC，并设置实际使用地区和安全选项。[完整说明](docs/BUILD.md)

## 开源与隐私

本项目原创代码采用 **GPL-2.0-only**；设备树另可按 MIT 使用；第三方代码保留原有许可和署名，见 [NOTICE](NOTICE.md) 和 [LICENSE](LICENSE)。基于 OpenWrt 不代表 NEC 专有程序、签名镜像或无线固件自动变成 GPL。

仓库不包含 NAND 全备份、Factory/EEPROM、原厂签名二进制、SSH 私钥、密码或实际家庭网络配置。`private/`、`work/`、`out/` 默认不入 Git。你自己生成的配置、DTB 和最终 System2 镜像也应视为私有资料，**不要上传到 Issue 或 Release**。

硬件信息参考 [NEC 规格](https://www.aterm.jp/product/atermstation/product/warpstar/wx3600hp/spec.html)，厂商源码来自 [NEC GPL 公告](https://www.aterm.jp/function/wx3600hp/appendix/opensource.html)。本项目与 NEC、OpenWrt 项目无隶属关系。

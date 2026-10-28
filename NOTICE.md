# License, attribution and source provenance

## 本仓库原创部分

除文件头另有声明外，本仓库原创的工具、板级集成、文档和测试采用 **GNU GPL version 2 only (`GPL-2.0-only`)**。完整文本见 [LICENSE](LICENSE) / [LICENSES/GPL-2.0.txt](LICENSES/GPL-2.0.txt)。Copyright © 2026 WX3600HP OpenWrt port contributors。

`openwrt/dts/*.dts` 按文件头提供 `GPL-2.0-only OR MIT` 双重选择，MIT 文本见 [LICENSES/MIT.txt](LICENSES/MIT.txt)。硬件连接和寄存器定义参考厂商公开源码，并结合本次实机读取与测试。

## 第三方部分

- **OpenWrt**：https://github.com/openwrt/openwrt 。构建框架/包文件遵循各自文件许可，项目主要为 GPL-2.0。`legacy/stock-4.4.198.config` 是测试所用 Linux 配置；不能由此推断厂商专有模块的许可。
- **Linux**：https://www.kernel.org/ 。`legacy/kexec/` 内部分 kexec 实现源于 Linux，保留原作者、GPL 文件头及源内注释；适用版本以各文件声明为准，不能统一改成宽松许可。
- **Fabian Mastenbroek 的 kexec-mod-arm64**：`legacy/kexec/` 保留其 Copyright (C) 2021 及 GPL version 2 or later 声明。原项目 README 描述它基于 [amonakov/kexec-module](https://github.com/amonakov/kexec-module)。本仓库版本包含为 stock 4.4.198 所做的兼容调整、EL1 限制与 WX3600HP DMA 停止流程。保留的第三方代码不是本项目重新授予单一新许可证。
- **NEC / WNC 厂商 GPL 源码**：[官方入口](https://www.aterm.jp/function/wx3600hp/appendix/opensource.html)，[2024-08-30 源码包](https://www.aterm.jp/function/source_code/wx3600hp/WX3600HP_source.tar.gz)。校验值记录于 `sources.lock.json`。源码包内各组件按自己的许可使用，不表示整部原厂固件全部开源。
- **U-Boot**：从使用者校验过的 NEC GPL 包构建 FIT 检查工具；未复制 NEC 的签名私钥，也未发布包含原厂内核/签名载体的 System2 镜像。
- **Dropbear / musl / mtd-utils / 无线固件等运行时组件**：由各自官方 OpenWrt 构建/下载流程获取，各有独立许可证；根 LICENSE 不替代 MIT、LGPL、GPL 或固件再分发条款。`stock_runtime.py` 仅下载官方包并核对哈希，不在 Git 仓库内重新托管这些二进制。

构建提交和 feeds 的精确版本见 `sources.lock.json`。原机上的后续 LuCI/网络配置不是基础 SquashFS 的原始内容；此仓库用干净配置重建，未复制用户家中配置。

## 二进制再分发

发布自己构建的二进制时，应同时提供对应源码、全部补丁、精确版本和构建脚本，并遵守包含的各组件许可证。手动构建工作流会把移植仓库源码和 OpenWrt/feeds/下载源码输入一并打包，保留源码与组件的对应关系。不要把本仓库的 GPL 当作重新分发 NEC 专有签名镜像、个人校准、密钥或备份的许可。

NEC、Aterm、OpenWrt 等名称属于各自权利人，仅用于说明适配对象，不表示官方认证或合作。

# 日常配置与板级功能

公开构建使用干净的 OpenWrt 配置，**不复制原机的 SSID、密码、管理 IP 或 Guest VLAN**。默认 Rt 式网络：WAN DHCP、LAN `192.168.1.1/24`，Wi-Fi 默认关闭；先连接 LAN1 设置密码、国家和无线安全。LuCI 的 HTTPS 使用设备自己生成的证书。

## Br / Rt 拨片

先在 LuCI 配好本机无线国家、SSID、加密与基础网络，保存配置备份，再显式运行：

```sh
wx-mode-setup --enable
```

它创建 `/etc/wx-mode/profiles/br` 与 `rt` 两套配置并启用拨片选择；未创建配置前，面板程序只管理 LED，不偷偷改变网络。

| 位置 | GPIO97 / 98 原始值 | 网络 |
|---|---|---|
| Br | 0 / 1（raw 2） | WAN + LAN + 关联 lan 的 Wi-Fi 同一网桥；管理 DHCP / DHCPv6；本机不提供 DHCP/RA |
| Rt | 1 / 1（raw 3） | WAN DHCP / DHCPv6，LAN `192.168.1.1/24` 与 NAT |
| CNV | 未定义 | 保持最后有效模式，不冒充已适配的转换器模式 |

切换约 1 秒去抖，重载网络而非重启整机。离开模式时保存当前 LuCI 修改，返回时恢复；同一模式开机不覆盖已经保存的配置。`pending` 文件用于继续完成中断的配置复制；不保证复杂 Guest/VPN 自定义配置能无修改跨模式迁移。

原机按用户要求使用开放的 `Openwrt-Br/Rt-WX3600HP-<本机MAC>`。公开默认保留你自己设置的无线加密，**不会自动广播无密码 Wi-Fi**。若确实需要开放网络，可在对应模式的 LuCI/无线配置里主动设置。Br 的管理地址在上级 DHCP 租约中查找；切换后地址改变是正常现象。

保守按钮切换的是“原厂 / OpenWrt”，拨片切换的是“同一个 OpenWrt 里的 Br / Rt”，两者不是同一机制。详见 [BOOT](BOOT.md)。

## LED 与 PHY

| 指示灯 | 行为 |
|---|---|
| Power | OpenWrt 面板服务运行时绿色常亮 |
| Active | 跟随以太网接口状态/活动 |
| 2.4G / 5G | 跟随默认 AP 接口启用和流量；更名后需调整 `panel.c` 的接口映射 |
| TV | 绿色约 10Hz 快闪，用于识别此 OpenWrt 面板服务 |
| Converter | Br 绿 / Rt 红 |
| 板载隐藏蓝灯（LED12） | 存在 SSH 已建立会话，或 root LuCI 会话最近 60 秒有活动时，约 2.5Hz 闪烁 |
| LAN/WAN 网口灯 | 从厂商 GPL 初始化值恢复；LAN 亮灭脉冲缩短至原时序约四分之一 |

GPIO 全部低有效：5G 绿31/红32，TV 绿33/红34，Converter 绿35/红94，蓝36，2.4G 绿100/红86，Power 绿92/红93，Active 绿91/红99。该表是已测板号记录，不适用于其他 Aterm 型号。面板使用 GPIO v2，不与另一个 GPIO 面板服务并行启动。

蓝灯代表连接/认证会话活跃的近似状态，不是每个网络包都闪；关闭 LuCI 页面后最多约 65 秒熄灭，只打开登录页不算认证会话。默认 SSH 22 端口，更改端口或 LuCI 用户后也须调整检测代码。

RTL8221B 初始化位于 MT7531 的内部 MDIO 地址5。`wx-hw-tuning` 仅在已知 PHY ID 匹配时关闭 EEE；没有把整份厂商私有驱动/寄存器脚本照搬进主线，也不宣称该设置带来固定百分比提速。WED/HFO 默认关闭，软件 flow offload 与 packet steering 开启。

## IPv6

优先使用标准 **WAN6 DHCPv6-PD → LAN RA/DHCPv6 server**。Br 是二层桥，终端直接接收上级通告，本机不应再发第二套 RA/DHCP。

上级不提供 PD 时，原机验证过 RA/DHCPv6/NDP relay。公开工具保留实现，但默认 `wx3600hp.ipv6.mode=manual`，不会仅因暂时没拿到 PD 就强制改变你已有配置。初始化模式后需要自动选择可显式设：

```sh
uci set wx3600hp.ipv6.mode=auto
uci set wx3600hp.ipv6.ra_source=auto
uci commit wx3600hp
wx-ipv6-mode
```

中继依赖上级网络是否允许 NDP/地址转发，并不等于获得可路由的独立委派前缀。原机还遇到多个上游的零生存期 RA 冲突；`wx-ra-source` 可只接受当前 WAN6 默认网关的 RA，默认关闭，必要时才启用。自定义 IPv6 设置的 LuCI 页面源码在 `contrib/luci-ipv6/`，未默认覆盖标准 LuCI 网络页面。

## UPnP、漫游与可选服务

- Rt 可启用 miniupnpd / IGDv2 / PCP / NAT-PMP；`wx-mode-setup` 配置 secure mode 并绑定 LAN。Br 不提供 NAT 映射，关闭 UPnP。初次启用后通过 LuCI 检查允许的端口范围和外部接口，不能将 WAN 管理面当内网开放。
- 完整 `wpad-mbedtls` 提供 802.11k/v/r 所需能力，usteer 可选。安装组件本身不会自动形成漫游；各 AP 仍须设置一致 SSID、加密、密钥、移动域和正确的 FT 参数，且管理网络需能互通。不同 AP/客户端的 FT 支持要实测，不能直接复制另一户网络的密钥。
- DDNS 默认不填写账户、不启动注册；WOL 按目标 MAC 配置；Speedtest 可在自有构建菜单中选择 C/C++ 实现或用 iperf3，路由器不需要 Python speedtest-cli。
- 不要从滚动 snapshot 仓库强行装 ABI 不匹配的 kmod。内核模块必须来自这次内核构建；日常 LuCI 应用也应使用相匹配的软件源/自建仓库。

## Guest SSID / VLAN

Br 瘦 AP 的 Guest 应桥接到上级专门的 **tagged VLAN**，不要挂到普通 `lan`。上级交换机/主路由必须已创建对应 VLAN、DHCP 和隔离策略；AP 不应擅自成为另一台 DHCP/RA 服务器。

推荐过程：备份当前 Br 配置 → 在 `br-lan` 中启用 VLAN filtering → 管理 VLAN 在 WAN 和需要的 LAN 端口 untagged/PVID → Guest VLAN 仅在上行 WAN tagged → 独立 `proto none` 接口绑定 `br-lan.<VID>` → Guest SSID 关联该接口；本机管理区拒绝 Guest 输入，终端之间是否允许互访也要另设。

这里不提供整份可覆盖的 VLAN 配置：管理 L3 必须随 filtering 正确迁移至管理 VLAN 子接口，否则会立即失联；DSA 名称和机身端口也未全部一一核验。尤其不能把 Rt 的独立 WAN 随意桥进去。

**已测原机 Br Guest VLAN；Rt 下额外 Guest 的泛化迁移尚未通过，未纳入默认配置。** 普通网络和 Guest 的隔离应从 Guest 客户端实际测试管理地址、其他 VLAN、IPv4 和 IPv6，不能只看 SSID 出现就算完成。

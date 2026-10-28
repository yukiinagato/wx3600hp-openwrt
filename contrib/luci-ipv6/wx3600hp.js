'use strict';
'require view';
'require form';
return view.extend({
 render: function() {
  var m = new form.Map('wx3600hp', 'WX3600HP', 'Br / Rt 拨片自动选择对应配置。国家和地区、无线加密、VLAN 等可在标准网络设置中修改。');
  var s = m.section(form.NamedSection, 'ipv6', 'ipv6', 'IPv6');
  var o = s.option(form.ListValue, 'mode', 'IPv6 配置策略');
  o.value('auto', '自动：优先前缀委派，无委派时中继');
  o.value('manual', '手动：遵循网络 / 接口中的 DHCP 与 IPv6 设置');
  o.default = 'auto';
  o = s.option(form.Value, 'ra_source', '中继上游路由器');
  o.default = 'auto';
  o.placeholder = 'auto';
  o.description = 'auto 自动选择当前 IPv6 默认网关；off 不筛选；也可填写指定路由器的 IPv6 地址。';
  o.datatype = 'or("auto","off",ip6addr)';
  return m.render();
 }
});

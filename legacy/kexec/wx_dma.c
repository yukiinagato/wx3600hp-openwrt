// SPDX-License-Identifier: GPL-2.0
/* WX3600HP-specific DMA handoff, based on vendor 4.4 mtk_stop_dma and mainline WED register definitions. */
#include <linux/module.h>
#include <linux/io.h>
#include <linux/pci.h>
#include <linux/netdevice.h>
#include <linux/rtnetlink.h>
#include <linux/delay.h>
#include <linux/errno.h>
#include <net/net_namespace.h>
static void __iomem *fe;
static void __iomem *wed[2];
static void __iomem *mirror;
static void __iomem *wdt;
static struct net_device *closed[64];
static unsigned int nclosed;
static int stop_dma(void __iomem *base, unsigned int off, const char *name)
{
 unsigned int val; int i;
 val=readl(base+off);writel(val & ~(BIT(0)|BIT(2)|BIT(6)),base+off);
 for(i=0;i<1000;i++) {
  val=readl(base+off);
  if (!(val & (BIT(1)|BIT(3)))) { pr_info("wx handoff: %s stopped cfg=%08x\n",name,val);return 0; }
  udelay(100);
 }
 pr_err("wx handoff: %s busy cfg=%08x\n",name,val);return -EBUSY;
}
int wx_dma_map(void)
{
 fe=ioremap(0x1b100000,0x3000);
 wed[0]=ioremap(0x1020a000,0x1000);wed[1]=ioremap(0x1020b000,0x1000);
 mirror=ioremap(0x10000400,0x10);
 wdt=ioremap(0x10212000,0x40);
 if (!fe || !wed[0] || !wed[1] || !mirror || !wdt) return -ENOMEM;
 pr_info("wx DMA preflight: PDMA=%08x QDMA=%08x WDMA0=%08x WDMA1=%08x WED0=%08x WED1=%08x\n",readl(fe+0xa04),readl(fe+0x1a04),readl(fe+0x2a04),readl(fe+0x2e04),readl(wed[0]+0x208),readl(wed[1]+0x208));
 return 0;
}
void wx_dma_unmap(void)
{
 if (wdt) { iounmap(wdt);wdt=NULL; }
 if (mirror) { iounmap(mirror);mirror=NULL; }
 if (fe) { iounmap(fe);fe=NULL; }
 if (wed[0]) { iounmap(wed[0]);wed[0]=NULL; }
 if (wed[1]) { iounmap(wed[1]);wed[1]=NULL; }
}
int wx_dma_quiesce(void)
{
 struct net_device *dev,*tmp;struct pci_dev *pdev=NULL;int err=0,i;u16 cmd;
 /* User tasks are frozen before this function, and wireless interfaces must already be down and HNAT must be unbound. */
 rtnl_lock();
 for_each_netdev_safe(&init_net,dev,tmp) {
  if (netif_running(dev)) {
   if (nclosed >= ARRAY_SIZE(closed)) { err=-E2BIG;break; }
   dev_hold(dev);closed[nclosed++]=dev;
   pr_info("wx handoff: closing %s\n",dev->name);dev_close(dev);
  }
 }
 rtnl_unlock();
 /* CONFIG_KEXEC_CORE=n omits this step from the stock PCI shutdown path. */
 for_each_pci_dev(pdev) {
  pci_clear_master(pdev);pci_read_config_word(pdev,PCI_COMMAND,&cmd);
  if (cmd & PCI_COMMAND_MASTER) err=-EBUSY;
  pr_info("wx handoff: PCI %s command=%04x\n",pci_name(pdev),cmd);
 }
 if (stop_dma(fe,0xa04,"PDMA"))err=-EBUSY;
 if (stop_dma(fe,0x1a04,"QDMA"))err=-EBUSY;
 /* MT7622 WDMA0/1 register bases are FE+0x2800/0x2c00, GLO_CFG at +0x204. */
 if (stop_dma(fe,0x2a04,"WDMA0"))err=-EBUSY;
 if (stop_dma(fe,0x2e04,"WDMA1"))err=-EBUSY;
 for(i=0;i<2;i++) {
  /* v1 WPDMA and WDMA driver enable bits 0/2; disable interrupt delivery too. */
  writel(0,mirror+i*4);
  writel(0,wed[i]+0x204);
  writel(readl(wed[i]+0x508)&~(BIT(0)|BIT(2)),wed[i]+0x508);
  writel(readl(wed[i]+0xa04)&~(BIT(0)|BIT(2)),wed[i]+0xa04);
  if(stop_dma(wed[i],0x208,i?"WED1":"WED0"))err=-EBUSY;
 }
 wmb();
 return err;
}

void wx_dma_resume(void)
{
 unsigned int i;
 rtnl_lock();
 for(i=0;i<nclosed;i++){dev_open(closed[i]);dev_put(closed[i]);}
 nclosed=0;
 rtnl_unlock();
}

void wx_arm_recovery_watchdog(void)
{
 u32 mode=readl(wdt);
 writel((31U<<11)|0x8,wdt+0x4);
 writel(0x1971,wdt+0x8);
 mode &= ~(BIT(3)|BIT(6));
 writel(mode|BIT(0)|BIT(2)|0x22000000,wdt);
 wmb();
}

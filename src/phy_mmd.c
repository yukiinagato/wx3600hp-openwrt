// SPDX-License-Identifier: GPL-2.0-only
/* Small PHY MMD diagnostic through the kernel's serialized C45 ioctl path. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <linux/mii.h>
#include <linux/mdio.h>
#include <linux/sockios.h>
int main(int argc,char **argv) {
 if(argc!=5 && argc!=6){fprintf(stderr,"usage: %s iface phy devad reg [value]\n",argv[0]);return 2;}
 struct ifreq req={0};
 if(strlen(argv[1])>=IFNAMSIZ)return 2;
 strcpy(req.ifr_name,argv[1]);
 struct mii_ioctl_data *m=(void *)&req.ifr_data;
 unsigned phy=strtoul(argv[2],0,0),dev=strtoul(argv[3],0,0),reg=strtoul(argv[4],0,0);
 if(phy>31||dev>31||reg>65535)return 2;
 m->phy_id=MDIO_PHY_ID_C45|(phy<<5)|dev;m->reg_num=reg;
 int fd=socket(AF_INET,SOCK_DGRAM,0);if(fd<0){perror("socket");return 1;}
 if(argc==6){unsigned val=strtoul(argv[5],0,0);if(val>65535)return 2;m->val_in=val;
  if(ioctl(fd,SIOCSMIIREG,&req)){perror("write MMD");close(fd);return 1;}}
 if(ioctl(fd,SIOCGMIIREG,&req)){perror("read MMD");close(fd);return 1;}
 if(argc==6 && m->val_out!=m->val_in){fprintf(stderr,"MMD readback mismatch\n");close(fd);return 1;}
 printf("%s phy%u mmd%u reg0x%04x=0x%04x\n",argv[1],phy,dev,reg,m->val_out);close(fd);return 0;
}

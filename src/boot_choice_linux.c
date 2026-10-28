/* SPDX-License-Identifier: GPL-2.0
 * Two-slot persistent boot choice in unused System2 kernel padding only.
 * Never opens BL2/FIP/Factory/bootseq. Old valid slot survives interrupted writes.
 */
#include "boot_choice.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <mtd/mtd-user.h>
#include <sys/file.h>
#include <errno.h>
static void die(const char *s){perror(s);exit(1);}
static int open_choice(off_t *base,int writing){
 FILE *f=fopen("/proc/mtd","r");if(!f)die("proc/mtd");
 char line[256],label[128],path[64];unsigned n,size,erase;int fallback=-1;
 while(fgets(line,sizeof(line),f))if(sscanf(line,"mtd%u: %x %x \"%127[^\"]\"",&n,&size,&erase,label)==4){
  if(!strcmp(label,"boot-selection") && size==2*WX_SLOT_SIZE && erase==WX_SLOT_SIZE){snprintf(path,sizeof(path),"/dev/mtd%u",n);*base=0;fclose(f);return open(path,writing?O_RDWR|O_SYNC:O_RDONLY);}
  if(!strcmp(label,"System2") && size==0x2000000 && erase==WX_SLOT_SIZE)fallback=n;
 }
 fclose(f);if(fallback<0){errno=ENODEV;die("boot-selection partition");}
 snprintf(path,sizeof(path),"/dev/mtd%d",fallback);*base=WX_CHOICE_OFFSET;return open(path,writing?O_RDWR|O_SYNC:O_RDONLY);
}
static int select_system(unsigned choice,int write){
 off_t base;int fd=open_choice(&base,write);if(fd<0)die("open selector");
 struct mtd_info_user info;if(ioctl(fd,MEMGETINFO,&info))die("geometry");
 if(info.type!=MTD_NANDFLASH || info.erasesize!=WX_SLOT_SIZE || info.writesize!=2048 || base+2*WX_SLOT_SIZE>info.size){errno=EINVAL;die("unexpected geometry");}
 struct wx_choice records[2];
 for(unsigned i=0;i<2;i++)if(pread(fd,&records[i],sizeof(records[i]),base+i*WX_SLOT_SIZE)!=sizeof(records[i]))die("read selector");
 int cur=wx_latest(records,records+1);unsigned current=cur<0?0:records[cur].choice;
 printf("current=%s sequence=%u slot=%d\n",current?"stock":"openwrt",cur<0?0:records[cur].sequence,cur);fflush(stdout);
 if(!write || current==choice){close(fd);return current;}
 if(cur<0){
  unsigned char blank[2048];
  for(unsigned o=0;o<2*WX_SLOT_SIZE;o+=sizeof(blank)){
   if(pread(fd,blank,sizeof(blank),base+o)!=sizeof(blank))die("read blank selector");
   for(unsigned j=0;j<sizeof(blank);j++)if(blank[j]!=255){errno=EINVAL;die("unrecognized nonblank selector; refusing erase");}
  }
 }
 unsigned target=cur<0?0:(cur^1);unsigned char page[2048];memset(page,255,sizeof(page));
 struct wx_choice *r=(void *)page;*r=(struct wx_choice){WX_MAGIC,1,cur<0?1:records[cur].sequence+1,choice,~choice,0};r->crc=wx_crc(r,20);
 off_t offset=base+target*WX_SLOT_SIZE;
 int64_t bad=offset;if(ioctl(fd,MEMGETBADBLOCK,&bad)!=0){errno=EIO;die("selector bad block");}
 struct erase_info_user erase={offset,WX_SLOT_SIZE};if(ioctl(fd,MEMERASE,&erase))die("erase inactive selector");
 if(pwrite(fd,page,sizeof(page),offset)!=sizeof(page))die("write selector");
 /* MTD char devices complete writes synchronously and may reject fsync. */
 if(fsync(fd) && errno!=EINVAL)die("sync selector");
 unsigned char check[2048];if(pread(fd,check,sizeof(check),offset)!=sizeof(check) || memcmp(page,check,sizeof(page))){errno=EIO;die("selector verification");}
 printf("verified selected=%s sequence=%u slot=%u\n",choice?"stock":"openwrt",r->sequence,target);close(fd);return choice;
}
int main(int argc,char **argv){
 if(argc==2 && !strcmp(argv[1],"--status")){select_system(0,0);return 0;}
 if(argc==3 && !strcmp(argv[1],"--select") && (!strcmp(argv[2],"stock") || !strcmp(argv[2],"openwrt"))){int lock=open("/tmp/wx-choice.lock",O_CREAT|O_RDWR,0600);if(lock<0 || flock(lock,LOCK_EX|LOCK_NB))die("selector lock");select_system(!strcmp(argv[2],"stock"),1);return 0;}
 if(argc!=3 || strcmp(argv[1],"--watch") || (strcmp(argv[2],"stock") && strcmp(argv[2],"openwrt"))){fprintf(stderr,"usage: %s --status | --select stock|openwrt | --watch stock|openwrt\n",argv[0]);return 2;}
 int lock=open("/tmp/wx-button.lock",O_CREAT|O_RDWR,0600);if(lock<0 || flock(lock,LOCK_EX|LOCK_NB))die("button lock");
 int mem=open("/dev/mem",O_RDWR|O_SYNC);if(mem<0)die("devmem");
 void *gpio=mmap(0,4096,PROT_READ,MAP_SHARED,mem,0x10211000);if(gpio==MAP_FAILED)die("gpio mmap");
 void *wd=mmap(0,4096,PROT_READ|PROT_WRITE,MAP_SHARED,mem,0x10212000);if(wd==MAP_FAILED)die("guard mmap");
 volatile uint32_t *input=(void *)((char *)gpio+0x220),*guard=(void *)((char *)wd+0x24);
 unsigned ticks=0,armed=0;puts("GPIO95 maintenance button: release to arm, hold 3 seconds and release to switch");fflush(stdout);
 for(;;){
  int released=!!(*input&0x80000000U);
  if(released){
   if(armed && ticks>=30){
    unsigned choice=!strcmp(argv[2],"openwrt");
    int slock=open("/tmp/wx-choice.lock",O_CREAT|O_RDWR,0600);if(slock<0 || flock(slock,LOCK_EX|LOCK_NB))die("selector lock");
    select_system(choice,1);*guard&=~0x10000U;__sync_synchronize();sync();
    puts("Choice verified; requesting clean reboot");fflush(stdout);execl("/sbin/reboot","reboot",(char *)0);die("reboot");
   }
   armed=1;ticks=0;
  }else if(armed && ticks<600)ticks++;
  usleep(100000);
 }
}

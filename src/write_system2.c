// SPDX-License-Identifier: GPL-2.0
/* Bounded owner installer: existing NMBM System2 only; never writes bootloader, calibration, or bootseq. */
#define _GNU_SOURCE
#include <mtd/mtd-user.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define SIZE 0x2000000
#define ERASE 0x20000
#define CARRIER 0x280000
static void die(const char *s){perror(s);exit(1);}
static void check(int ok,const char *s){if(!ok){fprintf(stderr,"REFUSED: %s\n",s);exit(2);}}
int main(int argc,char **argv){
 int write_mode=argc==4 && !strcmp(argv[1],"--write-system2");
 check((argc==3 && !strcmp(argv[1],"--check-only")) || write_mode,"usage: write_system2 --check-only image.bin | --write-system2 image.bin current-System2-backup.bin");
 FILE *f=fopen("/sys/class/mtd/mtd8/name","r");char name[128];check(f && fgets(name,sizeof name,f),"mtd8 name unavailable");fclose(f);check(!strcmp(name,"System2\n"),"mtd8 is not System2");
 f=fopen("/proc/mounts","r");char line[1024];check(f!=NULL,"mount table");
 while(fgets(line,sizeof line,f)){check(!strstr(line,"/dev/mtd") && !strstr(line,"ubi") && !strstr(line,"jffs2") && !strstr(line,"squashfs"),"installer requires a pure RAM root with no flash filesystem mounted");}fclose(f);
 int in=open(argv[2],O_RDONLY);if(in<0)die("image");struct stat st;if(fstat(in,&st))die("stat");check(st.st_size==SIZE,"image must be exactly 32 MiB");
 unsigned char *image=malloc(SIZE),*readback=malloc(ERASE);check(image && readback,"memory");
 check(read(in,image,SIZE)==SIZE,"complete image read");close(in);
 check(!memcmp(image,"\xd0\x0d\xfe\xed",4) && !memcmp(image+0x280000,"hsqs",4) && !memcmp(image+0xd00000+56,"ARM\x64",4),"FIT/SquashFS/ARM64 image layout");
 int fd=open("/dev/mtd8",write_mode?O_RDWR:O_RDONLY);if(fd<0)die("System2");struct mtd_info_user info;if(ioctl(fd,MEMGETINFO,&info))die("MEMGETINFO");
 printf("System2 type=%u size=%x erase=%x page=%x flags=%x\n",info.type,info.size,info.erasesize,info.writesize,info.flags);fflush(stdout);
 check(info.type==MTD_NANDFLASH && info.size==SIZE && info.erasesize==ERASE && info.writesize==2048,"unexpected NAND geometry");
 check((info.flags&MTD_WRITEABLE)!=0,"partition is not writable");
 if(!write_mode){puts("CHECK_ONLY_OK: no erase or write issued");return 0;}
 /* The backup was independently hashed in the read-only phase. Compare it again
  * to the actual target before the first erase, so wrong/stale targets fail closed. */
 int old=open(argv[3],O_RDONLY);if(old<0)die("current System2 backup");
 struct stat os;if(fstat(old,&os))die("backup stat");check(os.st_size==SIZE,"backup must be exactly 32 MiB");
 unsigned char *prior=malloc(ERASE);check(prior!=NULL,"backup comparison memory");
 for(uint32_t off=0;off<SIZE;off+=ERASE){
  check(pread(old,prior,ERASE,off)==ERASE && pread(fd,readback,ERASE,off)==ERASE,"read current bank");
  check(!memcmp(prior,readback,ERASE),"current System2 differs from saved backup; refusing erase");
 }
 free(prior);close(old);
 sync();
 for(uint32_t off=0;off<SIZE;off+=ERASE){struct erase_info_user e={off,ERASE};if(ioctl(fd,MEMERASE,&e))die("erase System2");if(!(off%0x200000)){printf("erased %x\n",off);fflush(stdout);}}
 /* Complete the root/kernel/helper before making the signed carrier bootable. */
 for(unsigned pass=0;pass<2;pass++){
  uint32_t start=pass?0:CARRIER,end=pass?CARRIER:SIZE;
  for(uint32_t off=start;off<end;off+=ERASE){
   for(uint32_t page=off;page<off+ERASE;page+=2048){
    unsigned j;for(j=0;j<2048 && image[page+j]==255;j++);if(j==2048)continue;
    if(pwrite(fd,image+page,2048,page)!=2048)die("NMBM NAND page write");
   }
   if(pread(fd,readback,ERASE,off)!=ERASE)die("readback");check(!memcmp(readback,image+off,ERASE),"block readback mismatch");
   if(!(off%0x200000)){printf("written and verified %x\n",off);fflush(stdout);}
  }
 }
 sync();puts("SYSTEM2_WRITE_AND_BLOCK_READBACK_OK");close(fd);return 0;
}

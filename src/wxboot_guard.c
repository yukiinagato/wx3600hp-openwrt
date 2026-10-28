// SPDX-License-Identifier: GPL-2.0
/* MT7622 watchdog NONRST_REG2 bit 16: volatile warm-reboot fallback marker. No flash access. */
#include <sys/mman.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <stdlib.h>
int main(int argc,char **argv){
 int fd;void *p;volatile uint32_t *reg;uint32_t before,after;
 if(argc!=2 || (strcmp(argv[1],"--read") && strcmp(argv[1],"--mark") && strcmp(argv[1],"--clear"))){fprintf(stderr,"usage: %s --read|--mark|--clear\n",argv[0]);return 2;}
 fd=open("/dev/mem",O_RDWR|O_SYNC);if(fd<0){perror("/dev/mem");return 1;}
 p=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0x10212000);if(p==MAP_FAILED){perror("mmap");return 1;}
 reg=(volatile uint32_t *)((char *)p+0x24);before=*reg;after=before;
 if(!strcmp(argv[1],"--mark"))after|=0x10000;
 if(!strcmp(argv[1],"--clear"))after&=~0x10000U;
 if(after!=before){*reg=after;__sync_synchronize();}
 printf("NONRST_REG2 before=%08x after=%08x readback=%08x\n",before,after,*reg);
 if(*reg!=after)return 1;
 munmap(p,4096);close(fd);return 0;
}

// SPDX-License-Identifier: GPL-2.0
/* Owner-specific WX3600HP RAM loader. No MTD opens, flash erase or write operations. */
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <sys/syscall.h>
#include <sys/reboot.h>
#include <linux/reboot.h>
static int native;

struct segment { const void *buf; size_t bufsz; unsigned long mem; size_t memsz; };
struct arguments { unsigned long entry,nr; struct segment *segments; unsigned long flags; };
static int load_image(int fd, struct arguments *a) { return native ? syscall(SYS_kexec_load,a->entry,a->nr,a->segments,a->flags) : ioctl(fd,0x45584542UL,a); }
#define IO_LOAD 0x45584542UL
#define IO_EXEC 0x45584543UL
#define DTB_ADDR 0x51000000UL
#define STUB_ADDR 0x51010000UL
#define INITRD_ADDR 0x52000000UL
static void die(const char *s) {perror(s);exit(1);}
static unsigned char *read_file(const char *p,size_t *size) {
 struct stat st;FILE *f=fopen(p,"rb");unsigned char *b;
 if(!f || fstat(fileno(f),&st) || st.st_size<=0 || st.st_size>96*1024*1024)die(p);
 *size=st.st_size;b=malloc(*size);if(!b)die("malloc");if(fread(b,1,*size,f)!=*size)die("read");fclose(f);return b;
}
static uint64_t le64(const unsigned char *p){uint64_t n=0;int i;for(i=7;i>=0;i--)n=n*256+p[i];return n;}
static size_t page_up(size_t n){return (n+4095)&~(size_t)4095;}
static int loaded(void){FILE *f=fopen("/sys/kernel/kexec_loaded","r");int n=-1;if(f){fscanf(f,"%d",&n);fclose(f);}return n;}
static void execute_preflight(void){
 const char *mods[]={"mt_whnat","mtfwd"};unsigned i;char p[128],line[1024];FILE*f;
 for(i=0;i<2;i++){snprintf(p,sizeof p,"/sys/module/%s",mods[i]);if(access(p,F_OK)==0){fprintf(stderr,"vendor module still loaded: %s\n",mods[i]);exit(2);}}
 if(access("/sys/bus/platform/drivers/mediatek_soc_hnat/1b100000.hnat",F_OK)==0){fputs("HNAT still bound\n",stderr);exit(2);}
 { DIR *d=opendir("/sys/class/net");struct dirent *de;
   if(!d)die("net devices");
   while((de=readdir(d))){
    if(!strncmp(de->d_name,"ra",2)||!strncmp(de->d_name,"apcli",5)){
     unsigned int flags=1;snprintf(p,sizeof p,"/sys/class/net/%.60s/flags",de->d_name);f=fopen(p,"r");
     if(f){fscanf(f,"%x",&flags);fclose(f);}
     if(flags&1){fprintf(stderr,"wireless interface still up: %s\n",de->d_name);exit(2);}
    }
   }closedir(d);
 }
 f=fopen("/sys/module/kexec_mod/parameters/allow_execute","r");if(!f || fgetc(f)!='Y'){fputs("module not armed\n",stderr);exit(2);}fclose(f);
 f=fopen("/proc/mounts","r");if(!f)die("mounts");
 while(fgets(line,sizeof line,f)){
  char dev[256],where[256],type[64],options[256];
  if(sscanf(line,"%255s %255s %63s %255s",dev,where,type,options)==4 && !strcmp(type,"jffs2") && strncmp(options,"ro,",3)){
   fprintf(stderr,"JFFS2 mount is still writable: %s\n",where);exit(2);
  }
 }
 fclose(f);
}
int main(int argc,char **argv){
 unsigned char *image,*dtb,*initrd;size_t ni,nd,nr,space;unsigned long entry;int fd,execute=0,unload=0;struct segment seg[4];struct arguments a;
 /* These instructions load x0=DTB, zero x1..x3, then branch through x4. */
 struct { uint32_t code[6];uint64_t dtb,entry; } stub={ {0x580000c0,0xaa1f03e1,0xaa1f03e2,0xaa1f03e3,0x58000084,0xd61f0080}, DTB_ADDR,0 };
 if(argc==2 && !strcmp(argv[1],"--unload"))unload=1;
 else if(argc!=4 && argc!=5){fprintf(stderr,"usage: %s Image dtb initrd [--execute] | --unload\n",argv[0]);return 2;}
 if(argc==5){if(strcmp(argv[4],"--execute"))return 2;execute=1;}
 native=access("/dev/kexec",F_OK)!=0; fd=-1; if(!native) { if(execute)execute_preflight(); fd=open("/dev/kexec",O_RDONLY);if(fd<0)die("open /dev/kexec"); }
 a=(struct arguments){0,0,NULL,183UL<<16};
 if(unload){if(load_image(fd,&a))die("unload");printf("loaded=%d\n",loaded());return loaded()!=0;}
 image=read_file(argv[1],&ni);dtb=read_file(argv[2],&nd);initrd=read_file(argv[3],&nr);
 if(ni<64 || memcmp(image+56,"ARM\x64",4) || nd<40 || memcmp(dtb,"\xd0\x0d\xfe\xed",4)){fputs("invalid Image/DTB\n",stderr);return 2;}
 entry=0x48000000UL+le64(image+8);space=le64(image+16);if(space<ni)space=ni;space=page_up(space);
 if((entry&4095) || entry<0x48000000UL || entry+space>0x50000000UL || nd>0x10000 || nr>0x04000000 || (le64(image+24)&1)){
  fputs("unsupported Image layout\n",stderr);return 2;
 }
 stub.entry=entry;
 seg[0]=(struct segment){image,ni,entry,space};seg[1]=(struct segment){dtb,nd,DTB_ADDR,page_up(nd)};
 seg[2]=(struct segment){initrd,nr,INITRD_ADDR,page_up(nr)};seg[3]=(struct segment){&stub,sizeof stub,STUB_ADDR,4096};
 a=(struct arguments){STUB_ADDR,4,seg,183UL<<16};
 printf("Image: entry=%lx file=%zu memory=%zu; DTB=%lx bytes=%zu; initrd=%lx bytes=%zu; trampoline=%lx\n",entry,ni,space,DTB_ADDR,nd,INITRD_ADDR,nr,STUB_ADDR);
 if(load_image(fd,&a))die("load Image");
 printf("loaded=%d, execute=%d\n",loaded(),execute);fflush(stdout);
 if(execute){sync();usleep(500000);if(native ? reboot(LINUX_REBOOT_CMD_KEXEC) : ioctl(fd,IO_EXEC,0))die("execute");}
 return 0;
}

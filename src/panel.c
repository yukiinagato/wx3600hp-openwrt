// SPDX-License-Identifier: GPL-2.0-only
#include <linux/gpio.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdint.h>
static int req(int chip,unsigned *pins,int n,unsigned long flags,const char *name){struct gpio_v2_line_request r={0};r.num_lines=n;r.config.flags=flags;memcpy(r.offsets,pins,n*sizeof(*pins));strncpy(r.consumer,name,sizeof(r.consumer)-1);if(ioctl(chip,GPIO_V2_GET_LINE_IOCTL,&r)){perror(name);exit(1);}return r.fd;}
static int raw(int fd){struct gpio_v2_line_values v={.mask=3};if(ioctl(fd,GPIO_V2_LINE_GET_VALUES_IOCTL,&v))return -1;return v.bits;}
static unsigned long long bytes(const char *iface){char p[128];unsigned long long a=0,b=0;snprintf(p,sizeof(p),"/sys/class/net/%s/statistics/rx_bytes",iface);FILE*f=fopen(p,"r");if(f){fscanf(f,"%llu",&a);fclose(f);}snprintf(p,sizeof(p),"/sys/class/net/%s/statistics/tx_bytes",iface);f=fopen(p,"r");if(f){fscanf(f,"%llu",&b);fclose(f);}return a+b;}
static int up(const char *iface){char p[128];unsigned flags=0;snprintf(p,sizeof(p),"/sys/class/net/%s/flags",iface);FILE*f=fopen(p,"r");if(f){fscanf(f,"%x",&flags);fclose(f);}return !!(flags&1);}
static int ssh_active(void){const char*paths[]={"/proc/net/tcp","/proc/net/tcp6"};for(int i=0;i<2;i++){FILE*f=fopen(paths[i],"r");if(!f)continue;char line[512];while(fgets(line,sizeof(line),f)){unsigned port=0,remote=0,state=0;if(sscanf(line," %*u: %*64[0-9A-Fa-f]:%x %*64[0-9A-Fa-f]:%x %x",&port,&remote,&state)==3&&port==22&&state==1){fclose(f);return 1;}}fclose(f);}return 0;}
static int luci_active(void){FILE*f=popen("ubus -t 1 call session list 2>/dev/null | jsonfilter -q -a -e '@[@.data.username=\"root\"][\"timeout\",\"expires\"]' 2>/dev/null","r");if(!f)return 0;unsigned timeout,expires;int active=0;while(fscanf(f,"%u %u",&timeout,&expires)==2)if(timeout&&expires&&timeout>=expires&&timeout-expires<60)active=1;pclose(f);return active;}
int main(int argc,char**argv){if(argc>1&&!strcmp(argv[1],"--activity")){printf("SSH=%d LuCI=%d\n",ssh_active(),luci_active());return 0;}int c=open("/dev/gpiochip0",O_RDONLY);if(c<0)return 1;unsigned ins[]={97,98};int in=req(c,ins,2,GPIO_V2_LINE_FLAG_INPUT,"wx-mode");if(argc>1&&!strcmp(argv[1],"--raw")){printf("%d\n",raw(in));return 0;}
unsigned pins[]={31,32,33,34,35,36,86,92,91,93,94,99,100};int led=req(c,pins,13,GPIO_V2_LINE_FLAG_OUTPUT|GPIO_V2_LINE_FLAG_ACTIVE_LOW,"wx-panel");int last=-1,count=0,tick=0;pid_t child=0;unsigned long long old[3]={0};int ssh=0,luci=0;
for(;;){int r=raw(in);if(r==last)count++;else{last=r;count=0;}if(child&&waitpid(child,0,WNOHANG)==child)child=0;if(argc==1&&count>=20&&!child&&(r==2||r==3)){char mode[16]="";FILE*f=fopen("/etc/wx-mode/current","r");if(f){fscanf(f,"%15s",mode);fclose(f);}const char *want=r==2?"br":"rt";if(strcmp(mode,want)){child=fork();if(!child){execl("/usr/sbin/wx-mode-switch","wx-mode-switch",want,(char*)0);_exit(127);}count=0;}}
const char *ifs[]={"wl0-ap0","wl1-ap0","eth0"};int on[3];for(int i=0;i<3;i++){unsigned long long b=bytes(ifs[i]);on[i]=up(ifs[i])&&(!(b!=old[i])||(tick%2));old[i]=b;}
uint64_t bits=(1ULL<<7);if(tick%2)bits|=1ULL<<2;if(on[0])bits|=1ULL<<12;if(on[1])bits|=1ULL<<0;if(on[2])bits|=1ULL<<8;if(r==2)bits|=1ULL<<4;else if(r==3)bits|=1ULL<<10;
FILE*f=fopen("/sys/class/net/wan/carrier","r");int carrier=0;if(f){fscanf(f,"%d",&carrier);fclose(f);}if(tick%20==0)ssh=ssh_active();if(tick%100==0)luci=luci_active();if((ssh||luci)&&((tick/4)%2))bits|=1ULL<<5;struct gpio_v2_line_values v={.mask=(1ULL<<13)-1,.bits=bits};if(ioctl(led,GPIO_V2_LINE_SET_VALUES_IOCTL,&v))return 1;tick++;usleep(50000);}}

// SPDX-License-Identifier: GPL-2.0-only
#include "boot_choice.h"
#include <assert.h>
#include <stdio.h>
static struct wx_choice rec(unsigned seq,unsigned choice){struct wx_choice r={WX_MAGIC,1,seq,choice,~choice,0};r.crc=wx_crc(&r,20);return r;}
int main(void){
 struct wx_choice a={0},b={0};assert(wx_latest(&a,&b)==-1);
 a=rec(1,0);assert(wx_latest(&a,&b)==0);
 b=rec(2,1);assert(wx_latest(&a,&b)==1);
 b.crc^=1;assert(wx_latest(&a,&b)==0);
 b=rec(2,1);for(unsigned i=0;i<sizeof(b);i++){struct wx_choice t=b;((unsigned char *)&t)[i]^=1;assert(!wx_valid(&t));}
 a=rec(0xffffffff,1);b=rec(0,0);assert(wx_latest(&a,&b)==1);
 puts("PASS: blank, both choices, newest slot, corruption rejection, generation wrap");
}

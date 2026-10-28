/* SPDX-License-Identifier: GPL-2.0 */
#ifndef WX_BOOT_CHOICE_H
#define WX_BOOT_CHOICE_H
#include <stdint.h>
#define WX_MAGIC 0x57425833U
#define WX_SLOT_SIZE 0x20000U
#define WX_CHOICE_OFFSET 0x18c0000U
struct wx_choice { uint32_t magic, version, sequence, choice, inverse, crc; };
static uint32_t wx_crc(const void *data, unsigned n) {
 const unsigned char *p=data; uint32_t c=~0U;
 while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^((0U-(c&1))&0xedb88320U);}
 return ~c;
}
static int wx_valid(const struct wx_choice *r) {
 return r->magic==WX_MAGIC && r->version==1 && r->choice<=1 && r->inverse==~r->choice && r->crc==wx_crc(r,20);
}
static int wx_latest(const struct wx_choice *a,const struct wx_choice *b) {
 int av=wx_valid(a),bv=wx_valid(b);
 if(!av)return bv?1:-1;
 return bv && (int32_t)(b->sequence-a->sequence)>0?1:0;
}
#endif

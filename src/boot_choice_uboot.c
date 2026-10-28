/* SPDX-License-Identifier: GPL-2.0
 * Freestanding U-Boot application. Returns 0 only for selected OpenWrt and
 * clear warm-boot guard. No ABI jump table, NAND writes or MMIO writes.
 * Two selector eraseblocks must already be read into RAM at 0x45020000.
 */
#include "boot_choice.h"
__attribute__((section(".text.entry"))) int wx_entry(int argc, char **argv) {
 (void)argc;(void)argv;
 const struct wx_choice *a=(const void *)0x45020000UL;
 const struct wx_choice *b=(const void *)(0x45020000UL+WX_SLOT_SIZE);
 int i=wx_latest(a,b);
 unsigned choice=i<0?0:(i?b:a)->choice;
 volatile uint32_t *guard=(void *)0x10212024UL;
 return choice!=0 || *guard!=0;
}

/* GPL-2.0. EL1-only transition; no hypervisor calls. */
#ifndef _ARM64_CPU_RESET_H
#define _ARM64_CPU_RESET_H
#include "idmap.h"
void __cpu_soft_restart(unsigned long entry,unsigned long arg0,unsigned long arg1,unsigned long arg2);
static void __noreturn cpu_soft_restart(unsigned long entry,unsigned long arg0,unsigned long arg1,unsigned long arg2)
{
 typeof(__cpu_soft_restart) *restart=(void *)kexec_pa_symbol(__cpu_soft_restart);
 kexec_idmap_install();
 restart(entry,arg0,arg1,arg2);
 unreachable();
}
#endif

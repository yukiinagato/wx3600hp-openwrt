/* GPL-2.0. WX3600HP Linux 4.4 port: first-stage EL1-only handoff.
 * This deliberately does not patch EL2 vectors or guess hidden data addresses.
 * Payload must have KVM disabled and boot maxcpus=1 until secondary EL handling is validated.
 */
#include <linux/mm_types.h>
#include <linux/kallsyms.h>
#include <linux/errno.h>
#include <asm/pgtable.h>
#include <asm/virt.h>
static void (*switch_mm_ptr)(unsigned long, struct mm_struct *);
static void (*flush_ptr)(void *, size_t);
void cpu_do_switch_mm(unsigned long pgd, struct mm_struct *mm) { switch_mm_ptr(pgd, mm); }
void __flush_dcache_area(void *addr, size_t len) { flush_ptr(addr,len); }
bool cpus_are_stuck_in_kernel(void) { return false; } /* execute path separately checks exactly one online CPU */
u64 idmap_t0sz = TCR_T0SZ(VA_BITS);
u32 __boot_cpu_mode[2] = { BOOT_CPU_MODE_EL1, BOOT_CPU_MODE_EL1 };
struct mm_struct init_mm;
int machine_kexec_compat_load(int detect_el2, int shim_hyp)
{
 unsigned long ttbr1, el;
 if (detect_el2 || shim_hyp) return -EINVAL;
 asm volatile("mrs %0, CurrentEL" : "=r"(el));
 if ((el >> 2) != 1) return -EINVAL;
 switch_mm_ptr=(void *)kallsyms_lookup_name("cpu_do_switch_mm");
 flush_ptr=(void *)kallsyms_lookup_name("__flush_dcache_area");
 if (!switch_mm_ptr || !flush_ptr) return -ENOENT;
 asm volatile("mrs %0, ttbr1_el1" : "=r"(ttbr1));
 init_mm.pgd=phys_to_virt(ttbr1 & 0x0000fffffffff000UL);
 pr_info("wx kexec: EL1-only handoff; no EL2 vector changes; payload requires maxcpus=1, KVM=n\n");
 return 0;
}
void machine_kexec_compat_unload(void) { }
void machine_kexec_compat_prereset(void) { }

/* GPL-2.0. Based on Linux ARM64 cpu-reset.S; EL1-only first test. */
#include <linux/linkage.h>
#include <asm/assembler.h>
#include <asm/sysreg.h>
/* Linux v4.9 SCTLR_ELx_FLAGS: I | SA | C | A | M */
#define SCTLR_ELx_FLAGS 0x100f
.text
ENTRY(__cpu_soft_restart)
 mrs x12, sctlr_el1
 ldr x13, =SCTLR_ELx_FLAGS
 bic x12, x12, x13
 msr sctlr_el1, x12
 isb
 mov x8, x0
 mov x0, x1
 mov x1, x2
 mov x2, x3
 br x8
ENDPROC(__cpu_soft_restart)

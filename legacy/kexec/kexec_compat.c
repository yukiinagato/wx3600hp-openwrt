/*
 * Arch-generic compatibility layer for enabling kexec as loadable kernel
 * module.
 *
 * Copyright (C) 2021 Fabian Mastenbroek.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 */

#define pr_fmt(fmt) "kexec_mod: " fmt

#include <linux/version.h>
#include <linux/mm_types.h>
#include <linux/kexec.h>
#include <linux/kallsyms.h>
#include <linux/slab.h>
#include <asm/uaccess.h>
#include <asm/virt.h>

#include "kexec_compat.h"

/* These kernel symbols need to be dynamically resolved at runtime
 * using kallsym due to them not being exposed to kernel modules */
static void (*machine_shutdown_ptr)(void);
static void (*kernel_restart_prepare_ptr)(char*);
static void (*migrate_to_reboot_cpu_ptr)(void);
static void (*cpu_hotplug_enable_ptr)(void);
static int (*freeze_ptr)(void);
static void (*thaw_ptr)(void);
static void (*syscore_ptr)(void);
extern int wx_dma_map(void);
extern void wx_dma_unmap(void);
int wx_freeze_users(void) { return freeze_ptr(); }
void wx_thaw_users(void) { thaw_ptr(); }
void wx_syscore_shutdown(void) { syscore_ptr(); }

void machine_shutdown(void)
{
	machine_shutdown_ptr();
}

void kernel_restart_prepare(char *cmd)
{
	kernel_restart_prepare_ptr(cmd);
}

void migrate_to_reboot_cpu(void)
{
	migrate_to_reboot_cpu_ptr();
}

void cpu_hotplug_enable(void)
{
	cpu_hotplug_enable_ptr();
}

static void *ksym(const char *name)
{
	return (void *)kallsyms_lookup_name(name);
}

int kexec_compat_load()
{
	if (!(machine_shutdown_ptr = ksym("machine_shutdown"))
	    || !(migrate_to_reboot_cpu_ptr = ksym("migrate_to_reboot_cpu"))
	    || !(kernel_restart_prepare_ptr = ksym("kernel_restart_prepare"))
	    || !(cpu_hotplug_enable_ptr = ksym("cpu_hotplug_enable"))
            || !(freeze_ptr = ksym("freeze_processes"))
            || !(thaw_ptr = ksym("thaw_processes"))
            || !(syscore_ptr = ksym("syscore_shutdown")))
		return -ENOENT;
	return wx_dma_map();
}

void kexec_compat_unload(void)
{ wx_dma_unmap(); }

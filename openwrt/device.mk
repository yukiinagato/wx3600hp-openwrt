# SPDX-License-Identifier: GPL-2.0-only
# Components only: NONE of these files is an OEM-web-UI or sysupgrade image.
define Build/wx-dtb
	cp $(KDIR)/image-mt7622-nec-aterm-wx3600hp-$(1).dtb $@
endef

define Device/nec_aterm-wx3600hp
  DEVICE_VENDOR := NEC
  DEVICE_MODEL := Aterm WX3600HP (experimental components)
  DEVICE_DTS_DIR := ../dts
  DEVICE_DTS := mt7622-nec-aterm-wx3600hp-flash mt7622-nec-aterm-wx3600hp-ram mt7622-nec-aterm-wx3600hp-ro mt7622-nec-aterm-wx3600hp-install
  SUPPORTED_DEVICES := nec,aterm-wx3600hp
  DEVICE_PACKAGES := -fitblk wx3600hp-tools kmod-mt7915e kmod-mt7915-firmware -wpad-basic-mbedtls wpad-mbedtls
  KERNEL := kernel-bin
  KERNEL_INITRAMFS :=
  KERNEL_SIZE := 12032k
  FILESYSTEMS := squashfs
  IMAGES := rootfs.bin
  IMAGE/rootfs.bin := append-rootfs | check-size 10752k
  ARTIFACTS := Image flash.dtb ram.dtb ro.dtb install.dtb
  ARTIFACT/Image := kernel-bin | check-size 12032k
  ARTIFACT/flash.dtb := wx-dtb flash
  ARTIFACT/ram.dtb := wx-dtb ram
  ARTIFACT/ro.dtb := wx-dtb ro
  ARTIFACT/install.dtb := wx-dtb install
endef
TARGET_DEVICES += nec_aterm-wx3600hp

# SPDX-License-Identifier: GPL-2.0-only
include $(TOPDIR)/rules.mk
PKG_NAME:=wx3600hp-tools
PKG_RELEASE:=1
PKG_LICENSE:=GPL-2.0-only
PKG_BUILD_DIR:=$(BUILD_DIR)/$(PKG_NAME)
include $(INCLUDE_DIR)/package.mk

define Package/wx3600hp-tools
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=WX3600HP boot guard and hardware tools
  DEPENDS:=+libc +ubus +uci +jsonfilter
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) ./src/* $(PKG_BUILD_DIR)/
endef

define Build/Compile
	$(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) -Os $(PKG_BUILD_DIR)/boot_choice_linux.c -o $(PKG_BUILD_DIR)/wxboot_choice $(TARGET_LDFLAGS)
	$(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) -Os $(PKG_BUILD_DIR)/wxboot_guard.c -o $(PKG_BUILD_DIR)/wxboot_guard $(TARGET_LDFLAGS)
	$(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) -Os $(PKG_BUILD_DIR)/phy_mmd.c -o $(PKG_BUILD_DIR)/wx-phy-mmd $(TARGET_LDFLAGS)
	$(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) -Os $(PKG_BUILD_DIR)/panel.c -o $(PKG_BUILD_DIR)/wx-panel $(TARGET_LDFLAGS)
endef

define Package/wx3600hp-tools/install
	$(INSTALL_DIR) $(1)/usr/sbin $(1)/etc/init.d $(1)/etc/uci-defaults
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/wxboot_choice $(PKG_BUILD_DIR)/wxboot_guard $(PKG_BUILD_DIR)/wx-phy-mmd $(PKG_BUILD_DIR)/wx-panel $(1)/usr/sbin/
	$(CP) ./files/* $(1)/
endef
$(eval $(call BuildPackage,wx3600hp-tools))

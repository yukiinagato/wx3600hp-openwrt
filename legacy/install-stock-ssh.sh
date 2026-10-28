#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
# Run from the unpacked private runtime directory on stock 1.5.3.
set -eu
[ "${1:-}" = --persistent ] || { echo 'Usage: sh install-stock-ssh.sh --persistent (changes stock overlay)'; exit 2; }
[ "$(uname -r)" = 4.4.198 ]
[ ! -e /etc/init.d/nec-ssh ] || { echo 'Existing SSH installation found; refusing overwrite'; exit 1; }
for name in dropbear ld-musl-aarch64.so.1 nanddump libgcc_s.so.1 authorized_keys; do [ -s "$name" ]; done
mkdir -p /opt/nec-ssh /etc/nec-ssh /etc/dropbear
chmod 700 /opt/nec-ssh /etc/nec-ssh /etc/dropbear
cp dropbear ld-musl-aarch64.so.1 nanddump libgcc_s.so.1 /opt/nec-ssh/
chmod 700 /opt/nec-ssh/*
ln -s dropbear /opt/nec-ssh/dropbearkey
/opt/nec-ssh/ld-musl-aarch64.so.1 --library-path /opt/nec-ssh /opt/nec-ssh/dropbearkey -t ed25519 -f /etc/nec-ssh/host_ed25519
# Preserve any existing authorized keys; no shared password or private key.
cat authorized_keys >>/etc/dropbear/authorized_keys
chmod 600 /etc/dropbear/authorized_keys /etc/nec-ssh/host_ed25519
cat >/etc/init.d/nec-ssh <<'EOF'
#!/bin/sh /etc/rc.common
START=96
STOP=10
start() {
 [ ! -s /var/run/nec-ssh.pid ] || return 0
 /opt/nec-ssh/ld-musl-aarch64.so.1 --library-path /opt/nec-ssh /opt/nec-ssh/dropbear -E -s -j -k -l br-lan -p 22 -P /var/run/nec-ssh.pid -r /etc/nec-ssh/host_ed25519 >>/tmp/nec-ssh.log 2>&1
}
stop() {
 [ -s /var/run/nec-ssh.pid ] || return 0
 pid="$(cat /var/run/nec-ssh.pid)"
 case "$pid" in *[!0-9]*|'') return 1;; esac
 kill "$pid"
 rm -f /var/run/nec-ssh.pid
}
EOF
chmod 755 /etc/init.d/nec-ssh
/etc/init.d/nec-ssh enable
/etc/init.d/nec-ssh start
sync
echo 'SSH key-only listener installed on br-lan:22. Save and verify its host-key fingerprint before use.'

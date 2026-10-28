#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Prepare the pinned OpenWrt source. Never accesses a router."""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def run(*args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True)
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT/'work/openwrt')
    args = p.parse_args(); tree = args.source.resolve()
    lock = json.loads((ROOT/'sources.lock.json').read_text())['openwrt']
    if not tree.exists():
        tree.mkdir(parents=True)
        run('git', 'init', str(tree))
        run('git', 'remote', 'add', 'origin', lock['url'], cwd=tree)
        run('git', 'fetch', '--depth=1', 'origin', lock['commit'], cwd=tree)
        run('git', 'checkout', '--detach', 'FETCH_HEAD', cwd=tree)
    head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=tree,text=True).strip()
    if head != lock['commit']:
        raise SystemExit('Source revision differs from sources.lock.json; use a fresh tree')
    stamp = tree/'.wx3600hp-overlay'
    if stamp.exists():
        raise SystemExit('Overlay already applied; use a fresh tree to update it')
    if subprocess.check_output(['git','status','--porcelain'],cwd=tree):
        raise SystemExit('Refusing to modify an existing dirty OpenWrt tree')
    for f in (ROOT/'openwrt/dts').glob('*.dts'):
        shutil.copyfile(f,tree/'target/linux/mediatek/dts'/f.name)
    with (tree/'target/linux/mediatek/image/mt7622.mk').open('a') as out:
        out.write('\n'+(ROOT/'openwrt/device.mk').read_text())
    for f in (ROOT/'openwrt/patches').glob('*.patch'):
        shutil.copyfile(f,tree/'target/linux/mediatek/patches-6.18'/f.name)
    # This driver is an OpenWrt overlay file, so modify the overlay, not a build tree.
    driver=tree/'target/linux/generic/files/drivers/mtd/nand/mtk_bmt.c'
    s=driver.read_text(); marker='static void\nmtk_bmt_replace_ops'
    assert s.count(marker)==1 and s.count('bmtd._block_markbad = mtd->_block_markbad;')==1
    helpers='/* WX3600HP read-only probe also blocks internal NMBM metadata writes. */\nstatic int wx_ro_write(struct mtd_info *mtd, loff_t off, struct mtd_oob_ops *ops) { return -EROFS; }\nstatic int wx_ro_erase(struct mtd_info *mtd, struct erase_info *ei) { return -EROFS; }\nstatic int wx_ro_markbad(struct mtd_info *mtd, loff_t off) { return -EROFS; }\n\n'
    s=s.replace(marker,helpers+marker)
    s=s.replace('bmtd._block_markbad = mtd->_block_markbad;', 'bmtd._block_markbad = mtd->_block_markbad;'+'\n\tif (of_property_read_bool(mtd_get_of_node(mtd), "nec,read-only-probe")) {\n\t\tbmtd._write_oob = wx_ro_write;\n\t\tbmtd._erase = wx_ro_erase;\n\t\tbmtd._block_markbad = wx_ro_markbad;\n\t\tmtd->flags &= ~MTD_WRITEABLE;\n\t\tpr_info("WX3600HP: all NMBM writes/erases/mark-bad disabled\\n");\n\t}')
    driver.write_text(s)
    board=tree/'target/linux/mediatek/mt7622/base-files/etc/board.d/02_network'
    s=board.read_text(); marker='\tcase $board in\n'
    assert marker in s
    s=s.replace(marker, marker+'\tnec,aterm-wx3600hp)\n\t\tucidef_set_interfaces_lan_wan "lan0 lan1 lan2 lan3 lan4" wan\n\t\t;;\n',1)
    board.write_text(s)
    package=tree/'package/wx3600hp'
    shutil.copytree(ROOT/'openwrt/package',package)
    shutil.copytree(ROOT/'src',package/'src')
    # Native sysupgrade would erase the custom carrier/selector. It is deliberately blocked.
    platform=tree/'target/linux/mediatek/mt7622/base-files/lib/upgrade/platform.sh'
    s=platform.read_text()
    marker='platform_check_image() {'
    if marker not in s:
        raise SystemExit('platform_check_image layout changed; review upgrade guard')
    s=s.replace(marker,marker+'\n\t[ "$(board_name)" != "nec,aterm-wx3600hp" ] || { echo "WX3600HP: use the documented RAM installer, not sysupgrade" >&2; return 1; }',1)
    marker='platform_do_upgrade() {'
    assert marker in s
    s=s.replace(marker,marker+'\n\t[ "$(board_name)" != "nec,aterm-wx3600hp" ] || { echo "WX3600HP: native sysupgrade unsupported" >&2; return 1; }',1)
    platform.write_text(s)
    with (tree/'target/linux/mediatek/mt7622/config-6.18').open('a') as out:
        out.write('\n'+(ROOT/'openwrt/kernel.config').read_text())
    feeds=json.loads((ROOT/'sources.lock.json').read_text())['feeds']
    (tree/'feeds.conf').write_text(''.join('src-git '+n+' '+f['url']+'^'+f['commit']+'\n' for n,f in feeds.items()))
    stamp.write_text('Pinned overlay applied; local changes are expected.\n')
    print('Prepared:',tree)
if __name__=='__main__': main()

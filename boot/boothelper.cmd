setenv wxsel nmbm nmbm0 read 45020000 58c0000 40000
setenv wxcheck go 45008000
setenv wxmark mw.l 10212024 10000
setenv wxkernel nmbm nmbm0 read 48000000 4d00000 c00000
setenv wxdt nmbm nmbm0 read 51000000 5900000 10000
setenv wxargs setenv bootargs console=ttyS0,115200n1 earlycon=uart8250,mmio32,0x11002000 swiotlb=512 panic=10 rootfstype=squashfs ubi.mtd=ubi
setenv wxwdlen mw.l 10212004 f808
setenv wxwdkey mw.l 10212008 1971
setenv wxwden mw.l 10212000 22000005
setenv wxboot booti 48000000 - 51000000
run wxsel wxcheck wxmark wxkernel wxdt wxargs wxwdlen wxwdkey wxwden wxboot;echo WX3600HP OpenWrt unconfirmed or unavailable, using System1;run boot_system1

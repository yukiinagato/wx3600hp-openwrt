FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
 build-essential clang flex bison gawk gettext git libncurses-dev libssl-dev \
 python3 python3-setuptools python3-pyelftools rsync swig unzip zlib1g-dev \
 file wget curl ca-certificates subversion zstd device-tree-compiler \
 u-boot-tools mtd-utils gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu \
 && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 builder
WORKDIR /home/builder/wx3600hp-openwrt
COPY --chown=builder:builder . .
USER builder
CMD ["./tools/build.sh"]

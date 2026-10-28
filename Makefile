# SPDX-License-Identifier: GPL-2.0-only
.PHONY: test prepare build tools

test:
	python3 -m unittest discover -s tests -v
	mkdir -p out/tests
	$(CC) -std=c11 -Wall -Wextra -Isrc tests/test_boot_choice.c -o out/tests/boot-choice
	./out/tests/boot-choice
	python3 tools/audit.py

prepare:
	python3 tools/prepare.py

build:
	./tools/build.sh

tools:
	./tools/build-host-tools.sh

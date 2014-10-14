override SHELL:=/bin/bash
override SHELLOPTS:=errexit:pipefail
export SHELLOPTS
override DATE:=$(shell date -u "+%Y%m%d-%H%M")


.PHONY: check
check:
	test -d lib/xmlsite

.PHONY: test
test: check
	cd lib && python -B -m xmlsite.main --config ../test/config.xml --scanner main --input-dir ../test/input --output-dir ../test/output

.PHONY: clean
clean: check
	rm -rf test/output
	rm -rf output

.PHONY: tarball
tarball: NAME:=xmlsite-$(shell date +%Y%m%d)-$(shell git describe --always)
tarball: check clean
	mkdir -p output
	git archive --format=tar --prefix=$(NAME)/ HEAD | xz > output/$(NAME).tar.xz


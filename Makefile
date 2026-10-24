# alabofur - install/uninstall and package build
#
# Honors the standard PREFIX and DESTDIR conventions so it works both for a
# direct `make install` and for staged packaging (deb/rpm/nfpm).

PREFIX     ?= /usr
BINDIR     := $(PREFIX)/bin
LIBDIR     := $(PREFIX)/lib/alabofur
SHAREDIR   := $(PREFIX)/share/alabofur
MANDIR     := $(PREFIX)/share/man/man1
VERSION    := 1.0.3

INSTALL    ?= install

.PHONY: all install uninstall check deb rpm package clean

all:
	@echo "Targets: install, uninstall, check, deb, rpm, package"

# Install into $(DESTDIR)$(PREFIX). The CLI finds its libs via <bindir>/../lib.
install:
	$(INSTALL) -d $(DESTDIR)$(BINDIR)
	$(INSTALL) -d $(DESTDIR)$(LIBDIR)
	$(INSTALL) -d $(DESTDIR)$(SHAREDIR)
	$(INSTALL) -d $(DESTDIR)$(MANDIR)
	$(INSTALL) -m 0755 bin/alabofur            $(DESTDIR)$(BINDIR)/alabofur
	$(INSTALL) -m 0644 lib/alabofur/common     $(DESTDIR)$(LIBDIR)/common
	$(INSTALL) -m 0644 lib/alabofur/config     $(DESTDIR)$(LIBDIR)/config
	$(INSTALL) -m 0644 lib/alabofur/tc         $(DESTDIR)$(LIBDIR)/tc
	$(INSTALL) -m 0644 share/alabofur/alabofur.service $(DESTDIR)$(SHAREDIR)/alabofur.service
	$(INSTALL) -m 0644 share/man/man1/alabofur.1       $(DESTDIR)$(MANDIR)/alabofur.1

uninstall:
	rm -f $(DESTDIR)$(BINDIR)/alabofur
	rm -rf $(DESTDIR)$(LIBDIR)
	rm -rf $(DESTDIR)$(SHAREDIR)
	rm -f $(DESTDIR)$(MANDIR)/alabofur.1

# Static analysis (requires shellcheck).
check:
	shellcheck -s sh bin/alabofur lib/alabofur/common lib/alabofur/config lib/alabofur/tc

# Build a .deb / .rpm with nfpm (https://nfpm.goreleaser.com).
deb:
	nfpm package -f packaging/nfpm.yaml -p deb -t .

rpm:
	nfpm package -f packaging/nfpm.yaml -p rpm -t .

package: deb rpm

clean:
	rm -f *.deb *.rpm

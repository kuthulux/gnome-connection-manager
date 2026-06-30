PKG_NAME    = gnome-connection-manager
PKG_VERSION = 1.3.3
PKG_MAINTAINER = "MathildeDec <mathilde.deuscher@gmail.com>"
PKG_DESCRIPTION = "Multi-protocol tabbed connection manager (SSH/RDP/VNC/SPICE/Serial)"
PKG_VENDOR  = MathildeDec
PKG_URL     = https://github.com/MathildeDec/gnome-connection-manager
PKG_ARCH    = all
PKG_ARCH_RPM = noarch
PKG_LICENSE = GPLv3
PKG_DEB     = $(PKG_NAME)_$(PKG_VERSION)_$(PKG_ARCH).deb
PKG_RPM     = $(PKG_NAME)-$(PKG_VERSION).$(PKG_ARCH_RPM).rpm
PKG_OPENSUSE = $(PKG_NAME)-opensuse-$(PKG_VERSION).$(PKG_ARCH_RPM).rpm

TMPINSTALLDIR = /tmp/$(PKG_NAME)-fpm-install

FPM_COMMON = -s dir -n $(PKG_NAME) -v $(PKG_VERSION) -C $(TMPINSTALLDIR) \
	--maintainer $(PKG_MAINTAINER) \
	--description "$$(printf '$(PKG_DESCRIPTION)')" \
	--license $(PKG_LICENSE) --vendor $(PKG_VENDOR) \
	--category net --url $(PKG_URL)

# ── Cibles principales ────────────────────────────────────────────────────────
.PHONY: all deb rpm opensuse install translate test lint validate clean help

all:  test lint deb rpm opensuse translate validate

help:
	@echo "Cibles disponibles :"
	@echo "  make          → deb + rpm (défaut)"
	@echo "  make deb      → paquet .deb (Debian/Ubuntu)"
	@echo "  make rpm      → paquet .rpm (Fedora/RHEL/CentOS)"
	@echo "  make opensuse → paquet .rpm (openSUSE — dépendances zypper)"
	@echo "  make translate → compile tous les .po → .mo"
	@echo "  make test     → lance la suite pytest"
	@echo "  make lint     → ruff + flake8"
	@echo "  make validate → valide .po (msgfmt) + .glade/.xml/.json"
	@echo "  make clean    → supprime les paquets et répertoires temporaires"

# ── Compilation des traductions ───────────────────────────────────────────────
translate:
	@echo "Compilation des fichiers .po → .mo…"









	msgfmt lang/de_DE.po  -o lang/de_DE/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/en_US.po  -o lang/en_US/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/fr_FR.po  -o lang/fr_FR/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/it_IT.po  -o lang/it_IT/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/ko_KR.po  -o lang/ko_KR/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/pl_PL.po  -o lang/pl_PL/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/pt_BR.po  -o lang/pt_BR/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/ru_RU.po  -o lang/ru_RU/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/uk_UA.po  -o lang/uk_UA/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/ja_JP.po  -o lang/ja_JP/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/ar_AR.po  -o lang/ar_AR/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/tr_TR.po  -o lang/tr_TR/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/nl_NL.po  -o lang/nl_NL/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/cs_CZ.po  -o lang/cs_CZ/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/sv_SE.po  -o lang/sv_SE/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/nb_NO.po  -o lang/nb_NO/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/zh_CN.po  -o lang/zh_CN/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/vi_VN.po  -o lang/vi_VN/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/th_TH.po  -o lang/th_TH/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/fi_FI.po  -o lang/fi_FI/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/hu_HU.po  -o lang/hu_HU/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/ro_RO.po  -o lang/ro_RO/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/da_DK.po  -o lang/da_DK/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/el_GR.po  -o lang/el_GR/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/fa_IR.po  -o lang/fa_IR/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/he_IL.po  -o lang/he_IL/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/hi_IN.po  -o lang/hi_IN/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/id_ID.po  -o lang/id_ID/LC_MESSAGES/gcm-lang.mo
	@echo "\033[92mOK : traductions compilées\033[0m"

# ── Installation dans un répertoire temporaire ────────────────────────────────
install: translate
	mkdir -p $(DESTDIR)/usr/share/$(PKG_NAME)
	mkdir -p $(DESTDIR)/usr/share/applications
	mkdir -p $(DESTDIR)/usr/share/doc/$(PKG_NAME)
	echo "$(PKG_NAME) ($(PKG_VERSION)) all; urgency=low" \
		> $(DESTDIR)/usr/share/doc/$(PKG_NAME)/changelog
	git log --no-merges --format="* %s" \
		>> $(DESTDIR)/usr/share/doc/$(PKG_NAME)/changelog
	gzip -9 $(DESTDIR)/usr/share/doc/$(PKG_NAME)/changelog
	cp gnome-connection-manager.desktop $(DESTDIR)/usr/share/applications/
	cp LICENSE $(DESTDIR)/usr/share/doc/$(PKG_NAME)/copyright
	cp -r lang gnome_connection_manager.py gnome-connection-manager.glade \
		icon.png pyAES.py ssh.expect urlregex.py style.css \
		$(DESTDIR)/usr/share/$(PKG_NAME)/

# ── Paquet .deb (Debian / Ubuntu) ────────────────────────────────────────────
deb:
	rm -rf $(TMPINSTALLDIR) $(PKG_DEB)
	chmod -R g-w *
	$(MAKE) install DESTDIR=$(TMPINSTALLDIR)
	fpm -t deb -p $(PKG_DEB) $(FPM_COMMON) \
		-a $(PKG_ARCH) \
		-d python3 \
		-d python3-gi \
		-d gir1.2-vte-2.91 \
		-d gir1.2-gtk-3.0 \
		-d expect \
		-d python3-paramiko \
		--after-install postinst \
		--deb-priority optional \
		usr
	@echo "\033[92mOK: $(PKG_DEB)\033[0m"

# ── Paquet .rpm (Fedora / RHEL / CentOS) ─────────────────────────────────────
rpm:
	rm -rf $(TMPINSTALLDIR) $(PKG_RPM)
	chmod -R g-w *
	$(MAKE) install DESTDIR=$(TMPINSTALLDIR)
	fpm -t rpm -p $(PKG_RPM) $(FPM_COMMON) \
		-a $(PKG_ARCH_RPM) \
		-d python3 \
		-d python3-gobject \
		-d vte291 \
		-d expect \
		-d python3-paramiko \
		--after-install postinst \
		usr
	@echo "\033[92mOK: $(PKG_RPM)\033[0m"

# ── Paquet .rpm (openSUSE / SLES) ────────────────────────────────────────────
# Les noms de paquets openSUSE diffèrent de Fedora :
#   python3-gobject → python3-gobject (identique)
#   vte291          → typelib-1_0-Vte-2.91 + libvte-2_91-0
#   expect          → expect (identique)
opensuse:
	rm -rf $(TMPINSTALLDIR) $(PKG_OPENSUSE)
	chmod -R g-w *
	$(MAKE) install DESTDIR=$(TMPINSTALLDIR)
	fpm -t rpm -p $(PKG_OPENSUSE) $(FPM_COMMON) \
		-a $(PKG_ARCH_RPM) \
		--rpm-dist "opensuse" \
		-d python3 \
		-d python3-gobject \
		-d "typelib-1_0-Vte-2.91" \
		-d expect \
		-d python3-paramiko \
		--after-install postinst \
		usr
	@echo "\033[92mOK: $(PKG_OPENSUSE) (openSUSE)\033[0m"

# ── Tests unitaires ───────────────────────────────────────────────────────────
test:
	python3 -m pytest tests/ -v

# ── Lint (ruff + flake8) ──────────────────────────────────────────────────────
lint:
	ruff check gnome_connection_manager.py tests/
	flake8 gnome_connection_manager.py

# ── Validation .po / .glade / .xml / .json ───────────────────────────────────
validate:
	@echo "Validation des fichiers .po…"
	@python3 tools/validate_po.py lang/*.po && echo "\033[92m  .po OK\033[0m"
	@echo "Validation XML/Glade/JSON…"
	@python3 tools/validate_xml_json.py gnome-connection-manager.glade && \
		echo "\033[92m  .glade OK\033[0m"

# ── Nettoyage ─────────────────────────────────────────────────────────────────
clean:
	rm -rf $(TMPINSTALLDIR)
	rm -f $(PKG_DEB) $(PKG_RPM)
	find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

# ── Aide au développeur ───────────────────────────────────────────────────────
check-gitignore:
	@if [ -n "$$(git status -uno -s)" ]; then \
		echo "ERROR: des fichiers trackés ont des modifications non commitées" >&2; \
		git status -uno -s; \
		exit 1; \
	fi

check: validate lint test check-gitignore

PKG_NAME=gnome-connection-manager
PKG_DESCRIPTION="Simple tabbed ssh and telnet connection manager for GTK+ environments\nMore info in http://kuthulu.com/gcm"
PKG_VERSION=1.2.2
PKG_MAINTAINER="Renzo Bertuzzi <kuthulu@gmail.com>"
PKG_VENDOR=kuthulu.com
PKG_URL=http://kuthulu.com/gcm
PKG_ARCH=all
PKG_ARCH_RPM=noarch
PKG_DEB=${PKG_NAME}_${PKG_VERSION}_${PKG_ARCH}.deb
PKG_RPM=${PKG_NAME}-${PKG_VERSION}.${PKG_ARCH_RPM}.rpm
FPM_OPTS=-s dir -n $(PKG_NAME) -v $(PKG_VERSION)  -C $(TMPINSTALLDIR) --maintainer ${PKG_MAINTAINER} --description "$$(printf ${PKG_DESCRIPTION})" -a $(PKG_ARCH) --license GPLv3 --vendor ${PKG_VENDOR} --category net --url ${PKG_URL}
TMPINSTALLDIR=/tmp/$(PKG_NAME)-fpm-install

all : deb rpm
.PHONY : all

#install all files in a temp directory
install: translate
	mkdir -p $(DESTDIR)/usr/share/$(PKG_NAME)
	mkdir -p $(DESTDIR)/usr/share/applications
	mkdir -p $(DESTDIR)/usr/share/doc/$(PKG_NAME)
	echo "${PKG_NAME} (${PKG_VERSION}.${PKG_RELEASE}) all; urgency=low" > $(DESTDIR)/usr/share/doc/$(PKG_NAME)/changelog
	git log --no-merges --format="* %s" >> $(DESTDIR)/usr/share/doc/$(PKG_NAME)/changelog
	gzip -9 $(DESTDIR)/usr/share/doc/$(PKG_NAME)/changelog
	cp gnome-connection-manager.desktop $(DESTDIR)/usr/share/applications
	cp LICENSE $(DESTDIR)/usr/share/doc/$(PKG_NAME)/copyright
	cp -r lang donate.gif gnome_connection_manager.py gnome-connection-manager.glade icon.png pyAES.py SimpleGladeApp.py ssh.expect style.css urlregex.py $(DESTDIR)/usr/share/gnome-connection-manager/

#compile translation files
translate:
	msgfmt lang/de_DE.po -o lang/de/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/en_US.po -o lang/en/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/fr_FR.po -o lang/fr/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/it_IT.po -o lang/it/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/ko_KO.po -o lang/ko/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/pl_PL.po -o lang/pl/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/pt_BR.po -o lang/pt/LC_MESSAGES/gcm-lang.mo
	msgfmt lang/ru_RU.po -o lang/ru/LC_MESSAGES/gcm-lang.mo

# Generate a deb package using fpm
deb:
	rm -rf $(TMPINSTALLDIR)
	rm -f $(PKG_DEB)
	chmod -R g-w *
	make install DESTDIR=$(TMPINSTALLDIR)

	fpm -t deb -p $(PKG_DEB) $(FPM_OPTS) \
		-d python3 \
		-d python3-gi \
		-d expect \
		-d gir1.2-vte-2.91 \
		--after-install postinst \
		--deb-priority optional \
		usr
	@echo "\033[92mOK: $(PKG_DEB)\033[0m"

# Generate a rpm package using fpm
rpm:
	rm -rf $(TMPINSTALLDIR)
	rm -f $(PKG_RPM)
	chmod -R g-w *
	make install DESTDIR=$(TMPINSTALLDIR)

	fpm -t rpm -p $(PKG_RPM) $(FPM_OPTS) \
		-d python3 \
		-d python3-gobject \
		-d expect \
		--after-install postinst \
		usr
	@echo "\033[92mOK: $(PKG_RPM)\033[0m"

# Developer aids below

# Files might be not committed by a developer, or changed by the build or a helper like style-strip-trailing-whitespace
check-gitignore:
	@if [ -n "`git status -uno -s`" ]; then \
		echo "ERROR: Changes to files tracked in Git are not committed" >&2; \
		git status -uno -s; \
		exit 1; \
	 fi

# Style fix: strip trailing whitespace in text-file sources
style-strip-trailing-whitespace:
	@git ls-files | egrep -v '\.(png|gif|mo)$$' | \
	 while read F ; do sed -e 's,[ '"`printf '\t'`"']*$$,,' -i "$$F" ; done

check-strip-trailing-whitespace: style-strip-trailing-whitespace
	@$(MAKE) check-gitignore

check: check-strip-trailing-whitespace

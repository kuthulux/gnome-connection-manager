# Changelog — Gnome Connection Manager

## [1.3.3] — 2026-06-12 (MathildeDec fork)

### Added
- **Résolution IP Proxmox améliorée** : pipeline 4 niveaux QGA → ipconfig0 → ARP filtré par MAC → nmap ping scan (identique à libvirt)
- **Thème GTK bureau** : GCM lit maintenant `gsettings org.gnome.desktop.interface gtk-theme` + mode sombre `color-scheme=prefer-dark` au démarrage
- **491 tests unitaires** : 44 nouveaux tests pour SPICE Proxmox, icônes protocole, résolution IP, détection QXL, sous-groupes import, validation port, VNC

### Fixed
- `SpiceTab._build_cmd` : variable `_stdin` au lieu de `_` pour l'unpacking `exec_command` (évite `UnboundLocalError` au conflit avec `gettext._`)
- ARP fallback Proxmox : filtrage par MAC VM (évitait de retourner l'IP d'une autre VM)

## [1.3.2] — 2026-06-10 (MathildeDec fork)

### Added
- **Import libvirt — dialogue 2 phases** :
  - Phase 1 : URIs pré-remplies depuis dconf, user SSH, cases SSH/SPICE/RDP, log temps réel, progression
  - Phase 2 : tableau de prévisualisation scrollable (>250 lignes) — colonnes Proto/Nom/Groupe/IP/État/Importé
  - Cases à cocher par VM, boutons « Tout cocher / Tout décocher », case « Écraser existants »
  - Déplacé dans le menu **Fichier** (était Serveurs)
- **SSH via ProxyJump** (`-J user@hv:port`) si IP connue, shell HV + `-t ssh user@vm` sinon
- **SPICE via tunnel libvirt natif** : `virt-viewer --connect qemu+ssh://user@hv/system vm` (bypass URI `spice://`)
- **RDP conditionnel** : port 3389 sondé depuis l'HV (`nc`/`nmap`) avant création de l'entrée
- **`_check_port_open`** : sonde TCP depuis l'HV (nc -z fallback nmap)
- **`tools/libvirt_inventory.py` v4** :
  - CLI argparse complet : `--uris`, `--no-os`, `--no-nmap`, `--detect-ports`, `--vm-user`, `--ssh-password`, `--ssh-timeout`
  - Exports : JSON, CSV, Ansible INI (groupes linux/windows/rdp/running/stopped), Ansible YAML
  - `PortInfo` : détection ports SPICE/VNC/RDP (nc/nmap depuis l'HV)
  - `VM` : vCPUs, memory_mb (virsh dominfo)
  - Détection OS : XML → guest-agent → SSH direct
  - `ssh_connect` : password optionnel + timeout configurable
- **`tools/ssh_deploy.py`** : génération clés RSA-4096 + Ed25519 sur l'HV, déploiement via ssh-copy-id
- **`pyproject.toml`** : ruff (Google docstring convention, rules E/W/F/I/D/UP/B/C4/SIM), black, pytest
- **`.pre-commit-config.yaml`** : ruff (fix + format) + black + flake8 + pre-commit-hooks
- **Badge ruff** dans README

### Fixed
- `SpiceTab._build_cmd` : détecte `opts_str.startswith("--connect")` → bypasse URI `spice://` pour le mode libvirt
- Audit complet GTK3 v1.3.2 : `override_font → CssProvider`, `GtkPaned` double-add, `get_color → get_rgba`, `set_has_resize_grip` supprimé, `gtk-menu-images` protégé, `set_alignment → set_xalign`
- `loadConfig` : fallback par option individuelle (`_gopt()`) — plus de crash si option manquante
- `mark_tab_as_closed` : guard `get_parent() is None`

### Changed
- Scripts déplacés : `fork/libvirt_inventory.py` + `fork/ssh_deploy.py` → `tools/`
- Version : `1.3.1` → `1.3.2`

---

## [1.3.1] — 2026-06-09 (MathildeDec fork)

### Added
- **SerialTab** : console série RS-232/RS-485 embarquée dans VTE — picocom / minicom / screen
  - 11 templates constructeurs (Cisco, HP, Aruba, Juniper, Fortinet, Palo Alto, F5, Linux, Arduino, Modbus, Libre)
  - Combos dédiés : débit, bits de données, parité, bits de stop, contrôle de flux
- **VncTab** : connexion VNC native (vncviewer / vinagre / remmina)
- **SpiceTab** : connexion SPICE (remote-viewer / virt-viewer)
- **16 langues** : ajout uk / ja / ar / tr / nl / cs / sv / nb
- **379 tests unitaires** (pytest)
- Fix `save_host_to_ini` TypeError Python 3 (champs non-str)
- Fix `encrypt_old`/`decrypt_old` Python 3 bytes/str

---

## [1.3.0] — 2026-06-09 (MathildeDec fork)

### Added
- **RDP support** (étape 5) : connexion RDP via `xfreerdp` ou `xfreerdp3`, détection automatique du binaire disponible, onglet dédié avec log de session et boutons Connecter/Déconnecter
- **RDP XEmbed** (étape 6) : session xfreerdp embarquée directement dans l'onglet GCM via `Gtk.Socket` (X11 / XWayland) ; bascule automatique sur fenêtre externe si Wayland pur
- **Import libvirt** (étape 4) : dialogue d'import de VMs depuis `libvirt` (SSH ou local), ajout dans les groupes existants ou dans un nouveau groupe
- **GCMBase** (étape 3) : remplacement de `SimpleGladeApp` par un wrapper natif `Gtk.Builder` sans dépendance tierce
- **Docstrings Google** (issue #110) : 188 fonctions/méthodes documentées au format Google-style
- **Support du protocole dans `Host`** : champ `protocol` (ssh/telnet/rdp/local) dans la classe `Host`, le formulaire hôte et la sérialisation INI

### Fixed
- Python 3.13 : suppression de `from __future__ import print_function`, remplacement de `xrange` → `range`
- GTK3 : suppression de `Gtk.ImageMenuItem`, `Gtk.STOCK_*`, APIs dépréciées ; migration vers `Gtk.MenuItem` + `Gtk.Box`
- Issue #81 : crash au démarrage si `style.css` manquant → `try/except` non-bloquant
- Issue #82 : clone d'onglet avec mot de passe → logique `sendPassword` corrigée
- Issue #87 : freeze SSH sur équipements MikroTik → debounce 200 ms sur `on_terminal_size_allocate`
- Issue #88 : logging VTE cassé sur GTK 3.24+ → migration `output-written` / fallback `contents-changed`
- Issue #89 : passphrase SSH redemandée à chaque onglet → injection `SSH_AUTH_SOCK` dans l'environnement VTE
- Issue #64 : double-clic dans Midnight Commander ouvre un onglet → vérification `posY < tab_bar_height`
- Issue #66 : port du tunnel SSH perdu à la sauvegarde → sérialisation `tunnel_host:port` corrigée
- Issue #67 : surligage jaune cluster ne disparaît pas → `queue_draw()` forcé sur changement de cluster
- VTE dual-path : `output-written` (≥ VTE 0.60) avec fallback `contents-changed`

### Changed
- `app_web` : pointe désormais vers `https://github.com/MathildeDec/gnome-connection-manager`
- Version bumped : `1.2.1` → `1.3.0`
- Code reformatté avec `black` (max-line-length 120) — 0 erreur `flake8`

---

## [1.2.1] — upstream kuthulux

Dernière version upstream de référence.
Voir : https://github.com/kuthulux/gnome-connection-manager


### Added
- **RDP support** (étape 5) : connexion RDP via `xfreerdp` ou `xfreerdp3`, détection automatique du binaire disponible, onglet dédié avec log de session et boutons Connecter/Déconnecter
- **RDP XEmbed** (étape 6) : session xfreerdp embarquée directement dans l'onglet GCM via `Gtk.Socket` (X11 / XWayland) ; bascule automatique sur fenêtre externe si Wayland pur
- **Import libvirt** (étape 4) : dialogue d'import de VMs depuis `libvirt` (SSH ou local), ajout dans les groupes existants ou dans un nouveau groupe
- **GCMBase** (étape 3) : remplacement de `SimpleGladeApp` par un wrapper natif `Gtk.Builder` sans dépendance tierce
- **Docstrings Google** (issue #110) : 188 fonctions/méthodes documentées au format Google-style
- **Support du protocole dans `Host`** : champ `protocol` (ssh/telnet/rdp/local) dans la classe `Host`, le formulaire hôte et la sérialisation INI

### Fixed
- Python 3.13 : suppression de `from __future__ import print_function`, remplacement de `xrange` → `range`
- GTK3 : suppression de `Gtk.ImageMenuItem`, `Gtk.STOCK_*`, APIs dépréciées ; migration vers `Gtk.MenuItem` + `Gtk.Box`
- Issue #81 : crash au démarrage si `style.css` manquant → `try/except` non-bloquant
- Issue #82 : clone d'onglet avec mot de passe → logique `sendPassword` corrigée
- Issue #87 : freeze SSH sur équipements MikroTik → debounce 200 ms sur `on_terminal_size_allocate`
- Issue #88 : logging VTE cassé sur GTK 3.24+ → migration `output-written` / fallback `contents-changed`
- Issue #89 : passphrase SSH redemandée à chaque onglet → injection `SSH_AUTH_SOCK` dans l'environnement VTE
- Issue #64 : double-clic dans Midnight Commander ouvre un onglet → vérification `posY < tab_bar_height`
- Issue #66 : port du tunnel SSH perdu à la sauvegarde → sérialisation `tunnel_host:port` corrigée
- Issue #67 : surligage jaune cluster ne disparaît pas → `queue_draw()` forcé sur changement de cluster
- VTE dual-path : `output-written` (≥ VTE 0.60) avec fallback `contents-changed`

### Changed
- `app_web` : pointe désormais vers `https://github.com/MathildeDec/gnome-connection-manager`
- Version bumped : `1.2.1` → `1.3.0`
- Code reformatté avec `black` (max-line-length 120) — 0 erreur `flake8`

---

## [1.2.1] — upstream kuthulux

Dernière version upstream de référence.
Voir : https://github.com/kuthulux/gnome-connection-manager

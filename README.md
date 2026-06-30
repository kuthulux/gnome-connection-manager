# Gnome Connection Manager (GCM) — v1.3.3

> **Le gestionnaire de connexions multi-protocoles le plus complet pour GNOME / GTK3.**

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://python.org)
[![GTK 3](https://img.shields.io/badge/GTK-3.24-green.svg)](https://gtk.org)
[![License: GPLv3](https://img.shields.io/badge/license-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0.html)
[![Tests](https://img.shields.io/badge/tests-491%20passés-brightgreen.svg)](tests/)
[![Ruff](https://img.shields.io/badge/ruff-pass-brightgreen.svg)](pyproject.toml)

**Fork de [kuthulux/gnome-connection-manager](https://github.com/kuthulux/gnome-connection-manager)**
maintenu par [MathildeDec](https://github.com/MathildeDec/gnome-connection-manager).

---

## Pourquoi GCM ?

GCM regroupe dans une seule fenêtre à onglets **tous vos accès distants** :
terminal SSH, bureau RDP embarqué, console série RS-232/485, VNC, SPICE,
telnet et session locale. Plus besoin de jongler entre dix outils différents.

| Protocole | Implémentation | Description |
|-----------|---------------|-------------|
| **SSH** | VTE intégré | Terminal complet avec agent, tunnels, cluster mode |
| **RDP** | XEmbed + xfreerdp | Bureau Windows **directement dans l'onglet** GCM (XEmbed X11) ou fenêtre externe (Wayland) |
| **VNC** | vncviewer / vinagre / remmina | Connexion VNC avec authentification |
| **SPICE** | remote-viewer / virt-viewer | Console VM SPICE haute performance (mode URI, tunnel libvirt, ticket Proxmox) |
| **Série** | picocom / minicom / screen | Port série RS-232/RS-485 avec **11 templates constructeurs** |
| **Telnet** | telnet / expect | Sessions Telnet classiques |
| **Local** | shell | Terminal local |

---

## Fonctionnalités clés

### 🖥️ Multi-protocoles dans un seul outil
- Ouvrez un onglet SSH, un onglet RDP et une console série côte à côte
- Chaque connexion conserve ses propres paramètres (police, couleurs, tunnel…)
- Sauvegarde chiffrée des mots de passe (AES)

### 🔷 RDP intégré via XEmbed
- La session Windows s'affiche **dans l'onglet GCM** (pas une fenêtre séparée)
- Bascule automatique sur fenêtre externe si Wayland pur est détecté
- Support `xfreerdp2` et `xfreerdp3`, `/cert:ignore`, `/dynamic-resolution`
- Domaine `CORP\user` géré automatiquement (`/d:` + `/u:`)

### 🔌 Console Série RS-232 / RS-485
- Terminal VTE **embarqué** (pas de fenêtre externe)
- Contrôles dédiés : débit, bits de données, parité, bits de stop, contrôle de flux
- **11 templates constructeurs** pré-configurés :

  | Template | Débit | Format |
  |----------|-------|--------|
  | Cisco IOS / IOS-XE / NX-OS | 9600 | 8N1 |
  | HP Comware (H3C) | 9600 | 8N1 |
  | Aruba AOS-S / AOS-CX | 9600 | 8N1 |
  | Juniper JunOS | 9600 | 8N1 |
  | Fortinet FortiOS | 9600 | 8N1 |
  | Palo Alto PAN-OS | 9600 | 8N1 |
  | F5 TMOS | **19200** | 8N1 |
  | Linux / Raspberry Pi | **115200** | 8N1 |
  | Arduino / ESP32 | **115200** | 8N1 |
  | RS-485 Modbus RTU | 9600 | 8N1 |
  | Libre (manuel) | configurable | configurable |

### 📦 Import libvirt — dialogue en 2 phases
- **Phase 1 — Scan** : saisie des URIs libvirt, user SSH, cases à cocher SSH/SPICE/RDP/VNC, log en temps réel, barre de progression
- **Phase 2 — Prévisualisation** : tableau des connexions découvertes (scroll, > 250 lignes) avant import
  — colonnes : Proto | Nom VM | Groupe | IP/Hôte | État | Importé
  — lignes déjà importées grisées / cases décochées, nouvelles cochées par défaut
  — case «Écraser existants», boutons **Tout cocher / Tout décocher**
- **SSH** : jamais direct — ProxyJump (`-J user@hv:port`) si IP connue, sinon shell HV + `-t ssh user@vm`
- **SPICE** : `virt-viewer --connect qemu+ssh://user@hv/system vm` (tunnel SSH natif, pas d'URI `spice://`)
- **RDP** : uniquement si port 3389 confirmé ouvert (sondé depuis l'HV via `nc`/`nmap`)
- **VNC** : uniquement si port 5900 confirmé ouvert

### 🖥️ Import Proxmox — nativement via `qm`
- **Menu Fichier → Importer depuis Proxmox…** — idem libvirt mais inventaire via `qm list` / `qm config`
- **SPICE** : détecte `vga: qxl` → génère un ticket SPICE Proxmox à la connexion via `pvesh` + SSH → fichier `.vv` temporaire → `remote-viewer`
- **Résolution IP améliorée** : pipeline 4 niveaux — QGA → `ipconfig0` → ARP filtré par MAC → nmap ping scan
- **VNC** : sonde le port 5900 depuis l'hyperviseur

### 🛠️ Outils en ligne de commande (`tools/`)

| Script | Description |
|--------|-------------|
| [tools/libvirt\_inventory.py](tools/libvirt_inventory.py) | Inventaire complet des VMs KVM/QEMU : IP, OS, vCPUs, RAM, ports SPICE/VNC/RDP |
| [tools/ssh\_deploy.py](tools/ssh_deploy.py) | Déploiement de clés SSH (RSA-4096 + Ed25519) sur toutes les VMs depuis l’HV |

**`libvirt_inventory.py`** — exports multiples :
```bash
python3 tools/libvirt_inventory.py \
  --detect-ports \
  --output-json inventory.json \
  --output-csv  inventory.csv \
  --ansible-ini inventory.ini \
  --ansible-yaml inventory.yml
```

Options principales : `--uris`, `--no-os`, `--no-nmap`, `--ssh-password`, `--ssh-timeout`

**`ssh_deploy.py`** :
```bash
# Génère clés RSA/Ed25519 sur l’HV + déploiement via ssh-copy-id vers toutes les VMs
python3 tools/ssh_deploy.py --inventory inventory.json --vm-user ubuntu
```

### 🌐 16 langues supportées
ar · cs · de · en · fr · it · ja · ko · nb · nl · pl · pt · ru · sv · tr · uk

### 🎨 Thème GTK bureau
- GCM lit automatiquement le thème GTK du bureau au démarrage (`gsettings org.gnome.desktop.interface gtk-theme`)
- Fallback : `~/.config/gtk-3.0/settings.ini`
- Mode sombre activé si `color-scheme = prefer-dark`

### 🧙 Qualité du code
- **ruff** (linter + formateur, style Google docstring) + **flake8**
- **pre-commit** : hooks automatisés à chaque commit (`pre-commit install`)
- 491 tests unitaires pytest (chiffrement, Host, HostUtils, Serial, RDP, VNC, SPICE, libvirt, Proxmox, proto-icons, validation port)

---

## Installation

### Depuis les sources

```bash
git clone https://github.com/MathildeDec/gnome-connection-manager
cd gnome-connection-manager
./gnome_connection_manager.py
```

### Dépendances (Debian / Ubuntu)

```bash
# Obligatoires
sudo apt install python3 python3-gi gir1.2-vte-2.91 gir1.2-gtk-3.0 expect python3-pycryptodome

# RDP
sudo apt install freerdp2-x11          # ou freerdp3-x11

# VNC
sudo apt install tigervnc-viewer       # ou vinagre, remmina

# SPICE
sudo apt install virt-viewer           # fournit remote-viewer

# Console série
sudo apt install picocom               # ou minicom

# Import libvirt (recommandé : paquet système)
sudo apt install python3-paramiko
# Alternative pip (si python3-paramiko absent de votre distro) :
# pip3 install --user paramiko
```

### Dépendances (Fedora / RHEL)

```bash
sudo dnf install python3 python3-gobject vte291 expect freerdp \
                 tigervnc virt-viewer picocom python3-paramiko python3-pycryptodome
```

### Qualité du code

```bash
pip install ruff pre-commit black
pre-commit install          # installe les hooks git
pre-commit run --all-files  # vérification manuelle
```

---

## Utilisation rapide

### Ajouter une connexion SSH
1. Clic droit sur un groupe → **Nouveau hôte**
2. Remplir : nom, adresse, utilisateur, port (22)
3. Protocole : `ssh` (défaut)
4. Double-clic sur le host pour ouvrir l’onglet terminal

### Ajouter une connexion RDP
1. **Nouveau hôte** → protocole `rdp`, port `3389`
2. Renseigner `Utilisateur` et optionnellement `Mot de passe`
3. Le bureau Windows s'ouvre directement dans l'onglet

### Ajouter une connexion série
1. **Nouveau hôte** → protocole `serial`
2. Host = chemin du port (`/dev/ttyUSB0`), Port = débit initial (`9600`)
3. À l'ouverture : sélectionnez un **template** pour pré-remplir tous les paramètres

### Importer des VMs libvirt
1. Menu **Fichier → Importer depuis libvirt…**
2. Les URIs virt-manager sont pré-remplies depuis dconf
3. Cocher les protocoles à importer : SSH / SPICE / RDP / VNC
4. Cliquer **🔍 Scanner les hyperviseurs** — le log s'affiche en temps réel
5. Phase 2 : vérifier le tableau, cocher/décocher les VMs, cliquer **⬇ Importer les sélectionnés**

### Importer des VMs Proxmox
1. Menu **Fichier → Importer depuis Proxmox…**
2. Saisir l'URI de l'hyperviseur : `qemu+ssh://root@192.168.105.41/system`
3. Cocher les protocoles : SSH / SPICE / RDP / VNC
4. Pour SPICE : la VM doit avoir `vga: qxl` (GCM le détecte automatiquement)
5. À la connexion SPICE, GCM génère un ticket via `pvesh` — aucune configuration manuelle nécessaire

---

## Langue

GCM détecte automatiquement la langue du système. Pour forcer :

```bash
LANG=en_US.UTF-8 ./gnome_connection_manager.py
LANG=de_DE.UTF-8 ./gnome_connection_manager.py
```

---

## Packaging (deb / rpm / opensuse)

### Prérequis

```bash
# Debian/Ubuntu
sudo apt install git ruby ruby-dev build-essential gettext python3-paramiko
sudo gem install fpm

# Fedora/RHEL
sudo dnf install git ruby ruby-devel make gettext python3-paramiko
sudo gem install fpm
```

### Cibles `make`

| Commande | Description |
|----------|-------------|
| `make` | Génère `.deb` + `.rpm` Fedora |
| `make deb` | `.deb` Debian / Ubuntu |
| `make rpm` | `.rpm` Fedora / RHEL / CentOS |
| `make opensuse` | `.rpm` **openSUSE / SLES** (dépendances zypper : `typelib-1_0-Vte-2.91`) |
| `make translate` | Compile les 16 `.po` → `.mo` |
| `make validate` | Valide `.po` (msgfmt) + `.glade` / `.xml` / `.json` |
| `make test` | Lance la suite pytest (491 tests) |
| `make lint` | ruff + flake8 |
| `make check` | validate + lint + test + vérification git propre |
| `make clean` | Supprime paquets et `__pycache__` |
| `make help` | Affiche l'aide |

```bash
git clone https://github.com/MathildeDec/gnome-connection-manager
cd gnome-connection-manager
make            # deb + rpm Fedora
make deb        # deb seulement
make opensuse   # rpm openSUSE
make validate   # valider .po + .glade avant commit
```

### Qualité du code

```bash
pip install ruff pre-commit
pre-commit install          # installe les hooks git
pre-commit run --all-files  # vérification manuelle
```

**Hooks pre-commit actifs** :

| Hook | Fichiers ciblés | Action |
|------|----------------|--------|
| `trailing-whitespace` | tous | supprime espaces en fin de ligne |
| `end-of-file-fixer` | tous | assure un `\n` final |
| `check-yaml` / `check-toml` / `check-json` | `.yaml` / `.toml` / `.json` | syntaxe |
| `ruff` | `.py` | lint + autofix |
| `ruff-format` | `.py` | formatage |
| `flake8` | `.py` | lint complémentaire |
| `validate-po` | `.po` | `msgfmt --check` — bloque si traduction invalide |
| `validate-xml-glade-json` | `.glade` / `.xml` / `.json` | parser XML/JSON Python — bloque si syntaxe cassée |

---

## Nouveautés

### v1.3.3
- **Résolution IP Proxmox améliorée** : pipeline 4 niveaux QGA → `ipconfig0` → ARP filtré par MAC → nmap ping scan (identique libvirt)
- **Thème GTK bureau** : lecture `gsettings gtk-theme` + `color-scheme` (mode sombre) au démarrage
- **491 tests unitaires** : +44 tests (SPICE Proxmox mock, icônes protocole, résolution IP, détection QXL, sous-groupes import, validation port, VNC)
- Fix `UnboundLocalError` : variable `_stdin` pour unpacking `exec_command` (conflit avec `gettext._`)
- Fix ARP Proxmox : filtrage par MAC VM (évitait de retourner l'IP d'une autre VM)

### v1.3.2
- **Import libvirt refondu** : dialogue 2 phases (scan → tableau de prévisualisation)
  - SSH via ProxyJump (`-J`), SPICE via tunnel libvirt natif, RDP conditionnel (port 3389)
  - Tableau scrollable (>250 VMs), cases à cocher, case «Écraser existants»
  - Déplacé dans le menu **Fichier** (plus dans Serveurs)
- **`SpiceTab`** : détection `--connect` pour tunnel libvirt natif (bypass URI `spice://`)
- **Outils CLI** `tools/` : `libvirt_inventory.py` v4 + `ssh_deploy.py`
  - Exports JSON / CSV / Ansible INI / Ansible YAML
  - Détection OS (XML, guest-agent, SSH), vCPUs, RAM, ports SPICE/VNC/RDP
  - `--ssh-password`, `--ssh-timeout`, `--detect-ports`, `--no-nmap`
- **Qualité** : `pyproject.toml` + `.pre-commit-config.yaml` (ruff Google style + flake8)
- **Corrections GTK3** : audit complet dépréciations v1.3.2 (`override_font→CssProvider`, `GtkPaned`, `get_color→get_rgba`, etc.)

### v1.3.1
- **SerialTab** : console série RS-232/RS-485 embarquée dans VTE — picocom / minicom / screen
  - 11 templates constructeurs (Cisco, HP, Aruba, Juniper, Fortinet, Palo Alto, F5, Linux, Arduino, Modbus, Libre)
  - Combos dédiés : débit, bits de données, parité, bits de stop, contrôle de flux
- **VncTab** : connexion VNC native (vncviewer / vinagre / remmina)
- **SpiceTab** : connexion SPICE (remote-viewer / virt-viewer)
- **16 langues** : ajout uk / ja / ar / tr / nl / cs / sv / nb
- **379 tests unitaires** (pytest)
- Fix `save_host_to_ini` TypeError Python 3 (champs non-str)
- Fix `encrypt_old`/`decrypt_old` Python 3 bytes/str

### v1.3.0
- **RDP XEmbed** : bureau Windows directement dans l’onglet (GtkSocket + `xfreerdp /parent-window`)
- **Import libvirt** : inventaire VMs KVM/QEMU avec détection Windows
- **GCMBase** : remplacement de `SimpleGladeApp` par `Gtk.Builder` natif
- 8 bugs upstream corrigés (#64 #66 #67 #81 #82 #87 #88 #89)
- 188 docstrings Google (#110)
- Compatibilité Python 3.13 / GTK 3.24+

---

## Contribuer

Les pull requests sont les bienvenues.
Consultez [fork/ROADMAP-GCM-v1.3.md](fork/ROADMAP-GCM-v1.3.md) pour les fonctionnalités planifiées.
Pour les changements importants, ouvrez d’abord une issue.

## Licence

[GPLv3](https://www.gnu.org/licenses/gpl-3.0.html)

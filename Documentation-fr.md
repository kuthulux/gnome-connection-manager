# GCM — Documentation utilisateur (français)

**Gnome Connection Manager v1.3.3**
Fork maintenu par [MathildeDec](https://github.com/MathildeDec/gnome-connection-manager)

---

## Table des matières

1. [Présentation générale](#1-présentation-générale)
2. [Installation](#2-installation)
3. [Interface principale](#3-interface-principale)
4. [Gestion des hôtes](#4-gestion-des-hôtes)
5. [Protocole SSH](#5-protocole-ssh)
6. [Protocole RDP](#6-protocole-rdp)
7. [Protocole VNC](#7-protocole-vnc)
8. [Protocole SPICE](#8-protocole-spice)
9. [Console Série (RS-232 / RS-485)](#9-console-série-rs-232--rs-485)
10. [Protocole Telnet](#10-protocole-telnet)
11. [Terminal local](#11-terminal-local)
12. [Import libvirt / KVM](#12-import-libvirt--kvm)
13. [Import Proxmox](#13-import-proxmox)
14. [Mode cluster (multi-hôtes)](#14-mode-cluster-multi-hôtes)
15. [Tunnels SSH](#15-tunnels-ssh)
16. [Chiffrement des mots de passe](#16-chiffrement-des-mots-de-passe)
17. [Personnalisation de l'apparence](#17-personnalisation-de-lapparence)
18. [Langues / Internationalisation](#18-langues--internationalisation)
19. [Sauvegarde et restauration de la configuration](#19-sauvegarde-et-restauration-de-la-configuration)
20. [Raccourcis clavier](#20-raccourcis-clavier)
21. [Dépannage](#21-dépannage)

---

## 1. Présentation générale

GCM (Gnome Connection Manager) est un gestionnaire de connexions distantes multi-protocoles
pour Linux / GNOME. Toutes les sessions s'affichent sous forme d'**onglets** dans une
fenêtre unique, ce qui évite de jongler entre de nombreuses fenêtres et applications.

### Protocoles supportés

| Protocole | Binaire utilisé | Intégration |
|-----------|----------------|-------------|
| **SSH** | `ssh` + `expect` | Terminal VTE embarqué |
| **RDP** | `xfreerdp` | Bureau XEmbed (onglet) ou fenêtre externe |
| **VNC** | `vncviewer` / `vinagre` / `remmina` | Fenêtre ou URI |
| **SPICE** | `remote-viewer` / `virt-viewer` | URI `spice://`, tunnel libvirt ou ticket Proxmox |
| **Série** | `picocom` / `minicom` / `screen` | Terminal VTE embarqué |
| **Telnet** | `telnet` + `expect` | Terminal VTE embarqué |
| **Local** | shell système | Terminal VTE embarqué |

### Architecture

```
gnome_connection_manager.py   ← application principale (~7 500 lignes)
├── GCMBase                   ← fenêtre principale, arbre hôtes, onglets
├── Host                      ← modèle de données d’une connexion
├── HostUtils                 ← lecture/écriture du fichier de config INI
├── RdpTab                    ← onglet RDP (xfreerdp fenêtre)
├── RdpEmbeddedTab            ← onglet RDP (GtkSocket XEmbed)
├── VncTab                    ← onglet VNC
├── SpiceTab                  ← onglet SPICE (URI spice:// ou tunnel libvirt)
├── SerialTab                 ← onglet console série
├── LibvirtImportDialog       ← dialogue import 2 phases (scan → prévisualisation)
├── SerialTemplatesTab        ← onglet templates série dans les préférences
├── Whost                     ← formulaire édition hôte
└── Wconfig                   ← fenêtre préférences

tools/
├── libvirt_inventory.py      ← inventaire CLI : JSON/CSV/Ansible, détection OS/ports
└── ssh_deploy.py             ← déploiement clés SSH RSA/Ed25519 vers les VMs
```

Le fichier de configuration est stocké dans `~/.config/gnome-connection-manager/config.ini`
(chiffré AES pour les mots de passe).

---

## 2. Installation

### Prérequis communs

```bash
# Debian / Ubuntu
sudo apt install python3 python3-gi gir1.2-vte-2.91 gir1.2-gtk-3.0 expect
```

### Protocoles optionnels

```bash
# RDP
sudo apt install freerdp2-x11        # ou freerdp3-x11

# VNC
sudo apt install tigervnc-viewer     # ou vinagre, remmina

# SPICE
sudo apt install virt-viewer         # fournit remote-viewer

# Console série
sudo apt install picocom             # ou minicom (screen est standard)

# Import libvirt
sudo apt install python3-libvirt
pip3 install paramiko
```

### Fedora / RHEL

```bash
sudo dnf install python3 python3-gobject vte291 expect freerdp \
                 tigervnc virt-viewer picocom python3-libvirt
pip3 install paramiko
```

### Lancement

```bash
git clone https://github.com/MathildeDec/gnome-connection-manager
cd gnome-connection-manager
./gnome_connection_manager.py
```

---

## 3. Interface principale

```
┌─────────────────────────────────────────────────────────────────────┐
│  Menu : Fichier  Connexion  Édition  Serveurs  Aide                  │
├───────────────┬─────────────────────────────────────────────────────┤
│  Arbre hôtes  │  Onglet 1 : SSH srv01  │  Onglet 2 : RDP win10      │
│               │                                                       │
│  ▶ PROD       │  (terminal VTE ou bureau RDP embarqué)               │
│    srv01      │                                                       │
│    srv02      │                                                       │
│  ▶ DEV        │                                                       │
│    dev01      │                                                       │
└───────────────┴─────────────────────────────────────────────────────┘
```

- **Arbre hôtes** (panneau gauche) : liste des groupes et connexions sauvegardées.
- **Onglets** (droite) : chaque double-clic ouvre un nouvel onglet de connexion.
- Le panneau gauche peut être caché via **Affichage → Masquer l'arbre**.

---

## 4. Gestion des hôtes

### Créer un hôte

1. Clic droit sur un groupe dans l'arbre → **Nouveau hôte**
   _ou_ menu **Connexion → Nouvelle connexion**
2. Remplir le formulaire :
   - **Nom** : libellé affiché dans l'arbre
   - **Groupe** : dossier de classement
   - **Hôte / Adresse** : IP ou nom DNS (pour serial : chemin du port)
   - **Utilisateur**
   - **Mot de passe** (optionnel — stocké chiffré AES)
   - **Port** : port TCP ou débit en bauds pour le série
   - **Protocole** : `ssh`, `rdp`, `vnc`, `spice`, `serial`, `telnet`, `local`
   - **Paramètres supplémentaires** : options passées directement au binaire
3. Cliquer **Enregistrer**.

### Modifier / Supprimer un hôte

- Clic droit sur l'hôte → **Éditer** ou **Supprimer**

### Créer un groupe

- Clic droit dans l'arbre (zone vide) → **Nouveau groupe**

### Importer / Exporter

- **Fichier → Importer…** : importe un fichier `config.ini` existant
- **Fichier → Exporter…** : sauvegarde la configuration actuelle

---

## 5. Protocole SSH

### Paramètres

| Champ | Exemple | Description |
|-------|---------|-------------|
| Hôte | `192.168.1.10` | Adresse IP ou FQDN |
| Utilisateur | `root` | Nom d'utilisateur SSH |
| Port | `22` | Port TCP (défaut 22) |
| Mot de passe | `(vide)` | Laissez vide pour utiliser l'agent SSH |
| Paramètres supp. | `-i ~/.ssh/id_rsa` | Options `ssh` supplémentaires |

### Authentification par clé

Laissez le mot de passe vide. GCM délègue l'authentification à l'agent SSH
(`ssh-agent`). Pour utiliser une clé spécifique :

```
Paramètres supp. : -i /home/user/.ssh/ma_cle_rsa
```

### Pseudo-TTY / expect

GCM utilise `expect` pour envoyer le mot de passe si celui-ci est renseigné.
L'entrée clavier reste disponible (pseudo-TTY interactif via VTE).

### Tunnel SSH (port forwarding)

Voir la section [Tunnels SSH](#14-tunnels-ssh).

---

## 6. Protocole RDP

### Modes d'affichage

| Mode | Condition | Description |
|------|-----------|-------------|
| **XEmbed** (onglet) | Session X11 active | Le bureau Windows s'affiche **dans l'onglet** GCM |
| **Fenêtre externe** | Wayland pur (sans XWayland) | `xfreerdp` ouvre sa propre fenêtre |

GCM détecte automatiquement le mode via `Gdk.Display.get_default()`.

### Paramètres

| Champ | Exemple | Description |
|-------|---------|-------------|
| Hôte | `192.168.1.20` | Adresse du serveur Windows |
| Utilisateur | `DOMAIN\admin` | Le domaine est extrait automatiquement |
| Port | `3389` | Port RDP (défaut 3389) |
| Mot de passe | `****` | Passé via `/p:` à xfreerdp |
| Paramètres supp. | `+clipboard /drive:home,/home/user` | Options xfreerdp directes |

### Options xfreerdp automatiques

GCM ajoute toujours : `/cert:ignore /dynamic-resolution /rfx`

Pour passer des options supplémentaires, utilisez le champ **Paramètres supp.** :

```
+clipboard /sound /drive:partage,/mnt/data
```

### Domaine Windows

Si l'utilisateur est au format `DOMAIN\user` ou `DOMAIN/user`, GCM extrait
automatiquement le domaine et génère `/d:DOMAIN /u:user`.

---

## 7. Protocole VNC

### Binaires supportés (auto-détectés)

1. `vncviewer` (TigerVNC — recommandé)
2. `vinagre` (GNOME — URI `vnc://`)
3. `remmina` (URI `vnc://`)

### Paramètres

| Champ | Exemple | Description |
|-------|---------|-------------|
| Hôte | `192.168.1.30` | Adresse du serveur VNC |
| Port | `5900` | Port VNC (défaut 5900 ; display :1 = 5901) |
| Mot de passe | `****` | Passé en argument ou via l'URI |

### Format de commande selon le binaire

```bash
# vncviewer (TigerVNC)
vncviewer -passwd <(echo "motdepasse") 192.168.1.30:5900

# vinagre / remmina
vinagre vnc://motdepasse@192.168.1.30:5900
```

---

## 8. Protocole SPICE

### Modes de connexion

GCM supporte deux modes pour SPICE :

| Mode | Quand | Description |
|------|-------|--------------|
| **URI directe** | Connexion manuelle (hote:port connus) | `spice://hote?port=5930` passé à `remote-viewer` |
| **Tunnel libvirt** | Import libvirt | `remote-viewer --connect qemu+ssh://user@hv/system vm` — tunnel SSH géré nativement |

Le mode utilisé est détecté automatiquement via le champ **Paramètres supplémentaires** : si la valeur commence par `--connect`, GCM utilise directement `remote-viewer --connect URI vm_name` sans construire d’URI `spice://`.

### Binaires supportés (auto-détectés)

1. `remote-viewer` (virt-viewer — recommandé)
2. `spicec`

### Paramètres (mode URI directe)

| Champ | Exemple | Description |
|-------|---------|-------------|
| Hôte | `192.168.1.40` | Adresse du serveur SPICE |
| Port | `5930` | Port SPICE (défaut 5930) |
| Mot de passe | `****` | Ajouté en paramètre `?password=` |
| Paramètres supp. | `--spice-ca-file=/etc/ssl/certs/ca.crt` | Options `remote-viewer` |

### Format URI (mode direct)

```
spice://192.168.1.40?port=5930&password=motdepasse
```

### Mode tunnel libvirt (import automatique)

Lorsque la VM est importée depuis libvirt, le champ Paramètres supp. contient :
```
--connect qemu+ssh://root@hyperviseur/system nom_vm
```
La commande résultante :
```bash
remote-viewer --connect qemu+ssh://root@hyperviseur/system nom_vm
```
`virt-viewer` établit le tunnel SSH vers l’hyperviseur et récupère le socket SPICE sans exposer le port.

---

## 9. Console Série (RS-232 / RS-485)

### Vue d'ensemble

La console série ouvre un terminal VTE **embarqué** (pas de fenêtre externe).
Tous les paramètres de la liaison série sont configurables via des combos dédiés
dans deux barres d'outils.

### Binaires supportés (auto-détectés)

| Binaire | Priorité | Notes |
|---------|----------|-------|
| `picocom` | 1 (recommandé) | Support complet de tous les paramètres |
| `minicom` | 2 | Interactif, certains flags différents |
| `screen` | 3 | Disponible partout, options limitées |

Installation recommandée :
```bash
sudo apt install picocom
```

### Paramètres de connexion

| Champ | Emplacement | Description |
|-------|-------------|-------------|
| **Port série** | Barre 1, champ texte | Chemin du device : `/dev/ttyUSB0`, `/dev/ttyS0`, etc. |
| **Débit (baud)** | Barre 1, combo | 300 / 1200 / 2400 / 4800 / **9600** / 19200 / 38400 / 57600 / **115200** / 230400 / 460800 / 921600 |
| **Template** | Barre 1, combo | Pré-remplit tous les paramètres (voir ci-dessous) |
| **Bits de données** | Barre 2, combo | 5 / 6 / 7 / **8** |
| **Parité** | Barre 2, combo | **Aucune (N)** / Paire (E) / Impaire (O) |
| **Bits de stop** | Barre 2, combo | **1** / 2 |
| **Contrôle de flux** | Barre 2, combo | **Aucun** / XON-XOFF (soft) / RTS-CTS (hard) / DSR-DTR |
| **Options libres** | Barre 2, champ texte | Paramètres supplémentaires bruts (`--logfile /tmp/serial.log`) |

Les valeurs **en gras** sont les valeurs par défaut (8N1 sans flux = standard industrie).

### Valeur par défaut du device

Si le champ **Port série** est laissé vide, GCM utilise `/dev/ttyUSB0`.

### Commandes générées

Selon le binaire détecté, GCM construit :

**picocom** (recommandé) :
```bash
picocom --baud 9600 --flow n --parity n --databits 8 --stopbits 1 /dev/ttyUSB0
```

**minicom** :
```bash
minicom -b 9600 -D /dev/ttyUSB0 --databits 8 --stopbits 1
# + flags selon flux : (-f on pour XON/XOFF, --rtscts pour RTS/CTS)
```

**screen** :
```bash
screen /dev/ttyUSB0 9600 8n1
```

### Templates constructeurs

La sélection d'un template **pré-remplit automatiquement** tous les combos (débit,
bits de données, parité, bits de stop, contrôle de flux).

| Template | Débit | Données | Parité | Stop | Flux |
|----------|-------|---------|--------|------|------|
| Cisco IOS / IOS-XE / NX-OS | 9 600 | 8 | N | 1 | Aucun |
| HP Comware (H3C) | 9 600 | 8 | N | 1 | Aucun |
| Aruba AOS-S / AOS-CX | 9 600 | 8 | N | 1 | Aucun |
| Juniper JunOS | 9 600 | 8 | N | 1 | Aucun |
| Fortinet FortiOS | 9 600 | 8 | N | 1 | Aucun |
| Palo Alto PAN-OS | 9 600 | 8 | N | 1 | Aucun |
| F5 TMOS | **19 200** | 8 | N | 1 | Aucun |
| Linux / Raspberry Pi | **115 200** | 8 | N | 1 | Aucun |
| Arduino / ESP32 | **115 200** | 8 | N | 1 | Aucun |
| RS-485 Modbus RTU | 9 600 | 8 | N | 1 | Aucun |
| Libre (manuel) | 9 600 | 8 | N | 1 | Aucun |

> **Astuce :** Sélectionnez "Libre (manuel)" pour partir d'une base 9600/8N1 et
> ajuster chaque combo manuellement.

### Droits d'accès au port série

Sous Linux, l'utilisateur doit appartenir au groupe `dialout` (ou `uucp` selon la distro) :

```bash
sudo usermod -aG dialout $USER
# Déconnexion/reconnexion requise
```

Vérifier l'appartenance :
```bash
groups | grep dialout
```

### Options libres

Le champ **Options libres** permet de passer des paramètres supplémentaires directement
au binaire, sans passer par les combos. Exemples :

```
# picocom
--logfile /tmp/serial.log --imap crlf

# screen
-L                        # journalisation dans screenlog.0
```

---

## 10. Protocole Telnet

### Paramètres

| Champ | Exemple | Description |
|-------|---------|-------------|
| Hôte | `192.168.1.1` | Adresse du équipement |
| Port | `23` | Port Telnet (défaut 23) |
| Utilisateur | `admin` | Envoyé via `expect` |
| Mot de passe | `****` | Envoyé via `expect` |

### Notes

Telnet transmet les données **en clair**. Réservez ce protocole aux équipements
anciens qui ne supportent pas SSH (switchs/routeurs legacy), sur un réseau de
gestion isolé.

---

## 11. Terminal local

Le protocole **local** ouvre un terminal shell sur la machine locale, sans connexion réseau.

- **Hôte** : ignoré
- **Utilisateur** : ignoré
- Shell utilisé : `$SHELL` ou `/bin/bash`

Utile pour avoir un terminal rapide sans quitter GCM.

---

## 12. Import libvirt / KVM

### Présentation

GCM interroge les hyperviseurs KVM/QEMU via SSH et importe automatiquement
les VMs découvertes sous forme de connexions GCM. L'import fonctionne en
**deux phases** : scan (découverte) + prévisualisation (sélection avant import).

### Accès

**Menu → Fichier → Importer depuis libvirt…**

### Phase 1 — Paramètres du scan

```
┌────────────────────────────────────────────────────────────────────────┐
│ URI libvirt détectées (virt-manager / dconf) :                         │
│ [☑] qemu+ssh://root@192.168.105.41/system                              │
│ [☑] qemu+ssh://root@192.168.105.42/system                              │
│                                                                         │
│ User SSH hyperviseur : [root     ]                                      │
│                                                                         │
│ Types de connexion à importer :                                         │
│   [☑] SSH  (ProxyJump -J ou shell HV + -t ssh user@vm)                 │
│   [☑] SPICE  (virt-viewer --connect libvirt URI)                       │
│   [☑] RDP  (port 3389 sondé depuis l'HV — nc/nmap)                    │
│                                                                         │
│ Log : [zone de log en temps réel]                                      │
│ Progression : [████████████████████          ] 1/2                     │
│                                              [🔍 Scanner]               │
└────────────────────────────────────────────────────────────────────────┘
```

### Phase 2 — Tableau de prévisualisation

Après le scan, un tableau apparaît avec toutes les connexions trouvées.

- Lignes **déjà présentes** dans GCM : grisées, case décochée par défaut
- **Nouvelles** lignes : case cochée par défaut
- Case **Écraser existants** : si cochée, les connexions existantes sont remplacées
- Boutons **✓ Tout cocher** / **✗ Tout décocher**
- Le tableau est scrollable (>250 lignes gérées)

### URIs supportées

| Type | Exemple |
|------|---------|
| Local | `qemu:///system` (ignoré — nécessite SSH) |
| SSH | `qemu+ssh://root@192.168.1.1/system` |
| SSH + port non-standard | `qemu+ssh://root@192.168.1.1:542/system` |

Les URIs configurées dans **virt-manager** sont pré-remplies automatiquement (lecture dconf).

### Stratégie de connexion par protocole

| Protocole | Comportement |
|-----------|-------------|
| **SSH** (IP connue) | `ssh -J user@hv:port user@ip_vm` — ProxyJump transparent |
| **SSH** (IP inconnue) | Shell HV puis `-t ssh user@vm_name` |
| **SPICE** | `remote-viewer --connect qemu+ssh://user@hv[:port]/system vm_name` |
| **RDP** | Uniquement si port 3389 confirmé ouvert (nc/nmap depuis l'HV) |

### Résolution IP

Pour chaque VM, GCM tente dans l'ordre :
1. `virsh domifaddr vm --source agent` (guest-agent)
2. `virsh domifaddr vm --source arp` (table ARP)
3. Leases DHCP (`virsh net-dhcp-leases`)
4. Scan nmap (`-sn`) sur les sous-réseaux de l'HV

### Convention de nommage des groupes

```
prod_web-01  →  groupe prod    / hote web-01  (sous-groupe prod/ssh, prod/rdp...)
dev-mysql    →  groupe dev     / hote mysql
win-dc       →  groupe win     / hote dc
standalone   →  (racine)       / hote standalone
```

Organisation par protocole : chaque protocole importé crée un sous-groupe `groupe/ssh`, `groupe/spice`, `groupe/rdp`, `groupe/vnc`.

---

## 13. Import Proxmox

### Présentation

GCM interroge les hyperviseurs Proxmox via SSH et importe les VMs via les outils
nativement Proxmox (`qm`, `pvesh`). Fonctionne indépendamment de libvirt.

### Accès

**Menu → Fichier → Importer depuis Proxmox…**

### Phase 1 — Paramètres du scan

```
┌────────────────────────────────────────────────────────────────────────┐
│ URI hyperviseurs Proxmox :                                              │
│ [+] qemu+ssh://root@192.168.105.41/system                              │
│ [+] qemu+ssh://root@192.168.105.42/system                              │
│                                                                        │
│ User SSH VMs : [ubuntu   ]                                             │
│                                                                        │
│ Types à importer :                                                     │
│   [☑] SSH   [☑] SPICE (qxl requis)   [☑] RDP   [ ] VNC               │
│                                                                        │
│ Log : [zone de log en temps réel]                                      │
│ Progression : [████████████████████          ] 1/2                     │
│                                              [🔍 Scanner]               │
└────────────────────────────────────────────────────────────────────────┘
```

### Stratégie de connexion par protocole

| Protocole | Comportement |
|-----------|--------------|
| **SSH** (IP connue) | `ssh -J root@hv:port user@ip_vm` — ProxyJump |
| **SSH** (IP inconnue) | Shell HV puis `-t ssh user@vm_name` |
| **SPICE** | `pvesh create /nodes/NODE/qemu/VMID/spiceproxy` → ticket `.vv` |
| **RDP** | Uniquement si port 3389 ouvert (nc/nmap depuis l'HV) |
| **VNC** | Uniquement si port 5900 ouvert (nc/nmap depuis l'HV) |

### Résolution IP (pipeline 4 niveaux)

Pour chaque VM, GCM tente dans l'ordre :
1. **QGA** : `qm guest cmd {vmid} network-get-interfaces` (guest-agent actif)
2. **ipconfig0** : `qm config {vmid} | grep ipconfig` (IP cloud-init ou statique)
3. **ARP filtré par MAC** : MAC récupérée depuis `qm config`, puis `ip neigh show` filtré
4. **nmap ping scan** : scan des sous-réseaux de l'HV, matching par MAC VM

### Prérequis SPICE Proxmox

- La VM doit avoir `vga: qxl` dans sa configuration (`qm config VMID | grep vga`)
- L'utilisateur SSH doit avoir accès à `pvesh` sur le noeud Proxmox
- `virt-viewer` / `remote-viewer` doit être installé sur la machine cliente

### Convention de nommage des groupes

Identique à libvirt : `groupe/ssh`, `groupe/spice`, `groupe/rdp`, `groupe/vnc`.

---

## 14. Mode cluster (multi-hôtes)

Le mode cluster permet d'envoyer des commandes simultanément à plusieurs hôtes SSH.

### Activer le mode cluster

1. Maintenir **Ctrl** et double-cliquer sur plusieurs hôtes de l'arbre
   _ou_ sélectionner les hôtes puis **Connexion → Ouvrir en cluster**
2. Une barre de saisie apparaît sous les onglets
3. Tapez une commande puis **Entrée** → exécution sur tous les onglets cluster

### Notes

- Chaque hôte garde son propre onglet (lecture individuelle des sorties)
- La saisie cluster n'affecte que les onglets marqués "cluster"
- Utile pour des déploiements rapides ou des vérifications d'état simultanées

---

## 15. Tunnels SSH

### Configurer un tunnel

Dans le formulaire d'édition de l'hôte, champ **Tunnel** :

```
PORT_LOCAL:HOTE_DISTANT:PORT_DISTANT
```

Exemples :

| Syntaxe | Effet |
|---------|-------|
| `8080:serveur-interne:80` | Accès à `localhost:8080` → `serveur-interne:80` |
| `5432:db-prod:5432` | PostgreSQL distant accessible en local |
| `3389:win-srv:3389` | Bureau Windows via le jump host |

### Fonctionnement

GCM établit d'abord la session SSH, puis configure le forwarding de port avec
`ssh -L PORT_LOCAL:HOTE_DISTANT:PORT_DISTANT`. Le tunnel reste actif tant que
l'onglet SSH est ouvert.

---

## 16. Chiffrement des mots de passe

### Algorithme

| Version config | Algorithme | Notes |
|----------------|-----------|-------|
| `VERSION = 1` | **AES (pyAES)** | Utilisé pour toutes les nouvelles configs |
| `VERSION = 0` | XOR + base64 (legacy) | Rétrocompatibilité avec anciennes configs |

GCM détecte automatiquement la version lors du chargement et migre vers AES
à la prochaine sauvegarde.

### Clé de chiffrement

La clé est dérivée du **mot de passe maître** saisi au démarrage (si configuré),
ou d'une clé interne fixe. Pour une sécurité maximale, utilisez un mot de passe
maître via **Édition → Préférences → Sécurité**.

### Fichier de configuration

```
~/.config/gnome-connection-manager/config.ini
```

Les mots de passe y sont stockés chiffrés — ne partagez jamais ce fichier
sans l'avoir purgé (utilisez l'export avec redaction).

---

## 17. Personnalisation de l'apparence

### Thème GTK

Depuis v1.3.3, GCM suit automatiquement le thème GTK du bureau :

1. Lecture de `gsettings get org.gnome.desktop.interface gtk-theme` (GNOME, XFCE, MATE)
2. Fallback : `~/.config/gtk-3.0/settings.ini`
3. Si `gsettings get org.gnome.desktop.interface color-scheme` retourne `prefer-dark`, le mode sombre GTK est activé

Pour forcer un thème en ligne de commande :
```bash
GTK_THEME=Adwaita:dark ./gnome_connection_manager.py
GTK_THEME=Yaru        ./gnome_connection_manager.py
```

### Police du terminal

**Édition → Préférences → Police** : sélecteur de polices Pango (ex. `Monospace 11`).

### Couleurs

- Couleur du texte, du fond, et du curseur configurables via les préférences.
- Le thème GTK du système est respecté par défaut.

### Transparence

Certaines versions de VTE supportent la transparence du terminal. Activable via
**Édition → Préférences → Transparence**.

### Taille de fenêtre

La taille et la position de la fenêtre principale sont mémorisées à la fermeture.

---

## 18. Langues / Internationalisation

GCM détecte automatiquement la langue via la variable `LANG` du système.

### Langues disponibles

| Code | Langue |
|------|--------|
| `ar` | العربية |
| `cs` | Čeština |
| `de` | Deutsch |
| `en` | English |
| `fr` | Français |
| `it` | Italiano |
| `ja` | 日本語 |
| `ko` | 한국어 |
| `nb` | Norsk Bokmål |
| `nl` | Nederlands |
| `pl` | Polski |
| `pt` | Português |
| `ru` | Русский |
| `sv` | Svenska |
| `tr` | Türkçe |
| `uk` | Українська |

### Forcer une langue

```bash
LANG=en_US.UTF-8 ./gnome_connection_manager.py
LANG=de_DE.UTF-8 ./gnome_connection_manager.py
LANG=ja_JP.UTF-8 ./gnome_connection_manager.py
```

---

## 19. Sauvegarde et restauration de la configuration

### Emplacement du fichier

```
~/.config/gnome-connection-manager/config.ini
```

### Sauvegarde manuelle

```bash
cp ~/.config/gnome-connection-manager/config.ini ~/gcm-backup-$(date +%Y%m%d).ini
```

### Migration vers un autre poste

```bash
# Sur la source
cp ~/.config/gnome-connection-manager/config.ini /tmp/gcm-export.ini

# Sur la cible
mkdir -p ~/.config/gnome-connection-manager/
cp /tmp/gcm-export.ini ~/.config/gnome-connection-manager/config.ini
```

> **Attention :** Le fichier contient les mots de passe chiffrés avec la clé
> interne de GCM. Il est conseillé de régénérer les mots de passe après
> migration si la sécurité est critique.

### Export / Import via le menu

- **Fichier → Exporter…** : choisir un emplacement de sauvegarde
- **Fichier → Importer…** : fusionner une configuration externe

---

## 20. Raccourcis clavier

| Raccourci | Action |
|-----------|--------|
| `Ctrl+T` | Nouvel onglet (connexion rapide) |
| `Ctrl+W` | Fermer l'onglet actif |
| `Ctrl+Tab` | Onglet suivant |
| `Ctrl+Shift+Tab` | Onglet précédent |
| `Ctrl+C` | Copier la sélection terminal |
| `Ctrl+V` | Coller dans le terminal |
| `Ctrl+Shift+C` | Copier (alternative) |
| `Ctrl+Shift+V` | Coller (alternative) |
| `F11` | Plein écran |
| `Ctrl+Q` | Quitter GCM |

---

## 21. Dépannage

### Le port série n'est pas accessible

```bash
# Vérifier que le device existe
ls -la /dev/ttyUSB* /dev/ttyS*

# Vérifier les droits
groups | grep dialout
# Si absent :
sudo usermod -aG dialout $USER
# Puis se déconnecter et se reconnecter
```

### picocom : "FATAL: cannot open /dev/ttyUSB0: Permission denied"

Le groupe `dialout` n'est pas activé pour la session courante. Redémarrez la
session utilisateur ou lancez GCM avec `sudo` (déconseillé en production).

### RDP : fenêtre noire ou onglet vide

- Vérifiez que `xfreerdp` est installé : `which xfreerdp`
- Sur Wayland pur (sans XWayland), GCM utilise automatiquement la fenêtre externe.
  Si XWayland n'est pas disponible, installez `xwayland` ou activez-le dans votre
  compositeur Wayland.

### VNC : "unable to connect"

```bash
# Tester la connectivité manuellement
vncviewer 192.168.1.30:5900
```

### SSH : "expect: spawn id exp4 not open"

Le mot de passe saisi est incorrect, ou l'hôte demande une confirmation de clé
(`yes/no`). Connectez-vous manuellement une première fois pour accepter la clé :

```bash
ssh user@hôte
# Répondre "yes" à la question de fingerprint
```

### Aucun onglet ne s'ouvre

Vérifiez que VTE est correctement installé :

```bash
python3 -c "import gi; gi.require_version('Vte','2.91'); from gi.repository import Vte; print(Vte.MAJOR_VERSION)"
```

Résultat attendu : `0` (VTE 0.x.x). Si erreur, installer :
```bash
sudo apt install gir1.2-vte-2.91
```

### Erreur "No module named 'gi'"

```bash
sudo apt install python3-gi
```

---

## Annexe — Valeurs de référence série

### Débits courants

| Débit | Usage typique |
|-------|--------------|
| 300 | Modems historiques |
| 1 200 | Terminaux anciens |
| 9 600 | **Équipements réseau (défaut industrie)** |
| 19 200 | F5 TMOS, certains équipements HP |
| 38 400 | GSM/GPRS modems |
| 57 600 | GPS, certains PLC |
| 115 200 | **Linux/Raspberry Pi, Arduino, ESP32** |
| 230 400 | Hautes performances |
| 460 800 | Hautes performances |
| 921 600 | Hautes performances |

### Format de trame : Données-Parité-Stop

| Format | Signification | Usage |
|--------|--------------|-------|
| **8N1** | 8 bits, pas de parité, 1 stop | **Standard universel** |
| 7E1 | 7 bits, parité paire, 1 stop | Protocoles industriels anciens |
| 7O1 | 7 bits, parité impaire, 1 stop | Rare |
| 8E1 | 8 bits, parité paire, 1 stop | Certains modems |

### Contrôle de flux

| Code | Nom | Mécanisme |
|------|-----|-----------|
| `n` | **Aucun** | Pas de contrôle (le plus courant pour équipements réseau) |
| `x` | XON/XOFF | Logiciel (caractères ASCII 17/19) |
| `h` | RTS/CTS | Matériel (broches RTS + CTS du câble) |
| `d` | DSR/DTR | Matériel alternatif (broches DSR + DTR) |

---

## 22. Outils CLI (`tools/`)

Le répertoire `tools/` contient des scripts autonomes pour la gestion des
hyperviseurs libvirt en dehors de l'interface GCM.

### `tools/libvirt_inventory.py` — Inventaire complet

Interroge les hyperviseurs KVM/QEMU et génère un inventaire complet : IP, OS,
vCPUs, RAM, ports SPICE/VNC/RDP. Exporte en JSON, CSV, Ansible INI et YAML.

#### Prérequis

```bash
pip install paramiko
```

#### Utilisation

```bash
# Inventaire rapide (sans scan nmap ni détection OS)
python3 tools/libvirt_inventory.py --no-nmap --no-os

# Inventaire complet avec sondage ports
python3 tools/libvirt_inventory.py \
  --detect-ports \
  --output-json inventory.json \
  --output-csv  inventory.csv \
  --ansible-ini inventory.ini \
  --ansible-yaml inventory.yml

# Surcharge des URIs (sans dconf)
python3 tools/libvirt_inventory.py \
  --uris qemu+ssh://root@192.168.105.41/system \
         qemu+ssh://root@192.168.105.42/system \
  --no-os --no-csv

# Connexion avec mot de passe (préférer les clés SSH)
python3 tools/libvirt_inventory.py --ssh-password MonMotDePasse
```

#### Options principales

| Option | Description |
|--------|-------------|
| `--uris URI...` | Surcharge les URIs dconf |
| `--no-os` | Désactive la détection d'OS (plus rapide) |
| `--no-nmap` | Désactive le scan nmap |
| `--detect-ports` | Sonde SPICE/VNC/RDP depuis l'HV |
| `--vm-user USER` | Utilisateur SSH pour les VMs (défaut : root) |
| `--ssh-password PASS` | Mot de passe SSH pour les HVs |
| `--ssh-timeout SEC` | Délai de connexion SSH (défaut : 10s) |
| `--no-csv` | Désactive l'export CSV |
| `--no-ansible` | Désactive les exports Ansible |
| `--no-report` | Pas d'affichage terminal |

#### Exports générés

| Fichier | Format | Description |
|---------|--------|-------------|
| `inventory.json` | JSON | Inventaire complet (toutes les données) |
| `inventory.csv` | CSV | Une ligne par VM × interface |
| `inventory.ini` | Ansible INI | Groupes : `vms_running`, `vms_stopped`, `os_linux`, `os_windows`, `rdp`, `hypervisor_*` |
| `inventory.yml` | Ansible YAML | Compatible `ansible-inventory --list` |

---

### `tools/ssh_deploy.py` — Déploiement de clés SSH

Génère des clés SSH (RSA-4096 + Ed25519) sur les hyperviseurs et les déploie
automatiquement vers toutes les VMs running via `ssh-copy-id`.

#### Prérequis

```bash
pip install paramiko
# Sur les hyperviseurs : apt install sshpass (ou expect)
```

#### Workflow

1. Connexion SSH à chaque hyperviseur (via clé ou mot de passe)
2. Génération des clés RSA-4096 et Ed25519 si absentes (`~/.ssh/`)
3. Pour chaque VM running avec IP connue :
   - Test de connexion par clé depuis l'HV → VM
   - Si échec : `ssh-copy-id` avec mot de passe (mis en cache par réseau)
   - Re-test après déploiement
4. Rapport JSON `ssh_deploy_report.json`

#### Utilisation

```bash
# Utilise inventory.json généré par libvirt_inventory.py
python3 tools/ssh_deploy.py

# Options
python3 tools/ssh_deploy.py \
  --inventory /chemin/inventory.json \
  --vm-user ubuntu \
  --uris qemu+ssh://root@192.168.105.41/system
```

---

*Documentation GCM v1.3.3 — [github.com/MathildeDec/gnome-connection-manager](https://github.com/MathildeDec/gnome-connection-manager)*

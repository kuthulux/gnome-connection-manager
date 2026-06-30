# Conversation : Libvirt Inventory & SSH Deploy

Date : 2026-06-08

---

## Résumé de la conversation

### Contexte
Gestion des hyperviseurs KVM/libvirt via virt-manager. Besoin d'un inventaire automatisé des VMs et d'un déploiement de clés SSH.

---

## Questions / Réponses clés

### 1. Où sont stockées les connexions virt-manager ?
- **Pas** dans `~/.config/virt-manager/` (dossier absent)
- Stockées dans **dconf/GSettings** :
  ```bash
  dconf read /org/virt-manager/virt-manager/connections/uris
  gsettings get org.virt-manager.virt-manager.connections uris
  dconf dump /org/virt-manager/       # tout le schéma
  dconf dump /org/virt-manager/ > virt-manager-backup.conf  # export
  dconf load /org/virt-manager/ < virt-manager-backup.conf  # restaurer
  ```

---

## Scripts produits

### `libvirt_inventory.py`
**Rôle** : Inventaire complet des VMs libvirt avec résolution MAC → IP.

**Fonctionnement** :
1. Lit les URIs de connexion depuis dconf virt-manager
2. Parse les URIs (`qemu+ssh://user@host:port/system`)
3. Se connecte en SSH aux hyperviseurs via paramiko
4. Liste toutes les VMs (running + stopped) via `virsh list --all`
5. Extrait les MAC adresses via `virsh dumpxml <vm>`
6. Résolution IP en 5 niveaux :
   - `virsh domifaddr --source agent` (qemu-guest-agent)
   - `virsh domifaddr --source arp`
   - **nmap -sn/-sP** sur tous les sous-réseaux de l'hyperviseur (ajout v2)
   - Leases DHCP libvirt (`virsh net-dhcp-leases`)
   - Table ARP noyau (`ip neigh`) — fraîche après nmap
7. Export JSON → `inventory.json`

**Dépendances** : `pip install paramiko`, `nmap` sur les hyperviseurs

**Usage** :
```bash
python3 libvirt_inventory.py
```

**Points techniques** :
- Détection automatique version nmap → flag `-sP` (v5) ou `-sn` (v6+)
- Sortie XML nmap (`-oX -`) parsée par regex pour extraire MAC→IP
- Calcul de l'adresse réseau en Python pur (sans dépendance ipaddress)
- Exclut loopback (127.x) et lien-local (169.254.x) des sous-réseaux scannés
- Table fusionnée : `{**arp, **dhcp, **nmap_table}` (priorité nmap)

---

### `ssh_deploy.py`
**Rôle** : Génère les clés SSH sur les hyperviseurs et les déploie vers toutes les VMs.

**Fonctionnement** :
1. Lit les URIs depuis dconf (ou `--uris` en argument)
2. Charge `inventory.json` (produit par `libvirt_inventory.py`)
3. Pour chaque hyperviseur :
   - Génère RSA-4096 (`/root/.ssh/id_rsa`) si absente
   - Génère Ed25519 (`/root/.ssh/id_ed25519`) si absente
4. Pour chaque VM running avec IP connue :
   - **Test SSH par clé** (`BatchMode=yes`) : si OK → suivante
   - Si échec → demande mot de passe (cache par user + /24)
   - **ssh-copy-id** via `sshpass` (priorité) ou `expect` (fallback)
   - **Re-test par clé** après copy-id → validation
   - Si tout échoue → log erreur, passe à la suivante
5. Export rapport → `ssh_deploy_report.json`

**Dépendances** : `pip install paramiko`, `sshpass` ou `expect` sur les hyperviseurs

**Usage** :
```bash
python3 ssh_deploy.py --inventory inventory.json --vm-user root
python3 ssh_deploy.py --vm-user ubuntu --uris qemu+ssh://root@proxmox01/system
```

**Points techniques** :
- Cache mot de passe par `(user, /24)` : réutilisation automatique sur le même sous-réseau
- `sshpass` en priorité, `expect` en fallback, message d'erreur clair si aucun
- Rapport JSON final : état de chaque VM (ssh_key_ok, ssh_copy_id_attempted, error)

---

## Workflow complet

```bash
# 1. Inventaire (génère inventory.json)
python3 libvirt_inventory.py

# 2. Déploiement clés SSH
python3 ssh_deploy.py --inventory inventory.json --vm-user root
```

---

## Fichiers dans ce dossier Drive

| Fichier | Description | Version |
|---|---|---|
| `libvirt_inventory.py` | Inventaire VMs libvirt + résolution IP | v2 (avec nmap) |
| `ssh_deploy.py` | Déploiement clés SSH vers VMs | v1 |
| `claude.md` | Ce fichier — résumé de conversation | — |

---

## Prérequis

**Sur la machine locale** :
```bash
pip install paramiko
```

**Sur les hyperviseurs** :
```bash
apt install nmap sshpass   # Debian/Ubuntu/Proxmox
dnf install nmap sshpass   # Rocky/RHEL/AlmaLinux
```

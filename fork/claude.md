# Conversation : Libvirt Inventory & SSH Deploy

Date : 2026-06-08
Mise à jour : 2026-06-09

---

## Résumé de la conversation

### Contexte
Gestion des hyperviseurs KVM/libvirt via virt-manager. Besoin d'un inventaire automatisé des VMs, résolution d'IP et déploiement de clés SSH.

---

## Questions / Réponses clés

### 1. Où sont stockées les connexions virt-manager ?
- **Pas** dans `~/.config/virt-manager/` (dossier absent sur le système de Mathilde)
- Stockées dans **dconf/GSettings** :
  ```bash
  dconf read /org/virt-manager/virt-manager/connections/uris
  gsettings get org.virt-manager.virt-manager.connections uris
  dconf dump /org/virt-manager/
  dconf dump /org/virt-manager/ > virt-manager-backup.conf
  dconf load /org/virt-manager/ < virt-manager-backup.conf
  ```

### 2. Amélioration ARP avec nmap
- Scan `nmap -sn/-sP` sur tous les sous-réseaux de l'hyperviseur
- Sortie XML `-oX -` parsée pour extraire MAC→IP
- Table fusionnée : `{**arp, **dhcp, **nmap_table}` (priorité nmap)
- Détection automatique version nmap → flag `-sP` (v5) ou `-sn` (v6+)

### 3. Détection OS des VMs
Trois méthodes en cascade (priorité SSH > agent > XML) :
1. **XML `virsh dumpxml`** : arch, type, osinfo variant (metadata libosinfo)
2. **`virsh guestinfo --os`** : via qemu-guest-agent (OS réel, kernel, hostname)
3. **SSH direct** : lit `/etc/os-release` + `uname -r` + `hostname` depuis l'hyperviseur

### 4. Sauvegarde Drive
- Chaque fichier rangé dans le dossier Drive du nom de la conversation
- Fichier `claude.md` maintenu avec résumé de tous les échanges

---

## Scripts produits

### `libvirt_inventory.py` — v3
**Rôle** : Inventaire complet des VMs libvirt (MAC, IP, OS).

**Fonctionnement** :
1. Lit les URIs depuis dconf virt-manager
2. SSH sur chaque hyperviseur (paramiko, clé SSH)
3. `virsh list --all` → liste VMs
4. `virsh dumpxml` → MACs + XML OS
5. Résolution IP (5 niveaux) :
   - `virsh domifaddr --source agent`
   - `virsh domifaddr --source arp`
   - nmap -sn sur tous les sous-réseaux
   - DHCP leases libvirt
   - Table ARP noyau
6. Détection OS (3 niveaux) :
   - XML libvirt (osinfo variant, arch, machine)
   - qemu-guest-agent (`virsh guestinfo --os`)
   - SSH direct sur la VM (`/etc/os-release`, `uname -r`, `hostname`)
7. Export `inventory.json`

**Structure JSON produite** :
```json
{
  "host": "proxmox01",
  "uri": "qemu+ssh://root@proxmox01/system",
  "vms": [{
    "name": "vm-debian12",
    "uuid": "...",
    "state": "running",
    "os": {
      "name": "Debian GNU/Linux 12 (bookworm)",
      "version": "12",
      "kernel": "6.1.0-18-amd64",
      "hostname": "vm-debian12",
      "arch": "x86_64",
      "sources": {
        "libvirt": {"type": "hvm", "arch": "x86_64", "machine": "pc-i440fx-8.2", "variant": "debian12"},
        "agent":   {"name": "Debian GNU/Linux 12", "version": "12", "kernel": "6.1.0-18-amd64"},
        "ssh":     {"name": "Debian GNU/Linux 12 (bookworm)", "version": "12", "kernel": "6.1.0-18-amd64"}
      }
    },
    "interfaces": [{"mac": "52:54:00:xx:xx:xx", "ip": "192.168.1.100", "network": "default"}]
  }]
}
```

**Usage** :
```bash
python3 libvirt_inventory.py
```

---

### `ssh_deploy.py` — v1
**Rôle** : Génère les clés SSH sur les hyperviseurs et les déploie vers les VMs.

**Fonctionnement** :
1. Lit URIs depuis dconf
2. Charge `inventory.json`
3. Pour chaque hyperviseur :
   - Génère RSA-4096 (`/root/.ssh/id_rsa`) si absente
   - Génère Ed25519 (`/root/.ssh/id_ed25519`) si absente
4. Pour chaque VM running avec IP :
   - Test SSH par clé (`BatchMode=yes`) → si OK suivante
   - Sinon : demande mdp (cache par `user + /24`)
   - `sshpass ssh-copy-id` (ou `expect` en fallback)
   - Re-test par clé → validation
5. Export `ssh_deploy_report.json`

**Usage** :
```bash
python3 ssh_deploy.py --inventory inventory.json --vm-user root
python3 ssh_deploy.py --vm-user ubuntu --uris qemu+ssh://root@proxmox01/system
```

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
| `libvirt_inventory.py` | Inventaire VMs libvirt + résolution IP + détection OS | v3 |
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
apt install nmap sshpass          # Debian/Ubuntu/Proxmox
dnf install nmap sshpass          # Rocky/RHEL/AlmaLinux
# Optionnel pour détection OS :
apt install qemu-guest-agent      # sur les VMs
```

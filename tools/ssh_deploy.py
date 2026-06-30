#!/usr/bin/env python3
"""
ssh_deploy.py
Pour chaque hyperviseur libvirt (lu depuis dconf virt-manager) :
  1. Génère les clés RSA-4096 et Ed25519 sur l'hyperviseur si absentes
  2. Pour chaque VM running avec une IP connue :
     a. Tente une connexion SSH par clé depuis l'hyperviseur → VM
     b. Si échec : tente ssh-copy-id avec mot de passe (mémorisé par IP/user)
     c. Si ssh-copy-id OK : reteste la connexion par clé
     d. Si tout échoue : passe à la suivante

Dépendances : pip install paramiko
"""

import getpass
import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from urllib.parse import urlparse

try:
    import paramiko
except ImportError:
    print("Dépendance manquante : pip install paramiko")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


@dataclass
class VMTarget:
    """Cible VM pour déploiement de clé SSH."""

    name: str
    ip: str
    user: str = "root"
    ssh_key_ok: bool = False
    ssh_copy_id_ok: bool = False
    error: str | None = None


@dataclass
class Hypervisor:
    """Hyperviseur et résultats de déploiement de ses VMs."""

    uri: str
    host: str
    user: str
    port: int
    transport: str
    vm_targets: list[VMTarget] = field(default_factory=list)


def get_libvirt_uris():
    """Lit les URIs libvirt depuis dconf.

    Returns:
        list[str]: URIs trouvées, ou liste vide.
    """
    try:
        result = subprocess.run(
            ["dconf", "read", "/org/virt-manager/virt-manager/connections/uris"],
            capture_output=True,
            text=True,
            check=True,
        )
        raw = result.stdout.strip()
        if not raw or raw == "@as []":
            return []
        return re.findall(r"'([^']+)'", raw)
    except Exception as e:
        log.error(f"dconf error: {e}")
        return []


def parse_libvirt_uri(uri):
    """Convertit une URI libvirt en objet Hypervisor.

    Args:
        uri (str): URI libvirt source.

    Returns:
        Hypervisor: Hyperviseur parsé.
    """
    parsed = urlparse(uri)
    scheme = parsed.scheme
    transport = scheme.split("+")[1] if "+" in scheme else ("tcp" if parsed.hostname else "local")
    return Hypervisor(
        uri=uri,
        host=parsed.hostname or "localhost",
        user=parsed.username or "",
        port=parsed.port or 22,
        transport=transport,
    )


def ssh_connect(host, user, port=22, password=None, timeout=10):
    """Établit une connexion SSH vers un hôte.

    Args:
        host (str): Adresse de l'hôte.
        user (str): Utilisateur SSH.
        port (int, optional): Port SSH. Defaults to 22.
        password (str | None, optional): Mot de passe SSH. Defaults to None.
        timeout (int, optional): Timeout de connexion en secondes. Defaults to 10.

    Returns:
        paramiko.SSHClient | None: Client connecté ou None.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs = dict(hostname=host, port=port, timeout=timeout, look_for_keys=True, allow_agent=True)
    if user:
        kwargs["username"] = user
    if password:
        kwargs.update(password=password, look_for_keys=False, allow_agent=False)
    try:
        client.connect(**kwargs)
        return client
    except Exception as e:
        log.debug(f"Connexion échouée {host}: {e}")
        return None


def ssh_run(client, cmd, timeout=30):
    """Exécute une commande SSH et retourne code, stdout, stderr.

    Args:
        client (paramiko.SSHClient): Client SSH connecté.
        cmd (str): Commande shell.
        timeout (int, optional): Timeout d'exécution. Defaults to 30.

    Returns:
        tuple[int, str, str]: Code de retour, stdout, stderr.
    """
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    rc = stdout.channel.recv_exit_status()
    return (
        rc,
        stdout.read().decode(errors="replace").strip(),
        stderr.read().decode(errors="replace").strip(),
    )


KEY_TYPES = [
    (
        "rsa",
        "/root/.ssh/id_rsa",
        "ssh-keygen -t rsa -b 4096 -N '' -f /root/.ssh/id_rsa",
    ),
    (
        "ed25519",
        "/root/.ssh/id_ed25519",
        "ssh-keygen -t ed25519 -N '' -f /root/.ssh/id_ed25519",
    ),
]


def ensure_ssh_keys(client, hv_host):
    """Vérifie/crée les clés SSH de l'hyperviseur et retourne les clés publiques.

    Args:
        client (paramiko.SSHClient): Client SSH hyperviseur.
        hv_host (str): Nom/IP de l'hyperviseur (log).

    Returns:
        list[str]: Contenus des clés publiques disponibles.
    """
    ssh_run(client, "mkdir -p /root/.ssh && chmod 700 /root/.ssh")
    pubkeys = []
    for ktype, privpath, keygen_cmd in KEY_TYPES:
        _, out, _ = ssh_run(client, f"test -f {privpath} && echo EXISTS || echo MISSING")
        if "MISSING" in out:
            log.info(f"  [{hv_host}] Génération clé {ktype}…")
            rc, _, err = ssh_run(client, keygen_cmd)
            if rc != 0:
                log.error(f"  Échec {ktype}: {err}")
                continue
            log.info(f"  [{hv_host}] Clé {ktype} générée.")
        else:
            log.info(f"  [{hv_host}] Clé {ktype} déjà présente.")
        _, pub, _ = ssh_run(client, f"cat {privpath}.pub 2>/dev/null")
        if pub:
            pubkeys.append(pub)
    return pubkeys


def load_inventory(path="inventory.json"):
    """Charge l'inventaire JSON généré en amont.

    Args:
        path (str, optional): Chemin de l'inventaire JSON. Defaults to "inventory.json".

    Returns:
        list[dict]: Contenu d'inventaire.
    """
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        log.error(f"{path} introuvable. Lancez d'abord libvirt_inventory.py")
        sys.exit(1)


def get_vm_targets(inventory, hv_host, default_user="root"):
    """Extrait les VMs running avec IP pour un hyperviseur donné.

    Args:
        inventory (list[dict]): Inventaire complet.
        hv_host (str): Hôte hyperviseur à filtrer.
        default_user (str, optional): Utilisateur SSH VM. Defaults to "root".

    Returns:
        list[VMTarget]: Cibles VM prêtes au déploiement.
    """
    targets = []
    for hv in inventory:
        if hv["host"] != hv_host:
            continue
        for vm in hv["vms"]:
            if vm["state"] != "running":
                continue
            for iface in vm["interfaces"]:
                ip = iface.get("ip")
                if ip:
                    targets.append(VMTarget(name=vm["name"], ip=ip, user=default_user))
                    break
    return targets


_password_cache: dict[tuple[str, str], str] = {}


def _subnet_key(ip, user):
    return (user, ".".join(ip.split(".")[:3]))


def get_password(ip, user):
    """Récupère/cache le mot de passe SSH pour une cible.

    Args:
        ip (str): IP de la VM cible.
        user (str): Utilisateur SSH.

    Returns:
        str | None: Mot de passe saisi ou None si ignoré.
    """
    exact = (user, ip)
    if exact in _password_cache:
        return _password_cache[exact]
    sk = _subnet_key(ip, user)
    if sk in _password_cache:
        log.info(f"    Mot de passe réutilisé (réseau {sk[1]}.0/24)")
        _password_cache[exact] = _password_cache[sk]
        return _password_cache[exact]
    print(f"\n  Mot de passe SSH requis pour {user}@{ip}")
    pwd = getpass.getpass("  Entrez le mot de passe (Entrée pour ignorer) : ")
    if not pwd:
        return None
    _password_cache[exact] = pwd
    _password_cache[sk] = pwd
    return pwd


def test_ssh_key_from_hypervisor(hv_client, vm):
    """Teste une connexion SSH par clé de l'hyperviseur vers la VM.

    Args:
        hv_client (paramiko.SSHClient): Client SSH hyperviseur.
        vm (VMTarget): VM cible.

    Returns:
        bool: True si la connexion par clé fonctionne.
    """
    cmd = f"ssh -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=5 {vm.user}@{vm.ip} echo OK 2>/dev/null"
    rc, out, _ = ssh_run(hv_client, cmd, timeout=15)
    return rc == 0 and "OK" in out


def _shell_quote(s):
    return "'" + s.replace("'", "'\\''") + "'"


def copy_id_from_hypervisor(hv_client, vm, password):
    """Déploie la clé publique hyperviseur vers une VM via ssh-copy-id.

    Args:
        hv_client (paramiko.SSHClient): Client SSH hyperviseur.
        vm (VMTarget): VM cible.
        password (str): Mot de passe SSH de la VM.

    Returns:
        bool: True si déploiement réussi ou clé déjà présente.
    """
    rc_sp, sshpass_path, _ = ssh_run(hv_client, "which sshpass 2>/dev/null")
    if rc_sp == 0 and sshpass_path.strip():
        cmd = f"sshpass -p {_shell_quote(password)} ssh-copy-id -o StrictHostKeyChecking=no -o ConnectTimeout=5 {vm.user}@{vm.ip} 2>&1"
    else:
        rc_ex, _, _ = ssh_run(hv_client, "which expect 2>/dev/null")
        if rc_ex != 0:
            log.warning("    Ni sshpass ni expect disponible. Installez : apt install sshpass")
            return False
        escaped = password.replace('"', '\\"')
        cmd = f'expect -c "spawn ssh-copy-id -o StrictHostKeyChecking=no {vm.user}@{vm.ip}; expect {{*password* {{ send \\"{escaped}\\r\\"; exp_continue }} eof}}" 2>&1'
    rc, out, _ = ssh_run(hv_client, cmd, timeout=30)
    return rc == 0 or "already" in out.lower()


def process_hypervisor(hv, inventory, default_vm_user="root"):
    """Exécute le workflow complet de déploiement de clés pour un hyperviseur.

    Args:
        hv (Hypervisor): Hyperviseur cible.
        inventory (list[dict]): Inventaire JSON des VMs.
        default_vm_user (str, optional): Utilisateur SSH par défaut pour les VMs.
            Defaults to "root".

    Returns:
        None: Met à jour `hv.vm_targets` en place.
    """
    print(f"\n{'═' * 60}\n  Hyperviseur : {hv.host}\n{'═' * 60}")
    hv_client = ssh_connect(hv.host, hv.user, hv.port)
    if not hv_client:
        log.error(f"  Impossible de se connecter à {hv.host}")
        return
    try:
        print(f"\n[1/2] Génération des clés SSH sur {hv.host}…")
        pubkeys = ensure_ssh_keys(hv_client, hv.host)
        if not pubkeys:
            log.error("  Aucune clé disponible, abandon.")
            return
        targets = get_vm_targets(inventory, hv.host, default_vm_user)
        if not targets:
            log.warning(f"  Aucune VM running avec IP pour {hv.host}")
            return
        print(f"\n[2/2] Déploiement vers {len(targets)} VM(s)…")
        results = []
        for vm in targets:
            print(f"\n  ▶ {vm.name} ({vm.user}@{vm.ip})")
            if test_ssh_key_from_hypervisor(hv_client, vm):
                vm.ssh_key_ok = True
                print("    ✅ Connexion par clé déjà OK")
                results.append(vm)
                continue
            password = get_password(vm.ip, vm.user)
            if not password:
                vm.error = "Mot de passe non fourni"
                print("    ⏭  Ignoré")
                results.append(vm)
                continue
            if copy_id_from_hypervisor(hv_client, vm, password):
                vm.ssh_copy_id_ok = True
                if test_ssh_key_from_hypervisor(hv_client, vm):
                    vm.ssh_key_ok = True
                    print("    ✅ Clé déployée et connexion validée")
                else:
                    vm.error = "ssh-copy-id OK mais re-test échoué"
                    print("    ⚠️  ssh-copy-id OK mais re-test échoué")
            else:
                vm.error = "ssh-copy-id échoué"
                print("    ❌ ssh-copy-id échoué, suivante")
            results.append(vm)
        hv.vm_targets = results
        ok = [v for v in results if v.ssh_key_ok]
        ko = [v for v in results if not v.ssh_key_ok]
        print(f"\n  Résumé {hv.host} : {len(ok)}/{len(results)} VM(s) OK")
        for v in ko:
            print(f"    ✗ {v.name} ({v.ip}) — {v.error or 'inconnu'}")
    finally:
        hv_client.close()


def export_report(hypervisors, path="ssh_deploy_report.json"):
    """Exporte un rapport JSON de déploiement SSH.

    Args:
        hypervisors (list[Hypervisor]): Hyperviseurs traités.
        path (str, optional): Fichier de sortie. Defaults to "ssh_deploy_report.json".

    Returns:
        None: Écrit le rapport sur disque.
    """
    data = [
        {
            "host": hv.host,
            "uri": hv.uri,
            "vms": [
                {
                    "name": v.name,
                    "ip": v.ip,
                    "user": v.user,
                    "ssh_key_ok": v.ssh_key_ok,
                    "ssh_copy_id_attempted": v.ssh_copy_id_ok,
                    "error": v.error,
                }
                for v in hv.vm_targets
            ],
        }
        for hv in hypervisors
    ]
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info(f"Rapport → {path}")


def main():
    """Point d'entrée CLI du déploiement SSH inter-VM.

    Returns:
        None: Exécute le flux complet de traitement.
    """
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--inventory", default="inventory.json")
    p.add_argument("--vm-user", default="root")
    p.add_argument("--uris", nargs="*")
    args = p.parse_args()
    inventory = load_inventory(args.inventory)
    uris = args.uris or get_libvirt_uris()
    if not uris:
        log.error("Aucune URI trouvée.")
        sys.exit(1)
    hypervisors = []
    for uri in uris:
        hv = parse_libvirt_uri(uri)
        if not hv or hv.transport == "local":
            continue
        process_hypervisor(hv, inventory, args.vm_user)
        hypervisors.append(hv)
    export_report(hypervisors)
    print("\n✅ Rapport → ssh_deploy_report.json")


if __name__ == "__main__":
    main()

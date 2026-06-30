#!/usr/bin/env python3
"""
libvirt_inventory.py — v4 (CLI complet, CSV, Ansible INI/YAML, ports SPICE/RDP)

Usage :
    python3 libvirt_inventory.py [options]

Options :
    --uris URI [URI ...]      Surcharge les URIs dconf (ex: qemu+ssh://root@hv/system)
    --no-os                   Ne tente pas la détection d'OS (plus rapide)
    --no-nmap                 Ne lance pas le scan nmap
    --output-json PATH        Exporte l'inventaire en JSON (défaut: inventory.json)
    --output-csv  PATH        Exporte l'inventaire en CSV (défaut: inventory.csv)
    --ansible-ini PATH        Génère un inventaire Ansible INI (défaut: inventory.ini)
    --ansible-yaml PATH       Génère un inventaire Ansible YAML (défaut: inventory.yml)
    --no-report               Ne pas afficher le rapport terminal
    --detect-ports            Sonde les ports SPICE (5900-5939) et RDP (3389) par VM
    --vm-user USER            Utilisateur SSH par défaut pour les VMs (défaut: root)
    --ssh-password PASS       Mot de passe SSH pour les hyperviseurs (préférer les clés)
    --ssh-timeout SEC         Délai de connexion SSH en secondes (défaut: 10)

Dépendances : pip install paramiko
"""

import argparse
import csv
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


# ─── Structures ──────────────────────────────────────────────────────────────


@dataclass
class Interface:
    """Interface réseau d'une VM avec MAC et IP éventuelle."""

    mac: str
    ip: str | None = None
    source_network: str | None = None


@dataclass
class OSInfo:
    """Métadonnées OS collectées depuis libvirt, agent invité et SSH."""

    # Depuis le XML libvirt
    libvirt_type: str | None = None
    libvirt_arch: str | None = None
    libvirt_machine: str | None = None
    libvirt_os_type: str | None = None
    libvirt_os_variant: str | None = None
    # Depuis qemu-guest-agent
    agent_os_name: str | None = None
    agent_os_version: str | None = None
    agent_kernel: str | None = None
    agent_hostname: str | None = None
    # Depuis SSH direct sur la VM
    ssh_os_name: str | None = None
    ssh_os_version: str | None = None
    ssh_kernel: str | None = None
    ssh_hostname: str | None = None
    # Synthèse finale
    os_name: str | None = None
    os_version: str | None = None
    kernel: str | None = None
    hostname: str | None = None
    arch: str | None = None


@dataclass
class PortInfo:
    """Ports ouverts détectés depuis l'hyperviseur."""

    spice_port: int | None = None  # port SPICE déclaré dans le XML libvirt
    spice_open: bool = False  # port SPICE confirmé ouvert (nc/nmap)
    rdp_open: bool = False  # port 3389 ouvert
    vnc_port: int | None = None  # port VNC déclaré dans le XML


@dataclass
class VM:
    """Représentation d'une VM inventoriée."""

    name: str
    uuid: str
    state: str
    interfaces: list[Interface] = field(default_factory=list)
    os: OSInfo = field(default_factory=OSInfo)
    ports: PortInfo = field(default_factory=PortInfo)
    vcpus: int | None = None
    memory_mb: int | None = None


@dataclass
class Hypervisor:
    """Hyperviseur libvirt cible et son inventaire de VMs."""

    uri: str
    host: str
    user: str
    port: int
    transport: str
    vms: list[VM] = field(default_factory=list)


# ─── Lecture dconf ────────────────────────────────────────────────────────────


def get_libvirt_uris() -> list[str]:
    """Lit les URIs libvirt configurées dans dconf (virt-manager).

    Returns:
        list[str]: Liste d'URIs libvirt détectées.
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
            log.warning("Aucune URI trouvée dans dconf.")
            return []
        uris = re.findall(r"'([^']+)'", raw)
        log.info(f"{len(uris)} URI(s) trouvée(s) dans virt-manager : {uris}")
        return uris
    except FileNotFoundError:
        log.error("dconf introuvable. Installez dconf-cli.")
        return []
    except subprocess.CalledProcessError as e:
        log.error(f"Erreur dconf : {e.stderr}")
        return []


# ─── Parsing URI libvirt ──────────────────────────────────────────────────────


def parse_libvirt_uri(uri: str) -> Hypervisor | None:
    """Parse une URI libvirt en structure Hypervisor.

    Args:
        uri (str): URI libvirt brute.

    Returns:
        Hypervisor | None: Hyperviseur parsé, ou None si invalide.
    """
    parsed = urlparse(uri)
    scheme = parsed.scheme
    if "+" in scheme:
        transport = scheme.split("+")[1]
    elif parsed.hostname:
        transport = "tcp"
    else:
        transport = "local"
    return Hypervisor(
        uri=uri,
        host=parsed.hostname or "localhost",
        user=parsed.username or "",
        port=parsed.port or 22,
        transport=transport,
    )


# ─── SSH helper ───────────────────────────────────────────────────────────────


def ssh_connect(
    hv: Hypervisor,
    password: str | None = None,
    timeout: int = 10,
) -> paramiko.SSHClient | None:
    """Ouvre une connexion SSH vers un hyperviseur.

    Args:
        hv: Hyperviseur cible (host, port, user).
        password: Mot de passe SSH optionnel. Si None, utilise les clés/agent.
        timeout: Délai de connexion en secondes.

    Returns:
        Client paramiko connecté, ou None en cas d'échec.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs: dict = dict(
        hostname=hv.host,
        port=hv.port,
        timeout=timeout,
        look_for_keys=True,
        allow_agent=True,
    )
    if hv.user:
        kwargs["username"] = hv.user
    if password:
        kwargs.update(password=password, look_for_keys=False, allow_agent=False)
    try:
        client.connect(**kwargs)
        log.info(
            f"SSH connecté à {hv.user + '@' if hv.user else ''}{hv.host}:{hv.port}"
            + (" (mot de passe)" if password else " (clé/agent)")
        )
        return client
    except Exception as e:
        log.error(f"Impossible de se connecter à {hv.host} : {e}")
        return None


def ssh_run(client: paramiko.SSHClient, cmd: str, timeout: int = 30) -> str:
    """Exécute une commande SSH et retourne stdout.

    Args:
        client (paramiko.SSHClient): Client SSH connecté.
        cmd (str): Commande shell à exécuter.
        timeout (int, optional): Timeout d'exécution en secondes. Defaults to 30.

    Returns:
        str: Sortie standard décodée.
    """
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace").strip()
    err = stderr.read().decode(errors="replace").strip()
    if err:
        log.debug(f"stderr: {err}")
    return out


# ─── Récupération des VMs ─────────────────────────────────────────────────────


def get_vms(client: paramiko.SSHClient) -> list[VM]:
    """Liste les VMs libvirt et enrichit CPU/RAM.

    Args:
        client (paramiko.SSHClient): Client SSH connecté à l'hyperviseur.

    Returns:
        list[VM]: Liste des VMs détectées.
    """
    out = ssh_run(client, "virsh list --all --name")
    names = [n for n in out.splitlines() if n.strip()]
    vms = []
    for name in names:
        uuid = ssh_run(client, f"virsh domuuid {name}").strip()
        state_raw = ssh_run(client, f"virsh domstate {name}").strip()
        vm = VM(name=name, uuid=uuid, state=state_raw)
        # vCPUs et mémoire depuis virsh dominfo
        info = ssh_run(client, f"virsh dominfo {name} 2>/dev/null")
        for line in info.splitlines():
            if line.startswith("CPU(s):"):
                try:
                    vm.vcpus = int(line.split(":")[1].strip())
                except ValueError:
                    pass
            elif line.startswith("Used memory:") or line.startswith("Max memory:"):
                try:
                    mem_kb = int(re.search(r"(\d+)", line.split(":")[1]).group(1))
                    vm.memory_mb = mem_kb // 1024
                except (ValueError, AttributeError):
                    pass
        vms.append(vm)
    log.info(f"  {len(vms)} VM(s) trouvée(s)")
    return vms


# ─── Récupération des MACs ────────────────────────────────────────────────────


def get_interfaces(client: paramiko.SSHClient, vm: VM) -> list[Interface]:
    """Extrait les interfaces réseau (MAC/réseau) et ports display depuis le XML VM.

    Args:
        client (paramiko.SSHClient): Client SSH connecté.
        vm (VM): VM cible.

    Returns:
        list[Interface]: Interfaces réseau détectées.
    """
    xml = ssh_run(client, f"virsh dumpxml {vm.name}")
    interfaces = []
    for block in re.findall(r"<interface.*?</interface>", xml, re.DOTALL):
        mac_m = re.search(r"<mac address=['\"]([^'\"]+)['\"]", block)
        net_m = re.search(r"<source (?:network|bridge|dev)=['\"]([^'\"]+)['\"]", block)
        if mac_m:
            interfaces.append(
                Interface(
                    mac=mac_m.group(1),
                    source_network=net_m.group(1) if net_m else None,
                )
            )
    # Ports SPICE/VNC depuis le XML
    m_spice = re.search(r'<graphics[^>]+type=[\'"]spice[\'"][^>]*port=[\'"](\d+)[\'"]', xml)
    if m_spice and m_spice.group(1) != "-1":
        vm.ports.spice_port = int(m_spice.group(1))
    m_vnc = re.search(r'<graphics[^>]+type=[\'"]vnc[\'"][^>]*port=[\'"](\d+)[\'"]', xml)
    if m_vnc and m_vnc.group(1) != "-1":
        vm.ports.vnc_port = int(m_vnc.group(1))
    return interfaces


# ─── Détection OS ─────────────────────────────────────────────────────────────

OSINFO_MAP = {
    "win11": "Windows 11",
    "win10": "Windows 10",
    "win2k22": "Windows Server 2022",
    "win2k19": "Windows Server 2019",
    "win2k16": "Windows Server 2016",
    "ubuntu24.04": "Ubuntu 24.04 LTS",
    "ubuntu22.04": "Ubuntu 22.04 LTS",
    "ubuntu20.04": "Ubuntu 20.04 LTS",
    "debian12": "Debian 12",
    "debian11": "Debian 11",
    "debian10": "Debian 10",
    "rocky9": "Rocky Linux 9",
    "rocky8": "Rocky Linux 8",
    "almalinux9": "AlmaLinux 9",
    "almalinux8": "AlmaLinux 8",
    "rhel9": "RHEL 9",
    "rhel8": "RHEL 8",
    "centos8": "CentOS 8",
    "centos7": "CentOS 7",
    "fedora39": "Fedora 39",
    "opensuse15.5": "openSUSE 15.5",
    "freebsd13": "FreeBSD 13",
}


def get_os_from_xml(client: paramiko.SSHClient, vm: VM) -> None:
    """Renseigne les informations OS depuis le XML libvirt.

    Args:
        client (paramiko.SSHClient): Client SSH connecté.
        vm (VM): VM cible à enrichir.

    Returns:
        None: Met à jour `vm.os` en place.
    """
    xml = ssh_run(client, f"virsh dumpxml {vm.name}")
    o = vm.os

    m = re.search(
        r"<type\s+arch=['\"]([^'\"]+)['\"](?:\s+machine=['\"]([^'\"]+)['\"])?[^>]*>([^<]+)<",
        xml,
    )
    if m:
        o.libvirt_arch = m.group(1)
        o.libvirt_machine = m.group(2)
        o.libvirt_type = m.group(3).strip()
        o.arch = m.group(1)

    m = re.search(r'libosinfo:os\s+id=["\']http[^"\']+/([^/"\']+)["\']', xml)
    if not m:
        m = re.search(r':os\s+id=["\'][^"\']+/([^/"\']+)["\']', xml)
    if m:
        variant = m.group(1)
        o.libvirt_os_variant = variant
        o.libvirt_os_type = "windows" if variant.startswith("win") else "linux"
        o.os_name = OSINFO_MAP.get(variant, variant)

    if not o.os_name:
        m = re.search(r"<description>([^<]+)</description>", xml)
        if m:
            o.os_name = m.group(1).strip()


def get_os_from_agent(client: paramiko.SSHClient, vm: VM) -> bool:
    """Récupère les infos OS depuis qemu-guest-agent.

    Args:
        client (paramiko.SSHClient): Client SSH connecté.
        vm (VM): VM cible.

    Returns:
        bool: True si des données agent ont été trouvées.
    """
    if vm.state != "running":
        return False
    out = ssh_run(client, f"virsh guestinfo {vm.name} --os 2>/dev/null")
    if not out or "error" in out.lower():
        return False
    o = vm.os
    found = False
    for line in out.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip().lower(), val.strip()
        if not val:
            continue
        found = True
        if key == "os.name":
            o.agent_os_name = val
        elif key in ("os.version-id", "os.version") and not o.agent_os_version:
            o.agent_os_version = val
        elif key == "os.kernel-release":
            o.agent_kernel = val
        elif key == "os.hostname":
            o.agent_hostname = val
        elif key == "os.machine" and not o.arch:
            o.arch = val
    if found:
        if o.agent_os_name:
            o.os_name = o.agent_os_name
        if o.agent_os_version:
            o.os_version = o.agent_os_version
        if o.agent_kernel:
            o.kernel = o.agent_kernel
        if o.agent_hostname:
            o.hostname = o.agent_hostname
        log.info(f"    Agent OS : {o.os_name} {o.os_version or ''} kernel={o.kernel}")
    return found


def get_os_from_ssh(hv_client: paramiko.SSHClient, vm: VM) -> bool:
    """Tente une détection OS par SSH direct vers la VM.

    Args:
        hv_client (paramiko.SSHClient): Client SSH de l'hyperviseur.
        vm (VM): VM cible.

    Returns:
        bool: True si la détection SSH a réussi.
    """
    if vm.state != "running":
        return False
    ip = next((i.ip for i in vm.interfaces if i.ip), None)
    if not ip:
        return False
    for user in ("root", "ubuntu", "debian", "rocky", "almalinux", "centos", "admin"):
        cmd = (
            f"ssh -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=4 {user}@{ip} "
            f"\"cat /etc/os-release 2>/dev/null; echo '---UNAME---'; uname -r; echo '---HOST---'; hostname\" "
            f"2>/dev/null"
        )
        out = ssh_run(hv_client, cmd, timeout=15)
        if not out or "---UNAME---" not in out:
            continue
        o = vm.os
        parts = out.split("---UNAME---")
        os_release_raw = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        uname_parts = rest.split("---HOST---")
        kernel_raw = uname_parts[0].strip()
        host_raw = uname_parts[1].strip() if len(uname_parts) > 1 else ""
        kv = {}
        for line in os_release_raw.splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                kv[k.strip()] = v.strip().strip('"')
        ssh_name = kv.get("PRETTY_NAME") or kv.get("NAME", "")
        ssh_version = kv.get("VERSION_ID", "")
        if ssh_name:
            o.ssh_os_name = ssh_name
            o.ssh_os_version = ssh_version
            o.ssh_kernel = kernel_raw or None
            o.ssh_hostname = host_raw or None
            o.os_name = ssh_name
            o.os_version = ssh_version or o.os_version
            o.kernel = kernel_raw or o.kernel
            o.hostname = host_raw or o.hostname
            log.info(
                f"    SSH OS  : {o.os_name} {o.os_version} kernel={o.kernel} host={o.hostname}"
            )
            return True
    return False


def enrich_os(hv_client: paramiko.SSHClient, vm: VM) -> None:
    """
    Détection OS en cascade :
      1. XML virsh dumpxml  (toujours)
      2. virsh guestinfo --os  (qemu-guest-agent, si running)
      3. SSH direct sur la VM  (si running + IP + clé dispo)
    Priorité : SSH > agent > XML
    """
    log.info(f"  OS {vm.name}…")
    get_os_from_xml(hv_client, vm)
    agent_ok = get_os_from_agent(hv_client, vm)
    if not agent_ok or not vm.os.kernel:
        get_os_from_ssh(hv_client, vm)
    if not vm.os.arch and vm.os.libvirt_arch:
        vm.os.arch = vm.os.libvirt_arch
    log.info(
        f"    → {vm.os.os_name or 'OS inconnu'} {vm.os.os_version or ''} | "
        f"arch={vm.os.arch} | kernel={vm.os.kernel or '-'} | host={vm.os.hostname or '-'}"
    )


# ─── Détection de ports ouverts (SPICE/VNC/RDP) ─────────────────────────────


def _port_open(client: paramiko.SSHClient, ip: str, port: int, timeout: int = 4) -> bool:
    """Vérifie si un port TCP est accessible depuis l'hyperviseur (nc, puis nmap)."""
    if not ip:
        return False
    out = ssh_run(
        client,
        f"nc -z -w {timeout} {ip} {port} 2>/dev/null && echo OPEN || echo CLOSED",
        timeout=timeout + 3,
    )
    if "OPEN" in out:
        return True
    if "CLOSED" in out:
        return False
    # Fallback nmap
    out = ssh_run(
        client,
        f"nmap -p {port} -sT --host-timeout {timeout}s {ip} -oG - 2>/dev/null",
        timeout=timeout + 5,
    )
    return f"{port}/open" in out.lower()


def detect_ports(client: paramiko.SSHClient, vms: list[VM]) -> None:
    """Sonde les ports SPICE, VNC et RDP depuis l'hyperviseur pour chaque VM running."""
    for vm in vms:
        if vm.state != "running":
            continue
        ip = next((i.ip for i in vm.interfaces if i.ip), None)
        if not ip:
            log.debug(f"  {vm.name} : IP inconnue, sondage de port ignoré")
            continue
        # SPICE (port déclaré dans XML)
        if vm.ports.spice_port:
            vm.ports.spice_open = _port_open(client, ip, vm.ports.spice_port)
            log.info(
                f"  {vm.name} SPICE :{vm.ports.spice_port} → "
                f"{'ouvert' if vm.ports.spice_open else 'fermé'}"
            )
        # VNC (port déclaré dans XML)
        if vm.ports.vnc_port:
            vnc_open = _port_open(client, ip, vm.ports.vnc_port)
            log.info(f"  {vm.name} VNC :{vm.ports.vnc_port} → {'ouvert' if vnc_open else 'fermé'}")
        # RDP
        vm.ports.rdp_open = _port_open(client, ip, 3389)
        if vm.ports.rdp_open:
            log.info(f"  {vm.name} RDP :3389 → ouvert")


# ─── Récupération des sous-réseaux ───────────────────────────────────────────


def get_host_subnets(client: paramiko.SSHClient) -> list[str]:
    """Détermine les sous-réseaux IPv4 de l'hyperviseur.

    Args:
        client (paramiko.SSHClient): Client SSH connecté.

    Returns:
        list[str]: Liste de sous-réseaux CIDR uniques.
    """
    out = ssh_run(client, "ip -o -f inet addr show")
    subnets, seen = [], set()
    for line in out.splitlines():
        m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/(\d+)", line)
        if not m:
            continue
        ip_str, prefix = m.group(1), int(m.group(2))
        if ip_str.startswith("127.") or ip_str.startswith("169.254."):
            continue
        ip_parts = list(map(int, ip_str.split(".")))
        mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
        net_int = 0
        for part in ip_parts:
            net_int = (net_int << 8) | part
        net_int &= mask
        net_parts = [(net_int >> (8 * i)) & 0xFF for i in reversed(range(4))]
        cidr = f"{'.'.join(map(str, net_parts))}/{prefix}"
        if cidr not in seen:
            seen.add(cidr)
            subnets.append(cidr)
            log.info(f"    Sous-réseau détecté : {cidr}")
    return subnets


# ─── nmap ping scan ───────────────────────────────────────────────────────────


def nmap_ping_scan(client: paramiko.SSHClient, subnets: list[str]) -> dict[str, str]:
    """Exécute un scan nmap ping et retourne une table MAC→IP.

    Args:
        client (paramiko.SSHClient): Client SSH connecté.
        subnets (list[str]): Sous-réseaux CIDR à scanner.

    Returns:
        dict[str, str]: Mapping mac_lower -> ip.
    """
    result: dict[str, str] = {}
    if not subnets:
        return result
    if not ssh_run(client, "which nmap 2>/dev/null"):
        log.warning("  nmap non disponible.")
        return result
    nmap_ver = ssh_run(client, "nmap --version 2>/dev/null | head -1")
    ver_m = re.search(r"Nmap version (\d+)", nmap_ver)
    flag = "-sn" if ver_m and int(ver_m.group(1)) >= 6 else "-sP"
    for cidr in subnets:
        log.info(f"  nmap {flag} {cidr}…")
        xml_out = ssh_run(
            client,
            f"nmap {flag} {cidr} -oX - --host-timeout 5s 2>/dev/null",
            timeout=300,
        )
        if not xml_out:
            continue
        count = 0
        for host_block in re.findall(r"<host\b.*?</host>", xml_out, re.DOTALL):
            ip_m = re.search(r'<address addr="([^"]+)" addrtype="ipv4"', host_block)
            mac_m = re.search(r'<address addr="([^"]+)" addrtype="mac"', host_block)
            if ip_m and mac_m:
                result[mac_m.group(1).lower()] = ip_m.group(1)
                count += 1
        log.info(f"    {count} hôte(s) avec MAC sur {cidr}")
    return result


# ─── ARP / DHCP ──────────────────────────────────────────────────────────────


def build_arp_table(client: paramiko.SSHClient) -> dict[str, str]:
    """Construit une table MAC→IP depuis ARP/neigh.

    Args:
        client (paramiko.SSHClient): Client SSH connecté.

    Returns:
        dict[str, str]: Mapping mac_lower -> ip.
    """
    arp = {}
    for line in ssh_run(client, "ip neigh show 2>/dev/null || arp -n 2>/dev/null").splitlines():
        m = re.search(r"(\d+\.\d+\.\d+\.\d+).*?([0-9a-f]{2}(?::[0-9a-f]{2}){5})", line, re.I)
        if m:
            arp[m.group(2).lower()] = m.group(1)
    return arp


def build_dhcp_table(client: paramiko.SSHClient) -> dict[str, str]:
    """Construit une table MAC→IP depuis les baux DHCP libvirt.

    Args:
        client (paramiko.SSHClient): Client SSH connecté.

    Returns:
        dict[str, str]: Mapping mac_lower -> ip.
    """
    leases: dict[str, str] = {}
    for net in ssh_run(client, "virsh net-list --name").splitlines():
        net = net.strip()
        if not net:
            continue
        for line in ssh_run(client, f"virsh net-dhcp-leases {net} 2>/dev/null").splitlines():
            parts = line.split()
            if len(parts) >= 4:
                mac_c = parts[1] if ":" in parts[1] else None
                ip_c = parts[3].split("/")[0] if "/" in parts[3] else parts[3]
                if mac_c and re.match(r"\d+\.\d+\.\d+\.\d+", ip_c):
                    leases[mac_c.lower()] = ip_c
    return leases


# ─── Résolution IP ────────────────────────────────────────────────────────────


def resolve_ips(client: paramiko.SSHClient, vms: list[VM], use_nmap: bool = True) -> None:
    """Résout les IP des interfaces VM via domifaddr, DHCP, ARP puis nmap.

    Args:
        client (paramiko.SSHClient): Client SSH connecté.
        vms (list[VM]): VMs à enrichir.
        use_nmap (bool, optional): Active le scan nmap complémentaire. Defaults to True.

    Returns:
        None: Met à jour les IP des interfaces en place.
    """
    for vm in vms:
        if vm.state != "running":
            continue
        for method in ("agent", "arp"):
            out = ssh_run(client, f"virsh domifaddr {vm.name} --source {method} 2>/dev/null")
            for iface in vm.interfaces:
                if iface.ip:
                    continue
                for line in out.splitlines():
                    if iface.mac.lower() in line.lower():
                        m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                        if m:
                            iface.ip = m.group(1)
                            break

    nmap_table: dict[str, str] = {}
    if use_nmap:
        subnets = get_host_subnets(client)
        nmap_table = nmap_ping_scan(client, subnets)
    dhcp = build_dhcp_table(client)
    arp = build_arp_table(client)
    combined = {**arp, **dhcp, **nmap_table}
    log.info(f"  Table MAC→IP fusionnée : {len(combined)} entrées")

    for vm in vms:
        for iface in vm.interfaces:
            if iface.ip:
                continue
            iface.ip = combined.get(iface.mac.lower())
            if iface.ip:
                log.info(f"    {vm.name} / {iface.mac} → {iface.ip}")


# ─── Affichage ────────────────────────────────────────────────────────────────


def print_report(hypervisors: list[Hypervisor]) -> None:
    """Affiche un rapport texte de l'inventaire collecté.

    Args:
        hypervisors (list[Hypervisor]): Hyperviseurs à afficher.

    Returns:
        None: Écrit le rapport sur stdout.
    """
    print("\n" + "═" * 68 + "\n  INVENTAIRE LIBVIRT\n" + "═" * 68)
    total_vms = sum(len(hv.vms) for hv in hypervisors)
    total_running = sum(1 for hv in hypervisors for vm in hv.vms if vm.state == "running")
    print(f"  Hyperviseurs : {len(hypervisors)}   VMs : {total_vms}   Running : {total_running}")
    for hv in hypervisors:
        print(f"\n🖥  Hyperviseur : {hv.host}  ({hv.uri})")
        if not hv.vms:
            print("   Aucune VM.")
            continue
        for vm in hv.vms:
            state_icon = "▶" if vm.state == "running" else "■"
            os_str = ""
            if vm.os.os_name:
                os_str = f"  [{vm.os.os_name}"
                if vm.os.os_version:
                    os_str += f" {vm.os.os_version}"
                if vm.os.arch:
                    os_str += f" {vm.os.arch}"
                os_str += "]"
            cpu_mem = ""
            if vm.vcpus:
                cpu_mem += f"  vCPUs={vm.vcpus}"
            if vm.memory_mb:
                cpu_mem += f"  RAM={vm.memory_mb}MB"
            print(f"\n  {state_icon} {vm.name}  [{vm.state}]{os_str}{cpu_mem}")
            if vm.os.hostname:
                print(f"      hostname={vm.os.hostname}  kernel={vm.os.kernel or '-'}")
            # Ports
            ports = []
            if vm.ports.spice_port:
                ports.append(
                    f"SPICE:{vm.ports.spice_port}({'open' if vm.ports.spice_open else 'closed'})"
                )
            if vm.ports.vnc_port:
                ports.append(f"VNC:{vm.ports.vnc_port}")
            if vm.ports.rdp_open:
                ports.append("RDP:3389(open)")
            if ports:
                print(f"      Ports : {', '.join(ports)}")
            for iface in vm.interfaces:
                net = f"  réseau={iface.source_network}" if iface.source_network else ""
                print(f"      MAC {iface.mac}  →  {iface.ip or 'IP inconnue'}{net}")
    print("\n" + "═" * 68)


def export_json(hypervisors: list[Hypervisor], path: str = "inventory.json") -> None:
    """Exporte l'inventaire complet au format JSON.

    Args:
        hypervisors (list[Hypervisor]): Données d'inventaire.
        path (str, optional): Chemin du fichier JSON. Defaults to "inventory.json".

    Returns:
        None: Écrit le fichier sur disque.
    """
    data = []
    for hv in hypervisors:
        hv_dict = {"host": hv.host, "uri": hv.uri, "vms": []}
        for vm in hv.vms:
            o = vm.os
            hv_dict["vms"].append(
                {
                    "name": vm.name,
                    "uuid": vm.uuid,
                    "state": vm.state,
                    "vcpus": vm.vcpus,
                    "memory_mb": vm.memory_mb,
                    "os": {
                        "name": o.os_name,
                        "version": o.os_version,
                        "kernel": o.kernel,
                        "hostname": o.hostname,
                        "arch": o.arch,
                        "sources": {
                            "libvirt": {
                                "type": o.libvirt_type,
                                "arch": o.libvirt_arch,
                                "machine": o.libvirt_machine,
                                "variant": o.libvirt_os_variant,
                            },
                            "agent": (
                                {
                                    "name": o.agent_os_name,
                                    "version": o.agent_os_version,
                                    "kernel": o.agent_kernel,
                                }
                                if o.agent_os_name
                                else None
                            ),
                            "ssh": (
                                {
                                    "name": o.ssh_os_name,
                                    "version": o.ssh_os_version,
                                    "kernel": o.ssh_kernel,
                                }
                                if o.ssh_os_name
                                else None
                            ),
                        },
                    },
                    "ports": {
                        "spice_port": vm.ports.spice_port,
                        "spice_open": vm.ports.spice_open,
                        "vnc_port": vm.ports.vnc_port,
                        "rdp_open": vm.ports.rdp_open,
                    },
                    "interfaces": [
                        {"mac": i.mac, "ip": i.ip, "network": i.source_network}
                        for i in vm.interfaces
                    ],
                }
            )
        data.append(hv_dict)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info(f"JSON exporté → {path}")


def export_csv(hypervisors: list[Hypervisor], path: str = "inventory.csv") -> None:
    """Exporte l'inventaire en CSV (une ligne par VM × interface)."""
    fields = [
        "hypervisor",
        "vm_name",
        "uuid",
        "state",
        "vcpus",
        "memory_mb",
        "os_name",
        "os_version",
        "os_arch",
        "kernel",
        "hostname",
        "mac",
        "ip",
        "network",
        "spice_port",
        "spice_open",
        "vnc_port",
        "rdp_open",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for hv in hypervisors:
            for vm in hv.vms:
                base = {
                    "hypervisor": hv.host,
                    "vm_name": vm.name,
                    "uuid": vm.uuid,
                    "state": vm.state,
                    "vcpus": vm.vcpus or "",
                    "memory_mb": vm.memory_mb or "",
                    "os_name": vm.os.os_name or "",
                    "os_version": vm.os.os_version or "",
                    "os_arch": vm.os.arch or "",
                    "kernel": vm.os.kernel or "",
                    "hostname": vm.os.hostname or "",
                    "spice_port": vm.ports.spice_port or "",
                    "spice_open": "1" if vm.ports.spice_open else "",
                    "vnc_port": vm.ports.vnc_port or "",
                    "rdp_open": "1" if vm.ports.rdp_open else "",
                }
                if vm.interfaces:
                    for iface in vm.interfaces:
                        row = dict(base)
                        row.update(
                            mac=iface.mac,
                            ip=iface.ip or "",
                            network=iface.source_network or "",
                        )
                        writer.writerow(row)
                else:
                    base.update(mac="", ip="", network="")
                    writer.writerow(base)
    log.info(f"CSV exporté → {path}")


def export_ansible_ini(
    hypervisors: list[Hypervisor],
    path: str = "inventory.ini",
    vm_user: str = "root",
) -> None:
    """Génère un inventaire Ansible au format INI.

    Structure :
      [all:vars]        ansible_user=root

      [hypervisor_HV_HOST]
      HV_HOST           ansible_host=HV_IP

      [vms_running]     VMs running avec IP connue
      [vms_stopped]     VMs arrêtées
      [os_linux]        VMs avec OS détecté Linux
      [os_windows]      VMs avec OS détecté Windows
      [rdp]             VMs avec RDP ouvert
    """
    lines: list[str] = [
        "# Inventaire Ansible généré par libvirt_inventory.py",
        "",
        "[all:vars]",
        f"ansible_user={vm_user}",
        "",
    ]

    running_entries: list[str] = []
    stopped_entries: list[str] = []
    linux_entries: list[str] = []
    windows_entries: list[str] = []
    rdp_entries: list[str] = []

    for hv in hypervisors:
        hv_slug = re.sub(r"[^\w]", "_", hv.host)
        lines += [
            f"[hypervisor_{hv_slug}]",
            f"{hv.host}  ansible_host={hv.host}  ansible_user={hv.user or vm_user}",
            "",
        ]
        for vm in hv.vms:
            ip = next((i.ip for i in vm.interfaces if i.ip), None)
            vm_slug = re.sub(r"[^\w]", "_", vm.name)
            if not ip:
                continue
            host_line = f"{vm_slug}  ansible_host={ip}  # hv={hv.host}  state={vm.state}  os={vm.os.os_name or '?'}"
            if vm.state == "running":
                running_entries.append(host_line)
            else:
                stopped_entries.append(host_line)
            os_lower = (vm.os.os_name or "").lower()
            if "windows" in os_lower or "win" in (vm.os.libvirt_os_variant or ""):
                windows_entries.append(host_line)
            else:
                linux_entries.append(host_line)
            if vm.ports.rdp_open:
                rdp_entries.append(host_line)

    for group_name, entries in (
        ("vms_running", running_entries),
        ("vms_stopped", stopped_entries),
        ("os_linux", linux_entries),
        ("os_windows", windows_entries),
        ("rdp", rdp_entries),
    ):
        lines.append(f"[{group_name}]")
        lines.extend(entries or ["# (vide)"])
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log.info(f"Ansible INI exporté → {path}")


def export_ansible_yaml(
    hypervisors: list[Hypervisor],
    path: str = "inventory.yml",
    vm_user: str = "root",
) -> None:
    """Génère un inventaire Ansible au format YAML (compatible ansible-inventory)."""

    # Construit à la main pour ne pas nécessiter PyYAML
    def _indent(n: int) -> str:
        return "  " * n

    lines: list[str] = [
        "# Inventaire Ansible YAML généré par libvirt_inventory.py",
        "all:",
        "  vars:",
        f"    ansible_user: {vm_user}",
        "  children:",
    ]

    for hv in hypervisors:
        hv_slug = re.sub(r"[^\w]", "_", hv.host)
        lines += [
            f"    hypervisor_{hv_slug}:",
            "      hosts:",
            f"        {hv.host}:",
            f"          ansible_host: {hv.host}",
            f"          ansible_user: {hv.user or vm_user}",
        ]

    lines += ["    vms_running:", "      hosts:"]
    for hv in hypervisors:
        for vm in hv.vms:
            if vm.state != "running":
                continue
            ip = next((i.ip for i in vm.interfaces if i.ip), None)
            if not ip:
                continue
            vm_slug = re.sub(r"[^\w]", "_", vm.name)
            lines += [
                f"        {vm_slug}:",
                f"          ansible_host: {ip}",
                f"          libvirt_hv: {hv.host}",
                f"          libvirt_state: {vm.state}",
            ]
            if vm.os.os_name:
                lines.append(f'          os_name: "{vm.os.os_name}"')
            if vm.os.arch:
                lines.append(f"          os_arch: {vm.os.arch}")
            if vm.vcpus:
                lines.append(f"          vcpus: {vm.vcpus}")
            if vm.memory_mb:
                lines.append(f"          memory_mb: {vm.memory_mb}")
            if vm.ports.rdp_open:
                lines.append("          rdp_available: true")
            if vm.ports.spice_port:
                lines.append(f"          spice_port: {vm.ports.spice_port}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log.info(f"Ansible YAML exporté → {path}")


# ─── Main ─────────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Inventaire des VMs libvirt via SSH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--uris",
        nargs="+",
        metavar="URI",
        help="Surcharge les URIs dconf (ex: qemu+ssh://root@hv/system)",
    )
    p.add_argument(
        "--no-os", action="store_true", help="Désactive la détection d'OS (plus rapide)"
    )
    p.add_argument("--no-nmap", action="store_true", help="Désactive le scan nmap (plus rapide)")
    p.add_argument(
        "--detect-ports",
        action="store_true",
        help="Sonde les ports SPICE/VNC/RDP depuis l'hyperviseur",
    )
    p.add_argument(
        "--vm-user",
        default="root",
        metavar="USER",
        help="Utilisateur SSH pour les VMs (défaut: root)",
    )
    p.add_argument(
        "--output-json",
        default="inventory.json",
        metavar="PATH",
        help="Chemin JSON de sortie (défaut: inventory.json)",
    )
    p.add_argument(
        "--output-csv",
        default="inventory.csv",
        metavar="PATH",
        help="Chemin CSV de sortie (défaut: inventory.csv, vide=désactivé)",
    )
    p.add_argument(
        "--ansible-ini",
        default="inventory.ini",
        metavar="PATH",
        help="Chemin inventaire Ansible INI (défaut: inventory.ini)",
    )
    p.add_argument(
        "--ansible-yaml",
        default="inventory.yml",
        metavar="PATH",
        help="Chemin inventaire Ansible YAML (défaut: inventory.yml)",
    )
    p.add_argument("--no-report", action="store_true", help="Ne pas afficher le rapport terminal")
    p.add_argument("--no-csv", action="store_true", help="Désactive l'export CSV")
    p.add_argument(
        "--no-ansible",
        action="store_true",
        help="Désactive les exports Ansible INI et YAML",
    )
    p.add_argument(
        "--ssh-password",
        default=None,
        metavar="PASS",
        help="Mot de passe SSH pour les hyperviseurs (déconseillé ; préférez les clés). "
        "Si omis, utilise clés/agent SSH.",
    )
    p.add_argument(
        "--ssh-timeout",
        type=int,
        default=10,
        metavar="SEC",
        help="Délai de connexion SSH en secondes (défaut: 10)",
    )
    return p


def main() -> None:
    """Point d'entrée CLI de l'inventaire libvirt.

    Returns:
        None: Exécute la collecte et les exports demandés.
    """
    args = _build_parser().parse_args()

    uris = args.uris or get_libvirt_uris()
    if not uris:
        log.error("Aucune connexion libvirt trouvée.")
        sys.exit(1)

    hypervisors: list[Hypervisor] = []
    for uri in uris:
        hv = parse_libvirt_uri(uri)
        if not hv or hv.transport == "local":
            log.info(f"URI locale ignorée : {uri}")
            continue
        log.info(f"\n── Hyperviseur : {hv.host} ({uri})")
        client = ssh_connect(hv, password=args.ssh_password, timeout=args.ssh_timeout)
        if not client:
            continue
        try:
            hv.vms = get_vms(client)
            for vm in hv.vms:
                vm.interfaces = get_interfaces(client, vm)
            resolve_ips(client, hv.vms, use_nmap=not args.no_nmap)
            if not args.no_os:
                for vm in hv.vms:
                    enrich_os(client, vm)
            if args.detect_ports:
                detect_ports(client, hv.vms)
        finally:
            client.close()
        hypervisors.append(hv)

    if not hypervisors:
        log.error("Aucun hyperviseur joignable.")
        sys.exit(1)

    if not args.no_report:
        print_report(hypervisors)

    export_json(hypervisors, args.output_json)

    if not args.no_csv:
        export_csv(hypervisors, args.output_csv)

    if not args.no_ansible:
        export_ansible_ini(hypervisors, args.ansible_ini, vm_user=args.vm_user)
        export_ansible_yaml(hypervisors, args.ansible_yaml, vm_user=args.vm_user)

    total_vms = sum(len(hv.vms) for hv in hypervisors)
    log.info(f"\n✅  {total_vms} VM(s) sur {len(hypervisors)} hyperviseur(s) inventoriées.")


if __name__ == "__main__":
    main()

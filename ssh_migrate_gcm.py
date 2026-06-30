#!/usr/bin/env python3
"""Migrate SSH host configuration from GCM (gcm.conf) to ~/.ssh/config.

This module is designed to be imported directly by gnome_connection_manager.py
and can also be run standalone from the command line.

What it does
------------
For every SSH host (``type = 0``) in gcm.conf:

1. **Backup** — timestamped copies of gcm.conf and ~/.ssh/config are created
   before any write operation.
2. **~/.ssh/config** — a stanza is appended / replaced inside a sentinel block,
   containing all SSH parameters (IdentityFile, ProxyJump, ForwardX11, …).
3. **gcm.conf rewrite** — the migrated entry is stripped down to the minimal
   set of keys GCM needs to display and connect:
     - ``name``, ``host``, ``password``, ``type``
     - ``port`` → kept but will be rendered as read-only / greyed-out in the UI
     - ``description`` → replaced with a red-badge notice
     - ``ssh_config_managed`` → ``true``  (new sentinel key)
   All other SSH parameters (private-key, tunnel, x11, agent, compression,
   keepalive, extra-params) are removed from gcm.conf because they now live
   in ~/.ssh/config.

Non-SSH entries (Telnet, RDP, VNC, SPICE, Serial) are left untouched.

GTK integration
---------------
In ``gnome_connection_manager.py``, call :func:`migrate_ssh_hosts` once at
startup (or on demand from a menu item).  Then patch the "Edit Host" dialog
to detect ``ssh_config_managed = true`` and:

  * grey out / disable the Port field
  * show the description label in red with the notice text
  * hide the advanced SSH fields (key, tunnel, X11, …)

Usage (standalone)::

    python3 gcm_ssh_migrate.py [--gcm-conf PATH] [--ssh-config PATH] [--dry-run]
"""

from __future__ import annotations

import argparse
import configparser
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GCM_TYPE_SSH = 0

DEFAULT_SSH_PORT = 22

# Keys kept in gcm.conf after migration (all others are removed for SSH hosts)
GCM_KEYS_RETAINED = {
    "name",
    "host",
    "user",
    "password",
    "type",
    "port",
    "group",
    # sentinel + UI hint
    "ssh_config_managed",
    "description",
    # non-SSH protocol fields that may coexist in a fork
    "rdp-domain",
    "rdp-width",
    "rdp-height",
    "vnc-password",
    "spice-password",
    "serial-device",
    "serial-baud",
}

# Keys migrated to ~/.ssh/config (removed from gcm.conf for SSH hosts)
GCM_KEYS_SSH_ONLY = {
    "private-key",
    "tunnel",
    "x11",
    "agent",
    "compression",
    "compressionlevel",
    "keepalive",
    "extra-params",
}

# Sentinel markers in ~/.ssh/config
_SSH_MARKER_BEGIN = "# === BEGIN gcm-managed-hosts ==="
_SSH_MARKER_END = "# === END gcm-managed-hosts ==="

# Description injected into gcm.conf for migrated hosts (read by GCM UI)
_MANAGED_DESCRIPTION = "⚙ SSH config: ~/.ssh/config → Host {name}"

# ---------------------------------------------------------------------------
# Helpers — configparser read / write
# ---------------------------------------------------------------------------


def _cp_get(cp: configparser.RawConfigParser, section: str, key: str, default: str = "") -> str:
    """Read a string value with a safe fallback."""
    try:
        return cp.get(section, key)
    except (configparser.NoSectionError, configparser.NoOptionError):
        return default


def _cp_getbool(
    cp: configparser.RawConfigParser,
    section: str,
    key: str,
    default: bool = False,
) -> bool:
    """Read a boolean value with a safe fallback."""
    try:
        return cp.getboolean(section, key)
    except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
        return default


def _cp_getint(
    cp: configparser.RawConfigParser,
    section: str,
    key: str,
    default: int = 0,
) -> int:
    """Read an integer value with a safe fallback."""
    try:
        return int(cp.get(section, key))
    except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------


def backup_file(path: Path) -> Path | None:
    """Create a timestamped backup copy of *path* next to the original.

    The backup name follows the pattern ``<name>.bak.<YYYYMMDD_HHMMSS>``.
    If *path* does not exist the function is a no-op and returns ``None``.

    Args:
        path: File to back up.

    Returns:
        Path of the backup file, or ``None`` if *path* did not exist.

    Raises:
        OSError: When the copy operation fails.
    """
    if not path.exists():
        logger.debug("backup_file | source does not exist, skipping | path={path}", path=path)
        return None

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = path.with_name(f"{path.name}.bak.{stamp}")
    shutil.copy2(str(path), str(dest))
    logger.info("backup_file | created | src={src} dst={dst}", src=path, dst=dest)
    return dest


# ---------------------------------------------------------------------------
# SSH config rendering
# ---------------------------------------------------------------------------


def _render_ssh_stanza(
    name: str, host: str, cp: configparser.RawConfigParser, section: str
) -> str:
    """Render a single ``Host`` stanza for ~/.ssh/config.

    Args:
        name: Host name (used as the ``Host`` keyword value).
        host: Hostname / IP address.
        cp: Config parser holding the full gcm.conf.
        section: The ``[host …]`` section name for this entry.

    Returns:
        Multi-line string for the stanza (no trailing newline).
    """
    safe_name = name.replace(" ", "_")
    port = _cp_getint(cp, section, "port", DEFAULT_SSH_PORT)
    user = _cp_get(cp, section, "user")
    private_key = _cp_get(cp, section, "private-key")
    tunnel = _cp_get(cp, section, "tunnel")
    x11 = _cp_getbool(cp, section, "x11")
    agent = _cp_getbool(cp, section, "agent")
    compression = _cp_getbool(cp, section, "compression")
    keep_alive = _cp_getint(cp, section, "keepalive")
    extra_params = _cp_get(cp, section, "extra-params")
    group = _cp_get(cp, section, "group")
    description = _cp_get(cp, section, "description")

    lines: list[str] = []

    # Header comment
    meta_parts: list[str] = []
    if group:
        meta_parts.append(f"group={group}")
    if description:
        meta_parts.append(description)
    comment = "# GCM"
    if meta_parts:
        comment += " | " + " | ".join(meta_parts)
    lines.append(comment)

    lines.append(f"Host {safe_name}")
    lines.append(f"    HostName {host}")

    if user:
        lines.append(f"    User {user}")

    if port != DEFAULT_SSH_PORT:
        lines.append(f"    Port {port}")

    if private_key:
        expanded = os.path.expanduser(private_key)
        lines.append(f"    IdentityFile {expanded}")
        lines.append("    IdentitiesOnly yes")
    else:
        lines.append("    # No IdentityFile — run ssh-copy-id to install a public key")

    # Jump host (tunnel)
    if tunnel:
        proxy = _parse_tunnel_to_proxyjump(tunnel)
        if proxy:
            lines.append(f"    ProxyJump {proxy}")

    if x11:
        lines.append("    ForwardX11 yes")
        lines.append("    ForwardX11Trusted yes")

    if agent:
        lines.append("    ForwardAgent yes")

    if compression:
        lines.append("    Compression yes")

    if keep_alive > 0:
        lines.append(f"    ServerAliveInterval {keep_alive}")
        lines.append("    ServerAliveCountMax 3")

    if extra_params:
        lines.append(f"    # GCM extra-params: {extra_params}")

    return "\n".join(lines)


def _parse_tunnel_to_proxyjump(raw: str) -> str:
    """Convert a GCM tunnel string to an SSH ``ProxyJump`` value.

    GCM format: ``user@jumphost:local_port:dest_host:dest_port``

    Args:
        raw: Raw tunnel string from gcm.conf.

    Returns:
        ProxyJump string (e.g. ``ops@bastion.example.com:2222``), or empty
        string if *raw* is malformed.
    """
    if not raw:
        return ""
    try:
        at_idx = raw.find("@")
        jump_user = raw[:at_idx] if at_idx != -1 else ""
        rest = raw[at_idx + 1 :] if at_idx != -1 else raw

        colon_idx = rest.find(":")
        jump_host = rest[:colon_idx] if colon_idx != -1 else rest
        jump_port = DEFAULT_SSH_PORT

        if colon_idx != -1:
            after_first_colon = rest[colon_idx + 1 :]
            next_colon = after_first_colon.find(":")
            port_str = after_first_colon[:next_colon] if next_colon != -1 else after_first_colon
            try:
                jump_port = int(port_str)
            except ValueError:
                jump_port = DEFAULT_SSH_PORT

        if not jump_host:
            return ""

        user_prefix = f"{jump_user}@" if jump_user else ""
        port_suffix = f":{jump_port}" if jump_port != DEFAULT_SSH_PORT else ""
        return f"{user_prefix}{jump_host}{port_suffix}"
    except Exception as exc:
        logger.warning(
            "_parse_tunnel_to_proxyjump | parse error | raw={raw} exc={exc}", raw=raw, exc=exc
        )
        return ""


# ---------------------------------------------------------------------------
# ~/.ssh/config writer
# ---------------------------------------------------------------------------


def _write_ssh_config(ssh_config_path: Path, stanzas: dict[str, str]) -> None:
    """Merge SSH stanzas into ~/.ssh/config inside sentinel markers.

    The block between ``_SSH_MARKER_BEGIN`` / ``_SSH_MARKER_END`` is replaced
    on every call; content outside the markers is preserved.

    Args:
        ssh_config_path: Path to the target ``~/.ssh/config``.
        stanzas: Mapping of alias → rendered stanza string.

    Raises:
        OSError: When the file cannot be written.
    """
    existing = ""
    if ssh_config_path.exists():
        existing = ssh_config_path.read_text(encoding="utf-8")

    # Strip existing managed block
    if _SSH_MARKER_BEGIN in existing:
        begin = existing.find(_SSH_MARKER_BEGIN)
        end = existing.find(_SSH_MARKER_END)
        if end != -1:
            tail = existing[end + len(_SSH_MARKER_END) :]
            existing = existing[:begin] + tail.lstrip("\n")
            logger.debug("_write_ssh_config | removed previous managed block")

    block_lines = [_SSH_MARKER_BEGIN]
    block_lines.append(
        f"# Generated by gcm_ssh_migrate.py — {datetime.now().isoformat(timespec='seconds')}"
    )
    block_lines.append(f"# {len(stanzas)} SSH host(s) managed here")
    block_lines.append("")
    for stanza in stanzas.values():
        block_lines.append(stanza)
        block_lines.append("")
    block_lines.append(_SSH_MARKER_END)

    separator = "\n" if existing and not existing.endswith("\n\n") else ""
    final = existing + separator + "\n".join(block_lines) + "\n"

    ssh_config_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    ssh_config_path.write_text(final, encoding="utf-8")
    ssh_config_path.chmod(0o600)
    logger.info(
        "_write_ssh_config | written | path={path} hosts={n}",
        path=ssh_config_path,
        n=len(stanzas),
    )


# ---------------------------------------------------------------------------
# gcm.conf rewriter
# ---------------------------------------------------------------------------


def _rewrite_gcm_conf(gcm_conf_path: Path, migrated_aliases: set[str]) -> None:
    """Rewrite gcm.conf in-place, stripping SSH-only keys from migrated entries.

    For each section in *migrated_aliases*:
      - Removes all keys in :data:`GCM_KEYS_SSH_ONLY`.
      - Sets ``ssh_config_managed = true``.
      - Replaces ``description`` with :data:`_MANAGED_DESCRIPTION`.

    Non-SSH entries and non-migrated SSH entries are written back verbatim.

    Args:
        gcm_conf_path: Path to the gcm.conf to rewrite.
        migrated_aliases: Set of host aliases that were migrated.

    Raises:
        OSError: When the file cannot be written.
    """
    cp = configparser.RawConfigParser()
    cp.optionxform = str  # preserve key case
    cp.read(str(gcm_conf_path), encoding="utf-8")

    for section in cp.sections():
        if not section.startswith("host "):
            continue

        alias = section[5:].strip()
        name = _cp_get(cp, section, "name")
        if alias not in migrated_aliases:
            continue

        # Remove SSH-only keys
        for key in GCM_KEYS_SSH_ONLY:
            if cp.has_option(section, key):
                cp.remove_option(section, key)
                logger.debug(
                    "_rewrite_gcm_conf | removed key | alias={alias} name={name} key={key}",
                    alias=alias,
                    name=name,
                    key=key,
                )

        # Mark as managed + update description
        safe_name = name.replace(" ", "_")
        cp.set(section, "ssh_config_managed", "true")
        cp.set(section, "description", _MANAGED_DESCRIPTION.format(name=name))
        cp.set(section, "name", safe_name)
        cp.set(section, "host", safe_name)
        logger.info(
            "_rewrite_gcm_conf | patched section | alias={alias} name={name}",
            alias=alias,
            name=name,
        )

    with gcm_conf_path.open("w", encoding="utf-8") as fh:
        cp.write(fh)

    gcm_conf_path.chmod(0o600)
    logger.info("_rewrite_gcm_conf | written | path={path}", path=gcm_conf_path)


# ---------------------------------------------------------------------------
# Public API — callable from gnome_connection_manager.py
# ---------------------------------------------------------------------------


def migrate_ssh_hosts(
    gcm_conf: Path | str | None = None,
    ssh_config: Path | str | None = None,
    *,
    dry_run: bool = False,
) -> dict[str, list[str]]:
    """Migrate all SSH hosts from gcm.conf to ~/.ssh/config.

    This is the single entry point intended to be called from
    ``gnome_connection_manager.py``.

    Args:
        gcm_conf: Path to gcm.conf. Defaults to ``~/.gcm/gcm.conf``.
        ssh_config: Path to the SSH config file. Defaults to ``~/.ssh/config``.
        dry_run: When ``True``, compute everything but write nothing.

    Returns:
        A result dict with keys:

        - ``"migrated"``  — list of alias strings successfully migrated
        - ``"skipped"``   — list of alias strings skipped (non-SSH)
        - ``"already"``   — list of alias strings already managed
        - ``"backups"``   — list of backup file paths created (as strings)
        - ``"errors"``    — list of error messages

    Raises:
        FileNotFoundError: When gcm.conf does not exist.
        configparser.Error: When gcm.conf cannot be parsed.
    """
    gcm_path = Path(gcm_conf).expanduser() if gcm_conf else Path.home() / ".gcm" / "gcm.conf"
    ssh_path = Path(ssh_config).expanduser() if ssh_config else Path.home() / ".ssh" / "config"

    logger.info(
        "migrate_ssh_hosts | start | gcm={gcm} ssh={ssh} dry_run={dry}",
        gcm=gcm_path,
        ssh=ssh_path,
        dry=dry_run,
    )

    if not gcm_path.exists():
        raise FileNotFoundError(f"gcm.conf not found: {gcm_path}")

    cp = configparser.RawConfigParser()
    cp.optionxform = str
    cp.read(str(gcm_path), encoding="utf-8")

    result: dict[str, list[str]] = {
        "migrated": [],
        "skipped": [],
        "already": [],
        "backups": [],
        "errors": [],
    }

    stanzas: dict[str, str] = {}
    migrated_aliases: set[str] = set()

    for section in cp.sections():
        if not section.startswith("host "):
            continue

        alias = section[5:].strip()
        conn_type = _cp_getint(cp, section, "type", GCM_TYPE_SSH)
        hostname = _cp_get(cp, section, "host")
        name = _cp_get(cp, section, "name")
        if conn_type != GCM_TYPE_SSH:
            logger.debug(
                "migrate_ssh_hosts | skip non-SSH | alias={alias} name={name} type={t}",
                alias=alias,
                name=name,
                t=conn_type,
            )
            result["skipped"].append("{alias}/{name}")
            continue

        already = _cp_getbool(cp, section, "ssh_config_managed")
        if already:
            logger.debug(
                "migrate_ssh_hosts | already managed | alias={alias} name={name}",
                alias=alias,
                name=name,
            )
            result["already"].append("{alias}/{name}")
            continue

        if not hostname:
            msg = f"alias={alias}: no hostname, skipping"
            logger.warning("migrate_ssh_hosts | {msg}", msg=msg)
            result["errors"].append(msg)
            continue

        if not name:
            msg = f"alias={alias}: no name, skipping"
            logger.warning("migrate_ssh_hosts | {msg}", msg=msg)
            result["errors"].append(msg)
            continue

        stanza = _render_ssh_stanza(name, hostname, cp, section)
        stanzas[name] = stanza
        migrated_aliases.add(alias)
        result["migrated"].append("{alias}/{name}")
        logger.debug(
            "migrate_ssh_hosts | queued | alias={alias} name={name}", alias=alias, name=name
        )

    if not migrated_aliases:
        logger.info("migrate_ssh_hosts | nothing to migrate")
        return result

    if dry_run:
        logger.info("migrate_ssh_hosts | dry-run — no files written")
        for alias, stanza in stanzas.items():
            logger.info(
                "migrate_ssh_hosts | [dry-run] stanza for {alias}/{name}:\n{stanza}",
                alias=alias,
                name=name,
                stanza=stanza,
            )
        return result

    # ------------------------------------------------------------------
    # Backups — must happen before any write
    # ------------------------------------------------------------------
    for path in (gcm_path, ssh_path):
        backup = backup_file(path)
        if backup:
            result["backups"].append(str(backup))

    # ------------------------------------------------------------------
    # Write ~/.ssh/config
    # ------------------------------------------------------------------
    # Load any stanzas already managed from a previous run so they are
    # preserved alongside the new ones.
    existing_stanzas = _load_existing_stanzas(ssh_path)
    merged = {**existing_stanzas, **stanzas}  # new entries overwrite old

    try:
        _write_ssh_config(ssh_path, merged)
    except OSError as exc:
        msg = f"Failed to write {ssh_path}: {exc}"
        logger.error("migrate_ssh_hosts | {msg}", msg=msg)
        result["errors"].append(msg)
        return result

    # ------------------------------------------------------------------
    # Rewrite gcm.conf
    # ------------------------------------------------------------------
    # Re-read to include "already managed" aliases so their stanzas are
    # preserved in ~/.ssh/config as well.
    all_managed = migrated_aliases | set(result["already"])

    try:
        _rewrite_gcm_conf(gcm_path, migrated_aliases)
    except OSError as exc:
        msg = f"Failed to rewrite {gcm_path}: {exc}"
        logger.error("migrate_ssh_hosts | {msg}", msg=msg)
        result["errors"].append(msg)
        return result

    logger.info(
        "migrate_ssh_hosts | done | migrated={m} skipped={s} already={a} errors={e}",
        m=len(result["migrated"]),
        s=len(result["skipped"]),
        a=len(result["already"]),
        e=len(result["errors"]),
    )
    return result


def _load_existing_stanzas(ssh_path: Path) -> dict[str, str]:
    """Extract the per-host stanzas from the existing managed block.

    Reads the ``_SSH_MARKER_BEGIN`` / ``_SSH_MARKER_END`` block and splits
    it into individual ``Host …`` stanzas, keyed by alias.

    Args:
        ssh_path: Path to ``~/.ssh/config``.

    Returns:
        Dict mapping alias → stanza string (may be empty if no block exists).
    """
    if not ssh_path.exists():
        return {}

    text = ssh_path.read_text(encoding="utf-8")
    begin = text.find(_SSH_MARKER_BEGIN)
    end = text.find(_SSH_MARKER_END)
    if begin == -1 or end == -1:
        return {}

    block = text[begin + len(_SSH_MARKER_BEGIN) : end]
    stanzas: dict[str, str] = {}
    current_lines: list[str] = []
    current_alias: str | None = None

    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("Host ") and not stripped.startswith("HostName"):
            if current_alias is not None:
                stanzas[current_alias] = "\n".join(current_lines).strip()
            current_alias = stripped[5:].strip()
            current_lines = [line]
        elif current_alias is not None:
            current_lines.append(line)

    if current_alias is not None and current_lines:
        stanzas[current_alias] = "\n".join(current_lines).strip()

    logger.debug("_load_existing_stanzas | found={n}", n=len(stanzas))
    return stanzas


# ---------------------------------------------------------------------------
# GTK UI helper — patch the Edit-Host dialog
# ---------------------------------------------------------------------------


def patch_edit_host_dialog(
    builder: object, host_section: str, cp: configparser.RawConfigParser
) -> None:
    """Grey out SSH fields and show the red managed-notice in the Edit dialog.

    Call this from the GCM dialog ``on_show`` callback after loading the host
    data into the form widgets.  The function is a no-op when the host is not
    managed by ``~/.ssh/config``.

    Glade widget IDs used (GCM fork — dialogue ``wHost``):

    * ``txtPort``        — GtkSpinButton for the port number
    * ``txtPrivateKey``  — GtkEntry for the SSH private-key path
    * ``btnBrowse``      — GtkButton to pick the private key
    * ``txtKeepAlive``   — GtkSpinButton for keep-alive interval
    * ``chkKeepAlive``   — GtkCheckButton enabling keep-alive
    * ``txtExtraParams`` — GtkEntry for extra SSH params
    * ``chkX11``         — GtkCheckButton for X11 forwarding
    * ``chkAgent``       — GtkCheckButton for agent forwarding
    * ``chkCompression`` — GtkCheckButton for compression
    * ``treeTunel``      — GtkTreeView for tunnels / port forwarding
    * ``txtDescription`` — GtkEntry holding the red managed-notice

    Args:
        builder: A ``Gtk.Builder`` instance that has already loaded the .glade file.
        host_section: The configparser section name, e.g. ``"host myserver"``.
        cp: Parsed gcm.conf (``configparser.RawConfigParser``).
    """
    managed = _cp_getbool(cp, host_section, "ssh_config_managed")
    if not managed:
        return

    alias = host_section[5:].strip() if host_section.startswith("host ") else host_section
    safe_alias = alias.replace(" ", "_")

    try:
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk

        def _get_widget(widget_id: str) -> object | None:
            obj = builder.get_object(widget_id)
            if obj is None:
                logger.debug("patch_edit_host_dialog | widget not found | id={wid}", wid=widget_id)
            return obj

        # Disable every SSH-related field (IDs réels du fork GCM, cf. wHost).
        for widget_id in (
            "txtPort",  # GtkSpinButton
            "txtPrivateKey",  # GtkEntry
            "btnBrowse",  # GtkButton (choix de la clé privée)
            "txtKeepAlive",  # GtkSpinButton
            "chkKeepAlive",  # GtkCheckButton
            "txtExtraParams",  # GtkEntry
            "chkX11",  # GtkCheckButton
            "chkAgent",  # GtkCheckButton
            "chkCompression",  # GtkCheckButton
            "treeTunel",  # GtkTreeView (tunnels / port forwarding)
        ):
            w = _get_widget(widget_id)
            if w is not None:
                w.set_sensitive(False)

        # Notice rouge : l'entry "description" contient déjà _MANAGED_DESCRIPTION
        # après migration. On la colore en rouge, la passe en lecture seule, et
        # on duplique le texte en infobulle. (txtDescription est une GtkEntry —
        # pas de set_markup possible, d'où le CSS.)
        notice = _MANAGED_DESCRIPTION.format(alias=safe_alias)
        desc = _get_widget("txtDescription")
        if desc is not None:
            if not (desc.get_text() or "").strip():
                desc.set_text(notice)
            desc.set_tooltip_text(notice)
            desc.set_editable(False)
            try:
                provider = Gtk.CssProvider()
                provider.load_from_data(b"entry { color: #cc0000; font-weight: bold; }")
                desc.get_style_context().add_provider(
                    provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
            except Exception:
                pass

        logger.info(
            "patch_edit_host_dialog | dialog patched for managed host | alias={alias}",
            alias=alias,
        )

    except Exception as exc:
        # Never crash GCM just because the UI patch failed
        logger.warning(
            "patch_edit_host_dialog | GTK patch failed | alias={alias} exc={exc}",
            alias=alias,
            exc=exc,
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    p = argparse.ArgumentParser(
        description="Migrate GCM SSH hosts to ~/.ssh/config",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--gcm-conf",
        default=str(Path.home() / ".gcm" / "gcm.conf"),
        metavar="PATH",
        help="Path to gcm.conf (default: ~/.gcm/gcm.conf)",
    )
    p.add_argument(
        "--ssh-config",
        default=str(Path.home() / ".ssh" / "config"),
        metavar="PATH",
        help="Path to SSH config (default: ~/.ssh/config)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing any file",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log verbosity (default: INFO)",
    )
    return p


def _configure_logging(level: str) -> None:
    """Configure loguru output.

    Args:
        level: Minimum log level string.
    """
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Argument list (defaults to sys.argv).

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.log_level)

    try:
        result = migrate_ssh_hosts(
            gcm_conf=args.gcm_conf,
            ssh_config=args.ssh_config,
            dry_run=args.dry_run,
        )
    except FileNotFoundError as exc:
        logger.error("main | {exc}", exc=exc)
        return 1
    except configparser.Error as exc:
        logger.error("main | config parse error | {exc}", exc=exc)
        return 1

    prefix = "[DRY-RUN] " if args.dry_run else ""
    logger.info(
        "main | {prefix}migrated={m} skipped={s} already={a} backups={b} errors={e}",
        prefix=prefix,
        m=len(result["migrated"]),
        s=len(result["skipped"]),
        a=len(result["already"]),
        b=len(result["backups"]),
        e=len(result["errors"]),
    )

    if result["migrated"]:
        logger.info("main | migrated hosts: {hosts}", hosts=", ".join(result["migrated"]))
    if result["backups"]:
        logger.info("main | backups created: {files}", files=", ".join(result["backups"]))
    if result["errors"]:
        for err in result["errors"]:
            logger.error("main | error: {err}", err=err)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

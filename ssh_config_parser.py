"""Parses, validates, and writes SSH configuration files.

Adapté de SSH-Studio (BuddySirJava/SSH-Studio, GPLv3)
pour gnome-connection-manager (MathildeDec/gnome-connection-manager).

Modifications :
- stdlib logging remplacé par loguru (avec fallback)
- Annotations modernisées (list/dict/tuple minuscules, X | Y)
- Docstrings Google ajoutées
"""

from __future__ import annotations

import fnmatch  # noqa: F401  (réexporté via __all__ pour usage futur)
import glob
import os
import re
import shutil
import stat
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)  # type: ignore[assignment]

__all__ = [
    "SSHOption",
    "SSHHost",
    "SSHConfig",
    "SSHConfigParser",
]


@dataclass
class SSHOption:
    """Représente une directive clé/valeur dans un bloc Host.

    Attributes:
        key: Nom de la directive SSH (ex. ``HostName``).
        value: Valeur associée.
        indentation: Préfixe d'indentation conservé à la réécriture.
    """

    key: str
    value: str
    indentation: str = "    "

    def __str__(self) -> str:
        """Sérialise la directive avec son indentation d'origine."""
        return f"{self.indentation}{self.key} {self.value}".rstrip()


@dataclass
class SSHHost:
    """Représente un bloc ``Host`` complet avec ses options.

    Attributes:
        patterns: Liste des patterns d'alias (ex. ``["myserver", "*.example.com"]``).
        options: Directives SSH du bloc.
        start_line: Numéro de ligne de début dans le fichier source.
        end_line: Numéro de ligne de fin dans le fichier source.
        raw_lines: Lignes brutes originales (pour reconstruction fidèle).
    """

    patterns: list[str] = field(default_factory=list)
    options: list[SSHOption] = field(default_factory=list)
    start_line: int = -1
    end_line: int = -1
    raw_lines: list[str] = field(default_factory=list)

    @classmethod
    def from_raw_lines(cls, lines: list[str]) -> SSHHost:
        """Construit un SSHHost depuis une liste de lignes brutes.

        Args:
            lines: Lignes brutes d'un seul bloc Host (avec commentaires).

        Returns:
            Instance SSHHost peuplée.

        Raises:
            ValueError: Si aucune directive ``Host`` n'est trouvée ou s'il y en a plusieurs.
        """
        host = cls()
        found_host_line = False
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                host.raw_lines.append(line)
                continue

            if stripped.lower().startswith("host ") and not found_host_line:
                patterns = stripped.split(None, 1)[1].split()
                host.patterns = patterns
                host.raw_lines.append(line)
                found_host_line = True
                continue
            elif stripped.lower().startswith("host ") and found_host_line:
                raise ValueError(
                    "Multiple Host declarations found within a single raw host block."
                )

            m = re.match(r"^(\S+)\s+(.+)$", stripped)
            if m:
                key, value = m.group(1), m.group(2)
                indentation = line[: len(line) - len(line.lstrip())]
                host.options.append(SSHOption(key=key, value=value, indentation=indentation))
                host.raw_lines.append(line)
            else:
                host.raw_lines.append(line)

        if not found_host_line:
            raise ValueError("No Host declaration found in raw host block.")

        return host

    def get_option(self, key: str) -> str | None:
        """Retourne la valeur d'une directive (insensible à la casse).

        Args:
            key: Nom de la directive à rechercher.

        Returns:
            Valeur de la directive, ou ``None`` si absente.
        """
        for opt in self.options:
            if opt.key.lower() == key.lower():
                return opt.value
        return None

    def set_option(self, key: str, value: str) -> None:
        """Définit ou ajoute une directive.

        Args:
            key: Nom de la directive.
            value: Valeur à affecter.
        """
        for opt in self.options:
            if opt.key.lower() == key.lower():
                opt.value = value
                return
        self.options.append(SSHOption(key=key, value=value))

    def remove_option(self, key: str) -> bool:
        """Supprime une directive si elle existe.

        Args:
            key: Nom de la directive à supprimer.

        Returns:
            ``True`` si la directive a été trouvée et supprimée, ``False`` sinon.
        """
        for i, opt in enumerate(self.options):
            if opt.key.lower() == key.lower():
                del self.options[i]
                return True
        return False


@dataclass
class SSHConfig:
    """Représente l'intégralité d'un fichier ``~/.ssh/config`` parsé.

    Attributes:
        file_path: Chemin vers le fichier de configuration.
        hosts: Liste ordonnée des blocs Host.
        global_options: Directives hors de tout bloc Host.
        include_directives: Directives ``Include`` détectées.
        includes_resolved: Contenu des fichiers inclus (chemin → lignes).
        original_lines: Lignes brutes d'origine (pour détection de modifications).
    """

    file_path: Path
    hosts: list[SSHHost] = field(default_factory=list)
    global_options: list[SSHOption] = field(default_factory=list)
    include_directives: list[str] = field(default_factory=list)
    includes_resolved: dict[Path, list[str]] = field(default_factory=dict)
    original_lines: list[str] = field(default_factory=list)

    def generate_content(self) -> str:
        """Génère le contenu texte du fichier de configuration.

        Returns:
            Contenu SSH config prêt à être écrit sur disque.
        """
        lines: list[str] = []
        for opt in self.global_options:
            lines.append(str(opt))
        if self.global_options and (not lines or lines[-1] != ""):
            lines.append("")
        for host in self.hosts:
            lines.append(f"Host {' '.join(host.patterns)}")
            for opt in host.options:
                lines.append(str(opt))
            lines.append("")
        while lines and lines[-1] == "":
            lines.pop()
        for inc in self.include_directives:
            lines.append(f"Include {inc}")
        return "\n".join(lines) + "\n"

    def is_dirty(self) -> bool:
        """Indique si le contenu a été modifié depuis le chargement.

        Returns:
            ``True`` si des modifications non sauvegardées existent.
        """
        current = self.generate_content().splitlines()
        original = [line.rstrip("\n") for line in self.original_lines]
        while current and current[-1] == "":
            current.pop()
        while original and original[-1] == "":
            original.pop()
        return current != original

    def get_host(self, alias: str) -> SSHHost | None:
        """Recherche un bloc Host par son alias exact.

        Args:
            alias: Pattern d'alias à rechercher.

        Returns:
            Le SSHHost correspondant, ou ``None`` si introuvable.
        """
        for h in self.hosts:
            if alias in h.patterns:
                return h
        return None

    def add_host(self, host: SSHHost) -> None:
        """Ajoute un bloc Host à la fin de la liste.

        Args:
            host: Bloc SSH à ajouter.
        """
        self.hosts.append(host)

    def remove_host(self, host: SSHHost) -> bool:
        """Supprime un bloc Host de la liste.

        Args:
            host: Bloc SSH à supprimer.

        Returns:
            ``True`` si trouvé et supprimé, ``False`` sinon.
        """
        try:
            self.hosts.remove(host)
            return True
        except ValueError:
            return False


class SSHConfigParser:
    """Lit, valide et écrit ``~/.ssh/config`` de façon sûre.

    Attributes:
        config_path: Chemin vers le fichier de configuration SSH.
        config: Objet SSHConfig en mémoire après parsing.
        auto_backup_enabled: Si ``True``, un backup est créé avant chaque écriture.
        backup_dir: Répertoire de backup (par défaut : même dossier que config).
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialise le parser.

        Args:
            config_path: Chemin explicite vers le fichier config SSH.
                Par défaut ``~/.ssh/config``.
        """
        self.config_path: Path = config_path or Path.home() / ".ssh" / "config"
        self.config: SSHConfig = SSHConfig(file_path=self.config_path)
        self._have_backed_up_this_session: bool = False
        self.auto_backup_enabled: bool = True
        self.backup_dir: Path | None = None

    def parse(self) -> SSHConfig:
        """Lit et parse le fichier de configuration SSH.

        Returns:
            Objet SSHConfig peuplé depuis le fichier.
        """
        if not self.config_path.exists():
            logger.warning("SSH config file not found: {path}", path=self.config_path)
            return self.config

        with self.config_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        self.config.original_lines = [line.rstrip("\n") for line in lines]

        self._parse_main_lines(self.config.original_lines)
        self._resolve_includes()
        return self.config

    def write(self, backup: bool = True) -> None:
        """Écrit la configuration sur disque (écriture atomique).

        Crée un backup automatique lors du premier appel de la session
        si ``auto_backup_enabled`` est ``True``.

        Args:
            backup: Si ``False``, désactive le backup pour cet appel.
        """
        content = self._generate_content()

        if self.config_path.exists():
            try:
                with self.config_path.open("r", encoding="utf-8") as f:
                    current = f.read()
                if current == content:
                    return
            except OSError:
                pass

        effective_backup = backup and self.auto_backup_enabled and self.config_path.exists()
        if effective_backup and not self._have_backed_up_this_session:
            self._backup_file()
            self._have_backed_up_this_session = True

        self._atomic_write(content)

    def validate(self) -> list[str]:
        """Valide la configuration chargée.

        Vérifie :
        - Absence de doublons d'alias
        - Ports dans la plage 1–65535
        - Existence des IdentityFile référencés

        Returns:
            Liste de messages d'erreur (vide si tout est valide).
        """
        errors: list[str] = []
        seen: dict[str, SSHHost] = {}

        for host in self.config.hosts:
            for pat in host.patterns:
                if pat in seen:
                    errors.append(f"Duplicate host alias: {pat}")
                else:
                    seen[pat] = host

        for host in self.config.hosts:
            port = host.get_option("Port")
            if port:
                try:
                    p = int(port)
                    if p < 1 or p > 65535:
                        errors.append(f"Invalid port for host {host.patterns[0]}: {port}")
                except ValueError:
                    errors.append(f"Port is not an integer for host {host.patterns[0]}: {port}")

        for host in self.config.hosts:
            ident = host.get_option("IdentityFile")
            if ident:
                path = Path(ident).expanduser()
                if not path.is_absolute():
                    path = Path.home() / ".ssh" / ident
                if not path.exists():
                    errors.append(f"IdentityFile not found for host {host.patterns[0]}: {ident}")

        return errors

    # ------------------------------------------------------------------
    # Méthodes privées
    # ------------------------------------------------------------------

    def _parse_main_lines(self, lines: list[str]) -> None:
        r"""Parse les lignes brutes et peuple self.config.

        Args:
            lines: Lignes du fichier config (sans ``\n`` terminaux).
        """
        self.config.hosts.clear()
        self.config.global_options.clear()
        self.config.include_directives.clear()

        current_host: SSHHost | None = None
        in_host = False

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                if in_host and current_host is not None:
                    current_host.raw_lines.append(line)
                continue

            if stripped.lower().startswith("include "):
                include_arg = stripped.split(None, 1)[1]
                self.config.include_directives.append(include_arg)
                continue

            if stripped.lower().startswith("host "):
                if current_host is not None:
                    current_host.end_line = idx - 1
                    self.config.hosts.append(current_host)
                patterns = stripped.split(None, 1)[1].split()
                current_host = SSHHost(patterns=patterns, start_line=idx, raw_lines=[line])
                in_host = True
                continue

            m = re.match(r"^(\S+)\s+(.+)$", stripped)
            if m:
                key, value = m.group(1), m.group(2)
                indentation = line[: len(line) - len(line.lstrip())]
                opt = SSHOption(key=key, value=value, indentation=indentation)
                if in_host and current_host is not None:
                    current_host.options.append(opt)
                    current_host.raw_lines.append(line)
                else:
                    self.config.global_options.append(opt)
                continue

            if in_host and current_host is not None:
                current_host.raw_lines.append(line)

        if current_host is not None:
            current_host.end_line = len(lines) - 1
            self.config.hosts.append(current_host)

    def _resolve_includes(self) -> None:
        """Résout les directives Include et stocke le contenu des fichiers inclus."""
        resolved: dict[Path, list[str]] = {}
        base_dir = self.config_path.parent

        for pattern in self.config.include_directives:
            expanded = os.path.expanduser(pattern)
            if not os.path.isabs(expanded):
                expanded = str(base_dir / expanded)

            try:
                matches = glob.glob(expanded, recursive=False)
                if not matches and "**" in expanded:
                    matches = glob.glob(expanded, recursive=True)
            except OSError:
                matches = []

            for path_str in matches:
                p = Path(path_str)
                try:
                    with p.open("r", encoding="utf-8") as f:
                        resolved[p] = f.readlines()
                except OSError:
                    continue

        self.config.includes_resolved = resolved

    def _backup_file(self) -> None:
        """Crée une copie de sauvegarde horodatée du fichier config."""
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        target_dir: Path
        if self.backup_dir:
            target_dir = Path(self.backup_dir).expanduser()
        else:
            target_dir = self.config_path.parent
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            target_dir = self.config_path.parent
        backup = (target_dir / self.config_path.name).with_suffix(f".{ts}.bak")
        try:
            shutil.copy2(self.config_path, backup)
            logger.info("Backup created: {backup}", backup=backup)
        except OSError as exc:
            logger.warning("Failed to create backup: {exc}", exc=exc)

    def _generate_content(self) -> str:
        """Génère le contenu final à écrire.

        Returns:
            Contenu SSH config sous forme de chaîne.
        """
        return self.config.generate_content()

    def _atomic_write(self, content: str) -> None:
        """Écrit ``content`` dans un fichier temporaire puis le déplace atomiquement.

        Args:
            content: Contenu complet à écrire.

        Raises:
            OSError: En cas d'échec d'écriture ou de déplacement.
        """
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(self.config_path.parent),
            delete=False,
        )
        tmp_path = Path(tmp.name)
        try:
            tmp.write(content)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            if self.config_path.exists():
                st = self.config_path.stat()
                os.chmod(tmp_path, stat.S_IMODE(st.st_mode))
            else:
                os.chmod(tmp_path, 0o600)
            os.replace(tmp_path, self.config_path)
        except Exception:
            try:
                tmp.close()
            except Exception:
                pass
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise

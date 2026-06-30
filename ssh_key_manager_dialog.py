"""Gestionnaire de clés SSH : liste, génération, import, suppression, copie.

Adapté de SSH-Studio (BuddySirJava/SSH-Studio, GPLv3) — GTK4/Adw → GTK3.

Fenêtre indépendante (non-modale) présentant :
- Onglet « Private keys » : clés privées de ~/.ssh/ avec leur .pub associée
- Onglet « Public keys » : clés publiques orphelines
- Barre d'actions : Generate, Import, Copy public key, Reveal in files, Delete
"""

from __future__ import annotations

import getpass
import os
import shutil
import socket
import stat
import subprocess
from gettext import gettext as _
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

try:
    from loguru import logger
except ImportError:
    import logging as _stdlib_logging

    logger = _stdlib_logging.getLogger(__name__)  # type: ignore[assignment]

__all__ = ["SSHKeyManagerDialog", "get_default_ssh_key_comment"]

_SSH_DIR = Path.home() / ".ssh"

# Types de clé supportés par ssh-keygen
_KEY_TYPES: list[str] = ["ed25519", "rsa", "ecdsa"]
_RSA_SIZES: list[str] = ["2048", "3072", "4096"]

# Noms de fichiers exclus du scan
_EXCLUDED_NAMES: frozenset[str] = frozenset(
    {"config", "known_hosts", "authorized_keys", "environment"}
)


def get_default_ssh_key_comment() -> str:
    """Retourne un commentaire par défaut pour ssh-keygen (user@hostname).

    Returns:
        Chaîne au format ``user@hostname``.
    """
    try:
        username = getpass.getuser()
    except Exception:
        username = os.environ.get("USER") or os.environ.get("USERNAME") or "user"
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "localhost"
    return f"{username}@{hostname}"


def _copy_text_to_clipboard(text: str) -> bool:
    """Copie du texte dans le presse-papiers GTK3 (Gdk.Atom).

    Args:
        text: Texte à copier.

    Returns:
        True si la copie a réussi.
    """
    try:
        clip = Gtk.Clipboard.get(Gdk.Atom.intern("CLIPBOARD", False))
        clip.set_text(text, -1)
        return True
    except Exception as exc:
        logger.warning("_copy_text_to_clipboard | GTK failed: {exc}", exc=exc)

    # Fallback CLI (Wayland / X11)
    for cmd in [
        ["wl-copy"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
    ]:
        try:
            res = subprocess.run(cmd, input=text, text=True, capture_output=True, timeout=3)
            if res.returncode == 0:
                return True
        except Exception:
            continue
    return False


class _GenerateKeyDialog(Gtk.Dialog):
    """Dialogue de saisie des paramètres ssh-keygen.

    Interne à ce module — utilisé par SSHKeyManagerDialog._on_generate.

    Args:
        parent: Fenêtre parente.
    """

    def __init__(self, parent: Gtk.Window) -> None:
        """Initialise le formulaire de génération de clé.

        Args:
            parent: Fenêtre parente pour centrage modal.
        """
        super().__init__(
            title=_("Generate SSH Key"),
            transient_for=parent,
            modal=True,
            destroy_with_parent=True,
        )
        self.set_default_size(420, 0)
        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self._btn_gen = self.add_button(_("⚙ Generate"), Gtk.ResponseType.OK)
        self._btn_gen.get_style_context().add_class("suggested-action")
        self._build_ui()
        self.show_all()

    def _build_ui(self) -> None:
        """Construit la grille de formulaire."""
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(8)
        grid.set_margin_start(16)
        grid.set_margin_end(16)
        grid.set_margin_top(12)
        grid.set_margin_bottom(12)

        # Type
        lbl_type = Gtk.Label(label=_("Key type:"), xalign=1.0)
        self._cmb_type = Gtk.ComboBoxText()
        for t in _KEY_TYPES:
            self._cmb_type.append_text(t)
        self._cmb_type.set_active(0)
        self._cmb_type.connect("changed", self._on_type_changed)
        grid.attach(lbl_type, 0, 0, 1, 1)
        grid.attach(self._cmb_type, 1, 0, 1, 1)

        # Taille RSA (visible uniquement si type == rsa)
        self._lbl_size = Gtk.Label(label=_("RSA size:"), xalign=1.0)
        self._cmb_size = Gtk.ComboBoxText()
        for s in _RSA_SIZES:
            self._cmb_size.append_text(s)
        self._cmb_size.set_active(1)  # 3072 par défaut
        grid.attach(self._lbl_size, 0, 1, 1, 1)
        grid.attach(self._cmb_size, 1, 1, 1, 1)
        self._lbl_size.hide()
        self._cmb_size.hide()

        # Nom du fichier
        lbl_name = Gtk.Label(label=_("File name:"), xalign=1.0)
        self._entry_name = Gtk.Entry()
        self._entry_name.set_placeholder_text("id_ed25519")
        self._entry_name.set_hexpand(True)
        self._entry_name.set_tooltip_text(_("Saved in ~/.ssh/ — leave blank for default name"))
        grid.attach(lbl_name, 0, 2, 1, 1)
        grid.attach(self._entry_name, 1, 2, 1, 1)

        # Commentaire
        lbl_comment = Gtk.Label(label=_("Comment:"), xalign=1.0)
        self._entry_comment = Gtk.Entry()
        self._entry_comment.set_text(get_default_ssh_key_comment())
        self._entry_comment.set_hexpand(True)
        grid.attach(lbl_comment, 0, 3, 1, 1)
        grid.attach(self._entry_comment, 1, 3, 1, 1)

        # Passphrase
        lbl_pass = Gtk.Label(label=_("Passphrase:"), xalign=1.0)
        self._entry_pass = Gtk.Entry()
        self._entry_pass.set_visibility(False)
        self._entry_pass.set_placeholder_text(_("(empty = no passphrase)"))
        self._entry_pass.set_hexpand(True)
        grid.attach(lbl_pass, 0, 4, 1, 1)
        grid.attach(self._entry_pass, 1, 4, 1, 1)

        # Info
        lbl_info = Gtk.Label()
        lbl_info.set_markup(
            "<small><i>"
            + _("Keys are saved in <b>~/.ssh/</b> with permissions 600.")
            + "</i></small>"
        )
        lbl_info.set_xalign(0.0)
        lbl_info.set_line_wrap(True)
        grid.attach(lbl_info, 0, 5, 2, 1)

        self.get_content_area().pack_start(grid, True, True, 0)

    def _on_type_changed(self, _cmb: Gtk.ComboBoxText) -> None:
        """Affiche ou masque le champ de taille RSA selon le type sélectionné."""
        key_type = self._cmb_type.get_active_text() or "ed25519"
        visible = key_type == "rsa"
        self._lbl_size.set_visible(visible)
        self._cmb_size.set_visible(visible)

    def get_options(self) -> dict[str, str | int]:
        """Retourne les options saisies dans le formulaire.

        Returns:
            Dictionnaire avec les clés ``type``, ``size``, ``name``,
            ``comment``, ``passphrase``.
        """
        key_type = self._cmb_type.get_active_text() or "ed25519"
        size_str = self._cmb_size.get_active_text() or "3072"
        return {
            "type": key_type,
            "size": int(size_str) if key_type == "rsa" else 0,
            "name": self._entry_name.get_text().strip(),
            "comment": self._entry_comment.get_text().strip() or get_default_ssh_key_comment(),
            "passphrase": self._entry_pass.get_text(),
        }


class SSHKeyManagerDialog(Gtk.Window):
    """Gestionnaire de clés SSH — liste, génération, import, suppression, copie.

    Fenêtre GTK3 non-modale (peut coexister avec GCM).

    Layout :
    - Notebook à 2 onglets : Private Keys / Public Keys
    - Barre d'actions en bas : Generate, Import, Copy Public, Reveal, Delete
    - Barre de statut pour les notifications temporaires

    Example:
        mgr = SSHKeyManagerDialog(parent=self.window)
        mgr.show_all()
    """

    def __init__(self, parent: Gtk.Window) -> None:
        """Initialise le gestionnaire et charge la liste des clés.

        Args:
            parent: Fenêtre parente GCM (pour centrage).
        """
        super().__init__(title=_("SSH Key Manager"))
        self.set_transient_for(parent)
        self.set_default_size(680, 480)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self._ssh_dir = _SSH_DIR
        self._build_ui()
        self._load_keys()
        self._setup_keyboard()
        logger.info("SSHKeyManagerDialog | ouvert ssh_dir={d}", d=self._ssh_dir)

    # ------------------------------------------------------------------
    # Construction UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construit la fenêtre principale : notebook + barre d'actions + statut."""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

        # --- Notebook ---
        self._notebook = Gtk.Notebook()
        self._notebook.set_margin_start(8)
        self._notebook.set_margin_end(8)
        self._notebook.set_margin_top(8)
        vbox.pack_start(self._notebook, True, True, 0)

        self._priv_store, priv_tab = self._build_key_tab()
        self._pub_store, pub_tab = self._build_key_tab()
        self._notebook.append_page(priv_tab, Gtk.Label(label=_("Private keys")))
        self._notebook.append_page(pub_tab, Gtk.Label(label=_("Public keys")))

        # Référencer les TreeView pour la sélection
        self._priv_tree: Gtk.TreeView = priv_tab.get_children()[0]  # ScrolledWindow > TreeView
        self._pub_tree: Gtk.TreeView = pub_tab.get_children()[0]

        for tree in (self._priv_tree, self._pub_tree):
            tree.get_selection().connect("changed", self._on_selection_changed)

        # --- Barre d'actions ---
        btn_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_bar.set_margin_start(8)
        btn_bar.set_margin_end(8)
        btn_bar.set_margin_top(6)
        btn_bar.set_margin_bottom(6)

        btn_generate = Gtk.Button(label=_("⚙ Generate"))
        btn_generate.set_tooltip_text(_("Generate a new SSH key pair (ssh-keygen)"))
        btn_generate.connect("clicked", self._on_generate)

        btn_import = Gtk.Button(label=_("↑ Import"))
        btn_import.set_tooltip_text(_("Import an existing private key file into ~/.ssh/"))
        btn_import.connect("clicked", self._on_import)

        self._btn_copy = Gtk.Button(label=_("⎘ Copy public key"))
        self._btn_copy.set_tooltip_text(_("Copy the public key content to clipboard"))
        self._btn_copy.set_sensitive(False)
        self._btn_copy.connect("clicked", self._on_copy_public)

        self._btn_reveal = Gtk.Button(label=_("📂 Reveal"))
        self._btn_reveal.set_tooltip_text(_("Open ~/.ssh/ in the file manager"))
        self._btn_reveal.connect("clicked", self._on_reveal)

        self._btn_delete = Gtk.Button(label=_("🗑 Delete"))
        self._btn_delete.set_tooltip_text(_("Permanently delete the selected key"))
        self._btn_delete.set_sensitive(False)
        self._btn_delete.get_style_context().add_class("destructive-action")
        self._btn_delete.connect("clicked", self._on_delete)

        btn_close = Gtk.Button(label=_("Close"))
        btn_close.connect("clicked", lambda _w: self.destroy())

        for btn in (btn_generate, btn_import, self._btn_copy, self._btn_reveal, self._btn_delete):
            btn_bar.pack_start(btn, False, False, 0)
        btn_bar.pack_end(btn_close, False, False, 0)
        vbox.pack_start(Gtk.Separator(), False, False, 0)
        vbox.pack_start(btn_bar, False, False, 0)

        # --- Barre de statut ---
        self._status_bar = Gtk.Statusbar()
        self._status_ctx = self._status_bar.get_context_id("main")
        vbox.pack_start(self._status_bar, False, False, 0)

    def _build_key_tab(self) -> tuple[Gtk.ListStore, Gtk.ScrolledWindow]:
        """Crée un onglet avec un TreeView de clés.

        Returns:
            Tuple (ListStore, ScrolledWindow contenant le TreeView).
        """
        # Colonnes : [name, private_path, pub_path, fingerprint, perms_str, perms_ok, pub_exists]
        store = Gtk.ListStore(str, str, str, str, str, bool, bool)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_margin_start(0)
        sw.set_margin_end(0)

        tree = Gtk.TreeView(model=store)
        tree.set_headers_visible(True)

        # Nom
        renderer_name = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn(_("Name"), renderer_name, text=0)
        col_name.set_expand(True)
        col_name.set_sort_column_id(0)
        tree.append_column(col_name)

        # Fingerprint
        renderer_fp = Gtk.CellRendererText()
        renderer_fp.set_property("ellipsize", 3)
        col_fp = Gtk.TreeViewColumn(_("Fingerprint"), renderer_fp, text=3)
        col_fp.set_expand(True)
        tree.append_column(col_fp)

        # Permissions
        renderer_perms = Gtk.CellRendererText()
        col_perms = Gtk.TreeViewColumn(_("Perms"), renderer_perms, text=4)
        col_perms.set_min_width(70)
        tree.append_column(col_perms)

        # Pub ?
        renderer_pub = Gtk.CellRendererText()
        col_pub = Gtk.TreeViewColumn(_("Public key"))
        col_pub.pack_start(renderer_pub, True)
        col_pub.set_cell_data_func(renderer_pub, self._render_pub_status)
        col_pub.set_min_width(80)
        tree.append_column(col_pub)

        sw.add(tree)
        return store, sw

    # ------------------------------------------------------------------
    # Chargement
    # ------------------------------------------------------------------

    def _load_keys(self) -> None:
        """Scanne ~/.ssh/ et peuple les deux ListStore."""
        for store in (self._priv_store, self._pub_store):
            store.clear()

        if not self._ssh_dir.exists():
            self._notify(_("~/.ssh/ not found — no keys loaded"))
            return

        priv_count = 0
        pub_count = 0

        for path in sorted(self._ssh_dir.iterdir()):
            if not path.is_file():
                continue
            name = path.name
            if name in _EXCLUDED_NAMES or name.startswith("."):
                continue

            fp = self._get_fingerprint(path)
            perms_str, perms_ok = self._check_permissions(path)

            if name.endswith(".pub"):
                # Clé publique orpheline (sans clé privée)
                priv = path.with_suffix("")
                if not priv.exists():
                    self._pub_store.append([name, str(path), "", fp, perms_str, perms_ok, False])
                    pub_count += 1
            else:
                pub = path.with_name(name + ".pub")
                pub_exists = pub.exists()
                self._priv_store.append(
                    [
                        name,
                        str(path),
                        str(pub) if pub_exists else "",
                        fp,
                        perms_str,
                        perms_ok,
                        pub_exists,
                    ]
                )
                priv_count += 1

        self._notify(
            _("{priv} private key(s), {pub} public key(s) loaded from ~/.ssh/").format(
                priv=priv_count, pub=pub_count
            )
        )
        logger.debug(
            "SSHKeyManagerDialog._load_keys | priv={p} pub={q}", p=priv_count, q=pub_count
        )
        self._update_buttons()

    def _get_fingerprint(self, path: Path) -> str:
        """Calcule le fingerprint via ssh-keygen -lf.

        Args:
            path: Chemin du fichier de clé.

        Returns:
            Fingerprint abrégé ou chaîne vide.
        """
        try:
            result = subprocess.run(
                ["ssh-keygen", "-lf", str(path)],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                return parts[1][:32] if len(parts) >= 2 else ""
        except Exception as exc:
            logger.debug("_get_fingerprint | {path} → {exc}", path=path, exc=exc)
        return ""

    def _check_permissions(self, path: Path) -> tuple[str, bool]:
        """Vérifie les permissions du fichier de clé.

        Args:
            path: Chemin du fichier à inspecter.

        Returns:
            Tuple (texte_permissions, permissions_correctes).
        """
        try:
            mode = path.stat().st_mode
            perms = stat.S_IMODE(mode)
            ok = perms <= 0o600 and not (mode & stat.S_IRWXG) and not (mode & stat.S_IRWXO)
            return (f"{oct(perms)[-3:]} ✓" if ok else f"{oct(perms)[-3:]} ⚠", ok)
        except OSError as exc:
            logger.debug("_check_permissions | {path} → {exc}", path=path, exc=exc)
            return ("?", False)

    # ------------------------------------------------------------------
    # Renderers
    # ------------------------------------------------------------------

    def _render_pub_status(
        self,
        _col: Gtk.TreeViewColumn,
        cell: Gtk.CellRendererText,
        model: Gtk.TreeModel,
        it: Gtk.TreeIter,
        _data: object,
    ) -> None:
        """Affiche un indicateur de présence de la clé publique.

        Args:
            _col: Colonne (non utilisée).
            cell: CellRenderer à configurer.
            model: Modèle de données.
            it: Itérateur courant.
            _data: Données utilisateur (non utilisées).
        """
        pub_exists = model[it][6]
        cell.set_property("text", "✓ .pub" if pub_exists else "✗ none")
        cell.set_property("foreground", "#2d9e44" if pub_exists else "#888888")

    # ------------------------------------------------------------------
    # Sélection
    # ------------------------------------------------------------------

    def _get_selected_key(self) -> dict[str, str | bool] | None:
        """Retourne les infos de la clé sélectionnée dans l'onglet actif.

        Returns:
            Dictionnaire ``{name, path, pub, perms_ok}`` ou None.
        """
        page = self._notebook.get_current_page()
        tree = self._priv_tree if page == 0 else self._pub_tree
        store = self._priv_store if page == 0 else self._pub_store
        _model, it = tree.get_selection().get_selected()
        if it is None:
            return None
        return {
            "name": store[it][0],
            "path": store[it][1],
            "pub": store[it][2],
            "perms_ok": store[it][5],
        }

    def _on_selection_changed(self, _sel: Gtk.TreeSelection) -> None:
        """Met à jour la sensibilité des boutons d'action."""
        self._update_buttons()

    def _update_buttons(self) -> None:
        """Active/désactive les boutons selon la sélection courante."""
        key = self._get_selected_key()
        has_sel = key is not None
        has_pub = has_sel and bool(key.get("pub"))  # type: ignore[union-attr]
        self._btn_copy.set_sensitive(has_pub)
        self._btn_delete.set_sensitive(has_sel)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_generate(self, _widget: Gtk.Widget) -> None:
        """Ouvre le formulaire de génération et lance ssh-keygen."""
        dlg = _GenerateKeyDialog(parent=self)
        response = dlg.run()
        opts: dict[str, str | int] = dlg.get_options()
        dlg.destroy()

        if response != Gtk.ResponseType.OK:
            return

        self._generate_key(opts)

    def _generate_key(self, opts: dict[str, str | int]) -> None:
        """Lance ssh-keygen avec les options données.

        Args:
            opts: Dictionnaire ``{type, size, name, comment, passphrase}``.
        """
        try:
            self._ssh_dir.mkdir(parents=True, exist_ok=True)

            name = str(opts.get("name") or "id_ed25519").strip()
            if not name:
                name = f"id_{opts['type']}"

            # Éviter d'écraser une clé existante
            final_name = name
            suffix = 0
            while (self._ssh_dir / final_name).exists():
                suffix += 1
                final_name = f"{name}_{suffix}"

            key_path = self._ssh_dir / final_name
            key_type = str(opts.get("type") or "ed25519").lower()
            comment = str(opts.get("comment") or get_default_ssh_key_comment())
            passphrase = str(opts.get("passphrase") or "")

            if key_type == "rsa":
                size = int(opts.get("size") or 3072)
                cmd = [
                    "ssh-keygen",
                    "-t",
                    "rsa",
                    "-b",
                    str(size),
                    "-f",
                    str(key_path),
                    "-N",
                    passphrase,
                    "-C",
                    comment,
                ]
            elif key_type == "ecdsa":
                cmd = [
                    "ssh-keygen",
                    "-t",
                    "ecdsa",
                    "-f",
                    str(key_path),
                    "-N",
                    passphrase,
                    "-C",
                    comment,
                ]
            else:
                cmd = [
                    "ssh-keygen",
                    "-t",
                    "ed25519",
                    "-f",
                    str(key_path),
                    "-N",
                    passphrase,
                    "-C",
                    comment,
                ]

            logger.info(
                "SSHKeyManagerDialog._generate_key | type={t} name={n} path={p}",
                t=key_type,
                n=final_name,
                p=key_path,
            )
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.debug("_generate_key | stdout={s}", s=result.stdout.strip())

            self._notify(_("Key generated: {name}").format(name=final_name))
            GLib.idle_add(self._load_keys)

        except FileNotFoundError:
            self._notify(_("ssh-keygen not found — install openssh-client"))
        except subprocess.CalledProcessError as exc:
            self._notify(_("ssh-keygen failed: {err}").format(err=exc.stderr.strip()[:80]))
            logger.error("_generate_key | CalledProcessError: {e}", e=exc)
        except Exception as exc:
            self._notify(_("Generation failed: {err}").format(err=str(exc)))
            logger.exception("_generate_key | unexpected error", exception=True)

    def _on_import(self, _widget: Gtk.Widget) -> None:
        """Ouvre un FileChooser pour importer une clé privée dans ~/.ssh/."""
        dlg = Gtk.FileChooserDialog(
            title=_("Import Private Key"),
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dlg.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        dlg.add_button(_("_Import"), Gtk.ResponseType.OK)

        # Filtre : tous les fichiers (les clés privées n'ont pas d'extension)
        flt_all = Gtk.FileFilter()
        flt_all.set_name(_("All files"))
        flt_all.add_pattern("*")
        dlg.add_filter(flt_all)

        # Démarrer dans ~/.ssh/ si possible
        if self._ssh_dir.exists():
            dlg.set_current_folder(str(self._ssh_dir))

        response = dlg.run()
        filename = dlg.get_filename()
        dlg.destroy()

        if response != Gtk.ResponseType.OK or not filename:
            return

        src = Path(filename)
        dst = self._ssh_dir / src.name

        if dst.exists():
            overwrite = self._confirm(
                _("File {name} already exists in ~/.ssh/ — overwrite?").format(name=src.name)
            )
            if not overwrite:
                return

        try:
            self._ssh_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            dst.chmod(0o600)
            # Importer également la .pub si elle existe à côté
            pub_src = src.with_name(src.name + ".pub")
            if pub_src.exists():
                pub_dst = dst.with_name(dst.name + ".pub")
                shutil.copy2(pub_src, pub_dst)
                pub_dst.chmod(0o644)
            logger.info("_on_import | imported {src} → {dst}", src=src, dst=dst)
            self._notify(_("Key imported: {name}").format(name=src.name))
            self._load_keys()
        except Exception as exc:
            self._notify(_("Import failed: {err}").format(err=str(exc)))
            logger.error("_on_import | {exc}", exc=exc)

    def _on_copy_public(self, _widget: Gtk.Widget) -> None:
        """Copie la clé publique sélectionnée dans le presse-papiers."""
        key = self._get_selected_key()
        if not key or not key.get("pub"):
            self._notify(_("No public key available for selected entry"))
            return

        pub_path = Path(str(key["pub"]))
        if not pub_path.exists():
            self._notify(_("Public key file not found: {p}").format(p=pub_path))
            return

        try:
            text = pub_path.read_text(encoding="utf-8").strip()
            if _copy_text_to_clipboard(text):
                self._notify(_("Public key copied to clipboard"))
            else:
                self._notify(_("Clipboard unavailable — key content logged"))
                logger.info("public key content: {text}", text=text)
        except Exception as exc:
            self._notify(_("Copy failed: {err}").format(err=str(exc)))
            logger.error("_on_copy_public | {exc}", exc=exc)

    def _on_reveal(self, _widget: Gtk.Widget) -> None:
        """Ouvre ~/.ssh/ dans le gestionnaire de fichiers."""
        try:
            import subprocess as _sp

            _sp.Popen(["xdg-open", str(self._ssh_dir)])
        except Exception as exc:
            self._notify(_("Cannot open file manager: {err}").format(err=str(exc)))

    def _on_delete(self, _widget: Gtk.Widget) -> None:
        """Supprime la clé sélectionnée après confirmation."""
        key = self._get_selected_key()
        if not key:
            return

        name = key["name"]
        confirmed = self._confirm(
            _(
                "Permanently delete <b>{name}</b> (and its public key if present)?\n"
                "<b>This cannot be undone.</b>"
            ).format(name=name)
        )
        if not confirmed:
            return

        try:
            Path(str(key["path"])).unlink(missing_ok=True)
            if key.get("pub"):
                Path(str(key["pub"])).unlink(missing_ok=True)
            logger.info("_on_delete | deleted {name}", name=name)
            self._notify(_("Key deleted: {name}").format(name=name))
            self._load_keys()
        except Exception as exc:
            self._notify(_("Delete failed: {err}").format(err=str(exc)))
            logger.error("_on_delete | {exc}", exc=exc)

    # ------------------------------------------------------------------
    # Clavier
    # ------------------------------------------------------------------

    def _setup_keyboard(self) -> None:
        """Connecte les raccourcis clavier (Ctrl+N, Ctrl+I, Delete, Escape)."""
        self.connect("key-press-event", self._on_key_press)

    def _on_key_press(self, _widget: Gtk.Window, event: Gdk.EventKey) -> bool:
        """Gère les raccourcis clavier.

        Args:
            _widget: Fenêtre source (non utilisée).
            event: Événement clavier.

        Returns:
            True si l'événement est consommé.
        """
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True
        if ctrl and event.keyval == Gdk.KEY_n:
            self._on_generate(None)
            return True
        if ctrl and event.keyval == Gdk.KEY_i:
            self._on_import(None)
            return True
        if event.keyval == Gdk.KEY_Delete:
            self._on_delete(None)
            return True
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _notify(self, msg: str, duration_ms: int = 4000) -> None:
        """Affiche un message dans la barre de statut pendant duration_ms.

        Args:
            msg: Message à afficher.
            duration_ms: Durée d'affichage en millisecondes.
        """
        self._status_bar.pop(self._status_ctx)
        self._status_bar.push(self._status_ctx, msg)
        GLib.timeout_add(duration_ms, lambda: self._status_bar.pop(self._status_ctx))

    def _confirm(self, markup_text: str) -> bool:
        """Affiche une boîte de confirmation Yes/No.

        Args:
            markup_text: Texte Pango markup de la question.

        Returns:
            True si l'utilisateur a confirmé.
        """
        dlg = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
        )
        dlg.get_message_area().foreach(lambda w: w.destroy())
        lbl = Gtk.Label()
        lbl.set_markup(markup_text)
        lbl.set_line_wrap(True)
        lbl.show()
        dlg.get_message_area().pack_start(lbl, False, False, 0)
        response = dlg.run()
        dlg.destroy()
        return response == Gtk.ResponseType.YES

"""Dialogue de sélection de clé SSH existante depuis ~/.ssh/.

Adapté de SSH-Studio (BuddySirJava/SSH-Studio, GPLv3) — GTK4/Adw → GTK3.

Émet le signal ``key-selected(path_str)`` avec le chemin de la clé privée
quand l'utilisateur clique « Use ».  Peut également ouvrir le SSHKeyManagerDialog
pour générer une nouvelle clé depuis « Generate… ».
"""

from __future__ import annotations

import stat
import subprocess
from gettext import gettext as _
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GObject, Gtk  # noqa: E402

try:
    from loguru import logger
except ImportError:
    import logging as _stdlib_logging

    logger = _stdlib_logging.getLogger(__name__)  # type: ignore[assignment]

__all__ = ["KeyPickerDialog"]

_EXCLUDED_NAMES: frozenset[str] = frozenset(
    {"config", "known_hosts", "authorized_keys", "environment"}
)


class KeyPickerDialog(Gtk.Dialog):
    """Dialogue GTK3 de sélection d'une clé SSH depuis ~/.ssh/.

    Liste les clés privées et publiques. Sélectionner une clé puis cliquer
    « Use » retourne le chemin de la clé privée via le signal ``key-selected``.

    Signals:
        key-selected (str): Émis avec le chemin absolu de la clé privée.

    Example:
        dlg = KeyPickerDialog(parent=self.window)
        dlg.connect("key-selected", lambda _d, path: entry.set_text(path))
        dlg.run()
        dlg.destroy()
    """

    __gsignals__: dict = {
        "key-selected": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self, parent: Gtk.Window) -> None:
        """Initialise le dialogue et charge la liste des clés.

        Args:
            parent: Fenêtre parente GCM (pour centrage modal).
        """
        super().__init__(
            title=_("Select SSH Key"),
            transient_for=parent,
            modal=True,
            destroy_with_parent=True,
        )
        self.set_default_size(520, 400)

        self._btn_cancel = self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self._btn_generate = self.add_button(_("⚙ Generate…"), Gtk.ResponseType.HELP)
        self._btn_use = self.add_button(_("_Use"), Gtk.ResponseType.OK)
        self._btn_use.get_style_context().add_class("suggested-action")
        self._btn_use.set_sensitive(False)

        self._build_ui()
        self._load_keys()
        self.show_all()
        self.connect("response", self._on_response)

    def _build_ui(self) -> None:
        """Construit le panneau principal : info label + liste de clés."""
        content = self.get_content_area()
        content.set_spacing(6)
        content.set_margin_start(12)
        content.set_margin_end(12)
        content.set_margin_top(12)
        content.set_margin_bottom(6)

        lbl = Gtk.Label()
        lbl.set_markup(_("Keys found in <b>~/.ssh/</b> — select one then click <i>Use</i>:"))
        lbl.set_xalign(0.0)
        lbl.set_line_wrap(True)
        content.pack_start(lbl, False, False, 0)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_vexpand(True)

        # [display_name, private_path, pub_path, fingerprint, perms_str, perms_ok]
        self._store = Gtk.ListStore(str, str, str, str, str, bool)
        self._tree = Gtk.TreeView(model=self._store)
        self._tree.set_headers_visible(True)
        self._tree.connect("row-activated", self._on_row_activated)
        self._tree.get_selection().connect("changed", self._on_selection_changed)

        renderer_icon = Gtk.CellRendererPixbuf()
        renderer_name = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn(_("Key name"))
        col_name.pack_start(renderer_icon, False)
        col_name.pack_start(renderer_name, True)
        col_name.set_cell_data_func(renderer_icon, self._render_icon)
        col_name.set_cell_data_func(renderer_name, self._render_name)
        col_name.set_expand(True)
        self._tree.append_column(col_name)

        renderer_type = Gtk.CellRendererText()
        col_type = Gtk.TreeViewColumn(_("Type"))
        col_type.pack_start(renderer_type, True)
        col_type.set_cell_data_func(renderer_type, self._render_type)
        col_type.set_min_width(70)
        self._tree.append_column(col_type)

        renderer_fp = Gtk.CellRendererText()
        renderer_fp.set_property("ellipsize", 3)
        col_fp = Gtk.TreeViewColumn(_("Fingerprint"), renderer_fp, text=3)
        col_fp.set_expand(True)
        self._tree.append_column(col_fp)

        renderer_perms = Gtk.CellRendererText()
        col_perms = Gtk.TreeViewColumn(_("Permissions"), renderer_perms, text=4)
        col_perms.set_min_width(90)
        self._tree.append_column(col_perms)

        sw.add(self._tree)
        content.pack_start(sw, True, True, 0)

        self._no_key_label = Gtk.Label()
        self._no_key_label.set_markup(
            _("<i>No SSH key found in ~/.ssh/.\nClick <b>Generate…</b> to create one.</i>")
        )
        self._no_key_label.set_justify(Gtk.Justification.CENTER)
        content.pack_start(self._no_key_label, False, False, 8)

    def _load_keys(self) -> None:
        """Scanne ~/.ssh/ et peuple le ListStore."""
        self._store.clear()
        ssh_dir = Path.home() / ".ssh"
        logger.debug("KeyPickerDialog._load_keys | ssh_dir={d}", d=ssh_dir)

        if not ssh_dir.exists():
            self._show_empty(True)
            return

        entries: list[tuple[str, Path, Path | None]] = []
        for path in sorted(ssh_dir.iterdir()):
            if not path.is_file():
                continue
            name = path.name
            if name in _EXCLUDED_NAMES or name.startswith("."):
                continue
            if name.endswith(".pub"):
                priv = path.with_suffix("")
                if not priv.exists():
                    entries.append((name, path, None))
            else:
                pub = path.with_name(name + ".pub")
                entries.append((name, path, pub if pub.exists() else None))

        for display_name, priv_path, pub_path in entries:
            fp = self._get_fingerprint(pub_path or priv_path)
            perms_str, perms_ok = self._check_permissions(priv_path)
            self._store.append(
                [
                    display_name,
                    str(priv_path),
                    str(pub_path) if pub_path else "",
                    fp,
                    perms_str,
                    perms_ok,
                ]
            )

        self._show_empty(len(self._store) == 0)

    def _show_empty(self, empty: bool) -> None:
        """Affiche ou masque le label « aucune clé ».

        Args:
            empty: True pour afficher le label, False pour le masquer.
        """
        self._no_key_label.set_visible(empty)
        parent_sw = self._tree.get_parent()
        if parent_sw:
            parent_sw.set_visible(not empty)

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
            path: Chemin de la clé.

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

    def _render_icon(
        self,
        _col: Gtk.TreeViewColumn,
        cell: Gtk.CellRendererPixbuf,
        model: Gtk.TreeModel,
        it: Gtk.TreeIter,
        _data: object,
    ) -> None:
        """Affiche une icône verrou selon le type et les permissions."""
        priv_path = model[it][1]
        perms_ok = model[it][5]
        if priv_path.endswith(".pub"):
            icon = "dialog-information-symbolic"
        elif perms_ok:
            icon = "channel-secure-symbolic"
        else:
            icon = "channel-insecure-symbolic"
        cell.set_property("icon-name", icon)
        cell.set_property("stock-size", Gtk.IconSize.SMALL_TOOLBAR)

    def _render_name(
        self,
        _col: Gtk.TreeViewColumn,
        cell: Gtk.CellRendererText,
        model: Gtk.TreeModel,
        it: Gtk.TreeIter,
        _data: object,
    ) -> None:
        """Affiche le nom, en orange si permissions incorrectes."""
        name = model[it][0]
        perms_ok = model[it][5]
        if not perms_ok and not name.endswith(".pub"):
            cell.set_property("markup", f'<span color="orange">{name}</span>')
        else:
            cell.set_property("text", name)

    def _render_type(
        self,
        _col: Gtk.TreeViewColumn,
        cell: Gtk.CellRendererText,
        model: Gtk.TreeModel,
        it: Gtk.TreeIter,
        _data: object,
    ) -> None:
        """Affiche 'private' ou 'public' selon le type de clé."""
        priv_path = model[it][1]
        cell.set_property("text", _("public") if priv_path.endswith(".pub") else _("private"))

    def _on_selection_changed(self, selection: Gtk.TreeSelection) -> None:
        """Active le bouton Use si une ligne est sélectionnée."""
        _model, it = selection.get_selected()
        self._btn_use.set_sensitive(it is not None)

    def _on_row_activated(
        self,
        _tree: Gtk.TreeView,
        path: Gtk.TreePath,
        _col: Gtk.TreeViewColumn,
    ) -> None:
        """Double-clic : émet key-selected et ferme."""
        it = self._store.get_iter(path)
        if it:
            self._emit_selection(it)
            self.destroy()

    def _on_response(self, _dlg: KeyPickerDialog, response_id: int) -> None:
        """Gère les boutons Cancel / Generate / Use."""
        if response_id == Gtk.ResponseType.OK:
            _model, it = self._tree.get_selection().get_selected()
            if it:
                self._emit_selection(it)
                self.destroy()
        elif response_id == Gtk.ResponseType.HELP:
            self._open_key_manager()
        else:
            self.destroy()

    def _emit_selection(self, it: Gtk.TreeIter) -> None:
        """Émet key-selected avec le chemin de la clé privée.

        Args:
            it: Itérateur sur la ligne sélectionnée.
        """
        priv_path = self._store[it][1]
        private = str(Path(priv_path).with_suffix("")) if priv_path.endswith(".pub") else priv_path
        logger.info("KeyPickerDialog | key-selected path={p}", p=private)
        self.emit("key-selected", private)

    def _open_key_manager(self) -> None:
        """Ouvre SSHKeyManagerDialog et recharge après fermeture."""
        from ssh_key_manager_dialog import SSHKeyManagerDialog  # noqa: PLC0415

        mgr = SSHKeyManagerDialog(parent=self.get_transient_for())
        mgr.connect("destroy", lambda _w: self._load_keys())
        mgr.show_all()

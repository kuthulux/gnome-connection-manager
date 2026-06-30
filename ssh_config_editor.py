"""Dialogue GTK3 d'édition de ~/.ssh/config intégré à GCM.

Fournit un éditeur visuel (liste d'hôtes + formulaire de champs)
et un onglet Raw (texte brut éditable) avec diff inline.
Utilise ssh_config_parser.py, adapté de SSH-Studio (BuddySirJava, GPLv3).

Corrections v2 :
- Ajout de Gdk dans les imports gi.repository
- Clipboard corrigé : Gdk.Atom.intern("CLIPBOARD", False) au lieu de gdk_atom_intern
- Handler _on_raw_changed réintégré (perdu lors du fix ruff I001)
"""

from __future__ import annotations

import difflib
import subprocess
from gettext import gettext as _
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk, Pango  # noqa: E402

try:
    from loguru import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)  # type: ignore[assignment]

from key_picker_dialog import KeyPickerDialog
from ssh_config_parser import (  # noqa: E402
    SSHConfig,
    SSHConfigParser,
    SSHHost,
    SSHOption,
)
from ssh_key_manager_dialog import SSHKeyManagerDialog

# ---------------------------------------------------------------------------
# Champs affichés dans le formulaire visuel
# ---------------------------------------------------------------------------
_BASIC_FIELDS: list[tuple[str, str]] = [
    ("Host", _("Alias(es)")),
    ("HostName", _("HostName")),
    ("User", _("User")),
    ("Port", _("Port")),
    ("IdentityFile", _("IdentityFile")),
    ("ProxyJump", _("ProxyJump")),
    ("ForwardAgent", _("ForwardAgent")),
    ("ServerAliveInterval", _("ServerAliveInterval")),
    ("Compression", _("Compression")),
]


# ---------------------------------------------------------------------------
# Dialogue principal
# ---------------------------------------------------------------------------


class SshConfigEditorDialog(Gtk.Dialog):
    """Éditeur visuel de ~/.ssh/config avec onglet Raw/diff.

    Onglets :
    - **Visual** : liste d'hôtes à gauche, formulaire à droite
    - **Raw** : texte brut du fichier avec diff des modifications

    Example:
        dlg = SshConfigEditorDialog(parent=self.window)
        if dlg.run() == Gtk.ResponseType.OK:
            dlg.save()
        dlg.destroy()
    """

    def __init__(self, parent: Gtk.Window) -> None:
        """Initialise le dialogue et charge ~/.ssh/config.

        Args:
            parent: Fenêtre parente GCM (pour centrage modal).
        """
        super().__init__(
            title=_("Edit ~/.ssh/config"),
            transient_for=parent,
            modal=True,
            destroy_with_parent=True,
        )
        self.set_default_size(940, 620)
        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self._btn_save = self.add_button(_("_Save"), Gtk.ResponseType.OK)
        self._btn_save.get_style_context().add_class("suggested-action")

        self._parser = SSHConfigParser()
        self._parser.parse()
        self._config: SSHConfig = self._parser.config
        self._current_host: SSHHost | None = None
        self._dirty = False

        self._build_ui()
        self._populate_list()
        self._sync_raw_from_model()
        self._update_save_button()

    # ------------------------------------------------------------------
    # Construction de l'UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construit l'ensemble de l'interface (notebook + panneaux)."""
        content = self.get_content_area()
        content.set_spacing(0)

        self._error_bar = Gtk.InfoBar()
        self._error_bar.set_message_type(Gtk.MessageType.ERROR)
        self._error_bar.set_show_close_button(True)
        self._error_label = Gtk.Label(label="")
        self._error_label.set_line_wrap(True)
        self._error_bar.get_content_area().pack_start(self._error_label, True, True, 0)
        self._error_bar.connect("response", lambda bar, _rid: bar.hide())
        self._error_bar.hide()
        content.pack_start(self._error_bar, False, False, 0)

        self._notebook = Gtk.Notebook()
        self._notebook.set_margin_start(8)
        self._notebook.set_margin_end(8)
        self._notebook.set_margin_top(8)
        self._notebook.set_margin_bottom(4)
        content.pack_start(self._notebook, True, True, 0)

        self._notebook.append_page(self._build_visual_tab(), Gtk.Label(label=_("Visual")))
        self._notebook.append_page(self._build_raw_tab(), Gtk.Label(label=_("Raw / Diff")))
        self._notebook.connect("switch-page", self._on_tab_switch)

        content.show_all()
        self._error_bar.hide()

    def _build_visual_tab(self) -> Gtk.Widget:
        """Construit le panneau Visual (liste + formulaire).

        Returns:
            Widget racine de l'onglet.
        """
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(230)

        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        left_box.set_margin_start(4)
        left_box.set_margin_end(4)
        left_box.set_margin_top(4)

        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text(_("Filter hosts…"))
        self._search_entry.connect("search-changed", self._on_search_changed)
        left_box.pack_start(self._search_entry, False, False, 0)

        sw_left = Gtk.ScrolledWindow()
        sw_left.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw_left.set_shadow_type(Gtk.ShadowType.IN)
        sw_left.set_min_content_width(210)

        self._host_store = Gtk.ListStore(str, str)
        self._host_filter = self._host_store.filter_new()
        self._host_filter.set_visible_func(self._host_filter_func)

        self._tree = Gtk.TreeView(model=self._host_filter)
        self._tree.set_headers_visible(False)
        self._tree.set_tooltip_column(1)
        col = Gtk.TreeViewColumn("", Gtk.CellRendererText(), text=0)
        self._tree.append_column(col)
        self._tree.get_selection().connect("changed", self._on_host_selected)
        sw_left.add(self._tree)
        left_box.pack_start(sw_left, True, True, 0)

        btn_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        btn_add = Gtk.Button(label=_("＋ Add"))
        btn_add.set_tooltip_text(_("Add a new empty host"))
        btn_add.connect("clicked", self._on_add_host)
        self._btn_remove = Gtk.Button(label=_("✕ Remove"))
        self._btn_remove.set_tooltip_text(_("Remove selected host"))
        self._btn_remove.set_sensitive(False)
        self._btn_remove.connect("clicked", self._on_remove_host)
        self._btn_test = Gtk.Button(label=_("⚡ Test"))
        self._btn_test.set_tooltip_text(_("Test SSH connection to selected host"))
        self._btn_test.set_sensitive(False)
        self._btn_test.connect("clicked", self._on_test_connection)
        btn_bar.pack_start(btn_add, True, True, 0)
        btn_bar.pack_start(self._btn_remove, True, True, 0)
        btn_bar.pack_start(self._btn_test, True, True, 0)
        left_box.pack_start(btn_bar, False, False, 0)

        paned.pack1(left_box, False, False)

        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        right_box.set_margin_start(8)
        right_box.set_margin_end(4)
        right_box.set_margin_top(4)

        self._form_grid = Gtk.Grid()
        self._form_grid.set_column_spacing(10)
        self._form_grid.set_row_spacing(6)
        self._form_grid.set_margin_top(8)

        self._entries: dict[str, Gtk.Entry] = {}
        self._error_labels: dict[str, Gtk.Label] = {}

        # for row, (key, label_text) in enumerate(_BASIC_FIELDS):
        #     lbl = Gtk.Label(label=label_text + ":", xalign=1.0)
        #     lbl.set_size_request(140, -1)
        #     entry = Gtk.Entry()
        #     entry.set_hexpand(True)
        #     entry.set_placeholder_text(key)
        #     entry.connect("changed", self._on_field_changed, key)
        #     err_lbl = Gtk.Label(label="")
        #     err_lbl.set_xalign(0.0)
        #     err_lbl.get_style_context().add_class("error")
        #     err_lbl.hide()
        #     self._form_grid.attach(lbl, 0, row * 2, 1, 1)
        #     self._form_grid.attach(entry, 1, row * 2, 1, 1)
        #     self._form_grid.attach(err_lbl, 1, row * 2 + 1, 1, 1)
        #     self._entries[key] = entry
        #     self._error_labels[key] = err_lbl

        for row, (key, label_text) in enumerate(_BASIC_FIELDS):
            lbl = Gtk.Label(label=label_text + ":", xalign=1.0)
            lbl.set_size_request(140, -1)
            entry = Gtk.Entry()
            entry.set_hexpand(True)
            entry.set_placeholder_text(key)
            entry.connect("changed", self._on_field_changed, key)
            err_lbl = Gtk.Label(label="")
            err_lbl.set_xalign(0.0)
            err_lbl.get_style_context().add_class("error")
            err_lbl.hide()

            if key == "IdentityFile":
                # Boîte horizontale : entry + bouton sélecteur de clé + bouton gestionnaire
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
                hbox.set_hexpand(True)
                hbox.pack_start(entry, True, True, 0)
                btn_pick = Gtk.Button(label=_("🔑 Pick…"))
                btn_pick.set_tooltip_text(_("Browse existing SSH keys in ~/.ssh/"))
                btn_pick.connect("clicked", self._on_pick_identity_file)
                btn_mgr = Gtk.Button(label=_("⚙"))
                btn_mgr.set_tooltip_text(_("Open SSH Key Manager (generate / import / delete)"))
                btn_mgr.connect("clicked", self._on_open_key_manager)
                hbox.pack_start(btn_pick, False, False, 0)
                hbox.pack_start(btn_mgr, False, False, 0)
                self._form_grid.attach(lbl, 0, row * 2, 1, 1)
                self._form_grid.attach(hbox, 1, row * 2, 1, 1)
            else:
                self._form_grid.attach(lbl, 0, row * 2, 1, 1)
                self._form_grid.attach(entry, 1, row * 2, 1, 1)

        copy_btn = Gtk.Button(label=_("Copy ssh cmd"))
        copy_btn.set_tooltip_text(_("Copy full ssh command to clipboard"))
        copy_btn.connect("clicked", self._on_copy_ssh_cmd)
        copy_btn.set_hexpand(False)
        self._form_grid.attach(copy_btn, 1, len(_BASIC_FIELDS) * 2, 1, 1)

        self._placeholder_label = Gtk.Label(label=_("← Select or create a host"))
        self._placeholder_label.set_sensitive(False)
        self._placeholder_label.set_valign(Gtk.Align.CENTER)
        self._placeholder_label.set_halign(Gtk.Align.CENTER)

        self._form_stack = Gtk.Stack()
        self._form_stack.add_named(self._placeholder_label, "placeholder")
        self._form_stack.add_named(self._form_grid, "form")
        self._form_stack.set_visible_child_name("placeholder")

        right_box.pack_start(self._form_stack, True, True, 0)
        paned.pack2(right_box, True, False)
        return paned

    def _build_raw_tab(self) -> Gtk.Widget:
        """Construit le panneau Raw/Diff.

        Returns:
            Widget racine de l'onglet.
        """
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_margin_start(8)
        vbox.set_margin_end(8)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(4)

        info = Gtk.Label(
            label=_("Edit raw ~/.ssh/config — changes here override the Visual tab on Save.")
        )
        info.set_xalign(0.0)
        info.set_line_wrap(True)
        vbox.pack_start(info, False, False, 0)

        paned_raw = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        paned_raw.set_position(340)

        sw_raw = Gtk.ScrolledWindow()
        sw_raw.set_shadow_type(Gtk.ShadowType.IN)
        self._raw_buffer = Gtk.TextBuffer()
        self._raw_view = Gtk.TextView(buffer=self._raw_buffer)
        self._raw_view.set_monospace(True)
        self._raw_view.set_left_margin(6)
        self._raw_view.set_top_margin(4)
        sw_raw.add(self._raw_view)
        paned_raw.pack1(sw_raw, True, False)

        sw_diff = Gtk.ScrolledWindow()
        sw_diff.set_shadow_type(Gtk.ShadowType.IN)
        sw_diff.set_min_content_height(120)
        self._diff_buffer = Gtk.TextBuffer()
        self._diff_buffer.create_tag("added", foreground="#2d9e44")
        self._diff_buffer.create_tag("removed", foreground="#e01b24")
        self._diff_buffer.create_tag("header", foreground="#888888", weight=Pango.Weight.BOLD)
        self._diff_view = Gtk.TextView(buffer=self._diff_buffer)
        self._diff_view.set_monospace(True)
        self._diff_view.set_editable(False)
        self._diff_view.set_left_margin(6)
        self._diff_view.set_top_margin(4)
        sw_diff.add(self._diff_view)

        diff_label = Gtk.Label(label=_("Diff (original → current):"), xalign=0.0)
        diff_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        diff_box.pack_start(diff_label, False, False, 0)
        diff_box.pack_start(sw_diff, True, True, 0)

        paned_raw.pack2(diff_box, False, False)
        vbox.pack_start(paned_raw, True, True, 0)

        btn_diff = Gtk.Button(label=_("⟳ Refresh diff"))
        btn_diff.connect("clicked", lambda _w: self._refresh_diff())
        btn_diff.set_halign(Gtk.Align.END)
        vbox.pack_start(btn_diff, False, False, 0)

        # IMPORTANT : connecter le signal APRÈS avoir créé self._raw_buffer
        self._raw_buffer.connect("changed", self._on_raw_changed)
        return vbox

    def _populate_list(self) -> None:
        """Remplit le ListStore depuis self._config.hosts."""
        self._host_store.clear()
        for host in self._config.hosts:
            alias = " ".join(host.patterns)
            hostname = host.get_option("HostName") or ""
            tooltip = f"{alias}\n{hostname}" if hostname else alias
            self._host_store.append([alias, tooltip])

    def _host_filter_func(self, model: Gtk.TreeModel, it: Gtk.TreeIter, _data: object) -> bool:
        """Filtre les hôtes selon le texte de recherche.

        Args:
            model: Modèle de données.
            it: Itérateur sur la ligne candidate.
            _data: Données utilisateur (non utilisé).

        Returns:
            True si la ligne doit être visible.
        """
        text = self._search_entry.get_text().strip().lower()
        if not text:
            return True
        return text in model[it][0].lower() or text in model[it][1].lower()

    def _load_host_in_form(self, host: SSHHost) -> None:
        """Remplit le formulaire avec les valeurs d'un hôte.

        Args:
            host: Bloc SSH à afficher.
        """
        self._current_host = host
        self._form_stack.set_visible_child_name("form")
        self._entries["Host"].set_text(" ".join(host.patterns))
        for key in list(_BASIC_FIELDS)[1:]:
            field_key = key[0]
            val = host.get_option(field_key) or ""
            self._entries[field_key].set_text(val)
            self._error_labels[field_key].hide()
        self._btn_remove.set_sensitive(True)
        self._btn_test.set_sensitive(bool(host.get_option("HostName") or host.patterns))

    def _save_form_to_host(self) -> bool:
        """Applique les valeurs du formulaire dans self._current_host.

        Returns:
            True si tous les champs sont valides, False sinon.
        """
        if self._current_host is None:
            return True

        valid = True

        raw_alias = self._entries["Host"].get_text().strip()
        if not raw_alias:
            self._show_field_error("Host", _("At least one alias is required"))
            valid = False
        else:
            self._current_host.patterns = raw_alias.split()
            self._error_labels["Host"].hide()

        port_str = self._entries["Port"].get_text().strip()
        if port_str:
            try:
                p = int(port_str)
                if p < 1 or p > 65535:
                    raise ValueError
                self._error_labels["Port"].hide()
            except ValueError:
                self._show_field_error("Port", _("Port must be an integer between 1 and 65535"))
                valid = False

        for key, _lbl in _BASIC_FIELDS:
            if key in ("Host", "Port"):
                continue
            val = self._entries[key].get_text().strip()
            if val:
                self._current_host.set_option(key, val)
            else:
                self._current_host.remove_option(key)

        return valid

    def _show_field_error(self, key: str, msg: str) -> None:
        """Affiche un message d'erreur sous un champ.

        Args:
            key: Clé du champ concerné.
            msg: Texte de l'erreur.
        """
        lbl = self._error_labels.get(key)
        if lbl:
            lbl.set_text(msg)
            lbl.show()

    def _sync_raw_from_model(self) -> None:
        """Copie le contenu généré par le modèle dans la zone Raw."""
        content = self._config.generate_content()
        self._raw_buffer.handler_block_by_func(self._on_raw_changed)
        self._raw_buffer.set_text(content)
        self._raw_buffer.handler_unblock_by_func(self._on_raw_changed)
        self._refresh_diff()

    def _sync_model_from_raw(self) -> bool:
        """Parse le contenu de la zone Raw et recharge le modèle.

        Returns:
            True si le parsing a réussi.
        """
        start, end = self._raw_buffer.get_bounds()
        text = self._raw_buffer.get_text(start, end, False)
        tmp_path = Path(self._config.file_path.parent / ".gcm_raw_tmp")
        try:
            tmp_path.write_text(text, encoding="utf-8")
            tmp_parser = SSHConfigParser(config_path=tmp_path)
            tmp_parser.parse()
            self._config.hosts = tmp_parser.config.hosts
            self._config.global_options = tmp_parser.config.global_options
            self._config.include_directives = tmp_parser.config.include_directives
            return True
        except Exception as exc:
            logger.warning("Raw parse failed: {exc}", exc=exc)
            return False
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass

    def _refresh_diff(self) -> None:
        """Met à jour la zone diff entre le fichier original et la version courante."""
        original = "\n".join(self._config.original_lines) + "\n"
        start, end = self._raw_buffer.get_bounds()
        current = self._raw_buffer.get_text(start, end, False)

        diff = list(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                current.splitlines(keepends=True),
                fromfile="original",
                tofile="current",
                n=2,
            )
        )

        self._diff_buffer.set_text("")
        it = self._diff_buffer.get_end_iter()
        if not diff:
            self._diff_buffer.insert_with_tags_by_name(it, _("No changes."), "header")
            return

        for line in diff:
            if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
                self._diff_buffer.insert_with_tags_by_name(it, line, "header")
            elif line.startswith("+"):
                self._diff_buffer.insert_with_tags_by_name(it, line, "added")
            elif line.startswith("-"):
                self._diff_buffer.insert_with_tags_by_name(it, line, "removed")
            else:
                self._diff_buffer.insert(it, line)

    def save(self) -> None:
        """Sauvegarde la configuration sur disque.

        Lit depuis la zone Raw si l'onglet Raw est actif,
        sinon utilise le modèle en mémoire.
        """
        if self._notebook.get_current_page() == 1:
            if not self._sync_model_from_raw():
                logger.error("save | raw parse failed, aborting write")
                return
        self._parser.write()
        logger.info("save | ~/.ssh/config written successfully")

    def _run_validation(self) -> list[str]:
        """Lance la validation et affiche les erreurs dans l'InfoBar.

        Returns:
            Liste des messages d'erreur (vide si OK).
        """
        errors = self._parser.validate()
        if errors:
            self._error_label.set_text("\n".join(errors))
            self._error_bar.show()
        else:
            self._error_bar.hide()
        return errors

    def _update_save_button(self) -> None:
        """Active ou désactive le bouton Save selon la validité."""
        self._run_validation()

    def _on_pick_identity_file(self, _widget: Gtk.Widget) -> None:
        """Ouvre le dialogue de sélection de clé SSH.

        Args:
            _widget: Widget qui a déclenché l'événement.
        """
        dlg = KeyPickerDialog(parent=self)
        dlg.connect("key-selected", self._on_key_selected)
        dlg.run()
        dlg.destroy()

    def _on_key_selected(self, _dlg, key_path: str) -> None:
        """Callback du signal key-selected de KeyPickerDialog.

        Args:
            _dlg: Dialog source (non utilisé).
            key_path: Chemin absolu de la clé privée sélectionnée.
        """
        self._entries["IdentityFile"].set_text(key_path)
        self._dirty = True

    def _on_open_key_manager(self, _widget: Gtk.Widget) -> None:
        """Ouvre le dialogue de gestion des clés SSH.

        Args:
            _widget: Widget qui a déclenché l'événement.
        """
        dlg = SSHKeyManagerDialog(parent=self)
        dlg.show_all()

    def _on_host_selected(self, selection: Gtk.TreeSelection) -> None:
        """Charge l'hôte sélectionné dans le formulaire.

        Args:
            selection: Sélection courante du TreeView.
        """
        if self._current_host is not None:
            self._save_form_to_host()
            self._dirty = True
            self._update_save_button()

        model, it = selection.get_selected()
        if it is None:
            self._current_host = None
            self._form_stack.set_visible_child_name("placeholder")
            self._btn_remove.set_sensitive(False)
            self._btn_test.set_sensitive(False)
            return

        alias_str = model[it][0]
        alias = alias_str.split()[0]
        host = self._config.get_host(alias)
        if host:
            self._load_host_in_form(host)

    def _on_field_changed(self, _entry: Gtk.Entry, _key: str) -> None:
        """Marque le formulaire comme modifié.

        Args:
            entry: Champ modifié.
            key: Clé SSH correspondante.
        """
        self._dirty = True

    def _on_raw_changed(self, _buf: Gtk.TextBuffer) -> None:
        """Marque l'onglet Raw comme modifié.

        Args:
            _buf: Buffer texte (non utilisé directement).
        """
        self._dirty = True

    def _on_add_host(self, _widget: Gtk.Widget) -> None:
        """Crée un nouvel hôte vide et le sélectionne.

        Args:
            _widget: Widget qui a déclenché l'événement.
        """
        new_host = SSHHost(patterns=["new-host"])
        new_host.options.append(SSHOption(key="HostName", value=""))
        new_host.options.append(SSHOption(key="User", value=""))
        self._config.add_host(new_host)
        self._populate_list()
        last = len(self._host_store) - 1
        if last >= 0:
            self._tree.set_cursor(Gtk.TreePath(last), None, False)
        self._dirty = True

    def _on_remove_host(self, _widget: Gtk.Widget) -> None:
        """Supprime l'hôte actuellement sélectionné après confirmation.

        Args:
            _widget: Widget qui a déclenché l'événement.
        """
        if self._current_host is None:
            return
        alias = " ".join(self._current_host.patterns)
        dlg = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Remove host?"),
        )
        dlg.format_secondary_text(_("Remove «{alias}» from ~/.ssh/config?").format(alias=alias))
        if dlg.run() == Gtk.ResponseType.YES:
            self._config.remove_host(self._current_host)
            self._current_host = None
            self._form_stack.set_visible_child_name("placeholder")
            self._populate_list()
            self._dirty = True
        dlg.destroy()

    def _on_test_connection(self, _widget: Gtk.Widget) -> None:
        """Lance un test de connexion SSH vers l'hôte sélectionné.

        Args:
            _widget: Widget qui a déclenché l'événement.
        """
        if self._current_host is None:
            return
        alias = self._current_host.patterns[0] if self._current_host.patterns else ""
        if not alias:
            return
        dlg = _SshTestDialog(parent=self, alias=alias)
        dlg.run()
        dlg.destroy()

    def _on_copy_ssh_cmd(self, _widget: Gtk.Widget) -> None:
        """Copie la commande SSH complète dans le presse-papiers.

        Args:
            _widget: Widget qui a déclenché l'événement.
        """
        if self._current_host is None:
            return
        alias = self._current_host.patterns[0] if self._current_host.patterns else ""
        user = self._current_host.get_option("User") or ""
        port = self._current_host.get_option("Port") or "22"
        hostname = self._current_host.get_option("HostName") or alias

        cmd = f"ssh -p {port} {user}@{hostname}" if user else f"ssh -p {port} {hostname}"

        # API Clipboard correcte pour GTK3 : Gdk.Atom.intern
        clip = Gtk.Clipboard.get(Gdk.Atom.intern("CLIPBOARD", False))
        clip.set_text(cmd, -1)
        _show_toast(self, _("Copied: {cmd}").format(cmd=cmd))

    def _on_search_changed(self, _entry: Gtk.SearchEntry) -> None:
        """Rafraîchit le filtre de la liste.

        Args:
            _entry: Champ de recherche (non utilisé directement).
        """
        self._host_filter.refilter()

    def _on_tab_switch(self, _nb: Gtk.Notebook, _page: Gtk.Widget, page_num: int) -> None:
        """Synchronise modèle ↔ Raw lors du changement d'onglet.

        Args:
            _nb: Notebook (non utilisé).
            _page: Page destination (non utilisé).
            page_num: Index de la page destination.
        """
        if page_num == 1:
            if self._current_host is not None:
                self._save_form_to_host()
            self._sync_raw_from_model()
        else:
            if self._sync_model_from_raw():
                self._populate_list()
                self._refresh_diff()


class _SshTestDialog(Gtk.Dialog):
    """Dialogue de test de connexion SSH (ssh -o ConnectTimeout=5 -v alias).

    Args:
        parent: Fenêtre parente.
        alias: Alias SSH à tester.
    """

    def __init__(self, parent: Gtk.Window, alias: str) -> None:
        """Initialise le dialogue de test SSH.

        Args:
            parent: Fenêtre parente.
            alias: Alias SSH du bloc Host à tester.
        """
        super().__init__(
            title=_("Test connection — {alias}").format(alias=alias),
            transient_for=parent,
            modal=True,
        )
        self.set_default_size(560, 300)
        self.add_button(_("Close"), Gtk.ResponseType.CLOSE)
        self._alias = alias
        self._build_ui()
        self.show_all()
        GLib.idle_add(self._run_test)

    def _build_ui(self) -> None:
        """Construit la zone d'affichage de sortie SSH."""
        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_margin_start(8)
        sw.set_margin_end(8)
        sw.set_margin_top(8)
        sw.set_margin_bottom(4)
        self._buf = Gtk.TextBuffer()
        tv = Gtk.TextView(buffer=self._buf)
        tv.set_monospace(True)
        tv.set_editable(False)
        tv.set_left_margin(4)
        sw.add(tv)
        self.get_content_area().pack_start(sw, True, True, 0)
        self.get_content_area().show_all()

    def _run_test(self) -> bool:
        """Lance ssh -o ConnectTimeout=5 -v alias et affiche la sortie.

        Returns:
            False (fin du GLib.idle_add).
        """
        cmd = ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", "-v", self._alias]
        self._append(_("Running: {cmd}\n\n").format(cmd=" ".join(cmd)))
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            output = result.stdout + result.stderr
            self._append(output or _("(no output)\n"))
            self._append(_("\nExit code: {rc}").format(rc=result.returncode))
        except subprocess.TimeoutExpired:
            self._append(_("\n[Timeout after 10 s]"))
        except Exception as exc:
            self._append(_("\n[Error: {exc}]").format(exc=exc))
        return False

    def _append(self, text: str) -> None:
        """Ajoute du texte à la fin du buffer d'affichage.

        Args:
            text: Texte à ajouter.
        """
        self._buf.insert(self._buf.get_end_iter(), text)


def _show_toast(parent: Gtk.Window, msg: str, duration_ms: int = 2500) -> None:
    """Affiche une notification temporaire dans une InfoBar flottante.

    Args:
        parent: Fenêtre parente (pour positionnement).
        msg: Message à afficher.
        duration_ms: Durée d'affichage en millisecondes.
    """
    bar = Gtk.InfoBar()
    bar.set_message_type(Gtk.MessageType.INFO)
    bar.get_content_area().pack_start(Gtk.Label(label=msg), True, True, 0)
    bar.show_all()
    content = parent.get_content_area() if isinstance(parent, Gtk.Dialog) else None
    if content:
        content.pack_start(bar, False, False, 0)
        GLib.timeout_add(duration_ms, lambda: bar.destroy() or False)

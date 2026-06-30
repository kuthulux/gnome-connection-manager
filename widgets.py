#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""Widgets GTK personnalisés pour l'interface GCM."""

import configparser
import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from Cryptodome.Cipher import DES
from gi.repository import Gdk, GLib, GObject, Gtk, Vte

from utils import conf

if TYPE_CHECKING:
    # `_` est injecté dans les builtins à l'exécution par bindtextdomain().
    # Cette déclaration sert uniquement au type-checker (Pylance) : elle évite
    # les faux positifs "_ is not defined" sans affecter le runtime.
    def _(message: str) -> str: ...


try:
    from loguru import logger as _loguru_logger

    _LOGURU_OK = True
except ImportError:
    _LOGURU_OK = False

try:
    USERHOME_DIR = os.getenv("HOME")
except:
    USERHOME_DIR = ""
if USERHOME_DIR is None or USERHOME_DIR == "":
    try:
        USERHOME_DIR = os.path.expanduser("~")
    except:
        USERHOME_DIR = ""

assert (USERHOME_DIR is not None) and (USERHOME_DIR != ""), (
    "FATAL: Could not determine home directory for the current user"
)

assert os.path.isdir(USERHOME_DIR), (
    "FATAL: Could not locate home directory '%s' for the current user" % (USERHOME_DIR)
)

CONFIG_DIR = USERHOME_DIR + "/.gcm"
CONFIG_FILE = CONFIG_DIR + "/gcm.conf"
KEY_FILE = CONFIG_DIR + "/.gcm.key"

if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)
app_name = "Gnome Connection Manager"
# Initialiser les valeurs de conf dépendantes du contexte d'exécution
conf.LOG_PATH = CONFIG_DIR + "/logs"
conf.CONTINUOUS_LOG_PATH = CONFIG_DIR + "/log"
conf.APP_TITLE = app_name


def _setup_app_logger():
    """Initialise le logger applicatif (Loguru) avec fallback stdlib.

    Returns:
        object: Logger configuré (`loguru.logger` ou `logging.Logger`).
    """
    log_dir = os.path.join(CONFIG_DIR, "log")
    log_file = os.path.join(log_dir, "gcm-app.log")
    os.makedirs(log_dir, exist_ok=True)

    if _LOGURU_OK:
        _loguru_logger.remove()
        _loguru_logger.add(
            sys.stderr,
            level="DEBUG",
            enqueue=True,
            backtrace=False,
            diagnose=False,
        )
        _loguru_logger.add(
            log_file,
            level="DEBUG",
            rotation="10 MB",
            retention="14 days",
            encoding="utf-8",
            enqueue=True,
            backtrace=True,
            diagnose=False,
        )
        return _loguru_logger

    fallback = logging.getLogger("gcm")
    fallback.setLevel(logging.DEBUG)
    if not fallback.handlers:
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        sh = logging.StreamHandler(sys.stderr)
        sh.setLevel(logging.DEBUG)
        sh.setFormatter(fmt)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        fallback.addHandler(sh)
        fallback.addHandler(fh)
    fallback.warning("loguru non installé, fallback sur logging standard")
    return fallback


app_logger = _setup_app_logger()

SHELL = os.environ["SHELL"]
# check Terminal version
TERMINAL_V048 = "spawn_async" in Vte.Terminal.__dict__
# Vérification runtime du signal 'output-written' (VTE >= 0.60)
# GObject.signal_lookup retourne 0 si le signal n'existe pas.

# Détection des binaires VNC disponibles (ordre de préférence)
VNC_BIN = (
    shutil.which("vncviewer")
    or shutil.which("tigervnc")
    or shutil.which("xtightvncviewer")
    or shutil.which("xvnc4viewer")
    or shutil.which("vinagre")
    or shutil.which("remmina")
    or "vncviewer"
)

# Détection des binaires SPICE disponibles
SPICE_BIN = (
    shutil.which("remote-viewer")
    or shutil.which("virt-viewer")
    or shutil.which("spicy")
    or "remote-viewer"
)

# Détection du binaire serial disponible (picocom > minicom > screen)
SERIAL_BIN = (
    shutil.which("picocom") or shutil.which("minicom") or shutil.which("screen") or "picocom"
)
RDP_BIN = shutil.which("xfreerdp") or shutil.which("xfreerdp3") or "xfreerdp"

# Templates série : (débit, flow, parity, databits, stopbits)
#   flow : n=none  x=xon/xoff  h=rts/cts
#   parity : n=none  e=even  o=odd
# Templates série par défaut (immuables — utilisés comme fallback).
_SERIAL_TEMPLATES_DEFAULT = {
    "Cisco IOS / IOS-XE / NX-OS": ("9600", "n", "n", "8", "1"),
    "HP Comware (H3C)": ("9600", "n", "n", "8", "1"),
    "Aruba AOS-S / AOS-CX": ("9600", "n", "n", "8", "1"),
    "Juniper JunOS": ("9600", "n", "n", "8", "1"),
    "Fortinet FortiOS": ("9600", "n", "n", "8", "1"),
    "Palo Alto PAN-OS": ("9600", "n", "n", "8", "1"),
    "F5 TMOS": ("19200", "n", "n", "8", "1"),
    "Linux / Raspberry Pi": ("115200", "n", "n", "8", "1"),
    "Arduino / ESP32": ("115200", "n", "n", "8", "1"),
    "RS-485 Modbus RTU": ("9600", "n", "n", "8", "1"),
    "Libre (manuel)": ("9600", "n", "n", "8", "1"),
}
# Copie mutable chargée au démarrage (peut être étendue / modifiée par l'user).
_SERIAL_TEMPLATES = dict(_SERIAL_TEMPLATES_DEFAULT)


def vte_run(terminal, command, arg=None):
    """Lance une commande dans un terminal VTE.

    Construit l'environnement complet (PATH, TERM, SSH_AUTH_SOCK, DISPLAY, etc.)
    et lance la commande via spawn_async (VTE >= 0.48) ou spawn_sync.

    Args:
        terminal (Vte.Terminal): Terminal VTE dans lequel lancer la commande.
        command (str): Chemin de l'executable a lancer.
        arg (list, optional): Arguments supplementaires. Defaults to None.
    """
    term_type = getattr(getattr(terminal, "host", None), "term", None) or "xterm"
    # fix #89: transmettre SSH_AUTH_SOCK et vars essentielles au processus VTE
    envv = ["PATH=%s" % os.getenv("PATH"), "TERM=%s" % term_type]
    for _ekey in (
        "SSH_AUTH_SOCK",
        "SSH_AGENT_PID",
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "HOME",
        "USER",
        "LOGNAME",
        "LANG",
        "LC_ALL",
        "XDG_RUNTIME_DIR",
        "DBUS_SESSION_BUS_ADDRESS",
        "GNOME_KEYRING_CONTROL",
    ):
        _eval = os.getenv(_ekey)
        if _eval:
            envv.append("%s=%s" % (_ekey, _eval))
    args = []
    args.append(command)
    if arg:
        args += arg
    flag_spawn = (
        GLib.SpawnFlags.DEFAULT if command == SHELL else GLib.SpawnFlags.FILE_AND_ARGV_ZERO
    )
    if TERMINAL_V048:
        terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            os.getenv("HOME"),
            args,
            envv,
            flag_spawn | GLib.SpawnFlags.SEARCH_PATH,
            None,
            None,
            -1,
            None,
            lambda term, pid, err, user_data: None,
            None,
        )
    else:
        terminal.spawn_sync(
            Vte.PtyFlags.DEFAULT,
            os.getenv("HOME"),
            args,
            envv,
            flag_spawn | GLib.SpawnFlags.DO_NOT_REAP_CHILD | GLib.SpawnFlags.SEARCH_PATH,
            None,
            None,
            None,
        )


class NotebookTabLabel(Gtk.Box):
    """Notebook tab label with close button."""

    def __init__(self, title, owner_, widget_, popup_):
        """Initialise l'instance.

        Args:
            title: Parametre title.
            owner_: Parametre owner_.
            widget_: Parametre widget_.
            popup_: Parametre popup_.
        """
        Gtk.Box.__init__(
            self, orientation=Gtk.Orientation.HORIZONTAL, homogeneous=False, spacing=0
        )

        self.title = title
        self.owner = owner_
        self.eb = Gtk.EventBox()
        label = self.label = Gtk.Label()
        self.eb.connect("button-press-event", self.popupmenu, label)
        label.halign = 0
        label.valign = 0.5
        label.set_text(title)
        self.eb.add(label)
        self.pack_start(self.eb, True, True, 0)
        label.show()
        self.eb.show()
        close_image = Gtk.Image.new_from_icon_name("window-close", Gtk.IconSize.MENU)
        _, image_w, image_h = Gtk.icon_size_lookup(Gtk.IconSize.MENU)
        self.widget_ = widget_
        self.popup = popup_
        close_btn = Gtk.Button()
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.connect("clicked", self.on_close_tab, owner_)
        close_btn.set_size_request(image_w + 7, image_h + 6)
        close_btn.add(close_image)
        self.eb2 = Gtk.EventBox()
        self.eb2.add(close_btn)
        self.pack_start(self.eb2, False, False, 0)
        self.eb2.show()
        close_btn.show_all()
        self.is_active = True
        self.eb.add_events(
            Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK
        )  # let the scroll-event pass through
        self.eb2.add_events(
            Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK
        )  # let the scroll-event pass through
        self.show()

    def set_selected(self, sel):
        """Marque ou demarque l'onglet comme selectionne visuellement.

        Args:
            selected (bool): True pour marquer comme selectionne.
        """
        if sel:
            self.get_style_context().add_class("selected")
        else:
            self.get_style_context().remove_class("selected")
        self.queue_draw()  # fix #67: forcer le redraw immédiat du label d'onglet

    def on_close_tab(self, widget, notebook, *args):
        """Gestionnaire du bouton fermeture d'onglet.

        Args:
            widget (Gtk.Button): Bouton clique.
        """
        from gnome_connection_manager import _, conf, msgconfirm

        if (
            conf.CONFIRM_ON_CLOSE_TAB
            and msgconfirm("%s [%s]?" % (_("Close console"), self.label.get_text().strip()))
            != Gtk.ResponseType.OK
        ):
            return True

        self.close_tab(widget)

    def close_tab(self, widget):
        """Ferme l'onglet associe au terminal.

        Args:
            widget: Parametre widget.
        """
        notebook = self.widget_.get_parent()
        page = notebook.page_num(self.widget_)
        if page >= 0:
            notebook.is_closed = True
            notebook.remove_page(page)
            notebook.is_closed = False
            self.widget_.destroy()

    def mark_tab_as_closed(self):
        """Marque visuellement l'onglet comme connexion fermee."""
        from gnome_connection_manager import conf

        self.label.set_markup(
            "<span color='darkgray' strikethrough='true'>%s</span>" % (self.label.get_text())
        )
        self.is_active = False
        if conf.AUTO_CLOSE_TAB != 0:
            if conf.AUTO_CLOSE_TAB == 2:
                parent_nb = self.widget_.get_parent()
                if parent_nb is None:
                    return
                terminal = parent_nb.get_nth_page(parent_nb.page_num(self.widget_)).get_child()
                if terminal.get_child_exit_status() != 0:
                    return
            self.close_tab(self.widget_)

    def mark_tab_as_active(self):
        """Marque visuellement l'onglet comme connexion active."""
        self.label.set_markup("%s" % (self.label.get_text()))
        self.is_active = True

    def get_text(self):
        """Retourne le texte de l'etiquette de l'onglet.

        Returns:
            str: Texte de l'onglet.
        """
        return self.label.get_text()

    def popupmenu(self, widget, event, label):
        """Affiche le menu contextuel de l'onglet.

        Args:
            widget (Gtk.Widget): Widget source.
            event (Gdk.EventButton): Evenement souris.
        """
        from gnome_connection_manager import conf

        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self.popup.label = self.label
            if self.is_active:
                self.popup.mnuReopen.hide()
            else:
                self.popup.mnuReopen.show()

            # show/hide split menu
            nb = self.widget_.get_parent()
            if nb.get_n_pages() > 1:
                self.popup.mnuSplitH.show()
                self.popup.mnuSplitV.show()
            else:
                self.popup.mnuSplitH.hide()
                self.popup.mnuSplitV.hide()

            # enable or disable log checkbox according to terminal
            self.popup.mnuLog.set_active(
                hasattr(self.widget_.get_children()[0], "log_handler_id")
                and self.widget_.get_children()[0].log_handler_id != 0
            )
            self.popup.popup(None, None, None, None, event.button, event.time)
            return True
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 2:
            from gnome_connection_manager import _, msgconfirm

            if (
                conf.CONFIRM_ON_CLOSE_TAB_MIDDLE
                and msgconfirm("%s [%s]?" % (_("Close console"), self.label.get_text().strip()))
                != Gtk.ResponseType.OK
            ):
                return True
            self.close_tab(self.widget_)


class EntryDialog(Gtk.Dialog):
    """Dialogue simple de saisie de texte."""

    def __init__(self, title, message, default_text="", modal=True, mask=False):
        """Initialise l'instance.

        Args:
            title: Parametre title.
            message: Parametre message.
            default_text: Parametre default_text.
            modal: Parametre modal.
            mask: Parametre mask.
        """
        Gtk.Dialog.__init__(self)
        self.set_title(title)
        self.connect("destroy", self.quit)
        self.connect("delete_event", self.quit)
        if modal:
            self.set_modal(True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        self.vbox.pack_start(box, True, True, 0)
        box.show()
        if message:
            label = Gtk.Label(label=message)
            box.pack_start(label, True, True, 0)
            label.show()
        self.entry = Gtk.Entry()
        self.entry.set_text(default_text)
        self.entry.set_visibility(not mask)
        box.pack_start(self.entry, True, True, 0)
        self.entry.show()
        self.entry.grab_focus()
        button = Gtk.Button(label=_("OK"))
        button.connect("clicked", self.click)
        self.entry.connect("activate", self.click)
        button.set_can_default(True)
        self.action_area.pack_start(button, True, True, 0)
        button.show()
        button.grab_default()
        button = Gtk.Button(label=_("Cancel"))
        button.connect("clicked", self.quit)
        button.set_can_default(True)
        self.action_area.pack_start(button, True, True, 0)
        button.show()
        self.ret = None

    def quit(self, w=None, event=None):
        """Ferme la boite de dialogue.

        Args:
            widget (Gtk.Widget): Widget declencheur.
        """
        self.hide()
        self.destroy()

    def click(self, button):
        """Valide la saisie et ferme la boite de dialogue.

        Args:
            widget (Gtk.Widget): Widget declencheur.
        """
        self.value = self.entry.get_text()
        self.response(Gtk.ResponseType.OK)


class CellTextView(Gtk.TextView, Gtk.CellEditable):
    """TextView pour edition en ligne dans une cellule."""

    __gtype_name__ = "CellTextView"

    __gproperties__ = {
        "editing-canceled": (
            bool,
            "Editing cancelled",
            "Editing was cancelled",
            False,
            GObject.ParamFlags.READWRITE,
        ),
    }

    def do_editing_done(self, *args):
        """Signale la fin de l'edition en ligne."""
        self.remove_widget()

    def do_remove_widget(self, *args):
        """Supprime le widget d'edition en ligne."""
        pass

    def do_start_editing(self, *args):
        """Demarre l'edition en ligne.

        Args:
            event (Gdk.Event): Evenement declencheur.
        """
        pass

    def get_text(self):
        """Retourne le texte de l'etiquette de l'onglet.

        Returns:
            str: Texte de l'onglet.
        """
        text_buffer = self.get_buffer()
        bounds = text_buffer.get_bounds()
        return text_buffer.get_text(*bounds, include_hidden_chars=True)

    def set_text(self, text):
        """Definit le texte de l'editeur.

        Args:
            text (str): Texte a afficher.
        """
        self.get_buffer().set_text(text)


class MultilineCellRenderer(Gtk.CellRendererText):
    """Renderer pour édition multiligne dans une cellule."""

    __gtype_name__ = "MultilineCellRenderer"

    def __init__(self):
        """Initialise l'instance."""
        Gtk.CellRendererText.__init__(self)
        self._in_editor_menu = False

    def _on_editor_focus_out_event(self, editor, *args):
        """Gestionnaire de perte de focus de l'editeur.

        Args:
            widget (Gtk.Widget): Widget source.
            event (Gdk.EventFocus): Evenement focus.
        """
        if self._in_editor_menu:
            return
        editor.remove_widget()
        self.emit("editing-canceled")

    def _on_editor_key_press_event(self, editor, event):
        """Gestionnaire de touche dans l'editeur inline.

        Args:
            widget (Gtk.Widget): Widget source.
            event (Gdk.EventKey): Evenement clavier.
        """
        if event.state & (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK):
            return
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            editor.remove_widget()
            self.emit("edited", editor.path, editor.get_text())
        elif event.keyval == Gdk.KEY_Escape:
            editor.remove_widget()
            self.emit("editing-canceled")

    def _on_editor_populate_popup(self, editor, menu):
        """Gestionnaire de remplissage du menu contextuel de l'editeur.

        Args:
            widget (Gtk.Widget): Widget source.
            popup (Gtk.Menu): Menu contextuel.
        """
        self._in_editor_menu = True

        def on_menu_unmap(menu, self):
            """Gestionnaire de fermeture du menu contextuel.

            Args:
                widget (Gtk.Menu): Menu ferme.
            """
            self._in_editor_menu = False

        menu.connect("unmap", on_menu_unmap, self)

    def _on_editor_pressed(self, editor, menu):
        # avoid bug: gtk_text_mark_get_buffer: assertion 'GTK_IS_TEXT_MARK (mark)' failed
        """Gestionnaire de clic souris dans l'editeur.

        Args:
            widget (Gtk.Widget): Widget source.
            event (Gdk.EventButton): Evenement souris.
        """
        return True

    def do_start_editing(self, event, widget, path, bg_area, cell_area, flags):
        """Demarre l'edition en ligne.

        Args:
            event (Gdk.Event): Evenement declencheur.
        """
        from gnome_connection_manager import set_widget_font

        editor = CellTextView()
        set_widget_font(editor, self.props.font_desc)
        editor.set_text(self.props.text)
        editor.set_size_request(cell_area.width, cell_area.height)
        editor.set_border_width(min(self.props.xpad, self.props.ypad))
        editor.path = path
        editor.connect("focus-out-event", self._on_editor_focus_out_event)
        editor.connect("key-press-event", self._on_editor_key_press_event)
        editor.connect("populate-popup", self._on_editor_populate_popup)
        editor.connect("button-press-event", self._on_editor_pressed)
        editor.show()
        return editor


class RdpEmbeddedTab(Gtk.Box):
    """Widget RDP avec session xfreerdp embarquee via XEmbed (Gtk.Socket).

    La fenetre xfreerdp s'affiche directement dans l'onglet GCM.
    Necessite X11 (Wayland+XWayland ou Xorg). Fallback: RdpTab.
    """

    def __init__(self, host, get_password_fn):
        """Initialise le panneau RDP embarque.

        Args:
            host (Host): Objet Host GCM avec protocol='rdp'.
            get_password_fn (callable): Fonction retournant le mot de passe dechiffre.
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.host = host
        self._get_password = get_password_fn
        app_logger.debug(f"RdpEmbeddedTab | init | mdp={self._get_password()}")
        self._proc = None
        self._xid = None
        self._build_ui()

    def _build_ui(self):
        """Construit la barre d'outils et la zone XEmbed."""
        h = self.host
        port = getattr(h, "port", 3389) or 3389

        # Barre d'outils compacte
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.set_margin_start(6)
        toolbar.set_margin_end(6)
        toolbar.set_margin_top(4)
        toolbar.set_margin_bottom(4)

        title = Gtk.Label()
        title.set_markup(f"<b>RDP</b> <small>{h.user}@{h.host}:{port}</small>")
        title.set_xalign(0)
        toolbar.pack_start(title, True, True, 0)

        self._lbl_status = Gtk.Label(label=_("Waiting…"))
        self._lbl_status.get_style_context().add_class("dim-label")
        toolbar.pack_start(self._lbl_status, False, False, 8)

        self._btn_connect = Gtk.Button(label=_("Connect"))
        self._btn_connect.get_style_context().add_class("suggested-action")
        self._btn_connect.connect("clicked", self._on_connect)
        toolbar.pack_start(self._btn_connect, False, False, 0)

        self._btn_disconnect = Gtk.Button(label=_("Disconnect"))
        self._btn_disconnect.set_sensitive(False)
        self._btn_disconnect.connect("clicked", self._on_disconnect)
        toolbar.pack_start(self._btn_disconnect, False, False, 0)

        self.pack_start(toolbar, False, False, 0)
        self.pack_start(Gtk.Separator(), False, False, 0)

        # Zone XEmbed
        self._socket = Gtk.Socket()
        self._socket.connect("plug-removed", self._on_plug_removed)
        self._socket.connect("plug-added", self._on_plug_added)
        self._socket.connect("realize", self._on_socket_realized)
        self._socket.set_hexpand(True)
        self._socket.set_vexpand(True)
        self.pack_start(self._socket, True, True, 0)

        self.show_all()

    def _on_socket_realized(self, widget):
        """Recupere le XID apres realisation du socket.

        Args:
            widget (Gtk.Socket): Socket GTK.
        """

        self.connect_rdp()

    def _on_plug_added(self, widget):
        """Signale que xfreerdp s'est connecte au socket XEmbed.

        Args:
            widget (Gtk.Socket): Socket GTK.
        """
        GLib.idle_add(self._set_status, _("Connect"))
        GLib.idle_add(self._btn_connect.set_sensitive, False)
        GLib.idle_add(self._btn_disconnect.set_sensitive, True)

    def _on_plug_removed(self, widget):
        """Signale que xfreerdp s'est deconnecte du socket XEmbed.

        Args:
            widget (Gtk.Socket): Socket GTK.

        Returns:
            bool: True pour garder le socket en vie.
        """
        GLib.idle_add(self._set_status, _("Session ended"))
        GLib.idle_add(self._btn_connect.set_sensitive, True)
        GLib.idle_add(self._btn_disconnect.set_sensitive, False)
        self._proc = None
        return True  # conserver le socket (ne pas le détruire)

    def _build_cmd(self):
        """Construit la commande xfreerdp avec /parent-window pour XEmbed.

        Returns:
            list[str]: Arguments pour subprocess.Popen.
        """
        h = self.host
        port = getattr(h, "port", 3389) or 3389
        pwd = self._get_password() or ""
        opts = getattr(h, "extra_params", "") or ""
        user = h.user

        if "\\" in user:
            domain, uname = user.split("\\", 1)
            cmd = [RDP_BIN, f"/v:{h.host}:{port}", f"/d:{domain}", f"/u:{uname}"]
        else:
            cmd = [RDP_BIN, f"/v:{h.host}:{port}", f"/u:{user}"]

        if pwd:
            cmd.append(f"/p:{pwd}")

        xid = self._xid or self._socket.get_id()
        cmd += [
            "/cert:ignore",
            "/dynamic-resolution",
            f"/parent-window:{hex(xid)}",
        ]

        if opts:
            cmd += shlex.split(opts)
        app_logger.debug("RdpEmbeddedTab | _build_cmd | cmd={cmd}", cmd=cmd)
        return cmd

    def _on_connect(self, widget):
        """Lance xfreerdp en mode XEmbed.

        Args:
            widget (Gtk.Button): Bouton declencheur (peut etre None).
        """
        if self._proc is not None and self._proc.poll() is None:
            return
        # S'assurer que le socket est realize
        if not self._socket.get_realized():
            self._socket.realize()
        # self._xid = self._socket.get_id()

        cmd = self._build_cmd()
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            self._set_status(_("xfreerdp not found"))
            return
        self._set_status(_("Connecting…"))
        self._btn_connect.set_sensitive(False)
        threading.Thread(target=self._wait_proc, daemon=True).start()

    def _wait_proc(self):
        """Attend la fin du processus xfreerdp en arriere-plan."""
        if self._proc:
            rc = self._proc.wait()
            if rc != 0:
                GLib.idle_add(
                    self._set_status,
                    _("Ended (code {rc})").format(rc=rc),
                )
        GLib.idle_add(self._btn_connect.set_sensitive, True)
        GLib.idle_add(self._btn_disconnect.set_sensitive, False)
        self._proc = None

    def _on_disconnect(self, widget):
        """Termine la session xfreerdp.

        Args:
            widget (Gtk.Button): Bouton declencheur.
        """
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        self._set_status(_("Disconnect"))
        self._btn_connect.set_sensitive(True)
        self._btn_disconnect.set_sensitive(False)

    def _set_status(self, text):
        """Met a jour le label de statut.

        Args:
            text (str): Nouveau statut.
        """
        self._lbl_status.set_text(text)

    def connect_rdp(self):
        """Lance la connexion RDP automatiquement (appele depuis addTab)."""

        self._xid = self._socket.get_id()
        app_logger.debug("RdpEmbeddedTab | _on_socket_realized | XID={xid}", xid=self._xid)
        if self._socket.get_realized():
            self._on_connect(None)
        else:
            # Connexion unique : stocker l'ID pour eviter l'accumulation de signaux
            if not getattr(self, "_realize_handler_id", None):
                self._realize_handler_id = self._socket.connect(
                    "realize",
                    self._on_realize_connect,
                )

    def _on_realize_connect(self, widget):
        """Callback realize unique : deconnecte le signal puis lance xfreerdp.

        Args:
            widget (Gtk.Socket): Socket GTK.
        """
        if self._realize_handler_id:
            self._socket.disconnect(self._realize_handler_id)
            self._realize_handler_id = None
        GLib.idle_add(self._on_connect, None)


class RdpTab(Gtk.Box):
    """Widget affiche dans le Gtk.Notebook pour les connexions RDP.

    Lance xfreerdp en fenetre externe, affiche le statut, le log stderr
    et un champ d'options modifiable a la volee.
    """

    def __init__(self, host, get_password_fn):
        """Initialise le panneau RDP.

        Args:
            host (Host): Objet Host GCM avec protocol='rdp'.
            get_password_fn (callable): Fonction retournant le mot de passe dechiffre.
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.host = host
        self._get_password = get_password_fn
        app_logger.debug(f"RdpTab | init | mdp={self._get_password()}")
        self._proc = None
        self._xid = None
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_margin_top(16)
        self.set_margin_bottom(16)
        self._build_ui()

    def _build_ui(self):
        """Construit l'interface du panneau RDP."""
        h = self.host
        port = getattr(h, "port", 3389) or 3389
        title = Gtk.Label()
        title.set_markup(f"<b>RDP \u2014 {h.name}</b><small>   {h.user}@{h.host}:{port}</small>")
        title.set_xalign(0)
        self.pack_start(title, False, False, 0)
        if h.description:
            d = Gtk.Label(label=h.description)
            d.set_xalign(0)
            d.get_style_context().add_class("dim-label")
            self.pack_start(d, False, False, 0)
        self.pack_start(Gtk.Separator(), False, False, 4)
        self._lbl_status = Gtk.Label(label=_("Waiting…"))
        self._lbl_status.set_xalign(0)
        self.pack_start(self._lbl_status, False, False, 0)
        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._btn_connect = Gtk.Button(label=_("Connect"))
        self._btn_connect.get_style_context().add_class("suggested-action")
        self._btn_connect.connect("clicked", self._on_connect)
        hb.pack_start(self._btn_connect, False, False, 0)
        self._btn_disconnect = Gtk.Button(label=_("Disconnect"))
        self._btn_disconnect.set_sensitive(False)
        self._btn_disconnect.connect("clicked", self._on_disconnect)
        hb.pack_start(self._btn_disconnect, False, False, 0)
        self.pack_start(hb, False, False, 0)
        self.pack_start(Gtk.Separator(), False, False, 4)
        hb2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hb2.pack_start(Gtk.Label(label=_("xfreerdp options:")), False, False, 0)
        self._entry_opts = Gtk.Entry()
        self._entry_opts.set_text(getattr(h, "extra_params", "") or "")
        self._entry_opts.set_tooltip_text(
            "Parametres additionnels xfreerdp\n"
            "Ex : /drive:home,/home/user  /sound:sys:alsa  /multimon  +clipboard"
        )
        hb2.pack_start(self._entry_opts, True, True, 0)
        self.pack_start(hb2, False, False, 0)
        self.pack_start(Gtk.Label(label=_("xfreerdp log:")), False, False, 2)
        self._log_buf = Gtk.TextBuffer()
        self._socket = Gtk.Socket()
        lv = Gtk.TextView(buffer=self._log_buf)
        lv.set_editable(False)
        lv.set_monospace(True)
        lv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        sw = Gtk.ScrolledWindow()
        sw.set_min_content_height(160)
        sw.add(lv)
        self.pack_start(sw, True, True, 0)
        self._log_view = lv
        self.show_all()

    def _build_cmd(self):
        """Construit la commande xfreerdp depuis les attributs Host rdp_*.

        Priorité des champs structurés (rdp_domain, rdp_geometry,
        rdp_cert_ignore…) sur le champ extra_params (options libres).

        Returns:
            list[str]: Liste d'arguments pour subprocess.Popen.
        """
        h = self.host
        port = getattr(h, "port", 3389) or 3389
        pwd = self._get_password() or ""
        # opts = self._entry_opts.get_text().strip()

        opts = (getattr(h, "extra_params", "") or "").strip()

        # ── Identité : domaine prioritaire sur la notation user\\domain
        rdp_domain = (getattr(h, "rdp_domain", "") or "").strip()
        user = h.user or ""
        if rdp_domain:
            cmd = [RDP_BIN, f"/v:{h.host}:{port}", f"/d:{rdp_domain}", f"/u:{user}"]
        elif "\\" in user:
            domain, uname = user.split("\\", 1)
            cmd = [RDP_BIN, f"/v:{h.host}:{port}", f"/d:{domain}", f"/u:{uname}"]
        else:
            cmd = [RDP_BIN, f"/v:{h.host}:{port}", f"/u:{user}"]
        if pwd:
            cmd.append(f"/p:{pwd}")

        # ── Résolution
        geo = (getattr(h, "rdp_geometry", "") or "").strip()
        if geo == "fullscreen":
            cmd.append("/f")
        elif geo == "custom":
            w = (getattr(h, "rdp_width", "") or "").strip()
            ht = (getattr(h, "rdp_height", "") or "").strip()
            if w and ht:
                cmd += [f"/w:{w}", f"/h:{ht}"]
        elif "x" in geo:
            w, ht = geo.split("x", 1)
            cmd += [f"/w:{w}", f"/h:{ht}"]

        # ── Flags booléens
        truthy = (True, "True", "true", "1", "yes")
        if getattr(h, "rdp_cert_ignore", False) in truthy:
            cmd.append("/cert:ignore")
        if getattr(h, "rdp_dyn_res", False) in truthy:
            cmd.append("/dynamic-resolution")

        # ── RemoteApp
        remote_app = (getattr(h, "rdp_remote_app", "") or "").strip()
        if remote_app:
            cmd.append(f"/app:{remote_app}")

        # ── XEmbed obligatoire
        xid = self._xid or self._socket.get_id()
        cmd.append(f"/parent-window:{hex(xid)}")

        # ── Options libres additionnelles
        if opts:
            cmd += shlex.split(opts)
        app_logger.debug("RdpTab | _build_cmd | cmd={cmd}", cmd=cmd)
        return cmd

    def _on_connect(self, widget):
        """Lance la connexion xfreerdp.

        Args:
            widget (Gtk.Button): Bouton declencheur (peut etre None).
        """
        if self._proc is not None and self._proc.poll() is None:
            return
        # Persister les options modifiees par l'utilisateur dans le widget
        self.host.extra_params = self._entry_opts.get_text().strip()
        cmd = self._build_cmd()
        cmd_display = ["****" if a.startswith("/p:") else a for a in cmd]
        self._log(f"$ {' '.join(cmd_display)}\n")
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except FileNotFoundError:
            self._log(
                f"ERREUR : xfreerdp introuvable ({RDP_BIN})\n  sudo apt install freerdp2-x11\n"
            )
            self._set_status(_("xfreerdp not found"))
            return
        self._set_status(_("Connecting…"))
        self._btn_connect.set_sensitive(False)
        self._btn_disconnect.set_sensitive(True)
        threading.Thread(target=self._read_output, daemon=True).start()

    def _on_disconnect(self, widget):
        """Termine le processus xfreerdp.

        Args:
            widget (Gtk.Button): Bouton declencheur.
        """
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        self._set_status(_("Disconnect"))
        self._btn_connect.set_sensitive(True)
        self._btn_disconnect.set_sensitive(False)

    def _read_output(self):
        """Lit la sortie de xfreerdp en arriere-plan et l'affiche dans le log."""
        try:
            for line in self._proc.stdout:
                GLib.idle_add(self._log, line)
        except Exception:
            pass
        rc = self._proc.wait()
        if rc == 0:
            GLib.idle_add(self._set_status, _("Session ended"))
        else:
            GLib.idle_add(self._set_status, _("Ended (code {rc})").format(rc=rc))
        GLib.idle_add(self._btn_connect.set_sensitive, True)
        GLib.idle_add(self._btn_disconnect.set_sensitive, False)

    def _log(self, text):
        """Ajoute du texte dans le TextView de log.

        Args:
            text (str): Texte a afficher.
        """
        self._log_buf.insert(self._log_buf.get_end_iter(), text)
        self._log_view.scroll_mark_onscreen(self._log_buf.get_insert())

    def _set_status(self, text):
        """Met a jour le label de statut.

        Args:
            text (str): Nouveau statut.
        """
        self._lbl_status.set_text(text)

    def connect_rdp(self):
        """Lance la connexion RDP automatiquement (appele depuis addTab)."""
        self._on_connect(None)


class VncTab(Gtk.Box):
    """Widget affiche dans le Gtk.Notebook pour les connexions VNC.

    Lance vncviewer (ou vinagre/remmina) en fenetre externe.
    Affiche le statut et un champ d'options modifiable.
    """

    def __init__(self, host, get_password_fn):
        """Initialise le panneau VNC.

        Args:
            host (Host): Objet Host GCM avec protocol='vnc'.
            get_password_fn (callable): Fonction retournant le mot de passe dechiffre.
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.host = host
        self._get_password = get_password_fn
        app_logger.debug(f"VncTab | init | mdp={self._get_password()}")
        self._proc = None
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_margin_top(16)
        self.set_margin_bottom(16)
        self._build_ui()

    def _build_ui(self):
        """Construit l'interface du panneau VNC."""
        h = self.host
        port = getattr(h, "port", "5900") or "5900"
        title = Gtk.Label()
        title.set_markup(f"<b>VNC — {h.name}</b><small>   {h.host}:{port}</small>")
        title.set_xalign(0)
        self.pack_start(title, False, False, 0)
        if h.description:
            d = Gtk.Label(label=h.description)
            d.set_xalign(0)
            d.get_style_context().add_class("dim-label")
            self.pack_start(d, False, False, 0)
        self.pack_start(Gtk.Separator(), False, False, 4)
        self._lbl_status = Gtk.Label(label=_("Waiting…"))
        self._lbl_status.set_xalign(0)
        self.pack_start(self._lbl_status, False, False, 0)
        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._btn_connect = Gtk.Button(label=_("Connect"))
        self._btn_connect.get_style_context().add_class("suggested-action")
        self._btn_connect.connect("clicked", self._on_connect)
        hb.pack_start(self._btn_connect, False, False, 0)
        self._btn_disconnect = Gtk.Button(label=_("Disconnect"))
        self._btn_disconnect.set_sensitive(False)
        self._btn_disconnect.connect("clicked", self._on_disconnect)
        hb.pack_start(self._btn_disconnect, False, False, 0)
        self.pack_start(hb, False, False, 0)
        self.pack_start(Gtk.Separator(), False, False, 4)
        hb2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hb2.pack_start(Gtk.Label(label=_("xfreerdp options:")), False, False, 0)
        self._entry_opts = Gtk.Entry()
        self._entry_opts.set_text(getattr(h, "extra_params", "") or "")
        self._entry_opts.set_tooltip_text(
            "Paramètres additionnels vncviewer\nEx: -FullScreen -FullColour -CompressLevel 6"
        )
        hb2.pack_start(self._entry_opts, True, True, 0)
        self.pack_start(hb2, False, False, 0)
        # Binaire détecté
        lbl_bin = Gtk.Label()
        lbl_bin.set_markup(f"<small><i>Binaire détecté : {VNC_BIN}</i></small>")
        lbl_bin.set_xalign(0)
        self.pack_start(lbl_bin, False, False, 0)
        self.show_all()

    def _build_cmd(self):
        """Construit la commande VNC depuis les attributs Host vnc_*.

        Sélectionne le binaire selon host.vnc_viewer, applique
        host.vnc_display, host.vnc_view_only et host.vnc_fullscreen.
        Le champ extra_params est appliqué en dernier.

        Returns:
            tuple[list[str], str]: (arguments Popen, mot de passe en clair).
        """
        h = self.host
        port = str(getattr(h, "port", "5900+") or "5900")
        pwd = self._get_password() or ""
        app_logger.debug("VNC 1 password for host {host} is '{pwd}'", host=h.name, pwd=pwd)
        opts_str = self._entry_opts.get_text().strip()
        truthy = (True, "True", "true", "1", "yes")

        # ── Résolution viewer : attribut structuré > auto-détection
        viewer_id = (getattr(h, "vnc_viewer", "") or "").strip()
        _VNC_BINS = {
            "tigervnc": shutil.which("vncviewer"),
            "vinagre": shutil.which("vinagre"),
            "remmina": shutil.which("remmina"),
            "krdc": shutil.which("krdc"),
        }
        vnc_bin = (_VNC_BINS.get(viewer_id) or VNC_BIN) if viewer_id else VNC_BIN
        bin_name = os.path.basename(vnc_bin)

        # ── Display number → port effectif
        display = (getattr(h, "vnc_display", "") or "").strip()
        if display:
            try:
                effective_port = str(5900 + int(display))
            except ValueError:
                effective_port = port
        else:
            effective_port = port

        # ── Construction de la commande selon le binaire
        if bin_name in ("vinagre",) or bin_name == "remmina":
            cmd = [vnc_bin, f"vnc://{h.host}:{effective_port}"]
        elif bin_name == "krdc":
            cmd = [vnc_bin, f"vnc:/{h.host}:{effective_port}"]
        else:
            # tigervnc / xtightvncviewer / vncviewer générique
            cmd = [vnc_bin, f"{h.host}:{effective_port}"]
            if pwd:
                app_logger.debug(f"VNC password provided for host {h.name} '{pwd}' ")
                self.make_vnc_passwd(pwd, "/tmp/klfhghzz")
                cmd += ["-passwd", "/tmp/klfhghzz"]
            if getattr(h, "vnc_view_only", False) in truthy:
                cmd.append("-ViewOnly")
            if getattr(h, "vnc_fullscreen", False) in truthy:
                cmd.append("-FullScreen")
                app_logger.debug(f"VNC fullscreen requested for host {h.name}; {cmd} ")

        if opts_str:
            cmd += shlex.split(opts_str)

        app_logger.debug("VNC command built for host {host}: {cmd}", host=h.name, cmd=cmd)
        return cmd, pwd

    def make_vnc_passwd(self, password: str, path: str) -> None:
        """Génère un fichier passwd compatible TigerVNC/RFB.

        Args:
            password: Mot de passe en clair (tronqué à 8 caractères).
            path: Chemin de destination du fichier passwd.
        """
        # Clé fixe RFB, bits inversés par octet
        key = bytes([self.reverse_bits(b) for b in [23, 82, 107, 6, 35, 78, 88, 7]])
        # Pad/tronque à 8 octets
        pwd_bytes = password[:8].encode("ascii").ljust(8, b"\x00")
        cipher = DES.new(key, DES.MODE_ECB)
        encrypted = cipher.encrypt(pwd_bytes)

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(encrypted)
        os.chmod(path, 0o600)

    def reverse_bits(self, b: int) -> int:
        return int(f"{b:08b}"[::-1], 2)

    def _on_connect(self, widget):
        """Lance la connexion VNC.

        Args:
            widget (Gtk.Button): Bouton declencheur.
        """
        if self._proc is not None and self._proc.poll() is None:
            return
        self.host.extra_params = self._entry_opts.get_text().strip()
        cmd, pwd = self._build_cmd()
        bin_name = os.path.basename(VNC_BIN)
        try:
            if bin_name not in ("vinagre", "remmina") and pwd:
                # Passer le mot de passe sur stdin
                self._proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._proc.stdin.write(pwd.encode() + b"\n")
                self._proc.stdin.close()
            else:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except FileNotFoundError:
            self._set_status(_("xfreerdp not found"))
            return
        self._set_status(_("Connecting…"))
        self._btn_connect.set_sensitive(False)
        self._btn_disconnect.set_sensitive(True)
        threading.Thread(target=self._wait_proc, daemon=True).start()

    def _wait_proc(self):
        """Attend la fin du processus VNC en arriere-plan."""
        if self._proc:
            rc = self._proc.wait()
            if rc != 0:
                GLib.idle_add(self._set_status, _("Ended (code {rc})").format(rc=rc))
            else:
                GLib.idle_add(self._set_status, _("Session ended"))
        GLib.idle_add(self._btn_connect.set_sensitive, True)
        GLib.idle_add(self._btn_disconnect.set_sensitive, False)
        self._proc = None

    def _on_disconnect(self, widget):
        """Termine la session VNC.

        Args:
            widget (Gtk.Button): Bouton declencheur.
        """
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        self._set_status(_("Disconnect"))
        self._btn_connect.set_sensitive(True)
        self._btn_disconnect.set_sensitive(False)

    def _set_status(self, text):
        """Met a jour le label de statut.

        Args:
            text (str): Nouveau statut.
        """
        self._lbl_status.set_text(text)

    def connect_vnc(self):
        """Lance la connexion VNC automatiquement (appele depuis addTab)."""
        self._on_connect(None)


class SpiceTab(Gtk.Box):
    """Widget affiche dans le Gtk.Notebook pour les connexions SPICE.

    Lance remote-viewer (virt-viewer) en fenetre externe avec URI spice://.
    """

    def __init__(self, host, get_password_fn):
        """Initialise le panneau SPICE.

        Args:
            host (Host): Objet Host GCM avec protocol='spice'.
            get_password_fn (callable): Fonction retournant le mot de passe dechiffre.
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.host = host
        self._get_password = get_password_fn
        app_logger.debug(f"SpiceTab | init | mdp={self._get_password()}")
        self._proc = None
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_margin_top(16)
        self.set_margin_bottom(16)
        print(f"_build_ui() called for SpiceTab with host: {host.name}")
        self._build_ui()

    def _build_ui(self):
        """Construit l'interface du panneau SPICE."""
        h = self.host

        port = getattr(h, "port", "5930") or "5930"
        title = Gtk.Label()
        title.set_markup(f"<b>SPICE — {h.name}</b><small>   {h.host}:{port}</small>")
        title.set_xalign(0)
        self.pack_start(title, False, False, 0)
        if h.description:
            d = Gtk.Label(label=h.description)
            d.set_xalign(0)
            d.get_style_context().add_class("dim-label")
            self.pack_start(d, False, False, 0)
        self.pack_start(Gtk.Separator(), False, False, 4)
        self._lbl_status = Gtk.Label(label=_("Waiting…"))
        self._lbl_status.set_xalign(0)
        self.pack_start(self._lbl_status, False, False, 0)
        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._btn_connect = Gtk.Button(label=_("Connect"))
        self._btn_connect.get_style_context().add_class("suggested-action")
        self._btn_connect.connect("clicked", self._on_connect)
        hb.pack_start(self._btn_connect, False, False, 0)
        self._btn_disconnect = Gtk.Button(label=_("Disconnect"))
        self._btn_disconnect.set_sensitive(False)
        self._btn_disconnect.connect("clicked", self._on_disconnect)
        hb.pack_start(self._btn_disconnect, False, False, 0)
        self.pack_start(hb, False, False, 0)
        self.pack_start(Gtk.Separator(), False, False, 4)
        hb2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hb2.pack_start(Gtk.Label(label=_("xfreerdp options:")), False, False, 0)
        self._entry_opts = Gtk.Entry()
        self._entry_opts.set_text(getattr(h, "extra_params", "") or "")
        self._entry_opts.set_tooltip_text(
            "Paramètres additionnels remote-viewer\n"
            "Ex: --spice-ca-file=/etc/ssl/certs/ca.crt --full-screen"
        )
        hb2.pack_start(self._entry_opts, True, True, 0)
        self.pack_start(hb2, False, False, 0)
        lbl_bin = Gtk.Label()
        lbl_bin.set_markup(f"<small><i>Binaire détecté : {SPICE_BIN}</i></small>")
        lbl_bin.set_xalign(0)
        self.pack_start(lbl_bin, False, False, 0)
        app_logger.debug(f"SPICE: SPICE_BIN = {SPICE_BIN}")
        self.show_all()

    def _build_cmd(self):
        """Construit la commande remote-viewer depuis les attributs Host spice_*.

        Trois modes sélectionnés par host.spice_mode :
        - ``"proxmox"`` : ticket SPICE généré via pvesh sur l'hyperviseur
          (host=nœud PVE, user=root, spice_px_node, spice_px_vmid).
        - ``"libvirt"`` : tunnel libvirt natif virt-viewer
          (spice_libvirt_uri + spice_vm_name).
        - ``"uri"`` (défaut) : URI spice://host:port directe, avec TLS
          optionnel (spice_tls_port, spice_ca_cert).

        Returns:
            list[str]: Arguments pour subprocess.Popen, ou None si erreur.
        """

        pairs = parse_spice_hosts(Path(CONFIG_FILE))
        try:
            n = HostsUpdater().update(pairs)
        except PermissionError as exc:
            app_logger.error("hosts update | {exc}", exc=exc)

        h = self.host
        port = str(getattr(h, "port", "5930") or "5930")
        pwd = self._get_password() or ""
        opts_str = self._entry_opts.get_text().strip()
        spice_mode = (getattr(h, "spice_mode", "uri") or "uri").strip()

        # ── Mode Proxmox : génération de ticket SPICE via pvesh
        if spice_mode == "proxmox":
            node_name = (getattr(h, "spice_px_node", "") or "").strip()
            vmid = (getattr(h, "spice_px_vmid", "") or "").strip()
            if not node_name or not vmid:
                self._set_status(_("Erreur : Proxmox node et VMID requis"))
                return None
            # L'hôte SSH est le champ host standard (API Proxmox)
            hv_host = h.host
            hv_port = (
                int(h.port) if str(h.port).isdigit() and int(h.port) not in (5900, 5930) else 22
            )
            hv_user = h.user or "root"
            try:
                import paramiko as _paramiko

                _client = _paramiko.SSHClient()
                _client.set_missing_host_key_policy(_paramiko.AutoAddPolicy())
                _client.connect(hv_host, port=hv_port, username=hv_user, timeout=10)
                cmd_pvesh = (
                    f"pvesh create /nodes/{node_name}/qemu/{vmid}/spiceproxy --output-format json"
                )
                app_logger.debug(f"SPICE: SSH {hv_user}@{hv_host}:{hv_port} cmd = {cmd_pvesh}")
                _stdin, stdout, stderr = _client.exec_command(cmd_pvesh)
                out = stdout.read().decode().strip()
                _client.close()
            except Exception as exc:
                app_logger.debug(f"SPICE: Erreur SSH : {exc}")
                self._set_status(_(f"Erreur SSH : {exc}"))
                return None
            try:
                ticket = json.loads(out)
            except Exception:
                self._set_status(_(f"Erreur ticket SPICE : {out[:80]}"))
                return None
            vv_lines = [
                "[virt-viewer]",
                "type=spice",
                f"host={ticket['host']}",
                f"tls-port={ticket['tls-port']}",
                f"password={ticket['password']}",
                f"proxy={ticket.get('proxy', '')}",
                f"host-subject={ticket.get('host-subject', '')}",
                f"ca={ticket.get('ca', '')}",
                "delete-this-file=1",
            ]
            import tempfile as _tempfile

            vv_fd, vv_path = _tempfile.mkstemp(suffix=".vv", prefix="gcm-spice-")
            app_logger.debug(f"SPICE: fichier temporaire {vv_fd},{vv_path}")
            d = "\n"
            with os.fdopen(vv_fd, "w") as vv_f:
                vv_f.write(d.join(vv_lines) + d)

            app_logger.debug(f"SPICE: file = {d.join(vv_lines) + d}")
            app_logger.debug(f"SPICE: vv_lines = {vv_lines}")
            app_logger.debug(f"SPICE: lancement remote-viewer {SPICE_BIN} {vv_path}")
            return [SPICE_BIN, vv_path]

        # ── Mode libvirt : virt-viewer avec URI qemu+ssh://
        if spice_mode == "libvirt":
            libvirt_uri = (getattr(h, "spice_libvirt_uri", "") or "").strip()
            vm_name = (getattr(h, "spice_vm_name", "") or "").strip()
            if not libvirt_uri:
                self._set_status(_("Erreur : libvirt URI requis"))
                return None
            cmd = [SPICE_BIN, "--connect", libvirt_uri]

            if vm_name:
                cmd.append(vm_name)
            if opts_str:
                cmd += shlex.split(opts_str)
            app_logger.debug(f"SPICE: libvirt command = {cmd}")
            return cmd

        # ── Mode URI directe : spice://host:port avec TLS optionnel
        if pwd:
            uri = f"spice://{h.host}?port={port}&password={pwd}"
        else:
            uri = f"spice://{h.host}?port={port}"
        cmd = [SPICE_BIN, uri]

        tls_port = (getattr(h, "spice_tls_port", "") or "").strip()
        ca_cert = (getattr(h, "spice_ca_cert", "") or "").strip()
        if tls_port:
            cmd.append(f"--spice-tls-port={tls_port}")
        if ca_cert:
            cmd.append(f"--spice-ca-file={ca_cert}")
        if opts_str:
            cmd += shlex.split(opts_str)
        app_logger.debug(f"SPICE: direct URI command = {cmd}")
        return cmd

    def _on_connect(self, widget):
        """Lance la connexion SPICE.

        Args:
            widget (Gtk.Button): Bouton declencheur.
        """
        if self._proc is not None and self._proc.poll() is None:
            return
        self.host.extra_params = self._entry_opts.get_text().strip()
        cmd = self._build_cmd()
        app_logger.debug(cmd)
        if cmd is None:
            return
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        except FileNotFoundError:
            app_logger.debug("Viewer not found")
            self._set_status(_("xfreerdp not found"))
            return
        except Exception as e:
            app_logger.debug(f"Error launching viewer: {e}")
            self._set_status(_("Error launching viewer"))
            return
        self._set_status(_("Connecting…"))
        self._btn_connect.set_sensitive(False)
        self._btn_disconnect.set_sensitive(True)
        threading.Thread(target=self._wait_proc, daemon=True).start()

    def _wait_proc(self):
        """Attend la fin du processus SPICE en arriere-plan."""
        if self._proc:
            rc = self._proc.wait()
            if rc != 0:
                GLib.idle_add(self._set_status, _("Ended (code {rc})").format(rc=rc))
            else:
                GLib.idle_add(self._set_status, _("Session ended"))
        GLib.idle_add(self._btn_connect.set_sensitive, True)
        GLib.idle_add(self._btn_disconnect.set_sensitive, False)
        self._proc = None

    def _on_disconnect(self, widget):
        """Termine la session SPICE.

        Args:
            widget (Gtk.Button): Bouton declencheur.
        """
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        self._set_status(_("Disconnect"))
        self._btn_connect.set_sensitive(True)
        self._btn_disconnect.set_sensitive(False)

    def _set_status(self, text):
        """Met a jour le label de statut.

        Args:
            text (str): Nouveau statut.
        """
        app_logger.debug(f"SPICE: status = {text}")
        self._lbl_status.set_text(text)

    def connect_spice(self):
        """Lance la connexion SPICE automatiquement (appele depuis addTab)."""
        self._on_connect(None)


class SerialTab(Gtk.Box):
    """Onglet de connexion série embarquant un terminal VTE.

    Lance picocom (ou minicom / screen) dans le widget VTE intégré.
    Supporte des templates constructeur (Cisco, HP Comware, Aruba…).

    Paramètres série complets exposés dans l'UI :
        - Port série (/dev/ttyUSBx, /dev/ttySx…)
        - Débit (baud rate) : 300 → 921600
        - Bits de données : 5 / 6 / 7 / 8
        - Parité : Aucune / Paire / Impaire
        - Bits de stop : 1 / 2
        - Contrôle de flux : Aucun / XON-XOFF / RTS-CTS / DSR-DTR

    Args:
        host (Host): Hôte avec protocol='serial'.
            - host.host         : chemin du port
            - host.port         : débit en bauds
            - host.extra_params : options libres supplémentaires
            - host.type         : clé template
    """

    # Correspondances valeur interne → label UI
    _FLOW_LABELS = [
        ("n", "None"),
        ("x", "XON/XOFF (soft)"),
        ("h", "RTS/CTS (hard)"),
        ("d", "DSR/DTR"),
    ]
    _PARITY_LABELS = [
        ("n", "Aucune (N)"),
        ("e", "Paire (E)"),
        ("o", "Impaire (O)"),
    ]
    _DATABITS_VALUES = ("5", "6", "7", "8")
    _STOPBITS_VALUES = ("1", "2")

    def __init__(self, host):
        """Initialise le widget SerialTab."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.host = host

        # ── ligne 1 : appareil + débit + template ───────────────────────────
        hb1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hb1.set_margin_start(6)
        hb1.set_margin_end(6)
        hb1.set_margin_top(4)

        # Port série
        lbl_dev = Gtk.Label(label=_("Serial port:"))
        lbl_dev.set_xalign(1.0)
        self._entry_dev = Gtk.Entry()
        self._entry_dev.set_text(getattr(host, "host", "/dev/ttyUSB0") or "/dev/ttyUSB0")
        self._entry_dev.set_tooltip_text(_("Ex : /dev/ttyUSB0, /dev/ttyS0, /dev/ttyACM0"))
        self._entry_dev.set_hexpand(True)

        # Débit (baud rate)
        lbl_baud = Gtk.Label(label=_("Baud rate:"))
        lbl_baud.set_xalign(1.0)
        self._cmb_baud = Gtk.ComboBoxText()
        for b in (
            "300",
            "1200",
            "2400",
            "4800",
            "9600",
            "19200",
            "38400",
            "57600",
            "115200",
            "230400",
            "460800",
            "921600",
        ):
            self._cmb_baud.append_text(b)
        self._cmb_baud.set_tooltip_text(_("Transmission speed in baud"))
        # serial_baud prioritaire sur port (héritage historique)
        baud = str(getattr(host, "serial_baud", "") or getattr(host, "port", "9600") or "9600")
        self._cmb_select(self._cmb_baud, baud, 4)  # défaut 9600 (idx 4)

        # Template constructeur
        lbl_tpl = Gtk.Label(label=_("Template:"))
        lbl_tpl.set_xalign(1.0)
        self._cmb_tpl = Gtk.ComboBoxText()
        for tpl_name in _SERIAL_TEMPLATES:
            self._cmb_tpl.append_text(tpl_name)
        self._cmb_tpl.set_tooltip_text(_("Load vendor-recommended serial settings"))
        tpl_saved = getattr(host, "type", "") or ""
        tpl_list = list(_SERIAL_TEMPLATES.keys())
        tpl_idx = tpl_list.index(tpl_saved) if tpl_saved in tpl_list else 10
        self._cmb_tpl.set_active(tpl_idx)
        self._cmb_tpl.connect("changed", self._on_template_changed)

        for w in (
            lbl_dev,
            self._entry_dev,
            lbl_baud,
            self._cmb_baud,
            lbl_tpl,
            self._cmb_tpl,
        ):
            hb1.pack_start(w, False, False, 0)

        # ── ligne 2 : paramètres série (databits, parity, stopbits, flow) ──
        hb2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hb2.set_margin_start(6)
        hb2.set_margin_end(6)

        # Bits de données
        lbl_data = Gtk.Label(label=_("Data bits:"))
        lbl_data.set_xalign(1.0)
        self._cmb_databits = Gtk.ComboBoxText()
        for d in self._DATABITS_VALUES:
            self._cmb_databits.append_text(d)
        self._cmb_databits.set_tooltip_text(_("Number of data bits per byte (8 = standard)"))
        _db = str(getattr(host, "serial_databits", "8") or "8")
        _db_idx = list(self._DATABITS_VALUES).index(_db) if _db in self._DATABITS_VALUES else 3
        self._cmb_databits.set_active(_db_idx)

        # Parité
        lbl_par = Gtk.Label(label=_("Parity:"))
        lbl_par.set_xalign(1.0)
        self._cmb_parity = Gtk.ComboBoxText()
        for _code, _label in self._PARITY_LABELS:
            self._cmb_parity.append_text(_label)
        self._cmb_parity.set_tooltip_text(_("Parity bit: None (N) = standard, Even (E), Odd (O)"))
        _par = str(getattr(host, "serial_parity", "n") or "n")
        _par_codes = [c for c, _ in self._PARITY_LABELS]
        self._cmb_parity.set_active(_par_codes.index(_par) if _par in _par_codes else 0)

        # Bits de stop
        lbl_stop = Gtk.Label(label=_("Stop bits:"))
        lbl_stop.set_xalign(1.0)
        self._cmb_stopbits = Gtk.ComboBoxText()
        for s in self._STOPBITS_VALUES:
            self._cmb_stopbits.append_text(s)
        self._cmb_stopbits.set_tooltip_text(
            _("Stop bits: 1 = standard, 2 = RS-485 / legacy hardware")
        )
        _sb = str(getattr(host, "serial_stopbits", "1") or "1")
        _sb_idx = list(self._STOPBITS_VALUES).index(_sb) if _sb in self._STOPBITS_VALUES else 0
        self._cmb_stopbits.set_active(_sb_idx)

        # Contrôle de flux
        lbl_flow = Gtk.Label(label=_("Flow control:"))
        lbl_flow.set_xalign(1.0)
        self._cmb_flow = Gtk.ComboBoxText()
        for _code, _label in self._FLOW_LABELS:
            self._cmb_flow.append_text(_label)
        self._cmb_flow.set_tooltip_text(
            _(
                "Flow control:\n"
                "  None = standard console\n"
                "  XON/XOFF = software (Ctrl-Q/Ctrl-S)\n"
                "  RTS/CTS = hardware (full cable)\n"
                "  DSR/DTR = legacy hardware"
            )
        )
        _fl = str(getattr(host, "serial_flow", "n") or "n")
        _fl_codes = [c for c, _ in self._FLOW_LABELS]
        self._cmb_flow.set_active(_fl_codes.index(_fl) if _fl in _fl_codes else 0)

        # Options libres
        lbl_opts = Gtk.Label(label=_("xfreerdp options:"))
        lbl_opts.set_xalign(1.0)
        self._entry_opts = Gtk.Entry()
        self._entry_opts.set_text(getattr(host, "extra_params", "") or "")
        self._entry_opts.set_tooltip_text(
            _(
                "Additional raw options passed to the binary\n"
                "Ex: --logfile /tmp/serial.log  (picocom)\n"
                "     -o -x  (minicom)"
            )
        )

        # Boutons
        self._btn_connect = Gtk.Button(label=_("Connect"))
        self._btn_connect.connect("clicked", self._on_connect)
        self._btn_disconnect = Gtk.Button(label=_("Disconnect"))
        self._btn_disconnect.set_sensitive(False)
        self._btn_disconnect.connect("clicked", self._on_disconnect)

        for w in (
            lbl_data,
            self._cmb_databits,
            lbl_par,
            self._cmb_parity,
            lbl_stop,
            self._cmb_stopbits,
            lbl_flow,
            self._cmb_flow,
            lbl_opts,
            self._entry_opts,
            self._btn_connect,
            self._btn_disconnect,
        ):
            hb2.pack_start(w, False, False, 0)

        # ── infos + terminal ────────────────────────────────────────────────
        lbl_bin = Gtk.Label()
        lbl_bin.set_markup(f"<small><i>Detected binary: {SERIAL_BIN}</i></small>")
        lbl_bin.set_xalign(0.0)
        lbl_bin.set_margin_start(6)

        self._lbl_status = Gtk.Label(label=_("Disconnect"))
        self._lbl_status.set_xalign(0.0)
        self._lbl_status.set_margin_start(6)

        self._terminal = Vte.Terminal()
        self._terminal.set_scrollback_lines(5000)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(self._terminal)
        sw.set_vexpand(True)
        sw.set_hexpand(True)

        self.pack_start(hb1, False, False, 0)
        self.pack_start(hb2, False, False, 0)
        self.pack_start(lbl_bin, False, False, 0)
        self.pack_start(self._lbl_status, False, False, 0)
        self.pack_start(sw, True, True, 0)
        self.show_all()

        # Appliquer le template après construction de l'UI
        if tpl_saved in _SERIAL_TEMPLATES:
            self._apply_template(tpl_saved)

    # ── helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _cmb_select(cmb, value, default_idx=0):
        """Sélectionne l'entrée dont le texte == value, sinon default_idx."""
        model = cmb.get_model()
        it = model.get_iter_first()
        while it is not None:
            if model[it][0] == value:
                cmb.set_active_iter(it)
                return
            it = model.iter_next(it)
        cmb.set_active(default_idx)

    def _flow_code(self):
        idx = self._cmb_flow.get_active()
        return self._FLOW_LABELS[idx][0] if 0 <= idx < len(self._FLOW_LABELS) else "n"

    def _parity_code(self):
        idx = self._cmb_parity.get_active()
        return self._PARITY_LABELS[idx][0] if 0 <= idx < len(self._PARITY_LABELS) else "n"

    def _databits(self):
        return self._cmb_databits.get_active_text() or "8"

    def _stopbits(self):
        return self._cmb_stopbits.get_active_text() or "1"

    # ── template ────────────────────────────────────────────────────────────

    def _apply_template(self, name):
        """Applique les paramètres d'un template aux combos de l'UI."""
        if name not in _SERIAL_TEMPLATES:
            return
        baud, flow, parity, databits, stopbits = _SERIAL_TEMPLATES[name]
        self._cmb_select(self._cmb_baud, baud, 4)
        # flow
        flow_codes = [c for c, _ in self._FLOW_LABELS]
        self._cmb_flow.set_active(flow_codes.index(flow) if flow in flow_codes else 0)
        # parity
        parity_codes = [c for c, _ in self._PARITY_LABELS]
        self._cmb_parity.set_active(parity_codes.index(parity) if parity in parity_codes else 0)
        # databits / stopbits
        self._cmb_select(self._cmb_databits, databits, 3)
        self._cmb_select(self._cmb_stopbits, stopbits, 0)
        self.host.type = name

    def _on_template_changed(self, cmb):
        """Applique le template sélectionné sur tous les combos."""
        name = cmb.get_active_text()
        self._apply_template(name)

    # ── construction de la commande ─────────────────────────────────────────

    def _build_cmd(self):
        """Construit la liste d'arguments pour le sous-processus série.

        Les paramètres (débit, databits, parity, stopbits, flow) sont lus
        directement depuis les combos dédiés, pas depuis une chaîne brute.

        Returns:
            list[str]: Commande prête pour vte_run().
        """
        device = self._entry_dev.get_text().strip() or "/dev/ttyUSB0"
        baud = self._cmb_baud.get_active_text() or "9600"
        flow = self._flow_code()
        parity = self._parity_code()
        databits = self._databits()
        stopbits = self._stopbits()
        extra = self._entry_opts.get_text().strip()

        # Résolution du binaire : serial_tool prioritaire sur la détection globale
        _TOOL_BINS = {
            "picocom": shutil.which("picocom"),
            "minicom": shutil.which("minicom"),
            "screen": shutil.which("screen"),
        }
        tool_id = (getattr(self.host, "serial_tool", "") or "").strip()
        serial_bin = (_TOOL_BINS.get(tool_id) or SERIAL_BIN) if tool_id else SERIAL_BIN
        bin_name = os.path.basename(serial_bin)

        if bin_name == "picocom":
            cmd = [
                serial_bin,
                "--baud",
                baud,
                "--flow",
                flow,
                "--parity",
                parity,
                "--databits",
                databits,
                "--stopbits",
                stopbits,
            ]
            if extra:
                cmd += shlex.split(extra)
            cmd.append(device)
        elif bin_name == "minicom":
            # minicom : -b baud  -D device  --databits  --stopbits
            # flow via --8bit / -f (xon) / --rtscts (rts/cts)
            cmd = [
                serial_bin,
                "-b",
                baud,
                "-D",
                device,
                "--databits",
                databits,
                "--stopbits",
                stopbits,
            ]
            if flow == "x":
                cmd += ["-f", "on"]
            elif flow == "h":
                cmd += ["--rtscts"]
            if extra:
                cmd += shlex.split(extra)
        else:  # screen : device baud [databits[parity[stopbits]]]
            # screen accepte 8n1, 7e1, etc. comme troisième argument
            parity_map = {"n": "n", "e": "e", "o": "o"}
            combo = f"{databits}{parity_map.get(parity, 'n')}{stopbits}"
            cmd = [serial_bin, device, baud, combo]
            if extra:
                cmd += shlex.split(extra)
        app_logger.debug(f"Serial: command = {cmd}")
        return cmd

    # ── connexion / déconnexion ──────────────────────────────────────────────

    def _on_connect(self, widget):
        """Lance la session série dans le terminal VTE."""
        self.host.extra_params = self._entry_opts.get_text().strip()
        # Persister dans les attributs structurés (serial_baud, etc.)
        baud = self._cmb_baud.get_active_text() or "9600"
        self.host.serial_baud = baud
        self.host.serial_databits = self._databits()
        self.host.serial_parity = self._parity_code()
        self.host.serial_stopbits = self._stopbits()
        self.host.serial_flow = self._flow_code()
        # Compatibilité : port = baud pour les anciens configs
        self.host.port = baud
        self.host.host = self._entry_dev.get_text().strip()
        cmd = self._build_cmd()
        if not cmd:
            return
        self._lbl_status.set_text(_("Connecting…"))
        self._btn_connect.set_sensitive(False)
        self._btn_disconnect.set_sensitive(True)
        vte_run(self._terminal, cmd[0], cmd[1:])

    def _on_disconnect(self, widget):
        """Envoie SIGTERM au processus fils du VTE."""
        try:
            pid = self._terminal.get_pty().get_fd()
            if pid and pid > 0:
                import signal as _signal

                os.kill(pid, _signal.SIGTERM)
        except Exception:
            pass
        self._lbl_status.set_text(_("Disconnect"))
        self._btn_connect.set_sensitive(True)
        self._btn_disconnect.set_sensitive(False)

    def connect_serial(self):
        """Démarre la session série automatiquement (appelé depuis addTab)."""
        self._on_connect(None)


def parse_spice_hosts(conf_path: Path) -> list[tuple[str, str]]:
    """Extrait les paires (host, spice_px_node) des entrées SPICE de gcm.conf.

    Args:
        conf_path: Chemin vers le fichier gcm.conf.

    Returns:
        Liste de tuples ``(host_ip, node_name)`` uniques, ordre de déclaration préservé.

    Raises:
        FileNotFoundError: Si ``conf_path`` n'existe pas.
    """
    app_logger.debug("parse_spice_hosts | enter | conf_path={conf_path}", conf_path=conf_path)

    if not conf_path.exists():
        raise FileNotFoundError(f"gcm.conf introuvable : {conf_path}")

    raw = conf_path.read_text(encoding="utf-8")
    parser = configparser.RawConfigParser()
    parser.read_string(raw)

    entries: list[tuple[str, str]] = []

    for section in parser.sections():
        if not section.startswith("host "):
            continue

        proto = parser.get(section, "protocol", fallback="")
        host = parser.get(section, "host", fallback="").strip()
        node = parser.get(section, "spice_px_node", fallback="").strip()

        if proto != "spice":
            app_logger.trace(
                "parse_spice_hosts | skip | section={section} proto={proto}",
                section=section,
                proto=proto,
            )
            continue

        if not host or not node:
            app_logger.warning(
                "parse_spice_hosts | section={section} ignorée — host ou spice_px_node vide",
                section=section,
            )
            continue

        app_logger.debug(
            "parse_spice_hosts | found | section={section} host={host} node={node}",
            section=section,
            host=host,
            node=node,
        )
        entries.append((host, node))

    # Dédoublonnage ordre-stable
    seen: set[tuple[str, str]] = set()
    unique: list[tuple[str, str]] = []
    for pair in entries:
        if pair not in seen:
            seen.add(pair)
            unique.append(pair)

    app_logger.debug(
        "parse_spice_hosts | exit | total={total} unique={unique}",
        total=len(entries),
        unique=len(unique),
    )
    return unique


# ---------------------------------------------------------------------------
# Gestion de /etc/hosts
# ---------------------------------------------------------------------------


def _existing_nodes(hosts_text: str) -> set[str]:
    """Retourne l'ensemble des noms d'hôtes déjà présents dans /etc/hosts.

    Args:
        hosts_text: Contenu brut de /etc/hosts.

    Returns:
        Ensemble de noms (colonnes 2+) en minuscules.
    """
    names: set[str] = set()
    for line in hosts_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        for name in parts[1:]:
            names.add(name.lower())
    return names


def _ask_password_dialog(prompt: str = "Mot de passe sudo requis :") -> str | None:
    """Affiche une boîte de dialogue GTK3 demandant le mot de passe.

    Args:
        prompt: Message affiché au-dessus du champ de saisie.

    Returns:
        Le mot de passe saisi, ou None si annulé.
    """
    dialog = Gtk.Dialog(
        title="Authentification requise",
        flags=Gtk.DialogFlags.MODAL,
    )
    dialog.add_buttons(
        Gtk.STOCK_CANCEL,
        Gtk.ResponseType.CANCEL,
        Gtk.STOCK_OK,
        Gtk.ResponseType.OK,
    )
    dialog.set_default_response(Gtk.ResponseType.OK)
    dialog.set_border_width(12)

    content = dialog.get_content_area()
    content.set_spacing(8)

    label = Gtk.Label(label=prompt)
    label.set_halign(Gtk.Align.START)
    content.add(label)

    entry = Gtk.Entry()
    entry.set_visibility(False)
    entry.set_invisible_char("●")
    entry.set_activates_default(True)
    content.add(entry)

    dialog.show_all()
    response = dialog.run()
    password = entry.get_text() if response == Gtk.ResponseType.OK else None
    dialog.destroy()
    return password


class HostsUpdater:
    """Mise à jour de /etc/hosts pour les nœuds SPICE, avec élévation GTK3.

    Si le processus est déjà root, l'écriture est directe.
    Sinon, un dialog GTK3 demande le mot de passe et l'écriture
    est déléguée à ``tee`` via ``sudo -S``, sans re-lancer l'appli.
    """

    HOSTS_FILE = "/etc/hosts"
    MARKER = "# gcm-spice"
    MAX_ATTEMPTS = 3

    def _existing_nodes(self, hosts_text: str) -> set[str]:
        """Retourne les noms d'hôtes déjà présents dans hosts_text.

        Args:
            hosts_text: Contenu brut de /etc/hosts.

        Returns:
            Ensemble de noms en minuscules.
        """
        names: set[str] = set()
        for line in hosts_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split()
            for name in parts[1:]:
                names.add(name.lower())
        return names

    def _build_lines(self, pairs: list[tuple[str, str]], existing: set[str]) -> list[str]:
        """Calcule les lignes à ajouter.

        Args:
            pairs: Liste de ``(host_ip, node_name)``.
            existing: Noms déjà présents dans /etc/hosts.

        Returns:
            Lignes prêtes à être ajoutées (sans newline finale).
        """
        lines: list[str] = []
        for host_ip, node_name in pairs:
            if node_name.lower() in existing:
                app_logger.debug("_build_lines | already present | node={node}", node=node_name)
                continue
            lines.append(f"{host_ip:<20}{node_name}  {self.MARKER}")
            app_logger.info(
                "_build_lines | queued | ip={ip} node={node}", ip=host_ip, node=node_name
            )
        return lines

    def _write_direct(self, new_text: str) -> None:
        """Écrit new_text dans /etc/hosts directement (déjà root).

        Args:
            new_text: Contenu complet du fichier.
        """
        with open(self.HOSTS_FILE, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        app_logger.info("_write_direct | écriture directe OK")

    def _write_via_sudo(self, new_text: str) -> None:
        """Écrit new_text dans /etc/hosts via sudo -S tee, avec dialog GTK3.

        Demande le mot de passe jusqu'à MAX_ATTEMPTS fois.

        Args:
            new_text: Contenu complet du fichier.

        Raises:
            PermissionError: Si l'authentification échoue après MAX_ATTEMPTS tentatives
                             ou si l'utilisateur annule.
        """
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            prompt = (
                "Mot de passe sudo requis pour modifier /etc/hosts :"
                if attempt == 1
                else f"Mot de passe incorrect — tentative {attempt}/{self.MAX_ATTEMPTS} :"
            )
            password = _ask_password_dialog(prompt)

            if password is None:
                raise PermissionError("Authentification annulée par l'utilisateur")

            # Vérifie le mot de passe
            check = subprocess.run(
                ["sudo", "-S", "-v"],
                input=password + "\n",
                capture_output=True,
                text=True,
            )
            app_logger.debug(
                "_write_via_sudo | sudo -v | attempt={attempt} rc={rc}",
                attempt=attempt,
                rc=check.returncode,
            )
            if check.returncode != 0:
                continue

            # Mot de passe valide → écriture via sudo tee (une seule opération)
            result = subprocess.run(
                ["sudo", "-S", "tee", self.HOSTS_FILE],
                input=password + "\n" + new_text,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise PermissionError(f"sudo tee a échoué : {result.stderr.strip()}")

            app_logger.info("_write_via_sudo | écriture via sudo tee OK")
            return

        raise PermissionError(f"Échec d'authentification après {self.MAX_ATTEMPTS} tentatives")

    def update(self, pairs: list[tuple[str, str]]) -> int:
        """Point d'entrée public : ajoute les entrées SPICE manquantes dans /etc/hosts.

        Args:
            pairs: Liste de ``(host_ip, spice_px_node)`` issues de gcm.conf.

        Returns:
            Nombre de lignes ajoutées (0 si déjà à jour).

        Raises:
            PermissionError: Si l'élévation est refusée ou annulée.
        """
        app_logger.debug("HostsUpdater.update | enter | pairs={pairs}", pairs=pairs)

        current_text = open(self.HOSTS_FILE, encoding="utf-8").read()
        existing = self._existing_nodes(current_text)
        lines = self._build_lines(pairs, existing)

        if not lines:
            app_logger.info("HostsUpdater.update | déjà à jour")
            return 0

        separator = "" if current_text.endswith("\n") else "\n"
        new_text = current_text + separator + "\n".join(lines) + "\n"

        if os.geteuid() == 0:
            self._write_direct(new_text)
        else:
            self._write_via_sudo(new_text)

        app_logger.debug("HostsUpdater.update | exit | added={n}", n=len(lines))
        return len(lines)

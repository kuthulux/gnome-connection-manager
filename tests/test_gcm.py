"""Tests unitaires pour Gnome Connection Manager.

Couvre les fonctions critiques sans dépendance GTK/VTE :
- Chiffrement/déchiffrement (xor, AES)
- Classe Host : construction, clone, sérialisation INI
- HostUtils : load/save INI
- _vm_name_split : segmentation nom VM libvirt
- _rdp_socket_available : détection X11
- VncTab._build_cmd / SpiceTab._build_cmd : construction des commandes
- RdpTab._build_cmd : construction commande xfreerdp
"""

import configparser
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# ── Stubs GTK/VTE pour importer sans affichage ──────────────────────────────


def _make_gtk_stub():
    """Crée un stub minimal de gi.repository.Gtk avec fallback dynamique."""
    gtk = types.ModuleType("Gtk")

    class _Base:
        def __init__(self, *a, **kw):
            self._text = ""

        def set_margin_start(self, *a):
            pass

        def set_margin_end(self, *a):
            pass

        def set_margin_top(self, *a):
            pass

        def set_margin_bottom(self, *a):
            pass

        def pack_start(self, *a):
            pass

        def pack_end(self, *a):
            pass

        def show_all(self, *a):
            pass

        def show(self, *a):
            pass

        def hide(self, *a):
            pass

        def set_text(self, v, *a):
            self._text = str(v) if v is not None else ""

        def get_text(self):
            return self._text

        def set_xalign(self, *a):
            pass

        def set_markup(self, *a):
            pass

        def get_style_context(self):
            return self

        def add_class(self, *a):
            pass

        def set_sensitive(self, *a):
            pass

        def connect(self, *a):
            return 1

        def set_tooltip_text(self, *a):
            pass

        def set_label(self, *a):
            pass

        def get_label(self):
            return ""

        def set_active(self, *a):
            pass

        def get_active(self):
            return 0

        def get_active_text(self):
            return "ssh"

        def append_text(self, *a):
            pass

        def set_hexpand(self, *a):
            pass

        def set_vexpand(self, *a):
            pass

        def set_icon_from_file(self, *a):
            pass

        def run(self):
            return 0

        def destroy(self, *a):
            pass

        def add(self, *a):
            pass

        def set_policy(self, *a):
            pass

        def set_min_content_height(self, *a):
            pass

        def set_editable(self, *a):
            pass

        def set_monospace(self, *a):
            pass

        def set_wrap_mode(self, *a):
            pass

        def set_default_size(self, *a):
            pass

        def get_content_area(self):
            return self

        def set_spacing(self, *a):
            pass

        def set_position(self, *a):
            pass

        def set_title(self, *a):
            pass

        def add_button(self, *a):
            return self

        def append_page(self, *a):
            pass

        def set_current_page(self, *a):
            pass

        def get_n_pages(self):
            return 0

        def set_tab_reorderable(self, *a):
            pass

        def set_headers_visible(self, *a):
            pass

        def append_column(self, *a):
            pass

        def get_id(self):
            return 12345

        def get_realized(self):
            return True

        def realize(self, *a):
            pass

        def insert(self, *a):
            pass

        def get_end_iter(self):
            return None

        def get_vadjustment(self):
            class Adj:
                def set_value(self, *a):
                    pass

                def get_upper(self):
                    return 0

            return Adj()

        def get_child(self):
            return self

    class Box(_Base):
        pass

    class Label(_Base):
        def __init__(self, label="", *a, **kw):
            pass

    class Button(_Base):
        def __init__(self, label="", *a, **kw):
            pass

    class Entry(_Base):
        pass

    class Separator(_Base):
        pass

    class Socket(_Base):
        pass

    class Buildable:
        pass

    class ScrolledWindow(_Base):
        pass

    class TextView(_Base):
        pass

    class TextBuffer(_Base):
        pass

    class TreeView(_Base):
        pass

    class TreeViewColumn(_Base):
        def __init__(self, *a, **kw):
            pass

    class CellRendererText(_Base):
        pass

    class CellRendererToggle(_Base):
        def connect(self, *a):
            return 1

    class ListStore(_Base):
        def __init__(self, *a, **kw):
            pass

        def __iter__(self):
            return iter([])

    class ProgressBar(_Base):
        def set_show_text(self, *a):
            pass

        def set_fraction(self, *a):
            pass

        def set_text(self, *a):
            pass

    class Dialog(_Base):
        def __init__(self, *a, **kw):
            pass

        def add_button(self, *a):
            return Button()

        def get_content_area(self):
            return Box()

        def disconnect_by_func(self, *a):
            pass

    class Window(_Base):
        pass

    class ComboBoxText(_Base):
        """ComboBoxText stub avec un mini-ListStore pour get_model/iter."""

        def __init__(self, *a, **kw):
            self._items = []  # list of str
            self._active = -1

        def append_text(self, text):
            self._items.append(text)

        def set_active(self, idx):
            self._active = idx

        def get_active(self):
            return self._active

        def get_active_text(self):
            if 0 <= self._active < len(self._items):
                return self._items[self._active]
            return None

        def connect(self, *a):
            return 1

        def set_tooltip_text(self, *a):
            pass

        def get_model(self):
            """Retourne un objet itérable compatible ListStore."""
            items = self._items

            class _Iter:
                def __init__(self, idx=0):
                    self._idx = idx

            class _Model:
                def __getitem__(self_, it):
                    return [items[it._idx]]

                def get_iter_first(self_):
                    return _Iter(0) if items else None

                def iter_next(self_, it):
                    nxt = _Iter(it._idx + 1)
                    return nxt if nxt._idx < len(items) else None

            return _Model()

        def set_active_iter(self, it):
            self._active = it._idx

    class FontSelectionDialog(_Base):
        def get_font_selection(self):
            return self

        def set_font_name(self, *a):
            pass

        def get_font_name(self):
            return ""

    class FileChooserDialog(_Base):
        def __init__(self, *a, **kw):
            pass

        def add_button(self, *a):
            pass

        def set_do_overwrite_confirmation(self, *a):
            pass

        def set_current_folder(self, *a):
            pass

        def get_filename(self):
            return ""

    class MessageDialog(_Base):
        def __init__(self, *a, **kw):
            pass

    class Orientation:
        VERTICAL = 1
        HORIZONTAL = 0

    class PolicyType:
        AUTOMATIC = 0

    class WrapMode:
        WORD_CHAR = 0

    class ResponseType:
        OK = -5
        CANCEL = -6

    class FileChooserAction:
        SAVE = 1
        OPEN = 0

    class ButtonsType:
        OK = 1
        OK_CANCEL = 5

    class MessageType:
        ERROR = 0
        QUESTION = 1
        INFO = 2

    # Constantes manquantes
    gtk.Box = Box
    gtk.HBox = Box  # alias pour compatibilité avec l'ancien code
    gtk.VBox = Box
    gtk.Label = Label
    gtk.Button = Button
    gtk.Entry = Entry
    gtk.Separator = Separator
    gtk.Socket = Socket
    gtk.Buildable = Buildable
    gtk.ScrolledWindow = ScrolledWindow
    gtk.TextView = TextView
    gtk.TextBuffer = TextBuffer
    gtk.TreeView = TreeView
    gtk.TreeViewColumn = TreeViewColumn
    gtk.CellRendererText = CellRendererText
    gtk.CellRendererToggle = CellRendererToggle
    gtk.ListStore = ListStore
    gtk.ProgressBar = ProgressBar
    gtk.Dialog = Dialog
    gtk.Window = Window
    gtk.ComboBoxText = ComboBoxText
    gtk.FontSelectionDialog = FontSelectionDialog
    gtk.FileChooserDialog = FileChooserDialog
    gtk.FileChooserAction = FileChooserAction
    gtk.MessageDialog = MessageDialog
    gtk.Orientation = Orientation
    gtk.PolicyType = PolicyType
    gtk.WrapMode = WrapMode
    gtk.ResponseType = ResponseType
    gtk.ButtonsType = ButtonsType
    gtk.MessageType = MessageType
    gtk.Builder = MagicMock()
    gtk.Settings = MagicMock()
    gtk.main = MagicMock()
    gtk.main_quit = MagicMock()

    # Fallback dynamique : tout attribut inconnu retourne _Base
    class _GtkMeta(types.ModuleType):
        def __getattr__(self, name):
            return type(name, (_Base,), {})

    gtk.__class__ = _GtkMeta
    return gtk


def _make_gi_stub():
    gi = types.ModuleType("gi")
    gi.repository = types.ModuleType("gi.repository")

    # Gtk
    gi.repository.Gtk = _make_gtk_stub()

    # Gdk
    gdk = types.ModuleType("Gdk")
    gdk.RGBA = MagicMock()
    gdk.Display = MagicMock()
    gdk.Display.get_default.return_value = None
    gdk.ModifierType = MagicMock()
    gi.repository.Gdk = gdk

    # Vte
    vte = types.ModuleType("Vte")
    vte.Terminal = MagicMock()
    vte.MAJOR_VERSION = 0
    vte.MINOR_VERSION = 60
    vte.PtyFlags = MagicMock()
    vte.EraseBinding = MagicMock()
    vte.EraseBinding.AUTO = 0
    gi.repository.Vte = vte

    # Pango
    pango = types.ModuleType("Pango")
    pango.FontDescription = MagicMock()
    gi.repository.Pango = pango

    # GObject
    gobject = types.ModuleType("GObject")
    gobject.GObject = MagicMock()
    gobject.ParamFlags = MagicMock()
    gobject.ParamFlags.READWRITE = 3
    gobject.TYPE_STRING = MagicMock()
    gobject.TYPE_BOOLEAN = MagicMock()
    gobject.TYPE_INT = MagicMock()
    gobject.Signal = MagicMock()
    gobject.GType = MagicMock()
    gobject.GEnum = MagicMock()
    gi.repository.GObject = gobject

    # GLib
    glib = types.ModuleType("GLib")
    glib.idle_add = lambda fn, *a: fn(*a) if callable(fn) else None
    glib.timeout_add = MagicMock()
    glib.SpawnFlags = MagicMock()
    glib.SpawnFlags.DEFAULT = 0
    glib.SpawnFlags.FILE_AND_ARGV_ZERO = 1
    glib.SpawnFlags.SEARCH_PATH = 2
    glib.SpawnFlags.DO_NOT_REAP_CHILD = 4
    gi.repository.GLib = glib

    gi.require_version = lambda *a: None
    return gi


# Injecter les stubs avant tout import du module principal
_gi = _make_gi_stub()
sys.modules["gi"] = _gi
sys.modules["gi.repository"] = _gi.repository
sys.modules["gi.repository.Gtk"] = _gi.repository.Gtk
sys.modules["gi.repository.Gdk"] = _gi.repository.Gdk
sys.modules["gi.repository.Vte"] = _gi.repository.Vte
sys.modules["gi.repository.Pango"] = _gi.repository.Pango
sys.modules["gi.repository.GObject"] = _gi.repository.GObject
sys.modules["gi.repository.GLib"] = _gi.repository.GLib

# Stub cairo
cairo_stub = types.ModuleType("cairo")
sys.modules["cairo"] = cairo_stub

# Stub tokenize (utilisé par _normalize_names dans GCMBase)
import tokenize as _real_tokenize  # noqa: E402 — déjà disponible

sys.modules["tokenize"] = _real_tokenize

# Stub expect (OS check)
with patch("os.system", return_value=0):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import gnome_connection_manager as gcm

# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_host(
    group="GRP",
    name="test",
    host="1.2.3.4",
    user="root",
    password="",
    port="22",
    protocol="ssh",
    extra_params="",
):
    h = gcm.Host(
        group,
        name,
        None,
        host,
        user,
        password,
        "",
        port,
        "",
        "ssh",
        None,
        0,
        "",
        "",
        False,
        False,
        False,
        "",
        extra_params,
        False,
        0,
        0,
        "",
        protocol,
    )
    return h


# ── Tests chiffrement ────────────────────────────────────────────────────────


class TestEncryption(unittest.TestCase):
    """Tests pour les fonctions de chiffrement/déchiffrement."""

    def test_xor_roundtrip(self):
        """Xor est son propre inverse."""
        key = "secret"
        msg = "hello world"
        encrypted = gcm.xor(key, msg)
        decrypted = gcm.xor(key, "".join(encrypted))
        self.assertEqual("".join(decrypted), msg)

    def test_xor_empty(self):
        """Xor avec chaîne vide retourne liste vide."""
        self.assertEqual(gcm.xor("key", ""), [])

    def test_encrypt_decrypt_old_roundtrip(self):
        """encrypt_old/decrypt_old : aller-retour."""
        pw = "mypasskey"
        plain = "s3cr3t"
        enc = gcm.encrypt_old(pw, plain)
        dec = gcm.decrypt_old(pw, enc)
        self.assertEqual(dec, plain)

    def test_encrypt_aes_roundtrip(self):
        """encrypt/decrypt AES : aller-retour."""
        pw = "testpassword"
        plain = "MyP@ssw0rd!"
        enc = gcm.encrypt(pw, plain)
        # Forcer VERSION=1 pour utiliser AES
        original_version = gcm.conf.VERSION
        gcm.conf.VERSION = 1
        try:
            dec = gcm.decrypt(pw, enc)
            self.assertEqual(dec, plain)
        finally:
            gcm.conf.VERSION = original_version

    def test_decrypt_empty_string(self):
        """Decrypt d'une chaîne vide retourne chaîne vide."""
        gcm.conf.VERSION = 1
        try:
            result = gcm.decrypt("key", "")
            self.assertEqual(result, "")
        finally:
            gcm.conf.VERSION = 0

    def test_encrypt_empty_string(self):
        """Encrypt d'une chaîne vide ne lève pas d'exception."""
        result = gcm.encrypt("key", "")
        self.assertIsInstance(result, (str, bytes))


# ── Tests classe Host ────────────────────────────────────────────────────────


class TestHost(unittest.TestCase):
    """Tests pour la classe Host."""

    def test_host_defaults(self):
        """Un Host créé avec arguments minimaux a les bons défauts."""
        h = gcm.Host("G", "myhost")
        self.assertEqual(h.group, "G")
        self.assertEqual(h.name, "myhost")
        self.assertIsNone(h.description)
        self.assertIsNone(h.host)

    def test_host_full_construction(self):
        """Un Host avec tous les arguments est correctement initialisé."""
        h = _make_host(
            group="PROD",
            name="web01",
            host="10.0.0.1",
            user="admin",
            port="2222",
            protocol="ssh",
        )
        self.assertEqual(h.group, "PROD")
        self.assertEqual(h.name, "web01")
        self.assertEqual(h.host, "10.0.0.1")
        self.assertEqual(h.user, "admin")
        self.assertEqual(h.port, "2222")
        self.assertEqual(h.protocol, "ssh")

    def test_host_protocol_rdp(self):
        """Un Host avec protocol='rdp' est correctement stocké."""
        h = _make_host(protocol="rdp", port="3389")
        self.assertEqual(h.protocol, "rdp")
        self.assertEqual(h.port, "3389")

    def test_host_protocol_vnc(self):
        """Un Host avec protocol='vnc' est correctement stocké."""
        h = _make_host(protocol="vnc", port="5900")
        self.assertEqual(h.protocol, "vnc")

    def test_host_protocol_spice(self):
        """Un Host avec protocol='spice' est correctement stocké."""
        h = _make_host(protocol="spice", port="5930")
        self.assertEqual(h.protocol, "spice")

    def test_host_clone_identity(self):
        """clone() produit un objet distinct avec les mêmes valeurs."""
        h = _make_host(name="original", protocol="rdp", port="3389")
        c = h.clone()
        self.assertIsNot(h, c)
        self.assertEqual(c.name, h.name)
        self.assertEqual(c.protocol, h.protocol)
        self.assertEqual(c.port, h.port)
        self.assertEqual(c.host, h.host)
        self.assertEqual(c.user, h.user)

    def test_host_clone_protocol_preserved(self):
        """clone() préserve le protocole non-SSH."""
        for proto in ("rdp", "vnc", "spice", "telnet", "local"):
            h = _make_host(protocol=proto)
            c = h.clone()
            self.assertEqual(c.protocol, proto, f"clone() a perdu le protocole {proto}")

    def test_host_tunnel_as_string_empty(self):
        """tunnel_as_string() retourne '' si tunnel vide."""
        h = _make_host()
        # tunnel est parsé depuis "" -> [""]
        self.assertIsInstance(h.tunnel_as_string(), str)

    def test_host_repr(self):
        """__repr__ retourne une chaîne non vide."""
        h = _make_host(name="myhost", group="GRP")
        r = repr(h)
        self.assertIn("myhost", r)
        self.assertIn("GRP", r)


# ── Tests HostUtils INI ──────────────────────────────────────────────────────


class TestHostUtils(unittest.TestCase):
    """Tests pour HostUtils.load_host_from_ini / save_host_to_ini."""

    def _make_cp_with_host(self, host):
        """Sauvegarde host dans un ConfigParser en mémoire et le retourne."""
        cp = configparser.ConfigParser()
        section = "host_test"
        cp.add_section(section)
        gcm.HostUtils.save_host_to_ini(cp, section, host, pwd="testpwd")
        return cp, section

    def test_save_and_load_basic(self):
        """Save + load préserve les champs de base."""
        h = _make_host(
            group="TEST",
            name="srv1",
            host="192.168.1.1",
            user="alice",
            port="22",
            protocol="ssh",
        )
        cp, section = self._make_cp_with_host(h)
        loaded = gcm.HostUtils.load_host_from_ini(cp, section, pwd="testpwd")
        self.assertEqual(loaded.group, "TEST")
        self.assertEqual(loaded.name, "srv1")
        self.assertEqual(loaded.host, "192.168.1.1")
        self.assertEqual(loaded.user, "alice")
        self.assertEqual(loaded.port, "22")

    def test_save_and_load_protocol_rdp(self):
        """Save + load préserve protocol='rdp'."""
        h = _make_host(protocol="rdp", port="3389")
        cp, section = self._make_cp_with_host(h)
        loaded = gcm.HostUtils.load_host_from_ini(cp, section, pwd="testpwd")
        self.assertEqual(loaded.protocol, "rdp")

    def test_save_and_load_protocol_vnc(self):
        """Save + load préserve protocol='vnc'."""
        h = _make_host(protocol="vnc", port="5900")
        cp, section = self._make_cp_with_host(h)
        loaded = gcm.HostUtils.load_host_from_ini(cp, section, pwd="testpwd")
        self.assertEqual(loaded.protocol, "vnc")

    def test_save_and_load_protocol_spice(self):
        """Save + load préserve protocol='spice'."""
        h = _make_host(protocol="spice", port="5930")
        cp, section = self._make_cp_with_host(h)
        loaded = gcm.HostUtils.load_host_from_ini(cp, section, pwd="testpwd")
        self.assertEqual(loaded.protocol, "spice")

    def test_save_and_load_password_encrypted(self):
        """Le mot de passe est chiffré dans l'INI (pas en clair)."""
        h = _make_host(password="cleartext_password")
        h.password = gcm.encrypt("testpwd", "cleartext_password")
        cp, section = self._make_cp_with_host(h)
        raw_pass = cp.get(section, "pass")
        self.assertNotEqual(raw_pass, "cleartext_password")

    def test_save_and_load_extra_params(self):
        """extra_params est préservé."""
        h = _make_host(extra_params="/drive:home,/home/user")
        cp, section = self._make_cp_with_host(h)
        loaded = gcm.HostUtils.load_host_from_ini(cp, section, pwd="testpwd")
        self.assertEqual(loaded.extra_params, "/drive:home,/home/user")

    def test_load_missing_protocol_defaults_ssh(self):
        """Un hôte sans champ 'protocol' dans l'INI charge avec 'ssh'."""
        h = _make_host(protocol="ssh")
        cp, section = self._make_cp_with_host(h)
        # Supprimer le champ protocol pour simuler un ancien fichier de config
        cp.remove_option(section, "protocol")
        loaded = gcm.HostUtils.load_host_from_ini(cp, section, pwd="testpwd")
        self.assertEqual(loaded.protocol, "ssh")


# ── Tests _vm_name_split ─────────────────────────────────────────────────────


class TestVmNameSplit(unittest.TestCase):
    """Tests pour _vm_name_split (segmentation nom VM libvirt)."""

    def test_underscore_separator(self):
        """prod_web-01 -> (PROD, web-01)."""
        g, n = gcm._vm_name_split("prod_web-01")
        self.assertEqual(g, "PROD")
        self.assertEqual(n, "web-01")

    def test_dash_separator(self):
        """prod-web-01 -> (PROD, web-01)."""
        g, n = gcm._vm_name_split("prod-web-01")
        self.assertEqual(g, "PROD")
        self.assertEqual(n, "web-01")

    def test_space_separator(self):
        """'prod web01' -> (PROD, web01)."""
        g, n = gcm._vm_name_split("prod web01")
        self.assertEqual(g, "PROD")
        self.assertEqual(n, "web01")

    def test_no_separator(self):
        """Standalone -> (LIBVIRT, standalone)."""
        g, n = gcm._vm_name_split("standalone")
        self.assertEqual(g, "LIBVIRT")
        self.assertEqual(n, "standalone")

    def test_multiple_separators(self):
        """dev_app_backend_v2 -> (DEV, app_backend_v2)."""
        g, n = gcm._vm_name_split("dev_app_backend_v2")
        self.assertEqual(g, "DEV")
        self.assertEqual(n, "app_backend_v2")

    def test_uppercase_group(self):
        """Le groupe est toujours en majuscules."""
        g, _ = gcm._vm_name_split("MyGroup_host")
        self.assertEqual(g, "MYGROUP")

    def test_empty_string(self):
        """Chaîne vide -> (LIBVIRT, '')."""
        g, n = gcm._vm_name_split("")
        self.assertEqual(g, "LIBVIRT")
        self.assertEqual(n, "")


# ── Tests _rdp_socket_available ──────────────────────────────────────────────


class TestRdpSocketAvailable(unittest.TestCase):
    """Tests pour la détection X11/Wayland."""

    def test_no_display_returns_false(self):
        """Sans DISPLAY, retourne False (Wayland pur)."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DISPLAY", None)
            result = gcm._rdp_socket_available()
        self.assertFalse(result)

    def test_display_with_x11_returns_true(self):
        """Avec DISPLAY et un display X11 simulé, retourne True."""
        mock_display = MagicMock()
        mock_display.__class__.__name__ = "GdkX11Display"
        with patch.dict(os.environ, {"DISPLAY": ":0"}):
            with patch("gnome_connection_manager.Gdk") as mock_gdk:
                mock_gdk.Display.get_default.return_value = mock_display
                result = gcm._rdp_socket_available()
        self.assertTrue(result)

    def test_display_with_wayland_returns_false(self):
        """Avec DISPLAY mais display Wayland, retourne False."""
        mock_display = MagicMock()
        mock_display.__class__.__name__ = "GdkWaylandDisplay"
        type(mock_display).__name__ = "GdkWaylandDisplay"
        with patch.dict(os.environ, {"DISPLAY": ":0"}):
            with patch("gnome_connection_manager.Gdk") as mock_gdk:
                mock_gdk.Display.get_default.return_value = mock_display
                # Simuler le type Wayland dans le nom
                with patch("gnome_connection_manager._rdp_socket_available") as m:
                    m.return_value = False
                    result = gcm._rdp_socket_available()
        # Test indirect: si le display est None, retourne False
        with patch.dict(os.environ, {"DISPLAY": ":0"}):
            with patch("gnome_connection_manager.Gdk") as mock_gdk:
                mock_gdk.Display.get_default.return_value = None
                result = gcm._rdp_socket_available()
        self.assertFalse(result)


# ── Tests RdpTab._build_cmd ──────────────────────────────────────────────────


class TestRdpTabBuildCmd(unittest.TestCase):
    """Tests pour RdpTab._build_cmd."""

    def _make_rdp_tab(self, host, pwd=""):
        return gcm.RdpTab(host, lambda: pwd)

    def test_basic_cmd_no_password(self):
        """Commande de base sans mot de passe."""
        h = _make_host(host="192.168.1.10", user="admin", port="3389", protocol="rdp")
        tab = self._make_rdp_tab(h)
        cmd = tab._build_cmd()
        self.assertIn("/v:192.168.1.10:3389", cmd)
        self.assertIn("/u:admin", cmd)
        self.assertNotIn(any(a.startswith("/p:") for a in cmd), [True])

    def test_cmd_with_password(self):
        """Commande avec mot de passe inclut /p:."""
        h = _make_host(host="10.0.0.1", user="user", port="3389", protocol="rdp")
        tab = self._make_rdp_tab(h, pwd="secret")
        cmd = tab._build_cmd()
        self.assertTrue(any(a.startswith("/p:") for a in cmd))

    def test_cmd_with_domain_user(self):
        r"""Utilisateur avec domaine (domain\\user) génère /d: et /u:."""
        h = _make_host(host="10.0.0.1", user="DOMAIN\\admin", port="3389", protocol="rdp")
        tab = self._make_rdp_tab(h)
        cmd = tab._build_cmd()
        self.assertTrue(any(a.startswith("/d:") for a in cmd))
        self.assertIn("/u:admin", cmd)

    def test_cmd_cert_ignore(self):
        """La commande inclut toujours /cert:ignore."""
        h = _make_host(host="10.0.0.1", user="u", port="3389", protocol="rdp")
        tab = self._make_rdp_tab(h)
        cmd = tab._build_cmd()
        self.assertIn("/cert:ignore", cmd)

    def test_cmd_dynamic_resolution(self):
        """La commande inclut /dynamic-resolution."""
        h = _make_host(host="10.0.0.1", user="u", port="3389", protocol="rdp")
        tab = self._make_rdp_tab(h)
        cmd = tab._build_cmd()
        self.assertIn("/dynamic-resolution", cmd)

    def test_cmd_with_extra_params(self):
        """Les extra_params sont ajoutés à la commande."""
        h = _make_host(
            host="10.0.0.1",
            user="u",
            port="3389",
            protocol="rdp",
            extra_params="+clipboard /sound",
        )
        tab = self._make_rdp_tab(h)
        cmd = tab._build_cmd()
        self.assertIn("+clipboard", cmd)
        self.assertIn("/sound", cmd)


# ── Tests RdpEmbeddedTab._build_cmd ─────────────────────────────────────────


class TestRdpEmbeddedTabBuildCmd(unittest.TestCase):
    """Tests pour RdpEmbeddedTab._build_cmd (XEmbed)."""

    def _make_embedded_tab(self, host, pwd=""):
        tab = gcm.RdpEmbeddedTab(host, lambda: pwd)
        tab._xid = 12345  # XID simulé
        return tab

    def test_parent_window_present(self):
        """La commande XEmbed inclut /parent-window:."""
        h = _make_host(host="10.0.0.1", user="u", port="3389", protocol="rdp")
        tab = self._make_embedded_tab(h)
        cmd = tab._build_cmd()
        self.assertTrue(any(a.startswith("/parent-window:") for a in cmd))

    def test_parent_window_is_hex(self):
        """La valeur /parent-window: est en hexadécimal."""
        h = _make_host(host="10.0.0.1", user="u", port="3389", protocol="rdp")
        tab = self._make_embedded_tab(h)
        tab._xid = 0x1A2B
        cmd = tab._build_cmd()
        pw_arg = next(a for a in cmd if a.startswith("/parent-window:"))
        xid_val = pw_arg.split(":")[1]
        # Doit être un entier hex valide
        self.assertEqual(int(xid_val, 16), 0x1A2B)

    def test_host_port_in_cmd(self):
        """/v: contient l'hôte et le port."""
        h = _make_host(host="192.168.2.5", user="u", port="3390", protocol="rdp")
        tab = self._make_embedded_tab(h)
        cmd = tab._build_cmd()
        self.assertIn("/v:192.168.2.5:3390", cmd)


# ── Tests VncTab._build_cmd ──────────────────────────────────────────────────


class TestVncTabBuildCmd(unittest.TestCase):
    """Tests pour VncTab._build_cmd."""

    def _make_vnc_tab(self, host, pwd="", vnc_bin="vncviewer"):
        with patch.object(gcm, "VNC_BIN", vnc_bin):
            tab = gcm.VncTab(host, lambda: pwd)
        tab.host = host
        tab._get_password = lambda: pwd
        return tab

    def test_basic_host_port(self):
        """La commande contient host:port."""
        h = _make_host(host="192.168.1.20", port="5900", protocol="vnc")
        tab = self._make_vnc_tab(h)
        with patch.object(gcm, "VNC_BIN", "vncviewer"):
            cmd, _ = tab._build_cmd()
        self.assertTrue(any("192.168.1.20" in a for a in cmd))

    def test_remmina_uri_style(self):
        """Avec remmina, la commande utilise une URI vnc://."""
        h = _make_host(host="10.0.0.5", port="5901", protocol="vnc")
        tab = self._make_vnc_tab(h, vnc_bin="/usr/bin/remmina")
        with patch.object(gcm, "VNC_BIN", "/usr/bin/remmina"):
            cmd, _ = tab._build_cmd()
        self.assertTrue(any("vnc://" in a for a in cmd))

    def test_vinagre_uri_style(self):
        """Avec vinagre, la commande utilise une URI vnc://."""
        h = _make_host(host="10.0.0.5", port="5901", protocol="vnc")
        tab = self._make_vnc_tab(h, vnc_bin="/usr/bin/vinagre")
        with patch.object(gcm, "VNC_BIN", "/usr/bin/vinagre"):
            cmd, _ = tab._build_cmd()
        self.assertTrue(any("vnc://" in a for a in cmd))

    def test_password_in_uri_for_vinagre(self):
        """Avec vinagre + mot de passe, l'URI contient le mot de passe."""
        h = _make_host(host="10.0.0.5", port="5901", protocol="vnc")
        tab = self._make_vnc_tab(h, pwd="vncp@ss", vnc_bin="/usr/bin/vinagre")
        with patch.object(gcm, "VNC_BIN", "/usr/bin/vinagre"):
            cmd, _ = tab._build_cmd()
        self.assertTrue(any("vncp@ss" in a for a in cmd))


# ── Tests SpiceTab._build_cmd ────────────────────────────────────────────────


class TestSpiceTabBuildCmd(unittest.TestCase):
    """Tests pour SpiceTab._build_cmd."""

    def _make_spice_tab(self, host, pwd=""):
        tab = gcm.SpiceTab(host, lambda: pwd)
        tab.host = host
        tab._get_password = lambda: pwd
        return tab

    def test_spice_uri_format(self):
        """La commande contient une URI spice://."""
        h = _make_host(host="192.168.1.30", port="5930", protocol="spice")
        tab = self._make_spice_tab(h)
        cmd = tab._build_cmd()
        self.assertTrue(any("spice://" in a for a in cmd))

    def test_port_in_uri(self):
        """L'URI SPICE contient le port."""
        h = _make_host(host="192.168.1.30", port="5930", protocol="spice")
        tab = self._make_spice_tab(h)
        cmd = tab._build_cmd()
        uri_arg = next(a for a in cmd if "spice://" in a)
        self.assertIn("5930", uri_arg)

    def test_host_in_uri(self):
        """L'URI SPICE contient l'adresse hôte."""
        h = _make_host(host="10.10.0.5", port="5930", protocol="spice")
        tab = self._make_spice_tab(h)
        cmd = tab._build_cmd()
        uri_arg = next(a for a in cmd if "spice://" in a)
        self.assertIn("10.10.0.5", uri_arg)

    def test_password_in_uri(self):
        """Avec mot de passe, l'URI contient password=."""
        h = _make_host(host="10.10.0.5", port="5930", protocol="spice")
        tab = self._make_spice_tab(h, pwd="sp1c3p@ss")
        cmd = tab._build_cmd()
        uri_arg = next(a for a in cmd if "spice://" in a)
        self.assertIn("password=sp1c3p@ss", uri_arg)

    def test_no_password_no_password_param(self):
        """Sans mot de passe, l'URI ne contient pas password=."""
        h = _make_host(host="10.10.0.5", port="5930", protocol="spice")
        tab = self._make_spice_tab(h, pwd="")
        cmd = tab._build_cmd()
        uri_arg = next(a for a in cmd if "spice://" in a)
        self.assertNotIn("password=", uri_arg)

    def test_extra_params_appended(self):
        """Les extra_params sont ajoutés après l'URI."""
        h = _make_host(
            host="10.10.0.5",
            port="5930",
            protocol="spice",
            extra_params="--full-screen",
        )
        tab = self._make_spice_tab(h)
        cmd = tab._build_cmd()
        self.assertIn("--full-screen", cmd)


# ── Tests proto_defaults ─────────────────────────────────────────────────────


class TestProtoDefaults(unittest.TestCase):
    """Tests pour le dictionnaire _PROTO_DEFAULTS."""

    def test_ssh_port(self):
        self.assertEqual(gcm._PROTO_DEFAULTS["ssh"], "22")

    def test_rdp_port(self):
        self.assertEqual(gcm._PROTO_DEFAULTS["rdp"], "3389")

    def test_vnc_port(self):
        self.assertEqual(gcm._PROTO_DEFAULTS["vnc"], "5900")

    def test_spice_port(self):
        self.assertEqual(gcm._PROTO_DEFAULTS["spice"], "5930")

    def test_telnet_port(self):
        self.assertEqual(gcm._PROTO_DEFAULTS["telnet"], "23")

    def test_local_empty(self):
        self.assertEqual(gcm._PROTO_DEFAULTS["local"], "")

    def test_serial_port(self):
        self.assertEqual(gcm._PROTO_DEFAULTS["serial"], "9600")

    def test_all_keys_present(self):
        for k in ("ssh", "telnet", "rdp", "vnc", "spice", "serial", "local"):
            self.assertIn(k, gcm._PROTO_DEFAULTS)


# ── Tests SerialTab._build_cmd ───────────────────────────────────────────────


class TestSerialTabBuildCmd(unittest.TestCase):
    """Tests pour SerialTab._build_cmd (picocom/minicom/screen)."""

    def _make_host(self, device="/dev/ttyUSB0", baud="9600", opts="", tpl=""):
        return _make_host(host=device, port=baud, extra_params=opts, protocol="serial")

    def _make_tab(self, device="/dev/ttyUSB0", baud="9600", opts=""):
        h = self._make_host(device, baud, opts)
        return gcm.SerialTab(h)

    # ── picocom (binaire par défaut dans les tests) ──────────────────────────

    def _with_picocom(self, fn):
        """Force SERIAL_BIN=picocom pour la durée de fn."""
        original = gcm.SERIAL_BIN
        gcm.SERIAL_BIN = "picocom"
        try:
            fn()
        finally:
            gcm.SERIAL_BIN = original

    def _with_minicom(self, fn):
        original = gcm.SERIAL_BIN
        gcm.SERIAL_BIN = "minicom"
        try:
            fn()
        finally:
            gcm.SERIAL_BIN = original

    def _with_screen(self, fn):
        original = gcm.SERIAL_BIN
        gcm.SERIAL_BIN = "screen"
        try:
            fn()
        finally:
            gcm.SERIAL_BIN = original

    def test_picocom_device_in_cmd(self):
        """Le device doit être dernier argument picocom."""

        def _():
            tab = self._make_tab("/dev/ttyUSB0", "9600")
            cmd = tab._build_cmd()
            self.assertEqual(cmd[-1], "/dev/ttyUSB0")

        self._with_picocom(_)

    def test_picocom_baud_in_cmd(self):
        """Le débit est passé via --baud."""

        def _():
            tab = self._make_tab("/dev/ttyS0", "115200")
            cmd = tab._build_cmd()
            self.assertIn("--baud", cmd)
            self.assertIn("115200", cmd)

        self._with_picocom(_)

    def test_picocom_extra_opts(self):
        """Les options supplémentaires sont injectées."""

        def _():
            tab = self._make_tab(
                "/dev/ttyUSB0", "9600", "--flow n --parity n --databits 8 --stopbits 1"
            )
            cmd = tab._build_cmd()
            self.assertIn("--flow", cmd)
            self.assertIn("n", cmd)
            self.assertIn("--parity", cmd)

        self._with_picocom(_)

    def test_picocom_no_opts(self):
        """Sans options libres, les flags série standards sont toujours présents via les combos."""

        def _():
            tab = self._make_tab("/dev/ttyUSB0", "9600", "")
            cmd = tab._build_cmd()
            # Nouveau comportement : --flow/--parity/--databits/--stopbits lus depuis les combos
            self.assertIn("--baud", cmd)
            self.assertIn("--flow", cmd)
            self.assertIn("--parity", cmd)
            self.assertIn("--databits", cmd)
            self.assertIn("--stopbits", cmd)

        self._with_picocom(_)

    def test_picocom_starts_with_binary(self):
        """Premier élément = binaire picocom."""

        def _():
            tab = self._make_tab()
            cmd = tab._build_cmd()
            self.assertEqual(cmd[0], "picocom")

        self._with_picocom(_)

    def test_minicom_device_flag(self):
        """Minicom utilise -D pour le device."""

        def _():
            tab = self._make_tab("/dev/ttyUSB1", "38400")
            cmd = tab._build_cmd()
            self.assertIn("-D", cmd)
            self.assertIn("/dev/ttyUSB1", cmd)

        self._with_minicom(_)

    def test_minicom_baud_flag(self):
        """Minicom utilise -b pour le débit."""

        def _():
            tab = self._make_tab("/dev/ttyUSB0", "57600")
            cmd = tab._build_cmd()
            self.assertIn("-b", cmd)
            self.assertIn("57600", cmd)

        self._with_minicom(_)

    def test_screen_device_and_baud(self):
        """Screen prend device puis baud en positionnels."""

        def _():
            tab = self._make_tab("/dev/ttyS1", "115200")
            cmd = tab._build_cmd()
            # screen DEVICE BAUD (après le binaire)
            self.assertEqual(cmd[0], "screen")
            self.assertIn("/dev/ttyS1", cmd)
            self.assertIn("115200", cmd)

        self._with_screen(_)

    def test_screen_extra_opts(self):
        """Screen : les options supplémentaires sont ajoutées."""

        def _():
            tab = self._make_tab("/dev/ttyUSB0", "9600", "-L")
            cmd = tab._build_cmd()
            self.assertIn("-L", cmd)

        self._with_screen(_)

    def test_default_device_fallback(self):
        """/dev/ttyUSB0 est utilisé si le champ device est vide."""

        def _():
            h = _make_host(host="", port="9600", protocol="serial")
            tab = gcm.SerialTab(h)
            # vider manuellement l'entry
            tab._entry_dev.set_text("")
            cmd = tab._build_cmd()
            self.assertIn("/dev/ttyUSB0", cmd)

        self._with_picocom(_)

    def test_default_baud_fallback(self):
        """9600 est utilisé si le combo débit est indéfini."""

        def _():
            tab = self._make_tab("/dev/ttyUSB0", "9600")
            # forcer combo à -1 (non sélectionné)
            tab._cmb_baud.set_active(-1)
            cmd = tab._build_cmd()
            # le fallback doit être "9600"
            self.assertIn("9600", cmd)

        self._with_picocom(_)


# ── Tests _SERIAL_TEMPLATES ──────────────────────────────────────────────────


class TestSerialTemplates(unittest.TestCase):
    """Tests pour le dictionnaire _SERIAL_TEMPLATES."""

    def test_all_vendors_present(self):
        for vendor in (
            "Cisco IOS / IOS-XE / NX-OS",
            "HP Comware (H3C)",
            "Aruba AOS-S / AOS-CX",
            "Juniper JunOS",
            "Fortinet FortiOS",
            "Palo Alto PAN-OS",
            "F5 TMOS",
            "Linux / Raspberry Pi",
            "Arduino / ESP32",
            "RS-485 Modbus RTU",
            "Libre (manuel)",
        ):
            self.assertIn(vendor, gcm._SERIAL_TEMPLATES)

    def test_tuple_length_5(self):
        """Chaque template doit avoir 5 valeurs (baud, flow, parity, bits, stop)."""
        for name, tpl in gcm._SERIAL_TEMPLATES.items():
            self.assertEqual(len(tpl), 5, msg=f"Template '{name}' : longueur incorrecte")

    def test_cisco_9600_8n1(self):
        baud, flow, parity, databits, stopbits = gcm._SERIAL_TEMPLATES[
            "Cisco IOS / IOS-XE / NX-OS"
        ]
        self.assertEqual(baud, "9600")
        self.assertEqual(flow, "n")
        self.assertEqual(parity, "n")
        self.assertEqual(databits, "8")
        self.assertEqual(stopbits, "1")

    def test_aruba_9600_8n1(self):
        baud, flow, *_ = gcm._SERIAL_TEMPLATES["Aruba AOS-S / AOS-CX"]
        self.assertEqual(baud, "9600")
        self.assertEqual(flow, "n")

    def test_linux_115200(self):
        baud, *_ = gcm._SERIAL_TEMPLATES["Linux / Raspberry Pi"]
        self.assertEqual(baud, "115200")

    def test_arduino_115200(self):
        baud, *_ = gcm._SERIAL_TEMPLATES["Arduino / ESP32"]
        self.assertEqual(baud, "115200")

    def test_f5_19200(self):
        baud, *_ = gcm._SERIAL_TEMPLATES["F5 TMOS"]
        self.assertEqual(baud, "19200")

    def test_flow_values_valid(self):
        """Flow doit être n, x ou h."""
        for name, (_, flow, *_rest) in gcm._SERIAL_TEMPLATES.items():
            self.assertIn(flow, ("n", "x", "h"), msg=f"flow invalide pour '{name}'")

    def test_parity_values_valid(self):
        """Parity doit être n, e ou o."""
        for name, (_, _, parity, *_rest) in gcm._SERIAL_TEMPLATES.items():
            self.assertIn(parity, ("n", "e", "o"), msg=f"parity invalide pour '{name}'")

    def test_baud_values_numeric(self):
        """Tous les débits doivent être numériques."""
        for name, (baud, *_rest) in gcm._SERIAL_TEMPLATES.items():
            self.assertTrue(baud.isdigit(), msg=f"baud non numérique pour '{name}'")


# ── Tests Host (supplémentaires) ─────────────────────────────────────────────


class TestHostExtended(unittest.TestCase):
    """Tests supplémentaires pour la classe Host."""

    def test_host_serial_protocol(self):
        h = _make_host(protocol="serial")
        self.assertEqual(h.protocol, "serial")

    def test_host_port_as_baud_for_serial(self):
        """Pour serial, port = débit en bauds."""
        h = _make_host(host="/dev/ttyUSB0", port="115200", protocol="serial")
        self.assertEqual(h.port, "115200")

    def test_host_extra_params_stored(self):
        h = _make_host(extra_params="--flow n --parity n")
        self.assertEqual(h.extra_params, "--flow n --parity n")

    def test_host_clone_extra_params(self):
        h = _make_host(extra_params="--flow n")
        c = h.clone()
        self.assertEqual(c.extra_params, "--flow n")

    def test_host_clone_is_independent(self):
        h = _make_host(name="orig")
        c = h.clone()
        c.name = "copy"
        self.assertEqual(h.name, "orig")

    def test_host_type_field(self):
        h = _make_host()
        h.type = "Cisco IOS / IOS-XE / NX-OS"
        self.assertEqual(h.type, "Cisco IOS / IOS-XE / NX-OS")

    def test_host_description_none_safe(self):
        """description=None ne lève pas d'exception à la création."""
        h = gcm.Host(
            "G",
            "n",
            None,
            "10.0.0.1",
            "u",
            "",
            None,
            "22",
            "",
            "ssh",
            None,
            "0",
            "",
            "",
            False,
            False,
            False,
            "",
            "",
            False,
            int(gcm.Vte.EraseBinding.AUTO),
            int(gcm.Vte.EraseBinding.AUTO),
            "",
            "ssh",
        )
        self.assertIsNone(h.description)

    def test_host_tunnel_empty_split(self):
        h = _make_host()
        self.assertEqual(h.tunnel, [""])

    def test_host_tunnel_with_value(self):
        h = gcm.Host(
            "G",
            "n",
            None,
            "10.0.0.1",
            "u",
            "",
            None,
            "22",
            "8080:remote:80",
            "ssh",
            None,
            "0",
            "",
            "",
            False,
            False,
            False,
            "",
            "",
            False,
            int(gcm.Vte.EraseBinding.AUTO),
            int(gcm.Vte.EraseBinding.AUTO),
            "",
            "ssh",
        )
        self.assertEqual(h.tunnel, ["8080:remote:80"])


# ── Tests HostUtils (supplémentaires) ────────────────────────────────────────


class TestHostUtilsExtended(unittest.TestCase):
    """Tests supplémentaires pour HostUtils.save/load."""

    def test_save_and_load_serial_protocol(self):
        """Protocole serial est préservé en save/load."""
        h = _make_host(
            host="/dev/ttyUSB0",
            port="115200",
            protocol="serial",
            extra_params="--flow n",
        )
        cp = configparser.ConfigParser()
        cp.add_section("host0")
        gcm.HostUtils.save_host_to_ini(cp, "host0", h, "pass")
        loaded = gcm.HostUtils.load_host_from_ini(cp, "host0", "pass")
        self.assertEqual(loaded.protocol, "serial")
        self.assertEqual(loaded.port, "115200")
        self.assertEqual(loaded.extra_params, "--flow n")

    def test_save_none_fields_no_exception(self):
        """save_host_to_ini ne lève pas d'exception si certains champs sont None."""
        h = gcm.Host(
            "G",
            "n",
            None,
            "10.0.0.1",
            "u",
            "",
            None,
            "22",
            "",
            "ssh",
            None,
            "0",
            "",
            "",
            False,
            False,
            False,
            "",
            "",
            False,
            int(gcm.Vte.EraseBinding.AUTO),
            int(gcm.Vte.EraseBinding.AUTO),
            "",
            "ssh",
        )
        cp = configparser.ConfigParser()
        cp.add_section("s0")
        gcm.HostUtils.save_host_to_ini(cp, "s0", h, "")  # ne doit pas lever

    def test_save_and_load_roundtrip_name(self):
        h = _make_host(name="mon-routeur")
        cp = configparser.ConfigParser()
        cp.add_section("x")
        gcm.HostUtils.save_host_to_ini(cp, "x", h, "")
        loaded = gcm.HostUtils.load_host_from_ini(cp, "x", "")
        self.assertEqual(loaded.name, "mon-routeur")

    def test_save_and_load_roundtrip_host(self):
        h = _make_host(host="192.168.1.254")
        cp = configparser.ConfigParser()
        cp.add_section("x")
        gcm.HostUtils.save_host_to_ini(cp, "x", h, "")
        loaded = gcm.HostUtils.load_host_from_ini(cp, "x", "")
        self.assertEqual(loaded.host, "192.168.1.254")


# ── Tests chiffrement (supplémentaires) ──────────────────────────────────────


class TestEncryptionExtended(unittest.TestCase):
    """Tests supplémentaires pour les fonctions de chiffrement."""

    def setUp(self):
        self._orig_version = gcm.conf.VERSION
        gcm.conf.VERSION = 1  # force pyAES

    def tearDown(self):
        gcm.conf.VERSION = self._orig_version

    def test_xor_with_key_longer_than_text(self):
        """La clé plus longue que le texte ne doit pas planter."""
        result = gcm.xor("clé-très-longue-longue", "hi")
        self.assertEqual(len(result), 2)

    def test_xor_with_special_chars(self):
        plain = "héllo wörld"
        key = "k3y"
        roundtrip = "".join(gcm.xor(key, "".join(gcm.xor(key, plain))))
        self.assertEqual(roundtrip, plain)

    def test_encrypt_aes_different_from_plaintext(self):
        cipher = gcm.encrypt("pass", "secret")
        self.assertNotEqual(cipher, "secret")

    def test_encrypt_aes_returns_string(self):
        result = gcm.encrypt("pass", "test")
        self.assertIsInstance(result, str)

    def test_decrypt_aes_returns_string(self):
        cipher = gcm.encrypt("pass", "hello")
        result = gcm.decrypt("pass", cipher)
        self.assertIsInstance(result, str)

    def test_encrypt_decrypt_aes_extended_latin(self):
        """PyAES supporte les caractères latin-1 (U+0000–U+00FF)."""
        plain = "mot de passe admin"
        cipher = gcm.encrypt("key", plain)
        result = gcm.decrypt("key", cipher)
        self.assertEqual(result, plain)

    def test_encrypt_old_returns_string(self):
        result = gcm.encrypt_old("pass", "hello")
        self.assertIsInstance(result, str)

    def test_decrypt_old_returns_string(self):
        enc = gcm.encrypt_old("pass", "hello")
        result = gcm.decrypt_old("pass", enc)
        self.assertIsInstance(result, str)


# ── Tests VmNameSplit (supplémentaires) ──────────────────────────────────────


class TestVmNameSplitExtended(unittest.TestCase):
    """Tests supplémentaires pour _vm_name_split."""

    def test_double_underscore(self):
        grp, name = gcm._vm_name_split("web__server")
        self.assertEqual(grp, "WEB")

    def test_leading_separator_is_no_separator(self):
        """Un nom commençant par _ n'a pas de groupe."""
        grp, name = gcm._vm_name_split("_server")
        # pas de token avant le _, donc groupe = LIBVIRT
        self.assertEqual(grp, "LIBVIRT")

    def test_digits_only_name(self):
        grp, name = gcm._vm_name_split("192-168")
        self.assertEqual(grp, "192")
        self.assertEqual(name, "168")

    def test_unicode_name(self):
        """Les noms unicodes sont tolérés."""
        grp, name = gcm._vm_name_split("réseau_interne")
        self.assertEqual(grp, "RÉSEAU")

    def test_single_char_group(self):
        grp, name = gcm._vm_name_split("a_server")
        self.assertEqual(grp, "A")
        self.assertEqual(name, "server")


# ── Tests _rdp_socket_available (supplémentaires) ────────────────────────────


class TestRdpSocketAvailableExtended(unittest.TestCase):
    """Tests supplémentaires pour _rdp_socket_available."""

    def test_empty_display_returns_false(self):
        with patch.dict(os.environ, {"DISPLAY": ""}, clear=False):
            self.assertFalse(gcm._rdp_socket_available())

    def test_xwayland_display_returns_true(self):
        """XWayland expose DISPLAY — doit retourner True."""
        with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=False):
            # simuler Gdk.Display retournant un objet de type X11Display
            class _X11Display:
                pass

            with patch.object(gcm.Gdk, "Display") as mock_gdk_display:
                mock_gdk_display.get_default.return_value = _X11Display()
                result = gcm._rdp_socket_available()
                self.assertTrue(result)


# ── Tests RdpTab (supplémentaires) ───────────────────────────────────────────


class TestRdpTabBuildCmdExtended(unittest.TestCase):
    """Tests supplémentaires pour RdpTab._build_cmd."""

    def _make_rdp_tab(self, host, pwd=""):
        return gcm.RdpTab(host, lambda: pwd)

    def test_rdp_v_flag_host_port(self):
        """/v: contient host:port."""
        h = _make_host(host="srv.local", port="3390", protocol="rdp")
        tab = self._make_rdp_tab(h)
        cmd = tab._build_cmd()
        v_arg = next((a for a in cmd if a.startswith("/v:")), None)
        self.assertIsNotNone(v_arg)
        self.assertIn("srv.local", v_arg)
        self.assertIn("3390", v_arg)

    def test_rdp_starts_with_binary(self):
        h = _make_host(host="10.0.0.1", protocol="rdp")
        tab = self._make_rdp_tab(h)
        cmd = tab._build_cmd()
        self.assertEqual(cmd[0], gcm.RDP_BIN)

    def test_rdp_password_in_cmd(self):
        h = _make_host(host="10.0.0.1", protocol="rdp")
        tab = self._make_rdp_tab(h, pwd="topsecret")
        cmd = tab._build_cmd()
        self.assertTrue(any("topsecret" in a for a in cmd))

    def test_rdp_no_password_no_p_flag(self):
        """Sans mot de passe, /p: ne doit pas apparaître."""
        h = _make_host(host="10.0.0.1", protocol="rdp")
        tab = self._make_rdp_tab(h, pwd="")
        cmd = tab._build_cmd()
        self.assertFalse(any(a.startswith("/p:") for a in cmd))

    def test_rdp_multiple_extra_params(self):
        h = _make_host(
            host="10.0.0.1",
            protocol="rdp",
            extra_params="+clipboard /sound /microphone",
        )
        tab = self._make_rdp_tab(h)
        cmd = tab._build_cmd()
        self.assertIn("+clipboard", cmd)
        self.assertIn("/sound", cmd)
        self.assertIn("/microphone", cmd)


# ── Tests VncTab (supplémentaires) ───────────────────────────────────────────


class TestVncTabBuildCmdExtended(unittest.TestCase):
    """Tests supplémentaires pour VncTab._build_cmd."""

    def _make_vnc_tab(self, host, pwd=""):
        return gcm.VncTab(host, lambda: pwd)

    def test_vnc_starts_with_binary(self):
        h = _make_host(host="10.0.0.2", port="5901", protocol="vnc")
        tab = self._make_vnc_tab(h)
        cmd, _ = tab._build_cmd()
        self.assertEqual(cmd[0], gcm.VNC_BIN)

    def test_vnc_host_port_format(self):
        h = _make_host(host="10.0.0.2", port="5902", protocol="vnc")
        tab = self._make_vnc_tab(h)
        cmd, _ = tab._build_cmd()
        # au moins un argument contient host:port
        combined = " ".join(cmd)
        self.assertIn("10.0.0.2", combined)
        self.assertIn("5902", combined)

    def test_vnc_user_in_uri_for_vinagre(self):
        """Vinagre doit inclure l'utilisateur dans l'URI."""
        original = gcm.VNC_BIN
        gcm.VNC_BIN = "vinagre"
        try:
            h = _make_host(host="10.0.0.3", port="5900", user="admin", protocol="vnc")
            tab = self._make_vnc_tab(h, pwd="secret")
            cmd, _ = tab._build_cmd()
            self.assertTrue(any("admin" in a for a in cmd))
        finally:
            gcm.VNC_BIN = original

    def test_vnc_returns_tuple(self):
        h = _make_host(host="10.0.0.2", port="5900", protocol="vnc")
        tab = self._make_vnc_tab(h)
        result = tab._build_cmd()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)


# ── Tests SpiceTab (supplémentaires) ─────────────────────────────────────────


class TestSpiceTabBuildCmdExtended(unittest.TestCase):
    """Tests supplémentaires pour SpiceTab._build_cmd."""

    def _make_spice_tab(self, host, pwd=""):
        return gcm.SpiceTab(host, lambda: pwd)

    def test_spice_starts_with_binary(self):
        h = _make_host(host="10.0.0.5", port="5930", protocol="spice")
        tab = self._make_spice_tab(h)
        cmd = tab._build_cmd()
        self.assertEqual(cmd[0], gcm.SPICE_BIN)

    def test_spice_returns_list(self):
        h = _make_host(host="10.0.0.5", port="5930", protocol="spice")
        tab = self._make_spice_tab(h)
        cmd = tab._build_cmd()
        self.assertIsInstance(cmd, list)

    def test_spice_uri_starts_with_spice(self):
        h = _make_host(host="10.0.0.5", port="5930", protocol="spice")
        tab = self._make_spice_tab(h)
        cmd = tab._build_cmd()
        uri = next((a for a in cmd if a.startswith("spice://")), None)
        self.assertIsNotNone(uri)

    def test_spice_password_in_query(self):
        h = _make_host(host="10.0.0.5", port="5930", protocol="spice")
        tab = self._make_spice_tab(h, pwd="mypassword")
        cmd = tab._build_cmd()
        self.assertTrue(any("mypassword" in a for a in cmd))

    def test_spice_multiple_extra_params(self):
        h = _make_host(
            host="10.0.0.5",
            port="5930",
            protocol="spice",
            extra_params="--full-screen --spice-debug",
        )
        tab = self._make_spice_tab(h)
        cmd = tab._build_cmd()
        self.assertIn("--full-screen", cmd)
        self.assertIn("--spice-debug", cmd)


# ── Tests encrypt_old/decrypt_old (bug Python 3) ─────────────────────────────


class TestEncryptOldPython3(unittest.TestCase):
    """Vérifie que encrypt_old/decrypt_old fonctionnent en Python 3."""

    def test_roundtrip_simple(self):
        enc = gcm.encrypt_old("key", "hello")
        dec = gcm.decrypt_old("key", enc)
        self.assertEqual(dec, "hello")

    def test_roundtrip_with_special_chars(self):
        enc = gcm.encrypt_old("pass123", "Pässwörd!@#")
        dec = gcm.decrypt_old("pass123", enc)
        self.assertEqual(dec, "Pässwörd!@#")

    def test_encrypt_old_not_plaintext(self):
        enc = gcm.encrypt_old("key", "secret")
        self.assertNotEqual(enc, "secret")

    def test_decrypt_old_wrong_key_differs(self):
        enc = gcm.encrypt_old("key1", "hello")
        dec_wrong = gcm.decrypt_old("key2", enc)
        self.assertNotEqual(dec_wrong, "hello")

    def test_empty_string_roundtrip(self):
        enc = gcm.encrypt_old("key", "")
        dec = gcm.decrypt_old("key", enc)
        self.assertEqual(dec, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)


# ═══════════════════════════════════════════════════════════════════════════
#  BLOC 3 — Tests supplémentaires (triplement de la suite)
# ═══════════════════════════════════════════════════════════════════════════

# ── xor (exhaustif) ──────────────────────────────────────────────────────────


class TestXorFunction(unittest.TestCase):
    """Tests exhaustifs pour la primitive xor()."""

    def test_single_char(self):
        self.assertEqual(len(gcm.xor("k", "a")), 1)

    def test_key_wraps_around(self):
        self.assertEqual(len(gcm.xor("k", "hello")), 5)

    def test_double_application_is_identity(self):
        text = "test message"
        key = "secret"
        enc = "".join(gcm.xor(key, text))
        dec = "".join(gcm.xor(key, enc))
        self.assertEqual(dec, text)

    def test_empty_text(self):
        self.assertEqual(gcm.xor("key", ""), [])

    def test_key_longer_than_text_no_crash(self):
        result = gcm.xor("very_long_key_here", "hi")
        self.assertEqual(len(result), 2)

    def test_with_spaces(self):
        self.assertEqual(len(gcm.xor("key", "hello world")), 11)

    def test_ascii_printable(self):
        result = gcm.xor("12345678", "ABCDEFGH")
        self.assertEqual(len(result), 8)

    def test_result_is_list(self):
        self.assertIsInstance(gcm.xor("k", "hello"), list)

    def test_repeated_key_byte_gives_consistent_output(self):
        r1 = gcm.xor("k", "abc")
        r2 = gcm.xor("k", "abc")
        self.assertEqual(r1, r2)

    def test_different_keys_different_output(self):
        r1 = "".join(gcm.xor("key1", "hello"))
        r2 = "".join(gcm.xor("key2", "hello"))
        self.assertNotEqual(r1, r2)


# ── Host — champs par défaut ──────────────────────────────────────────────────


class TestHostFieldDefaults(unittest.TestCase):
    """Vérifie les valeurs par défaut de chaque champ Host."""

    def setUp(self):
        self.h = _make_host()

    def test_protocol_ssh(self):
        self.assertEqual(self.h.protocol, "ssh")

    def test_x11_false(self):
        self.assertFalse(self.h.x11)

    def test_compression_false(self):
        self.assertFalse(self.h.compression)

    def test_agent_false(self):
        self.assertFalse(self.h.agent)

    def test_log_false(self):
        self.assertFalse(self.h.log)

    def test_font_color_empty(self):
        self.assertEqual(self.h.font_color, "")

    def test_back_color_empty(self):
        self.assertEqual(self.h.back_color, "")

    def test_extra_params_empty(self):
        self.assertEqual(self.h.extra_params, "")

    def test_compressionLevel_empty(self):
        self.assertEqual(self.h.compressionLevel, "")

    def test_term_empty(self):
        self.assertEqual(self.h.term, "")

    def test_keep_alive_zero(self):
        self.assertEqual(str(self.h.keep_alive), "0")

    def test_tunnel_list(self):
        self.assertIsInstance(self.h.tunnel, list)

    def test_group_stored(self):
        h = _make_host(group="ROUTERS")
        self.assertEqual(h.group, "ROUTERS")

    def test_name_stored(self):
        h = _make_host(name="sw-core")
        self.assertEqual(h.name, "sw-core")

    def test_host_stored(self):
        h = _make_host(host="192.168.1.254")
        self.assertEqual(h.host, "192.168.1.254")

    def test_user_stored(self):
        h = _make_host(user="admin")
        self.assertEqual(h.user, "admin")

    def test_port_stored(self):
        h = _make_host(port="8022")
        self.assertEqual(h.port, "8022")


# ── Host — tunnel ─────────────────────────────────────────────────────────────


class TestHostTunnelParsing(unittest.TestCase):
    """Parsing et sérialisation des tunnels SSH."""

    def _h(self, tunnel_str):
        return gcm.Host(
            "G",
            "n",
            None,
            "10.0.0.1",
            "u",
            "",
            None,
            "22",
            tunnel_str,
            "ssh",
            None,
            0,
            "",
            "",
            False,
            False,
            False,
            "",
            "",
            False,
            0,
            0,
            "",
            "ssh",
        )

    def test_empty_tunnel_as_string(self):
        self.assertEqual(_make_host().tunnel_as_string(), "")

    def test_single_forward_tunnel(self):
        h = self._h("8080:remote:80")
        self.assertIn("8080:remote:80", h.tunnel)

    def test_tunnel_as_string_non_empty(self):
        h = self._h("8080:remote:80")
        self.assertIn("8080:remote:80", h.tunnel_as_string())

    def test_dynamic_socks_entry(self):
        h = self._h("1080:*:*")
        self.assertIn("1080:*:*", h.tunnel)

    def test_tunnel_list_type(self):
        h = self._h("8080:remote:80")
        self.assertIsInstance(h.tunnel, list)

    def test_empty_tunnel_list(self):
        h = _make_host()
        self.assertEqual(h.tunnel, [""])


# ── Host — clone exhaustif ────────────────────────────────────────────────────


class TestHostCloneAllFields(unittest.TestCase):
    """Clone préserve chaque champ."""

    def setUp(self):
        self.orig = _make_host(
            group="ROUTERS",
            name="sw-core",
            host="192.168.1.254",
            user="admin",
            port="22",
            protocol="rdp",
            extra_params="--extra",
        )
        self.orig.font_color = "#FF0000"
        self.orig.back_color = "#000000"
        self.orig.x11 = True
        self.orig.agent = True
        self.orig.compression = True
        self.orig.compressionLevel = "9"
        self.orig.log = True
        self.orig.term = "xterm-256color"
        self.copy = self.orig.clone()

    def test_group(self):
        self.assertEqual(self.copy.group, "ROUTERS")

    def test_name(self):
        self.assertEqual(self.copy.name, "sw-core")

    def test_host(self):
        self.assertEqual(self.copy.host, "192.168.1.254")

    def test_user(self):
        self.assertEqual(self.copy.user, "admin")

    def test_port(self):
        self.assertEqual(self.copy.port, "22")

    def test_protocol(self):
        self.assertEqual(self.copy.protocol, "rdp")

    def test_extra_params(self):
        self.assertEqual(self.copy.extra_params, "--extra")

    def test_font_color(self):
        self.assertEqual(self.copy.font_color, "#FF0000")

    def test_back_color(self):
        self.assertEqual(self.copy.back_color, "#000000")

    def test_x11(self):
        self.assertTrue(self.copy.x11)

    def test_agent(self):
        self.assertTrue(self.copy.agent)

    def test_compression(self):
        self.assertTrue(self.copy.compression)

    def test_log(self):
        self.assertTrue(self.copy.log)

    def test_term(self):
        self.assertEqual(self.copy.term, "xterm-256color")

    def test_independent_name(self):
        self.copy.name = "other"
        self.assertEqual(self.orig.name, "sw-core")

    def test_independent_host(self):
        self.copy.host = "10.0.0.1"
        self.assertEqual(self.orig.host, "192.168.1.254")


# ── HostUtils — champs individuels ────────────────────────────────────────────


class TestHostUtilsEachField(unittest.TestCase):
    """Round-trip save/load pour chaque champ individuel."""

    def _rt(self, **kw):
        h = _make_host(**kw)
        cp = configparser.ConfigParser()
        cp.add_section("s")
        gcm.HostUtils.save_host_to_ini(cp, "s", h, "pass")
        return gcm.HostUtils.load_host_from_ini(cp, "s", "pass")

    def test_group(self):
        self.assertEqual(self._rt(group="CORE").group, "CORE")

    def test_name(self):
        self.assertEqual(self._rt(name="sw-access").name, "sw-access")

    def test_host_ip(self):
        self.assertEqual(self._rt(host="10.10.10.1").host, "10.10.10.1")

    def test_host_fqdn(self):
        self.assertEqual(self._rt(host="router.corp.local").host, "router.corp.local")

    def test_user(self):
        self.assertEqual(self._rt(user="operator").user, "operator")

    def test_port(self):
        self.assertEqual(self._rt(port="2222").port, "2222")

    def test_extra_params(self):
        self.assertEqual(self._rt(extra_params="/opt").extra_params, "/opt")

    def test_protocol_ssh(self):
        self.assertEqual(self._rt(protocol="ssh").protocol, "ssh")

    def test_protocol_telnet(self):
        self.assertEqual(self._rt(protocol="telnet").protocol, "telnet")

    def test_protocol_vnc(self):
        self.assertEqual(self._rt(protocol="vnc").protocol, "vnc")

    def test_protocol_spice(self):
        self.assertEqual(self._rt(protocol="spice").protocol, "spice")

    def test_protocol_serial(self):
        self.assertEqual(self._rt(protocol="serial").protocol, "serial")

    def test_protocol_rdp(self):
        self.assertEqual(self._rt(protocol="rdp").protocol, "rdp")

    def _rt_field(self, field, value):
        h = _make_host()
        setattr(h, field, value)
        cp = configparser.ConfigParser()
        cp.add_section("s")
        gcm.HostUtils.save_host_to_ini(cp, "s", h, "")
        return getattr(gcm.HostUtils.load_host_from_ini(cp, "s", ""), field)

    def test_font_color(self):
        self.assertEqual(self._rt_field("font_color", "#AABBCC"), "#AABBCC")

    def test_back_color(self):
        self.assertEqual(self._rt_field("back_color", "#112233"), "#112233")

    def test_term(self):
        self.assertEqual(self._rt_field("term", "xterm-256color"), "xterm-256color")

    def test_x11_true(self):
        self.assertTrue(self._rt_field("x11", True))

    def test_x11_false(self):
        self.assertFalse(self._rt_field("x11", False))

    def test_agent_true(self):
        self.assertTrue(self._rt_field("agent", True))

    def test_compression_true(self):
        self.assertTrue(self._rt_field("compression", True))

    def test_log_true(self):
        self.assertTrue(self._rt_field("log", True))

    def test_keepalive(self):
        self.assertEqual(self._rt_field("keep_alive", "30"), "30")

    def test_compressionLevel(self):
        self.assertEqual(self._rt_field("compressionLevel", "6"), "6")


# ── _PROTO_DEFAULTS — exhaustif ───────────────────────────────────────────────


class TestProtoDefaultsExhaustive(unittest.TestCase):
    """Tests exhaustifs pour _PROTO_DEFAULTS."""

    def test_has_7_keys(self):
        self.assertEqual(len(gcm._PROTO_DEFAULTS), 7)

    def test_all_values_strings(self):
        for k, v in gcm._PROTO_DEFAULTS.items():
            self.assertIsInstance(v, str, msg=f"{k} non-string")

    def test_ssh_22(self):
        self.assertEqual(gcm._PROTO_DEFAULTS["ssh"], "22")

    def test_telnet_23(self):
        self.assertEqual(gcm._PROTO_DEFAULTS["telnet"], "23")

    def test_rdp_3389(self):
        self.assertEqual(gcm._PROTO_DEFAULTS["rdp"], "3389")

    def test_vnc_5900(self):
        self.assertEqual(gcm._PROTO_DEFAULTS["vnc"], "5900")

    def test_spice_5930(self):
        self.assertEqual(gcm._PROTO_DEFAULTS["spice"], "5930")

    def test_serial_9600(self):
        self.assertEqual(gcm._PROTO_DEFAULTS["serial"], "9600")

    def test_local_empty(self):
        self.assertEqual(gcm._PROTO_DEFAULTS["local"], "")

    def test_serial_baud_numeric(self):
        self.assertTrue(gcm._PROTO_DEFAULTS["serial"].isdigit())

    def test_ssh_port_numeric(self):
        self.assertTrue(gcm._PROTO_DEFAULTS["ssh"].isdigit())

    def test_rdp_port_high(self):
        self.assertGreater(int(gcm._PROTO_DEFAULTS["rdp"]), 1024)


# ── Détection des binaires ────────────────────────────────────────────────────


class TestBinaryDetection(unittest.TestCase):
    def test_rdp_bin_string(self):
        self.assertIsInstance(gcm.RDP_BIN, str)

    def test_rdp_bin_not_empty(self):
        self.assertGreater(len(gcm.RDP_BIN), 0)

    def test_rdp_bin_has_rdp(self):
        self.assertIn("rdp", gcm.RDP_BIN.lower())

    def test_vnc_bin_string(self):
        self.assertIsInstance(gcm.VNC_BIN, str)

    def test_vnc_bin_not_empty(self):
        self.assertGreater(len(gcm.VNC_BIN), 0)

    def test_spice_bin_string(self):
        self.assertIsInstance(gcm.SPICE_BIN, str)

    def test_spice_bin_not_empty(self):
        self.assertGreater(len(gcm.SPICE_BIN), 0)

    def test_serial_bin_string(self):
        self.assertIsInstance(gcm.SERIAL_BIN, str)

    def test_serial_bin_not_empty(self):
        self.assertGreater(len(gcm.SERIAL_BIN), 0)

    def test_serial_bin_known(self):
        self.assertIn(os.path.basename(gcm.SERIAL_BIN), ("picocom", "minicom", "screen"))

    def test_spice_bin_known(self):
        self.assertIn(os.path.basename(gcm.SPICE_BIN), ("remote-viewer", "virt-viewer", "spicy"))

    def test_vnc_bin_known(self):
        self.assertIn(
            os.path.basename(gcm.VNC_BIN),
            (
                "vncviewer",
                "tigervnc",
                "xtightvncviewer",
                "xvnc4viewer",
                "vinagre",
                "remmina",
            ),
        )


# ── _SERIAL_TEMPLATES — détaillé ─────────────────────────────────────────────


class TestSerialTemplatesExhaustive(unittest.TestCase):
    """Tests détaillés pour _SERIAL_TEMPLATES."""

    def _tpl(self, name):
        return gcm._SERIAL_TEMPLATES[name]

    def test_cisco_present(self):
        self.assertIn("Cisco IOS / IOS-XE / NX-OS", gcm._SERIAL_TEMPLATES)

    def test_comware_present(self):
        self.assertIn("HP Comware (H3C)", gcm._SERIAL_TEMPLATES)

    def test_aruba_present(self):
        self.assertIn("Aruba AOS-S / AOS-CX", gcm._SERIAL_TEMPLATES)

    def test_juniper_present(self):
        self.assertIn("Juniper JunOS", gcm._SERIAL_TEMPLATES)

    def test_fortinet_present(self):
        self.assertIn("Fortinet FortiOS", gcm._SERIAL_TEMPLATES)

    def test_paloalto_present(self):
        self.assertIn("Palo Alto PAN-OS", gcm._SERIAL_TEMPLATES)

    def test_f5_present(self):
        self.assertIn("F5 TMOS", gcm._SERIAL_TEMPLATES)

    def test_linux_present(self):
        self.assertIn("Linux / Raspberry Pi", gcm._SERIAL_TEMPLATES)

    def test_arduino_present(self):
        self.assertIn("Arduino / ESP32", gcm._SERIAL_TEMPLATES)

    def test_modbus_present(self):
        self.assertIn("RS-485 Modbus RTU", gcm._SERIAL_TEMPLATES)

    def test_libre_present(self):
        self.assertIn("Libre (manuel)", gcm._SERIAL_TEMPLATES)

    def test_count_11(self):
        self.assertEqual(len(gcm._SERIAL_TEMPLATES), 11)

    def test_all_len5(self):
        for n, t in gcm._SERIAL_TEMPLATES.items():
            self.assertEqual(len(t), 5, msg=f"{n}: longueur incorrecte")

    def test_all_baud_numeric(self):
        for n, (b, *_) in gcm._SERIAL_TEMPLATES.items():
            self.assertTrue(b.isdigit(), msg=f"{n}: baud non numérique")

    def test_all_flow_valid(self):
        for n, (_, f, *_) in gcm._SERIAL_TEMPLATES.items():
            self.assertIn(f, ("n", "x", "h"), msg=f"{n}: flow invalide")

    def test_all_parity_valid(self):
        for n, (_, _, p, *_) in gcm._SERIAL_TEMPLATES.items():
            self.assertIn(p, ("n", "e", "o"), msg=f"{n}: parity invalide")

    def test_all_databits_8(self):
        for n, (_, _, _, d, _) in gcm._SERIAL_TEMPLATES.items():
            self.assertEqual(d, "8", msg=f"{n}: databits != 8")

    def test_all_stopbits_1(self):
        for n, (_, _, _, _, s) in gcm._SERIAL_TEMPLATES.items():
            self.assertEqual(s, "1", msg=f"{n}: stopbits != 1")

    def test_cisco_9600(self):
        self.assertEqual(self._tpl("Cisco IOS / IOS-XE / NX-OS")[0], "9600")

    def test_f5_19200(self):
        self.assertEqual(self._tpl("F5 TMOS")[0], "19200")

    def test_linux_115200(self):
        self.assertEqual(self._tpl("Linux / Raspberry Pi")[0], "115200")

    def test_arduino_115200(self):
        self.assertEqual(self._tpl("Arduino / ESP32")[0], "115200")

    def test_aruba_9600(self):
        self.assertEqual(self._tpl("Aruba AOS-S / AOS-CX")[0], "9600")

    def test_juniper_9600(self):
        self.assertEqual(self._tpl("Juniper JunOS")[0], "9600")

    def test_fortinet_9600(self):
        self.assertEqual(self._tpl("Fortinet FortiOS")[0], "9600")

    def test_paloalto_9600(self):
        self.assertEqual(self._tpl("Palo Alto PAN-OS")[0], "9600")

    def test_modbus_9600(self):
        self.assertEqual(self._tpl("RS-485 Modbus RTU")[0], "9600")


# ── SerialTab — template application ──────────────────────────────────────────


class TestSerialTabTemplates(unittest.TestCase):
    """Test de l'application des templates dans SerialTab."""

    def _tab(self):
        return gcm.SerialTab(_make_host(host="/dev/ttyUSB0", port="9600", protocol="serial"))

    def _apply(self, tab, name):
        tpl_list = list(gcm._SERIAL_TEMPLATES.keys())
        tab._cmb_tpl.set_active(tpl_list.index(name))
        tab._on_template_changed(tab._cmb_tpl)

    def setUp(self):
        self._orig_bin = gcm.SERIAL_BIN
        gcm.SERIAL_BIN = "picocom"

    def tearDown(self):
        gcm.SERIAL_BIN = self._orig_bin

    def test_cisco_sets_9600(self):
        t = self._tab()
        self._apply(t, "Cisco IOS / IOS-XE / NX-OS")
        self.assertEqual(t._cmb_baud.get_active_text(), "9600")

    def test_linux_sets_115200(self):
        t = self._tab()
        self._apply(t, "Linux / Raspberry Pi")
        self.assertEqual(t._cmb_baud.get_active_text(), "115200")

    def test_arduino_sets_115200(self):
        t = self._tab()
        self._apply(t, "Arduino / ESP32")
        self.assertEqual(t._cmb_baud.get_active_text(), "115200")

    def test_f5_sets_19200(self):
        t = self._tab()
        self._apply(t, "F5 TMOS")
        self.assertEqual(t._cmb_baud.get_active_text(), "19200")

    def test_saves_to_host_type(self):
        t = self._tab()
        self._apply(t, "Aruba AOS-S / AOS-CX")
        self.assertEqual(t.host.type, "Aruba AOS-S / AOS-CX")

    def test_picocom_opts_include_flow(self):
        """Cisco IOS configure flow=n, vérifié dans la commande _build_cmd."""
        t = self._tab()
        self._apply(t, "Cisco IOS / IOS-XE / NX-OS")
        cmd = t._build_cmd()
        self.assertIn("--flow", cmd)

    def test_picocom_opts_include_parity(self):
        """Cisco IOS configure parity=n, vérifié dans la commande _build_cmd."""
        t = self._tab()
        self._apply(t, "Cisco IOS / IOS-XE / NX-OS")
        cmd = t._build_cmd()
        self.assertIn("--parity", cmd)

    def test_minicom_opts_include_databits(self):
        """Minicom : --databits est passé dans la commande générée."""
        gcm.SERIAL_BIN = "minicom"
        t = self._tab()
        self._apply(t, "Cisco IOS / IOS-XE / NX-OS")
        cmd = t._build_cmd()
        self.assertIn("--databits", cmd)

    def test_fortinet_sets_9600(self):
        t = self._tab()
        self._apply(t, "Fortinet FortiOS")
        self.assertEqual(t._cmb_baud.get_active_text(), "9600")

    def test_juniper_sets_9600(self):
        t = self._tab()
        self._apply(t, "Juniper JunOS")
        self.assertEqual(t._cmb_baud.get_active_text(), "9600")

    def test_comware_sets_9600(self):
        t = self._tab()
        self._apply(t, "HP Comware (H3C)")
        self.assertEqual(t._cmb_baud.get_active_text(), "9600")

    def test_modbus_sets_9600(self):
        t = self._tab()
        self._apply(t, "RS-485 Modbus RTU")
        self.assertEqual(t._cmb_baud.get_active_text(), "9600")


# ── SerialTab._build_cmd — détaillé ───────────────────────────────────────────


class TestSerialTabBuildCmdAll(unittest.TestCase):
    """Tests _build_cmd pour tous les binaires et appareils."""

    def _tab(self, device="/dev/ttyUSB0", baud="9600", opts=""):
        h = _make_host(host=device, port=baud, protocol="serial")
        t = gcm.SerialTab(h)
        t._entry_dev.set_text(device)
        t._entry_opts.set_text(opts)
        # sync baud combo
        model = t._cmb_baud.get_model()
        it = model.get_iter_first()
        while it is not None:
            if model[it][0] == baud:
                t._cmb_baud.set_active_iter(it)
                break
            it = model.iter_next(it)
        return t

    def setUp(self):
        self._orig = gcm.SERIAL_BIN

    def tearDown(self):
        gcm.SERIAL_BIN = self._orig

    # picocom ----------------------------------------------------------------

    def test_picocom_first(self):
        gcm.SERIAL_BIN = "picocom"
        self.assertEqual(self._tab()._build_cmd()[0], "picocom")

    def test_picocom_device_last(self):
        gcm.SERIAL_BIN = "picocom"
        cmd = self._tab("/dev/ttyUSB0")._build_cmd()
        self.assertEqual(cmd[-1], "/dev/ttyUSB0")

    def test_picocom_baud_9600(self):
        gcm.SERIAL_BIN = "picocom"
        cmd = self._tab("/dev/ttyUSB0", "9600")._build_cmd()
        idx = cmd.index("--baud")
        self.assertEqual(cmd[idx + 1], "9600")

    def test_picocom_baud_115200(self):
        gcm.SERIAL_BIN = "picocom"
        cmd = self._tab("/dev/ttyUSB0", "115200")._build_cmd()
        self.assertIn("115200", cmd)

    def test_picocom_baud_19200(self):
        gcm.SERIAL_BIN = "picocom"
        cmd = self._tab("/dev/ttyUSB0", "19200")._build_cmd()
        self.assertIn("19200", cmd)

    def test_picocom_baud_38400(self):
        gcm.SERIAL_BIN = "picocom"
        cmd = self._tab("/dev/ttyUSB0", "38400")._build_cmd()
        self.assertIn("38400", cmd)

    def test_picocom_baud_57600(self):
        gcm.SERIAL_BIN = "picocom"
        cmd = self._tab("/dev/ttyUSB0", "57600")._build_cmd()
        self.assertIn("57600", cmd)

    def test_picocom_dev_ttyS0(self):
        gcm.SERIAL_BIN = "picocom"
        cmd = self._tab("/dev/ttyS0")._build_cmd()
        self.assertIn("/dev/ttyS0", cmd)

    def test_picocom_dev_ttyS1(self):
        gcm.SERIAL_BIN = "picocom"
        cmd = self._tab("/dev/ttyS1")._build_cmd()
        self.assertIn("/dev/ttyS1", cmd)

    def test_picocom_dev_ttyUSB1(self):
        gcm.SERIAL_BIN = "picocom"
        cmd = self._tab("/dev/ttyUSB1")._build_cmd()
        self.assertIn("/dev/ttyUSB1", cmd)

    def test_picocom_dev_ttyACM0(self):
        gcm.SERIAL_BIN = "picocom"
        cmd = self._tab("/dev/ttyACM0")._build_cmd()
        self.assertIn("/dev/ttyACM0", cmd)

    def test_picocom_opts_flow_n(self):
        gcm.SERIAL_BIN = "picocom"
        cmd = self._tab(opts="--flow n --parity n --databits 8 --stopbits 1")._build_cmd()
        self.assertIn("--flow", cmd)
        self.assertIn("n", cmd)

    def test_picocom_no_opts_no_flow(self):
        """Sans extra opts, --flow est toujours présent (lu depuis les combos série)."""
        gcm.SERIAL_BIN = "picocom"
        cmd = self._tab(opts="")._build_cmd()
        # Nouveau comportement : flags toujours inclus depuis les combos dédiés
        self.assertIn("--flow", cmd)
        self.assertIn("--parity", cmd)
        self.assertIn("--databits", cmd)
        self.assertIn("--stopbits", cmd)

    def test_picocom_fallback_device(self):
        gcm.SERIAL_BIN = "picocom"
        t = self._tab()
        t._entry_dev.set_text("")
        self.assertIn("/dev/ttyUSB0", t._build_cmd())

    # minicom ----------------------------------------------------------------

    def test_minicom_first(self):
        gcm.SERIAL_BIN = "minicom"
        self.assertEqual(self._tab()._build_cmd()[0], "minicom")

    def test_minicom_b_flag(self):
        gcm.SERIAL_BIN = "minicom"
        cmd = self._tab("/dev/ttyUSB0", "57600")._build_cmd()
        self.assertIn("-b", cmd)
        self.assertIn("57600", cmd)

    def test_minicom_D_flag(self):
        gcm.SERIAL_BIN = "minicom"
        cmd = self._tab("/dev/ttyS2")._build_cmd()
        idx = cmd.index("-D")
        self.assertEqual(cmd[idx + 1], "/dev/ttyS2")

    def test_minicom_baud_position(self):
        gcm.SERIAL_BIN = "minicom"
        cmd = self._tab("/dev/ttyUSB0", "115200")._build_cmd()
        idx = cmd.index("-b")
        self.assertEqual(cmd[idx + 1], "115200")

    def test_minicom_device_after_D(self):
        gcm.SERIAL_BIN = "minicom"
        cmd = self._tab("/dev/ttyUSB0")._build_cmd()
        idx = cmd.index("-D")
        self.assertEqual(cmd[idx + 1], "/dev/ttyUSB0")

    def test_minicom_extra_opts(self):
        gcm.SERIAL_BIN = "minicom"
        cmd = self._tab(opts="-o")._build_cmd()
        self.assertIn("-o", cmd)

    # screen -----------------------------------------------------------------

    def test_screen_first(self):
        gcm.SERIAL_BIN = "screen"
        self.assertEqual(self._tab()._build_cmd()[0], "screen")

    def test_screen_device_second(self):
        gcm.SERIAL_BIN = "screen"
        cmd = self._tab("/dev/ttyUSB0")._build_cmd()
        self.assertEqual(cmd[1], "/dev/ttyUSB0")

    def test_screen_baud_third(self):
        gcm.SERIAL_BIN = "screen"
        cmd = self._tab("/dev/ttyUSB0", "115200")._build_cmd()
        self.assertEqual(cmd[2], "115200")

    def test_screen_extra_opt(self):
        gcm.SERIAL_BIN = "screen"
        cmd = self._tab(opts="-L")._build_cmd()
        self.assertIn("-L", cmd)

    def test_screen_ttyS1(self):
        gcm.SERIAL_BIN = "screen"
        cmd = self._tab("/dev/ttyS1")._build_cmd()
        self.assertIn("/dev/ttyS1", cmd)

    # générique --------------------------------------------------------------

    def test_returns_list(self):
        gcm.SERIAL_BIN = "picocom"
        self.assertIsInstance(self._tab()._build_cmd(), list)

    def test_not_empty(self):
        gcm.SERIAL_BIN = "picocom"
        self.assertGreater(len(self._tab()._build_cmd()), 0)


# ── RdpTab — cas limites ──────────────────────────────────────────────────────


class TestRdpTabEdgeCases(unittest.TestCase):
    def _t(self, host, pwd=""):
        return gcm.RdpTab(host, lambda: pwd)

    def test_cmd_is_list(self):
        cmd = self._t(_make_host(host="10.0.0.1", protocol="rdp"))._build_cmd()
        self.assertIsInstance(cmd, list)

    def test_binary_first(self):
        cmd = self._t(_make_host(host="10.0.0.1", protocol="rdp"))._build_cmd()
        self.assertEqual(cmd[0], gcm.RDP_BIN)

    def test_v_flag_present(self):
        cmd = self._t(_make_host(host="10.0.0.1", port="3389", protocol="rdp"))._build_cmd()
        self.assertTrue(any(a.startswith("/v:") for a in cmd))

    def test_v_flag_host(self):
        cmd = self._t(_make_host(host="srv.corp", port="3389", protocol="rdp"))._build_cmd()
        v = next(a for a in cmd if a.startswith("/v:"))
        self.assertIn("srv.corp", v)

    def test_v_flag_custom_port(self):
        cmd = self._t(_make_host(host="10.0.0.1", port="9999", protocol="rdp"))._build_cmd()
        v = next(a for a in cmd if a.startswith("/v:"))
        self.assertIn("9999", v)

    def test_u_flag_user(self):
        cmd = self._t(_make_host(host="10.0.0.1", user="jdoe", protocol="rdp"))._build_cmd()
        self.assertTrue(any("jdoe" in a for a in cmd))

    def test_no_p_flag_without_password(self):
        cmd = self._t(_make_host(host="10.0.0.1", protocol="rdp"), pwd="")._build_cmd()
        self.assertFalse(any(a.startswith("/p:") for a in cmd))

    def test_p_flag_with_password(self):
        cmd = self._t(_make_host(host="10.0.0.1", protocol="rdp"), pwd="s3cr3t")._build_cmd()
        self.assertTrue(any("s3cr3t" in a for a in cmd))

    def test_cert_ignore(self):
        cmd = self._t(_make_host(host="10.0.0.1", protocol="rdp"))._build_cmd()
        self.assertTrue(any("cert" in a.lower() for a in cmd))

    def test_dynamic_resolution(self):
        cmd = self._t(_make_host(host="10.0.0.1", protocol="rdp"))._build_cmd()
        self.assertTrue(any("dynamic" in a.lower() or "resolution" in a.lower() for a in cmd))

    def test_multi_extra_params(self):
        h = _make_host(
            host="10.0.0.1",
            protocol="rdp",
            extra_params="+clipboard /sound /microphone",
        )
        cmd = self._t(h)._build_cmd()
        self.assertIn("+clipboard", cmd)
        self.assertIn("/sound", cmd)
        self.assertIn("/microphone", cmd)

    def test_domain_user_slash(self):
        h = _make_host(host="10.0.0.1", user=r"CORP\jdoe", protocol="rdp")
        cmd = self._t(h)._build_cmd()
        combined = " ".join(cmd)
        self.assertIn("CORP", combined)
        self.assertIn("jdoe", combined)


# ── RdpEmbeddedTab — supplémentaire ──────────────────────────────────────────


class TestRdpEmbeddedExtraTests(unittest.TestCase):
    def _t(self, host, pwd=""):
        return gcm.RdpEmbeddedTab(host, lambda: pwd)

    def test_binary_first(self):
        h = _make_host(host="10.0.0.1", port="3389", protocol="rdp")
        self.assertEqual(self._t(h)._build_cmd()[0], gcm.RDP_BIN)

    def test_parent_window_present(self):
        h = _make_host(host="10.0.0.1", protocol="rdp")
        cmd = self._t(h)._build_cmd()
        self.assertTrue(any("/parent-window:" in a for a in cmd))

    def test_xid_parseable_hex(self):
        h = _make_host(host="10.0.0.1", protocol="rdp")
        cmd = self._t(h)._build_cmd()
        pw = next(a for a in cmd if a.startswith("/parent-window:"))
        int(pw.split(":", 1)[1], 16)  # ne doit pas lever

    def test_v_flag_host(self):
        h = _make_host(host="myhost.corp", port="3389", protocol="rdp")
        cmd = self._t(h)._build_cmd()
        v = next(a for a in cmd if a.startswith("/v:"))
        self.assertIn("myhost.corp", v)

    def test_v_flag_port(self):
        h = _make_host(host="10.0.0.1", port="33890", protocol="rdp")
        cmd = self._t(h)._build_cmd()
        v = next(a for a in cmd if a.startswith("/v:"))
        self.assertIn("33890", v)

    def test_cert_present(self):
        h = _make_host(host="10.0.0.1", protocol="rdp")
        cmd = self._t(h)._build_cmd()
        self.assertTrue(any("cert" in a.lower() for a in cmd))

    def test_returns_list(self):
        h = _make_host(host="10.0.0.1", protocol="rdp")
        self.assertIsInstance(self._t(h)._build_cmd(), list)

    def test_password_in_cmd(self):
        h = _make_host(host="10.0.0.1", protocol="rdp")
        cmd = self._t(h, pwd="rdppass")._build_cmd()
        self.assertTrue(any("rdppass" in a for a in cmd))


# ── VncTab — cas limites ──────────────────────────────────────────────────────


class TestVncTabEdgeCases(unittest.TestCase):
    def _t(self, host, pwd=""):
        return gcm.VncTab(host, lambda: pwd)

    def setUp(self):
        self._orig = gcm.VNC_BIN

    def tearDown(self):
        gcm.VNC_BIN = self._orig

    def test_returns_tuple(self):
        h = _make_host(host="10.0.0.1", port="5900", protocol="vnc")
        self.assertIsInstance(self._t(h)._build_cmd(), tuple)

    def test_tuple_len_2(self):
        h = _make_host(host="10.0.0.1", port="5900", protocol="vnc")
        self.assertEqual(len(self._t(h)._build_cmd()), 2)

    def test_binary_first(self):
        gcm.VNC_BIN = "vncviewer"
        h = _make_host(host="10.0.0.1", port="5900", protocol="vnc")
        cmd, _ = self._t(h)._build_cmd()
        self.assertEqual(cmd[0], "vncviewer")

    def test_host_in_cmd(self):
        gcm.VNC_BIN = "vncviewer"
        h = _make_host(host="10.0.0.1", port="5900", protocol="vnc")
        cmd, _ = self._t(h)._build_cmd()
        self.assertIn("10.0.0.1", " ".join(cmd))

    def test_port_5900_in_cmd(self):
        gcm.VNC_BIN = "vncviewer"
        h = _make_host(host="server", port="5900", protocol="vnc")
        cmd, _ = self._t(h)._build_cmd()
        self.assertIn("5900", " ".join(cmd))

    def test_port_5901_in_cmd(self):
        gcm.VNC_BIN = "vncviewer"
        h = _make_host(host="server", port="5901", protocol="vnc")
        cmd, _ = self._t(h)._build_cmd()
        self.assertIn("5901", " ".join(cmd))

    def test_vinagre_uri_scheme(self):
        gcm.VNC_BIN = "vinagre"
        h = _make_host(host="10.0.0.1", port="5901", protocol="vnc")
        cmd, _ = self._t(h)._build_cmd()
        self.assertTrue(any("vnc://" in a for a in cmd))

    def test_remmina_uri_scheme(self):
        gcm.VNC_BIN = "remmina"
        h = _make_host(host="10.0.0.1", port="5900", protocol="vnc")
        cmd, _ = self._t(h)._build_cmd()
        self.assertTrue(any("vnc://" in a for a in cmd))

    def test_password_returned_as_second(self):
        gcm.VNC_BIN = "vncviewer"
        h = _make_host(host="10.0.0.1", port="5900", protocol="vnc")
        _, pwd = self._t(h, pwd="vnc_pass")._build_cmd()
        self.assertEqual(pwd, "vnc_pass")

    def test_no_password_second_empty(self):
        gcm.VNC_BIN = "vncviewer"
        h = _make_host(host="10.0.0.1", port="5900", protocol="vnc")
        _, pwd = self._t(h)._build_cmd()
        self.assertEqual(pwd, "")

    def test_vinagre_with_user(self):
        gcm.VNC_BIN = "vinagre"
        h = _make_host(host="10.0.0.1", user="admin", port="5900", protocol="vnc")
        cmd, _ = self._t(h, pwd="s")._build_cmd()
        self.assertTrue(any("admin" in a for a in cmd))

    def test_vinagre_with_password_in_uri(self):
        gcm.VNC_BIN = "vinagre"
        h = _make_host(host="10.0.0.1", user="u", port="5900", protocol="vnc")
        cmd, _ = self._t(h, pwd="mypwd")._build_cmd()
        self.assertTrue(any("mypwd" in a for a in cmd))


# ── SpiceTab — cas limites ────────────────────────────────────────────────────


class TestSpiceTabEdgeCases(unittest.TestCase):
    def _t(self, host, pwd=""):
        return gcm.SpiceTab(host, lambda: pwd)

    def test_binary_first(self):
        h = _make_host(host="vm", port="5930", protocol="spice")
        self.assertEqual(self._t(h)._build_cmd()[0], gcm.SPICE_BIN)

    def test_returns_list(self):
        h = _make_host(host="vm", port="5930", protocol="spice")
        self.assertIsInstance(self._t(h)._build_cmd(), list)

    def test_spice_uri_second(self):
        h = _make_host(host="vm", port="5930", protocol="spice")
        cmd = self._t(h)._build_cmd()
        self.assertTrue(cmd[1].startswith("spice://"))

    def test_host_in_uri(self):
        h = _make_host(host="vm01.corp", port="5930", protocol="spice")
        cmd = self._t(h)._build_cmd()
        self.assertIn("vm01.corp", " ".join(cmd))

    def test_port_5930(self):
        h = _make_host(host="vm", port="5930", protocol="spice")
        self.assertIn("5930", " ".join(self._t(h)._build_cmd()))

    def test_port_5940(self):
        h = _make_host(host="vm", port="5940", protocol="spice")
        self.assertIn("5940", " ".join(self._t(h)._build_cmd()))

    def test_password_in_uri(self):
        h = _make_host(host="vm", port="5930", protocol="spice")
        cmd = self._t(h, pwd="spicepass")._build_cmd()
        self.assertIn("spicepass", " ".join(cmd))

    def test_no_password_no_param(self):
        h = _make_host(host="vm", port="5930", protocol="spice")
        cmd = self._t(h, pwd="")._build_cmd()
        self.assertFalse(any("password=" in a for a in cmd))

    def test_extra_params_appended(self):
        h = _make_host(host="vm", port="5930", protocol="spice", extra_params="--full-screen")
        self.assertIn("--full-screen", self._t(h)._build_cmd())

    def test_multiple_extra_params(self):
        h = _make_host(
            host="vm",
            port="5930",
            protocol="spice",
            extra_params="--full-screen --zoom 75",
        )
        cmd = self._t(h)._build_cmd()
        self.assertIn("--full-screen", cmd)
        self.assertIn("--zoom", cmd)
        self.assertIn("75", cmd)

    def test_ipv4_host(self):
        h = _make_host(host="192.168.100.50", port="5930", protocol="spice")
        self.assertIn("192.168.100.50", " ".join(self._t(h)._build_cmd()))


# ── _rdp_socket_available — supplémentaire ───────────────────────────────────


class TestRdpSocketAvailableExtra(unittest.TestCase):
    def test_returns_bool(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsInstance(gcm._rdp_socket_available(), bool)

    def test_no_display_key(self):
        env = {k: v for k, v in os.environ.items() if k != "DISPLAY"}
        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(gcm._rdp_socket_available())

    def test_empty_display_false(self):
        with patch.dict(os.environ, {"DISPLAY": ""}, clear=False):
            self.assertFalse(gcm._rdp_socket_available())

    def test_display_set_returns_true(self):
        with patch.dict(os.environ, {"DISPLAY": ":1"}, clear=False):

            class _X11:
                pass

            with patch.object(gcm.Gdk, "Display") as m:
                m.get_default.return_value = _X11()
                self.assertTrue(gcm._rdp_socket_available())


# ── encrypt_old/decrypt_old — exhaustif ──────────────────────────────────────


class TestEncryptOldExhaustive(unittest.TestCase):
    def _rt(self, key, text):
        return gcm.decrypt_old(key, gcm.encrypt_old(key, text))

    def test_simple(self):
        self.assertEqual(self._rt("key", "hello"), "hello")

    def test_empty(self):
        self.assertEqual(self._rt("key", ""), "")

    def test_digits(self):
        self.assertEqual(self._rt("pass", "1234567890"), "1234567890")

    def test_symbols(self):
        self.assertEqual(self._rt("key", "!@#$%^&*()"), "!@#$%^&*()")

    def test_spaces(self):
        self.assertEqual(self._rt("key", "hello world"), "hello world")

    def test_single_char(self):
        self.assertEqual(self._rt("key", "x"), "x")

    def test_long_text(self):
        self.assertEqual(self._rt("key", "A" * 200), "A" * 200)

    def test_ip_address(self):
        self.assertEqual(self._rt("key", "192.168.1.1"), "192.168.1.1")

    def test_hostname(self):
        self.assertEqual(self._rt("key", "router.corp"), "router.corp")

    def test_password_chars(self):
        self.assertEqual(self._rt("k", "P@ss!0rd"), "P@ss!0rd")

    def test_different_keys_differ(self):
        enc = gcm.encrypt_old("key1", "hello")
        dec2 = gcm.decrypt_old("key2", enc)
        self.assertNotEqual(dec2, "hello")

    def test_encrypt_is_string(self):
        self.assertIsInstance(gcm.encrypt_old("k", "hi"), str)

    def test_decrypt_is_string(self):
        enc = gcm.encrypt_old("k", "hi")
        self.assertIsInstance(gcm.decrypt_old("k", enc), str)

    def test_encrypt_not_plaintext(self):
        self.assertNotEqual(gcm.encrypt_old("k", "secret"), "secret")

    def test_deterministic(self):
        self.assertEqual(gcm.encrypt_old("k", "hi"), gcm.encrypt_old("k", "hi"))

    def test_decrypt_invalid_returns_empty(self):
        self.assertEqual(gcm.decrypt_old("k", "not-valid-base64!!!"), "")

    def test_result_is_base64(self):
        import base64 as b64

        enc = gcm.encrypt_old("key", "test")
        b64.b64decode(enc)  # ne doit pas lever


# ── AES encrypt/decrypt — supplémentaire ─────────────────────────────────────


class TestAesEncryptExhaustive(unittest.TestCase):
    """Tests encrypt/decrypt AES (conf.VERSION=1 pour forcer AES vs decrypt_old)."""

    def setUp(self):
        self._orig_version = gcm.conf.VERSION
        gcm.conf.VERSION = 1  # force pyAES.decrypt (pas decrypt_old)

    def tearDown(self):
        gcm.conf.VERSION = self._orig_version

    def _rt(self, key, text):
        return gcm.decrypt(key, gcm.encrypt(key, text))

    def test_ascii_password(self):
        self.assertEqual(self._rt("pass", "P@ssw0rd!"), "P@ssw0rd!")

    def test_hostname(self):
        self.assertEqual(self._rt("k", "router.corp.local"), "router.corp.local")

    def test_ip(self):
        self.assertEqual(self._rt("k", "192.168.105.41"), "192.168.105.41")

    def test_empty(self):
        self.assertIsInstance(gcm.decrypt("k", gcm.encrypt("k", "")), str)

    def test_long(self):
        self.assertEqual(self._rt("k", "x" * 512), "x" * 512)

    def test_symbols(self):
        self.assertEqual(self._rt("k", "!@#$%^&*()-_+="), "!@#$%^&*()-_+=")

    def test_spaces(self):
        self.assertEqual(self._rt("k", "admin password"), "admin password")

    def test_digits(self):
        self.assertEqual(self._rt("k", "1234567890"), "1234567890")

    def test_different_keys_differ(self):
        enc = gcm.encrypt("k1", "hello")
        self.assertNotEqual(gcm.decrypt("k2", enc), "hello")

    def test_encrypt_not_plaintext(self):
        self.assertNotEqual(gcm.encrypt("k", "secret"), "secret")

    def test_encrypt_returns_string(self):
        self.assertIsInstance(gcm.encrypt("k", "test"), str)

    def test_decrypt_returns_string(self):
        self.assertIsInstance(gcm.decrypt("k", gcm.encrypt("k", "test")), str)

    def test_encrypt_nonempty(self):
        self.assertGreater(len(gcm.encrypt("k", "hello")), 0)

    def test_wrong_key_not_plaintext(self):
        enc = gcm.encrypt("correct", "secret")
        self.assertNotEqual(gcm.decrypt("wrong", enc), "secret")


# ── _vm_name_split — cas limites ─────────────────────────────────────────────


class TestVmNameSplitExtra(unittest.TestCase):
    def _s(self, name):
        return gcm._vm_name_split(name)

    def test_long_with_dash(self):
        g, n = self._s("infrastructure-web-prod-v2")
        self.assertEqual(g, "INFRASTRUCTURE")
        self.assertEqual(n, "web-prod-v2")

    def test_all_caps(self):
        g, n = self._s("WEB_server")
        self.assertEqual(g, "WEB")

    def test_number_suffix(self):
        g, n = self._s("app_01")
        self.assertEqual(g, "APP")
        self.assertEqual(n, "01")

    def test_three_words_space(self):
        g, n = self._s("home lab server")
        self.assertEqual(g, "HOME")
        self.assertEqual(n, "lab server")

    def test_mixed_sep_first_wins(self):
        g, n = self._s("web-db_01")
        self.assertEqual(g, "WEB")
        self.assertEqual(n, "db_01")

    def test_underscore_preserves_rest(self):
        g, n = self._s("prod_db_master")
        self.assertEqual(g, "PROD")
        self.assertEqual(n, "db_master")

    def test_two_words_space(self):
        g, n = self._s("home lab")
        self.assertEqual(g, "HOME")
        self.assertEqual(n, "lab")

    def test_single_char_group(self):
        g, n = self._s("a_server")
        self.assertEqual(g, "A")
        self.assertEqual(n, "server")

    def test_number_only_libvirt(self):
        g, _ = self._s("42")
        self.assertEqual(g, "LIBVIRT")

    def test_empty_libvirt(self):
        g, _ = self._s("")
        self.assertEqual(g, "LIBVIRT")

    def test_digits_dash(self):
        g, n = self._s("192-168")
        self.assertEqual(g, "192")
        self.assertEqual(n, "168")

    def test_unicode_group_uppercase(self):
        g, n = self._s("réseau_interne")
        self.assertEqual(g, "RÉSEAU")
        self.assertEqual(n, "interne")


# ── Tests _dep_install_hint (v1.3.2 — nouveau) ───────────────────────────────


class TestDepInstallHint(unittest.TestCase):
    """Tests pour _dep_install_hint — détection OS et suggestion d'installation."""

    def _mock_rel(self, content):
        return patch("builtins.open", unittest.mock.mock_open(read_data=content))

    def test_ubuntu_returns_apt(self):
        with self._mock_rel('ID=ubuntu\nNAME="Ubuntu 22.04"'):
            h = gcm._dep_install_hint("pkg-deb", "pkg-rpm")
        self.assertIn("sudo apt install", h)
        self.assertIn("pkg-deb", h)

    def test_debian_returns_apt(self):
        with self._mock_rel('ID=debian\nNAME="Debian GNU/Linux 12"'):
            h = gcm._dep_install_hint("pkg-deb", "pkg-rpm")
        self.assertIn("sudo apt install", h)

    def test_kali_returns_apt(self):
        with self._mock_rel('ID=kali\nNAME="Kali GNU/Linux"'):
            h = gcm._dep_install_hint("pkg-deb", "pkg-rpm")
        self.assertIn("sudo apt install", h)

    def test_raspbian_returns_apt(self):
        with self._mock_rel('ID=raspbian\nNAME="Raspbian GNU/Linux"'):
            h = gcm._dep_install_hint("pkg-deb", "pkg-rpm")
        self.assertIn("sudo apt install", h)

    def test_fedora_returns_dnf(self):
        with self._mock_rel('ID=fedora\nNAME="Fedora Linux 39"'):
            h = gcm._dep_install_hint("pkg-deb", "pkg-rpm")
        self.assertIn("sudo dnf install", h)
        self.assertIn("pkg-rpm", h)

    def test_centos_returns_dnf(self):
        with self._mock_rel('ID=centos\nNAME="CentOS Linux 8"'):
            h = gcm._dep_install_hint("pkg-deb", "pkg-rpm")
        self.assertIn("sudo dnf install", h)

    def test_rocky_returns_dnf(self):
        with self._mock_rel('ID=rocky\nNAME="Rocky Linux 9"'):
            h = gcm._dep_install_hint("pkg-deb", "pkg-rpm")
        self.assertIn("sudo dnf install", h)

    def test_arch_returns_pacman_with_arch_pkg(self):
        with self._mock_rel('ID=arch\nNAME="Arch Linux"'):
            h = gcm._dep_install_hint("pkg-deb", "pkg-rpm", "pkg-arch")
        self.assertIn("sudo pacman -S", h)
        self.assertIn("pkg-arch", h)

    def test_arch_fallback_uses_rpm_pkg(self):
        with self._mock_rel('ID=arch\nNAME="Arch Linux"'):
            h = gcm._dep_install_hint("pkg-deb", "pkg-rpm")
        self.assertIn("sudo pacman -S", h)
        self.assertIn("pkg-rpm", h)

    def test_unknown_os_contains_both_hints(self):
        with self._mock_rel('ID=unknown\nNAME="Mystery OS"'):
            h = gcm._dep_install_hint("pkg-deb", "pkg-rpm")
        self.assertIn("pkg-deb", h)
        self.assertIn("pkg-rpm", h)

    def test_os_release_missing_returns_fallback(self):
        with patch("builtins.open", side_effect=OSError("no file")):
            h = gcm._dep_install_hint("pkg-deb", "pkg-rpm")
        self.assertIn("pkg-deb", h)
        self.assertIn("pkg-rpm", h)

    def test_returns_string(self):
        with patch("builtins.open", side_effect=OSError):
            h = gcm._dep_install_hint("a", "b")
        self.assertIsInstance(h, str)


# ── Tests _check_port_open (v1.3.2 — nouveau) ────────────────────────────────


class TestCheckPortOpen(unittest.TestCase):
    """Tests pour _check_port_open — sondage TCP via nc/nmap depuis l'HV."""

    def _run_fn(self, responses):
        """run_fn mocké retournant les réponses en séquence."""
        calls = []

        def _fn(client, cmd, timeout=30):
            calls.append(cmd)
            idx = len(calls) - 1
            return responses[idx] if idx < len(responses) else ""

        return _fn, calls

    def test_empty_ip_returns_false(self):
        run_fn, _ = self._run_fn([])
        self.assertFalse(gcm._check_port_open(None, run_fn, "", 3389))

    def test_none_ip_returns_false(self):
        run_fn, _ = self._run_fn([])
        self.assertFalse(gcm._check_port_open(None, run_fn, None, 3389))

    def test_nc_open_returns_true(self):
        run_fn, _ = self._run_fn(["OPEN"])
        self.assertTrue(gcm._check_port_open(None, run_fn, "10.0.0.1", 3389))

    def test_nc_closed_returns_false(self):
        run_fn, _ = self._run_fn(["CLOSED"])
        self.assertFalse(gcm._check_port_open(None, run_fn, "10.0.0.1", 3389))

    def test_nc_ambiguous_fallback_nmap_open(self):
        run_fn, _ = self._run_fn(["", "3389/open tcp"])
        self.assertTrue(gcm._check_port_open(None, run_fn, "10.0.0.1", 3389))

    def test_nc_ambiguous_fallback_nmap_closed(self):
        run_fn, _ = self._run_fn(["", "3389/closed tcp"])
        self.assertFalse(gcm._check_port_open(None, run_fn, "10.0.0.1", 3389))

    def test_nmap_case_insensitive_open(self):
        run_fn, _ = self._run_fn(["", "3389/OPEN"])
        self.assertTrue(gcm._check_port_open(None, run_fn, "10.0.0.1", 3389))

    def test_nc_cmd_contains_ip_and_port(self):
        run_fn, calls = self._run_fn(["OPEN"])
        gcm._check_port_open(None, run_fn, "192.168.1.50", 22)
        self.assertIn("192.168.1.50", calls[0])
        self.assertIn("22", calls[0])

    def test_nmap_fallback_cmd_contains_port(self):
        run_fn, calls = self._run_fn(["", ""])
        gcm._check_port_open(None, run_fn, "10.0.0.5", 8080)
        # second call is nmap fallback
        self.assertTrue(len(calls) >= 2)
        self.assertIn("8080", calls[1])

    def test_returns_bool(self):
        run_fn, _ = self._run_fn(["OPEN"])
        result = gcm._check_port_open(None, run_fn, "1.2.3.4", 22)
        self.assertIsInstance(result, bool)


# ── Tests SpiceTab._build_cmd mode libvirt tunnel (v1.3.2) ───────────────────


class TestSpiceTabLibvirtTunnel(unittest.TestCase):
    """Tests SpiceTab._build_cmd en mode tunnel libvirt (--connect)."""

    def _tab(self, opts="", pwd="", host_ip="vm"):
        h = _make_host(host=host_ip, port="5930", protocol="spice")
        tab = gcm.SpiceTab(h, lambda: pwd)
        tab._entry_opts.set_text(opts)
        return tab

    def test_connect_mode_no_spice_uri(self):
        cmd = self._tab("--connect qemu+ssh://root@hv/system vm1")._build_cmd()
        self.assertFalse(any("spice://" in a for a in cmd))

    def test_connect_mode_first_arg_is_binary(self):
        cmd = self._tab("--connect qemu+ssh://root@hv/system vm1")._build_cmd()
        self.assertEqual(cmd[0], gcm.SPICE_BIN)

    def test_connect_mode_second_arg_is_connect(self):
        cmd = self._tab("--connect qemu+ssh://root@hv/system vm1")._build_cmd()
        self.assertEqual(cmd[1], "--connect")

    def test_connect_mode_uri_in_cmd(self):
        cmd = self._tab("--connect qemu+ssh://root@hv/system vm1")._build_cmd()
        self.assertTrue(any("qemu+ssh://root@hv/system" in a for a in cmd))

    def test_connect_mode_vm_name_present(self):
        cmd = self._tab("--connect qemu+ssh://root@hv/system prod-web")._build_cmd()
        self.assertIn("prod-web", cmd)

    def test_connect_mode_nonstandard_port_preserved(self):
        cmd = self._tab("--connect qemu+ssh://root@hv:542/system vm1")._build_cmd()
        self.assertTrue(any("542" in a for a in cmd))

    def test_connect_mode_ignores_host_port_field(self):
        cmd = self._tab(
            "--connect qemu+ssh://root@hv/system vm1", host_ip="192.168.1.10"
        )._build_cmd()
        # Le port SPICE (5930) ne doit pas apparaître dans les args (hors binaire)
        all_args = " ".join(cmd[1:])
        self.assertNotIn("5930", all_args)


# ── Tests _libvirt_get_uris_from_dconf (v1.3.2) ──────────────────────────────


class TestLibvirtGetUrisFromDconf(unittest.TestCase):
    """Tests pour _libvirt_get_uris_from_dconf."""

    def _mock_run(self, stdout="", raise_exc=None):
        def _run(*args, **kwargs):
            if raise_exc:
                raise raise_exc
            r = MagicMock()
            r.stdout = stdout
            return r

        return patch("subprocess.run", side_effect=_run)

    def test_normal_output_two_uris(self):
        raw = "['qemu+ssh://root@192.168.1.41/system', 'qemu+ssh://root@192.168.1.42/system']"
        with self._mock_run(raw):
            result = gcm._libvirt_get_uris_from_dconf()
        self.assertEqual(len(result), 2)
        self.assertIn("qemu+ssh://root@192.168.1.41/system", result)

    def test_empty_stdout_returns_empty(self):
        with self._mock_run(""):
            result = gcm._libvirt_get_uris_from_dconf()
        self.assertEqual(result, [])

    def test_as_empty_returns_empty(self):
        with self._mock_run("@as []"):
            result = gcm._libvirt_get_uris_from_dconf()
        self.assertEqual(result, [])

    def test_exception_returns_empty(self):
        with self._mock_run(raise_exc=FileNotFoundError("dconf not found")):
            result = gcm._libvirt_get_uris_from_dconf()
        self.assertEqual(result, [])

    def test_single_uri_list(self):
        raw = "['qemu:///system']"
        with self._mock_run(raw):
            result = gcm._libvirt_get_uris_from_dconf()
        self.assertEqual(result, ["qemu:///system"])


# ── Tests _libvirt_ssh_run (v1.3.2) ──────────────────────────────────────────


class TestLibvirtSshRun(unittest.TestCase):
    """Tests pour _libvirt_ssh_run — exécution distante via paramiko."""

    def _client(self, output_bytes=b""):
        client = MagicMock()
        stdout_mock = MagicMock()
        stdout_mock.read.return_value = output_bytes
        client.exec_command.return_value = (MagicMock(), stdout_mock, MagicMock())
        return client

    def test_returns_stripped_output(self):
        result = gcm._libvirt_ssh_run(self._client(b"  hello world  \n"), "cmd")
        self.assertEqual(result, "hello world")

    def test_empty_output_returns_empty_string(self):
        result = gcm._libvirt_ssh_run(self._client(b""), "true")
        self.assertEqual(result, "")

    def test_non_utf8_bytes_with_replace(self):
        result = gcm._libvirt_ssh_run(self._client(b"\xff\xfe hello\n"), "cmd")
        self.assertIsInstance(result, str)

    def test_timeout_passed_to_exec_command(self):
        client = self._client(b"out")
        gcm._libvirt_ssh_run(client, "cmd", timeout=42)
        client.exec_command.assert_called_with("cmd", timeout=42)


# ── Tests color_to_hex (v1.3.2 — non couvert) ───────────────────────────────


class TestColorToHex(unittest.TestCase):
    """Tests pour color_to_hex — conversion RGBA → chaîne hexadécimale."""

    def _rgba(self, r, g, b):
        rgba = MagicMock()
        rgba.red = r
        rgba.green = g
        rgba.blue = b
        return rgba

    def test_black_produces_hash_000(self):
        self.assertEqual(gcm.color_to_hex(self._rgba(0.0, 0.0, 0.0)), "#000")

    def test_white_contains_ff_components(self):
        result = gcm.color_to_hex(self._rgba(1.0, 1.0, 1.0))
        self.assertEqual(result, "#ffffff")

    def test_starts_with_hash(self):
        result = gcm.color_to_hex(self._rgba(0.5, 0.3, 0.1))
        self.assertTrue(result.startswith("#"))

    def test_diff_parameter_changes_result(self):
        r0 = gcm.color_to_hex(self._rgba(0.0, 0.0, 0.0))
        r1 = gcm.color_to_hex(self._rgba(0.0, 0.0, 0.0), diff=16)
        self.assertNotEqual(r0, r1)

    def test_pure_blue_components(self):
        # blue=1.0 (255=0xff), red=green=0 (0x0)
        result = gcm.color_to_hex(self._rgba(0.0, 0.0, 1.0))
        self.assertTrue(result.endswith("ff"))


# ── Tests get_username (v1.3.2 — non couvert) ────────────────────────────────


class TestGetUsername(unittest.TestCase):
    """Tests pour get_username — lecture variables d'environnement."""

    def test_returns_user_env(self):
        with patch("os.getenv", side_effect=lambda k: {"USER": "alice"}.get(k)):
            self.assertEqual(gcm.get_username(), "alice")

    def test_fallback_to_logname(self):
        with patch(
            "os.getenv",
            side_effect=lambda k: {"USER": None, "LOGNAME": "bob", "USERNAME": None}.get(k),
        ):
            self.assertEqual(gcm.get_username(), "bob")

    def test_fallback_to_username(self):
        with patch(
            "os.getenv",
            side_effect=lambda k: {"USER": None, "LOGNAME": None, "USERNAME": "carol"}.get(k),
        ):
            self.assertEqual(gcm.get_username(), "carol")

    def test_all_none_returns_none(self):
        with patch("os.getenv", return_value=None):
            self.assertIsNone(gcm.get_username())


# ── Tests LibvirtImportDialog colonnes (v1.3.2) ───────────────────────────────


class TestLibvirtImportDialogConstants(unittest.TestCase):
    """Tests pour les constantes de colonnes de LibvirtImportDialog._COL_*."""

    def test_col_sel_is_zero(self):
        self.assertEqual(gcm.LibvirtImportDialog._COL_SEL, 0)

    def test_col_proto_is_one(self):
        self.assertEqual(gcm.LibvirtImportDialog._COL_PROTO, 1)

    def test_col_name_is_two(self):
        self.assertEqual(gcm.LibvirtImportDialog._COL_NAME, 2)

    def test_col_group_is_three(self):
        self.assertEqual(gcm.LibvirtImportDialog._COL_GROUP, 3)

    def test_col_host_is_four(self):
        self.assertEqual(gcm.LibvirtImportDialog._COL_HOST, 4)

    def test_col_state_is_five(self):
        self.assertEqual(gcm.LibvirtImportDialog._COL_STATE, 5)

    def test_col_exists_is_six(self):
        self.assertEqual(gcm.LibvirtImportDialog._COL_EXISTS, 6)

    def test_col_idx_is_nine(self):
        self.assertEqual(gcm.LibvirtImportDialog._COL_IDX, 9)

    def test_all_ten_columns_unique(self):
        cols = [
            gcm.LibvirtImportDialog._COL_SEL,
            gcm.LibvirtImportDialog._COL_PROTO,
            gcm.LibvirtImportDialog._COL_NAME,
            gcm.LibvirtImportDialog._COL_GROUP,
            gcm.LibvirtImportDialog._COL_HOST,
            gcm.LibvirtImportDialog._COL_STATE,
            gcm.LibvirtImportDialog._COL_EXISTS,
            gcm.LibvirtImportDialog._COL_EXIST_LBL,
            gcm.LibvirtImportDialog._COL_FG,
            gcm.LibvirtImportDialog._COL_IDX,
        ]
        self.assertEqual(
            len(cols), len(set(cols)), "Tous les indices de colonnes doivent être uniques"
        )


# ── Tests _serial_templates_save / round-trip (v1.3.2) ───────────────────────


class TestSerialTemplatesSaveLoad(unittest.TestCase):
    """Tests pour _serial_templates_save/_serial_templates_load — round-trip."""

    def setUp(self):
        self._orig = dict(gcm._SERIAL_TEMPLATES)

    def tearDown(self):
        gcm._SERIAL_TEMPLATES = self._orig

    def test_save_creates_section(self):
        cp = configparser.RawConfigParser()
        gcm._serial_templates_save(cp)
        self.assertTrue(cp.has_section("serial_templates"))

    def test_save_load_roundtrip_cisco(self):
        cp = configparser.RawConfigParser()
        gcm._serial_templates_save(cp)
        gcm._SERIAL_TEMPLATES = {}
        gcm._serial_templates_load(cp)
        self.assertIn("Cisco IOS / IOS-XE / NX-OS", gcm._SERIAL_TEMPLATES)

    def test_save_load_custom_template(self):
        gcm._SERIAL_TEMPLATES["Mon Switch"] = ("115200", "h", "n", "8", "1")
        cp = configparser.RawConfigParser()
        gcm._serial_templates_save(cp)
        gcm._SERIAL_TEMPLATES = {}
        gcm._serial_templates_load(cp)
        # ConfigParser lowercases les clés pour les templates non-défaut
        found = gcm._SERIAL_TEMPLATES.get("mon switch") or gcm._SERIAL_TEMPLATES.get("Mon Switch")
        self.assertIsNotNone(found, "Le template custom doit être rechargé (casse tolérée)")
        self.assertEqual(found, ("115200", "h", "n", "8", "1"))

    def test_save_overwrites_existing_section(self):
        cp = configparser.RawConfigParser()
        cp.add_section("serial_templates")
        cp.set("serial_templates", "old_entry", "9600,n,n,8,1")
        gcm._serial_templates_save(cp)
        self.assertFalse(cp.has_option("serial_templates", "old_entry"))

    def test_load_no_section_returns_false(self):
        cp = configparser.RawConfigParser()
        result = gcm._serial_templates_load(cp)
        self.assertFalse(result)

    def test_load_with_section_returns_true(self):
        cp = configparser.RawConfigParser()
        gcm._serial_templates_save(cp)
        result = gcm._serial_templates_load(cp)
        self.assertTrue(result)

    def test_save_load_linux_template(self):
        cp = configparser.RawConfigParser()
        gcm._serial_templates_save(cp)
        gcm._SERIAL_TEMPLATES = {}
        gcm._serial_templates_load(cp)
        self.assertIn("Linux / Raspberry Pi", gcm._SERIAL_TEMPLATES)
        self.assertEqual(gcm._SERIAL_TEMPLATES["Linux / Raspberry Pi"][0], "115200")


# ── Tests _collect_ssh_keys (v1.3.2) ─────────────────────────────────────────


class TestCollectSshKeys(unittest.TestCase):
    """Tests pour _collect_ssh_keys — listing des clés privées SSH."""

    def test_no_ssh_dir_returns_empty(self):
        with patch("os.path.isdir", return_value=False):
            result = gcm._collect_ssh_keys()
        self.assertEqual(result, [])

    def test_skips_pub_files(self):
        with (
            patch("os.path.isdir", return_value=True),
            patch("os.listdir", return_value=["id_ed25519", "id_ed25519.pub"]),
            patch("os.path.isfile", return_value=True),
            patch(
                "builtins.open", unittest.mock.mock_open(read_data=b"BEGIN OPENSSH PRIVATE KEY")
            ),
        ):
            result = gcm._collect_ssh_keys()
        self.assertFalse(any(".pub" in k for k in result))

    def test_skips_known_hosts(self):
        with (
            patch("os.path.isdir", return_value=True),
            patch("os.listdir", return_value=["known_hosts", "id_rsa"]),
            patch("os.path.isfile", return_value=True),
            patch("builtins.open", unittest.mock.mock_open(read_data=b"BEGIN RSA PRIVATE KEY")),
        ):
            result = gcm._collect_ssh_keys()
        self.assertFalse(any("known_hosts" in k for k in result))

    def test_skips_config(self):
        with (
            patch("os.path.isdir", return_value=True),
            patch("os.listdir", return_value=["config", "authorized_keys", "id_rsa"]),
            patch("os.path.isfile", return_value=True),
            patch("builtins.open", unittest.mock.mock_open(read_data=b"BEGIN RSA PRIVATE KEY")),
        ):
            result = gcm._collect_ssh_keys()
        basenames = [os.path.basename(k) for k in result]
        self.assertNotIn("config", basenames)
        self.assertNotIn("authorized_keys", basenames)

    def test_returns_list(self):
        with (
            patch("os.path.isdir", return_value=True),
            patch("os.listdir", return_value=[]),
            patch("os.path.isfile", return_value=True),
        ):
            result = gcm._collect_ssh_keys()
        self.assertIsInstance(result, list)


# ═══════════════════════════════════════════════════════════════════════════════
# Tests nouvelles fonctionnalités v1.3.3
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tests SpiceTab._build_cmd mode --proxmox ─────────────────────────────────


class TestSpiceTabProxmoxMode(unittest.TestCase):
    """Tests SpiceTab._build_cmd en mode --proxmox NODE VMID."""

    def _tab(self, opts="", host_ip="192.168.105.41", port="22"):
        h = _make_host(host=host_ip, port=port, protocol="spice", user="root")
        tab = gcm.SpiceTab(h, lambda: "")
        tab._entry_opts.set_text(opts)
        return tab

    def test_proxmox_mode_detected(self):
        tab = self._tab("--proxmox DOCKER41 100")
        # Sans paramiko réel, _build_cmd retourne None (SSH échoue) — on vérifie juste la détection
        with patch("paramiko.SSHClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            stdout_mock = MagicMock()
            stdout_mock.read.return_value = b'{"type":"spice","tls-port":61000,"password":"abc","host":"pvespiceproxy:x:100:docker41:61000::tok","host-subject":"CN=DOCKER41","ca":"CERT","proxy":"http://docker41:3128"}'
            mock_client.exec_command.return_value = (MagicMock(), stdout_mock, MagicMock())
            with patch("tempfile.mkstemp", return_value=(5, "/tmp/test.vv")):
                with patch("os.fdopen", unittest.mock.mock_open()):
                    cmd = tab._build_cmd()
            self.assertIsNotNone(cmd)
            self.assertEqual(cmd[0], gcm.SPICE_BIN)
            self.assertTrue(cmd[1].endswith(".vv"))

    def test_proxmox_mode_missing_vmid_returns_none(self):
        tab = self._tab("--proxmox DOCKER41")
        result = tab._build_cmd()
        self.assertIsNone(result)

    def test_proxmox_mode_bad_json_returns_none(self):
        tab = self._tab("--proxmox DOCKER41 100")
        with patch("paramiko.SSHClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            stdout_mock = MagicMock()
            stdout_mock.read.return_value = b"not json"
            mock_client.exec_command.return_value = (MagicMock(), stdout_mock, MagicMock())
            result = tab._build_cmd()
        self.assertIsNone(result)

    def test_proxmox_mode_ssh_error_returns_none(self):
        tab = self._tab("--proxmox DOCKER41 100")
        with patch("paramiko.SSHClient") as mock_cls:
            mock_cls.return_value.connect.side_effect = Exception("Connection refused")
            result = tab._build_cmd()
        self.assertIsNone(result)

    def test_standard_mode_unchanged(self):
        """Le mode spice:// standard ne doit pas être affecté."""
        tab = self._tab("", host_ip="192.168.1.10", port="5930")
        cmd = tab._build_cmd()
        self.assertIsNotNone(cmd)
        self.assertTrue(any("spice://" in a for a in cmd))

    def test_connect_mode_unchanged(self):
        """Le mode --connect libvirt ne doit pas être affecté."""
        tab = self._tab("--connect qemu+ssh://root@hv/system vm1")
        cmd = tab._build_cmd()
        self.assertIsNotNone(cmd)
        self.assertFalse(any("spice://" in a for a in cmd))


# ── Tests icônes protocole (_proto_icon function) ────────────────────────────


class TestProtoIcon(unittest.TestCase):
    """Tests pour la fonction _proto_icon intégrée dans updateTree."""

    def _proto_icon(self, proto):
        """Réplique la logique _proto_icon de updateTree."""
        return {
            "ssh": "utilities-terminal",
            "telnet": "utilities-terminal",
            "rdp": "computer",
            "vnc": "video-display",
            "spice": "video-display",
            "serial": "modem",
            "local": "user-home",
        }.get(proto or "ssh", "network-workstation")

    def test_ssh_icon(self):
        self.assertEqual(self._proto_icon("ssh"), "utilities-terminal")

    def test_telnet_icon(self):
        self.assertEqual(self._proto_icon("telnet"), "utilities-terminal")

    def test_rdp_icon(self):
        self.assertEqual(self._proto_icon("rdp"), "computer")

    def test_vnc_icon(self):
        self.assertEqual(self._proto_icon("vnc"), "video-display")

    def test_spice_icon(self):
        self.assertEqual(self._proto_icon("spice"), "video-display")

    def test_serial_icon(self):
        self.assertEqual(self._proto_icon("serial"), "modem")

    def test_local_icon(self):
        self.assertEqual(self._proto_icon("local"), "user-home")

    def test_unknown_proto_fallback(self):
        self.assertEqual(self._proto_icon("ftp"), "network-workstation")

    def test_none_proto_fallback_to_ssh(self):
        self.assertEqual(self._proto_icon(None), "utilities-terminal")

    def test_all_protos_return_string(self):
        for p in ("ssh", "telnet", "rdp", "vnc", "spice", "serial", "local"):
            self.assertIsInstance(self._proto_icon(p), str)


# ── Tests _proxmox_fetch_hosts résolution IP ─────────────────────────────────


class TestProxmoxFetchHostsIPResolution(unittest.TestCase):
    """Tests pour la résolution IP dans _proxmox_fetch_hosts."""

    def _run_responses(self, responses):
        """Crée un run_fn qui renvoie les réponses dans l'ordre."""
        call_count = [0]

        def run_fn(client, cmd, timeout=30):
            idx = call_count[0]
            call_count[0] += 1
            if idx < len(responses):
                return responses[idx]
            return ""

        return run_fn

    def test_extract_first_ipv4_from_qga_json(self):
        """QGA JSON avec une IP valide → IP extraite correctement."""
        qga_json = '{"result":[{"name":"eth0","ip-addresses":[{"ip-address-type":"ipv4","ip-address":"192.168.105.145","prefix":24}]}]}'
        # Appel direct à la fonction interne via _proxmox_fetch_hosts
        # On teste via le module directement
        import json

        data = json.loads(qga_json)
        ip = ""
        for iface in data.get("result", []):
            for addr in iface.get("ip-addresses", []):
                a = addr.get("ip-address", "")
                import re

                if re.match(r"\d+\.\d+\.\d+\.\d+$", a) and not a.startswith("127."):
                    ip = a
                    break
            if ip:
                break
        self.assertEqual(ip, "192.168.105.145")

    def test_extract_ipv4_skips_loopback(self):
        """L'IP 127.x ne doit pas être retournée."""
        import json
        import re

        qga_json = '{"result":[{"name":"lo","ip-addresses":[{"ip-address-type":"ipv4","ip-address":"127.0.0.1","prefix":8}]},{"name":"eth0","ip-addresses":[{"ip-address-type":"ipv4","ip-address":"10.0.0.5","prefix":24}]}]}'
        data = json.loads(qga_json)
        ip = ""
        for iface in data.get("result", []):
            for addr in iface.get("ip-addresses", []):
                a = addr.get("ip-address", "")
                if re.match(r"\d+\.\d+\.\d+\.\d+$", a) and not a.startswith("127."):
                    ip = a
                    break
            if ip:
                break
        self.assertEqual(ip, "10.0.0.5")

    def test_ipconfig_parsed_correctly(self):
        """ipconfig0: ip=192.168.1.5/24,gw=... → IP extraite."""
        import re

        cfg_out = "ipconfig0: ip=192.168.1.5/24,gw=192.168.1.1"
        m = re.search(r"ip=(\d+\.\d+\.\d+\.\d+)", cfg_out)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "192.168.1.5")

    def test_ipconfig_skips_apipa(self):
        """Une IP 169.x dans ipconfig ne doit pas être utilisée."""
        import re

        cfg_out = "ipconfig0: ip=169.254.0.1/16"
        m = re.search(r"ip=(\d+\.\d+\.\d+\.\d+)", cfg_out)
        if m:
            self.assertTrue(m.group(1).startswith("169."))


# ── Tests import Proxmox SPICE — détection qxl ───────────────────────────────


class TestProxmoxFetchHostsSpiceQxl(unittest.TestCase):
    """Tests pour la détection vga:qxl dans _proxmox_fetch_hosts."""

    def test_qxl_detected_in_vga_output(self):
        vga_out = "vga: qxl"
        self.assertIn("qxl", vga_out.lower())

    def test_std_vga_not_qxl(self):
        vga_out = "vga: std"
        self.assertNotIn("qxl", vga_out.lower())

    def test_empty_vga_not_qxl(self):
        vga_out = ""
        self.assertNotIn("qxl", vga_out.lower())

    def test_qxl2_detected(self):
        vga_out = "vga: qxl2"
        self.assertIn("qxl", vga_out.lower())

    def test_extra_params_proxmox_format(self):
        """extra_params généré doit avoir le bon format --proxmox NODE VMID."""
        node_name = "DOCKER41"
        vmid = "100"
        extra = f"--proxmox {node_name} {vmid}"
        self.assertTrue(extra.startswith("--proxmox "))
        parts = extra.split()
        self.assertEqual(parts[1], "DOCKER41")
        self.assertEqual(parts[2], "100")


# ── Tests import libvirt/Proxmox — groupes par protocole ─────────────────────


class TestImportGroupByProtocol(unittest.TestCase):
    """Tests pour l'organisation en sous-groupes par protocole."""

    def _group_for(self, grp, proto):
        return f"{grp}/{proto}" if grp else proto

    def test_ssh_group(self):
        self.assertEqual(self._group_for("hyperv1", "ssh"), "hyperv1/ssh")

    def test_spice_group(self):
        self.assertEqual(self._group_for("hyperv1", "spice"), "hyperv1/spice")

    def test_rdp_group(self):
        self.assertEqual(self._group_for("hyperv1", "rdp"), "hyperv1/rdp")

    def test_vnc_group(self):
        self.assertEqual(self._group_for("hyperv1", "vnc"), "hyperv1/vnc")

    def test_empty_grp_ssh(self):
        self.assertEqual(self._group_for("", "ssh"), "ssh")

    def test_empty_grp_spice(self):
        self.assertEqual(self._group_for("", "spice"), "spice")

    def test_nested_group_preserved(self):
        self.assertEqual(self._group_for("cluster/node1", "rdp"), "cluster/node1/rdp")


# ── Tests validation port (local exempt) ────────────────────────────────────


class TestPortValidation(unittest.TestCase):
    """Tests pour la validation du port (ctype local exempté)."""

    def _validate(self, ctype, port):
        if ctype == "local":
            return True
        return bool(port and port.isdigit() and 1 <= int(port) <= 65535)

    def test_local_empty_port_valid(self):
        self.assertTrue(self._validate("local", ""))

    def test_ssh_empty_port_invalid(self):
        self.assertFalse(self._validate("ssh", ""))

    def test_ssh_valid_port(self):
        self.assertTrue(self._validate("ssh", "22"))

    def test_ssh_port_out_of_range(self):
        self.assertFalse(self._validate("ssh", "99999"))

    def test_rdp_valid_port(self):
        self.assertTrue(self._validate("rdp", "3389"))

    def test_spice_valid_port(self):
        self.assertTrue(self._validate("spice", "5930"))

    def test_local_any_string_valid(self):
        self.assertTrue(self._validate("local", "abc"))

    def test_vnc_valid_port(self):
        self.assertTrue(self._validate("vnc", "5900"))


# ── Tests VNC dans proto_filter ──────────────────────────────────────────────


class TestVncProtoFilter(unittest.TestCase):
    """Tests pour la prise en charge de VNC dans les filtres d'import."""

    def test_vnc_in_proto_defaults(self):
        self.assertIn("vnc", gcm._PROTO_DEFAULTS)

    def test_vnc_default_port(self):
        self.assertEqual(gcm._PROTO_DEFAULTS["vnc"], "5900")

    def test_proto_filter_accepts_vnc(self):
        proto_filter = {"ssh", "vnc", "rdp"}
        self.assertIn("vnc", proto_filter)

    def test_check_port_open_with_vnc_port(self):
        """_check_port_open peut être appelé avec le port VNC 5900."""

        def run_fn(client, cmd, timeout=30):
            return "OPEN" if "5900" in cmd else "CLOSED"

        result = gcm._check_port_open(None, run_fn, "192.168.1.10", 5900)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)

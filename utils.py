#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""Utilitaires généraux et classe de base GTK pour l'application GCM."""

import re as _re
import weakref as _weakref
from tokenize import Name as _tokenize_Name

from gi.repository import Gtk


class GCMBase:
    """Base class GTK3 natif remplacant SimpleGladeApp.

    Charge un fichier .glade via Gtk.Builder, expose tous les widgets
    comme attributs d'instance, connecte les signaux, puis appelle new().
    """

    def __init__(self, path, root=None, domain=None, parent=None, **kwargs):
        """Initialise le chargement Glade et l'arbre de widgets.

        Args:
            path (str): Chemin vers le fichier .glade.
            root (str, optional): Nom du widget racine a charger.
            domain (str, optional): Domaine de traduction.
            parent (Gtk.Window, optional): Fenetre parente (pour les dialogues).
            **kwargs: Attributs supplementaires a definir sur l'instance.
        """
        for key, value in kwargs.items():
            try:
                setattr(self, key, _weakref.proxy(value))
            except TypeError:
                setattr(self, key, value)

        self.builder = Gtk.Builder()
        if domain:
            self.builder.set_translation_domain(domain)

        if root:
            if parent:
                self.builder.expose_object("wMain", parent)
            self.builder.add_objects_from_file(path, [root])
            self.main_widget = self.builder.get_object(root)
            if self.main_widget:
                self.main_widget.show_all()
        else:
            self.builder.add_from_file(path)
            self.main_widget = None

        self._normalize_names()
        self.new()
        self.builder.connect_signals(self)

    def _normalize_names(self):
        """Expose chaque widget GTK comme attribut self.<widget_api_name>."""
        for widget in self.builder.get_objects():
            if isinstance(widget, Gtk.Buildable):
                raw = Gtk.Buildable.get_name(widget)
                parts = raw.split(":")
                api_name = "_".join(_re.findall(_tokenize_Name, parts[-1]))
                if api_name and not hasattr(self, api_name):
                    setattr(self, api_name, widget)

    def get_widget(self, name):
        """Retourne le widget GTK identifie par name.

        Args:
            name (str): Nom du widget dans le fichier Glade.

        Returns:
            Gtk.Widget or None: Widget trouve ou None.
        """
        return self.builder.get_object(name)

    def new(self):
        """Appelee apres le chargement Glade. A surcharger dans les sous-classes."""
        pass

    def run(self):
        """Demarre la boucle evenementielle GTK principale."""
        try:
            Gtk.main()
        except KeyboardInterrupt:
            pass

    def quit(self, *args):
        """Quitte la boucle evenementielle GTK.

        Args:
            *args: Arguments ignores (compatibilite signal GTK).
        """
        Gtk.main_quit()

    def gtk_main_quit(self, *args):
        """Callback GTK predefined: quitte l'application.

        Args:
            *args: Arguments ignores.
        """
        Gtk.main_quit()


class conf:
    """Classe de configuration globale de l'application."""

    WORD_SEPARATORS = "-A-Za-z0-9,./?%&#:_=+@~"
    BUFFER_LINES = 2000
    STARTUP_LOCAL = True
    LOG_LOCAL = False
    CONFIRM_ON_EXIT = True
    FONT_COLOR = ""
    BACK_COLOR = ""
    TRANSPARENCY = 0
    TERM = ""
    PASTE_ON_RIGHT_CLICK = 1
    CONFIRM_ON_CLOSE_TAB = 1
    CONFIRM_ON_CLOSE_TAB_MIDDLE = 1
    AUTO_CLOSE_TAB = 0
    CYCLE_TABS = True
    COLLAPSED_FOLDERS = ""
    LEFT_PANEL_WIDTH = 100
    CHECK_UPDATES = True
    WINDOW_WIDTH = -1
    WINDOW_HEIGHT = -1
    FONT = ""
    DISABLE_HOSTS_STRIPES = False
    AUTO_COPY_SELECTION = 0
    LOG_PATH = None  # Sera défini par le module principal
    CONTINUOUS_TAB_LOG = False
    CONTINUOUS_LOG_PATH = None  # Sera défini par le module principal
    SHOW_TOOLBAR = True
    SHOW_PANEL = True
    DARK_MODE = False
    THEME_MODE = "system"  # "system" | "light" | "dark"
    VERSION = 0
    UPDATE_TITLE = 0
    APP_TITLE = ""  # Sera défini par le module principal

#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""Modèles de données pour les hôtes et utilitaires de configuration."""

from gi.repository import Vte


class Host:
    """Classe représentant une connexion d'hôte avec tous ses paramètres."""

    def __init__(self, *args):
        """Initialise l'instance."""
        try:
            self.i = 0
            self.group = self.get_arg(args, None)
            self.name = self.get_arg(args, None)
            self.description = self.get_arg(args, None)
            self.host = self.get_arg(args, None)
            self.user = self.get_arg(args, None)
            self.password = self.get_arg(args, None)
            self.private_key = self.get_arg(args, None)
            self.port = self.get_arg(args, 22)
            self.tunnel = self.get_arg(args, "").split(",")
            self.type = self.get_arg(args, "ssh")
            self.commands = self.get_arg(args, None)
            self.keep_alive = self.get_arg(args, 0)
            self.font_color = self.get_arg(args, "")
            self.back_color = self.get_arg(args, "")
            self.x11 = self.get_arg(args, False)
            self.agent = self.get_arg(args, False)
            self.compression = self.get_arg(args, False)
            self.compressionLevel = self.get_arg(args, "")
            self.extra_params = self.get_arg(args, "")
            self.log = self.get_arg(args, False)
            self.backspace_key = self.get_arg(args, int(Vte.EraseBinding.AUTO))
            self.delete_key = self.get_arg(args, int(Vte.EraseBinding.AUTO))
            self.term = self.get_arg(args, "")
            self.protocol = self.get_arg(args, "ssh")
            # Paramètres série (RS-232/RS-485)
            self.serial_databits = self.get_arg(args, "8")
            self.serial_parity = self.get_arg(args, "n")
            self.serial_stopbits = self.get_arg(args, "1")
            self.serial_flow = self.get_arg(args, "n")
            self.serial_tool = self.get_arg(args, "picocom")
            # Paramètres RDP (xfreerdp)
            self.rdp_domain = self.get_arg(args, "")
            self.rdp_geometry = self.get_arg(args, "fullscreen")
            self.rdp_width = self.get_arg(args, "")
            self.rdp_height = self.get_arg(args, "")
            self.rdp_cert_ignore = self.get_arg(args, False)
            self.rdp_dyn_res = self.get_arg(args, False)
            self.rdp_remote_app = self.get_arg(args, "")
            # Paramètres VNC
            self.vnc_viewer = self.get_arg(args, "tigervnc")
            self.vnc_display = self.get_arg(args, "")
            self.vnc_view_only = self.get_arg(args, False)
            self.vnc_fullscreen = self.get_arg(args, False)
            # Paramètres SPICE
            self.spice_mode = self.get_arg(args, "uri")  # uri | libvirt | proxmox
            self.spice_tls_port = self.get_arg(args, "")
            self.spice_ca_cert = self.get_arg(args, "")
            self.spice_libvirt_uri = self.get_arg(args, "")
            self.spice_vm_name = self.get_arg(args, "")
            self.spice_px_node = self.get_arg(args, "")
            self.spice_px_vmid = self.get_arg(args, "")
        except:
            pass

    def get_arg(self, args, default):
        """Retourne la valeur d'un argument de connexion.

        Args:
            key (str): Nom de l'argument.

        Returns:
            str: Valeur de l'argument ou chaine vide.
        """
        arg = args[self.i] if len(args) > self.i else default
        self.i += 1
        return arg

    def __repr__(self):
        """Retourne une representation textuelle de l'hote.

        Returns:
            str: Representation de l'hote.
        """
        return "group=[%s],\t name=[%s],\t host=[%s],\t type=[%s]" % (
            self.group,
            self.name,
            self.host,
            self.type,
        )

    def tunnel_as_string(self):
        """Retourne la definition des tunnels SSH sous forme de chaine.

        Returns:
            str: Chaine de tunnels formatee.
        """
        return ",".join(self.tunnel)

    def clone(self):
        """Cree une copie profonde de l'hote.

        Returns:
            Host: Nouvel hote identique.
        """
        return Host(
            self.group,
            self.name,
            self.description,
            self.host,
            self.user,
            self.password,
            self.private_key,
            self.port,
            self.tunnel_as_string(),
            self.type,
            self.commands,
            self.keep_alive,
            self.font_color,
            self.back_color,
            self.x11,
            self.agent,
            self.compression,
            self.compressionLevel,
            self.extra_params,
            self.log,
            self.backspace_key,
            self.delete_key,
            self.term,
            getattr(self, "protocol", "ssh"),
            getattr(self, "serial_databits", "8"),
            getattr(self, "serial_parity", "n"),
            getattr(self, "serial_stopbits", "1"),
            getattr(self, "serial_flow", "n"),
            getattr(self, "serial_tool", "picocom"),
            getattr(self, "rdp_domain", ""),
            getattr(self, "rdp_geometry", "fullscreen"),
            getattr(self, "rdp_width", ""),
            getattr(self, "rdp_height", ""),
            getattr(self, "rdp_cert_ignore", False),
            getattr(self, "rdp_dyn_res", False),
            getattr(self, "rdp_remote_app", ""),
            getattr(self, "vnc_viewer", "tigervnc"),
            getattr(self, "vnc_display", ""),
            getattr(self, "vnc_view_only", False),
            getattr(self, "vnc_fullscreen", False),
            getattr(self, "spice_mode", "uri"),
            getattr(self, "spice_tls_port", ""),
            getattr(self, "spice_ca_cert", ""),
            getattr(self, "spice_libvirt_uri", ""),
            getattr(self, "spice_vm_name", ""),
            getattr(self, "spice_px_node", ""),
            getattr(self, "spice_px_vmid", ""),
        )


class HostUtils:
    """Utilitaires pour charger/sauvegarder les paramètres d'hôtes depuis/vers INI."""

    @staticmethod
    def get_val(cp, section, name, default):
        """Retourne la valeur d'un champ de l'hote avec valeur par defaut.

        Args:
            key (str): Nom du champ.
            default (str, optional): Valeur par defaut.

        Returns:
            str: Valeur du champ.
        """
        try:
            return cp.get(section, name) if type(default) != bool else cp.getboolean(section, name)
        except:
            return default

    @staticmethod
    def load_host_from_ini(cp, section, pwd=""):
        """Charge les parametres d'un hote depuis une section INI.

        Args:
            config (configparser.ConfigParser): Objet de configuration.
            section (str): Nom de la section.
        """
        from gnome_connection_manager import decrypt, get_password

        if pwd == "":
            pwd = get_password()
        group = cp.get(section, "group")
        name = cp.get(section, "name")
        host = cp.get(section, "host")
        user = cp.get(section, "user")
        password = decrypt(pwd, cp.get(section, "pass"))
        description = HostUtils.get_val(cp, section, "description", "")
        private_key = HostUtils.get_val(cp, section, "private_key", "")
        port = HostUtils.get_val(cp, section, "port", "22")
        tunnel = HostUtils.get_val(cp, section, "tunnel", "")
        ctype = HostUtils.get_val(cp, section, "type", "ssh")
        commands = (
            HostUtils.get_val(cp, section, "commands", "")
            .replace("\x00", "\n")
            .replace("\\n", "\n")
        )
        keepalive = HostUtils.get_val(cp, section, "keepalive", "")
        fcolor = HostUtils.get_val(cp, section, "font-color", "")
        bcolor = HostUtils.get_val(cp, section, "back-color", "")
        x11 = HostUtils.get_val(cp, section, "x11", False)
        agent = HostUtils.get_val(cp, section, "agent", False)
        compression = HostUtils.get_val(cp, section, "compression", False)
        compressionLevel = HostUtils.get_val(cp, section, "compression-level", "")
        extra_params = HostUtils.get_val(cp, section, "extra_params", "")
        log = HostUtils.get_val(cp, section, "log", False)
        backspace_key = int(
            HostUtils.get_val(cp, section, "backspace-key", int(Vte.EraseBinding.AUTO))
        )
        delete_key = int(HostUtils.get_val(cp, section, "delete-key", int(Vte.EraseBinding.AUTO)))
        term = HostUtils.get_val(cp, section, "term", "")
        protocol = HostUtils.get_val(cp, section, "protocol", "ssh")
        serial_databits = HostUtils.get_val(cp, section, "serial_databits", "8")
        serial_baud = HostUtils.get_val(cp, section, "serial_baud", "9600")
        serial_parity = HostUtils.get_val(cp, section, "serial_parity", "n")
        serial_stopbits = HostUtils.get_val(cp, section, "serial_stopbits", "1")
        serial_flow = HostUtils.get_val(cp, section, "serial_flow", "n")
        serial_tool = HostUtils.get_val(cp, section, "serial_tool", "picocom")
        rdp_domain = HostUtils.get_val(cp, section, "rdp_domain", "")
        rdp_geometry = HostUtils.get_val(cp, section, "rdp_geometry", "fullscreen")
        rdp_width = HostUtils.get_val(cp, section, "rdp_width", "")
        rdp_height = HostUtils.get_val(cp, section, "rdp_height", "")
        rdp_cert_ignore = HostUtils.get_val(cp, section, "rdp_cert_ignore", False)
        rdp_dyn_res = HostUtils.get_val(cp, section, "rdp_dyn_res", False)
        rdp_remote_app = HostUtils.get_val(cp, section, "rdp_remote_app", "")
        vnc_viewer = HostUtils.get_val(cp, section, "vnc_viewer", "tigervnc")
        vnc_display = HostUtils.get_val(cp, section, "vnc_display", "")
        vnc_view_only = HostUtils.get_val(cp, section, "vnc_view_only", False)
        vnc_fullscreen = HostUtils.get_val(cp, section, "vnc_fullscreen", False)
        spice_mode = HostUtils.get_val(cp, section, "spice_mode", "uri")
        spice_tls_port = HostUtils.get_val(cp, section, "spice_tls_port", "")
        spice_ca_cert = HostUtils.get_val(cp, section, "spice_ca_cert", "")
        spice_libvirt_uri = HostUtils.get_val(cp, section, "spice_libvirt_uri", "")
        spice_vm_name = HostUtils.get_val(cp, section, "spice_vm_name", "")
        spice_px_node = HostUtils.get_val(cp, section, "spice_px_node", "")
        spice_px_vmid = HostUtils.get_val(cp, section, "spice_px_vmid", "")
        h = Host(
            group,
            name,
            description,
            host,
            user,
            password,
            private_key,
            port,
            tunnel,
            ctype,
            commands,
            keepalive,
            fcolor,
            bcolor,
            x11,
            agent,
            compression,
            compressionLevel,
            extra_params,
            log,
            backspace_key,
            delete_key,
            term,
            protocol,
            serial_databits,
            serial_parity,
            serial_stopbits,
            serial_flow,
            serial_tool,
            rdp_domain,
            rdp_geometry,
            rdp_width,
            rdp_height,
            rdp_cert_ignore,
            rdp_dyn_res,
            rdp_remote_app,
            vnc_viewer,
            vnc_display,
            vnc_view_only,
            vnc_fullscreen,
            spice_mode,
            spice_tls_port,
            spice_ca_cert,
            spice_libvirt_uri,
            spice_vm_name,
            spice_px_node,
            spice_px_vmid,
        )
        h.serial_baud = serial_baud
        h.protocol = protocol
        return h

    @staticmethod
    def save_host_to_ini(cp, section, host, pwd=""):
        """Sauvegarde les parametres d'un hote dans une section INI.

        Args:
            config (configparser.ConfigParser): Objet de configuration.
        """
        from gnome_connection_manager import encrypt, get_password

        def _s(v):
            """Coerce any value to str safely (None → '')."""
            return "" if v is None else str(v)

        if pwd == "":
            pwd = get_password()
        cp.set(section, "group", _s(host.group))
        cp.set(section, "name", _s(host.name))
        cp.set(section, "description", _s(host.description))
        cp.set(section, "host", _s(host.host))
        cp.set(section, "user", _s(host.user))
        cp.set(section, "pass", encrypt(pwd, host.password))
        cp.set(section, "private_key", _s(host.private_key))
        cp.set(section, "port", _s(host.port))
        cp.set(section, "tunnel", host.tunnel_as_string())
        cp.set(section, "type", _s(host.type))
        commands = host.commands or ""
        cp.set(section, "commands", commands.replace("\n", "\\n"))
        cp.set(section, "keepalive", str(host.keep_alive))
        cp.set(section, "font-color", str(host.font_color))
        cp.set(section, "back-color", str(host.back_color))
        cp.set(section, "x11", str(host.x11))
        cp.set(section, "agent", str(host.agent))
        cp.set(section, "compression", str(host.compression))
        cp.set(section, "compression-level", str(host.compressionLevel))
        cp.set(section, "extra_params", str(host.extra_params))
        cp.set(section, "log", str(host.log))
        cp.set(section, "backspace-key", str(host.backspace_key))
        cp.set(section, "delete-key", str(host.delete_key))
        cp.set(section, "term", str(host.term))
        cp.set(section, "protocol", str(getattr(host, "protocol", "ssh")))
        cp.set(section, "serial_databits", str(getattr(host, "serial_databits", "8")))
        cp.set(section, "serial_baud", str(getattr(host, "serial_baud", "9600")))
        cp.set(section, "serial_parity", str(getattr(host, "serial_parity", "n")))
        cp.set(section, "serial_stopbits", str(getattr(host, "serial_stopbits", "1")))
        cp.set(section, "serial_flow", str(getattr(host, "serial_flow", "n")))
        cp.set(section, "serial_tool", str(getattr(host, "serial_tool", "picocom")))
        cp.set(section, "rdp_domain", str(getattr(host, "rdp_domain", "")))
        cp.set(section, "rdp_geometry", str(getattr(host, "rdp_geometry", "fullscreen")))
        cp.set(section, "rdp_width", str(getattr(host, "rdp_width", "")))
        cp.set(section, "rdp_height", str(getattr(host, "rdp_height", "")))
        cp.set(section, "rdp_cert_ignore", str(getattr(host, "rdp_cert_ignore", False)))
        cp.set(section, "rdp_dyn_res", str(getattr(host, "rdp_dyn_res", False)))
        cp.set(section, "rdp_remote_app", str(getattr(host, "rdp_remote_app", "")))
        cp.set(section, "vnc_viewer", str(getattr(host, "vnc_viewer", "tigervnc")))
        cp.set(section, "vnc_display", str(getattr(host, "vnc_display", "")))
        cp.set(section, "vnc_view_only", str(getattr(host, "vnc_view_only", False)))
        cp.set(section, "vnc_fullscreen", str(getattr(host, "vnc_fullscreen", False)))
        cp.set(section, "spice_mode", str(getattr(host, "spice_mode", "uri")))
        cp.set(section, "spice_tls_port", str(getattr(host, "spice_tls_port", "")))
        cp.set(section, "spice_ca_cert", str(getattr(host, "spice_ca_cert", "")))
        cp.set(section, "spice_libvirt_uri", str(getattr(host, "spice_libvirt_uri", "")))
        cp.set(section, "spice_vm_name", str(getattr(host, "spice_vm_name", "")))
        cp.set(section, "spice_px_node", str(getattr(host, "spice_px_node", "")))
        cp.set(section, "spice_px_vmid", str(getattr(host, "spice_px_vmid", "")))

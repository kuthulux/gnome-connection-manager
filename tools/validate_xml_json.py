#!/usr/bin/env python3
"""Valide les fichiers XML, Glade (.glade) et JSON (.json).

Usage (pre-commit) : appelé avec la liste des fichiers à vérifier.
Exit 0 = tout OK, exit 1 = au moins une erreur.

- .glade / .xml : validation XML avec xml.etree.ElementTree
- .json         : validation JSON avec json.loads
                  (pre-commit-hooks check-json couvre déjà .json,
                   ce hook est un filet de sécurité supplémentaire)
"""
import json
import sys
import xml.etree.ElementTree as ET

errors = []

for path in sys.argv[1:]:
    if path.endswith((".glade", ".xml")):
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            errors.append(f"[XML] {path}: {exc}")
        except OSError as exc:
            errors.append(f"[XML] {path}: impossible de lire le fichier — {exc}")

    elif path.endswith(".json"):
        try:
            with open(path, encoding="utf-8") as fh:
                json.load(fh)
        except json.JSONDecodeError as exc:
            errors.append(f"[JSON] {path}: {exc}")
        except OSError as exc:
            errors.append(f"[JSON] {path}: impossible de lire le fichier — {exc}")

if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)

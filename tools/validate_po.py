#!/usr/bin/env python3
"""Valide les fichiers .po avec msgfmt --check.

Usage (pre-commit) : appelé avec la liste des fichiers .po à vérifier.
Exit 0 = tout OK, exit 1 = au moins une erreur.
"""
import subprocess
import sys

errors = []
for path in sys.argv[1:]:
    if not path.endswith(".po"):
        continue
    result = subprocess.run(
        ["msgfmt", "--check", "--output-file=/dev/null", path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        errors.append(f"[PO] {path}:\n{result.stderr.strip()}")

if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)

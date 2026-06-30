# Feuille de route — GCM v1.3
**Projet :** Fork de kuthulux/gnome-connection-manager
**Fork cible :** https://github.com/MathildeDec/gnome-connection-manager
**Date de démarrage :** 2026-06-09
**Version courante :** v1.3.2
**Modèle :** Claude Sonnet 4.6 (GitHub Copilot)

---

## Vue d'ensemble des étapes

| # | Étape | Statut | Complexité |
|---|---|---|---|
| 0 | Mise en place du fork GitHub | ✅ Terminé | Facile |
| 1 | Corrections bugs Python 3.13 | ✅ Terminé | Facile |
| 1b | Corrections bugs upstream (issues GitHub) | ✅ Terminé | Moyen |
| 2 | Modernisation APIs GTK3 + docstrings Google (#110) | ✅ Terminé | Moyen |
| 3 | Remplacement SimpleGladeApp → GCMBase natif | ✅ Terminé | Complexe |
| 4 | Intégration patch Import Libvirt v2 | ✅ Terminé | Moyen |
| 5 | Intégration patch RDP (processus externe) | ✅ Terminé | Moyen |
| 6 | xfreerdp embarqué via GtkSocket/XEmbed | ✅ Terminé | Complexe |
| 7 | Packaging et release v1.3.0 | ✅ Terminé | Facile |
| 8 | v1.3.1 — bugfixes + 16 langues + VNC/SPICE/Serial | ✅ Terminé | Moyen |
| 9 | Serial RS-232/485 + templates constructeurs (11) | ✅ Terminé | Moyen |
| 10 | Suite tests unitaires pytest (379 tests) | ✅ Terminé | Moyen |
| 11 | Documentation utilisateur + README | ✅ Terminé | Facile |
| 12 | **v1.3.2** — Import libvirt 2 phases + SpiceTab tunnel libvirt | ✅ Terminé | Complexe |
| 13 | **v1.3.2** — `tools/libvirt_inventory.py` v4 (CSV/Ansible/ports) | ✅ Terminé | Moyen |
| 14 | **v1.3.2** — `tools/ssh_deploy.py` + pre-commit ruff/black/flake8 | ✅ Terminé | Moyen |

**28 issues ouvertes** analysées. Classées ci-dessous.

### 🔴 Bugs critiques — à corriger dans v1.3

| Issue | Titre | Description du problème | Correction prévue |
|---|---|---|---|
| [#81](https://github.com/kuthulux/gnome-connection-manager/issues/81) | ✅ Crash au démarrage — `style.css` manquant | `provider.load_from_path` fatal → `try/except` non-bloquant | **Corrigé — commit 1b** |
| [#82](https://github.com/kuthulux/gnome-connection-manager/issues/82) | ✅ Clone impossible avec mot de passe | `sendPassword()` + `clone()` revu dans `addTab()` | **Corrigé — commit 1b** |
| [#88](https://github.com/kuthulux/gnome-connection-manager/issues/88) | ✅ Logging cassé sur Ubuntu 24.04 / GTK 3.24+ | Migré vers `output-written` (VTE 2.91+) | **Corrigé — commit 1b** |
| [#89](https://github.com/kuthulux/gnome-connection-manager/issues/89) | ✅ Passphrase SSH redemandée à chaque onglet | `SSH_AUTH_SOCK` injecté dans l'env VTE (`vte_run()`) | **Corrigé — commit 1b** |
| [#87](https://github.com/kuthulux/gnome-connection-manager/issues/87) | ✅ Freeze SSH MikroTik (`window-change` flood) | Debounce 200ms sur `on_terminal_size_allocate` | **Corrigé — commit 1b** |
| [#64](https://github.com/kuthulux/gnome-connection-manager/issues/64) | ✅ Double-clic dans Midnight Commander | Vérification `posY < tab_bar_height` dans `on_terminal_click` | **Corrigé — commit 1b** |
| [#67](https://github.com/kuthulux/gnome-connection-manager/issues/67) | ✅ Surlignage jaune cluster persiste | `queue_draw()` forcé sur tous les onglets au changement cluster | **Corrigé — commit 1b** |
| [#66](https://github.com/kuthulux/gnome-connection-manager/issues/66) | ✅ Port tunnel SSH perdu à la sauvegarde | Sérialisation `host:port` corrigée (split max 2) | **Corrigé — commit 1b** |

### 🟡 Issues de packaging — réglées pour la release

| Issue | Titre | Action |
|---|---|---|
| [#71](https://github.com/kuthulux/gnome-connection-manager/issues/71) | ✅ `style.css` absent du paquet .deb | Livré dans release v1.3.0 |

### 🟢 Bonnes idées — futures évolutions (post v1.3)

| Issue | Titre | Note |
|---|---|---|
| [#76](https://github.com/kuthulux/gnome-connection-manager/issues/76) | ✅ Traductions manquantes/incorrectes | **16 langues** : de/en/fr/it/ko/pl/pt/ru + uk/ja/ar/tr/nl/cs/sv/nb — commit `08a48a1` |
| [#100](https://github.com/MathilDec/gnome-connection-manager/issues/100) | ✅ Traduction ukrainienne | `lang/uk_UA/` compilé et inclus — commit `08a48a1` |
| [#101](https://github.com/MathilDec/gnome-connection-manager/issues/101) | ✅ Connexion VMs libvirt/QEMU | Détection heuristique Windows → protocol=rdp, import libvirt v2 — étape 4 |
| [#102]() | ✅ Support VNC et SPICE | `VncTab` + `SpiceTab` — commit `1394da1` |
| [#110]() | ✅ Docstrings Google | 188 fonctions documentées — étape 2 |
| [#111]() | ✅ Tests unitaires (pytest) | **379 tests**, 0 échec — commit `1394da1` |
| [#80](https://github.com/kuthulux/gnome-connection-manager/issues/80) | 🔲 Config CLI `--config` | `argparse` — post v1.3 |
| [#79](https://github.com/kuthulux/gnome-connection-manager/issues/79) | 🔲 Zoom terminal Ctrl++/- | post v1.3 |
| [#78](https://github.com/kuthulux/gnome-connection-manager/issues/78) | 🔲 Couleurs personnalisables | post v1.3 |
| [#77](https://github.com/kuthulux/gnome-connection-manager/issues/77) | 🔲 Fermeture automatique onglet | post v1.3 |
| [#74](https://github.com/kuthulux/gnome-connection-manager/issues/74) | 🔲 Import CSV / PuTTY | post v1.3 |
| [#103]() | 🔲 Terminal web xterm.js | Remplacement VTE par xterm.js embarqué |
| [#104]() | 🔲 Wayland natif | Adapter XEmbed / xfreerdp pour Wayland |
| [#105]() | 🔲 Application mobile Android/iOS | Portage avec interface adaptée SSH/RDP/VNC |
| [#106]() | 🔲 API REST de contrôle GCM | Lancer connexions + état sessions via HTTP sécurisé |
| [#107]() | 🔲 Architecture plugins | Extensions communauté (Ansible, monitoring…) |
| [#108]() | 🔲 Gestion des clés SSH intégrée | Génération / import / export clés SSH dans GCM |
| [#109]() | 🔲 Notifications desktop | Alértes déconnexion / erreurs via le système de notifications |
| [#112]() | 🔲 Refactor MVC | Séparer logique métier et UI |
| [#113]() | 🔲 Mode sombre | Thème sombre optionnel |
| [#114]() | 🔲 Recherche dans onglets | Chercher du texte dans les sessions ouvertes |
| [#115]() | 🔲 Partage de session | Multi-utilisateurs sur une même session SSH |
| [#116]() | 🔲 Scripting avant/après connexion | Scripts personnalisés sur événements |

### TODO upstream original — état détaillé

| Item | Statut | Notes |
|---|---|---|
| ayuda (aide contextuelle) | 🔲 post v1.3 | Tooltip / page d'aide intégrée |
| drag'n drop hosts entre groupes | 🔲 post v1.3 | DnD Gtk.TreeView |
| **sftp** | 🔲 post v1.3 | Navigateur de fichiers via paramiko SFTP |
| master password au démarrage | 🔲 post v1.3 | Chiffrement du keyring local |
| sauvegarder état des onglets ouverts | 🔲 post v1.3 | Restaurer sessions au redémarrage |
| shortcut navigation entre notebooks | 🔲 post v1.3 | Ctrl+Tab / Alt+1..9 |
| retirer les accelerators du .glade | 🔲 post v1.3 | ou les rendre optionnels |
| **soporte picocom / minicom / serial** | ✅ **Fait v1.3.1** | `SerialTab` + 11 templates constructeurs |
| Modifier CTRL+Q fermeture app | 🔲 post v1.3 | Préférences raccourcis |
| icône system tray | 🔲 post v1.3 | `Gtk.StatusIcon` / `libappindicator` |
| supprimer shortcut ALT+F | 🔲 post v1.3 | Ou option pour le désactiver |
| proxy socks/http pour SSH | 🔲 post v1.3 | `-o ProxyCommand` |
| cluster mode — liste déroulante | 🔲 post v1.3 | UX améliorée |
| masquer saisie en mode cluster | 🔲 post v1.3 | Checkbox afficher/masquer |
| sélectionner plusieurs hosts | 🔲 post v1.3 | Multi-sélection TreeView |
| édition multiple hosts | 🔲 post v1.3 | Modifier port/groupe en lot |
| couleurs par groupe | 🔲 post v1.3 | Comme PuTTY |
| renommer un groupe | 🔲 post v1.3 | |
| import sessions PuTTY | 🔲 post v1.3 | Parser `~/.putty/sessions/` |
| masquer passwords dans les commandes | 🔲 post v1.3 | `#P=password` (Angelo Corsaro) |
| historique commandes cluster | 🔲 post v1.3 | Persistance optionnelle |
| désactiver les shortcuts | 🔲 post v1.3 | Option dans préférences |
| charset dynamique en console | 🔲 post v1.3 | Option par host |

### ✅ Réalisé en v1.3.2 (post v1.3.1)

| Priorité | Feature | Statut |
|---|---|---|
| ⭐⭐⭐ | **libvirt_inventory** v4 | ✅ `tools/libvirt_inventory.py` — CLI, CSV, Ansible INI/YAML, détection ports, OS, vCPUs, RAM |
| ⭐⭐⭐ | **ssh_deploy** | ✅ `tools/ssh_deploy.py` — Génération clés RSA-4096 + Ed25519, ssh-copy-id batch |
| ⭐⭐⭐ | **Import libvirt 2 phases** | ✅ `LibvirtImportDialog` — scan + prévisualisation, ProxyJump, SPICE libvirt URI, RDP conditionnel |
| ⭐⭐⭐ | **SpiceTab tunnel libvirt** | ✅ `remote-viewer --connect qemu+ssh://…` via détection `--connect` |
| ⭐⭐⭐ | **Qualité code** | ✅ `pyproject.toml` ruff Google style + `.pre-commit-config.yaml` (ruff/black/flake8) |

### 🔲 Prochaines évolutions planifiées (post v1.3.2)

| Priorité | Feature | Détails |
|---|---|---|
| ⭐⭐⭐ | Import CSV / PuTTY | Parser `~/.putty/sessions/` + CSV export/import |
| ⭐⭐⭐ | https://github.com/BuddySirJava/SSH-Studio/tree/master | Étudier le code source de SSH-Studio pour inspiration ; notamment la gestion des onglets et des sessions , la persistance des connexions, et l'interface utilisateur. , segmentation du code en modules réutilisables: gui, src, plugins,
synchronisation .ssh/config : .ssh/config permet de gérer les configurations SSH de manière centralisée, ce qui pourrait être utile pour GCM/VSCode | garder un fichier de configuration centralisé pour les connexions SSH, et permettre aux utilisateurs de modifier facilement leurs paramètres de connexion. .ssh/config sait contenir des informations sur les hôtes, les ports, les utilisateurs, les clés privées, etc. , les connexions complexes : SSH-Studio gère les connexions complexes avec des tunnels, des proxys et des redirections de ports. GCM pourrait s'inspirer de cette approche pour offrir une meilleure gestion des connexions avancées. / j'imagine fusionner les fonctionnalités de GCM et SSH-Studio pour créer une application plus complète et plus puissante pour la gestion des connexions SSH. . les connexions multiples : SSH-Studio permet de gérer plusieurs connexions simultanément, ce qui pourrait être utile pour les utilisateurs qui ont besoin de se connecter à plusieurs serveurs en même temps. , l'interface utilisateur : SSH-Studio a une interface utilisateur moderne et conviviale, avec des onglets pour chaque connexion et des options de personnalisation. GCM pourrait s'inspirer de cette interface pour améliorer l'expérience utilisateur. les
| ⭐⭐ | Zoom terminal Ctrl++/- (#79) | `terminal.set_font()` ajusté |
| ⭐⭐ | Fermeture auto onglet (#77) | Option par host ou globale |
| ⭐⭐ | Config CLI `--config` (#80) | `argparse` |
| ⭐⭐ | Import CSV / PuTTY (#74) | |
| ⭐⭐ | ajoute une coche dans "editer hote" pour ajouter à l'espace de travail, ajouter un bouton "ouvrir l'espace de travail" qui ouvrira tous les onglets/connexions de l'espace de travail | |
| ⭐⭐ | Terminal web xterm.js (#103) | |
| ⭐⭐ | Wayland natif (#104) | |
| ⭐⭐| API REST (#106) | |
| ⭐ | Architecture plugins (#107) | |
| ⭐ | Gestion clés SSH (#108) créer mes clés rsa et ed25519 | |
| ⭐ | Notifications desktop (#109) | |
| ⭐⭐ | Mode sombre (#113) | |
| ⭐ | Recherche dans onglets (#114) | |
| ⭐ | Refactor MVC (#112) | |

### ⚪ Issues dans scope / questions utilisateurs

| Issue | Statut |
|---|---|
| [#90](https://github.com/kuthulux/gnome-connection-manager/issues/90) | ✅ Packaging Makefile deb+rpm inclus dans le repo |
| [#58](https://github.com/kuthulux/gnome-connection-manager/issues/58) | ✅ Résolu par fix GTK étape 2 |
| [#68](https://github.com/kuthulux/gnome-connection-manager/issues/68) | ✅ Documentation-fr.md + README.md mis à jour v1.3.1 |

---

## Étape 1 — Corrections bugs Python 3.13

### Objectif
Corriger les incompatibilités Python 2→3 qui empêchent le lancement de GCM.

### Analyse
GCM parse correctement (`ast.parse` OK) mais contient des bugs à l'exécution :

| Ligne | Problème | Correction | Statut |
|---|---|---|---|
| 41 | `from __future__ import with_statement` | Supprimé | ✅ |
| 315 | `xrange(len(str1))` → `NameError: xrange` | Remplacé par `range(len(str1))` | ✅ |
| 3510 | `web.readline().strip().decode('utf-8')` | Vérification type — OK (urllib3 retourne des bytes en Python 3) | ✅ vérif OK |

### Résultat
`ast.parse` OK. `xrange` corrigé. `from __future__` supprimé.
**Commit :** à faire après validation (étape 1b).

---

## Étape 1b — Corrections bugs upstream (issues GitHub)

---

## Étape 0 — Fork GitHub et configuration du dépôt local

### Objectif
Créer le fork officiel sur le compte MathildeDec et reconfigurer le dépôt local pour travailler sur ce fork.

### Actions

**0.1 — Créer le fork sur GitHub**
- Aller sur https://github.com/kuthulux/gnome-connection-manager
- Cliquer sur **Fork** → compte **MathildeDec**
- Nom du repo : `gnome-connection-manager`
- *Problème connu : le PAT actuel n'a pas le scope `repo` pour créer des forks via l'API `gh fork`. Le fork doit être créé manuellement via le navigateur ou en régénérant le token avec le scope `repo`.*

**0.2 — Reconfigurer les remotes git locaux**
```bash
cd /app/gnome-connection-manager
git remote rename origin upstream
git remote add origin https://github.com/MathildeDec/gnome-connection-manager.git
git push -u origin master
```

**0.3 — Créer la branche de développement**
```bash
git checkout -b develop
git push -u origin develop
```

**0.4 — Déplacer les fichiers du fork dans le repo**
Les fichiers actuellement dans `fork/` seront intégrés au fur et à mesure dans le code principal. Le dossier `fork/` sert d'archive de référence.

### Résultat attendu
- Remote `origin` → MathildeDec/gnome-connection-manager
- Remote `upstream` → kuthulux/gnome-connection-manager (pour récupérer les MAJ upstream)
- Branche `develop` active pour le développement

---

## Étape 1 — Corrections bugs Python 3.13

### Objectif
Corriger les incompatibilités Python 2→3 qui empêchent le lancement de GCM.

### Analyse
GCM parse correctement (`ast.parse` OK) mais contient des bugs à l'exécution :

| Ligne | Problème | Correction |
|---|---|---|
| 315 | `xrange(len(str1))` → `NameError: xrange` | Remplacer par `range(len(str1))` |
| 41 | `from __future__ import with_statement` | Supprimer (relique Python 2, ignoré en Python 3 mais inutile) |
| 3510 | `web.readline().strip().decode('utf-8')` | Vérifier le type retourné (string vs bytes) pour éviter `AttributeError` |

### Actions détaillées

**1.1 — Corriger `xrange` (bloquant)**
Fichier : `gnome_connection_manager.py`, ligne 315
Fonction `xor()` utilisée pour le chiffrement des mots de passe.

```python
# AVANT
for k in xrange(len(str1)):

# APRÈS
for k in range(len(str1)):
```

**1.2 — Supprimer `from __future__`**
Ligne 41 — relique inoffensive mais inutile sous Python 3.

**1.3 — Corriger la lecture de version (check_updates)**
Ligne 3510 — `web.readline()` retourne déjà un `str` si la connexion HTTP est correctement décodée. Vérifier et corriger si nécessaire.

**1.4 — Validation**
```bash
python3 -c "
import ast
with open('gnome_connection_manager.py') as f: src = f.read()
ast.parse(src)
print('Parse OK')
"
# Tester le lancement si display X disponible
python3 gnome_connection_manager.py
```

### Résultat attendu
GCM se lance sans erreur Python sous Python 3.13.

---

### Objectif
Corriger les 8 bugs remontés dans les issues du dépôt upstream qui impactent les utilisateurs actuels.

### Bug 1 — `style.css` manquant → crash au démarrage (issue #81) ⭐ CRITIQUE

**Symptôme :** GCM crashe avec `GLib.GError: Error opening file .../style.css: No such file or directory`
**Cause :** `provider.load_from_path()` est appelé sans vérifier que le fichier existe.
**Correction :** rendre le chargement non-fatal.

```python
# AVANT
provider.load_from_path(BASE_PATH + "/style.css")

# APRÈS
try:
    provider.load_from_path(BASE_PATH + "/style.css")
except Exception:
    pass  # style.css absent — non bloquant, on continue sans thème
```

### Bug 2 — Clone onglet impossible avec mot de passe (issue #82)

**Symptôme :** Le 2e onglet cloné reste noir (curseur clignotant, rien ne se passe).
**Cause :** Lors d'un `clone()`, la méthode `addTab()` récupère le mot de passe depuis `host.password` mais le processus `expect` de saisie automatique du mot de passe ne se déclenche pas au bon moment sur la session clonée.
**Correction :** Analyser `addTab()` → vérifier que `sendPassword()` est appelé sur le bon terminal VTE après connexion SSH, pas avant.

### Bug 3 — Logging cassé sur Ubuntu 24.04 / VTE récent (issue #88) ⭐ CRITIQUE

**Symptôme :** Le fichier de log ne contient que l'en-tête d'ouverture de session, rien de plus. Sessions très lentes si logging activé.
**Cause :** VTE 2.91+ a supprimé/modifié le signal `contents-changed`. GCM utilise probablement ce signal pour déclencher l'écriture dans le fichier de log.
**Correction :** Migrer vers `output-written` (signal VTE 2.91+) :

```python
# AVANT (VTE ancien)
terminal.connect("contents-changed", self.on_terminal_contents_changed)

# APRÈS (VTE 2.91+)
terminal.connect("output-written", self.on_terminal_output_written)
```

Chercher dans le code : `set_terminal_logger()` et `on_contents_changed()`.

### Bug 4 — Passphrase SSH redemandée à chaque onglet (issue #89)

**Symptôme :** À chaque nouvel onglet SSH, GCM demande la passphrase de la clé privée, même si l'agent SSH (gnome-keyring, ssh-agent) est actif.
**Cause :** La variable `SSH_AUTH_SOCK` n'est pas transmise au sous-processus VTE qui lance SSH.
**Correction :** Injecter `SSH_AUTH_SOCK` dans l'environnement du processus SSH :

```python
# Dans vte_run() ou addTab(), lors de la construction du env[] passé à terminal.spawn_async()
import os
env = os.environ.copy()
# SSH_AUTH_SOCK est déjà dans os.environ si l'agent est actif
# S'assurer qu'il est dans la liste env passée à Vte
```

Ou plus simplement : passer `-o AddKeysToAgent=yes` dans les arguments SSH par défaut.

### Bug 5 — Freeze SSH sur équipements réseau (MikroTik, etc.) (issue #87)

**Symptôme :** La session SSH se gèle après quelques minutes. Le device reçoit des centaines de paquets `window-change` en boucle.
**Cause :** À chaque redimensionnement de la fenêtre GCM (même minuscule), `Vte` notifie la taille et GCM renvoie immédiatement un `window-change` SSH. Des animations GTK ou des redimensionnements automatiques génèrent des dizaines d'événements par seconde.
**Correction :** Throttler les envois `window-change` avec un debounce de 200ms :

```python
self._resize_timer = None

def _on_terminal_size_allocate(self, terminal, allocation):
    if self._resize_timer:
        GLib.source_remove(self._resize_timer)
    self._resize_timer = GLib.timeout_add(200, self._send_window_change, terminal)

def _send_window_change(self, terminal):
    self._resize_timer = None
    # ... envoyer le window-change SSH ici
    return False
```

### Bug 6 — Double-clic dans Midnight Commander ouvre un onglet (issue #64)

**Symptôme :** Un double-clic dans le panneau droit de MC ouvre un nouvel onglet GCM au lieu d'exécuter l'action MC.
**Cause :** Dans `on_terminal_click()`, le calcul `posY = event.y + widget.get_allocation().y` est relatif au mauvais widget selon si on clique dans le terminal ou dans la barre d'onglets. Avec MC actif, les coordonnées tombent dans la zone "ouvrir un onglet".
**Correction :** Ajouter une vérification de hauteur — si `posY > tab_bar_height`, le clic est dans le terminal, pas dans les onglets :

```python
# Dans on_terminal_click(), avant le bloc if qui ouvre un onglet :
tab_bar_height = self.get_tab_bar_height()  # ~30px environ
if posY > tab_bar_height:
    return  # clic dans le terminal, pas dans les onglets
```

### Bug 7 — Surlignage jaune cluster ne se réinitialise pas (issue #67)

**Symptôme :** Après ajout/suppression d'une connexion en mode cluster, les onglets gardent leur surbrillance jaune même après désélection.
**Cause :** Le `queue_draw()` n'est pas appelé sur les onglets retirés du cluster lors de la modification de la liste.
**Correction :** Forcer le redraw de tous les label d'onglets lors d'un changement de cluster.

### Bug 8 — Port tunnel SSH perdu à la sauvegarde (issue #66)

**Symptôme :** Le champ "Tunnel remote host" avec port (`hostname:8080`) est perdu après sauvegarde.
**Cause :** La sérialisation du champ `tunnel_host` ne gère pas le format `host:port` (confond avec le champ `host` principal).
**Correction :** Sauvegarder `tunnel_host` et `tunnel_port` comme deux champs séparés dans la config.

### Ordre de traitement

```
Priorité 1 (bloquants/fréquents) :
  Bug 1 — style.css crash         → étape 1b.1
  Bug 3 — logging VTE cassé       → étape 1b.3
  Bug 4 — SSH_AUTH_SOCK           → étape 1b.4

Priorité 2 (gênants) :
  Bug 2 — clone avec password     → étape 1b.2
  Bug 5 — freeze MikroTik         → étape 1b.5
  Bug 6 — MC double-clic          → étape 1b.6

Priorité 3 (mineurs) :
  Bug 7 — cluster highlight       → étape 1b.7
  Bug 8 — tunnel port perdu       → étape 1b.8
```

### Commit prévu
```
git commit -m "fix: corrections bugs upstream issues #81 #82 #87 #88 #89 #64 #67 #66"
```

---

## Étape 2 — Modernisation APIs GTK3 dépréciées

### Objectif
Corriger les 71 occurrences d'APIs GTK3 dépréciées qui génèrent des warnings (et crasheront sous une future version de GTK).

### Analyse des dépréciations

**Environnement :** GTK 3.24.49 + python3-gi 3.50.0

| API dépréciée | Remplacement | Nb occurrences |
|---|---|---|
| `Gtk.ImageMenuItem` | `Gtk.MenuItem` (icônes supprimées dans GTK3 moderne) | ~20 |
| `Gtk.STOCK_CANCEL` | `_("Annuler")` ou icon name string | ~5 |
| `Gtk.STOCK_OPEN` | `_("Ouvrir")` | ~2 |
| `Gtk.STOCK_SAVE` | `_("Enregistrer")` | ~2 |
| `Gtk.STOCK_INDEX` | supprimer ou remplacer par icône | ~1 |
| Autres `STOCK_*` | icon names via `Gtk.Image.new_from_icon_name()` | ~10 |
| `Gtk.ButtonBox` | `Gtk.Box` avec `set_spacing()` | si présent dans .glade |

### Actions détaillées

**2.1 — Remplacer `Gtk.ImageMenuItem` dans `createMenu()`**
Fichier : `gnome_connection_manager.py`, méthode `createMenu()` (~ligne 903)
Chaque `Gtk.ImageMenuItem(label=...)` → `Gtk.MenuItem(label=...)`
Supprimer les `menuItem.set_image(...)` correspondants (les images ne sont plus affichées par GTK3 moderne de toute façon).

**2.2 — Remplacer les constantes `STOCK_*` dans les dialogues**
Fichier : `gnome_connection_manager.py`, fonction `show_open_dialog()` (~ligne 241)

```python
# AVANT
dlg.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
dlg.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

# APRÈS
dlg.add_button(_("Annuler"), Gtk.ResponseType.CANCEL)
dlg.add_button(_("Ouvrir"), Gtk.ResponseType.OK)
```

**2.3 — Audit du fichier .glade**
Fichier : `gnome-connection-manager.glade`
Chercher et corriger :
- `GtkImageMenuItem` → `GtkMenuItem`
- `use-stock="True"` → supprimer
- `stock-id="..."` → remplacer par `label="..."`

**2.4 — Validation**
```bash
python3 gnome_connection_manager.py 2>&1 | grep -i "warn\|deprecat\|error" | head -20
```

### Résultat attendu
Zéro warning GTK au démarrage. Interface identique visuellement.

---

## Étape 3 — Remplacement de SimpleGladeApp

### Objectif
Supprimer la dépendance à `SimpleGladeApp.py` (fichier généré en 2010, archaïque) et migrer vers `Gtk.Builder` natif.

### Analyse
`SimpleGladeApp.py` est un wrapper autour de `Gtk.Builder` qui :
- Auto-connecte les signaux par convention de nommage
- Expose les widgets comme attributs de la classe via `__getattr__`
- Gère `bindtextdomain` pour l'i18n

**Risque :** Étape la plus complexe — touche à l'architecture de `class Wmain`. À faire après les étapes 4 et 5.

### Actions détaillées

**3.1 — Analyser toutes les utilisations de SimpleGladeApp**
```bash
grep -n "SimpleGladeApp\|self\.\(builder\|glade\|xml\)" gnome_connection_manager.py
```

**3.2 — Créer un `Gtk.Builder` natif dans `Wmain.__init__`**
```python
# AVANT (SimpleGladeApp)
class Wmain(SimpleGladeApp):
    def __init__(self, path, root, domain):
        SimpleGladeApp.__init__(self, path, root, domain)

# APRÈS (Gtk.Builder natif)
class Wmain:
    def __init__(self, path, root, domain):
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain(domain)
        self.builder.add_from_file(path)
        self.builder.connect_signals(self)
        # Exposer le widget racine
        self.mainWindow = self.builder.get_object(root)
```

**3.3 — Remplacer les accès `self.widget_name` par `self.builder.get_object("widget_name")`**
*Environ 150-200 occurrences — à faire avec un script de remplacement assisté.*

**3.4 — Supprimer `SimpleGladeApp.py` du projet**

**3.5 — Validation complète de l'interface**

### Résultat attendu
Plus de dépendance externe. Code 100% PyGObject natif.

---

## Étape 4 — Intégration du patch Import Libvirt v2

### Objectif
Intégrer `fork/gcm_import_libvirt_v2.py` dans `gnome_connection_manager.py`.

### Source
Fichier de référence : `fork/gcm_import_libvirt_v2.py`
Développé lors de la session du 2026-06-08/09.

### Fonctionnalités apportées
- Menu **Serveurs > Importer depuis libvirt…**
- Dialogue GTK3 : liste des hyperviseurs (URIs dconf/virt-manager), user SSH, log, progressbar
- **Segmentation automatique** des noms de VM en groupes GCM :
  - `prod-web-01` → groupe **PROD** / host `web-01`
  - `INT-dns01` → groupe **INT** / host `dns01`
  - `standalone` → groupe **LIBVIRT** / host `standalone`
- **Auth SSH par clé** : Ed25519 → RSA → agent (jamais de mot de passe)
- **Résolution IP** : domifaddr agent → domifaddr arp → DHCP leases → ARP noyau → fallback hostname
- **Onglet Libvirt** dans les préférences (user SSH par défaut)
- **Détection heuristique Windows** : noms contenant `win|w2019|w2022|wdc|wsrv` → protocol=rdp

### 6 points d'intégration

**Point 1 — Imports** (haut du fichier, après les imports existants)
```python
import threading
from urllib.parse import urlparse
import paramiko
LIBVIRT_DEFAULT_USER = "root"
```

**Point 2 — Fonctions et classes libvirt** (avant `class Wmain`)
```python
def _vm_name_split(vm_name): ...
def _collect_ssh_keys(): ...
def _paramiko_connect(host, user): ...
def _libvirt_get_uris_from_dconf(): ...
def _libvirt_ssh_run(client, cmd): ...
def _libvirt_fetch_hosts(uri, ssh_user, log_cb, progress_cb): ...
class LibvirtImportDialog(Gtk.Dialog): ...
class LibvirtPrefsTab(Gtk.Box): ...
```

**Point 3 — Item de menu** (fin de `Wmain.createMenu()`)
```python
# Après la création du menuServers existant :
self.menuServers.mnu_import_libvirt = item = Gtk.MenuItem(label=_("Importer depuis libvirt…"))
item.connect("activate", self.on_mnu_import_libvirt_activate)
self.menuServers.append(item)
item.show()
```

**Point 4 — Handler menu** (dans `class Wmain`)
```python
def on_mnu_import_libvirt_activate(self, widget):
    dlg = LibvirtImportDialog(parent=self.mainWindow, default_user=...)
    # ... création groupes + hosts + save_config()
```

**Point 5 — Onglet préférences** (dans `Wmain.on_preferences_activate()`)
```python
self._libvirt_prefs_tab = LibvirtPrefsTab(config=self.conf)
notebook_prefs.append_page(self._libvirt_prefs_tab, Gtk.Label(label="Libvirt"))
```

**Point 6 — Persistance config**
Dans `loadConfig()` et `saveConfig()` :
```python
config["libvirt_default_user"] = self.conf.get("libvirt_default_user", "root")
```

### Dépendance
```bash
pip3 install paramiko
```

### Validation
1. Lancer GCM → menu Serveurs → "Importer depuis libvirt…" visible
2. Renseigner un hyperviseur SSH → lancer l'import
3. Vérifier que les groupes et hosts apparaissent dans l'arbre

---

## Étape 5 — Intégration du patch RDP (processus externe)

### Objectif
Intégrer `fork/gcm_rdp.py` dans `gnome_connection_manager.py`.

### Source
Fichier de référence : `fork/gcm_rdp.py`
Développé lors de la session du 2026-06-08/09.

### Fonctionnalités apportées
- Nouveau protocole **RDP** sur la classe `Host` (`protocol = "ssh"|"telnet"|"rdp"|"local"`)
- ComboBox **Protocole** + **Port** dans le dialogue d'édition de host
- Onglet RDP dans GCM : widget GTK `RdpTab` avec statut, log xfreerdp, boutons
- **xfreerdp lancé en processus externe** via `subprocess.Popen`
- Masquage du mot de passe dans les logs (`/p:****`)
- Reconnexion sans fermer l'onglet

### 6 points d'intégration

**Point 1 — Imports** (haut du fichier)
```python
import shutil
RDP_BIN = shutil.which("xfreerdp") or "xfreerdp"
```

**Point 2 — Champ `protocol` dans `class Host`**
```python
class Host:
    def __init__(self, ...):
        self.protocol = "ssh"   # nouveau champ
    def clone(self):
        h.protocol = self.protocol  # dans la méthode clone
    # sérialisation : ajouter protocol dans load/save config
```

**Point 3 — `class RdpTab`** (avant `class Wmain`)
```python
class RdpTab(Gtk.Box):
    # Widget d'onglet RDP : titre, description, statut, boutons, log
    # Options xfreerdp modifiables à la volée
    # Thread lecteur de sortie xfreerdp
```

**Point 4 — Détection RDP dans `addTab()`** (début de la méthode)
```python
def addTab(self, notebook, host):
    if getattr(host, 'protocol', 'ssh') == 'rdp':
        return self._open_rdp_tab(notebook, host)
    # ... suite normale VTE pour SSH/Telnet
```

**Point 5 — Méthode `_open_rdp_tab()`** (dans `class Wmain`)
```python
def _open_rdp_tab(self, notebook, host):
    tab = RdpTab(host)
    # Construire la commande xfreerdp
    cmd = [RDP_BIN, f"/v:{host.host}:{host.port}",
           f"/u:{host.user}", "/cert:ignore",
           "/dynamic-resolution"]
    if host.password:
        cmd.append(f"/p:{host.password}")
    tab.launch(cmd)
    notebook.append_page(tab, ...)
```

**Point 6 — ComboBox Protocol dans le dialogue host**
Dans le dialogue d'édition/création de host :
- Ajouter une ComboBox : `ssh / telnet / rdp / local`
- Port auto selon protocole : ssh→22, rdp→3389, telnet→23

### Commande xfreerdp construite
```bash
xfreerdp /v:HOST:PORT /u:USER [/d:DOMAIN] [/p:PASS] \
         /cert:ignore /dynamic-resolution [OPTIONS_LIBRES]
```
Si `user` contient `\` → domaine séparé : `/d:DOMAIN /u:USER`

### Dépendance
```bash
sudo apt install freerdp2-x11   # ou freerdp3-x11
```

### Validation
1. Créer un host avec protocole RDP
2. Double-clic → onglet RDP s'ouvre dans GCM
3. xfreerdp se lance, log visible dans l'onglet
4. Tester Connecter / Déconnecter / Reconnecter

---

## Étape 6 — xfreerdp embarqué via GtkSocket / XEmbed

### Objectif
Améliorer l'étape 5 : au lieu d'une fenêtre xfreerdp indépendante, **embarquer la session RDP directement dans l'onglet GCM** comme VTE le fait pour SSH.

### Technique : XEmbed via GtkSocket

```
┌─────────────────────────────┐
│  GCM — onglet RDP           │
│  ┌───────────────────────┐  │
│  │   Gtk.Socket          │  │
│  │   (XEmbed host)       │  │
│  │                       │  │
│  │   xfreerdp window     │  │
│  │   (plug XEmbed)       │  │
│  │                       │  │
│  └───────────────────────┘  │
│  [Reconnecter] [Déconnecter]│
└─────────────────────────────┘
```

| Composant | Rôle |
|---|---|
| `Gtk.Socket` | Crée une fenêtre X11 hôte (conteneur XEmbed) |
| `socket.get_id()` | Retourne le `XID` (identifiant fenêtre X11) |
| `xfreerdp /parent-window:XID` | xfreerdp s'accroche dans la fenêtre GTK |
| `socket.connect("plug-removed", ...)` | Signal déclenché à la déconnexion RDP |

### Contraintes et conditions
- **Requiert X11** (pas Wayland pur) — OK sur DOCKER45 (Xorg)
- **xfreerdp ≥ 2.0** pour le support `/parent-window`
- Redimensionnement : `/dynamic-resolution` + `socket.connect("size-allocate", ...)` pour envoyer le resize à xfreerdp

### Actions détaillées

**6.1 — Remplacer `RdpTab` de l'étape 5 par `RdpEmbeddedTab`**

```python
class RdpEmbeddedTab(Gtk.Box):
    def __init__(self, host):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        # Barre d'outils (statut + boutons)
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.status_label = Gtk.Label(label="Déconnecté")
        btn_connect = Gtk.Button(label="Connecter")
        btn_disconnect = Gtk.Button(label="Déconnecter")
        toolbar.pack_start(self.status_label, False, False, 0)
        toolbar.pack_end(btn_disconnect, False, False, 0)
        toolbar.pack_end(btn_connect, False, False, 0)

        # Socket XEmbed (zone RDP)
        self.socket = Gtk.Socket()
        self.socket.connect("plug-removed", self._on_plug_removed)
        self.socket.connect("realize", self._on_socket_realized)

        self.pack_start(toolbar, False, False, 0)
        self.pack_start(self.socket, True, True, 0)

        btn_connect.connect("clicked", lambda w: self._launch(host))
        btn_disconnect.connect("clicked", lambda w: self._kill())

        self._process = None
        self._host = host

    def _on_socket_realized(self, widget):
        """Le socket est prêt, on peut récupérer le XID."""
        self._xid = self.socket.get_id()

    def _launch(self, host):
        xid = self.socket.get_id()
        cmd = [RDP_BIN,
               f"/v:{host.host}:{host.port}",
               f"/u:{host.user}",
               "/cert:ignore",
               "/dynamic-resolution",
               f"/parent-window:{hex(xid)}"]
        if host.password:
            cmd.append(f"/p:{host.password}")
        self._process = subprocess.Popen(cmd)
        self.status_label.set_text(f"Connecté — {host.host}")

    def _kill(self):
        if self._process:
            self._process.terminate()
            self._process = None
        self.status_label.set_text("Déconnecté")

    def _on_plug_removed(self, socket):
        """xfreerdp s'est terminé — mettre à jour le statut."""
        self.status_label.set_text("Session terminée")
        self._process = None
        return True  # Garder le socket (ne pas le détruire)
```

**6.2 — Gestion du redimensionnement**
Quand l'onglet est redimensionné, envoyer `SIGUSR1` à xfreerdp (xfreerdp ≥ 2.4 supporte le resize dynamique via signal) ou utiliser `/size:WxH` au lancement et reconstruire la connexion si resize.

**6.3 — Fallback transparent**
Si `Gtk.Socket` n'est pas disponible (Wayland sans XWayland), retomber automatiquement sur le comportement de l'étape 5 (fenêtre externe).

```python
def _open_rdp_tab(self, notebook, host):
    # Tenter XEmbed
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
        socket_test = Gtk.Socket()
        tab = RdpEmbeddedTab(host)
    except Exception:
        tab = RdpTab(host)   # fallback étape 5
    ...
```

**6.4 — Validation**
1. Vérifier que `Gtk.Socket` fonctionne sous X11 : `python3 -c "from gi.repository import Gtk; s=Gtk.Socket(); print('XID serait:', s.get_id())"`
2. Tester l'embarquement avec une simple fenêtre X (`xterm -into XID`) avant xfreerdp
3. Tester avec xfreerdp réel sur un hôte Windows ou RDP test

### Résultat attendu
La session RDP s'affiche directement dans l'onglet GCM. L'expérience est identique à SSH.

---

## Étape 7 — Packaging et release v1.3

### Objectif
Livrer une version propre, taggée et documentée.

### Actions

**7.1 — Mettre à jour la version**
Fichier : `gnome_connection_manager.py`, ligne contenant `app_version`
```python
app_version = "1.3.0"
```

**7.2 — Mettre à jour le README**
Ajouter une section **Nouveautés v1.3** :
- Import libvirt (détection automatique des VMs depuis virt-manager)
- Support RDP via xfreerdp (embarqué dans les onglets GCM)
- Compatibilité Python 3.13 / GTK 3.24+

**7.3 — Mettre à jour le CHANGELOG**
Créer `CHANGELOG.md` avec les détails des changements.

**7.4 — Dépendances**
Créer ou mettre à jour `requirements.txt` :
```
paramiko>=3.0
```
Ajouter dans le README :
```bash
pip3 install paramiko
sudo apt install freerdp2-x11   # ou freerdp3-x11
```

**7.5 — Commit et tag**
```bash
git add -A
git commit -m "v1.3.0 — Python 3.13, GTK3 moderne, import libvirt, support RDP XEmbed"
git tag -a v1.3.0 -m "Version 1.3.0"
git push origin develop
git push origin v1.3.0
# Optionnel : merge vers master
git checkout master
git merge develop
git push origin master
```

**7.6 — Release GitHub**
```bash
gh release create v1.3.0 --title "GCM v1.3.0" --notes-file CHANGELOG.md
```

---

## Suivi de progression

| # | Étape | Responsable | Statut | Commit |
|---|---|---|---|---|
| 0 | Fork GitHub + config remotes | Mathilde + Claude | ✅ | — |
| 1 | Bugs Python 3.13 (`xrange`, `__future__`) | Claude | ✅ | `init` |
| 1b | Bugs upstream #81 #82 #87 #88 #89 #64 #67 #66 | Claude | ✅ | `1b` |
| 2 | APIs GTK3 dépréciées + 188 docstrings (#110) | Claude | ✅ | étape 2 |
| 3 | Remplacement SimpleGladeApp → GCMBase | Claude | ✅ | `c169a90` |
| 4 | Import libvirt v2 + détection Windows | Claude | ✅ | étape 4 |
| 5 | RDP externe (xfreerdp subprocess) | Claude | ✅ | étape 5 |
| 6 | RDP XEmbed GtkSocket (`/parent-window`) | Claude | ✅ | `8db68fa` |
| 7 | Release v1.3.0 (tag + gh release) | Claude | ✅ | `cdec80e` / `v1.3.0` |
| 8 | Cleanup kuthulu/donate/SimpleGladeApp | Claude | ✅ | `f44b388` |
| 9 | Fix `_rdp_socket_available()` Wayland | Claude | ✅ | `f44b388` |
| 10 | v1.3.1 bugfixes (vte_feed, RDP signal, RDP opts) | Claude | ✅ | `08a48a1` |
| 11 | 16 langues i18n (uk/ja/ar/tr/nl/cs/sv/nb) (#76 #100) | Claude | ✅ | `08a48a1` |
| 12 | VncTab + SpiceTab (#102) | Claude | ✅ | `1394da1` |
| 13 | SerialTab RS-232/485 + 11 templates constructeurs | Claude | ✅ | `1394da1` |
| 14 | 379 tests unitaires pytest (#111) | Claude | ✅ | `1394da1` |
| 15 | Fix save_host_to_ini TypeError Python 3 | Claude | ✅ | `1394da1` |
| 16 | Fix encrypt_old/decrypt_old Python 3 bytes | Claude | ✅ | `1394da1` |
| 17 | Documentation-fr.md + README.md | Claude | ✅ | en cours |
| 18 | Release v1.3.1 | Claude | 🔲 | — |

**Légende :** 🔲 À faire · 🔄 En cours · ✅ Terminé · ❌ Bloqué

---

## Notes techniques transversales

### Décisions d'architecture prises
| Décision | Raison |
|---|---|
| GTK3 (pas GTK4) | GTK4 non installé sur DOCKER45 ; VTE/GTK4 peu mature ; migration sans bénéfice visible |
| Pas de nmap dans import libvirt | Éviter les blocages UI GTK |
| Thread worker pour imports SSH | UI non gelée pendant l'inventaire virsh/paramiko |
| XEmbed pour RDP (étape 6) | Intégration native dans les onglets GCM, expérience uniforme SSH/RDP |
| Fallback RDP externe | Si X11/XEmbed indisponible (Wayland pur), fenêtre xfreerdp externe |
| Auth SSH par clé uniquement | Sécurité — jamais de mot de passe en transit pour l'inventaire libvirt |
| Masquage `/p:****` dans log RDP | Sécurité — pas de mot de passe RDP en clair dans l'UI |
| Détection Windows par nom VM | `virsh dumpxml` ne fournit pas toujours l'OS type de façon fiable |

### Fichiers du projet
```
gnome-connection-manager/
├── gnome_connection_manager.py    ← fichier principal (modifié étapes 1-6)
├── SimpleGladeApp.py              ← supprimé à l'étape 3
├── gnome-connection-manager.glade ← modifié étape 2+3
├── pyAES.py                       ← inchangé
├── urlregex.py                    ← inchangé
├── style.css                      ← inchangé
├── fork/
│   ├── ROADMAP-GCM-v1.3.md       ← CE FICHIER
│   ├── gcm_import_libvirt_v2.py  ← source patch étape 4
│   ├── gcm_rdp.py                ← source patch étape 5
│   ├── claude.md                 ← historique session v1
│   ├── claude_v2.md              ← historique session v2
│   └── claude_v3.md              ← historique session v3
└── requirements.txt               ← créé étape 7
```

### Environnement de développement
- Machine : DOCKER45 (192.168.105.45), Proxmox VM
- Python : 3.13.7
- GTK : 3.24.49 + python3-gi 3.50.0
- Dépôt local : `/app/gnome-connection-manager`
- Remote origin (cible) : https://github.com/MathildeDec/gnome-connection-manager
- Remote upstream (source) : https://github.com/kuthulux/gnome-connection-manager

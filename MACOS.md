# Running GCM on macOS

GCM is a GTK 3 application. There is no native macOS package, but it runs from source on macOS using GTK 3 and VTE from [Homebrew](https://brew.sh). Windows are drawn with GTK's native macOS backend, so XQuartz is not needed.

Tested with:

| Component | Version |
|---|---|
| macOS | 27.0.1 (Apple Silicon) |
| Homebrew | 7.0.10 |
| Python (Homebrew) | 3.15.0 |
| GTK | 3.24.52 |
| VTE | 0.84.1 |
| PyGObject | 3.58.1 |
| pycairo | 1.29.2 |

Every command below uses `$(brew --prefix)` instead of a hardcoded Homebrew path, so the same steps should work on Intel Macs, but they have not been tested there yet.

---

## 1. Prerequisites

Install the Xcode Command Line Tools (Homebrew needs them, and PyGObject is compiled from source):

```bash
xcode-select --install
```

Install Homebrew by following the instructions on [brew.sh](https://brew.sh).

`ssh` and `expect` ship with macOS, so there is nothing to install for them. You can check that they are present with:

```bash
/usr/bin/ssh -V
/usr/bin/expect -v
```

## 2. Install GTK 3 and VTE

```bash
brew install gtk+3 vte3 pkg-config gobject-introspection cairo adwaita-icon-theme
```

This pulls in about 100 dependencies, including Homebrew's own Python, and can take 10 minutes or more.

## 3. Get the source

```bash
git clone https://github.com/kuthulux/gnome-connection-manager.git
cd gnome-connection-manager
```

## 4. Create a virtual environment

Create the virtual environment with Homebrew's Python. The Python that ships with macOS (`/usr/bin/python3`) can't load Homebrew's GTK libraries.

```bash
"$(brew --prefix)/bin/python3" -m venv venv
./venv/bin/pip install -r requirements.txt
```

PyGObject is compiled against the Homebrew libraries during this step, which takes under a minute.

To check that GTK and VTE load correctly:

```bash
./venv/bin/python -c "import gi; gi.require_version('Gtk', '3.0'); gi.require_version('Vte', '2.91'); from gi.repository import Gtk, Vte; print('GTK and VTE OK')"
```

## 5. Run GCM

```bash
LANG=en_US.UTF-8 ./venv/bin/python gnome_connection_manager.py
```

* Start GCM with the virtual environment's Python as shown. Running `./gnome_connection_manager.py` directly does not work on macOS, because its first line points at `/usr/bin/python3`.
* `LANG` sets the UI language. GCM's built-in text is Spanish and every other language comes from a translation, so if your terminal reports `LANG=C` or `LANG=C.UTF-8` (run `echo $LANG` to check), the UI shows up in Spanish. Replace `en_US.UTF-8` with another locale to use a different translation: `de_DE`, `fr_FR`, `it_IT`, `ko_KR`, `pl_PL`, `pt_BR` or `ru_RU`, each followed by `.UTF-8`.

Optionally, add a `gcm` shell alias. Run this from the `gnome-connection-manager` folder, then open a new terminal:

```bash
echo "alias gcm='LANG=en_US.UTF-8 \"$PWD/venv/bin/python\" \"$PWD/gnome_connection_manager.py\"'" >> ~/.zshrc
```

## 6. Optional: open GCM like a regular Mac app

When GCM is started from Terminal, macOS shows it as "Python", with Python's icon, in the Dock and in the Cmd+Tab app switcher. To give GCM its own name and icon, and to open it from Spotlight, Launchpad or the Dock, create an app for your copy of GCM:

```bash
./macos/create-app.sh
```

This creates `~/Applications/Gnome Connection Manager.app`. To create it in another folder, pass the folder, for example `./macos/create-app.sh /Applications`.

* The app runs GCM from this folder with this virtual environment, so keep both where they are. If you move the folder or recreate the virtual environment, for example after Homebrew upgrades Python to a new version, run the script again.
* When opened from Finder, the Dock or Spotlight, GCM uses the language of your macOS region (**System Settings → General → Language & Region**). If GCM has no translation for that language, it uses English.
* Terminals opened in GCM get the same `PATH` as in Terminal, including Homebrew's commands.

---

## Keyboard shortcuts

On macOS, GCM's shortcuts use the Command key, like other Mac apps. This also leaves Ctrl keys such as Ctrl+W, Ctrl+H and Ctrl+F to the shell running in the terminal.

| Action | macOS | Linux |
|---|---|---|
| Copy | Cmd+C | Ctrl+Shift+C |
| Paste | Cmd+V | Ctrl+Shift+V |
| Copy all | Cmd+A | Ctrl+Shift+A |
| Save buffer | Cmd+S | Ctrl+S |
| Find | Cmd+F | Ctrl+F |
| Find next | Cmd+G | Ctrl+G |
| Find previous | Cmd+Shift+G | Ctrl+H |
| Filter hosts | Cmd+P | Ctrl+Shift+F |
| Close tab | Cmd+W | Ctrl+W |
| Reconnect | Cmd+R | Ctrl+N |
| Connect | Cmd+Return | Ctrl+Return |
| Reset terminal | Cmd+K | Ctrl+Shift+K |
| Clone tab | Cmd+D | Ctrl+Shift+D |
| New local tab | Cmd+T | Ctrl+Shift+N |
| Fullscreen | Cmd+Ctrl+F | F11 |
| Go to tab 1–9 | Cmd+1–9 | Alt+1–9 |
| Next / previous tab | Ctrl+Tab / Ctrl+Shift+Tab | Ctrl+Tab / Ctrl+Shift+Tab |

Next and previous tab keep Ctrl+Tab because Cmd+Tab switches between apps on macOS.

If your settings come from Linux, any shortcut that is still set to its Linux default switches to the macOS default when GCM starts. Shortcuts you have customised are kept. To change a shortcut, open **Edit → Settings → Shortcuts** and press the new key combination for it.

Find opens a find bar under the toolbar. Return finds the next match, Shift+Return the previous one, and Escape closes the bar and returns to the terminal.

---

## Menu bar

GCM's File, Edit, View, Servers and Help menus appear in the macOS menu bar at the top of the screen, and the menu bar inside the window is hidden. The app menu adds About, Settings (Cmd+,), Hide (Cmd+H) and Quit (Cmd+Q). Quit works like closing the window: it asks first if **Confirm on exit** is on in **Edit → Settings** and consoles are open, and it saves your settings.

The items in GCM's own menus have no keyboard shortcuts in the menu bar, so keys such as Cmd+C keep going to the terminal and GCM's shortcuts work as listed above.

---

## Dark theme

By default GCM follows the macOS appearance in **System Settings → Appearance**, including the window's title bar, and switches within a couple of seconds when macOS changes between Light and Dark. To always use one look, set **Theme** in **Edit → Settings** to **Light** or **Dark**.

The theme covers the window, menus and dialogs. Terminal colors are set separately in **Edit → Settings → Colors**, and hosts that have their own colors keep them. Color and font changes apply to open tabs as soon as you press OK.

---

## Folder colors

To tell environments apart, right-click a folder in the host list and choose **Color**. The folder gets a colored dot in the list, and tabs of hosts in it get a colored stripe along their top edge. Subfolders use their parent's color unless you give them their own. Folder colors are saved with your hosts and included in **File → Export servers**.

---

## Migrating your hosts from Linux

GCM keeps its settings and hosts in `~/.gcm/`. Saved passwords are encrypted with a key made from your login name plus the `~/.gcm/.gcm.key` file, so choose the method that fits your setup.

### Option A: Export and import (works even if your usernames differ)

1. On Linux, choose **File → Export servers**, pick a file name, and set a password.
2. Copy the exported file to your Mac.
3. On the Mac, start GCM once and quit it with **File → Quit**. Until GCM has saved its settings for the first time, it checks import passwords using an older format, so importing during the very first session fails with "Invalid password".
4. Start GCM again, choose **File → Import servers**, select the file, and enter the password. This replaces the current host list.

### Option B: Copy the config files (same username only)

Use this only if `whoami` prints the same name on both machines. Copy both files before starting GCM on the Mac for the first time, replacing `linux-host` with your Linux machine's address:

```bash
mkdir -p ~/.gcm && chmod 700 ~/.gcm
scp linux-host:~/.gcm/gcm.conf linux-host:~/.gcm/.gcm.key ~/.gcm/
chmod 600 ~/.gcm/.gcm.key
```

If the usernames differ, your hosts still load but their saved passwords won't decrypt. Use Option A instead.

### After migrating

Home folders on macOS are `/Users/<name>`, not `/home/<name>`, so Linux paths saved in GCM won't exist on the Mac. Check:

* The private key file of each host that uses one, for example `/home/you/.ssh/id_rsa` becomes `/Users/you/.ssh/id_rsa`.
* If you used Option B: **Logs path** in **Edit → Settings**, if you log sessions to files.

---

## Known limitations on macOS

* **Telnet:** macOS no longer includes `telnet`. Installing it with `brew install telnet` should make telnet hosts work as long as they don't have both a saved user and password. Hosts that do have both go through `ssh.expect`, which hardcodes `/usr/bin/telnet`, so they still fail. SSH connections are not affected.
* **Donate button:** does nothing, because it opens the page with the Linux-only `xdg-open` command.
* **Transparency:** when **Transparency** in **Edit → Settings** is above 0, the macOS title bar becomes see-through along with the terminals, because GTK makes the whole window clear. Restart GCM after turning Transparency on or off.
* **Quit from the Dock:** right-clicking GCM in the Dock and choosing Quit, or logging out, closes GCM straight away, without asking about open consoles and without saving settings such as the window size. GTK 3 ends the app on this path before GCM can respond. Quit with Cmd+Q or **File → Quit** instead.
* **Intel Macs:** not tested yet.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'cairo'`**

GCM was started with the Python that ships with macOS, either by running `/usr/bin/python3` or `./gnome_connection_manager.py`. Start it with `./venv/bin/python gnome_connection_manager.py` instead.

**`python3-gi and gir1.2-vte-2.91 required`**

GCM couldn't load GTK or VTE. Check that both are installed with `brew list gtk+3 vte3`, and that the virtual environment was created with Homebrew's Python: the `home` line in `venv/pyvenv.cfg` should start with the path printed by `brew --prefix`. If it doesn't, delete the `venv` folder and repeat step 4.

**`pip install` fails while building PyGObject or pycairo**

Make sure step 2 finished without errors and the Xcode Command Line Tools are installed. If the error says pkg-config can't find a dependency, point it at Homebrew's libraries and run `pip install` again:

```bash
export PKG_CONFIG_PATH="$(brew --prefix)/lib/pkgconfig:$(brew --prefix)/share/pkgconfig"
./venv/bin/pip install -r requirements.txt
```

**Menus and dialogs are in Spanish**

`LANG` isn't set to a language GCM has a translation for. Start GCM with `LANG=en_US.UTF-8` as shown in step 5.

**The Gnome Connection Manager app doesn't open, or closes straight away**

Run the app's launcher from Terminal to see the error message:

```bash
"$HOME/Applications/Gnome Connection Manager.app/Contents/MacOS/gnome-connection-manager"
```

If the error mentions a missing file, the GCM folder or its virtual environment has moved or changed since the app was created. Run `./macos/create-app.sh` again.

**"Invalid password" when importing servers**

GCM hasn't saved its settings yet. Quit GCM once with **File → Quit**, start it again, and retry the import.

**Messages you can ignore**

These are printed in the terminal but don't affect GCM:

* `SyntaxWarning: "\." is an invalid escape sequence` from `urlregex.py`
* `Gtk-WARNING ... Attempting to add a widget with type GtkPaned to a container of type GtkWindow ...`
* `DeprecationWarning` lines
* `Invalid entry in configuration file: No section: 'options'` on the first launch, before any settings have been saved

---

## Why macOS needs extra steps

GTK, VTE and their Python bindings are system libraries on Linux distributions. On macOS they come from Homebrew, and PyGObject has to be built against them inside a virtual environment.

Python on macOS also lacks `locale.bindtextdomain`, which only exists in Python builds linked against glibc. GtkBuilder needs that call to translate the strings in `gnome-connection-manager.glade`, so when it is missing, `SimpleGladeApp.py` binds the translation domain through Homebrew's `libintl` library instead. Linux behaviour is unchanged.

macOS takes an app's name and icon from the `.app` bundle that contains the running executable. Homebrew's Python always switches to the interpreter inside its own `Python.app`, so GCM appears as "Python". `macos/create-app.sh` puts a link to that interpreter inside a GCM bundle and starts it from there, setting `__PYVENV_LAUNCHER__` the same way Python's own launcher does, so the interpreter still uses the virtual environment.

GTK's macOS backend reports the Command key as the `META` modifier. GCM names it `CMD` in shortcuts, but only on macOS: on Linux, `META` can be set together with Super or Alt, and recognising it there would rename shortcuts that people have already saved.

GTK dialogs also keep a transparent visual left over from a header bar that GTK removes during setup, which on macOS makes their title bars see-through, so on macOS GCM switches each dialog back to the normal visual before it is first shown.

GTK 3 only puts menus in the macOS menu bar for a registered `Gtk.Application`. GCM registers one on macOS while keeping its existing `Gtk.main()` loop, and builds the menu bar from the menus inside the window each time they change, so both always match.

GTK 3 doesn't follow the macOS appearance by itself. When **Theme** is set to **System**, GCM reads the appearance from AppKit and turns GTK's dark theme on or off to match. For **Light** and **Dark**, it also sets the app's appearance so the native macOS title bar matches the GTK theme.

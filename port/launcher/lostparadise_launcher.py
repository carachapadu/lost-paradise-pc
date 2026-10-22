#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fist of the North Star: Lost Paradise - PC launcher (Tk, standard library only).

Picks the game folder you dumped from your own console (CUSA12781), keeps the settings in
tlg.ini (the same file the in-game menu writes), prepares the game and starts tlg-probe through
run.py. No game file is bundled or copied anywhere except a small working folder made of links.

Packaged executable roles (PyInstaller): --script <file> [args] runs a preparation script,
--run [args] runs run.py (what "Play" and the in-game restart start), --play starts with the saved
settings and no window (shortcuts).
"""
import json
import multiprocessing
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import threading
import time

TITLE = 'Fist of the North Star: Lost Paradise — PC'
SERIAL = 'CUSA12781'
HERE = Path(__file__).resolve().parent
PORT = HERE.parent if not getattr(sys, 'frozen', False) else Path(sys.executable).resolve().parent
sys.path.insert(0, str(PORT / 'scripts'))


# ------------------------------------------------------------------------------ data folders
def config_dir():
    if os.name == 'nt':
        return Path(os.environ.get('APPDATA') or Path.home() / 'AppData' / 'Roaming') / 'LostParadise-PC'
    return Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'lostparadise-pc'


def settings_path():
    return config_dir() / 'launcher.json'


def load_settings():
    try:
        data = json.loads(settings_path().read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(settings):
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def data_dir(settings):
    """tlg.ini, out/, saves (user/) and the shader cache (user/cache): outside the program folder,
    so a new version never touches them."""
    return Path(settings.get('data_dir') or config_dir() / 'data')


def user_dir(settings):
    return data_dir(settings) / 'user'


# ------------------------------------------------------------------------------- game folder
def find_game_root(chosen):
    """The folder holding eboot.bin/eboot.elf: the chosen one, or one level below it."""
    chosen = Path(chosen)
    for candidate in [chosen, *sorted(p for p in chosen.glob('*') if p.is_dir())]:
        if (candidate / 'eboot.bin').is_file() or (candidate / 'eboot.elf').is_file():
            return candidate
    return None


def link_entry(source, target):
    """Directory junction/symlink, else a hard link or a copy for files; never touches the source."""
    if target.exists() or target.is_symlink():
        return
    if source.is_dir():
        if os.name == 'nt':
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(target), str(source)], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if target.exists():
                return
        try:
            target.symlink_to(source, target_is_directory=True)
        except OSError:
            shutil.copytree(source, target)
        return
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def prepare_game(settings, log):
    """Returns the folder run.py uses as TLG_GAME_DIR. A dump that already has eboot.bin is used
    as it is; one with only the decrypted eboot.elf gets a working folder (links + eboot.bin)."""
    root = find_game_root(settings.get('game_dir', ''))
    if not root:
        raise RuntimeError('No eboot.bin or eboot.elf in the chosen folder.')
    if (root / 'eboot.bin').is_file():
        return root
    work = data_dir(settings) / 'game' / SERIAL
    work.mkdir(parents=True, exist_ok=True)
    for entry in root.iterdir():
        if entry.name.lower() in ('eboot.elf', 'eboot.bin'):
            continue
        link_entry(entry, work / entry.name)
    elf = root / 'eboot.elf'
    target = work / 'eboot.bin'
    if not target.is_file() or target.stat().st_size != elf.stat().st_size:
        log(f'Copying {elf.name} to eboot.bin (decrypted executable)')
        shutil.copy2(elf, target)
    return work


# ----------------------------------------------------------------------------- tlg.ini options
DISPLAY_MODES = ('Windowed', 'Borderless', 'Fullscreen')
DEFAULT_OPTIONS = {'display_mode': 'Windowed', 'vsync': '1', 'async_shaders': '1',
                   'deferred_readback': '1', 'stale_readback': '1', 'mouse_enabled': '1'}
TOGGLES = {  # launcher key -> (environment variable, label)
    'bp09': ('TLG_BP09', 'Texture fix BP09 (blocky/checkered textures)'),
    'block1d': ('TLG_BLOCK1D', 'Treat compressed 1D textures as 2D (texture artifacts)'),
}


def ini_path(settings):
    return data_dir(settings) / 'tlg.ini'


def read_options(settings):
    import graphics_options
    ini = graphics_options.read_ini(ini_path(settings))
    return {key: ini.get(key, value) for key, value in DEFAULT_OPTIONS.items()}


def write_options(settings, options):
    import graphics_options
    data_dir(settings).mkdir(parents=True, exist_ok=True)
    graphics_options.write_keys(ini_path(settings), options)


def build_env(settings):
    env = dict(os.environ)
    data = data_dir(settings)
    env.update({'TLG_SKIP_LINK_LIBC': '1', 'TLG_DATA_DIR': str(data), 'TLG_USER_DIR': str(user_dir(settings)),
                'ISS_USER_DIR': str(user_dir(settings)), 'TLG_CONFIG': str(ini_path(settings)),
                'PYTHONIOENCODING': 'utf-8'})
    for key, (name, _label) in TOGGLES.items():
        if settings.get(key):
            env[name] = '1'
    return env


# --------------------------------------------------------------------------------- run / game
def run_command(extra=()):
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--run', *extra]
    return [sys.executable, str(PORT / 'run.py'), *extra]


def clear_shader_cache(settings):
    cache = [p for p in (user_dir(settings) / 'cache').glob('*') if p.is_dir()] \
        if (user_dir(settings) / 'cache').is_dir() else []
    for folder in cache:
        shutil.rmtree(folder, ignore_errors=True)
    return len(cache)


def backup_saves(settings):
    savedata = user_dir(settings) / 'savedata'
    if not savedata.is_dir():
        return None
    target = user_dir(settings) / 'savedata_backups' / time.strftime('%Y%m%d-%H%M%S')
    shutil.copytree(savedata, target)
    return target


def open_folder(path):
    Path(path).mkdir(parents=True, exist_ok=True)
    if os.name == 'nt':
        os.startfile(str(path))  # noqa: S606 - the player's own folder
    else:
        subprocess.Popen(['xdg-open', str(path)], stdin=subprocess.DEVNULL)


def play(settings, log=print, wait=False):
    game = prepare_game(settings, log)
    env = build_env(settings)
    env['TLG_GAME_DIR'] = str(game)
    data_dir(settings).mkdir(parents=True, exist_ok=True)
    logfile = data_dir(settings) / 'last-run.log'
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
    handle = open(logfile, 'w', encoding='utf-8', errors='replace')
    process = subprocess.Popen(run_command(), cwd=str(PORT), env=env, stdin=subprocess.DEVNULL,
                               stdout=handle, stderr=subprocess.STDOUT, creationflags=flags)
    log(f'Started (log: {logfile})')
    return process.wait() if wait else process


# -------------------------------------------------------------------------------------- UI
def main_window():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    settings = load_settings()
    root = tk.Tk(className='lostparadise-pc')
    root.title(TITLE)
    root.geometry('720x600')
    try:
        ttk.Style().theme_use('clam')
    except tk.TclError:
        pass
    icon = HERE / 'lostparadise.png'
    if icon.is_file():
        try:
            root.iconphoto(True, tk.PhotoImage(file=str(icon)))
        except tk.TclError:
            pass

    frame = ttk.Frame(root, padding=12)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Fist of the North Star: Lost Paradise', font=('', 14, 'bold')).pack(anchor='w')
    ttk.Label(frame, text=f'PC — {SERIAL} v1.09. You provide the game files from your own console.').pack(anchor='w')

    notebook = ttk.Notebook(frame)
    notebook.pack(fill='both', expand=True, pady=8)
    tab_game, tab_video, tab_input, tab_data = (ttk.Frame(notebook, padding=10) for _ in range(4))
    for tab, name in ((tab_game, 'Game'), (tab_video, 'Graphics'), (tab_input, 'Controls'), (tab_data, 'Saves / cache')):
        notebook.add(tab, text=name)

    status = tk.StringVar(value='')
    options = read_options(settings)

    # --- Game tab
    game_var = tk.StringVar(value=settings.get('game_dir', ''))
    ttk.Label(tab_game, text='Game folder (the dump with eboot.bin or the decrypted eboot.elf):').pack(anchor='w')
    row = ttk.Frame(tab_game)
    row.pack(fill='x', pady=4)
    ttk.Entry(row, textvariable=game_var).pack(side='left', fill='x', expand=True)

    def browse():
        chosen = filedialog.askdirectory(title='Game folder', initialdir=game_var.get() or str(Path.home()))
        if chosen:
            game_var.set(chosen)
            check_game()

    ttk.Button(row, text='Browse...', command=browse).pack(side='left', padx=4)
    game_info = tk.StringVar()
    ttk.Label(tab_game, textvariable=game_info, wraplength=640).pack(anchor='w', pady=4)

    def check_game():
        root_dir = find_game_root(game_var.get()) if game_var.get() else None
        if not root_dir:
            game_info.set('No eboot.bin / eboot.elf found yet.')
            return False
        sfo = (root_dir / 'sce_sys' / 'param.sfo').is_file()
        game_info.set(f'Found: {root_dir}' + ('' if sfo else '  (sce_sys/param.sfo missing: check the dump)'))
        return True

    check_game()
    ttk.Label(tab_game, text='Open the in-game menu with Insert or R3+L2. Esc releases the mouse.').pack(anchor='w', pady=8)

    # --- Graphics tab
    display_var = tk.StringVar(value=options['display_mode'] if options['display_mode'] in DISPLAY_MODES else 'Windowed')
    vsync_var = tk.BooleanVar(value=options['vsync'] != '0')
    async_var = tk.BooleanVar(value=options['async_shaders'] != '0')
    deferred_var = tk.BooleanVar(value=options['deferred_readback'] != '0')
    stale_var = tk.BooleanVar(value=options['stale_readback'] != '0')
    ttk.Label(tab_video, text='Display mode').grid(row=0, column=0, sticky='w')
    ttk.Combobox(tab_video, textvariable=display_var, values=DISPLAY_MODES, state='readonly', width=14).grid(row=0, column=1, sticky='w', padx=6)
    ttk.Checkbutton(tab_video, text='VSync', variable=vsync_var).grid(row=1, column=0, columnspan=2, sticky='w')
    ttk.Checkbutton(tab_video, text='Compile shaders in the background (less stutter)', variable=async_var).grid(row=2, column=0, columnspan=2, sticky='w')
    ttk.Checkbutton(tab_video, text='Deferred image readback', variable=deferred_var).grid(row=3, column=0, columnspan=2, sticky='w')
    ttk.Checkbutton(tab_video, text='Stale readback', variable=stale_var).grid(row=4, column=0, columnspan=2, sticky='w')
    toggle_vars = {}
    ttk.Separator(tab_video).grid(row=5, column=0, columnspan=2, sticky='ew', pady=8)
    ttk.Label(tab_video, text='Texture workarounds (only if you see blocky or checkered textures):').grid(row=6, column=0, columnspan=2, sticky='w')
    for i, (key, (_name, label)) in enumerate(TOGGLES.items()):
        toggle_vars[key] = tk.BooleanVar(value=bool(settings.get(key)))
        ttk.Checkbutton(tab_video, text=label, variable=toggle_vars[key]).grid(row=7 + i, column=0, columnspan=2, sticky='w')
    ttk.Label(tab_video, text='The game runs at a fixed 60 FPS; resolution and frame rate patches are not available for this build.',
              wraplength=640).grid(row=10, column=0, columnspan=2, sticky='w', pady=8)

    # --- Controls tab
    mouse_var = tk.BooleanVar(value=options['mouse_enabled'] != '0')
    ttk.Checkbutton(tab_input, text='Mouse and keyboard support', variable=mouse_var).pack(anchor='w')
    ttk.Label(tab_input, wraplength=640, text='Controllers (XInput/DualShock/DualSense via SDL) work without setup. '
              'Key bindings, mouse sensitivity and the rest are edited in the in-game menu (Insert or R3+L2) '
              'and stored in tlg.ini.').pack(anchor='w', pady=8)
    ttk.Button(tab_input, text='Open the settings file (tlg.ini) folder', command=lambda: open_folder(data_dir(settings))).pack(anchor='w')

    # --- Saves tab
    save_var = tk.StringVar(value=str(data_dir(settings)))
    ttk.Label(tab_data, text='Data folder (settings, saves, shader cache):').pack(anchor='w')
    row = ttk.Frame(tab_data)
    row.pack(fill='x', pady=4)
    ttk.Entry(row, textvariable=save_var).pack(side='left', fill='x', expand=True)

    def browse_data():
        chosen = filedialog.askdirectory(title='Data folder', initialdir=save_var.get())
        if chosen:
            save_var.set(chosen)

    ttk.Button(row, text='Browse...', command=browse_data).pack(side='left', padx=4)

    def act(function, done):
        collect()
        try:
            status.set(done(function(settings)))
        except OSError as error:
            messagebox.showerror(TITLE, str(error))

    ttk.Button(tab_data, text='Open saves folder', command=lambda: open_folder(user_dir(settings) / 'savedata')).pack(anchor='w', pady=2)
    ttk.Button(tab_data, text='Back up saves now', command=lambda: act(
        backup_saves, lambda r: f'Saves copied to {r}' if r else 'No saves yet.')).pack(anchor='w', pady=2)
    ttk.Button(tab_data, text='Clear shader cache (rebuilt on next play; first minutes may stutter)', command=lambda: act(
        clear_shader_cache, lambda n: f'Shader cache cleared ({n} folder(s)).')).pack(anchor='w', pady=2)

    # --- Log + play
    log_box = tk.Text(frame, height=8, state='disabled', wrap='word')
    log_box.pack(fill='x')

    def log(text):
        log_box.configure(state='normal')
        log_box.insert('end', text + '\n')
        log_box.see('end')
        log_box.configure(state='disabled')

    def collect():
        settings['game_dir'] = game_var.get().strip()
        settings['data_dir'] = save_var.get().strip()
        for key, var in toggle_vars.items():
            settings[key] = bool(var.get())
        save_settings(settings)
        write_options(settings, {
            'display_mode': display_var.get(), 'vsync': int(vsync_var.get()), 'async_shaders': int(async_var.get()),
            'deferred_readback': int(deferred_var.get()), 'stale_readback': int(stale_var.get()),
            'mouse_enabled': int(mouse_var.get())})

    process = {'p': None}

    def watch(proc):
        proc.wait()
        root.after(0, lambda: (play_button.configure(state='normal'), status.set(f'Game closed (exit code {proc.returncode}).'),
                               show_log()))

    def show_log():
        try:
            tail = (data_dir(settings) / 'last-run.log').read_text(encoding='utf-8', errors='replace').splitlines()[-25:]
        except OSError:
            return
        log('--- end of last-run.log ---')
        for line in tail:
            log(line)

    def start():
        if not check_game():
            messagebox.showwarning(TITLE, 'Choose the game folder first (the dump with eboot.bin or eboot.elf).')
            return
        collect()
        try:
            proc = play(settings, log)
        except (RuntimeError, OSError) as error:
            messagebox.showerror(TITLE, str(error))
            return
        process['p'] = proc
        play_button.configure(state='disabled')
        status.set('Preparing and starting the game... the window opens in a moment.')
        threading.Thread(target=watch, args=(proc,), daemon=True).start()

    bottom = ttk.Frame(frame)
    bottom.pack(fill='x', pady=6)
    ttk.Label(bottom, textvariable=status).pack(side='left')
    play_button = ttk.Button(bottom, text='▶  Play', command=start)
    play_button.pack(side='right')
    ttk.Button(bottom, text='Open log', command=lambda: open_folder(data_dir(settings))).pack(side='right', padx=6)
    root.mainloop()


def main():
    multiprocessing.freeze_support()   # packaged: the shader list generator starts worker processes
    args = sys.argv[1:]
    if args[:1] == ['--script'] and len(args) > 1:
        sys.argv = args[1:]
        runpy.run_path(args[1], run_name='__main__')
        return 0
    if args[:1] == ['--run']:
        sys.argv = [str(PORT / 'run.py'), *args[1:]]
        runpy.run_path(str(PORT / 'run.py'), run_name='__main__')
        return 0
    if args[:1] == ['--play']:
        return play(load_settings(), wait=True)
    main_window()
    return 0


if __name__ == '__main__':
    sys.exit(main())

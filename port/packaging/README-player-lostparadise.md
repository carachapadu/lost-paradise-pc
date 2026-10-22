# Fist of the North Star: Lost Paradise — PC port (CUSA12781 v1.09)

**No game files are included.** You need your own copy of the game, dumped from your own PS4.
Based on the HayatoG PS4 "core" (GPL-2.0-or-later). Playable, in development.

## How to play
1. Run `Lost Paradise.exe`.
2. **Game** tab: pick your dump folder (the one with `eboot.bin`, or the decrypted `eboot.elf`, plus `sce_sys/`, `sce_module/`, `data/`...).
3. Adjust **Graphics** / **Controls** if you want, then press **Play**.
   `Play Lost Paradise.cmd` starts the game with the saved settings and no launcher window.

Requirements: Windows 10/11 64-bit, a Vulkan 1.3 GPU with up-to-date drivers.

## Tips
- In-game menu: `Insert` or `R3 + L2`. `Esc` releases the mouse.
- The first minutes may stutter while shaders compile; they are cached, so later runs are smooth.
- Blocky/checkered textures: enable the texture workarounds in **Graphics**.
- Settings, saves and cache live in `%APPDATA%\LostParadise-PC\data` (change it in **Saves / cache**). The launcher backs saves up on request.
- Log of the last run: `last-run.log` in that data folder.
- Output resolution (720p to 4K) is in **Graphics**: the game renders at 1080p and is upscaled (FSR 1 + sharpening) to the window size. Fixed 60 FPS.

Never share game files. The launcher only reads your dump and, for a decrypted `eboot.elf`, makes a small working folder of links.

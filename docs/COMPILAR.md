# Como compilar e empacotar (Windows) / Build and package (Windows)

Port nativo de **Fist of the North Star: Lost Paradise** (PS4, CUSA12781, v1.09). Nenhum arquivo do jogo faz parte do
repositório: use o dump do **seu** PS4.

## 1. Requisitos
- Windows 10/11 64-bit, GPU com Vulkan 1.3 e driver atualizado.
- [MSYS2](https://www.msys2.org) (`winget install MSYS2.MSYS2`) — use o shell **MSYS2 CLANG64**.
- [Python 3 do python.org](https://www.python.org/downloads/) (para o launcher e o empacotamento). Opcional: `pip install iced-x86==1.21.0`
  (só serve para CPUs sem MOVBE/BMI1/LZCNT).
- Git for Windows (para clonar; o Git do MSYS2 não tem o login do navegador).
- Seu dump do jogo: `eboot.bin` decriptado (ou `eboot.elf`), `sce_sys/`, `sce_module/libc.prx`, `sce_module/libSceFios2.prx`, `data/`.

## 2. Dependências do MSYS2 (shell CLANG64)
```bash
pacman -S --needed git patch \
  mingw-w64-clang-x86_64-{toolchain,cmake,ninja,pkgconf,python} \
  mingw-w64-clang-x86_64-{vulkan-headers,vulkan-loader,vulkan-memory-allocator,glslang} \
  mingw-w64-clang-x86_64-{sdl3,fmt,boost,robin-map,xxhash,ffmpeg,zydis} \
  mingw-w64-clang-x86_64-{spirv-tools,spirv-headers,spirv-cross}
```

## 3. Clonar e compilar
No PowerShell (Git for Windows, repositório privado: entre pelo navegador quando o Git pedir):
```powershell
git config --global core.autocrlf false
git clone --recurse-submodules https://github.com/carachapadu/lost-paradise-pc D:\LostParadise\lost-paradise-pc
```
No shell MSYS2 CLANG64:
```bash
cd /d/LostParadise/lost-paradise-pc/port
TLG_LTO=OFF bash build.sh        # gera out/tlg-probe.exe (TLG_LTO=OFF se a máquina tiver pouca RAM)
```
Se um submódulo faltar: `git submodule update --init --recursive`. Scripts e patches precisam de quebra de linha LF
(`.gitattributes` já força).

## 4. Rodar do código-fonte
```powershell
cd D:\LostParadise\lost-paradise-pc\port
$env:TLG_SKIP_LINK_LIBC='1'                 # o libc.prx deste jogo é ligado por link_modules.py
$env:TLG_GAME_DIR='D:\LostParadise\work\game\CUSA12781'   # pasta com eboot.bin (cópia do eboot.elf)
python run.py
```
Ou use o launcher: `python launcher\lostparadise_launcher.py`. Menu do jogo: `Insert` ou `R3+L2`.

## 5. Gerar o pacote para jogadores
No shell MSYS2 CLANG64, depois do build:
```bash
cd /d/LostParadise/lost-paradise-pc/port
WINPYTHON=/c/Python315/python.exe bash packaging/windows/package-lostparadise.sh
```
Saída: `port/dist/lostparadise-windows-x86_64.zip` (`Lost Paradise.exe`, `out/tlg-probe.exe` + DLLs, scripts, patches).
O `check_package.sh` aborta se algum arquivo do jogo, do firmware ou de jogador entrar no pacote.
Extraia o zip numa pasta **separada** do dump.

## 6. Problemas conhecidos de build
- `git pull` pedindo senha no MSYS2: faça o pull no PowerShell.
- Erro de patch `fsr-vulkan` com CRLF: `git config core.autocrlf false` e reclone/restaure os arquivos.
- `clang -Werror` por variável não usada: já corrigido em `runtime_memory.c`.

---

# Referências usadas para criar o port (recomp) / References

**Método:** não há emulador de CPU. O código x86-64 original do `eboot` roda nativamente; o sistema do PS4 (kernel, libc,
áudio, entrada, arquivos) é reimplementado por imports resolvidos em `src/runtime_*.c`; a GPU (AMD GCN) é traduzida para Vulkan.

**Base do projeto (core de PS4, GPL-2.0-or-later)**
- HayatoG — `iss_pc` (inFAMOUS Second Son PC), https://github.com/HayatoG/iss_pc : pipeline `prepare/link_modules/content_profile`,
  runtime, launcher, empacotamento. Mesma linhagem de: `tlg_pc` (The Last Guardian), `gr2_pc` (Gravity Rush 2), `gow3_pc`, inFAMOUS PC, Bloodborne PC.
- A parte específica deste jogo (`port/src/runtime_hokuto.c`, `sceKernelMemoryPool*` em `runtime_memory.c`, tabela de imports
  `import_names.inc`, launcher `lostparadise_launcher.py`, empacotamento) está em `port/docs/lost-paradise/lost_paradise_runtime.patch`
  e nos commits deste repositório.

**GPU / shaders (vendorizado em `port/gpu`, ver `port/gpu/VENDOR.txt`)**
- shadPS4 (`video_core`, `shader_recompiler`), https://github.com/shadps4-emu/shadPS4 — GPL-2.0-or-later.
- Correções portadas de forks: shadPS4-Infamous-FixBuild (rayhlancaner-png, TOXIC-KID, 0xDeftones) e Shadow of the Colossus PC (AjncSystem; Pink-shadPS4/luizgustavs).

**Bibliotecas (submódulos e MSYS2)**
- FSR-Vulkan (FireBurn), Dear ImGui, magic_enum, miniz, xbyak, Vulkan-Headers (Khronos), LibAtrac9 (Thealexbarney).
- SDL3, FFmpeg, Zydis, SPIRV-Tools/Headers/Cross, glslang, VMA, Boost, fmt, robin-map, xxhash.

**Análise do eboot (ferramentas de engenharia reversa)**
- Ghidra (com REA/Rizin/objdump) para listar imports (372 símbolos, 31 bibliotecas) e achar os chamadores dos imports que faltavam
  (`port/docs/lost-paradise/eboot_imports_1.09.json`, `imports_cruzamento_1.09.csv`, `chamadores_imports_restantes.json`).
- Formato SELF/ELF do PS4 e tags dinâmicas SCE (`0x6100000F`, `0x61000015`, `0x61000035/39/3F`, relocs `0x61000029/2d/2f/31`).
- Documentação pública de NIDs e das bibliotecas do SDK do PS4 usada para nomear os imports.

Licença: GPL-2.0-or-later (`port/LICENSE`). Nenhum arquivo do jogo, do firmware ou de arte oficial é distribuído.

# Fist of the North Star: Lost Paradise — PC (Windows)

Port nativo do **Lost Paradise** (PS4, CUSA12781, v1.09) sobre o core do `HayatoG/iss_pc`
(GPL-2.0-or-later). Os arquivos do jogo **não** fazem parte do repositório: use o seu próprio dump.

## Estado (2026-10-22)

- **Jogável no Windows com GPU Vulkan:** abertura, menus, tutorial e combate; áudio, gráficos e controle funcionam.
- Imports do eboot: 372 distintos / 31 bibliotecas; verificação oficial: 3 faltando, todos de módulos `.prx`.
- `src/runtime_hokuto.c` (stubs, `sceZlib*`, `GetCpumode`, IME) e `sceKernelMemoryPool*` em `src/runtime_memory.c`.
- Launcher Tk (`launcher/lostparadise_launcher.py`) e pacote Windows (`packaging/windows/package-lostparadise.sh`);
  resolução de saída até 4K por upscale FSR 1 (a resolução interna fica em 1080p: não há patch do jogo).
- **Pendências:** blocos em xadrez na abertura (testar `TLG_BP09=1`/`TLG_BLOCK1D=1`); engasgo inicial (compilação de shaders);
  confirmar contratos de `sceZlibGetResult`, `sceKernelMemoryPoolBatch` e `sceImeDialogGetPanelSize`; save real, vídeos longos e
  sessões longas; sem perfil de patches (CUSA12781); `iced_x86` opcional. Veja `docs/COMPILAR.md` na raiz.

## Compilar no Windows (MSYS2 CLANG64)

1. Instale o MSYS2 (`winget install MSYS2.MSYS2`) e abra o shell **MSYS2 CLANG64**.
2. Dependências:

```bash
pacman -S --needed git patch \
  mingw-w64-clang-x86_64-{toolchain,cmake,ninja,pkgconf,python} \
  mingw-w64-clang-x86_64-{vulkan-headers,vulkan-loader,vulkan-memory-allocator,glslang} \
  mingw-w64-clang-x86_64-{sdl3,fmt,boost,robin-map,xxhash,ffmpeg,zydis} \
  mingw-w64-clang-x86_64-{spirv-tools,spirv-headers,spirv-cross}
```

3. Clone com submódulos e compile (se a máquina tiver pouca RAM, use `TLG_LTO=OFF`):

```bash
git clone https://github.com/carachapadu/lost-paradise-pc
cd lost-paradise-pc/port
git submodule update --init --recursive
TLG_LTO=OFF bash build.sh        # gera out/tlg-probe.exe
```

Se o `submodule update` falhar (os submódulos apontam para repositórios do upstream), clone
`https://github.com/HayatoG/iss_pc` com `--recursive` e aplique `lost_paradise_runtime.patch` nele
(`git apply port/docs/lost-paradise/lost_paradise_runtime.patch`, a partir da raiz).

## Verificar imports e primeiro boot

Troque o caminho pelo do seu dump (a pasta com `eboot.bin` decriptado, `sce_module/`, `sce_sys/`):

```bash
export TLG_GAME_DIR=D:/LostParadise/CUSA12781
export TLG_SKIP_LINK_LIBC=1      # link_modules.py já liga o libc.prx deste jogo
python scripts/prepare.py "$TLG_GAME_DIR" --out out
python scripts/link_modules.py "$TLG_GAME_DIR" --out out
./out/tlg-probe.exe out/boot-linked.bin --check-imports --cpu-only
```

Mande a saída (as linhas `MISSING:` e `Imports: N missing`). Depois do check limpo:

```bash
python run.py                    # pipeline completo e primeiro boot
```

Esperado no primeiro boot: parar no primeiro import não resolvido ou em algum comportamento
do kernel ainda não coberto. Mande o log.

## Rodar o jogo (sem limite de tempo)

No shell MSYS2 CLANG64, na pasta `port`, depois do passo anterior (cópia preparada do jogo em `D:\LostParadise\work\game\CUSA12781`):

```bash
export TLG_SKIP_LINK_LIBC=1
export TLG_GAME_DIR=/d/LostParadise/work/game/CUSA12781
python run.py
```

Variáveis para o defeito das texturas 1D: `TLG_BP09=1` (toda textura 1D vira 2D) ou `TLG_BLOCK1D=1`.

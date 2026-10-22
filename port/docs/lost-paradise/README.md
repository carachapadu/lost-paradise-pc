# Fist of the North Star: Lost Paradise — PC (Windows)

Port nativo do **Lost Paradise** (PS4, CUSA12781, v1.09) sobre o core do `HayatoG/iss_pc`
(GPL-2.0-or-later). Os arquivos do jogo **não** fazem parte do repositório: use o seu próprio dump.

## Estado

- Imports do eboot: 372 distintos / 31 bibliotecas (`eboot_imports_1.09.json`, `imports_cruzamento_1.09.csv`).
- `prepare.py` e `link_modules.py` (com `libc.prx` e `libSceFios2.prx` do jogo) rodam no dump 1.09.
- Verificação oficial (`tlg-probe --check-imports`, com GPU registrada, Windows, RTX 3060): **3 faltando**, todos de
  módulos `.prx` (`NhpspxdjEKU`, `jh+8XiK4LeE`, `hHrGoGoNf+s`).
- `src/runtime_hokuto.c`: stubs offline, `sceZlib*` (inflate próprio), `GetCpumode`, `ImeDialogGetPanelSize`.
  `src/runtime_memory.c`: `sceKernelMemoryPool*`. Contratos lidos dos chamadores no eboot
  (`chamadores_imports_restantes.json`); o do `Batch` e o tamanho do painel IME precisam de confirmação em execução real.
- **Primeiro boot (2026-10-22, 40 s, com GPU):** o jogo inicializa, abre 240 arquivos de `data/`, cria as threads do
  motor (CRI, pxd), abre áudio (WASAPI, 74 mil buffers), mostra o diálogo de save/mensagem do sistema e envia
  3585+ lotes de draws à GPU. Só com `--cpu-only` ele para em `sceVideoOutOpen`, como esperado.
- Erros vistos: `image view type Color2D is incompatible with image type Color1D` (testar `TLG_BP09=1`/`TLG_BLOCK1D=1`);
  sem perfil de patches para CUSA12781; `iced_x86` não instalado (reescrita ISA indisponível, só importa em CPU sem MOVBE/BMI1/LZCNT).
- Ainda não verificado: o que aparece na janela, entrada de pad, vídeos (CRI/Mana), save real, estabilidade em sessões longas.

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

## Pendências

- Rodar a verificação oficial e o primeiro boot (`--cpu-only`, depois GPU).
- Confirmar contratos: `sceZlibGetResult` (ordem de `length`/`status`), `sceKernelMemoryPoolBatch` (operações), `sceImeDialogGetPanelSize`.
- Ver se o dump 1.09 precisa de `playgo.pgm` / `sce_discmap_patch.plt`.
- Descobrir quem carrega os módulos `libSceFace`, `libSceHand`, `libSceSmart`, `libSceS3DConversion`.
- Perfil de patches (`scripts/patches.py` não tem perfil para CUSA12781).

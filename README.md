<p align="center"><img src="port/packaging/icon/lostparadise-icon-512.png" width="128" alt=""></p>

<h1 align="center">Fist of the North Star: Lost Paradise — PC port</h1>

> **Jogável, em desenvolvimento / Playable, in development.** O jogo inicia, chega ao gameplay e ao combate no Windows
> com GPU Vulkan; áudio, gráficos e controle funcionam. Ainda há falhas conhecidas (ver `port/docs/lost-paradise/README.md`).

Port nativo (sem emulador de CPU) de **Fist of the North Star: Lost Paradise** (PS4, CUSA12781, v1.09): o código original
do jogo roda direto no processador, o sistema do PS4 é reimplementado e a GPU é traduzida para Vulkan.
Baseado no core de PS4 de [HayatoG](https://github.com/HayatoG/iss_pc) (GPL-2.0-or-later); o código desse core mantém seus créditos e licença.

**Nenhum arquivo do jogo é distribuído.** Você precisa do dump do seu próprio PS4 — veja [`docs/ARQUIVOS_NECESSARIOS.md`](docs/ARQUIVOS_NECESSARIOS.md).

## Usar / Use
- **Pacote para jogadores:** `Lost Paradise.exe` (launcher) — veja `port/packaging/README-player-lostparadise.md`.
- **Gerar o pacote (Windows, shell MSYS2 CLANG64):** `bash packaging/windows/package-lostparadise.sh` dentro de `port/`.
- **Rodar do código-fonte:** `port/docs/lost-paradise/README.md` (compilar, preparar, executar).
- **Linux:** `./lostparadise_launcher.sh` ou `TLG_GAME_DIR=... ./run_lostparadise.sh` (não testado).

Menu do jogo: `Insert` ou `R3+L2`. `Esc` solta o mouse.

## Licença / License
GPL-2.0-or-later (ver `port/LICENSE`). Sem arquivos do jogo, do firmware ou de arte oficial.

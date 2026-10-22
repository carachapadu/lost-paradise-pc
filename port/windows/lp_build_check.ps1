# Lost Paradise (CUSA12781 1.09): instala o MSYS2 (se faltar), compila o core, prepara o jogo e roda a
# verificacao de imports. Tudo vai para o log (padrao: D:\LostParadise\lp-check.log); mande esse arquivo.
#
# Uso (PowerShell):  powershell -ExecutionPolicy Bypass -File lp_build_check.ps1
# Antes: clone o repositorio com o Git para Windows, por exemplo
#   git clone https://github.com/carachapadu/lost-paradise-pc D:\LostParadise\lost-paradise-pc
param(
    [string]$Repo = 'D:\LostParadise\lost-paradise-pc',
    [string]$Dump = 'D:\LostParadise\CUSA12781',          # eboot.elf (decriptado), sce_module, sce_sys
    [string]$Work = 'D:\LostParadise\work',               # copia preparada do jogo e saidas
    [string]$Log  = 'D:\LostParadise\lp-check.log',
    [string]$Msys = 'C:\msys64'
)
$ErrorActionPreference = 'Stop'
function Say($m) { Write-Host $m; try { Add-Content -Path $Log -Encoding UTF8 -Value $m } catch { } }
New-Item -ItemType Directory -Force -Path (Split-Path $Log) | Out-Null
Set-Content -Path $Log -Encoding UTF8 -Value "Lost Paradise build/check $(Get-Date -Format s)"

if (-not (Test-Path "$Repo\port\build.sh")) { Say "Repositorio nao encontrado em $Repo (git clone primeiro)."; exit 1 }
foreach ($f in 'eboot.elf', 'sce_sys\param.sfo', 'sce_module') {
    if (-not (Test-Path "$Dump\$f")) { Say "Faltando $Dump\$f"; exit 1 }
}
if (-not (Test-Path "$Msys\usr\bin\bash.exe")) {
    Say 'Instalando o MSYS2 (winget)...'
    winget install --id MSYS2.MSYS2 -e --accept-package-agreements --accept-source-agreements
    if (-not (Test-Path "$Msys\usr\bin\bash.exe")) { Say "MSYS2 nao ficou em $Msys; passe -Msys com a pasta certa."; exit 1 }
}

# Copia preparada do jogo: eboot.bin = o eboot.elf decriptado (o dump original nao e alterado).
$Game = Join-Path $Work 'game\CUSA12781'
New-Item -ItemType Directory -Force -Path $Game | Out-Null
Copy-Item "$Dump\eboot.elf" "$Game\eboot.bin" -Force
Copy-Item "$Dump\sce_module" "$Game\sce_module" -Recurse -Force
New-Item -ItemType Directory -Force -Path "$Game\sce_sys" | Out-Null
Copy-Item "$Dump\sce_sys\param.sfo" "$Game\sce_sys\param.sfo" -Force

function Msys-Path($p) { $p = $p -replace '\\', '/'; if ($p -match '^([A-Za-z]):(.*)$') { return '/' + $Matches[1].ToLower() + $Matches[2] }; return $p }
$repoM = Msys-Path $Repo; $gameM = Msys-Path $Game; $workM = Msys-Path $Work; $logM = Msys-Path $Log

$script = @"
set -euo pipefail
pacman -Sy --noconfirm
pacman -S --needed --noconfirm git patch \
  mingw-w64-clang-x86_64-{toolchain,cmake,ninja,pkgconf,python} \
  mingw-w64-clang-x86_64-{vulkan-headers,vulkan-loader,vulkan-memory-allocator,glslang} \
  mingw-w64-clang-x86_64-{sdl3,fmt,boost,robin-map,xxhash,ffmpeg,zydis} \
  mingw-w64-clang-x86_64-{spirv-tools,spirv-headers,spirv-cross}
git config --global --add safe.directory '*'
cd '$repoM/port'
# Git for Windows may have checked the repository out with CRLF; patches and shell scripts need LF.
git config core.autocrlf false
find . -path ./gpu/third_party -prune -o \( -name '*.patch' -o -name '*.sh' \) -type f -print0 | xargs -0 sed -i 's/\r$//'
git submodule update --init --recursive
echo '== build'
TLG_LTO=OFF bash build.sh
echo '== prepare/link'
OUT='$workM/out'; mkdir -p "`$OUT"
python scripts/prepare.py '$gameM' --out "`$OUT"
python scripts/link_modules.py '$gameM' --out "`$OUT"
echo '== check-imports'
./out/tlg-probe.exe "`$OUT/boot-linked.bin" --check-imports --cpu-only || true
echo '== fim'
"@
$tmp = Join-Path $env:TEMP 'lp_build_check.sh'
[IO.File]::WriteAllText($tmp, ($script -replace "`r`n", "`n"))
$ErrorActionPreference = 'Continue'   # warnings of pacman/git go to stderr and must not stop the script
$env:MSYSTEM = 'CLANG64'; $env:CHERE_INVOKING = '1'
& "$Msys\usr\bin\bash.exe" -lc "bash '$(Msys-Path $tmp)'" 2>&1 | ForEach-Object { $l = "$_"; Write-Host $l; try { Add-Content -Path $Log -Encoding UTF8 -Value $l } catch { } }
Say "Codigo de saida: $LASTEXITCODE. Log: $Log"

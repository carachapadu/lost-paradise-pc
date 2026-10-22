#!/usr/bin/env bash
# Builds dist/lostparadise-windows-x86_64.zip after `bash build.sh` in an MSYS2 CLANG64 shell:
# "Lost Paradise.exe" (Tk launcher frozen with PyInstaller: players need no Python), out/tlg-probe.exe
# with the CLANG64 DLLs it loads, the preparation scripts and the player README.
# No game, console or player file may ship (packaging/check_package.sh stops the build).
set -euo pipefail
cd -- "$(dirname -- "$0")/../.."
source ./msys2-env.sh
[[ -f out/tlg-probe.exe ]] || { echo 'Build first: TLG_LTO=OFF bash build.sh' >&2; exit 1; }
NAME='Lost Paradise'
name=${TLG_PACKAGE_NAME:-lostparadise-windows-x86_64}

python=${WINPYTHON:-}
if [[ -z $python ]]; then
    for candidate in /c/Python3*/python.exe "${LOCALAPPDATA:-/c/Users/$USER/AppData/Local}"/Programs/Python/Python3*/python.exe; do
        [[ -x $candidate ]] && python=$candidate
    done
fi
[[ -n $python ]] || { echo 'Need a Windows Python 3 (python.org) or WINPYTHON=path\to\python.exe' >&2; exit 1; }
export USERPROFILE=${USERPROFILE:-$(cygpath -w "/c/Users/$(id -un)")}
[[ -x out/pyenv/Scripts/python.exe ]] || "$python" -m venv out/pyenv
out/pyenv/Scripts/python.exe -m pip install -q --disable-pip-version-check pyinstaller iced-x86==1.21.0 pillow
hidden=()
for module in argparse base64 collections hashlib json re shutil struct tempfile xml.etree.ElementTree \
              urllib.request runpy sqlite3 mmap multiprocessing multiprocessing.pool dataclasses array bisect \
              random time typing ctypes.wintypes msvcrt iced_x86 PIL PIL.Image tkinter tkinter.ttk tkinter.filedialog tkinter.messagebox; do
    hidden+=("$module")
done
LP_SPEC_NAME=$NAME LP_SPEC_ROOT=$(cygpath -w "$PWD") LP_SPEC_ICON=$(cygpath -w "$PWD/launcher/lostparadise.ico") \
LP_SPEC_HIDDEN="${hidden[*]}" \
    out/pyenv/Scripts/python.exe -m PyInstaller --noconfirm --clean --log-level WARN \
    --distpath out/pyi-dist --workpath out/pyi-work "$(cygpath -w "$PWD/packaging/lostparadise.spec")"

dest=out/stage/$name
rm -rf -- out/stage
mkdir -p "$dest/out" "$dest/launcher"
cp -r "out/pyi-dist/$NAME/." "$dest/"
cp launcher/lostparadise.ico launcher/lostparadise.png "$dest/launcher/"
cp run.py "$dest/"
llvm-strip --strip-debug -o "$dest/out/tlg-probe.exe" out/tlg-probe.exe
# Every CLANG64 DLL the probe loads (SDL3, FFmpeg, Vulkan loader, ...), found through the import tables.
declare -A shipped=()
queue=("$dest/out/tlg-probe.exe")
while ((${#queue[@]})); do
    binary=${queue[0]}; queue=("${queue[@]:1}")
    while read -r dll; do
        key=${dll,,}
        [[ -n ${shipped[$key]:-} ]] && continue
        shipped[$key]=1
        source=$(find /clang64/bin -maxdepth 1 -iname "$dll" -print -quit)
        [[ -n $source ]] || continue
        cp -u "$source" "$dest/out/"
        queue+=("$source")
    done < <(llvm-readobj --coff-imports "$binary" | awk '$1 == "Name:" && tolower($2) ~ /\.dll$/ {print $2}')
done
echo "Packaged $(find "$dest/out" -maxdepth 1 -iname '*.dll' | wc -l) DLLs from /clang64/bin"
cp -r scripts patches "$dest/"
mkdir -p "$dest/tools"; cp -r tools/xpps "$dest/tools/"
find "$dest" -name __pycache__ -prune -exec rm -r {} +
cp LICENSE "$dest/"
cp packaging/README-player-lostparadise.md "$dest/README.md"
printf '%s\r\n' '@echo off' 'start "" "%~dp0Lost Paradise.exe" --play' > "$dest/Play Lost Paradise.cmd"
git rev-parse --short HEAD > "$dest/VERSION" 2>/dev/null || echo dev > "$dest/VERSION"
bash packaging/check_package.sh "$dest"
mkdir -p dist
rm -f "dist/$name.zip"
(cd out/stage && powershell -NoProfile -Command "Compress-Archive -Path '$name' -DestinationPath '../../dist/$name.zip'")
du -sh "$dest" "dist/$name.zip"

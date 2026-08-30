#!/usr/bin/env bash
# Launch FreeCAD with its profile inside this project, so the add-on and any
# settings changes never touch ~/.config/FreeCAD or ~/.local/share/FreeCAD.
set -euo pipefail
cd "$(dirname "$0")"

export FREECAD_USER_HOME="$PWD/sandbox/home"

# FREECAD_USER_HOME covers FreeCAD's own config, but Qt writes its settings to
# XDG_CONFIG_HOME regardless -- which lands in ~/.config/FreeCAD. Redirect those
# too, so nothing outside sandbox/ is written.
export XDG_CONFIG_HOME="$PWD/sandbox/xdg/config"
export XDG_DATA_HOME="$PWD/sandbox/xdg/data"
export XDG_CACHE_HOME="$PWD/sandbox/xdg/cache"

mkdir -p "$FREECAD_USER_HOME/Mod" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME"
if [ -d addon ] && [ ! -e "$FREECAD_USER_HOME/Mod/ConversationalCAD" ]; then
  ln -s "$PWD/addon" "$FREECAD_USER_HOME/Mod/ConversationalCAD"
fi

exec vendor/FreeCAD_1.1.3-x86_64.AppImage "$@"

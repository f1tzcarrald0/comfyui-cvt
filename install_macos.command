#!/usr/bin/env bash

set -u

echo "============================================"
echo "  SoraUtils Installer for ComfyUI (macOS)"
echo "============================================"
echo
echo "A folder picker will open. Select:"
echo "  1) Your ComfyUI folder (contains custom_nodes), or"
echo "  2) Your portable root folder (contains ComfyUI/custom_nodes)."
echo

pick_folder() {
  osascript <<'APPLESCRIPT'
try
  set selectedFolder to choose folder with prompt "Select ComfyUI folder or portable root"
  return POSIX path of selectedFolder
on error number -128
  return ""
end try
APPLESCRIPT
}

pick_python_file() {
  osascript <<'APPLESCRIPT'
try
  set selectedFile to choose file with prompt "Select ComfyUI Python executable (python or python3)"
  return POSIX path of selectedFile
on error number -128
  return ""
end try
APPLESCRIPT
}

trim_path() {
  local path="$1"
  path="${path//$'\r'/}"
  path="${path//$'\n'/}"
  while [[ "$path" == */ && "$path" != "/" ]]; do
    path="${path%/}"
  done
  printf "%s" "$path"
}

SELECTED_DIR="$(trim_path "$(pick_folder)")"
if [[ -z "$SELECTED_DIR" ]]; then
  echo
  echo "Cancelled by user."
  echo
  exit 1
fi

COMFY_DIR=""
if [[ -d "$SELECTED_DIR/custom_nodes" ]]; then
  COMFY_DIR="$SELECTED_DIR"
elif [[ -d "$SELECTED_DIR/ComfyUI/custom_nodes" ]]; then
  COMFY_DIR="$SELECTED_DIR/ComfyUI"
fi

if [[ -z "$COMFY_DIR" ]]; then
  echo
  echo "ERROR: Could not find custom_nodes in the selected location."
  echo "       Selected: $SELECTED_DIR"
  echo
  echo "Select a ComfyUI folder or portable root folder."
  echo
  exit 1
fi

COMFY_DIR="$(cd "$COMFY_DIR" && pwd)"
COMFY_PARENT="$(cd "$COMFY_DIR/.." && pwd)"

echo
echo "Found ComfyUI at: $COMFY_DIR"

PYTHON_EXE=""
PIP_EXE=""
ENV_NOTE=""
LOOKED_PATHS=()

set_python_if_exists() {
  local candidate="$1"
  local label="$2"
  LOOKED_PATHS+=("$candidate")
  if [[ -x "$candidate" ]]; then
    PYTHON_EXE="$candidate"
    ENV_NOTE="$label $candidate"
    return 0
  fi
  return 1
}

set_pip_if_exists() {
  local candidate="$1"
  local label="$2"
  LOOKED_PATHS+=("$candidate")
  if [[ -x "$candidate" ]]; then
    PIP_EXE="$candidate"
    ENV_NOTE="$label $candidate"
    return 0
  fi
  return 1
}

detect_python() {
  local root
  for root in "$COMFY_DIR" "$COMFY_PARENT"; do
    set_python_if_exists "$root/venv/bin/python3" "Found venv python at:" && return 0
    set_python_if_exists "$root/venv/bin/python" "Found venv python at:" && return 0
    set_python_if_exists "$root/.venv/bin/python3" "Found .venv python at:" && return 0
    set_python_if_exists "$root/.venv/bin/python" "Found .venv python at:" && return 0
    set_python_if_exists "$root/python_embeded/bin/python3" "Found embedded python at:" && return 0
    set_python_if_exists "$root/python_embeded/bin/python" "Found embedded python at:" && return 0
    set_python_if_exists "$root/python_embedded/bin/python3" "Found embedded python at:" && return 0
    set_python_if_exists "$root/python_embedded/bin/python" "Found embedded python at:" && return 0
  done

  for root in "$COMFY_DIR" "$COMFY_PARENT"; do
    set_pip_if_exists "$root/venv/bin/pip3" "Found venv pip at:" && return 0
    set_pip_if_exists "$root/venv/bin/pip" "Found venv pip at:" && return 0
    set_pip_if_exists "$root/.venv/bin/pip3" "Found .venv pip at:" && return 0
    set_pip_if_exists "$root/.venv/bin/pip" "Found .venv pip at:" && return 0
    set_pip_if_exists "$root/python_embeded/bin/pip3" "Found embedded pip at:" && return 0
    set_pip_if_exists "$root/python_embeded/bin/pip" "Found embedded pip at:" && return 0
    set_pip_if_exists "$root/python_embedded/bin/pip3" "Found embedded pip at:" && return 0
    set_pip_if_exists "$root/python_embedded/bin/pip" "Found embedded pip at:" && return 0
  done

  return 1
}

detect_python
if [[ -n "$ENV_NOTE" ]]; then
  echo "$ENV_NOTE"
fi

if [[ -z "$PYTHON_EXE" && -z "$PIP_EXE" ]]; then
  echo
  echo "WARNING: Could not find ComfyUI's Python environment automatically."
  echo "Looked for:"
  for looked in "${LOOKED_PATHS[@]}"; do
    echo "  $looked"
  done
  echo
  read -r -p "Select ComfyUI python manually now? [y/N]: " PICK_MANUAL
  if [[ "$PICK_MANUAL" =~ ^[Yy]$ ]]; then
    MANUAL_PY="$(trim_path "$(pick_python_file)")"
    if [[ -n "$MANUAL_PY" ]]; then
      MANUAL_BASE="$(basename "$MANUAL_PY")"
      if [[ "$MANUAL_BASE" == python || "$MANUAL_BASE" == python3 || "$MANUAL_BASE" == python3.* ]]; then
        PYTHON_EXE="$MANUAL_PY"
        ENV_NOTE="Using manually selected python at: $MANUAL_PY"
        echo "$ENV_NOTE"
      else
        echo "Selected file is not a python executable: $MANUAL_PY"
      fi
    else
      echo "Manual python selection cancelled."
    fi
  fi
fi

SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST_DIR="$COMFY_DIR/custom_nodes/SoraUtils"

echo
echo "Copying SoraUtils to: $DEST_DIR"
if [[ -d "$DEST_DIR" ]]; then
  echo "Removing existing SoraUtils installation..."
  rm -rf "$DEST_DIR"
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo
  echo "ERROR: rsync is required on macOS for installation copy."
  exit 1
fi

rsync -a --delete \
  --exclude "__pycache__" \
  --exclude ".git" \
  --exclude "build" \
  --exclude "dist" \
  --exclude "installer" \
  --exclude ".claude" \
  --exclude "install.bat" \
  --exclude "build_installer.ps1" \
  --exclude "build_macos_pkg.sh" \
  --exclude "*.spec" \
  --exclude "*.exe" \
  --exclude "install_macos.command" \
  "$SOURCE_DIR/" "$DEST_DIR/"

if [[ -d "$SOURCE_DIR/example_workflows" && ! -d "$DEST_DIR/example_workflows" ]]; then
  echo "example_workflows was missing after copy. Copying it explicitly..."
  cp -R "$SOURCE_DIR/example_workflows" "$DEST_DIR/example_workflows"
fi

if [[ ! -f "$DEST_DIR/__init__.py" ]]; then
  echo
  echo "ERROR: Copy failed. Check folder permissions."
  exit 1
fi

if [[ -d "$SOURCE_DIR/example_workflows" && ! -d "$DEST_DIR/example_workflows" ]]; then
  echo
  echo "WARNING: example_workflows could not be copied automatically."
fi

echo "Files copied successfully."

if [[ -n "$PYTHON_EXE" ]]; then
  echo
  echo "Installing Python dependencies with: $PYTHON_EXE"
  "$PYTHON_EXE" -m pip install -r "$DEST_DIR/requirements.txt"
  if [[ $? -ne 0 ]]; then
    echo
    echo "WARNING: pip install had errors. You may need to install dependencies manually."
  else
    echo "Dependencies installed successfully."
  fi
elif [[ -n "$PIP_EXE" ]]; then
  echo
  echo "Installing Python dependencies with: $PIP_EXE"
  "$PIP_EXE" install -r "$DEST_DIR/requirements.txt"
  if [[ $? -ne 0 ]]; then
    echo
    echo "WARNING: pip install had errors. You may need to install dependencies manually."
  else
    echo "Dependencies installed successfully."
  fi
else
  echo
  echo "Dependencies were NOT installed automatically."
  echo "Run this in your ComfyUI Python environment:"
  echo "  pip install -r \"$DEST_DIR/requirements.txt\""
fi

echo
echo "============================================"
echo "  SoraUtils installed successfully!"
echo "  Restart ComfyUI to load the new nodes."
echo "============================================"
echo
read -r -p "Press Enter to close..."

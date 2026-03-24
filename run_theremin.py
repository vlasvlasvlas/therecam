#!/usr/bin/env python3
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
VENV_DIR = ROOT_DIR / "venv"
REQUIREMENTS_FILE = ROOT_DIR / "requirements.txt"
APP_FILE = ROOT_DIR / "webcam_theremin_python.py"


def run(cmd, check=True):
    print(">", " ".join(str(x) for x in cmd))
    return subprocess.run(cmd, check=check)


def detect_system_python():
    candidates = []
    if os.name == "nt":
        candidates.extend([
            ["py", "-3"],
            ["python"],
        ])
    else:
        candidates.extend([
            ["python3"],
            ["python"],
        ])

    for candidate in candidates:
        try:
            res = subprocess.run(candidate + ["--version"], capture_output=True, text=True)
            if res.returncode == 0:
                return candidate
        except FileNotFoundError:
            continue
    return None


def venv_python_path():
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def ensure_venv(system_python):
    if not VENV_DIR.exists():
        print("[1/5] Creando entorno virtual...")
        run(system_python + ["-m", "venv", str(VENV_DIR)])
    else:
        print("[1/5] Entorno virtual ya existe.")


def ensure_deps(python_bin):
    print("[2/5] Actualizando pip/setuptools/wheel...")
    run([str(python_bin), "-m", "pip", "install", "-U", "pip", "setuptools", "wheel"])

    print("[3/5] Instalando dependencias del proyecto...")
    run([str(python_bin), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)])


def maybe_install_portaudio_macos():
    if platform.system() != "Darwin":
        return

    brew = shutil.which("brew")
    if not brew:
        print("[4/5] Homebrew no encontrado. Si no hay audio, instala portaudio manualmente.")
        return

    check = subprocess.run([brew, "list", "--versions", "portaudio"], capture_output=True, text=True)
    if check.returncode == 0 and check.stdout.strip():
        print("[4/5] portaudio ya esta instalado en macOS.")
        return

    print("[4/5] Instalando portaudio con Homebrew (solo macOS)...")
    run([brew, "install", "portaudio"])


def run_app(python_bin):
    if not APP_FILE.exists():
        raise FileNotFoundError(f"No se encontro {APP_FILE}")

    print("[5/5] Iniciando theremin Python...\n")
    print("Controles:")
    print("- 2 manos: derecha=tono (cerca antena vertical derecha = mas agudo)")
    print("           izquierda=volumen (cerca antena horizontal inferior izquierda = volumen 0)")
    print("- 1 mano: controla tono + volumen")
    print("- Sonido: R/F vibrato depth, J vibrato off, T/G vibrato rate, Y/H delay mix, D delay off")
    print("- Waveforms: Z ciclo, U sine, I triangle, O square, P saw")
    print("- Visual: M grid, N snap, B/V snap buffer, K modo snap, L fullscreen")
    print("- Salir: tecla q en la ventana")
    print("")

    os.execv(str(python_bin), [str(python_bin), str(APP_FILE)])


def main():
    system_python = detect_system_python()
    if not system_python:
        print("Error: no se encontro Python 3 en el sistema.")
        print("Instala Python desde https://www.python.org/downloads/")
        sys.exit(1)

    ensure_venv(system_python)

    python_bin = venv_python_path()
    if not python_bin.exists():
        print("Error: no se pudo encontrar Python dentro del venv.")
        sys.exit(1)

    ensure_deps(python_bin)
    maybe_install_portaudio_macos()
    run_app(python_bin)


if __name__ == "__main__":
    main()

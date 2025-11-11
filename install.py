import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

APP_NAME = "Quadernino"
VENV_NAME = ".venv"

def print_colored(text, color="cyan"):
    colors = {"cyan": "\033[96m", "green": "\033[92m", "red": "\033[91m", "reset": "\033[0m"}
    if platform.system().lower() == "windows": # Semplice fallback per Windows CMD standard
        print(text)
    else:
        print(f"{colors.get(color, '')}{text}{colors['reset']}")

def run_command(command, cwd=None, shell=False):
    try:
        subprocess.check_call(command, cwd=cwd, shell=shell)
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    print_colored(f"🚀 Inizio installazione di {APP_NAME}...", "cyan")

    # 1. Controllo Python
    print(f"Versione Python rilevata: {sys.version.split()[0]}")
    if sys.version_info < (3, 9):
        print_colored("❌ Errore: Richiesto Python 3.9 o superiore.", "red")
        sys.exit(1)

    # 2. Creazione Virtual Environment
    if not Path(VENV_NAME).exists():
        print_colored(f"🛠️ Creazione virtual environment '{VENV_NAME}'...", "cyan")
        if not run_command([sys.executable, "-m", "venv", VENV_NAME]):
             print_colored("❌ Errore nella creazione del venv.", "red")
             sys.exit(1)
    else:
        print_colored(f"ℹ️ Virtual environment '{VENV_NAME}' già esistente.", "green")

    # 3. Determinazione percorso pip/python nel venv
    if platform.system().lower() == "windows":
        venv_pip = Path(VENV_NAME) / "Scripts" / "pip.exe"
        venv_python = Path(VENV_NAME) / "Scripts" / "python.exe"
        streamlit_cmd = Path(VENV_NAME) / "Scripts" / "streamlit.exe"
    else:
        venv_pip = Path(VENV_NAME) / "bin" / "pip"
        venv_python = Path(VENV_NAME) / "bin" / "python"
        streamlit_cmd = Path(VENV_NAME) / "bin" / "streamlit"

    # 4. Installazione Dipendenze
    print_colored("📦 Installazione dipendenze da requirements.txt...", "cyan")
    # Upgrade pip prima
    run_command([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
    if not run_command([str(venv_pip), "install", "-r", "requirements.txt"]):
        print_colored("❌ Errore durante l'installazione delle dipendenze.", "red")
        sys.exit(1)

    # 5. Setup .env
    if not Path(".env").exists():
        print_colored("🔑 Creazione file .env...", "cyan")
        with open(".env", "w") as f:
            f.write("# Quadernino - File di configurazione\n")
            f.write("# Inserisci qui la tua Google API Key\n")
            f.write("GOOGLE_API_KEY=\n\n")
            f.write("# Modello predefinito\n")
            f.write("DEFAULT_MODEL=models/gemini-2.5-flash\n\n")
            f.write("# Quadernini (generato automaticamente)\n")
            f.write("QUADERNINI=[]\n")
            f.write("ACTIVE_NOTEBOOK=\n")
        print_colored("⚠️ File .env creato! Ricordati di aprirlo e inserire la tua GOOGLE_API_KEY.", "green")

    print_colored(f"\n✅ Installazione di {APP_NAME} completata con successo!", "green")
    print("\nPer avviare l'applicazione, usa il seguente comando:")

    if platform.system().lower() == "windows":
         print_colored(f"    {VENV_NAME}\\Scripts\\streamlit run Home.py", "cyan")
    else:
         print_colored(f"    {VENV_NAME}/bin/streamlit run Home.py", "cyan")

    print("\nBuono studio da Craicek!")

if __name__ == "__main__":
    import shutil
    main()
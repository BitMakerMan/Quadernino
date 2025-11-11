import os
import shutil
from pathlib import Path
import streamlit as st

# Usa percorso assoluto per evitare problemi con working directory
UPLOAD_DIR = Path(__file__).parent.parent / "uploaded_files"

#
# --- FUNZIONI DI ESTRAZIONE TESTO RIMOSSE ---
# _extract_from_text, _extract_from_pdf, _extract_from_docx
# e extract_text_from_file non sono più necessarie.
# Google File Search fa tutto questo parsing sul server.
#

def save_uploaded_file(uploaded_file):
    """
    Salva un file caricato tramite Streamlit nella directory locale.
    Ritorna il percorso completo del file salvato.
    """
    try:
        UPLOAD_DIR.mkdir(exist_ok=True)
        file_path = UPLOAD_DIR / uploaded_file.name

        # Scrive il buffer del file su disco
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        return str(file_path)
    except Exception as e:
        st.error(f"Errore durante il salvataggio locale del file: {e}")
        return None


def list_local_files():
    """Ritorna una lista dei percorsi dei file presenti nella directory di upload."""
    if not UPLOAD_DIR.exists():
        return []
    return [str(f) for f in UPLOAD_DIR.iterdir() if f.is_file() and f.name != ".gitkeep"]


def delete_local_file(file_name):
    """Elimina un file specifico dalla directory locale."""
    try:
        file_path = UPLOAD_DIR / file_name
        if file_path.exists():
            os.remove(file_path)
            return True
    except Exception as e:
        st.error(f"Errore durante l'eliminazione del file: {e}")
    return False


def get_file_info(file_path):
    """Ritorna informazioni base su un file (dimensione formattata, estensione)."""
    path = Path(file_path)
    if not path.exists():
        return None

    size_bytes = path.stat().st_size

    # Logica per unità di misura dinamica
    if size_bytes < 1024:
        size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    else:
        size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

    return {
        "name": path.name,
        "size_formatted": size_str,
        "type": path.suffix.lower()
    }
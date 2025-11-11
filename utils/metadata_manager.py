import json
from pathlib import Path
from typing import List, Dict, Set
from utils.logger import log_info, log_error

METADATA_FILE = Path("metadata.json")
# Usiamo un file di lock anche qui per sicurezza
METADATA_LOCK = Path("metadata.json.lock")
from filelock import FileLock, Timeout


def _load_metadata() -> Dict:
    """Carica i metadati dal file JSON in modo sicuro (con lock)."""
    if not METADATA_FILE.exists():
        return {}

    lock = FileLock(str(METADATA_LOCK), timeout=10)
    try:
        with lock:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Timeout:
        log_error("Timeout: Impossibile acquisire il lock su metadata.json per la lettura")
        return {}
    except (IOError, json.JSONDecodeError) as e:
        log_error(f"Errore lettura metadata.json: {e}")
        return {}


def _save_metadata(data: Dict):
    """Salva i metadati sul file JSON in modo sicuro (con lock)."""
    lock = FileLock(str(METADATA_LOCK), timeout=10)
    try:
        with lock:
            with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            return True
    except Timeout:
        log_error("Timeout: Impossibile acquisire il lock su metadata.json per la scrittura")
        return False
    except IOError as e:
        log_error(f"Errore scrittura metadata.json: {e}")
        return False


def add_file_to_notebook(notebook_name: str, file_name: str) -> bool:
    """Aggiunge un file (con tag vuoti) a un quadernino."""
    try:
        data = _load_metadata()
        if notebook_name not in data:
            data[notebook_name] = {}

        if file_name not in data[notebook_name]:
            data[notebook_name][file_name] = {"tags": []}
            log_info(f"File {file_name} aggiunto a {notebook_name} nei metadati")
            return _save_metadata(data)
        return True  # File già presente
    except Exception as e:
        log_error(f"Errore aggiunta file ai metadati: {e}")
        return False


def remove_file_from_notebook(notebook_name: str, file_name: str) -> bool:
    """Rimuove un file da un quadernino."""
    try:
        data = _load_metadata()
        if notebook_name in data and file_name in data[notebook_name]:
            del data[notebook_name][file_name]
            log_info(f"File {file_name} rimosso da {notebook_name} nei metadati")
            return _save_metadata(data)
        return True  # File non trovato, operazione "riuscita"
    except Exception as e:
        log_error(f"Errore rimozione file dai metadati: {e}")
        return False


def remove_notebook_metadata(notebook_name: str) -> bool:
    """Rimuove l'intera sezione di un quadernino dai metadati."""
    try:
        data = _load_metadata()
        if notebook_name in data:
            del data[notebook_name]
            log_info(f"Metadati per {notebook_name} rimossi")
            return _save_metadata(data)
        return True
    except Exception as e:
        log_error(f"Errore rimozione metadati quadernino: {e}")
        return False


def get_notebook_files(notebook_name: str) -> Dict[str, Dict]:
    """Ottiene un dizionario di file e i loro metadati (tag) per un quadernino."""
    data = _load_metadata()
    return data.get(notebook_name, {})


def get_notebook_file_names(notebook_name: str) -> List[str]:
    """Ottiene solo la lista dei nomi dei file per un quadernino."""
    return list(get_notebook_files(notebook_name).keys())


def update_file_tags(notebook_name: str, file_name: str, tags: List[str]) -> bool:
    """Aggiorna i tag per un file specifico."""
    try:
        data = _load_metadata()
        if notebook_name not in data or file_name not in data[notebook_name]:
            log_warning(f"Tentativo di aggiornare tag per file non esistente: {notebook_name}/{file_name}")
            # Crea la voce se non esiste
            if notebook_name not in data:
                data[notebook_name] = {}
            data[notebook_name][file_name] = {"tags": tags}
        else:
            data[notebook_name][file_name]["tags"] = tags

        return _save_metadata(data)
    except Exception as e:
        log_error(f"Errore aggiornamento tag: {e}")
        return False


def get_file_tags(notebook_name: str, file_name: str) -> List[str]:
    """Ottiene i tag per un file specifico."""
    files = get_notebook_files(notebook_name)
    return files.get(file_name, {}).get("tags", [])


def get_all_tags_for_notebook(notebook_name: str) -> List[str]:
    """Ottiene un elenco unico di tutti i tag usati in un quadernino."""
    files = get_notebook_files(notebook_name)
    all_tags: Set[str] = set()
    for file_data in files.values():
        for tag in file_data.get("tags", []):
            all_tags.add(tag)
    return sorted(list(all_tags))
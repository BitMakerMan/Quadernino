from pathlib import Path
import os
import ast
from typing import List, Dict
from utils.logger import log_info, log_error, log_warning
from filelock import FileLock, Timeout

ENV_PATH = Path(".env")
# File di lock per prevenire race conditions sul file .env
ENV_LOCK_PATH = ENV_PATH.with_suffix(".env.lock")


def update_env_variable(key: str, value: str):
    """
    Aggiorna o aggiunge una variabile d'ambiente nel file .env locale.
    Questa funzione è THREAD-SAFE (usa un lock).
    """
    lock = FileLock(str(ENV_LOCK_PATH), timeout=10)
    try:
        with lock:
            # Assicura che il file esista
            if not ENV_PATH.exists():
                with open(ENV_PATH, "w") as f:
                    f.write(f"{key}={value}\n")
                return True

            # Leggi tutte le righe esistenti
            with open(ENV_PATH, "r") as f:
                lines = f.readlines()

            new_lines = []
            key_found = False

            for line in lines:
                # Se la riga inizia con la chiave cercata (ed è attiva, non commentata)
                if line.strip().startswith(f"{key}="):
                    new_lines.append(f"{key}={value}\n")
                    key_found = True
                else:
                    new_lines.append(line)

            # Se la chiave non c'era, aggiungila in fondo
            if not key_found:
                if new_lines and not new_lines[-1].endswith('\n'):
                    new_lines[-1] += '\n'
                new_lines.append(f"{key}={value}\n")

            # Riscrivi il file
            with open(ENV_PATH, "w") as f:
                f.writelines(new_lines)

            return True
    except Timeout:
        log_error(f"Timeout: Impossibile acquisire il lock su .env per aggiornare '{key}'")
        return False
    except Exception as e:
        log_error(f"Errore aggiornamento .env: {e}")
        return False


def save_notebooks(notebooks: List[Dict]):
    """
    Salva la lista dei quadernini nel .env come JSON string.
    Questa funzione è THREAD-SAFE (usa il suo lock).
    """
    lock = FileLock(str(ENV_LOCK_PATH), timeout=10)
    try:
        with lock:
            import json
            from dotenv import load_dotenv
            notebooks_json = json.dumps(notebooks)

            # NON chiamiamo update_env_variable() per evitare deadlock!
            # Scriviamo direttamente il file .env qui

            # Assicura che il file esista
            if not ENV_PATH.exists():
                with open(ENV_PATH, "w") as f:
                    f.write(f"QUADERNINI={notebooks_json}\n")
            else:
                # Leggi tutte le righe esistenti
                with open(ENV_PATH, "r") as f:
                    lines = f.readlines()

                new_lines = []
                key_found = False

                for line in lines:
                    if line.strip().startswith("QUADERNINI="):
                        new_lines.append(f"QUADERNINI={notebooks_json}\n")
                        key_found = True
                    else:
                        new_lines.append(line)

                # Se la chiave non c'era, aggiungila in fondo
                if not key_found:
                    if new_lines and not new_lines[-1].endswith('\n'):
                        new_lines[-1] += '\n'
                    new_lines.append(f"QUADERNINI={notebooks_json}\n")

                # Riscrivi il file
                with open(ENV_PATH, "w") as f:
                    f.writelines(new_lines)

            # Forza ricarica delle variabili d'ambiente dopo il salvataggio
            load_dotenv(override=True)

            return True
    except Timeout:
        log_error("Timeout: Impossibile acquisire il lock su .env per salvare i quadernini")
        return False
    except Exception as e:
        log_error(f"Errore salvataggio quadernini: {e}")
        return False


def load_notebooks() -> List[Dict]:
    """
    Carica la lista dei quadernini dal .env.
    Questa funzione NON necessita di lock perché legge da os.getenv,
    che è in memoria di processo.
    """
    try:
        import json
        notebooks_json = os.getenv("QUADERNINI", "[]")
        # Gestisce sia il caso in cui è già una lista che stringa JSON
        if notebooks_json.startswith('[') and notebooks_json.endswith(']'):
            return json.loads(notebooks_json)
        else:
            log_warning(f"Quadernini in formato non valido: {notebooks_json}")
            return []
    except Exception as e:
        log_error(f"Errore caricamento quadernini: {e}")
        return []


def add_notebook(name: str, description: str = "", store_name: str = "") -> bool:
    """
    Aggiunge un nuovo quadernino alla lista.
    (Eredita la sicurezza dal lock in save_notebooks)
    """
    try:
        notebooks = load_notebooks()
        if any(nb["name"] == name for nb in notebooks):
            return False

        new_notebook = {
            "name": name,
            "description": description,
            "store_name": store_name,
            "created_at": os.getenv("CREATION_TIME", ""),
            "file_count": 0,
            "files": []
        }
        notebooks.append(new_notebook)
        return save_notebooks(notebooks)
    except Exception as e:
        log_error(f"Errore aggiunta quadernino: {e}")
        return False


def remove_notebook(name: str) -> bool:
    """
    Rimuove un quadernino dalla lista.
    (Eredita la sicurezza dal lock in save_notebooks)
    """
    try:
        notebooks = load_notebooks()
        notebooks = [nb for nb in notebooks if nb["name"] != name]
        return save_notebooks(notebooks)
    except Exception as e:
        log_error(f"Errore rimozione quadernino: {e}")
        return False


def get_active_notebook() -> Dict:
    """
    Ottiene il quadernino attualmente attivo.
    (Legge da os.getenv, non serve lock)
    """
    try:
        active_name = os.getenv("ACTIVE_NOTEBOOK", "")
        if not active_name:
            return {}
        notebooks = load_notebooks()
        for notebook in notebooks:
            if notebook["name"] == active_name:
                return notebook
        return {}
    except Exception as e:
        log_error(f"Errore recupero quadernino attivo: {e}")
        return {}


def set_active_notebook(name: str) -> bool:
    """
    Imposta il quadernino attivo.
    (Usa il suo lock per evitare deadlock)
    """
    lock = FileLock(str(ENV_LOCK_PATH), timeout=10)
    try:
        with lock:
            from dotenv import load_dotenv
            notebooks = load_notebooks()  # Legge dalla memoria
            if not any(nb["name"] == name for nb in notebooks):
                return False

            # Aggiorna direttamente il file .env per evitare deadlock con update_env_variable()
            # Leggi tutte le righe esistenti
            if ENV_PATH.exists():
                with open(ENV_PATH, "r") as f:
                    lines = f.readlines()
            else:
                lines = []

            new_lines = []
            key_found = False

            for line in lines:
                if line.strip().startswith("ACTIVE_NOTEBOOK="):
                    new_lines.append(f"ACTIVE_NOTEBOOK={name}\n")
                    key_found = True
                else:
                    new_lines.append(line)

            # Se la chiave non c'era, aggiungila in fondo
            if not key_found:
                if new_lines and not new_lines[-1].endswith('\n'):
                    new_lines[-1] += '\n'
                new_lines.append(f"ACTIVE_NOTEBOOK={name}\n")

            # Riscrivi il file
            with open(ENV_PATH, "w") as f:
                f.writelines(new_lines)

            # Forza ricarica delle variabili d'ambiente (lockato)
            load_dotenv(override=True)
            return True
    except Timeout:
        log_error(f"Timeout: Impossibile acquisire il lock su .env per settare quadernino attivo")
        return False
    except Exception as e:
        log_error(f"Errore impostazione quadernino attivo: {e}")
        return False


def add_file_to_notebook(notebook_name: str, file_name: str) -> bool:
    """
    Aggiunge un file a un quadernino specifico.
    (Eredita la sicurezza dal lock in save_notebooks)
    """
    try:
        notebooks = load_notebooks()
        for notebook in notebooks:
            if notebook["name"] == notebook_name:
                if "files" not in notebook:
                    notebook["files"] = []
                if file_name not in notebook["files"]:
                    notebook["files"].append(file_name)
                    notebook["file_count"] = len(notebook["files"])
                break
        return save_notebooks(notebooks)
    except Exception as e:
        log_error(f"Errore aggiunta file al quadernino: {e}")
        return False


def get_notebook_files(notebook_name: str) -> List[str]:
    """
    Ottiene la lista dei file di un quadernino specifico.
    (Legge da os.getenv, non serve lock)
    """
    try:
        notebooks = load_notebooks()
        for notebook in notebooks:
            if notebook["name"] == notebook_name:
                return notebook.get("files", [])
        return []
    except Exception as e:
        log_error(f"Errore recupero file quadernino: {e}")
        return []


def remove_file_from_notebook(notebook_name: str, file_name: str) -> bool:
    """
    Rimuove un file da un quadernino specifico.
    (Eredita la sicurezza dal lock in save_notebooks)
    """
    try:
        notebooks = load_notebooks()
        for notebook in notebooks:
            if notebook["name"] == notebook_name:
                if "files" in notebook and file_name in notebook["files"]:
                    notebook["files"].remove(file_name)
                    notebook["file_count"] = len(notebook["files"])
                break
        return save_notebooks(notebooks)
    except Exception as e:
        log_error(f"Errore rimozione file dal quadernino: {e}")
        return False


def find_existing_store_for_notebook(notebook_name: str, api_key: str) -> str:
    """
    Cerca se esiste già un File Search store per il quadernino specificato.
    (Non tocca .env, non serve lock)
    """
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        for store in client.file_search_stores.list():
            store_display = getattr(store, 'display_name', '')
            if f'Quadernino - {notebook_name}' in store_display:
                log_info(f"Store esistente trovato per '{notebook_name}': {store.name}")
                return store.name
        log_info(f"Nessun store esistente trovato per '{notebook_name}'")
        return ""
    except Exception as e:
        log_error(f"Errore ricerca store esistente per '{notebook_name}': {e}")
        return ""


def restore_notebooks_from_api(api_key: str) -> int:
    """
    Scansiona tutti i File Search stores su Google e ricostruisce l'elenco dei quadernini.
    (Chiama save_notebooks, che è lockato)
    """
    try:
        from google import genai
        import json
        log_info("Iniziando ripristino automatico quadernini da Google API")
        client = genai.Client(api_key=api_key)
        restored_notebooks = []
        stores = list(client.file_search_stores.list())
        log_info(f"Trovati {len(stores)} File Search stores totali")

        for store in stores:
            store_display = getattr(store, 'display_name', '')
            store_name = getattr(store, 'name', '')

            if store_display.startswith('Quadernino - '):
                notebook_name = store_display.replace('Quadernino - ', '').strip()
                if notebook_name:
                    file_count = 0
                    files_list = []
                    try:
                        if hasattr(store, 'active_documents_count'):
                            file_count = int(getattr(store, 'active_documents_count', 0))
                        elif hasattr(store, 'file_names'):
                            files_list = list(getattr(store, 'file_names', []))
                            file_count = len(files_list)
                    except Exception as e:
                        log_warning(f"Impossibile ottenere dettagli file per {notebook_name}: {e}")

                    store_created_at = getattr(store, 'create_time', 'unknown')
                    if hasattr(store_created_at, 'isoformat'):
                        store_created_at = store_created_at.isoformat()

                    restored_notebook = {
                        "name": notebook_name,
                        "description": f"Ripristinato automaticamente da Google Cloud ({len(restored_notebooks) + 1}/{len(stores)})",
                        "store_name": store_name,
                        "created_at": "ripristinato",
                        "file_count": file_count,
                        "files": files_list,
                        "restored": True,
                        "store_created_at": store_created_at
                    }
                    restored_notebooks.append(restored_notebook)
                    log_info(f"Quadernino ripristinato: {notebook_name} ({file_count} file)")

        if restored_notebooks:
            if save_notebooks(restored_notebooks):
                log_info(f"Salvati {len(restored_notebooks)} quadernini ripristinati nel .env")
                return len(restored_notebooks)
            else:
                log_error("Fallimento salvataggio quadernini ripristinati")
                return 0
        else:
            log_info("Nessun quadernino Quadernino trovato su Google Cloud")
            return 0
    except Exception as e:
        log_error(f"Errore durante ripristino quadernini: {e}")
        return 0


def auto_restore_on_first_setup(api_key: str) -> dict:
    """
    Funzione principale da chiamare quando l'utente inserisce una nuova API key.
    (Non tocca .env direttamente, non serve lock)
    """
    result = {"attempted": True, "restored_count": 0, "message": ""}
    existing_notebooks = load_notebooks()

    if existing_notebooks:
        log_info(f".env contiene già {len(existing_notebooks)} quadernini, salto ripristino automatico")
        result["message"] = f"Gia presenti {len(existing_notebooks)} quadernini nel sistema"
        return result

    log_info("Nessun quadernino locale trovato, avvio ripristino automatico da Google Cloud")
    restored_count = restore_notebooks_from_api(api_key)
    result["restored_count"] = restored_count

    if restored_count > 0:
        result["message"] = f"✅ Ripristinati automaticamente {restored_count} quadernini da Google Cloud!"
    else:
        result["message"] = "Nessun quadernino precedente trovato su Google Cloud."
    return result


def update_notebook_store_name(notebook_name: str, store_name: str) -> bool:
    """
    Aggiorna il nome dello store nel quadernino.
    (Eredita la sicurezza dal lock in save_notebooks)
    """
    try:
        notebooks = load_notebooks()
        for notebook in notebooks:
            if notebook["name"] == notebook_name:
                notebook["store_name"] = store_name
                break
        return save_notebooks(notebooks)
    except Exception as e:
        log_error(f"Errore aggiornamento store quadernino: {e}")
        return False
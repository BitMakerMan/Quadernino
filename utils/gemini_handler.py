from google import genai
from google.genai import types
import streamlit as st
import time
from pathlib import Path
import sys
from utils.logger import log_info, log_warning, log_error, log_error_with_context, log_api_call


# NON importiamo più file_manager per l'estrazione del testo.
# Fa tutto Google sui suoi server.

def get_available_models(api_key):
    """Recupera dinamicamente la lista dei modelli Gemini disponibili."""
    if not api_key:
        return []
    try:
        # Usa il nuovo client per listare i modelli
        client = genai.Client(api_key=api_key)
        models = client.models.list()

        # Filtra i modelli che supportano generateContent e contengono "gemini"
        gemini_models = []

        for model in models:
            # Controlla sia supported_generation_methods (vecchio) che supported_actions (nuovo)
            has_generate_content = False

            if hasattr(model, 'supported_generation_methods'):
                if 'generateContent' in model.supported_generation_methods:
                    has_generate_content = True
            elif hasattr(model, 'supported_actions'):
                if 'generateContent' in model.supported_actions:
                    has_generate_content = True

            if has_generate_content:
                if hasattr(model, 'name') and 'gemini' in model.name:
                    gemini_models.append(model.name)

        return sorted(gemini_models, reverse=True)
    except Exception as e:
        log_error_with_context(e, "get_available_models", {"api_key_present": bool(api_key)})
        return []


class GeminiHandler:
    def __init__(self, api_key, model_name=None, chunk_size=200, overlap=20):
        self.api_key = api_key

        # Se non viene passato un modello, usa vuoto per forzare la selezione dall'utente
        if model_name:
            self.model_name = f"models/{model_name}" if not model_name.startswith("models/") else model_name
        else:
            self.model_name = ""

        # Configurazione chunking per ottimizzare la ricerca
        self.chunking_config = {
            'white_space_config': {
                'max_tokens_per_chunk': chunk_size,
                'max_overlap_tokens': overlap
            }
        }

        self.is_configured = False

        # Nome univoco per il File Store (sarà generato per ogni capitolo)
        self.file_store_name = None  # Sarà impostato dinamicamente per ogni capitolo

        if self.api_key:
            try:
                # Usa il client come da documentazione ufficiale
                self.client = genai.Client(api_key=api_key)
                self.is_configured = True
            except Exception as e:
                st.error(f"Configurazione API Key fallita: {e}")
                self.is_configured = False

    def upload_files_to_google(self, local_file_paths):
        """
        Carica i file locali su Google Cloud e attende che siano pronti ('ACTIVE').
        Ritorna una lista di nomi di file ('files/...') pronti per il Vector Store.
        """
        if not self.is_configured or not local_file_paths:
            return []

        google_files = []
        my_bar = None
        try:
            progress_text = "Caricamento file su Google Cloud..."
            my_bar = st.progress(0, text=progress_text)

            for i, file_path in enumerate(local_file_paths):
                file_name = Path(file_path).name
                my_bar.progress((i + 1) / len(local_file_paths), text=f"Upload di {file_name}...")

                uploaded_file = genai.upload_file(path=file_path)
                google_files.append(uploaded_file)

            my_bar.progress(100, text="Upload completato. Attesa elaborazione...")

            timeout = 300  # 5 minuti
            start_time = time.time()

            for i, gfile in enumerate(google_files):
                while (time.time() - start_time) < timeout:
                    my_bar.progress((i + 1) / len(google_files), text=f"Processando {gfile.display_name}...")

                    # Aggiunto un try/except per il get_file, che a volte fallisce
                    try:
                        file_state = genai.get_file(gfile.name).state.name
                    except Exception as e:
                        log_warning(f"Controllo stato fallito per {gfile.display_name}, riprovo... ({e})")
                        st.warning(f"Controllo stato fallito per {gfile.display_name}, riprovo...")
                        time.sleep(2)
                        continue

                    if file_state == "ACTIVE":
                        break
                    if file_state == "FAILED":
                        raise Exception(f"Elaborazione fallita per {gfile.display_name}")
                    time.sleep(3)  # Polling

            my_bar.empty()
            return [f.name for f in google_files]

        except Exception as e:
            st.error(f"Errore durante l'upload dei file: {str(e)}")
            if my_bar: my_bar.empty()
            # Pulizia dei file già caricati se l'upload fallisce a metà
            for gfile in google_files:
                try:
                    genai.delete_file(gfile.name)
                except:
                    pass
            return []

    def create_vector_store_for_chapter(self, chapter_name, local_file_paths):
        """
        Crea un File Search Store specifico per un capitolo.
        """
        if not self.is_configured or not local_file_paths:
            return None

        # Genera nome unico per lo store del capitolo
        timestamp = str(int(time.time()))[-8:]
        self.file_store_name = f"quadernino_cap_{chapter_name.lower().replace(' ', '-').replace('_', '-')}_{timestamp}"

        try:
            # 1. Crea il File Search store per il capitolo
            with st.spinner(f"Creazione File Search Store per '{chapter_name}'..."):
                file_search_store = self.client.file_search_stores.create(
                    config={'display_name': f'Quadernino - {chapter_name}'}
                )

            st.toast(f"Creato File Search Store per '{chapter_name}': {file_search_store.name}")

            # 2. Upload e import dei file con chunking configuration
            uploaded_operations = []
            my_bar = st.progress(0, text=f"Upload e indicizzazione file per '{chapter_name}'...")

            for i, file_path in enumerate(local_file_paths):
                file_name = Path(file_path).name
                my_bar.progress((i + 1) / len(local_file_paths), text=f"Processando {file_name}...")

                try:
                    # Sanitizza il nome del file per l'API Google (max 40 caratteri)
                    safe_file_name = file_name.lower()
                    safe_file_name = ''.join(c if c.isalnum() else '-' for c in safe_file_name)
                    safe_file_name = '-'.join(filter(None, safe_file_name.split('-')))

                    # Tronca il nome per rispettare il limite di 40 caratteri
                    # Considera anche il timestamp (6 caratteri + trattino)
                    max_base_length = 33  # 40 - 6 (timestamp) - 1 (trattino)
                    if len(safe_file_name) > max_base_length:
                        safe_file_name = safe_file_name[:max_base_length]

                    # Aggiungi timestamp per evitare conflitti
                    file_timestamp = str(int(time.time()))[-6:]
                    unique_safe_name = f"{safe_file_name}-{file_timestamp}"

                    # Controllo finale per sicurezza
                    if len(unique_safe_name) > 40:
                        unique_safe_name = unique_safe_name[:40]

                    sample_file = self.client.files.upload(
                        file=file_path,
                        config={
                            'name': unique_safe_name,
                            'display_name': file_name
                        }
                    )

                    # Import con chunking configuration e metadati
                    import_config = {
                        'chunking_config': self.chunking_config
                    }

                    # Aggiungi metadati specifici del capitolo
                    metadata = self._extract_file_metadata(file_name, file_path)
                    metadata.append({"key": "chapter", "string_value": chapter_name})

                    if metadata:
                        import_config['custom_metadata'] = metadata

                    operation = self.client.file_search_stores.import_file(
                        file_search_store_name=file_search_store.name,
                        file_name=sample_file.name,
                        config=import_config
                    )
                    uploaded_operations.append(operation)
                    st.success(f"✅ {file_name} uploadato in '{chapter_name}'")

                except Exception as e:
                    st.error(f"Errore processamento {file_name}: {str(e)}")

            my_bar.empty()

            if not uploaded_operations:
                st.error("Nessun file è stato caricato correttamente.")
                return None

            # 3. Attesa completamento importazioni
            with st.spinner(f"Attesa indicizzazione file per '{chapter_name}'..."):
                for i, operation in enumerate(uploaded_operations):
                    file_name = Path(local_file_paths[i]).name

                    max_wait_time = 300  # 5 minuti massimo per file
                    start_time = time.time()

                    while not operation.done and (time.time() - start_time) < max_wait_time:
                        time.sleep(5)
                        try:
                            operation = self.client.operations.get(operation)
                        except Exception:
                            break

                    # Controlla il risultato dell'operazione
                    if hasattr(operation, 'result') and operation.result:
                        st.success(f"✅ {file_name} indicizzato con successo")
                    elif hasattr(operation, 'error') and operation.error:
                        st.error(f"❌ Errore importazione {file_name}: {operation.error}")
                    else:
                        if operation.done:
                            st.success(f"✅ {file_name} indicizzato con successo")
                        else:
                            st.warning(f"⚠️ {file_name} - Timeout nell'indicizzazione")

            st.success(f"✅ Capitolo '{chapter_name}' creato con {len(uploaded_operations)} file!")
            st.caption(f"📊 Chunking configurato: {self.chunking_config['white_space_config']['max_tokens_per_chunk']} tokens per chunk")
            return file_search_store.name

        except Exception as e:
            st.error(f"❌ Errore durante la creazione del File Search Store per '{chapter_name}': {str(e)}")
            return None

    def create_or_get_vector_store(self, local_file_paths):
        """
        Metodo legacy per compatibilità. Usa create_vector_store_for_chapter invece.
        """
        return self.create_vector_store_for_chapter("Generale", local_file_paths)

    def generate_response_stream(self, prompt, history=None, vector_store_name=None):
        """
        Genera una risposta usando File Search come da documentazione ufficiale.
        """
        if not self.is_configured:
            yield "⚠️ API Key mancante."
            return

        if not vector_store_name:
            yield "⚠️ File Search Store non trovato. Prova a ricaricare i file."
            return

        try:
            # Usa il client con File Search come da documentazione ufficiale
            config = types.GenerateContentConfig(
                system_instruction="""
                Sei Quadernino, un assistente di studio intelligente e preciso.
                Il tuo compito è rispondere alle domande dell'utente basandoti ESCLUSIVAMENTE sui documenti forniti nello strumento di ricerca (File Search).
                NON usare la tua conoscenza generale. Se la risposta non si trova nei documenti, dillo chiaramente: "Non ho trovato questa informazione nei documenti caricati."
                Cita sempre le tue fonti in modo chiaro alla fine della risposta, usando il nome del file.
                """
            )

            # Aggiungi File Search se disponibile
            if vector_store_name:
                try:
                    # Configura il File Search con l'approccio corretto
                    file_search_config = types.FileSearch(
                        file_search_store_names=[vector_store_name]
                    )
                    config.tools = [
                        types.Tool(file_search=file_search_config)
                    ]
                except Exception as e:
                    log_error_with_context(e, "configurazione File Search")
                    # Fallback senza tools
                    pass

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # Simula streaming per compatibilità con l'interfaccia esistente
            if response.text:
                for word in response.text.split():
                    yield word + " "
                    time.sleep(0.05)  # Simula streaming
            else:
                yield "Nessuna risposta generata."

        except Exception as e:
            yield f"❌ Errore durante la generazione: {str(e)}"

    def test_connection(self):
        """Testa la connessione all'API usando il nuovo client."""
        if not self.is_configured:
            return False
        if not self.model_name:
            log_error("Test connessione fallito: Nessun modello specificato")
            return False
        try:
            # Usa il client per testare la connessione
            response = self.client.models.generate_content(
                model=self.model_name,
                contents="Test",
                config=types.GenerateContentConfig(max_output_tokens=10)
            )
            log_api_call("test_connection", "success", 0)
            return True
        except Exception as e:
            log_error_with_context(e, "test_connection", {"model": self.model_name})
            return False

    def get_context_info(self, vector_store_name=None):
        """Ottieni informazioni sul File Search Store."""
        if not vector_store_name:
            return {"has_context": False, "using_file_search": True}
        try:
            # Usa il nuovo client per ottenere le informazioni
            store = self.client.file_search_stores.get(name=vector_store_name)

            # Prova diversi attributi per il conteggio file
            file_count = 0
            try:
                if hasattr(store, 'active_documents_count'):
                    active_count = getattr(store, 'active_documents_count', 0)
                    file_count = int(active_count) if active_count is not None else 0
                elif hasattr(store, 'file_names'):
                    file_count = len(getattr(store, 'file_names', []))
                elif hasattr(store, 'files'):
                    file_count = len(getattr(store, 'files', []))
                elif hasattr(store, 'file_count'):
                    count = getattr(store, 'file_count', 0)
                    file_count = int(count) if count is not None else 0
            except Exception as e:
                log_warning(f"Errore nel calcolo file_count: {e}")
                file_count = 0

            return {
                "has_context": True,
                "using_file_search": True,
                "vector_store_name": store.name,
                "vector_store_display_name": getattr(store, 'display_name', store.name),
                "file_count": file_count,
                "model_name": self.model_name
            }
        except Exception as e:
            log_error_with_context(e, "recupero info store", {"store_name": vector_store_name})
            return {"has_context": False, "using_file_search": True}

    def list_file_search_stores(self):
        """Elenca tutti i File Search stores disponibili."""
        if not self.is_configured:
            return []
        try:
            stores = []
            for store in self.client.file_search_stores.list():
                stores.append({
                    'name': store.name,
                    'display_name': getattr(store, 'display_name', store.name),
                })
            return stores
        except Exception as e:
            log_error_with_context(e, "elenco File Search stores")
            return []

    def get_file_search_store(self, store_name):
        """Recupera un File Search store specifico."""
        if not self.is_configured:
            return None
        try:
            return self.client.file_search_stores.get(name=store_name)
        except Exception as e:
            error_str = str(e)
            log_error_with_context(e, "recupero File Search store", {"store_name": store_name})

            # Se è un errore di permessi, restituisci un'informazione speciale
            if "PERMISSION_DENIED" in error_str or "403" in error_str:
                return {"permission_error": True, "store_name": store_name}

            return None

    def delete_file_search_store(self, store_name, force=False):
        """Elimina un File Search store specifico."""
        if not self.is_configured:
            return False
        try:
            config = {'force': True} if force else {}
            self.client.file_search_stores.delete(name=store_name, config=config)
            return True
        except Exception as e:
            log_error_with_context(e, "eliminazione File Search store", {"store_name": store_name, "force": force})
            return False

    def _extract_file_metadata(self, file_name, file_path):
        """Estrae metadati automatici dal nome e percorso del file."""
        import os
        from datetime import datetime

        metadata = []
        file_path_obj = Path(file_path)

        # Metadati di base
        metadata.append({"key": "file_name", "string_value": file_name})
        metadata.append({"key": "file_extension", "string_value": file_path_obj.suffix.lower()})
        metadata.append({"key": "upload_date", "string_value": datetime.now().isoformat()})

        # Estrai anno dal nome file se presente
        import re
        year_match = re.search(r'(19|20)\d{2}', file_name)
        if year_match:
            metadata.append({"key": "year", "numeric_value": int(year_match.group())})

        # Categoria basata sull'estensione
        ext = file_path_obj.suffix.lower()
        if ext in ['.pdf', '.doc', '.docx']:
            metadata.append({"key": "document_type", "string_value": "academic_paper"})
        elif ext in ['.txt', '.md']:
            metadata.append({"key": "document_type", "string_value": "text_document"})
        elif ext in ['.ppt', '.pptx']:
            metadata.append({"key": "document_type", "string_value": "presentation"})

        return metadata

    def generate_response_with_metadata_filter(self, prompt, vector_store_name, metadata_filter=None, history=None):
        """
        Genera una risposta usando File Search con filtro metadati.
        """
        if not self.is_configured:
            yield "⚠️ API Key mancante."
            return

        if not vector_store_name:
            yield "⚠️ File Search Store non trovato. Prova a ricaricare i file."
            return

        try:
            # Configura File Search con filtro metadati
            file_search_config = {
                'file_search_store_names': [vector_store_name]
            }

            if metadata_filter:
                file_search_config['metadata_filter'] = metadata_filter

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="""
                    Sei Quadernino, un assistente di studio intelligente e preciso.
                    Il tuo compito è rispondere alle domande dell'utente basandoti ESCLUSIVAMENTE sui documenti forniti nello strumento di ricerca (File Search).
                    NON usare la tua conoscenza generale. Se la risposta non si trova nei documenti, dillo chiaramente: "Non ho trovato questa informazione nei documenti caricati."
                    Cita sempre le tue fonti in modo chiaro alla fine della risposta, usando il nome del file.
                    """,
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(**file_search_config)
                        )
                    ]
                )
            )

            # Simula streaming per compatibilità
            if response.text:
                for word in response.text.split():
                    yield word + " "
                    time.sleep(0.05)
            else:
                yield "Nessuna risposta generata."

            # Aggiungi citazioni se disponibili
            if hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'grounding_metadata'):
                        yield f"\n\n📚 **Fonti:**\n"
                        for citation in candidate.grounding_metadata:
                            if hasattr(citation, 'file_name'):
                                yield f"• {citation.file_name}\n"

        except Exception as e:
            yield f"❌ Errore durante la generazione: {str(e)}"

    def cleanup_resources(self, vector_store_name):
        """Pulisce il File Search Store su Google usando i nuovi metodi."""
        if not vector_store_name or not self.is_configured:
            return
        try:
            # Usa il nuovo metodo per eliminare il File Search store
            success = self.delete_file_search_store(vector_store_name, force=True)
            if success:
                st.toast("File Search Store eliminato da Google Cloud.")
            else:
                st.error("Errore durante l'eliminazione del File Search Store.")
        except Exception as e:
            # Non mostrare errore se lo store è già stato cancellato
            if "not found" not in str(e).lower():
                log_warning(f"Errore pulizia File Search Store: {e}")
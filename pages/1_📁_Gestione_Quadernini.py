import streamlit as st
import time
import os
from pathlib import Path
from utils.file_manager import save_uploaded_file, list_local_files, delete_local_file, get_file_info
from utils.env_manager import (
    load_notebooks, add_notebook, remove_notebook, set_active_notebook, get_active_notebook,
    add_file_to_notebook, remove_file_from_notebook, get_notebook_files,
    find_existing_store_for_notebook, update_notebook_store_name, auto_restore_on_first_setup
)
from utils.logger import log_error
from utils.gemini_handler import GeminiHandler

st.set_page_config(page_title="Gestione Quadernini - Quadernino", page_icon="📁")

st.title("📁 Gestione Quadernini")
st.caption(
    "Organizza i tuoi materiali di studio per argomenti. Ogni quadernino ha i suoi documenti e il suo indice di ricerca.")

# --- Gestione Quadernini ---
st.subheader("📚 I Tuoi Quadernini")

notebooks = load_notebooks()
active_notebook = get_active_notebook()

if st.session_state.get("api_key"):
    col_sync, col_info = st.columns([1, 3])
    with col_sync:
        if st.button("🔄", help="Sincronizza quadernini da Google Cloud", type="secondary"):
            with st.spinner("🔍 Sincronizzazione quadernini da Google Cloud..."):
                restore_result = auto_restore_on_first_setup(st.session_state.api_key)
            if restore_result["restored_count"] > 0:
                st.success(restore_result["message"], icon="🎉")
                st.balloons()
            else:
                st.info(restore_result["message"])
            time.sleep(2)
            st.rerun()
    with col_info:
        st.caption("🔄 Sincronizza quadernini precedenti da Google Cloud")

col1, col2 = st.columns([3, 1])
with col1:
    if not notebooks:
        st.info("Nessun quadernino creato. Crea il tuo primo quadernino qui sotto!")
    else:
        for notebook in notebooks:
            is_active = notebook["name"] == active_notebook.get("name", "")
            with st.container(border=is_active):
                col_a, col_b, col_c = st.columns([3, 2, 1])
                with col_a:
                    if is_active:
                        st.success(f"📖 **{notebook['name']}** *(attivo)*")
                    else:
                        st.write(f"📖 **{notebook['name']}**")
                    if notebook.get("description"):
                        st.caption(notebook["description"])
                    st.caption(f"📄 {notebook.get('file_count', 0)} file")
                with col_b:
                    if not is_active:
                        if st.button("Attiva", key=f"activate_{notebook['name']}"):
                            if set_active_notebook(notebook["name"]):
                                st.success(f"Quadernino '{notebook['name']}' attivato!")
                                time.sleep(1)
                                st.rerun()
                with col_c:
                    if st.button("🗑️", key=f"del_notebook_{notebook['name']}", help="Elimina quadernino"):
                        st.session_state["confirm_delete"] = notebook["name"]
                        st.rerun()

with st.expander("➕ Crea Nuovo Quadernino", expanded=not notebooks):
    new_notebook_name = st.text_input("Nome del quadernino", placeholder="es: Storia Romana, Fisica Quantistica")
    new_notebook_desc = st.text_area("Descrizione (opzionale)",
                                     placeholder="Breve descrizione degli argomenti trattati...")
    col_create, col_cancel = st.columns(2)
    with col_create:
        if st.button("➕ Crea Quadernino", type="primary", disabled=not new_notebook_name.strip()):
            if add_notebook(new_notebook_name.strip(), new_notebook_desc.strip()):
                st.success(f"Quadernino '{new_notebook_name}' creato!")
                set_active_notebook(new_notebook_name.strip())
                time.sleep(1)
                st.rerun()
            else:
                st.error("Errore nella creazione del quadernino. Forse esiste già?")
    with col_cancel:
        if st.button("Annulla"):
            st.rerun()

st.divider()

if "confirm_delete" in st.session_state and st.session_state["confirm_delete"]:
    notebook_to_delete = st.session_state["confirm_delete"]
    st.warning(
        f"⚠️ **Conferma eliminazione**: Sei sicuro di voler eliminare il quadernino '{notebook_to_delete}'? Anche il suo indice di ricerca (File Store) su Google Cloud verrà rimosso.")
    col_confirm, col_abort = st.columns(2)
    with col_confirm:
        if st.button("✅ Conferma", type="primary"):
            try:
                notebook_obj = next((nb for nb in notebooks if nb["name"] == notebook_to_delete), None)
                store_to_delete = notebook_obj.get('store_name') if notebook_obj else None
                api_key = st.session_state.get("api_key") or os.getenv("GOOGLE_API_KEY")

                if store_to_delete and api_key:
                    with st.spinner(f"Eliminazione indice '{store_to_delete}' da Google Cloud..."):
                        gemini = GeminiHandler(api_key=api_key)
                        if gemini.delete_file_search_store(store_to_delete, force=True):
                            st.toast(f"Indice '{store_to_delete}' eliminato da Google Cloud.")
                        else:
                            st.warning(f"Impossibile eliminare l'indice '{store_to_delete}'.")
                st.session_state.pop(f"vector_store_{notebook_to_delete}", None)
            except Exception as e:
                st.error(f"Errore durante la pulizia delle risorse cloud: {e}")
            if remove_notebook(notebook_to_delete):
                st.success(f"Quadernino '{notebook_to_delete}' eliminato localmente!")
                del st.session_state["confirm_delete"]
                time.sleep(1)
                st.rerun()
            else:
                st.error("Errore nell'eliminare il quadernino localmente.")
    with col_abort:
        if st.button("❌ Annulla"):
            del st.session_state["confirm_delete"]
            st.rerun()

if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

if active_notebook:
    with st.expander(f"📤 Carica file nel quadernino '{active_notebook['name']}'", expanded=True):
        uploaded_files = st.file_uploader(
            f"Carica file per '{active_notebook['name']}' (PDF, DOCX, TXT, MD)",
            type=["pdf", "docx", "txt", "md"],
            accept_multiple_files=True,
            key=f"uploader_{st.session_state['uploader_key']}"
        )
        if uploaded_files:
            for file in uploaded_files:
                path = save_uploaded_file(file)
                if path:
                    if add_file_to_notebook(active_notebook["name"], file.name):
                        st.toast(f"✅ {file.name} aggiunto a '{active_notebook['name']}'")
                    else:
                        st.error(f"❌ Errore aggiungendo {file.name} al quadernino")
            notebook_key = f"vector_store_{active_notebook['name']}"
            if notebook_key in st.session_state:
                st.session_state.pop(notebook_key, None)
            st.toast("📁 File aggiunti! Ricorda di indicizzare il quadernino prima di usare la chat.")
            st.session_state["uploader_key"] += 1
            time.sleep(1)
            st.rerun()
else:
    st.warning("⚠️ Attiva un quadernino per caricare file.", icon="📖")

if active_notebook:
    notebook_files = get_notebook_files(active_notebook['name'])
    if notebook_files:
        st.subheader("🔍 Indicizzazione Ricerca")
        notebook_key = f"vector_store_{active_notebook['name']}"
        is_indexed_in_session = notebook_key in st.session_state
        saved_store_name = active_notebook.get('store_name', '')

        if not is_indexed_in_session and saved_store_name:
            try:
                gemini = GeminiHandler(api_key=st.session_state.api_key)
                existing_store = gemini.get_file_search_store(saved_store_name)
                if existing_store:
                    st.session_state[notebook_key] = saved_store_name
                    is_indexed_in_session = True
                    st.info("🔄 Indice esistente trovato e ripristinato!")
            except Exception as e:
                log_error(f"Errore verifica store esistente: {e}")

        is_indexed = is_indexed_in_session or bool(saved_store_name)

        if is_indexed:
            st.success("✅ Quadernino indicizzato e pronto per la chat!")
            if saved_store_name:
                st.caption(f"📁 Store: {saved_store_name}")
        else:
            st.warning("⚠️ Quadernino non indicizzato", icon="🔍")
            st.caption(
                f"⚠️ Il quadernino '{active_notebook['name']}' ha {len(notebook_files)} file ma non è ancora indicizzato.")

        col_index, col_regenerate = st.columns([1, 1])
        with col_index:
            if st.button(f"🔍 Indicizza '{active_notebook['name']}'",
                         type="primary" if not is_indexed else "secondary"):

                # --- INIZIO CODICE MIGLIORATO (Controllo Sincronia File) ---
                local_files_all_paths = list_local_files()
                local_files_names = [Path(f).name for f in local_files_all_paths]
                notebook_files_in_env = get_notebook_files(active_notebook['name'])

                missing_files = []
                files_to_index_paths = []

                for file_name_in_env in notebook_files_in_env:
                    if file_name_in_env not in local_files_names:
                        missing_files.append(file_name_in_env)
                    else:
                        idx = local_files_names.index(file_name_in_env)
                        files_to_index_paths.append(local_files_all_paths[idx])

                if missing_files:
                    st.error("❌ Impossibile indicizzare! File mancanti dalla cartella 'uploaded_files/':")
                    for f in missing_files:
                        st.write(f"• {f}")
                    st.info("Carica nuovamente i file mancanti prima di indicizzare.")
                elif not files_to_index_paths:
                    st.warning("⚠️ Nessun file da indicizzare per questo quadernino.")
                else:
                    # --- FINE CODICE MIGLIORATO ---
                    with st.spinner(
                            f"🔧 Creazione indice per '{active_notebook['name']}' con {len(files_to_index_paths)} file..."):
                        try:
                            gemini = GeminiHandler(
                                api_key=st.session_state.api_key,
                                model_name=st.session_state.get("selected_model", "models/gemini-2.5-flash")
                            )
                            existing_store = find_existing_store_for_notebook(active_notebook['name'],
                                                                              st.session_state.api_key)
                            if existing_store:
                                store_name = existing_store
                                st.info(f"🔄 Trovato store esistente. Riutilizzo...")
                            else:
                                # Usa la lista filtrata e verificata
                                store_name = gemini.create_vector_store_for_chapter(active_notebook['name'],
                                                                                    files_to_index_paths)
                            if store_name:
                                st.session_state[notebook_key] = store_name
                                update_notebook_store_name(active_notebook['name'], store_name)
                                st.success(
                                    f"✅ Indice per '{active_notebook['name']}' creato con {len(files_to_index_paths)} file!",
                                    icon="🎯")
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error(
                                    "❌ Errore durante la creazione dell'indice. Controlla i file e la connessione.")
                        except Exception as e:
                            st.error(f"❌ Errore: {str(e)}")

        with col_regenerate:
            if st.button("🔄 Rigenera Indice", help="Rimuove l'indice esistente e lo ricrea da zero"):
                store_to_delete = st.session_state.get(notebook_key) or active_notebook.get('store_name')
                if store_to_delete:
                    try:
                        gemini = GeminiHandler(
                            api_key=st.session_state.api_key,
                            model_name=st.session_state.get("selected_model", "models/gemini-2.5-flash")
                        )
                        with st.spinner("Pulizia vecchio indice..."):
                            gemini.delete_file_search_store(store_to_delete, force=True)

                        st.session_state.pop(notebook_key, None)
                        # Rimuovi anche lo store_name dal .env
                        update_notebook_store_name(active_notebook['name'], "")

                        st.success("🧹 Vecchio indice rimosso. Ora usa 'Indicizza' per crearlo nuovo!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Errore: {str(e)}")
                else:
                    st.info("Nessun indice da rigenerare.")

    st.markdown("---")

if active_notebook:
    st.subheader(f"📚 File del quadernino '{active_notebook['name']}'")
    local_files = list_local_files()
    notebook_files = get_notebook_files(active_notebook['name'])

    if not local_files:
        st.info("Nessun documento caricato localmente.")
    else:
        st.caption("File locali disponibili (puoi aggiungerli al quadernino attivo):")
        for file_path in local_files:
            col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1.5, 1, 0.5])
            info = get_file_info(file_path)
            if info:
                file_name = info['name']
                is_in_notebook = file_name in notebook_files
                with col1:
                    if is_in_notebook:
                        st.success(f"📄 **{file_name}** *(in questo quadernino)*")
                    else:
                        st.write(f"📄 **{file_name}**")
                with col2:
                    st.write(info['type'].upper())
                with col3:
                    st.write(info['size_formatted'])
                with col4:
                    if is_in_notebook:
                        st.caption("✅ In quadernino")
                    else:
                        if st.button("Aggiungi", key=f"add_{file_name}", help="Aggiungi al quadernino"):
                            if add_file_to_notebook(active_notebook['name'], file_name):
                                st.success(f"✅ {file_name} aggiunto a '{active_notebook['name']}'")
                                time.sleep(1);
                                st.rerun()
                with col5:
                    if is_in_notebook:
                        if st.button("❌", key=f"rem_{file_name}", help="Rimuovi dal quadernino"):
                            if remove_file_from_notebook(active_notebook['name'], file_name):
                                st.success(f"❌ {file_name} rimosso da '{active_notebook['name']}'")
                                time.sleep(1);
                                st.rerun()
    if notebook_files:
        st.info(f"📋 **Riepilogo quadernino '{active_notebook['name']}**: {len(notebook_files)} file")
    else:
        st.warning(f"⚠️ Nessun file aggiunto al quadernino '{active_notebook['name']}'.")
else:
    st.subheader("📚 File disponibili")
    local_files = list_local_files()
    if not local_files:
        st.info("Nessun documento caricato.")
    else:
        st.info("Attiva un quadernino per gestire i file al suo interno.")
        for file_path in local_files:
            col1, col2, col3 = st.columns([4, 2, 1])
            info = get_file_info(file_path)
            if info:
                with col1: st.write(f"📄 **{info['name']}**")
                with col2: st.write(info['type'].upper())
                with col3: st.write(info['size_formatted'])
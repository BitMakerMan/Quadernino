import streamlit as st
import os
import time
from utils.gemini_handler import get_available_models, GeminiHandler  # Importa anche GeminiHandler
from utils.env_manager import update_env_variable, auto_restore_on_first_setup
from utils.google_monitor import get_google_monitor

st.set_page_config(page_title="Impostazioni - Quadernino", page_icon="⚙️")

st.title("⚙️ Impostazioni")
st.caption("Configura il motore del tuo Quadernino.")


# --- INIZIO CODICE MIGLIORATO (Funzione Helper) ---
def _invalidate_all_vector_stores():
    """
    Pulisce tutti gli store dei quadernini dalla sessione corrente
    per forzare un ricaricamento (utile se cambia API Key o modello).
    """
    keys_to_pop = [key for key in st.session_state.keys() if key.startswith("vector_store_")]
    for key in keys_to_pop:
        st.session_state.pop(key, None)

    # Pulisce anche la vecchia chiave (se esiste, per sicurezza)
    st.session_state.pop("active_vector_store_name", None)

    if keys_to_pop:
        st.toast(f"Invalidati {len(keys_to_pop)} indici in sessione. Verranno ricaricati.", icon="🔄")


# --- FINE CODICE MIGLIORATO ---


# --- API Key ---
st.subheader("🔑 Google API Key")

# Link per ottenere la API Key
st.markdown("""
**📖 Come ottenere la tua API Key:**

1. Vai a [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Fai clic su "Create API Key"
3. Copia la chiave generata
4. Incollala qui sotto

> ⚠️ **Nota:** La tua API Key è privata e verrà salvata solo localmente nel file `.env`
""")

# Mostra stato attuale
env_key = os.getenv("GOOGLE_API_KEY")
if env_key:
    st.success("✅ API Key configurata", icon="🔒")
    masked_key = env_key[:8] + "..." + env_key[-4:] if len(env_key) > 12 else "***"
    st.caption(f"Chiave attuale: {masked_key}")

    with st.expander("🔄 Modifica API Key", expanded=False):
        new_key = st.text_input(
            "Nuova API Key", type="password", help="Incolla qui la tua nuova Google API Key",
            key="new_api_key_input"
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Aggiorna", type="primary", disabled=not new_key.strip()):
                if update_env_variable("GOOGLE_API_KEY", new_key.strip()):
                    st.session_state.api_key = new_key.strip()
                    _invalidate_all_vector_stores()  # --- CODICE MIGLIORATO ---
                    st.success("✅ API Key aggiornata!")
                    time.sleep(1)
                    st.rerun()
        with col2:
            if st.button("🗑️ Rimuovi", help="Rimuovi l'API Key dal file .env"):
                if update_env_variable("GOOGLE_API_KEY", ""):
                    st.session_state.api_key = ""
                    _invalidate_all_vector_stores()  # --- CODICE MIGLIORATO ---
                    st.success("✅ API Key rimossa!")
                    time.sleep(1)
                    st.rerun()
else:
    st.info("🔑 Configura la tua API Key per iniziare")
    new_key = st.text_input(
        "Inserisci la tua Google API Key", type="password",
        help="Incolla qui la tua API Key da Google AI Studio", placeholder="AIzaSy..."
    )
    if st.button("💾 Salva API Key", type="primary", disabled=not new_key.strip()):
        if update_env_variable("GOOGLE_API_KEY", new_key.strip()):
            st.session_state.api_key = new_key.strip()

            # Ripristino automatico quadernini da Google Cloud
            with st.spinner("🔍 Ricerca quadernini precedenti..."):
                restore_result = auto_restore_on_first_setup(new_key.strip())

            # Mostra risultato ripristino
            if restore_result["restored_count"] > 0:
                st.success(f"✅ API Key salvata! {restore_result['message']}", icon="🎉")
                st.balloons()  # Festa per quadernini ripristinati!
            else:
                st.success("✅ API Key salvata con successo!")
                st.info(restore_result["message"])

            _invalidate_all_vector_stores()  # --- CODICE MIGLIORATO ---
            time.sleep(2)
            st.rerun()

if not st.session_state.get("api_key"):
    st.error("⚠️ API Key mancante. Configura la tua API Key per usare Quadernino.", icon="🔑")

st.divider()

# --- Modello ---
st.subheader("🧠 Modello Gemini")

# Nota importante sui modelli supportati
st.warning("""
ℹ️ **IMPORTANTE:** Per il File Search (RAG), sono consigliati solo:
- **gemini-2.5-pro** ✅ (più potente)
- **gemini-2.5-flash** ✅ (più veloce)

Altri modelli potrebbero non funzionare con la ricerca documenti.
""")

available_models = []
api_key = st.session_state.get("api_key") or os.getenv("GOOGLE_API_KEY")

if api_key:
    with st.spinner("Ricerca modelli..."):
        available_models = get_available_models(api_key)

if not available_models:
    # Se non riesce a caricare i modelli dinamicamente, usa quelli più comuni
    st.warning("⚠️ Caricamento modelli fallito, uso fallback hardcoded")
    available_models = ["models/gemini-2.5-flash", "models/gemini-2.5-pro", "models/gemini-2.0-flash"]

# Usa il modello salvato nella sessione, nel .env, o il primo disponibile
current_selection = st.session_state.get("selected_model") or os.getenv("DEFAULT_MODEL") or (
    available_models[0] if available_models else "")
if current_selection not in available_models and available_models:
    current_selection = available_models[0]
    # Salva il modello corretto nella sessione
    st.session_state.selected_model = current_selection

selected_idx = 0
if current_selection in available_models:
    selected_idx = available_models.index(current_selection)

new_model = st.selectbox("Seleziona Modello", available_models, index=selected_idx)

# --- INIZIO CODICE MIGLIORATO (Logica di cambio modello) ---
# Controlla se il modello è cambiato rispetto a quello in sessione
model_changed = ("selected_model" not in st.session_state) or (new_model != st.session_state.get("selected_model"))

if new_model and model_changed:
    st.session_state.selected_model = new_model
    # INVALIDA IL VECTOR STORE: Se cambia il modello, gli indici vanno ricaricati
    _invalidate_all_vector_stores()
    update_env_variable("DEFAULT_MODEL", new_model)
    st.toast(f"Modello cambiato in {new_model}. Gli indici verranno ricaricati.", icon="🔄")
# --- FINE CODICE MIGLIORATO ---

st.divider()

# --- Test Connessione ---
st.subheader("🧪 Test e Diagnostica")
if st.session_state.get("api_key"):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 Testa Connessione API", type="secondary"):
            with st.spinner("Test connessione in corso..."):
                try:
                    # Usa il modello selezionato nella sessione
                    selected_model = st.session_state.get("selected_model")
                    if not selected_model:
                        st.error(
                            "❌ Nessun modello selezionato. Seleziona un modello sopra prima di testare la connessione.",
                            icon="⚠️")
                    else:
                        handler = GeminiHandler(api_key=st.session_state.api_key, model_name=selected_model)
                        if handler.test_connection():
                            st.success("✅ Connessione API funzionante!", icon="🎉")
                            st.caption(f"Modello testato: {selected_model}")
                        else:
                            st.error("❌ Connessione API fallita", icon="⚠️")
                            st.caption(
                                "Possibili cause: quota API esaurita, modello non disponibile o problemi di rete")
                except Exception as e:
                    st.error(f"❌ Errore: {str(e)}", icon="⚠️")
    with col2:
        if st.button("📊 Mostra Info Sistema"):
            with st.expander("Informazioni Sistema", expanded=True):
                import sys, platform
                from pathlib import Path

                st.json({
                    "Sistema Operativo": platform.system(),
                    "Versione Python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                    "Directory Progetto": str(Path.cwd()),
                    "File .env esiste": Path(".env").exists(),
                    "Modello Selezionato": st.session_state.get("selected_model", "N/D"),
                    "API Key Configurata": bool(st.session_state.get("api_key"))
                })
st.divider()

# --- 📊 Dashboard Monitoraggio Google ---
st.subheader("📊 Dashboard Google Cloud")

if st.session_state.get("api_key"):
    with st.expander("📊 Monitoraggio API Google", expanded=False):
        with st.spinner("Caricamento statistiche..."):
            try:
                monitor = get_google_monitor(st.session_state.api_key)

                # Statistiche File Search
                file_stats = monitor.get_file_search_stats()

                if file_stats:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📁 File Search Stores", file_stats.get("total_stores", 0))
                    with col2:
                        st.metric("📄 Documenti Indicizzati", file_stats.get("total_files", 0))
                    with col3:
                        st.metric("🗃️ Quadernini", file_stats.get("quadernino_stores", 0))

                    # Occupazione memoria
                    size_mb = file_stats.get("total_size_estimate_mb", 0)
                    if size_mb > 0:
                        st.caption(f"💾 **Occupazione stimata:** {size_mb} MB")

                    # Dettagli quadernini
                    quadernino_files = file_stats.get("quadernino_files", 0)
                    if quadernino_files > 0:
                        st.info(f"📚 **File nei tuoi quadernini:** {quadernino_files}")

                    # Statistiche per tipo di store
                    quadernino_stores = file_stats.get("quadernino_stores", 0)
                    other_stores = file_stats.get("total_stores", 0) - quadernino_stores

                    # Mostra sempre gestione completa store se ci sono store totali
                    total_stores = file_stats.get("total_stores", 0)
                    if total_stores > 0:
                        if other_stores > 0:
                            st.warning(f"⚠️ **Altri store trovati:** {other_stores} (non creati da Quadernino)")
                        else:
                            st.info(f"✅ **Trovati {total_stores} store totali** - Tutti creati da Quadernino")

                        with st.expander("🧹 Gestione Completa Store", expanded=False):
                            st.markdown("### 🗂️ **Gestione File Search Stores**")

                            # Carica tutti gli store dettagliati
                            all_stores = monitor.get_all_stores_detailed()

                            if all_stores.get("stores"):
                                # Riepilogo generale
                                col_a, col_b, col_c = st.columns(3)
                                with col_a:
                                    st.metric("🗃️ Quadernini", all_stores.get("quadernino_count", 0))
                                with col_b:
                                    st.metric("📁 Altri Store", all_stores.get("other_count", 0))
                                with col_c:
                                    st.metric("💾 Spazio Totale", f"{all_stores.get('total_size_mb', 0)} MB")

                                st.markdown("---")

                                # Tabs per categorie
                                tab1, tab2 = st.tabs(["🗃️ Quadernini", "📁 Altri Store"])

                                with tab1:
                                    quadernino_stores = [s for s in all_stores["stores"] if s["is_quadernino"]]
                                    if quadernino_stores:
                                        st.info("ℹ️ **Attenzione:** Eliminare un quadernino qui elimina **permanentemente** i dati da Google Cloud!")
                                        for store in quadernino_stores:
                                            # Chiave univoca per questo store
                                            store_hash = hash(store['store_id']) % 100000
                                            confirm_key = f"confirm_quad_{store_hash}"

                                            # Se è richiesta una conferma, mostra subito sotto la riga
                                            if confirm_key in st.session_state:
                                                st.warning(f"🚨 **Conferma eliminazione '{store['name']}'**")
                                                st.caption(f"⚠️ Questo eliminerà permanentemente {store.get('file_count', 0)} file!")
                                                col_confirm, col_cancel = st.columns([1, 1])
                                                with col_confirm:
                                                    if st.button("✅ Sì, Elimina", type="primary", key=f"yes_{confirm_key}"):
                                                        with st.spinner("Eliminazione quadernino..."):
                                                            try:
                                                                monitor = get_google_monitor(st.session_state.api_key)
                                                                result = monitor.delete_store(store["store_id"], force=True)
                                                                if result.get("success"):
                                                                    st.success(f"✅ Quadernino '{store['name']}' eliminato!")
                                                                    # Pulisci .env
                                                                    from utils.env_manager import load_notebooks, save_notebooks
                                                                    notebooks = load_notebooks()
                                                                    for nb in notebooks:
                                                                        if nb.get('store_name') == store["store_id"]:
                                                                            nb['store_name'] = ''
                                                                    save_notebooks(notebooks)
                                                                    _invalidate_all_vector_stores()
                                                                else:
                                                                    st.error(f"❌ Errore: {result.get('error', 'Errore')}")
                                                                del st.session_state[confirm_key]
                                                                time.sleep(1)
                                                                st.rerun()
                                                            except Exception as e:
                                                                st.error(f"❌ Errore: {e}")
                                                with col_cancel:
                                                    if st.button("❌ Annulla", key=f"no_{confirm_key}"):
                                                        del st.session_state[confirm_key]
                                                        st.rerun()
                                                st.markdown("---")
                                            else:
                                                # Mostra riga normale con pulsante elimina
                                                col_name, col_files, col_size, col_action = st.columns([3, 1, 1, 2])
                                                with col_name:
                                                    st.write(f"📖 **{store['name']}**")
                                                    st.caption(f"ID: `{store['store_id'][:40]}...`")
                                                with col_files:
                                                    st.metric("File", store['file_count'])
                                                with col_size:
                                                    st.write(f"~{store['size_estimate_mb']} MB")
                                                with col_action:
                                                    store_key = f"del_quad_{store_hash}"
                                                    if st.button("🗑️Elimina", key=store_key, help="Elimina quadernino"):
                                                        st.session_state[confirm_key] = store
                                                        st.rerun()  # Forza rerun immediato per mostrare conferma
                                    else:
                                        st.info("Nessun quadernino trovato")

                                with tab2:
                                    other_stores = [s for s in all_stores["stores"] if not s["is_quadernino"]]
                                    if other_stores:
                                        st.success("✅ Questi store possono essere eliminati in sicurezza")
                                        for store in other_stores:
                                            # Chiave univoca per questo store
                                            store_hash = hash(store['store_id']) % 100000
                                            confirm_key = f"confirm_other_{store_hash}"

                                            # Se è richiesta una conferma, mostra subito sotto la riga
                                            if confirm_key in st.session_state:
                                                st.warning(f"🚨 **Conferma eliminazione '{store['name']}'**")
                                                st.caption(f"ℹ️ Questo eliminerà {store.get('file_count', 0)} file da questo store")
                                                col_confirm, col_cancel = st.columns([1, 1])
                                                with col_confirm:
                                                    if st.button("✅ Sì, Elimina", type="primary", key=f"yes_{confirm_key}"):
                                                        with st.spinner("Eliminazione store..."):
                                                            try:
                                                                monitor = get_google_monitor(st.session_state.api_key)
                                                                result = monitor.delete_store(store["store_id"], force=True)
                                                                if result.get("success"):
                                                                    st.success(f"✅ Store '{store['name']}' eliminato!")
                                                                    _invalidate_all_vector_stores()
                                                                else:
                                                                    st.error(f"❌ Errore: {result.get('error', 'Errore')}")
                                                                del st.session_state[confirm_key]
                                                                time.sleep(1)
                                                                st.rerun()
                                                            except Exception as e:
                                                                st.error(f"❌ Errore: {e}")
                                                with col_cancel:
                                                    if st.button("❌ Annulla", key=f"no_{confirm_key}"):
                                                        del st.session_state[confirm_key]
                                                        st.rerun()
                                                st.markdown("---")
                                            else:
                                                # Mostra riga normale con pulsante elimina
                                                col_name, col_files, col_size, col_action = st.columns([3, 1, 1, 2])
                                                with col_name:
                                                    st.write(f"📁 **{store['name']}**")
                                                    st.caption(f"ID: `{store['store_id'][:40]}...`")
                                                    if store['file_list']:
                                                        st.caption("File: " + ", ".join(store['file_list'][:3]))
                                                with col_files:
                                                    st.metric("File", store['file_count'])
                                                with col_size:
                                                    st.write(f"~{store['size_estimate_mb']} MB")
                                                with col_action:
                                                    store_key = f"del_other_{store_hash}"
                                                    if st.button("🗑️Elimina", key=store_key, help="Elimina store"):
                                                        st.session_state[confirm_key] = store
                                                        st.rerun()  # Forza rerun immediato per mostrare conferma
                                    else:
                                        st.info("Nessun altro store trovato")
                            else:
                                st.info("Nessun store trovato su Google Cloud")

                            # Pulsante refresh
                            if st.button("🔄 Aggiorna Lista Store"):
                                st.rerun()

                            # 🎉 File Explorer Section COMPLETO
                            st.markdown("### 🗂️ **File Explorer dei Store**")
                            st.info("🔍 **Esplora i contenuti dei singoli store** per ottimizzare lo spazio e gestire i file di Google Search")

                            # Selettore store per esplorazione migliorato
                            store_options = []
                            store_values = []

                            # Crea opzioni dettagliate per il dropdown
                            for s in all_stores["stores"]:
                                icon = "📖" if s["is_quadernino"] else "📁"
                                quadernino_info = " (Quadernino)" if s["is_quadernino"] else " (Altro Store)"
                                store_options.append(f"{icon} {s['name']} ({s['file_count']} file){quadernino_info}")
                                store_values.append(s["store_id"])

                            if store_options:
                                selected_store_idx = st.selectbox(
                                    "🔍 **Seleziona Store da Esplorare:**",
                                    range(len(store_options)),
                                    format_func=lambda x: store_options[x],
                                    help="Scegli uno store per vedere esattamente quali file contiene"
                                )

                                selected_store_id = store_values[selected_store_idx]
                                selected_store = all_stores["stores"][selected_store_idx]

                                # Mostra informazioni riassuntive dello store selezionato
                                st.markdown("---")
                                col_info1, col_info2, col_info3 = st.columns(3)
                                with col_info1:
                                    st.metric("📁 Tipo Store", "Quadernino" if selected_store["is_quadernino"] else "Altro")
                                with col_info2:
                                    st.metric("📄 File Totali", selected_store["file_count"])
                                with col_info3:
                                    st.metric("💾 Spazio Stimato", f"~{selected_store['size_estimate_mb']} MB")

                                # Pulsante principale per esplorazione con icona migliorata
                                col_explore, col_refresh = st.columns([3, 1])
                                with col_explore:
                                    explore_button = st.button(
                                        f"🔍 Esplora File in '{selected_store['name']}'",
                                        type="primary",
                                        use_container_width=True,
                                        help="Scansiona lo store e mostra tutti i file dettagliati"
                                    )
                                with col_refresh:
                                    if st.button("🔄", help="Aggiorna dati store"):
                                        st.rerun()

                                # Stato di esplorazione in sessione
                                session_key = f"explored_store_{selected_store_id}"

                                if explore_button or session_key in st.session_state:
                                    if explore_button:
                                        # Carica dati freschi
                                        with st.spinner(f"🔍 Analizzando file in '{selected_store['name']}'..."):
                                            files_details = monitor.get_store_files_detailed(selected_store_id)
                                            st.session_state[session_key] = files_details
                                    else:
                                        # Usa dati in cache
                                        files_details = st.session_state[session_key]

                                    if files_details.get("success"):
                                        # Header risultati
                                        st.success(f"✅ **{selected_store['name']}** - {files_details['total_files']} file trovati")

                                        # Statistiche file
                                        if files_details["files"]:
                                            # Calcola statistiche sui file
                                            file_types = {}
                                            total_size_est = 0
                                            for file_info in files_details["files"]:
                                                file_type = file_info.get('type', 'Unknown')
                                                file_types[file_type] = file_types.get(file_type, 0) + 1
                                                # Stima dimensione (1MB per file di default)
                                                total_size_est += 1024 * 1024

                                            # Mostra statistiche file
                                            col_stat1, col_stat2, col_stat3 = st.columns(3)
                                            with col_stat1:
                                                st.metric("📄 Documenti", len(files_details["files"]))
                                            with col_stat2:
                                                st.metric("🏷️ Tipi File", len(file_types))
                                            with col_stat3:
                                                size_mb = total_size_est // (1024 * 1024)
                                                st.metric("💾 Spazio Totale", f"~{size_mb} MB")

                                            st.markdown("#### 📋 **Dettaglio File Completo**")

                                            # Tabella migliorata con checkboxes per selezione
                                            st.info("📌 **Seleziona i file che vuoi gestire** (ricreazione indice disponibile)")

                                            selected_files = []
                                            for i, file_info in enumerate(files_details["files"]):
                                                # Checkbox per selezione file
                                                col_checkbox, col_name, col_type, col_size, col_status = st.columns([0.5, 4, 1.5, 1.5, 1])

                                                with col_checkbox:
                                                    file_key = f"select_file_{selected_store_id}_{i}"
                                                    is_selected = st.checkbox("", key=file_key, help="Seleziona per gestione")
                                                    if is_selected:
                                                        selected_files.append(file_info['name'])

                                                with col_name:
                                                    file_icon = "📄" if file_info['type'] == 'PDF' else "📝" if file_info['type'] == 'Text' else "📎"
                                                    st.write(f"{file_icon} **{file_info['name']}**")
                                                    if len(file_info['name']) > 30:
                                                        st.caption(file_info['name'])

                                                with col_type:
                                                    # Badge tipo file colorato
                                                    type_color = {
                                                        'PDF': '🔴',
                                                        'Word': '🔵',
                                                        'Text': '🟢',
                                                        'Markdown': '🟣'
                                                    }.get(file_info['type'], '⚪')
                                                    st.write(f"{type_color} {file_info['type']}")

                                                with col_size:
                                                    st.write(f"📏 {file_info['size_estimate']}")

                                                with col_status:
                                                    status_icon = "✅" if file_info.get('status') == 'active' else "⚠️"
                                                    st.write(f"{status_icon}")

                                            # Azioni sui file selezionati
                                            if selected_files:
                                                st.markdown("#### 🛠️ **Azioni su File Selezionati**")
                                                st.warning(f"⚠️ **{len(selected_files)} file selezionati** - Pronto per gestione avanzata")

                                                col_action1, col_action2, col_action3 = st.columns(3)
                                                with col_action1:
                                                    if st.button("🔄 Ricrea Indice SENZA questi File", type="secondary", use_container_width=True):
                                                        with st.spinner("🔄 Analisi e preparazione ricostruzione store..."):
                                                            # Usa la nuova funzione per ricreazione selettiva
                                                            recreate_result = monitor.recreate_store_without_files(
                                                                selected_store_id, selected_files
                                                            )

                                                            if recreate_result.get("success"):
                                                                st.success(f"✅ **Store ricostruito con successo!**")
                                                                st.json({
                                                                    "File Originali": recreate_result["original_files"],
                                                                    "File Mantenuti": recreate_result["kept_files"],
                                                                    "File Rimossi": recreate_result["removed_files"],
                                                                    "Nuovo Store ID": recreate_result["new_store_id"]
                                                                })

                                                                # Pulisci cache e aggiorna
                                                                if session_key in st.session_state:
                                                                    del st.session_state[session_key]
                                                                _invalidate_all_vector_stores()
                                                                time.sleep(2)
                                                                st.rerun()
                                                            else:
                                                                st.error(f"❌ **Errore nella ricostruzione:** {recreate_result.get('error', 'Errore sconosciuto')}")
                                                                st.info("💡 Per la rimozione completa di file, potresti dover ricaricare i documenti localmente")

                                                with col_action2:
                                                    if st.button("📥 Analisi Dettagliata", use_container_width=True):
                                                        with st.spinner("🔍 Analisi avanzata file..."):
                                                            analysis = monitor.get_file_analysis_summary(selected_store_id)
                                                            if analysis.get("success"):
                                                                st.success("✅ **Analisi completata**")

                                                                col_an1, col_an2, col_an3 = st.columns(3)
                                                                with col_an1:
                                                                    st.metric("📄 File Totali", analysis["total_files"])
                                                                with col_an2:
                                                                    st.metric("💾 Spazio Totale", f"~{analysis['total_size_estimate_mb']} MB")
                                                                with col_an3:
                                                                    st.metric("📏 Dim. Media", f"~{analysis['average_file_size_mb']} MB")

                                                                # Tipi file
                                                                if analysis["file_types"]:
                                                                    st.markdown("**🏷️ Distribuzione Tipi File:**")
                                                                    for file_type, count in analysis["file_types"].items():
                                                                        st.write(f"• {file_type}: {count} file")

                                                                # Suggerimenti
                                                                if analysis["recommendations"]:
                                                                    st.markdown("**💡 Suggerimenti:**")
                                                                    for rec in analysis["recommendations"]:
                                                                        st.write(f"• {rec}")
                                                            else:
                                                                st.error(f"❌ Errore analisi: {analysis.get('error', 'Errore')}")

                                                with col_action3:
                                                    if st.button("❌ Deseleziona Tutto", use_container_width=True):
                                                        for i in range(len(files_details["files"])):
                                                            file_key = f"select_file_{selected_store_id}_{i}"
                                                            if file_key in st.session_state:
                                                                st.session_state[file_key] = False
                                                        st.rerun()

                                                # Sezione ottimizzazione store
                                                st.markdown("#### 🎯 **Ottimizzazione Store**")
                                                with st.expander("🚀 Suggerimenti Automatici Ottimizzazione", expanded=False):
                                                    st.info("🤖 **Analisi intelligente** per ottimizzare lo spazio del tuo store")

                                                    if st.button("🔍 Analizza Ottimizzazioni", use_container_width=True):
                                                        with st.spinner("🧠 Calcolo suggerimenti ottimizzazione..."):
                                                            suggestions = monitor.optimize_store_suggestions(selected_store_id)

                                                            if suggestions.get("success") and suggestions["actions"]:
                                                                st.success(f"✅ **Trovate {len(suggestions['actions'])} ottimizzazioni**")

                                                                # Mostra potenziale risparmio
                                                                if suggestions["potential_savings"] > 0:
                                                                    st.info(f"💰 **Risparmio potenziale:** ~{suggestions['potential_savings']:.1f} MB")
                                                                    st.write(f"📉 **Dimensione stimata dopo ottimizzazione:** ~{suggestions['estimated_new_size']:.1f} MB")

                                                                # Lista azioni consigliate
                                                                for i, action in enumerate(suggestions["actions"]):
                                                                    priority = suggestions["priorities"][i]
                                                                    priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
                                                                    st.write(f"{priority_icon} **{action}**")

                                                            else:
                                                                st.info("ℹ️ **Nessuna ottimizzazione significativa suggerita**")
                                                                st.write("👍 Il tuo store sembra già ben ottimizzato!")

                                            # Dettagli tecnici espandibili
                                            with st.expander("🔧 Dettagli Tecnici e Debug API"):
                                                col_debug1, col_debug2 = st.columns(2)
                                                with col_debug1:
                                                    st.json({
                                                        "store_id": selected_store_id,
                                                        "store_name": files_details.get("store_name"),
                                                        "total_files": files_details.get("total_files"),
                                                        "api_file_count": files_details.get("file_count_from_api"),
                                                        "extracted_files": len(files_details.get("files", [])),
                                                        "success": files_details.get("success")
                                                    })
                                                with col_debug2:
                                                    st.json({
                                                        "is_quadernino": selected_store["is_quadernino"],
                                                        "created_time": selected_store.get("created_time", "unknown"),
                                                        "store_size_mb": selected_store.get("size_estimate_mb", 0),
                                                        "file_count_discrepancy": (
                                                            files_details.get("file_count_from_api", 0) -
                                                            len(files_details.get("files", []))
                                                        )
                                                    })

                                        else:
                                            st.info("📂 **Nessun file dettagliato disponibile** - Lo store potrebbe essere vuoto o i file non sono accessibili")
                                    else:
                                        st.error(f"❌ **Errore nell'esplorazione:** {files_details.get('error', 'Errore sconosciuto')}")

                                        # Opzione di retry
                                        if st.button("🔄 Riprova Esplorazione", type="secondary"):
                                            if session_key in st.session_state:
                                                del st.session_state[session_key]
                                            st.rerun()

                            else:
                                st.warning("🚫 **Nessun store disponibile per l'esplorazione**")

                            # Cleanup suggestions
                            cleanup_info = monitor.cleanup_old_stores()
                            if cleanup_info.get("count", 0) > 0:
                                st.markdown("### 🧽 **Cleanup Automatico**")
                                st.write(f"🗑️ **{cleanup_info['count']}** store non Quadernino trovati")
                                st.write(f"💰 Risparmio potenziale: **~{cleanup_info['potential_savings_mb']} MB**")

                                if st.button("🧽 Esegui Cleanup Automatico", type="secondary"):
                                    # Esegui cleanup automatico effettivo
                                    with st.spinner("🧹 Pulizia store non Quadernino in corso..."):
                                        deleted_count = 0
                                        errors = []

                                        all_stores = monitor.get_all_stores_detailed()
                                        non_quad_stores = [s for s in all_stores.get("stores", []) if not s["is_quadernino"]]

                                        for store in non_quad_stores:
                                            try:
                                                result = monitor.delete_store(store["store_id"], force=True)
                                                if result.get("success"):
                                                    deleted_count += 1
                                                    log_info(f"Store non quadernino eliminato: {store['name']}")
                                                else:
                                                    errors.append(f"{store['name']}: {result.get('error', 'Errore')}")
                                            except Exception as e:
                                                errors.append(f"{store['name']}: {str(e)}")

                                        # Mostra risultati
                                        if deleted_count > 0:
                                            st.success(f"✅ Eliminati {deleted_count} store non Quadernino!")
                                            if errors:
                                                st.warning(f"Attenzione: {len(errors)} errori durante il cleanup:")
                                                for error in errors[:5]:  # Mostra primi 5 errori
                                                    st.write(f"• {error}")
                                        else:
                                            st.error("❌ Nessuno store eliminato")
                                            if errors:
                                                st.error("Errori riscontrati:")
                                                for error in errors:
                                                    st.write(f"• {error}")

                                        # Invalida session store per forzare ricaricamento
                                        _invalidate_all_vector_stores()
                                        time.sleep(2)
                                        st.rerun()
                else:
                    st.warning("⚠️ Impossibile caricare le statistiche File Search")

                # Statistiche del modello corrente
                selected_model = st.session_state.get("selected_model", "")
                if selected_model:
                    usage_info = monitor.get_usage_estimate(selected_model)

                    if usage_info and "memory" in usage_info:
                        st.markdown("### 📈 Utilizzo Modello Corrente")

                        # Progress bar memoria
                        memory_pct = usage_info["memory"]["percentage"]
                        memory_color = "green" if memory_pct < 50 else "orange" if memory_pct < 80 else "red"

                        st.markdown(f"""
                        <div style="margin: 10px 0;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                <span>💾 Occupazione Memoria</span>
                                <span>{memory_pct}%</span>
                            </div>
                            <div style="background: #ddd; border-radius: 5px; height: 20px; overflow: hidden;">
                                <div style="background: {memory_color}; height: 100%; width: {memory_pct}%; transition: width 0.3s;"></div>
                            </div>
                            <small>{usage_info["memory"]["used_mb"]} MB / ~{usage_info["memory"]["limit_mb"]} MB</small>
                        </div>
                        """, unsafe_allow_html=True)

                        # Limiti API
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("🚀 Limite Richieste/min", usage_info["api_limits"]["rpm_limit"])
                        with col_b:
                            st.metric("📝 Limite Token/min", f"{usage_info['api_limits']['tpm_limit']:,}")

                        # Costi stimati
                        st.caption(f"💰 **Costo mensile stimato:** ${usage_info['costs']['estimated_monthly_cost']}")

                        # Health status
                        health = usage_info.get("health_status", {})
                        health_level = health.get("level", "good")

                        if health_level == "good":
                            st.success("✅ Sistema in buone condizioni")
                        elif health_level == "warning":
                            st.warning("⚠️ Attenzione: alcuni limiti sono vicini")
                            for issue in health.get("issues", []):
                                st.write(f"• {issue}")
                            for rec in health.get("recommendations", []):
                                st.info(f"💡 {rec}")
                        elif health_level == "critical":
                            st.error("🚨 AZIONE RICHIESTA: Limiti quasi raggiunti")
                            for issue in health.get("issues", []):
                                st.write(f"• {issue}")
                            for rec in health.get("recommendations", []):
                                st.info(f"⚡ {rec}")

            except Exception as e:
                st.error(f"❌ Errore caricamento dashboard: {e}")
                st.info("Riprova più tardi o controlla la connessione API")
else:
    st.info("🔑 Configura una API Key per vedere il monitoraggio")

st.divider()

# --- 🗑️ Conferme Eliminazione Store (Sistema Inline - Rimosso il sistema in fondo) ---
# Le conferme ora appaiono direttamente sotto ogni store per una UX più intuitiva

# Nota: La pulizia della chat è disponibile nella pagina 💬 Chat

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9em;'>
    <p>💡 Le tue impostazioni vengono salvate nel file <code>.env</code></p>
    <p>🔒 La tua API Key è conservata localmente.</p>
</div>
""", unsafe_allow_html=True)
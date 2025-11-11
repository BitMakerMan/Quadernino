import streamlit as st
from utils.gemini_handler import GeminiHandler
from utils import file_manager
from utils.env_manager import load_notebooks, get_active_notebook, set_active_notebook, \
    find_existing_store_for_notebook, update_notebook_store_name
from pathlib import Path
import time

st.set_page_config(page_title="Chat - Quadernino", page_icon="💬", layout="wide")

st.title("💬 Quadernino Chat")
st.caption("Modalità: File Search di Google (Vector Store)")

if not st.session_state.get("api_key"):
    st.warning("⚠️ Per favore, configura prima la tua Google API Key nella pagina Impostazioni.")
    st.stop()

notebooks = load_notebooks()
active_notebook = get_active_notebook()

if not notebooks:
    st.info(
        "👋 Ciao! Non hai ancora creato nessun quadernino. Vai alla pagina '📁 Gestione Quadernini' per creare il tuo primo quadernino.")
    st.stop()

if not active_notebook:
    st.warning("⚠️ Nessun quadernino attivo. Seleziona o crea un quadernino nella pagina '📁 Gestione Quadernini'.")
    st.stop()

try:
    selected_model = st.session_state.get("selected_model")
    if not selected_model:
        st.error("⚠️ Nessun modello selezionato. Vai nelle Impostazioni per scegliere un modello.")
        st.stop()
    gemini = GeminiHandler(api_key=st.session_state.api_key, model_name=selected_model)
except Exception as e:
    st.error(f"Errore inizializzazione Gemini: {e}")
    st.stop()

st.subheader("📚 Seleziona Quadernino")
st.success(f"📖 **Quadernino Attivo:** {active_notebook.get('name', 'N/D')}")
if active_notebook.get('description'):
    st.caption(active_notebook['description'])

notebook_names = [nb['name'] for nb in notebooks]
selected_notebook_name = st.selectbox(
    "Cambia quadernino:",
    options=notebook_names,
    index=notebook_names.index(active_notebook['name']) if active_notebook['name'] in notebook_names else 0,
    help="Seleziona un quadernino per chattare con i suoi documenti specifici"
)

if selected_notebook_name != active_notebook['name']:
    set_active_notebook(selected_notebook_name)
    st.rerun()

st.markdown("---")

from utils.env_manager import get_notebook_files

notebook_files = get_notebook_files(active_notebook['name'])

local_files = file_manager.list_local_files()
notebook_file_paths = [f for f in local_files if Path(f).name in notebook_files]

if not notebook_file_paths:
    st.info(
        f"📄 Nessun documento nel quadernino '{active_notebook['name']}'. Vai alla pagina '📁 Gestione Quadernini' per aggiungere file.")
    st.stop()

notebook_key = f"vector_store_{active_notebook['name']}"
saved_store_name = active_notebook.get('store_name', '')
active_store_name = st.session_state.get(notebook_key) or saved_store_name

if not active_store_name:
    existing_store = find_existing_store_for_notebook(active_notebook['name'], st.session_state.api_key)
    if existing_store:
        st.info(f"🔄 Trovato store esistente per '{active_notebook['name']}'. Riutilizzo...")
        active_store_name = existing_store
        st.session_state[notebook_key] = existing_store
        update_notebook_store_name(active_notebook['name'], existing_store)

# --- INIZIO CODICE MIGLIORATO (Rimozione Auto-Indicizzazione) ---
# Se, dopo tutti i controlli, non c'è uno store, fermati e avvisa l'utente.
if not active_store_name:
    st.warning(f"⚠️ Il quadernino '{active_notebook['name']}' non è indicizzato.")
    st.info(
        "Vai alla pagina '📁 Gestione Quadernini' e clicca su '🔍 Indicizza' per attivare la chat."
    )
    st.stop()
else:
    # Mostra successo solo se lo store è confermato
    st.success(f"✅ Store per '{active_notebook['name']}' pronto!", icon="🔄")
# --- FINE CODICE MIGLIORATO ---


with st.sidebar:
    st.subheader("📄 Stato Quadernino")
    st.write(f"Quadernino attivo: **{active_notebook['name']}**")
    st.write(f"File nel quadernino: **{len(notebook_files)}**")

    if active_store_name:
        try:
            context_info = gemini.get_context_info(active_store_name)
            if context_info.get("has_context"):
                st.success("🌐 **Indice ATTIVO**", icon="🔍")
                st.write(f"File indicizzati: **{context_info.get('file_count', 'N/D')}**")
            else:
                st.warning("Indice trovato ma vuoto.", icon="⚠️")
        except Exception as e:
            st.warning(f"Errore recupero info store: {e}", icon="⚠️")

        store_info = gemini.get_file_search_store(active_store_name)
        if store_info and isinstance(store_info, dict) and store_info.get("permission_error"):
            st.error(f"""
            🔑 **Errore di Permesso**
            L'indice '{active_store_name}' non è accessibile.
            **Soluzione:** Vai in '📁 Gestione Quadernini', seleziona '{active_notebook['name']}'
            e clicca '🔄 Rigenera Indice'.
            """, icon="🚫")
    else:
        st.warning("Indice non attivo.", icon="⚠️")

    st.markdown("---")
    if notebook_files:
        st.caption(f"File in '{active_notebook['name']}':")
        for file_name in notebook_files:
            st.write(f"• {file_name}")

col1, col2 = st.columns([1, 3])
with col1:
    if st.button("🗑️ Pulisci Chat", help="Cancella tutta la cronologia della chat", type="secondary"):
        st.session_state.chat_history = []
        st.rerun()
with col2:
    chat_count = len(st.session_state.chat_history) if "chat_history" in st.session_state else 0
    st.metric("💬 Messaggi", chat_count)

st.markdown("---")

# Inizializza chat_history se non esiste
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Fai una domanda ai tuoi documenti..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()

        # --- INIZIO CODICE MIGLIORATO (Spinner Immediato) ---
        # Mostra spinner MENTRE l'API lavora (chiamata bloccante)
        with st.spinner("🧠 Quadernino sta pensando..."):
            stream_generator = gemini.generate_response_stream(
                prompt=prompt,
                history=st.session_state.chat_history[:-1],
                vector_store_name=active_store_name
            )

        # Ora che la chiamata è finita, esegui la simulazione di streaming
        full_response = ""
        for chunk in stream_generator:
            full_response += chunk
            response_placeholder.markdown(full_response + "▌")

        response_placeholder.markdown(full_response)
        # --- FINE CODICE MIGLIORATO ---

    st.session_state.chat_history.append({"role": "assistant", "content": full_response})
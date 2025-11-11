import streamlit as st
import os
from dotenv import load_dotenv
from google import genai

# --- Configurazione Pagina (DEVE ESSERE LA PRIMA ISTRUZIONE STREAMLIT) ---
st.set_page_config(
    page_title="Quadernino",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --- Inizializzazione ---
def init_app():
    """Inizializza lo stato dell'applicazione e carica le configurazioni."""
    load_dotenv()
    if "api_key" not in st.session_state:
        st.session_state.api_key = os.getenv("GOOGLE_API_KEY", "")
    # Usa il modello salvato nel .env
    default_model = os.getenv("DEFAULT_MODEL", "")
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = default_model

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Crea cartella upload se manca
    os.makedirs("uploaded_files", exist_ok=True)


init_app()

# --- Interfaccia Home ---
# Header con logo e titolo
col1, col2 = st.columns([1, 3])
with col1:
    st.markdown("# 📒")
with col2:
    st.title("Quadernino")
    st.caption("Il Tuo Assistente di Studio Intelligente")
    st.markdown("**Autore:** Craicek | **Licenza:** MIT")

st.markdown("---")

# Informazioni sull'autore e progetto
with st.container(border=True):
    st.subheader("👨‍💻 Informazioni sul Progetto")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        **Autore:** Craicek
        **Repository:** [GitHub - BitMakerMan/Quadernino](https://github.com/BitMakerMan/Quadernino)
        **Licenza:** MIT License

        Quadernino è un'applicazione educativa progettata per aiutare gli studenti a studiare in modo mirato e senza distrazioni.
        """)

    with col2:
        if st.link_button("⭐ Visita GitHub", "https://github.com/BitMakerMan/Quadernino", use_container_width=True):
            st.success("Grazie per il supporto!")

st.markdown("---")

# Come funziona Quadernino
with st.container(border=True):
    st.subheader("🎯 Come Funziona Quadernino")

    st.markdown("""
    ### 📚 **Filosofia Educativa**
    Quadernino nasce per fornire supporto scolastico mirato, permettendo agli studenti di:
    - **Studiare senza distrazioni**: L'AI risponde solo usando i documenti caricati
    - **Organizzare i materiali**: Sistema a quadernini come un vero quaderno scolastico
    - **Prepararsi per verifiche**: Supporto mirato per ogni materia

    ### 🔄 **Flusso di Lavoro**
    1. **Crea Quadernini** → Organizza le materie per argomenti (es. "Storia Romana", "Fisica Quantistica")
    2. **Carica Documenti** → Aggiungi PDF, DOCX, TXT, MD ai quadernini corrispondenti
    3. **Indicizza Manualmente** → Crea l'indice di ricerca per ogni quadernino
    4. **Chatta Mirato** → Fai domande usando solo i documenti del quadernino selezionato

    ### 🚀 **Potenzialità**
    - **Studio Focalizzato**: Niente distrazioni da conversazioni generiche dell'AI
    - **Sistema Scolastico**: Organizzazione intuitiva come quaderni di classe
    - **Supporto Multiformato**: PDF, testi, documenti Word, Markdown
    - **Ricerca Veloce**: Indicizzazione avanzata con Google Gemini File Search
    - **Gestione Personale**: Ogni studente ha i propri capitoli e materiali
    """)

st.markdown("---")

# Stato Corrente
st.header("📋 Stato del Tuo Quadernino")

# Importiamo le funzioni per gestire i quadernini
try:
    from utils.env_manager import get_active_notebook, load_notebooks
    notebooks = load_notebooks()
    active_notebook = get_active_notebook()

    if notebooks:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("📚 Quadernini", len(notebooks))

        with col2:
            active_name = active_notebook.get('name', 'Nessuno')
            st.metric("📖 Attivo", active_name[:15] + '...' if len(active_name) > 15 else active_name)

        with col3:
            total_files = sum(nb.get('file_count', 0) for nb in notebooks)
            st.metric("📄 Documenti", total_files)

        with col4:
            indexed_notebooks = sum(1 for nb in notebooks if nb.get('store_name'))
            st.metric("🔍 Indicizzati", indexed_notebooks)

        st.markdown("---")

        st.subheader("📚 I Tuoi Quadernini")
        for notebook in notebooks:
            is_active = notebook["name"] == active_notebook.get("name", "")
            is_indexed = bool(notebook.get('store_name'))

            col_nb, col_status = st.columns([4, 1])
            with col_nb:
                if is_active:
                    st.success(f"✅ **{notebook['name']}** - *{notebook.get('description', 'Nessuna descrizione')}*")
                else:
                    st.write(f"📖 **{notebook['name']}** - *{notebook.get('description', 'Nessuna descrizione')}*")

            with col_status:
                if is_indexed:
                    st.success("🔍")
                else:
                    st.warning("⏳")
    else:
        st.info("👋 **Benvenuto in Quadernino!** Inizia creando il tuo primo quadernino per organizzare i tuoi materiali di studio.")

except Exception as e:
    st.error(f"Errore nel caricare i dati dei quadernini: {e}")
    st.info("Vai su ⚙️ Impostazioni per configurare l'applicazione")

st.markdown("---")

# Azioni Rapide
st.subheader("🚀 Azioni Rapide")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📁 Gestione Quadernini")
    st.caption("Crea quadernini, carica documenti, indicizza i materiali")
    if st.button("📁 Vai a Gestione Quadernini", type="primary", use_container_width=True):
        st.switch_page("pages/1_📁_Gestione_Quadernini.py")

with col2:
    st.markdown("### 💬 Chat con i Documenti")
    st.caption("Fai domande usando solo i tuoi documenti indicizzati")
    if st.button("💬 Vai alla Chat", type="primary", use_container_width=True):
        st.switch_page("pages/2_💬_Chat.py")

st.markdown("---")

# Note tecniche (rimosso debug visibile)
with st.expander("📖 Informazioni Tecniche", expanded=False):
    st.markdown("""
    **Tecnologia Utilizzata:**
    - Google Gemini File Search API
    - Vector Store per indicizzazione efficiente
    - Streamlit per l'interfaccia web
    - Architettura multi-capitolo
    """)

# Footer informativo
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <strong>Quadernino</strong> - Supporto scolastico intelligente per studenti<br>
    Sviluppato con ❤️ utilizzando <strong>Google Gemini File Search API</strong><br>
    © 2025 Craicek - <a href="https://github.com/BitMakerMan/Quadernino" target="_blank">GitHub</a> - Licenza MIT
</div>
""", unsafe_allow_html=True)

# Footer nella sidebar
with st.sidebar:
    st.markdown("---")
    st.markdown("**👨‍💻 Sviluppato da:** Craicek")
    if st.session_state.api_key:
        st.success("🔑 API Key configurata")
    else:
        st.warning("⚠️ Configura API Key")
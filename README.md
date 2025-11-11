# 📒 Quadernino

**Autore:** Craicek | **Licenza:** MIT | **Repository:** [GitHub](https://github.com/BitMakerMan/Quadernino)

[![Licenza: MIT](https://img.shields.io/badge/Licenza-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Framework: Streamlit](https://img.shields.io/badge/Framework-Streamlit-red.svg)](https://streamlit.io)
[![Tecnologia: Google Gemini](https://img.shields.io/badge/Tecnologia-Google_Gemini-purple.svg)](https://ai.google.com/gemini/)

---

**Quadernino** è un assistente di studio personale e intelligente, costruito interamente sulla piattaforma **Google Gemini**. È progettato per lo studio focalizzato, permettendo agli studenti e ai professionisti di creare "Quadernini" tematici (come materie scolastiche o progetti) e di chattare esclusivamente con i documenti caricati in essi.

La sua filosofia è semplice: **studiare senza distrazioni**. L'AI risponde solo utilizzando i materiali forniti, eliminando la possibilità di risposte generiche o non pertinenti.

Ma Quadernino è più di una semplice chat RAG (Retrieval-Augmented Generation). Grazie alla sua integrazione nativa con l'API **Google File Search**, agisce come un potente **manager di indici vettoriali (Store)**, offrendo un pannello di controllo completo per monitorare costi, utilizzo e contenuti dei tuoi indici su Google Cloud.

## 🚀 Funzionalità Principali

* **🧠 Gestione a Quadernini:** Crea Quadernini isolati per ogni materia o progetto (es. "Storia Romana", "Fisica Quantistica", "Appunti Progetto X").
* **📚 RAG Potente (Server-Side):** Sfrutta l'API Google File Search. L'analisi di PDF, DOCX, TXT e la loro indicizzazione (parsing, chunking, embedding) avvengono interamente sui server di Google, garantendo massima efficienza.
* **💬 Chat Mirata:** Chatta solo con i documenti del Quadernino attivo, con la certezza che le risposte provengano esclusivamente da quel contesto.
* **📊 Dashboard Amministrativa (Il cuore di Quadernino):**
    * Monitora tutti i File Search Store sul tuo account Google.
    * Distingui tra store creati da Quadernino e "Altri".
    * Analizza costi, utilizzo API, numero di file e spazio occupato.
    * **Esplora i file** indicizzati all'interno di uno store.
    * Gestisci e **pulisci** gli store obsoleti direttamente dall'interfaccia.
* **🔄 Auto-Ripristino Intelligente:** Se perdi il file `.env` locale, Quadernino può scansionare il tuo account Google alla prima configurazione e "ripristinare" i Quadernini esistenti.
* **🔐 Persistenza Sicura:** Lo stato dell'applicazione è salvato localmente in un file `.env`, gestito in modo **Thread-Safe** (tramite `FileLock`) per prevenire conflitti.

## 🛠️ Stack Tecnologico

Quadernino adotta un approccio "Tutto Google" per il backend, delegando il lavoro pesante all'infrastruttura Google Cloud:

* **Interfaccia Utente:** [Streamlit](https://streamlit.io)
* **Modello LLM:** [Google Gemini (es. 2.5-Pro / 2.5-Flash)](https://ai.google.com/gemini/)
* **Backend RAG / Vector Store:** [**Google File Search API**](https://ai.google.dev/docs/file_search) (Nessun database vettoriale locale, tutto gestito server-side da Google).
* **Persistenza Stato:** File `.env` locale.

## 📖 Documentazione

Per iniziare, consulta le nostre guide dettagliate:

* **[Guida all'Installazione (INSTALL.md)](./docs/INSTALL.md)**: Come installare e avviare Quadernino.
* **[Guida all'Utilizzo (GUIDA.md)](./docs/GUIDA.md)**: Come usare i menu dell'applicazione.
* **[Architettura e Gestione Store (ARCHITETTURA.md)](./docs/ARCHITETTURA.md)**: Una spiegazione tecnica di come funziona Quadernino e della sua potente dashboard di gestione.

## 💡 Idee di Utilizzo

* **Studenti:** Crea un Quadernino per ogni materia, carica appunti, slide e PDF, e usalo per ripassare e preparare gli esami.
* **Professionisti:** Usa Quadernino per gestire la documentazione di diversi progetti. Carica specifiche, report e contratti per trovare rapidamente le informazioni.
* **Sviluppatori:** Usa Quadernino come **interfaccia di amministrazione** per i tuoi File Search Store su Google Cloud. Sfrutta la sua dashboard per monitorare e pulire gli indici usati da altre applicazioni.

## 👨‍💻 Autore

Sviluppato con ❤️ da **Craicek**.

[https://github.com/BitMakerMan/Quadernino](https://github.com/BitMakerMan/Quadernino)

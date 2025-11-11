# 📒 Architettura e Gestione Store

Questa pagina descrive l'architettura tecnica di Quadernino, con un focus sulla sua funzione più potente: la gestione degli indici (Store) di Google.

## L'architettura "Tutto Google"

Quadernino è progettato per essere leggero localmente e potente nel cloud. Invece di eseguire complesse operazioni di embedding o di gestire database vettoriali locali (come ChromaDB o FAISS), delega l'intero processo RAG (Retrieval-Augmented Generation) ai server di Google.

* **Nessun Parsing Locale:** Quando carichi un PDF, `file_manager.py` lo salva. Non lo legge.
* **Nessun Embedding Locale:** Il tuo PC non usa la CPU/GPU per creare vettori.
* **Nessun DB Vettoriale Locale:** Non c'è un database che occupa spazio su disco.

Quando clicchi "Indicizza" in `Gestione Quadernini`, l'app (tramite `gemini_handler.py`) dice a Google: "Prendi questi file, analizzali, crea un indice vettoriale (File Search Store) e dammi solo l'ID".

Questo ID è tutto ciò che Quadernino memorizza localmente (nel file `.env`).

## La Persistenza: `env_manager.py`

Lo stato dell'applicazione (l'elenco dei tuoi Quadernini e i loro ID) è salvato come una stringa JSON dentro il file `.env`:

```ini
QUADERNINI=[{"name": "Storia Romana", "store_name": "fileSearchStores/abcd-1234", ...}]
ACTIVE_NOTEBOOK=Storia Romana
````

Questa scelta rende l'app "serverless" e facile da gestire. Per prevenire errori di scrittura concorrente (comuni in app Streamlit), `env_manager.py` utilizza `FileLock` per assicurare che ogni scrittura sul file `.env` sia atomica e sicura (Thread-Safe).

### Auto-Ripristino

La funzione `auto_restore_on_first_setup` è un meccanismo di resilienza. Se il tuo `.env` viene cancellato, ma la tua API key rimane la stessa, l'app scansiona il tuo progetto Google Cloud. Se trova store con nomi "Quadernino - ...", li re-importa automaticamente nel `.env`.

## 📊 La Dashboard: Il Gestore di Store

La pagina `⚙️ Impostazioni` contiene una dashboard di amministrazione avanzata (basata su `google_monitor.py`). Questa dashboard trasforma Quadernino da semplice app di chat a un **manager completo per l'API Google File Search**.

### Monitoraggio

La dashboard elenca **tutti** i File Search Store presenti sul tuo account Google, non solo quelli creati da Quadernino.

  * **🗃️ Quadernini:** Store che Quadernino riconosce e gestisce.
  * **📁 Altri Store:** Store "orfani" o creati da altre applicazioni.

Per ogni store, vedi il numero di file indicizzati e lo spazio stimato.

### Gestione e Pulizia

Puoi eliminare in sicurezza qualsiasi store direttamente dall'interfaccia. L'app richiede una conferma (inline) per prevenire errori. Se elimini un Quadernino, l'app aggiorna anche il `.env` per rimuovere l'associazione.

È presente anche un pulsante "Cleanup Automatico" per eliminare in blocco tutti gli store "Altri" (non Quadernino).

### 🔍 Esplorazione File (Funzione Avanzata)

Questa è la funzione più potente della dashboard. Puoi:

1.  Selezionare uno store dall'elenco.
2.  Cliccare "Esplora File".
3.  L'app contatta Google e ottiene l'elenco di **tutti i singoli file** indicizzati in quello store.

Questo ti permette di vedere *esattamente* cosa c'è dentro un indice.

### Ottimizzazione Store

L'esploratore di file ti permette anche azioni complesse. Ad esempio, puoi selezionare 5 file su 100 e cliccare su **"Ricrea Indice SENZA questi File"**.

Questa funzione (implementata in `google_monitor.recreate_store_without_files`) è complessa:

1.  Recupera i file da mantenere.
2.  Crea un *nuovo* store temporaneo.
3.  (Richiede implementazione complessa) Ri-carica i file da mantenere nel nuovo store.
4.  Elimina il vecchio store.
5.  Aggiorna il `.env` con l'ID del nuovo store.

Questa sezione di "Ottimizzazione" e "Analisi" fornisce una panoramica completa sui costi, l'utilizzo e la salute dei tuoi indici, rendendo Quadernino uno strumento indispensabile per chiunque utilizzi l'API Google File Search in modo intensivo.

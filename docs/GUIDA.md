Ecco il contenuto grezzo in formato Markdown per il file `docs/GUIDA.md`.

```text
# 📒 Guida all'Utilizzo di Quadernino

Quadernino è diviso in tre sezioni principali, accessibili dalla barra laterale.

## 🏠 1. Home

È la pagina di benvenuto e la tua dashboard principale.

* **Informazioni sul Progetto:** Dettagli sull'autore e sulla filosofia educativa dell'app.
* **Come Funziona:** Una spiegazione del flusso di lavoro: Crea Quadernini -> Carica Documenti -> Indicizza -> Chatta.
* **Stato del Tuo Quadernino:** Un riepilogo metrico di quanti Quadernini hai, quale è attivo, il numero totale di documenti e quanti sono indicizzati.
* **Azioni Rapide:** Link veloci per andare alla Gestione Quadernini o alla Chat.

## 📁 2. Gestione Quadernini (Pagina non fornita, flusso presunto)

Questa è la pagina operativa dove costruisci la tua conoscenza.

1.  **Crea Quadernino:** Inserisci un nome (es. "Storia Romana") e una descrizione. Questo crea una voce nell'app.
2.  **Carica Documenti:** Seleziona un Quadernino e carica i tuoi file (PDF, DOCX, TXT, MD). I file vengono salvati localmente nella cartella `uploaded_files`.
3.  **Indicizza Quadernino (Azione Chiave):** Dopo aver caricato i file, clicca su "Indicizza". Questo processo:
    * Prende tutti i file locali associati a quel Quadernino.
    * Li carica sui server di Google.
    * Crea un **File Search Store** (un indice vettoriale) dedicato.
    * Salva l'ID di questo store (es. `fileSearchStores/...`) nel tuo file `.env`, associandolo al nome "Storia Romana".

## 💬 2. Chat

Questa è la pagina dove interagisci con l'IA.

1.  **Seleziona Quadernino:** In alto, troverai un menu a tendina. Seleziona il Quadernino con cui vuoi parlare (es. "Storia Romana").
2.  **Chatta:** Fai le tue domande. L'applicazione:
    * Recupera l'ID dello store associato (es. `fileSearchStores/abcd-1234`).
    * Invia la tua domanda a Gemini, **istruendolo** a usare *solo* quello store per trovare la risposta.
3.  **Pulizia Chat:** Un pulsante per cancellare la cronologia della conversazione corrente.

## ⚙️ 3. Impostazioni

Questo è il "pannello di controllo" del tuo Quadernino.

* **Google API Key:** Gestisci (inserisci, aggiorna, rimuovi) la tua API key.
* **Modello Gemini:** Seleziona quale modello usare (es. Flash per velocità, Pro per potenza). Il cambio di modello invalida la cache per garantire la coerenza.
* **Test e Diagnostica:** Testa la tua connessione API e visualizza le info di sistema.
* **Dashboard Google Cloud:** Il cuore della gestione. Vedi [Architettura e Gestione Store](./ARCHITETTURA.md) per i dettagli completi su questa sezione avanzata.
```

# 📒 Guida all'Installazione di Quadernino

Segui questi passaggi per installare e avviare Quadernino sul tuo computer locale.

## 1. Prerequisiti

* **Python 3.9** o superiore.
* Un account Google e una **API Key** per Google AI Studio (Gemini).

## 2. Installazione

Consiglio di usare lo script di installazione fornito, che automatizza la creazione dell'ambiente virtuale e l'installazione delle dipendenze.

**Passo 1: Clona il Repository**
```bash
git clone [https://github.com/BitMakerMan/Quadernino.git](https://github.com/BitMakerMan/Quadernino.git)
cd Quadernino
```

Passo 2: Esegui lo script di installazione
Lo script rileva automaticamente il tuo sistema operativo.
```bash
 * Su Linux/macOS:
   python3 install.py

 * Su Windows:
   python install.py
```
Cosa fa lo script install.py:
 * Controlla la tua versione di Python.
 * Crea un ambiente virtuale (es. .venv).
 * Installa tutte le dipendenze da requirements.txt.
 * Crea un file .env vuoto, pronto per essere configurato dall'applicazione.
3. Avvio e Configurazione API
A differenza di altre app, non devi modificare il file .env a mano. La configurazione avviene direttamente dall'interfaccia.
Passo 1: Avvia l'Applicazione
Usa il comando mostrato alla fine dell'installazione per avviare il server Streamlit:
 * Su Linux/macOS:
   ```bash
   .venv/bin/streamlit run Home.py
   ```

 * Su Windows:
   ```bash
   .venv\Scripts\streamlit.exe run Home.py
   ```

Passo 2: Configura dall'App
Apri il link http://localhost:8501 nel tuo browser.
Naviga alla pagina ⚙️ Impostazioni dalla barra laterale.
Troverai un campo per inserire la tua Google API Key.
Incolla la tua chiave e clicca su "💾 Salva API Key".
Nota: Inserendo la chiave tramite l'applicazione, attiverai la funzione di auto-ripristino. L'app cercherà automaticamente i "Quadernini" (File Search Store) già esistenti sul tuo account Google e li importerà, allineando subito il tuo stato sul cloud.

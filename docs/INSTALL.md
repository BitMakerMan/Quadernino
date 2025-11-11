# 📒 Guida all'Installazione di Quadernino

Segui questi passaggi per installare e avviare Quadernino sul tuo computer locale.

## 1\. Prerequisiti

  * **Python 3.9** o superiore.
  * Un account Google e una **API Key** per Google AI Studio (Gemini).

## 2\. Installazione

Consigliamo di usare lo script di installazione fornito, che automatizza la creazione dell'ambiente virtuale e l'installazione delle dipendenze.

**Passo 1: Clona il Repository**

```bash
git clone https://github.com/BitMakerMan/Quadernino.git
cd Quadernino
```

**Passo 2: Esegui lo script di installazione**
Lo script rileva automaticamente il tuo sistema operativo.

  * Su **Linux/macOS**:
    ```bash
    python3 install.py
    ```
  * Su **Windows**:
    ```bash
    python install.py
    ```

Cosa fa lo script `install.py`:

1.  Controlla la tua versione di Python.
2.  Crea un ambiente virtuale (es. `.venv`).
3.  Attiva l'ambiente e installa tutte le dipendenze da `requirements.txt`.
4.  Crea un file `.env` pre-configurato.

**Passo 3: Configura la tua API Key**
Apri il file `.env` che è stato creato nella cartella principale del progetto.

```ini
# Quadernino - File di configurazione
# Inserisci qui la tua Google API Key
GOOGLE_API_KEY=

# Modello predefinito
DEFAULT_MODEL=models/gemini-2.5-flash

# ... (altre variabili generate automaticamente)
```

Incolla la tua `GOOGLE_API_KEY` dopo l'uguale (`=`). Salva e chiudi il file.

> **Nota:** Se hai già degli store "Quadernino" sul tuo account Google, l'app tenterà di ripristinarli automaticamente al primo avvio.

## 3\. Avvio dell'Applicazione

Dopo aver configurato l'API Key, puoi avviare l'applicazione. Lo script di installazione ti avrà mostrato il comando esatto.

  * Su **Linux/macOS**:
    ```bash
    .venv/bin/streamlit run Home.py
    ```
  * Su **Windows**:
    ```bash
    .venv\Scripts\streamlit.exe run Home.py
    ```

Apri il link `http://localhost:8501` nel tuo browser per iniziare a usare Quadernino.

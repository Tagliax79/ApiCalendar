# ApiCalendar - Serie TV Recommendations App

Un'applicazione web che consiglia serie TV basate sui gusti personali dell'utente utilizzando l'API OpenAI per generare suggerimenti personalizzati.

## Funzionalità

- Gestione delle serie TV già viste
- Categorizzazione delle serie TV
- Generazione di consigli personalizzati basati sui gusti dell'utente
- Verifica della disponibilità delle serie consigliate su Netflix Italia
- Interfaccia responsive per dispositivi mobili e desktop

## Tecnologie Utilizzate

- **Backend**: Flask, SQLAlchemy
- **Database**: SQLite (sviluppo locale), PostgreSQL (in produzione su Render)
- **API**: OpenAI API (GPT-4o)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Web Scraping**: BeautifulSoup4, Trafilatura

## Installazione e Utilizzo Locale

### Prerequisiti

- Python 3.11 o superiore
- Chiave API OpenAI (opzionale, può essere inserita anche nell'interfaccia web)

### Installazione

1. Clona il repository:
   ```bash
   git clone https://github.com/Tagliax79/ApiCalendar.git
   cd ApiCalendar
   ```

2. Crea e attiva un ambiente virtuale:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Per Linux/Mac
   venv\Scripts\activate  # Per Windows
   ```

3. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```

4. Configura le variabili d'ambiente:
   Crea un file `.env` nella directory principale con i seguenti contenuti:
   ```
   FLASK_SECRET_KEY=una_chiave_segreta_sicura
   OPENAI_API_KEY=la_tua_api_key  # Opzionale, può essere inserita via UI
   ```

5. Inizializza il database e importa le serie TV di esempio:
   ```bash
   python import_watched_shows.py
   ```

6. Avvia l'applicazione:
   ```bash
   python app.py
   ```

7. Apri un browser e visita `http://localhost:5000`

## Deployment su Render

Questa applicazione è pronta per essere deployata su Render:

1. Crea un nuovo Web Service su Render
2. Collega il tuo repository GitHub
3. Seleziona il branch principale
4. Configura il servizio:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Environment Variables**: 
     - `FLASK_SECRET_KEY`: una chiave segreta sicura
     - `OPENAI_API_KEY`: la tua API key OpenAI (opzionale)
     - `DATABASE_URL`: aggiunto automaticamente da Render se utilizzi un database PostgreSQL
     - `PYTHON_VERSION`: 3.11

## Licenza

MIT License
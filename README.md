# GestPTF - Gestione Portafoglio

Applicazione web per la gestione e il monitoraggio del patrimonio personale, sviluppata in Python/Flask con SQLite.

## Funzionalità

### Panoramica
- **Dashboard** interattiva con allocazione patrimoniale, evoluzione storica (stacked area), slider sconto immobili separati (esteri/italia), click su grafico per aggiornare la torta, toggle variazione % (vs precedente / vs inizio)
- **Patrimonio** con storico completo, variazione % tra record, valori live automatici da BFP/FP/TFR/Fineco, integrazione VRP

### Investimenti
- **ETF** - gestione posizioni con import da Fineco, stato attivo/venduto
- **Obbligazioni / BTP** - gestione bond con import Fineco, mapping ISIN automatico (emissione -> mercato), stato attivo/venduto
- **BFP (Buoni Fruttiferi Postali)** - calcolo automatico valori rimborso/scadenza con coefficienti importati da PDF, dropdown prodotti, rendita BSF/BO65 con calcolo al 65° anno, ricalcolo automatico alla data odierna
- **Immobili** - gestione immobili esteri e italia con storico valutazioni e grafico andamento

### Previdenza e Liquidità
- **Fondo Pensione** - storico valori con grafico andamento
- **TFR** - storico con variazioni
- **Liquidità** - gestione cash con storico dal patrimonio
- **Debiti** - gestione debiti con progress bar

### Simulatori
- **Simulatore BSF vs BFP** - confronto rendimenti nel tempo
- **Simulatore BTPi** - proiezione valore indicizzato all'inflazione con calcolo rendita
- **Vendita con Riserva di Proprietà** - piano ammortamento alla francese, calcolo plusvalenza (esenzione automatica > 5 anni), cash flow annuale, confronto vendita immediata vs VRP, costo opportunità, salvataggio simulazioni collegate a immobili, integrazione con patrimonio (credito residuo automatico)
- **Simulazione Investimento** - analisi sostenibilità patrimoniale con proiezione anni durata capitale

### Strumenti
- **Import/Export** - importazione da Excel originale, CSV, export completo, export con grafici
- **Import Fineco** - parsing export portafoglio .xls Fineco con preview, aggiornamento automatico posizioni ETF/Bond e record patrimonio, gestione ISIN alias
- **Impostazioni** - parametri globali (data nascita, sconti dashboard, parametri simulazione), tema persistente (dark/light)

## Tecnologie

- **Backend**: Python 3.10, Flask
- **Database**: SQLite con WAL mode
- **Frontend**: Bootstrap 5, Plotly.js, DataTables
- **Deploy**: Docker + Gunicorn

## Installazione

### Locale

```bash
pip install -r requirements.txt
python app.py
```

Disponibile su http://localhost:5000

### Docker

```bash
docker compose up -d --build
```

Per importare dati esistenti:

```bash
docker cp data/gestptf.db gestptf:/app/data/
docker cp xlsbase/ gestptf:/app/
```

## Struttura progetto

```
gestptf/
├── app.py                  # Entry point Flask
├── config.py               # Configurazione path
├── database.py             # Schema DB e init
├── routes/                 # Blueprint Flask
│   ├── dashboard.py
│   ├── patrimonio.py
│   ├── etf.py, bond.py, bfp.py
│   ├── immobili.py
│   ├── fondo_pensione.py, tfr_route.py
│   ├── liquidita.py, liquidita_nuova.py
│   ├── debiti.py
│   ├── simulatore.py       # BSF, BTPi, VRP
│   ├── simulazione_inv.py
│   ├── import_export.py
│   └── impostazioni.py
├── services/               # Logica business
│   ├── patrimonio_service.py
│   ├── etf_service.py, bond_service.py
│   ├── bfp_service.py, bfp_calculator.py, bfp_pdf_parser.py
│   ├── immobili_service.py
│   ├── fp_service.py, tfr_service.py
│   ├── liquidita_service.py, liquidita_nuova_service.py
│   ├── debiti_service.py
│   ├── simulatore_service.py
│   ├── fineco_import_service.py
│   └── import_service.py
├── templates/              # Template Jinja2
├── static/                 # CSS, JS
├── data/                   # Database (gitignored)
├── xlsbase/                # File Excel personali (gitignored)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Note

- I dati personali (database, file Excel, screenshot) sono esclusi dal repository tramite `.gitignore`
- Il tema (dark/light) è persistente via localStorage
- I BFP vengono ricalcolati automaticamente alla data odierna all'apertura della sezione
- L'import Fineco gestisce automaticamente i cambi ISIN dei BTP (emissione -> mercato secondario)

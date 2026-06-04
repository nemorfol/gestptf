# CLAUDE.md

Contesto di progetto per assistenti AI (Claude Code, Cursor, ecc.) che lavorano su GestPTF. Tenere conciso e aggiornato.

## Cos'è

Web app per la gestione del patrimonio personale italiano: BTP, BFP, ETF, fondo pensione, TFR, immobili, liquidità, debiti. Calcoli specifici del contesto italiano (es. valori di rimborso BFP con coefficienti CDP, rendita BSF/BO65, Vendita con Riserva di Proprietà).

Single-user, locale o piccolo deploy Docker. Non è un SaaS multi-tenant.

## Stack

- **Backend**: Python 3.10+, Flask, SQLite (WAL mode)
- **Frontend**: Bootstrap 5, Plotly.js, DataTables, jQuery (richiesto da DataTables)
- **No build tools**: niente webpack/vite/npm. JS vanilla, CSS direttamente in `static/css/`.
- **No JS framework**: niente React/Vue/Svelte. Aggiungere uno di questi è fuori scope.
- **Deploy**: Docker + Gunicorn (vedi `Dockerfile`, `docker-compose.yml`).

## Avvio locale

```bash
pip install -r requirements.txt
python app.py
```

Server su http://127.0.0.1:5000. Il DB SQLite viene creato automaticamente in `data/gestptf.db` al primo avvio (`database.py:init_db`).

## Struttura

```
app.py                 # entry point, registra blueprint, filtri Jinja (currency, percent, date)
config.py              # path: DB_PATH, EXCEL_PATH, UPLOAD_FOLDER, EXPORT_FOLDER
database.py            # schema + init_db (gestisce anche le migrazioni con ALTER TABLE)
routes/<area>.py       # blueprint Flask: una route file per sezione
services/<area>_service.py   # logica business e accesso al DB
templates/<area>.html  # template Jinja2, estendono base.html
static/css/style.css   # stili custom (oltre Bootstrap)
static/js/app.js       # helper globali esposti su window.PM
```

Pattern: **route sottile, service spesso**. Le route fanno solo parsing della request e jsonify del risultato. Tutta la logica e le query SQL stanno nei service.

## Sezioni principali

| Sezione | Route prefix | Service | Tabella DB |
|---|---|---|---|
| Dashboard | `/` | (legge varie) | — |
| Patrimonio | `/patrimonio` | `patrimonio_service.py` | `patrimonio` |
| ETF | `/etf` | `etf_service.py` | `etf`, `quotazioni` |
| Obbligazioni/BTP | `/bond` | `bond_service.py` | `bond`, `quotazioni` |
| BFP | `/bfp` | `bfp_service.py`, `bfp_calculator.py`, `bfp_pdf_parser.py` | `bfp`, `bfp_coefficienti` |
| Immobili | `/immobili` | `immobili_service.py` | `immobili`, `immobili_storico` |
| Fondo Pensione | `/fondo-pensione` | `fp_service.py` | `fondo_pensione` |
| TFR | `/tfr` | `tfr_service.py` | `tfr` |
| Liquidità | `/liquidita` | `liquidita_nuova_service.py`, `liquidita_service.py` | `liquidita`, `investimento_liquidita` |
| Debiti | `/debiti` | `debiti_service.py` | `debiti` |
| Simulatori | `/simulatore` | `simulatore_service.py` | `parametri`, `vendita_riserva` |
| Impostazioni | `/impostazioni` | (parametri table) | `parametri` |

## Glossario dominio (italiano finanza)

- **BFP** — Buoni Fruttiferi Postali (prodotto Poste/CDP). Tipologie: Ordinario, 4x4, BSF (Buono Soluzione Futuro), BO65 (Buono Obiettivo 65), BFPi (Buono Indicizzato Inflazione Italiana).
- **CDP** — Cassa Depositi e Prestiti. Emette i BFP; pubblica "Fogli Informativi" PDF con i coefficienti di rivalutazione.
- **BSF/BO65** — Hanno una rendita mensile tra i 65 e gli 80 anni. Il valore di scadenza si calcola con la **Tabella A** (eta-based), il valore di rimborso periodico con la **Tabella B** (anni/semestri).
- **BTP** — Buoni del Tesoro Poliennali (titoli di Stato). I BTPi sono indicizzati all'inflazione.
- **VRP** — Vendita con Riserva di Proprietà: vendita immobile dilazionata con piano di ammortamento alla francese.
- **RPOL** — Portale Poste per scaricare l'estratto dei BFP in Excel.
- **TFR** — Trattamento di Fine Rapporto. Trattato come asset patrimoniale.

## Convenzioni codice

- **PEP 8**, indent 4 spazi.
- **Niente commenti ovvi**. Il codice si spiega coi nomi. Commento solo per il *perché* non ovvio (bug storici, regole di business sottili, vincoli esterni).
- **Niente docstring multi-paragrafo**. Una riga sintetica basta.
- **Niente nuovi file `.md` di documentazione** non richiesti dall'utente.
- **Niente emoji nel codice o nei file di progetto** salvo richiesta esplicita.
- **Niente fallback/validation per casi che non possono succedere**: trust internal code, valida solo ai boundary (request utente, file esterni).
- **Una funzione = una responsabilità**. Service di una sezione = un file.

## Pattern: Patrimonio "live values"

`/patrimonio/valori-live?data=YYYY-MM-DD` aggrega in un singolo endpoint i valori correnti da: BFP (ricalcolato), Fondo Pensione (ultimo record), TFR (ultimo record), Immobili (somma per tipo), e i valori Fineco salvati come parametri (ETF, BTP, CD).

Quando l'utente crea un nuovo record patrimonio, questi valori popolano automaticamente il form. Se aggiungi una nuova asset class, aggiorna sia [routes/patrimonio.py:valori_live](routes/patrimonio.py) sia il template `patrimonio.html` lato JS (`liveFields`).

## Pattern: integrazione VRP

`patrimonio_service.get_vrp_impatto_record(data)` calcola per ogni record patrimonio l'impatto cumulativo delle VRP attive a quella data (delta su immobile_italia/esteri + cash da incassi). Il totale "Netto + VRP" mostra il patrimonio come se la VRP fosse applicata. Si assume che l'utente inserisca i valori **pre-VRP** (immobile a valore pieno, cash senza incassi VRP).

## Gotcha: BFP calculator

Quando lavori su `services/bfp_calculator.py` attenzione a:

1. **Unità `semestri`**: il calcolatore usa `0` o `1` (quale metà dell'anno), ma il DB salva `0` o `6` (mesi extra). Confronta sempre in **mesi totali** (`anni*12 + semestri`). Non assumere coincidenza di unità.
2. **`durata_massima` ha semantiche diverse** per tipo di BFP:
   - Buono Ordinario: `durata_massima` = scadenza reale in anni (es. 20)
   - BO65/BSF: `durata_massima` = periodo iniziale di non-rivalutazione (es. 3)
   - **Non usare come filtro generico**.
3. Il parser PDF può concatenare tabelle ausiliarie (rendita, conversione) sotto la stessa serie con `tipo_tabella='B'`. Per il valore a scadenza ordinare per `coeff_lordo DESC` (= max rivalutazione vera), non per max periodo.
4. Per stesso `(anni, semestri)` possono esserci righe multiple (sub-periodi bimestrali del Buono Ordinario). Ordinare anche per `coeff_lordo DESC` come chiave secondaria.

## Gotcha: BFP recalculation

`/bfp/` chiama `calcola_tutti_bfp()` a ogni GET → sovrascrive i valori salvati. I valori dall'import Excel di Poste vengono preservati in colonne `imp_*` (`imp_lordo_attuale`, `imp_rimborso_netto`, `imp_lordo_scadenza`, `imp_netto_scadenza`) e mostrati nei template come confronto. Non rimuovere quel salvataggio in `bfp_service.import_bfp_from_excel`.

Per BSF/BO65 il calcolo del valore a scadenza usa **Tabella A** se `data_nascita` è in `parametri`. Senza data nascita cade sul max di Tabella B e produce risultati errati.

## Database & migrazioni

Niente Alembic. Le migrazioni stanno in `database.py:init_db()` con pattern:

```python
existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(<tabella>)").fetchall()}
for col in (...):
    if col not in existing_cols:
        conn.execute(f"ALTER TABLE <tabella> ADD COLUMN {col} ...")
```

Aggiungere nuove colonne sempre con `ALTER TABLE ADD COLUMN` qui dentro, mai droppare colonne esistenti in produzione.

## Filtri Jinja standard

Definiti in `app.py`. Usali nei template invece di formattare a mano:

- `{{ valore|currency }}` → `€ 1.234,56`
- `{{ valore|percent }}` → `+12,34%` o `-3,21%`
- `{{ valore|number(2) }}` → `1.234,56`
- `{{ data|date }}` → strippa la parte orario da datetime stringhe

In JavaScript usa `PM.Fmt.currency()`, `PM.Fmt.percent()`, `PM.Fmt.number()` da `static/js/app.js`.

## Helper JS globali (`window.PM`)

- `PM.apiCall(url, method, data)` — fetch wrapper con loading overlay e toast su errore
- `PM.Toast.show(msg, type)` — `type` in `success|error|warning|info`
- `PM.confirmAction(msg, onConfirm)` — modal Bootstrap di conferma
- `PM.DT.init(selector, opts)` — DataTable con lingua italiana
- `PM.Plotly.layout(title)` — layout Plotly tema-aware (light/dark)
- `PM.colorPLCells()` — colora celle P/L verde/rosso

## Cosa NON committare

Tutto già in `.gitignore`, da NON aggirare:

- `data/` — database SQLite e cache locale
- `xlsbase/` — Excel personali
- `pdf/bfp/` — Foglio Informativo PDF (potrebbero contenere dati riservati a seconda della versione)
- Screenshot con valori reali (`*.png` con dati patrimoniali)
- `.env`, token, credenziali

Non includere mai dati di patrimonio reale (cifre, ISIN personali, intestazioni libretti) negli esempi nei commenti, nei test, nei seed o nelle issue/PR.

## Test rapidi

Non c'è una suite di test formale (`pytest` non è in `requirements.txt`). Per validare le modifiche:

```python
from app import create_app
app = create_app()
with app.test_client() as c:
    r = c.get('/<route>/')
    assert r.status_code == 200
```

Per UI changes: avvia il server, apri http://127.0.0.1:5000, verifica manualmente.

## Aggiungere una nuova sezione

1. Crea `routes/<nome>.py` con blueprint e prefisso URL
2. Crea `services/<nome>_service.py` con CRUD + funzioni di calcolo
3. Aggiorna `database.py:init_db()` con `CREATE TABLE IF NOT EXISTS`
4. Crea `templates/<nome>.html` che estende `base.html`
5. Registra il blueprint in `app.py:create_app`
6. Aggiungi voce nella sidebar in `templates/base.html`
7. Se la sezione ha un valore "live" per il patrimonio, integralo in `/patrimonio/valori-live`

import sqlite3
import os
from config import DB_PATH, BASE_DIR


def get_db():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize the database schema."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS etf (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isin TEXT NOT NULL,
            nome TEXT NOT NULL,
            data_acquisto DATE NOT NULL,
            quantita REAL NOT NULL,
            prezzo_acquisto REAL NOT NULL,
            commissioni REAL DEFAULT 0,
            costo_totale REAL DEFAULT 0,
            attivo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS bond (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isin TEXT NOT NULL,
            nome TEXT NOT NULL,
            data_acquisto DATE NOT NULL,
            quantita REAL NOT NULL,
            prezzo_acquisto REAL NOT NULL,
            commissioni REAL DEFAULT 0,
            rateo_lordo REAL DEFAULT 0,
            ritenuta_rateo REAL DEFAULT 0,
            ritenuta_dis REAL DEFAULT 0,
            uscita REAL DEFAULT 0,
            uscita_per_calcolo REAL DEFAULT 0,
            coeff_indicizz REAL DEFAULT 0,
            attivo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS quotazioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isin TEXT NOT NULL,
            data DATE NOT NULL,
            quotazione_eur REAL,
            quotazione_usd REAL,
            coeff_indicizz REAL DEFAULT 0,
            UNIQUE(isin, data)
        );

        CREATE TABLE IF NOT EXISTS patrimonio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE NOT NULL UNIQUE,
            immobili_esteri REAL DEFAULT 0,
            immobile_italia REAL DEFAULT 0,
            fondo_pensione REAL DEFAULT 0,
            etf REAL DEFAULT 0,
            bfp REAL DEFAULT 0,
            btp REAL DEFAULT 0,
            cash REAL DEFAULT 0,
            cd REAL DEFAULT 0,
            tfr_netto REAL DEFAULT 0,
            debiti REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS investimento_liquidita (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anno INTEGER,
            data DATE,
            mese INTEGER,
            liquidita_entrata REAL DEFAULT 0,
            importo_cd REAL DEFAULT 0,
            importo_bfpi REAL DEFAULT 0,
            liquidita_accumulata REAL DEFAULT 0,
            accumulo_bsf REAL DEFAULT 0,
            accumulo_bfpi REAL DEFAULT 0,
            pct_bfpi REAL DEFAULT 0,
            accumulo_cd REAL DEFAULT 0,
            pct_cd REAL DEFAULT 0,
            accumulo_altro REAL DEFAULT 0,
            pct_altro REAL DEFAULT 0,
            totale_bsf REAL DEFAULT 0,
            totale_altro REAL DEFAULT 0,
            mesi_passati INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS simulazione_investimento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE,
            immobili_esteri REAL DEFAULT 0,
            immobile_italia REAL DEFAULT 0,
            fondo_pensione REAL DEFAULT 0,
            etf REAL DEFAULT 0,
            bfp REAL DEFAULT 0,
            btp REAL DEFAULT 0,
            cash REAL DEFAULT 0,
            cd REAL DEFAULT 0,
            tfr_netto REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS parametri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chiave TEXT NOT NULL UNIQUE,
            valore TEXT NOT NULL,
            descrizione TEXT,
            categoria TEXT DEFAULT 'generale'
        );

        -- ══ Nuove tabelle per gestione scorporata ══

        CREATE TABLE IF NOT EXISTS bfp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipologia TEXT NOT NULL,
            serie TEXT,
            data_sottoscrizione DATE NOT NULL,
            scadenza DATE,
            valore_nominale REAL NOT NULL DEFAULT 0,
            valore_rimborso_lordo REAL DEFAULT 0,
            valore_lordo_attuale REAL DEFAULT 0,
            ritenuta_fiscale REAL DEFAULT 0,
            valore_rimborso_netto REAL DEFAULT 0,
            valore_lordo_scadenza REAL DEFAULT 0,
            ritenuta_scadenza REAL DEFAULT 0,
            valore_netto_scadenza REAL DEFAULT 0,
            regolato_su TEXT,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS immobili (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'estero',
            indirizzo TEXT,
            valore_stimato REAL NOT NULL DEFAULT 0,
            data_acquisto DATE,
            prezzo_acquisto REAL DEFAULT 0,
            rendita_annua REAL DEFAULT 0,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS immobili_storico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            immobile_id INTEGER NOT NULL,
            data DATE NOT NULL,
            valore_stimato REAL NOT NULL,
            note TEXT,
            FOREIGN KEY (immobile_id) REFERENCES immobili(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS fondo_pensione (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL DEFAULT 'Fondo Pensione',
            data DATE NOT NULL,
            valore REAL NOT NULL DEFAULT 0,
            contributo REAL DEFAULT 0,
            rendimento REAL DEFAULT 0,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS tfr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE NOT NULL,
            valore_netto REAL NOT NULL DEFAULT 0,
            variazione REAL DEFAULT 0,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS liquidita (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL DEFAULT 'cash',
            descrizione TEXT,
            importo REAL NOT NULL DEFAULT 0,
            data_aggiornamento DATE NOT NULL,
            tasso REAL DEFAULT 0,
            scadenza DATE,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS debiti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL DEFAULT 'altro',
            descrizione TEXT NOT NULL,
            importo_iniziale REAL NOT NULL DEFAULT 0,
            importo_residuo REAL NOT NULL DEFAULT 0,
            tasso_interesse REAL DEFAULT 0,
            rata_mensile REAL DEFAULT 0,
            data_inizio DATE,
            data_fine DATE,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS bfp_coefficienti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serie TEXT NOT NULL,
            tipologia TEXT NOT NULL,
            tipo_tabella TEXT NOT NULL,
            anni INTEGER DEFAULT 0,
            semestri INTEGER DEFAULT 0,
            eta_da TEXT,
            eta_a TEXT,
            coeff_lordo REAL NOT NULL,
            coeff_netto REAL NOT NULL,
            tasso_lordo REAL DEFAULT 0,
            tasso_netto REAL DEFAULT 0,
            durata_massima INTEGER DEFAULT 0,
            note TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_bfp_coeff_serie ON bfp_coefficienti(serie);

        CREATE INDEX IF NOT EXISTS idx_etf_isin ON etf(isin);
        CREATE INDEX IF NOT EXISTS idx_bond_isin ON bond(isin);
        CREATE INDEX IF NOT EXISTS idx_quotazioni_isin ON quotazioni(isin);
        CREATE INDEX IF NOT EXISTS idx_patrimonio_data ON patrimonio(data);
        CREATE INDEX IF NOT EXISTS idx_bfp_tipologia ON bfp(tipologia);
        CREATE INDEX IF NOT EXISTS idx_immobili_tipo ON immobili(tipo);
        CREATE INDEX IF NOT EXISTS idx_fondo_pensione_data ON fondo_pensione(data);
        CREATE INDEX IF NOT EXISTS idx_tfr_data ON tfr(data);
        CREATE INDEX IF NOT EXISTS idx_debiti_tipo ON debiti(tipo);

        CREATE TABLE IF NOT EXISTS vendita_riserva (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            immobile_id INTEGER,
            nome TEXT NOT NULL,
            data_simulazione DATE NOT NULL,
            data_inizio_piano DATE,
            attiva INTEGER DEFAULT 0,
            valore_vendita REAL NOT NULL DEFAULT 0,
            valore_vendita_immediata REAL DEFAULT 0,
            prezzo_acquisto REAL DEFAULT 0,
            data_acquisto DATE,
            anticipo REAL DEFAULT 0,
            durata_anni INTEGER DEFAULT 0,
            tasso_interesse REAL DEFAULT 0,
            spese_notarili REAL DEFAULT 0,
            aliquota_plusvalenza REAL DEFAULT 0,
            imposta_registro REAL DEFAULT 0,
            imu_annuale REAL DEFAULT 0,
            costo_assicurazione REAL DEFAULT 0,
            tasso_investimento REAL DEFAULT 0,
            rata_mensile REAL DEFAULT 0,
            ricavo_netto REAL DEFAULT 0,
            anni_sostenibilita INTEGER DEFAULT 0,
            note TEXT,
            FOREIGN KEY (immobile_id) REFERENCES immobili(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_vrp_immobile ON vendita_riserva(immobile_id);

        CREATE TABLE IF NOT EXISTS addizionali_irpef (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            nome TEXT NOT NULL,
            regione TEXT,
            reddito_da REAL DEFAULT 0,
            reddito_a REAL DEFAULT 999999999,
            aliquota REAL NOT NULL DEFAULT 0,
            anno INTEGER DEFAULT 2025
        );

        CREATE INDEX IF NOT EXISTS idx_addizionali_tipo ON addizionali_irpef(tipo, nome);
    """)

    # Insert default parameters
    defaults = [
        ('inflazione_prevista', '0', 'Inflazione prevista %', 'simulazione'),
        ('tasso_bfp_ordinario', '0', 'Tasso BFP Ordinario %', 'simulazione'),
        ('tasso_bsf', '0', 'Tasso Buono Soluzione Futuro %', 'simulazione'),
        ('anni_simulazione', '0', 'Anni simulazione', 'simulazione'),
        ('importo_simulazione', '0', 'Importo base simulazione', 'simulazione'),
        ('vrp_tasso_interesse', '0', 'Tasso interesse VRP %', 'simulazione'),
        ('vrp_durata_anni', '0', 'Durata piano VRP anni', 'simulazione'),
        ('vrp_aliquota_plusvalenza', '0', 'Aliquota plusvalenza %', 'simulazione'),
        ('vrp_tasso_investimento', '0', 'Tasso investimento alternativo %', 'simulazione'),
        ('data_nascita', '', 'Data di nascita utente', 'generale'),
        ('tema', 'light', 'Tema interfaccia (light/dark)', 'generale'),
        ('dashboard_sconto_esteri', '0', 'Sconto % Immobili Esteri dashboard', 'generale'),
        ('dashboard_sconto_italia', '0', 'Sconto % Immobile Italia dashboard', 'generale'),
    ]
    for chiave, valore, desc, cat in defaults:
        cursor.execute(
            "INSERT OR IGNORE INTO parametri (chiave, valore, descrizione, categoria) VALUES (?, ?, ?, ?)",
            (chiave, valore, desc, cat)
        )

    conn.commit()

    # Auto-import BFP coefficients from PDF if table is empty
    count = conn.execute("SELECT COUNT(*) FROM bfp_coefficienti").fetchone()[0]
    if count == 0:
        pdf_dir = os.path.join(BASE_DIR, 'pdf', 'bfp')
        if os.path.isdir(pdf_dir) and any(f.endswith('.pdf') for f in os.listdir(pdf_dir)):
            conn.close()
            try:
                from services.bfp_pdf_parser import import_all_bfp_pdfs
                result = import_all_bfp_pdfs(pdf_dir)
                if isinstance(result, dict) and result.get("success"):
                    print(f"  BFP: importati {result['totale_coefficienti']} coefficienti da {result['files_processati']} PDF")
                elif isinstance(result, dict) and "error" in result:
                    print(f"  BFP: errore import PDF - {result['error']}")
            except Exception as e:
                print(f"  BFP: errore import PDF - {e}")
        else:
            conn.close()
    else:
        conn.close()


if __name__ == '__main__':
    init_db()
    print("Database inizializzato con successo!")

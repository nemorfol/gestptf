from database import get_db

# Asset class fields in the patrimonio table (excluding id, data, debiti)
ASSET_FIELDS = [
    "immobili_esteri",
    "immobile_italia",
    "fondo_pensione",
    "etf",
    "bfp",
    "btp",
    "cash",
    "cd",
    "tfr_netto",
]

ALL_FIELDS = ASSET_FIELDS + ["debiti"]


def get_all_patrimonio():
    """Returns all patrimonio records ordered by data ASC."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM patrimonio ORDER BY data ASC"
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


def get_patrimonio_by_id(id):
    """Returns a single patrimonio record by id."""
    try:
        db = get_db()
        row = db.execute(
            "SELECT * FROM patrimonio WHERE id = ?", (id,)
        ).fetchone()
        db.close()
        if row is None:
            return {"error": "Record non trovato"}
        return dict(row)
    except Exception as e:
        return {"error": str(e)}


def get_latest_patrimonio():
    """Returns the most recent patrimonio record."""
    try:
        db = get_db()
        row = db.execute(
            "SELECT * FROM patrimonio ORDER BY data DESC LIMIT 1"
        ).fetchone()
        db.close()
        if row is None:
            return {"error": "Nessun record trovato"}
        return dict(row)
    except Exception as e:
        return {"error": str(e)}


def create_patrimonio(data):
    """Insert a new patrimonio record."""
    try:
        db = get_db()
        cursor = db.execute(
            """INSERT INTO patrimonio (data, immobili_esteri, immobile_italia,
               fondo_pensione, etf, bfp, btp, cash, cd, tfr_netto, debiti)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["data"],
                float(data.get("immobili_esteri", 0)),
                float(data.get("immobile_italia", 0)),
                float(data.get("fondo_pensione", 0)),
                float(data.get("etf", 0)),
                float(data.get("bfp", 0)),
                float(data.get("btp", 0)),
                float(data.get("cash", 0)),
                float(data.get("cd", 0)),
                float(data.get("tfr_netto", 0)),
                float(data.get("debiti", 0)),
            ),
        )
        db.commit()
        new_id = cursor.lastrowid
        db.close()
        return {"id": new_id}
    except Exception as e:
        return {"error": str(e)}


def update_patrimonio(id, data):
    """Update an existing patrimonio record."""
    try:
        db = get_db()
        db.execute(
            """UPDATE patrimonio SET data = ?, immobili_esteri = ?,
               immobile_italia = ?, fondo_pensione = ?, etf = ?,
               bfp = ?, btp = ?, cash = ?, cd = ?, tfr_netto = ?,
               debiti = ? WHERE id = ?""",
            (
                data["data"],
                float(data.get("immobili_esteri", 0)),
                float(data.get("immobile_italia", 0)),
                float(data.get("fondo_pensione", 0)),
                float(data.get("etf", 0)),
                float(data.get("bfp", 0)),
                float(data.get("btp", 0)),
                float(data.get("cash", 0)),
                float(data.get("cd", 0)),
                float(data.get("tfr_netto", 0)),
                float(data.get("debiti", 0)),
                id,
            ),
        )
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def delete_patrimonio(id):
    """Delete a patrimonio record by id."""
    try:
        db = get_db()
        db.execute("DELETE FROM patrimonio WHERE id = ?", (id,))
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def get_patrimonio_totali(record):
    """Calculate totale, totale_netto (- debiti), totale_adj (-20% immobili).

    Returns dict with totale, totale_netto, totale_adj.
    """
    try:
        totale = sum(float(record.get(f, 0)) for f in ASSET_FIELDS)
        debiti = float(record.get("debiti", 0))
        totale_netto = totale - debiti

        immobili = float(record.get("immobili_esteri", 0)) + float(
            record.get("immobile_italia", 0)
        )
        totale_adj = totale_netto - (immobili * 0.20)

        return {
            "totale": round(totale, 2),
            "totale_netto": round(totale_netto, 2),
            "totale_adj": round(totale_adj, 2),
        }
    except Exception as e:
        return {"error": str(e)}


def get_patrimonio_percentuali(record):
    """Calculate % allocation for each asset class. Returns dict."""
    try:
        totale = sum(float(record.get(f, 0)) for f in ASSET_FIELDS)

        percentuali = {}
        for field in ASSET_FIELDS:
            valore = float(record.get(field, 0))
            percentuali[field] = (
                round(valore / totale * 100, 2) if totale > 0 else 0
            )

        percentuali["totale"] = totale
        return percentuali
    except Exception as e:
        return {"error": str(e)}


def get_patrimonio_variazioni():
    """Returns list of records with variazione % vs first record."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM patrimonio ORDER BY data ASC"
        ).fetchall()
        db.close()

        if not rows:
            return []

        records = [dict(r) for r in rows]
        primo = records[0]
        totali_primo = get_patrimonio_totali(primo)

        if "error" in totali_primo:
            return {"error": totali_primo["error"]}

        base = totali_primo["totale_netto"]

        risultati = []
        for record in records:
            totali = get_patrimonio_totali(record)
            if "error" in totali:
                continue
            corrente = totali["totale_netto"]
            variazione = (
                round((corrente - base) / base * 100, 2) if base > 0 else 0
            )
            record["totale_netto"] = corrente
            record["variazione_pct"] = variazione
            risultati.append(record)

        return risultati
    except Exception as e:
        return {"error": str(e)}

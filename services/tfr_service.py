from database import get_db


TFR_FIELDS = ["data", "valore_netto", "variazione", "note"]


def get_all_tfr():
    """Returns all TFR records ordered by data DESC."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM tfr ORDER BY data DESC"
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


def get_tfr_by_id(id):
    """Returns a single TFR record by id."""
    try:
        db = get_db()
        row = db.execute(
            "SELECT * FROM tfr WHERE id = ?", (id,)
        ).fetchone()
        db.close()
        if row is None:
            return {"error": "Record non trovato"}
        return dict(row)
    except Exception as e:
        return {"error": str(e)}


def create_tfr(data):
    """Insert a new TFR record."""
    try:
        db = get_db()
        placeholders = ", ".join(["?"] * len(TFR_FIELDS))
        columns = ", ".join(TFR_FIELDS)
        values = [data.get(f) for f in TFR_FIELDS]

        cursor = db.execute(
            f"INSERT INTO tfr ({columns}) VALUES ({placeholders})",
            values,
        )
        db.commit()
        new_id = cursor.lastrowid
        db.close()
        return {"id": new_id}
    except Exception as e:
        return {"error": str(e)}


def update_tfr(id, data):
    """Update an existing TFR record."""
    try:
        db = get_db()
        set_clause = ", ".join([f"{f} = ?" for f in TFR_FIELDS])
        values = [data.get(f) for f in TFR_FIELDS]
        values.append(id)

        db.execute(
            f"UPDATE tfr SET {set_clause} WHERE id = ?",
            values,
        )
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def delete_tfr(id):
    """Delete a TFR record by id."""
    try:
        db = get_db()
        db.execute("DELETE FROM tfr WHERE id = ?", (id,))
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def get_latest_tfr():
    """Returns the most recent TFR record."""
    try:
        db = get_db()
        row = db.execute(
            "SELECT * FROM tfr ORDER BY data DESC LIMIT 1"
        ).fetchone()
        db.close()
        if row is None:
            return {"error": "Nessun record trovato"}
        return dict(row)
    except Exception as e:
        return {"error": str(e)}


def get_tfr_summary():
    """Returns TFR summary: ultimo_valore, prima_registrazione, variazione_totale."""
    try:
        db = get_db()
        # Latest record
        latest = db.execute(
            "SELECT valore_netto, data FROM tfr ORDER BY data DESC LIMIT 1"
        ).fetchone()

        # First record
        first = db.execute(
            "SELECT valore_netto, data FROM tfr ORDER BY data ASC LIMIT 1"
        ).fetchone()

        db.close()

        if latest is None:
            return {
                "ultimo_valore": 0,
                "prima_registrazione": None,
                "variazione_totale": 0,
            }

        latest_d = dict(latest)
        first_d = dict(first)

        ultimo_valore = latest_d["valore_netto"] or 0
        prima_registrazione = first_d["data"]
        primo_valore = first_d["valore_netto"] or 0
        variazione_totale = ultimo_valore - primo_valore

        return {
            "ultimo_valore": ultimo_valore,
            "valore_attuale": ultimo_valore,
            "prima_registrazione": prima_registrazione,
            "variazione_totale": variazione_totale,
        }
    except Exception as e:
        return {"error": str(e)}

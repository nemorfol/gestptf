from database import get_db


LIQUIDITA_FIELDS = [
    "tipo", "descrizione", "importo", "data_aggiornamento",
    "tasso", "scadenza", "note",
]


def get_all_liquidita_nuova():
    """Returns all liquidita records ordered by tipo, data_aggiornamento DESC."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM liquidita ORDER BY tipo, data_aggiornamento DESC"
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


def get_liquidita_by_id(id):
    """Returns a single liquidita record by id."""
    try:
        db = get_db()
        row = db.execute(
            "SELECT * FROM liquidita WHERE id = ?", (id,)
        ).fetchone()
        db.close()
        if row is None:
            return {"error": "Record non trovato"}
        return dict(row)
    except Exception as e:
        return {"error": str(e)}


def create_liquidita_nuova(data):
    """Insert a new liquidita record."""
    try:
        db = get_db()
        placeholders = ", ".join(["?"] * len(LIQUIDITA_FIELDS))
        columns = ", ".join(LIQUIDITA_FIELDS)
        values = [data.get(f) for f in LIQUIDITA_FIELDS]

        cursor = db.execute(
            f"INSERT INTO liquidita ({columns}) VALUES ({placeholders})",
            values,
        )
        db.commit()
        new_id = cursor.lastrowid
        db.close()
        return {"id": new_id}
    except Exception as e:
        return {"error": str(e)}


def update_liquidita_nuova(id, data):
    """Update an existing liquidita record."""
    try:
        db = get_db()
        set_clause = ", ".join([f"{f} = ?" for f in LIQUIDITA_FIELDS])
        values = [data.get(f) for f in LIQUIDITA_FIELDS]
        values.append(id)

        db.execute(
            f"UPDATE liquidita SET {set_clause} WHERE id = ?",
            values,
        )
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def delete_liquidita_nuova(id):
    """Delete a liquidita record by id."""
    try:
        db = get_db()
        db.execute("DELETE FROM liquidita WHERE id = ?", (id,))
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def get_liquidita_storico():
    """Returns cash history from patrimonio table for the chart."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT data, cash FROM patrimonio ORDER BY data ASC"
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


def get_liquidita_summary_nuova():
    """Returns liquidita summary based on latest record per type."""
    try:
        db = get_db()
        # Get the most recent value for each type
        row = db.execute(
            """SELECT
                  COALESCE((SELECT importo FROM liquidita WHERE tipo = 'cash'
                            ORDER BY data_aggiornamento DESC LIMIT 1), 0) as totale_cash,
                  COALESCE((SELECT SUM(sub.importo) FROM (
                      SELECT tipo, importo, ROW_NUMBER() OVER (PARTITION BY tipo ORDER BY data_aggiornamento DESC) as rn
                      FROM liquidita WHERE tipo IN ('cd', 'xeon', 'deposito')
                  ) sub WHERE sub.rn = 1), 0) as totale_cd,
                  COUNT(*) as count
               FROM liquidita"""
        ).fetchone()
        db.close()
        result = dict(row)
        result["totale"] = round((result["totale_cash"] or 0) + (result["totale_cd"] or 0), 2)
        result["totale_liquidita"] = result["totale"]
        return result
    except Exception as e:
        return {"error": str(e)}

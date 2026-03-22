from database import get_db

FIELDS = [
    "anno", "data", "mese", "liquidita_entrata", "importo_cd",
    "importo_bfpi", "liquidita_accumulata", "accumulo_bsf",
    "accumulo_bfpi", "pct_bfpi", "accumulo_cd", "pct_cd",
    "accumulo_altro", "pct_altro", "totale_bsf", "totale_altro",
    "mesi_passati",
]


def get_all_liquidita():
    """Returns all liquidita records ordered by data ASC."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM investimento_liquidita ORDER BY data ASC"
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
            "SELECT * FROM investimento_liquidita WHERE id = ?", (id,)
        ).fetchone()
        db.close()
        if row is None:
            return {"error": "Record non trovato"}
        return dict(row)
    except Exception as e:
        return {"error": str(e)}


def create_liquidita(data):
    """Insert a new liquidita record."""
    try:
        db = get_db()
        placeholders = ", ".join(["?"] * len(FIELDS))
        columns = ", ".join(FIELDS)
        values = [data.get(f, 0) for f in FIELDS]

        cursor = db.execute(
            f"INSERT INTO investimento_liquidita ({columns}) VALUES ({placeholders})",
            values,
        )
        db.commit()
        new_id = cursor.lastrowid
        db.close()
        return {"id": new_id}
    except Exception as e:
        return {"error": str(e)}


def update_liquidita(id, data):
    """Update an existing liquidita record."""
    try:
        db = get_db()
        set_clause = ", ".join([f"{f} = ?" for f in FIELDS])
        values = [data.get(f, 0) for f in FIELDS]
        values.append(id)

        db.execute(
            f"UPDATE investimento_liquidita SET {set_clause} WHERE id = ?",
            values,
        )
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def delete_liquidita(id):
    """Delete a liquidita record by id."""
    try:
        db = get_db()
        db.execute("DELETE FROM investimento_liquidita WHERE id = ?", (id,))
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def get_liquidita_summary():
    """Returns totals and distributions for liquidita."""
    try:
        db = get_db()
        row = db.execute(
            """SELECT
                COUNT(*) AS totale_count,
                COALESCE(SUM(liquidita_entrata), 0) AS totale_liquidita_entrata,
                COALESCE(SUM(importo_cd), 0) AS totale_importo_cd,
                COALESCE(SUM(importo_bfpi), 0) AS totale_importo_bfpi,
                COALESCE(SUM(liquidita_accumulata), 0) AS totale_liquidita_accumulata,
                COALESCE(SUM(accumulo_bsf), 0) AS totale_accumulo_bsf,
                COALESCE(SUM(accumulo_bfpi), 0) AS totale_accumulo_bfpi,
                COALESCE(SUM(accumulo_cd), 0) AS totale_accumulo_cd,
                COALESCE(SUM(accumulo_altro), 0) AS totale_accumulo_altro
            FROM investimento_liquidita"""
        ).fetchone()
        db.close()

        if row is None:
            return {"error": "Nessun dato disponibile"}

        result = dict(row)

        # Calculate latest totals from the most recent record
        db = get_db()
        latest = db.execute(
            "SELECT * FROM investimento_liquidita ORDER BY data DESC LIMIT 1"
        ).fetchone()
        db.close()

        if latest:
            result["ultimo_totale_bsf"] = latest["totale_bsf"]
            result["ultimo_totale_altro"] = latest["totale_altro"]

        return result
    except Exception as e:
        return {"error": str(e)}

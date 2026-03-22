from database import get_db


DEBITI_FIELDS = [
    "tipo", "descrizione", "importo_iniziale", "importo_residuo",
    "tasso_interesse", "rata_mensile", "data_inizio", "data_fine", "note",
]


def get_all_debiti():
    """Returns all debiti records ordered by importo_residuo DESC."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM debiti ORDER BY importo_residuo DESC"
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


def get_debito_by_id(id):
    """Returns a single debito record by id."""
    try:
        db = get_db()
        row = db.execute(
            "SELECT * FROM debiti WHERE id = ?", (id,)
        ).fetchone()
        db.close()
        if row is None:
            return {"error": "Record non trovato"}
        return dict(row)
    except Exception as e:
        return {"error": str(e)}


def create_debito(data):
    """Insert a new debito record."""
    try:
        db = get_db()
        placeholders = ", ".join(["?"] * len(DEBITI_FIELDS))
        columns = ", ".join(DEBITI_FIELDS)
        values = [data.get(f) for f in DEBITI_FIELDS]

        cursor = db.execute(
            f"INSERT INTO debiti ({columns}) VALUES ({placeholders})",
            values,
        )
        db.commit()
        new_id = cursor.lastrowid
        db.close()
        return {"id": new_id}
    except Exception as e:
        return {"error": str(e)}


def update_debito(id, data):
    """Update an existing debito record."""
    try:
        db = get_db()
        set_clause = ", ".join([f"{f} = ?" for f in DEBITI_FIELDS])
        values = [data.get(f) for f in DEBITI_FIELDS]
        values.append(id)

        db.execute(
            f"UPDATE debiti SET {set_clause} WHERE id = ?",
            values,
        )
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def delete_debito(id):
    """Delete a debito record by id."""
    try:
        db = get_db()
        db.execute("DELETE FROM debiti WHERE id = ?", (id,))
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def get_debiti_summary():
    """Returns debiti summary: totale_residuo, totale_rate_mensili, count, has_mutuo."""
    try:
        db = get_db()
        row = db.execute(
            """SELECT
                  SUM(importo_residuo) as totale_residuo,
                  SUM(rata_mensile) as totale_rate_mensili,
                  COUNT(*) as count
               FROM debiti"""
        ).fetchone()

        has_mutuo_row = db.execute(
            "SELECT COUNT(*) as cnt FROM debiti WHERE tipo = 'mutuo'"
        ).fetchone()

        db.close()

        result = dict(row)
        result["has_mutuo"] = dict(has_mutuo_row)["cnt"] > 0
        return result
    except Exception as e:
        return {"error": str(e)}

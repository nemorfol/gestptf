from database import get_db


FP_FIELDS = ["nome", "data", "valore", "contributo", "rendimento", "note"]


def get_all_fp():
    """Returns all fondo pensione records ordered by data DESC."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM fondo_pensione ORDER BY data DESC"
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


def get_fp_by_id(id):
    """Returns a single fondo pensione record by id."""
    try:
        db = get_db()
        row = db.execute(
            "SELECT * FROM fondo_pensione WHERE id = ?", (id,)
        ).fetchone()
        db.close()
        if row is None:
            return {"error": "Record non trovato"}
        return dict(row)
    except Exception as e:
        return {"error": str(e)}


def create_fp(data):
    """Insert a new fondo pensione record."""
    try:
        db = get_db()
        placeholders = ", ".join(["?"] * len(FP_FIELDS))
        columns = ", ".join(FP_FIELDS)
        values = [data.get(f) for f in FP_FIELDS]

        cursor = db.execute(
            f"INSERT INTO fondo_pensione ({columns}) VALUES ({placeholders})",
            values,
        )
        db.commit()
        new_id = cursor.lastrowid
        db.close()
        return {"id": new_id}
    except Exception as e:
        return {"error": str(e)}


def update_fp(id, data):
    """Update an existing fondo pensione record."""
    try:
        db = get_db()
        set_clause = ", ".join([f"{f} = ?" for f in FP_FIELDS])
        values = [data.get(f) for f in FP_FIELDS]
        values.append(id)

        db.execute(
            f"UPDATE fondo_pensione SET {set_clause} WHERE id = ?",
            values,
        )
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def delete_fp(id):
    """Delete a fondo pensione record by id."""
    try:
        db = get_db()
        db.execute("DELETE FROM fondo_pensione WHERE id = ?", (id,))
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def get_latest_fp():
    """Returns the most recent fondo pensione record."""
    try:
        db = get_db()
        row = db.execute(
            "SELECT * FROM fondo_pensione ORDER BY data DESC LIMIT 1"
        ).fetchone()
        db.close()
        if row is None:
            return {"error": "Nessun record trovato"}
        return dict(row)
    except Exception as e:
        return {"error": str(e)}


def get_fp_summary():
    """Returns fondo pensione summary: ultimo_valore, totale_contributi, rendimento_medio."""
    try:
        db = get_db()
        # Get latest value
        latest = db.execute(
            "SELECT valore FROM fondo_pensione ORDER BY data DESC LIMIT 1"
        ).fetchone()
        ultimo_valore = dict(latest)["valore"] if latest else 0

        # Get totals
        row = db.execute(
            """SELECT SUM(contributo) as totale_contributi,
                      AVG(rendimento) as rendimento_medio
               FROM fondo_pensione"""
        ).fetchone()
        db.close()

        result = dict(row)
        result["ultimo_valore"] = ultimo_valore
        result["valore_attuale"] = ultimo_valore
        return result
    except Exception as e:
        return {"error": str(e)}

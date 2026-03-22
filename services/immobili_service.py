from database import get_db


IMMOBILI_FIELDS = [
    "nome", "tipo", "indirizzo", "valore_stimato",
    "data_acquisto", "prezzo_acquisto", "rendita_annua", "note",
]


def get_all_immobili():
    """Returns all immobili records ordered by tipo, nome."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM immobili ORDER BY tipo, nome"
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


def get_immobile_by_id(id):
    """Returns a single immobile record by id."""
    try:
        db = get_db()
        row = db.execute(
            "SELECT * FROM immobili WHERE id = ?", (id,)
        ).fetchone()
        db.close()
        if row is None:
            return {"error": "Record non trovato"}
        return dict(row)
    except Exception as e:
        return {"error": str(e)}


def create_immobile(data):
    """Insert a new immobile record."""
    try:
        db = get_db()
        placeholders = ", ".join(["?"] * len(IMMOBILI_FIELDS))
        columns = ", ".join(IMMOBILI_FIELDS)
        values = [data.get(f) for f in IMMOBILI_FIELDS]

        cursor = db.execute(
            f"INSERT INTO immobili ({columns}) VALUES ({placeholders})",
            values,
        )
        db.commit()
        new_id = cursor.lastrowid
        db.close()
        return {"id": new_id}
    except Exception as e:
        return {"error": str(e)}


def update_immobile(id, data):
    """Update an existing immobile record."""
    try:
        db = get_db()
        set_clause = ", ".join([f"{f} = ?" for f in IMMOBILI_FIELDS])
        values = [data.get(f) for f in IMMOBILI_FIELDS]
        values.append(id)

        db.execute(
            f"UPDATE immobili SET {set_clause} WHERE id = ?",
            values,
        )
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def delete_immobile(id):
    """Delete an immobile record and its storico (cascade)."""
    try:
        db = get_db()
        db.execute("DELETE FROM immobili_storico WHERE immobile_id = ?", (id,))
        db.execute("DELETE FROM immobili WHERE id = ?", (id,))
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def get_storico_immobile(immobile_id):
    """Returns all storico records for a given immobile, ordered by data DESC."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM immobili_storico WHERE immobile_id = ? ORDER BY data DESC",
            (immobile_id,),
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


def add_valutazione(immobile_id, data, valore_stimato, note=None):
    """Insert a new valutazione into storico and update valore_stimato in immobili."""
    try:
        db = get_db()
        db.execute(
            """INSERT INTO immobili_storico (immobile_id, data, valore_stimato, note)
               VALUES (?, ?, ?, ?)""",
            (immobile_id, data, valore_stimato, note),
        )
        db.execute(
            "UPDATE immobili SET valore_stimato = ? WHERE id = ?",
            (valore_stimato, immobile_id),
        )
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def get_all_storico():
    """Returns storico for all immobili, grouped by immobile name."""
    try:
        db = get_db()
        rows = db.execute(
            """SELECT s.data, s.valore_stimato, i.nome, i.id as immobile_id
               FROM immobili_storico s
               JOIN immobili i ON i.id = s.immobile_id
               ORDER BY s.data ASC"""
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


def get_immobili_summary():
    """Returns summary totals for immobili."""
    try:
        db = get_db()
        row = db.execute(
            """SELECT
                  SUM(CASE WHEN tipo = 'estero' THEN valore_stimato ELSE 0 END) as totale_esteri,
                  SUM(CASE WHEN tipo = 'italia' THEN valore_stimato ELSE 0 END) as totale_italia,
                  SUM(valore_stimato) as totale,
                  COUNT(*) as count,
                  SUM(rendita_annua) as totale_rendita
               FROM immobili"""
        ).fetchone()
        db.close()
        result = dict(row)
        result["totale_complessivo"] = result.get("totale", 0)
        result["rendita_annua_totale"] = result.get("totale_rendita", 0)
        return result
    except Exception as e:
        return {"error": str(e)}


def get_totale_per_tipo():
    """Returns dict with 'estero' and 'italia' totals."""
    try:
        db = get_db()
        rows = db.execute(
            """SELECT tipo, SUM(valore_stimato) as totale
               FROM immobili
               GROUP BY tipo"""
        ).fetchall()
        db.close()
        result = {"estero": 0, "italia": 0}
        for r in rows:
            row = dict(r)
            if row["tipo"] in result:
                result[row["tipo"]] = row["totale"] or 0
        return result
    except Exception as e:
        return {"error": str(e)}

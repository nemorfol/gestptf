from database import get_db


def get_all_bond():
    """Returns all bond records ordered by data_acquisto DESC."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM bond ORDER BY data_acquisto DESC"
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


def get_bond_by_id(id):
    """Returns a single bond record by id."""
    try:
        db = get_db()
        row = db.execute("SELECT * FROM bond WHERE id = ?", (id,)).fetchone()
        db.close()
        if row is None:
            return {"error": "Record non trovato"}
        return dict(row)
    except Exception as e:
        return {"error": str(e)}


def create_bond(data):
    """Insert a new bond record. Calculates uscita_per_calcolo automatically."""
    try:
        uscita = float(data.get("uscita", 0))
        uscita_per_calcolo = abs(uscita) if uscita < 0 else uscita

        db = get_db()
        cursor = db.execute(
            """INSERT INTO bond (isin, nome, data_acquisto, quantita,
               prezzo_acquisto, commissioni, rateo_lordo, ritenuta_rateo,
               ritenuta_dis, uscita, uscita_per_calcolo, coeff_indicizz)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["isin"],
                data["nome"],
                data["data_acquisto"],
                float(data.get("quantita", 0)),
                float(data.get("prezzo_acquisto", 0)),
                float(data.get("commissioni", 0)),
                float(data.get("rateo_lordo", 0)),
                float(data.get("ritenuta_rateo", 0)),
                float(data.get("ritenuta_dis", 0)),
                uscita,
                uscita_per_calcolo,
                float(data.get("coeff_indicizz", 0)),
            ),
        )
        db.commit()
        new_id = cursor.lastrowid
        db.close()
        return {"id": new_id, "uscita_per_calcolo": uscita_per_calcolo}
    except Exception as e:
        return {"error": str(e)}


def update_bond(id, data):
    """Update an existing bond record. Supports partial update (e.g. attivo only)."""
    try:
        # Partial update for attivo field only
        if list(data.keys()) == ["attivo"]:
            db = get_db()
            db.execute("UPDATE bond SET attivo = ? WHERE id = ?", (int(data["attivo"]), id))
            db.commit()
            db.close()
            return {"success": True}

        uscita = float(data.get("uscita", 0))
        uscita_per_calcolo = abs(uscita) if uscita < 0 else uscita

        db = get_db()
        db.execute(
            """UPDATE bond SET isin = ?, nome = ?, data_acquisto = ?,
               quantita = ?, prezzo_acquisto = ?, commissioni = ?,
               rateo_lordo = ?, ritenuta_rateo = ?, ritenuta_dis = ?,
               uscita = ?, uscita_per_calcolo = ?, coeff_indicizz = ?
               WHERE id = ?""",
            (
                data["isin"],
                data["nome"],
                data["data_acquisto"],
                float(data.get("quantita", 0)),
                float(data.get("prezzo_acquisto", 0)),
                float(data.get("commissioni", 0)),
                float(data.get("rateo_lordo", 0)),
                float(data.get("ritenuta_rateo", 0)),
                float(data.get("ritenuta_dis", 0)),
                uscita,
                uscita_per_calcolo,
                float(data.get("coeff_indicizz", 0)),
                id,
            ),
        )
        db.commit()
        db.close()
        return {"success": True, "uscita_per_calcolo": uscita_per_calcolo}
    except Exception as e:
        return {"error": str(e)}


def delete_bond(id):
    """Delete a bond record by id."""
    try:
        db = get_db()
        db.execute("DELETE FROM bond WHERE id = ?", (id,))
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def get_bond_riepilogo():
    """GROUP BY isin, nome: sum quantita, weight % per ISIN. Only active bonds."""
    try:
        db = get_db()
        rows = db.execute(
            """SELECT isin, nome,
                      SUM(quantita) AS totale_quantita,
                      SUM(uscita_per_calcolo) AS totale_uscita
               FROM bond
               WHERE attivo = 1
               GROUP BY isin, nome
               ORDER BY totale_uscita DESC"""
        ).fetchall()
        db.close()

        risultati = [dict(r) for r in rows]
        totale_investito = sum(r["totale_uscita"] for r in risultati)

        for r in risultati:
            r["peso_pct"] = (
                round(r["totale_uscita"] / totale_investito * 100, 2)
                if totale_investito > 0
                else 0
            )

        return risultati
    except Exception as e:
        return {"error": str(e)}


def get_bond_summary():
    """Returns total invested and total count of active bond records."""
    try:
        db = get_db()
        row = db.execute(
            """SELECT COUNT(*) AS totale_count,
                      COALESCE(SUM(uscita_per_calcolo), 0) AS totale_investito
               FROM bond WHERE attivo = 1"""
        ).fetchone()
        db.close()
        return {
            "totale_investito": row["totale_investito"],
            "totale_count": row["totale_count"],
        }
    except Exception as e:
        return {"error": str(e)}

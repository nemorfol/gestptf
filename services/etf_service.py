from database import get_db


def get_all_etf():
    """Returns all ETF records ordered by data_acquisto DESC."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM etf ORDER BY data_acquisto DESC"
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


def get_etf_by_id(id):
    """Returns a single ETF record by id."""
    try:
        db = get_db()
        row = db.execute("SELECT * FROM etf WHERE id = ?", (id,)).fetchone()
        db.close()
        if row is None:
            return {"error": "Record non trovato"}
        return dict(row)
    except Exception as e:
        return {"error": str(e)}


def create_etf(data):
    """Insert a new ETF record. Calculates costo_totale automatically."""
    try:
        quantita = float(data.get("quantita", 0))
        prezzo_acquisto = float(data.get("prezzo_acquisto", 0))
        commissioni = float(data.get("commissioni", 0))
        costo_totale = quantita * prezzo_acquisto + commissioni

        db = get_db()
        cursor = db.execute(
            """INSERT INTO etf (isin, nome, data_acquisto, quantita,
               prezzo_acquisto, commissioni, costo_totale)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                data["isin"],
                data["nome"],
                data["data_acquisto"],
                quantita,
                prezzo_acquisto,
                commissioni,
                costo_totale,
            ),
        )
        db.commit()
        new_id = cursor.lastrowid
        db.close()
        return {"id": new_id, "costo_totale": costo_totale}
    except Exception as e:
        return {"error": str(e)}


def update_etf(id, data):
    """Update an existing ETF record. Supports partial update (e.g. attivo only)."""
    try:
        # Partial update for attivo field only
        if list(data.keys()) == ["attivo"]:
            db = get_db()
            db.execute("UPDATE etf SET attivo = ? WHERE id = ?", (int(data["attivo"]), id))
            db.commit()
            db.close()
            return {"success": True}

        quantita = float(data.get("quantita", 0))
        prezzo_acquisto = float(data.get("prezzo_acquisto", 0))
        commissioni = float(data.get("commissioni", 0))
        costo_totale = quantita * prezzo_acquisto + commissioni

        db = get_db()
        db.execute(
            """UPDATE etf SET isin = ?, nome = ?, data_acquisto = ?,
               quantita = ?, prezzo_acquisto = ?, commissioni = ?,
               costo_totale = ? WHERE id = ?""",
            (
                data["isin"],
                data["nome"],
                data["data_acquisto"],
                quantita,
                prezzo_acquisto,
                commissioni,
                costo_totale,
                id,
            ),
        )
        db.commit()
        db.close()
        return {"success": True, "costo_totale": costo_totale}
    except Exception as e:
        return {"error": str(e)}


def delete_etf(id):
    """Delete an ETF record by id."""
    try:
        db = get_db()
        db.execute("DELETE FROM etf WHERE id = ?", (id,))
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def get_etf_riepilogo():
    """GROUP BY isin, nome: sum quantita, sum costo_totale, weight % per ISIN. Only active."""
    try:
        db = get_db()
        rows = db.execute(
            """SELECT isin, nome,
                      SUM(quantita) AS totale_quantita,
                      SUM(costo_totale) AS totale_costo
               FROM etf
               WHERE attivo = 1
               GROUP BY isin, nome
               ORDER BY totale_costo DESC"""
        ).fetchall()
        db.close()

        risultati = [dict(r) for r in rows]
        totale_investito = sum(r["totale_costo"] for r in risultati)

        for r in risultati:
            r["peso_pct"] = (
                round(r["totale_costo"] / totale_investito * 100, 2)
                if totale_investito > 0
                else 0
            )

        return risultati
    except Exception as e:
        return {"error": str(e)}


def get_etf_summary():
    """Returns total invested and total count of active ETF records."""
    try:
        db = get_db()
        row = db.execute(
            """SELECT COUNT(*) AS totale_count,
                      COALESCE(SUM(costo_totale), 0) AS totale_investito
               FROM etf WHERE attivo = 1"""
        ).fetchone()
        db.close()
        return {
            "totale_investito": row["totale_investito"],
            "totale_count": row["totale_count"],
        }
    except Exception as e:
        return {"error": str(e)}

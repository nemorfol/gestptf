from database import get_db

FIELDS = [
    "anno", "data", "mese", "liquidita_entrata", "importo_cd",
    "importo_bfpi", "liquidita_accumulata", "accumulo_bsf",
    "accumulo_bfpi", "pct_bfpi", "accumulo_cd", "pct_cd",
    "accumulo_altro", "pct_altro", "totale_bsf", "totale_altro",
    "mesi_passati",
]

# Fields the user enters manually (the rest are calculated)
INPUT_FIELDS = [
    "data", "liquidita_entrata", "importo_cd", "importo_bfpi",
    "accumulo_bsf", "accumulo_bfpi", "accumulo_cd", "accumulo_altro",
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


def _parse_date(dt):
    """Extract anno and mese from a date string."""
    dt = str(dt or "")
    anno = int(dt[:4]) if len(dt) >= 4 else 0
    mese = int(dt[5:7]) if len(dt) >= 7 else 0
    return anno, mese


def create_liquidita(data):
    """Insert a new liquidita record, then recalculate derived fields."""
    try:
        db = get_db()

        dt = data.get("data", "")
        anno, mese = _parse_date(dt)

        # For accumulo_bfpi / accumulo_cd: if not provided, compute from previous + importo
        acc_bfpi = data.get("accumulo_bfpi")
        acc_cd = data.get("accumulo_cd")

        if acc_bfpi is None or acc_bfpi == "":
            prev = db.execute(
                "SELECT accumulo_bfpi, accumulo_cd FROM investimento_liquidita ORDER BY data DESC LIMIT 1"
            ).fetchone()
            prev_bfpi = prev["accumulo_bfpi"] if prev else 0
            prev_cd = prev["accumulo_cd"] if prev else 0
            acc_bfpi = (prev_bfpi or 0) + float(data.get("importo_bfpi", 0))
            if acc_cd is None or acc_cd == "":
                imp_cd = float(data.get("importo_cd", 0))
                if mese in (3, 9) and prev_cd:
                    acc_cd = (prev_cd or 0) / 2.0 + imp_cd
                else:
                    acc_cd = (prev_cd or 0) + imp_cd

        cursor = db.execute(
            """INSERT INTO investimento_liquidita
               (anno, data, mese, liquidita_entrata, importo_cd, importo_bfpi,
                liquidita_accumulata, accumulo_bsf, accumulo_bfpi, pct_bfpi,
                accumulo_cd, pct_cd, accumulo_altro, pct_altro,
                totale_bsf, totale_altro, mesi_passati)
               VALUES (?,?,?,?,?,?,0,?,?,0,?,0,?,0,0,0,0)""",
            (
                anno, dt, mese,
                float(data.get("liquidita_entrata", 0)),
                float(data.get("importo_cd", 0)),
                float(data.get("importo_bfpi", 0)),
                float(data.get("accumulo_bsf", 0)),
                float(acc_bfpi or 0),
                float(acc_cd or 0),
                float(data.get("accumulo_altro", 0)),
            ),
        )
        db.commit()
        new_id = cursor.lastrowid
        db.close()

        recalculate_derived()
        return {"id": new_id}
    except Exception as e:
        return {"error": str(e)}


def update_liquidita(id, data):
    """Update user-input fields, then recalculate derived fields."""
    try:
        db = get_db()

        dt = data.get("data", "")
        anno, mese = _parse_date(dt)

        db.execute(
            """UPDATE investimento_liquidita
               SET anno=?, data=?, mese=?, liquidita_entrata=?,
                   importo_cd=?, importo_bfpi=?,
                   accumulo_bsf=?, accumulo_bfpi=?, accumulo_cd=?, accumulo_altro=?
               WHERE id=?""",
            (
                anno, dt, mese,
                float(data.get("liquidita_entrata", 0)),
                float(data.get("importo_cd", 0)),
                float(data.get("importo_bfpi", 0)),
                float(data.get("accumulo_bsf", 0)),
                float(data.get("accumulo_bfpi", 0)),
                float(data.get("accumulo_cd", 0)),
                float(data.get("accumulo_altro", 0)),
                id,
            ),
        )
        db.commit()
        db.close()

        recalculate_derived()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def delete_liquidita(id):
    """Delete a liquidita record by id, then recalculate."""
    try:
        db = get_db()
        db.execute("DELETE FROM investimento_liquidita WHERE id = ?", (id,))
        db.commit()
        db.close()
        recalculate_derived()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def recalculate_derived():
    """Recalculate ONLY derived fields, preserving user-entered values.

    Derived fields (auto-calculated):
      - anno, mese          (from data)
      - liquidita_accumulata (G = entrata + prev_G - bsf - altro)
      - pct_bfpi, pct_cd, pct_altro  (percentages)
      - totale_bsf           (running sum of accumulo_bsf)
      - totale_altro          (running sum of accumulo_altro)
      - mesi_passati          (row counter)

    User-entered fields (NOT touched):
      - data, liquidita_entrata, importo_cd, importo_bfpi,
        accumulo_bsf, accumulo_bfpi, accumulo_cd, accumulo_altro
    """
    try:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM investimento_liquidita ORDER BY data ASC"
        ).fetchall()
        records = [dict(r) for r in rows]

        prev_liq_acc = 0.0
        tot_bsf = 0.0
        tot_altro = 0.0

        for i, rec in enumerate(records):
            anno, mese = _parse_date(rec["data"])

            bsf = rec["accumulo_bsf"] or 0
            altro = rec["accumulo_altro"] or 0
            entrata = rec["liquidita_entrata"] or 0
            acc_bfpi = rec["accumulo_bfpi"] or 0
            acc_cd = rec["accumulo_cd"] or 0

            # Running totals
            tot_bsf += bsf
            tot_altro += altro

            # Liquidita Accumulata: entrata + prev - bsf - altro
            if i == 0:
                liq_acc = entrata
            else:
                liq_acc = entrata + prev_liq_acc - bsf - altro

            # Percentages: based on accumulo_bfpi, accumulo_cd, totale_altro
            denom = acc_bfpi + acc_cd + tot_altro
            pct_bfpi = (acc_bfpi / denom) if denom > 0 else 0
            pct_cd = (acc_cd / denom) if denom > 0 else 0
            pct_altro = (tot_altro / denom) if denom > 0 else 0

            db.execute(
                """UPDATE investimento_liquidita
                   SET anno=?, mese=?, liquidita_accumulata=?,
                       pct_bfpi=?, pct_cd=?, pct_altro=?,
                       totale_bsf=?, totale_altro=?, mesi_passati=?
                   WHERE id=?""",
                (
                    anno, mese,
                    round(liq_acc, 2),
                    round(pct_bfpi, 10),
                    round(pct_cd, 10),
                    round(pct_altro, 10),
                    round(tot_bsf, 2),
                    round(tot_altro, 2),
                    i,
                    rec["id"],
                ),
            )

            prev_liq_acc = liq_acc

        db.commit()
        db.close()
    except Exception as e:
        print(f"Errore recalculate_derived: {e}")


def get_liquidita_summary():
    """Returns totals and latest values for liquidita."""
    try:
        db = get_db()
        row = db.execute(
            """SELECT
                COUNT(*) AS totale_count,
                COALESCE(SUM(liquidita_entrata), 0) AS totale_liquidita_entrata,
                COALESCE(SUM(liquidita_accumulata), 0) AS totale_liquidita_accumulata
            FROM investimento_liquidita"""
        ).fetchone()

        result = dict(row) if row else {}

        latest = db.execute(
            "SELECT * FROM investimento_liquidita ORDER BY data DESC LIMIT 1"
        ).fetchone()
        db.close()

        if latest:
            result["ultimo_totale_bsf"] = latest["totale_bsf"]
            result["ultimo_totale_altro"] = latest["totale_altro"]
            result["ultima_liquidita_accumulata"] = latest["liquidita_accumulata"]

        return result
    except Exception as e:
        return {"error": str(e)}


def generate_piano(importo_mensile, pct_bsf, pct_bfpi, pct_cd, pct_altro,
                   data_inizio, num_mesi):
    """Generate N months of projected savings plan, replacing existing records."""
    try:
        parts = data_inizio.split('-')
        start_year = int(parts[0])
        start_month = int(parts[1])

        db = get_db()
        db.execute("DELETE FROM investimento_liquidita")
        db.commit()
        db.close()

        acc_bfpi = 0.0
        acc_cd = 0.0

        for i in range(num_mesi):
            month = (start_month + i - 1) % 12 + 1
            year = start_year + (start_month + i - 1) // 12

            bsf_mese = round(importo_mensile * pct_bsf / 100, 2)
            bfpi_mese = round(importo_mensile * pct_bfpi / 100, 2)
            cd_mese = round(importo_mensile * pct_cd / 100, 2)
            altro_mese = round(importo_mensile * pct_altro / 100, 2)

            acc_bfpi += bfpi_mese
            if month in (3, 9) and i > 0:
                acc_cd = acc_cd / 2.0 + cd_mese
            else:
                acc_cd += cd_mese

            db = get_db()
            db.execute(
                """INSERT INTO investimento_liquidita
                   (anno, data, mese, liquidita_entrata, importo_cd, importo_bfpi,
                    accumulo_bsf, accumulo_bfpi, accumulo_cd, accumulo_altro)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (year, f"{year}-{month:02d}-01", month, importo_mensile,
                 cd_mese, bfpi_mese, bsf_mese, round(acc_bfpi, 2),
                 round(acc_cd, 2), altro_mese),
            )
            db.commit()
            db.close()

        recalculate_derived()
        return {"success": True, "count": num_mesi}
    except Exception as e:
        return {"error": str(e)}


def clear_piano():
    """Delete all piano records."""
    try:
        db = get_db()
        db.execute("DELETE FROM investimento_liquidita")
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

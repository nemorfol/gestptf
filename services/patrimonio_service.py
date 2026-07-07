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


def get_vrp_impatto_record(data_record):
    """Calculate the cumulative VRP impact for a patrimonio record at a given date.

    Returns a dict with:
        - has_vrp: True if there is at least one VRP active at that date
        - delta_immobile_italia: amount to apply to immobile_italia (negative = sold property)
        - delta_immobili_esteri: same for esteri
        - cash_aggiuntivo: cash to add from anticipo + rate
        - delta_netto: net impact on totale_netto
        - dettagli: list of per-VRP details
    """
    try:
        from services.simulatore_service import get_vrp_attive, calcola_vrp_a_data

        vrp_list = get_vrp_attive()
        if isinstance(vrp_list, dict) and "error" in vrp_list:
            return {"has_vrp": False, "delta_immobile_italia": 0,
                    "delta_immobili_esteri": 0, "cash_aggiuntivo": 0,
                    "delta_netto": 0, "dettagli": []}

        if not vrp_list:
            return {"has_vrp": False, "delta_immobile_italia": 0,
                    "delta_immobili_esteri": 0, "cash_aggiuntivo": 0,
                    "delta_netto": 0, "dettagli": []}

        delta_italia = 0.0
        delta_esteri = 0.0
        cash_aggiuntivo = 0.0
        dettagli = []
        attive_alla_data = False

        for vrp in vrp_list:
            data_inizio = vrp.get("data_inizio_piano") or vrp.get("data_simulazione")
            if not data_inizio:
                continue
            # VRP not yet started at the record's date → no impact
            if str(data_record)[:10] < str(data_inizio)[:10]:
                continue

            attive_alla_data = True
            stato = calcola_vrp_a_data(vrp, data_record)
            valore_vendita = float(vrp.get("valore_vendita", 0))
            credito_residuo = stato["credito_residuo"]
            totale_incassato = stato["totale_incassato"]

            # Delta = credito_residuo - valore_vendita (assuming user enters pre-VRP values)
            delta = credito_residuo - valore_vendita
            tipo = (vrp.get("immobile_tipo") or "italia").lower()
            if tipo == "estero" or tipo == "esteri":
                delta_esteri += delta
            else:
                delta_italia += delta

            cash_aggiuntivo += totale_incassato

            dettagli.append({
                "nome": vrp.get("nome", ""),
                "immobile_nome": vrp.get("immobile_nome", ""),
                "immobile_tipo": tipo,
                "credito_residuo": credito_residuo,
                "totale_incassato": totale_incassato,
                "valore_vendita": valore_vendita,
                "mesi_trascorsi": stato["mesi_trascorsi"],
                "piano_completato": stato["piano_completato"],
            })

        delta_netto = delta_italia + delta_esteri + cash_aggiuntivo

        return {
            "has_vrp": attive_alla_data,
            "delta_immobile_italia": round(delta_italia, 2),
            "delta_immobili_esteri": round(delta_esteri, 2),
            "cash_aggiuntivo": round(cash_aggiuntivo, 2),
            "delta_netto": round(delta_netto, 2),
            "dettagli": dettagli,
        }
    except Exception as e:
        return {"has_vrp": False, "delta_immobile_italia": 0,
                "delta_immobili_esteri": 0, "cash_aggiuntivo": 0,
                "delta_netto": 0, "dettagli": [], "error": str(e)}


def get_patrimonio_totali(record, vrp_impatto=None):
    """Calculate totale, totale_netto (- debiti), totale_adj (-20% immobili).

    If vrp_impatto is provided (dict from get_vrp_impatto_record), also computes
    the VRP-adjusted variants:
      - totale_con_vrp, totale_netto_con_vrp, totale_adj_con_vrp

    Returns dict.
    """
    try:
        totale = sum(float(record.get(f, 0)) for f in ASSET_FIELDS)
        debiti = float(record.get("debiti", 0))
        totale_netto = totale - debiti

        immobili = float(record.get("immobili_esteri", 0)) + float(
            record.get("immobile_italia", 0)
        )
        totale_adj = totale_netto - (immobili * 0.20)

        result = {
            "totale": round(totale, 2),
            "totale_netto": round(totale_netto, 2),
            "totale_adj": round(totale_adj, 2),
        }

        if vrp_impatto and vrp_impatto.get("has_vrp"):
            delta_italia = vrp_impatto.get("delta_immobile_italia", 0)
            delta_esteri = vrp_impatto.get("delta_immobili_esteri", 0)
            cash_extra = vrp_impatto.get("cash_aggiuntivo", 0)
            delta_netto = vrp_impatto.get("delta_netto", 0)

            totale_con_vrp = totale + delta_italia + delta_esteri + cash_extra
            totale_netto_con_vrp = totale_con_vrp - debiti

            # Adjusted immobili (after VRP)
            immobili_con_vrp = (
                float(record.get("immobili_esteri", 0)) + delta_esteri
                + float(record.get("immobile_italia", 0)) + delta_italia
            )
            totale_adj_con_vrp = totale_netto_con_vrp - (immobili_con_vrp * 0.20)

            result["totale_con_vrp"] = round(totale_con_vrp, 2)
            result["totale_netto_con_vrp"] = round(totale_netto_con_vrp, 2)
            result["totale_adj_con_vrp"] = round(totale_adj_con_vrp, 2)
            result["vrp_delta_netto"] = round(delta_netto, 2)
            result["vrp_has"] = True
        else:
            result["totale_con_vrp"] = result["totale"]
            result["totale_netto_con_vrp"] = result["totale_netto"]
            result["totale_adj_con_vrp"] = result["totale_adj"]
            result["vrp_delta_netto"] = 0
            result["vrp_has"] = False

        return result
    except Exception as e:
        return {"error": str(e)}


def _sum_rendita_annua():
    """Somma le rendite annue (affitti) dichiarate sugli immobili."""
    try:
        db = get_db()
        row = db.execute(
            "SELECT COALESCE(SUM(rendita_annua), 0) AS r FROM immobili"
        ).fetchone()
        db.close()
        return float(row["r"] or 0) if row else 0.0
    except Exception:
        return 0.0


def build_fire_export():
    """Costruisce l'export 'patrimonio-italiano' v1 per FIRE Planner (fire20)
    a partire dallo snapshot piu' recente della tabella `patrimonio`.

    Mappa i campi asset di GestPTF sulle chiavi PortfolioAllocation di FIRE
    Planner: `bfp` e `cd` mappano 1:1 (FIRE Planner ha asset class dedicate).
    Gli immobili sono aggregati in `realEstate`; il dettaglio per singolo
    titolo/ISIN e' intenzionalmente omesso (FIRE Planner ragiona per classi).

    Esporta SOLO la riga piu' recente di `patrimonio` (MAI patrimonio + tabelle
    di dettaglio insieme, per non raddoppiare il netto).
    """
    latest = get_latest_patrimonio()
    if isinstance(latest, dict) and "error" in latest:
        return latest

    def g(k):
        return float(latest.get(k, 0) or 0)

    assets = {
        "stocks": round(g("etf"), 2),
        "bonds": round(g("btp"), 2),
        "bfp": round(g("bfp"), 2),
        "cd": round(g("cd"), 2),
        "cash": round(g("cash"), 2),
        "realEstate": round(g("immobili_esteri") + g("immobile_italia"), 2),
        "gold": 0,
        "crypto": 0,
        "pensionFund": round(g("fondo_pensione"), 2),
        "tfr": round(g("tfr_netto"), 2),
        "other": 0,
    }

    return {
        "format": "patrimonio-italiano",
        "version": 1,
        "app": "gestptf",
        "asOf": str(latest.get("data", ""))[:10],
        "currency": "EUR",
        "assets": assets,
        "debts": round(g("debiti"), 2),
        "rentalIncomeAnnual": round(_sum_rendita_annua(), 2),
        "meta": {
            "realEstateBreakdown": {
                "italia": round(g("immobile_italia"), 2),
                "estero": round(g("immobili_esteri"), 2),
            },
            "bondsBreakdown": {
                "btp": round(g("btp"), 2),
                "bfp": round(g("bfp"), 2),
                "cd": round(g("cd"), 2),
            },
        },
    }


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
    """Returns list of records with variazione % vs first record (using VRP-adjusted values)."""
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
        vrp_primo = get_vrp_impatto_record(primo["data"])
        totali_primo = get_patrimonio_totali(primo, vrp_primo)

        if "error" in totali_primo:
            return {"error": totali_primo["error"]}

        # Use VRP-adjusted totale_netto as baseline
        base = totali_primo["totale_netto_con_vrp"]

        risultati = []
        for record in records:
            vrp_imp = get_vrp_impatto_record(record["data"])
            totali = get_patrimonio_totali(record, vrp_imp)
            if "error" in totali:
                continue
            corrente = totali["totale_netto_con_vrp"]
            variazione = (
                round((corrente - base) / base * 100, 2) if base > 0 else 0
            )
            record["totale_netto"] = totali["totale_netto"]
            record["totale_netto_con_vrp"] = corrente
            record["vrp_delta_netto"] = totali.get("vrp_delta_netto", 0)
            record["variazione_pct"] = variazione
            risultati.append(record)

        return risultati
    except Exception as e:
        return {"error": str(e)}

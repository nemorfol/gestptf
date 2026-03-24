"""
BFP Calculator - Calculates redemption values, maturity values, and amortization schedules
for Buoni Fruttiferi Postali using imported coefficients.
"""

import re
from datetime import date, datetime
from database import get_db


def _parse_date(d):
    """Parse a date string or date object into a date object."""
    if isinstance(d, date):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(d, fmt).date()
            except ValueError:
                continue
    return None


def _calcola_anni_semestri(data_sottoscrizione, data_calcolo):
    """Calculate elapsed years and semesters between two dates.

    Returns:
        tuple (anni, semestri) where semestri is 0 or 1 (within the current year)
        and anni is the number of complete years.
        BFP interest is calculated on complete semesters only.
    """
    d1 = _parse_date(data_sottoscrizione)
    d2 = _parse_date(data_calcolo)
    if not d1 or not d2:
        return 0, 0

    if d2 < d1:
        return 0, 0

    total_months = (d2.year - d1.year) * 12 + (d2.month - d1.month)
    if d2.day < d1.day:
        total_months -= 1

    total_semestri = total_months // 6
    anni = total_semestri // 2
    semestri = total_semestri % 2

    return anni, semestri


def _get_coefficiente(serie, anni, semestri):
    """Look up the coefficient from bfp_coefficienti table for a given period.

    Finds the matching row for the exact (anni, semestri) or the closest
    previous period if no exact match exists.

    Returns:
        dict with coefficient data or None if not found.
    """
    db = get_db()

    # Try exact match first
    row = db.execute(
        """SELECT * FROM bfp_coefficienti
           WHERE serie = ? AND tipo_tabella = 'B' AND anni = ? AND semestri = ?
           LIMIT 1""",
        (serie, anni, semestri),
    ).fetchone()

    if row:
        db.close()
        return dict(row)

    # Try to find closest previous period (floor)
    # Convert to total semesters for comparison
    total_sem = anni * 2 + semestri
    row = db.execute(
        """SELECT * FROM bfp_coefficienti
           WHERE serie = ? AND tipo_tabella = 'B'
             AND (anni * 2 + semestri) <= ?
           ORDER BY (anni * 2 + semestri) DESC
           LIMIT 1""",
        (serie, total_sem),
    ).fetchone()

    db.close()

    if row:
        return dict(row)
    return None


def _get_max_coefficiente(serie):
    """Get the maximum period coefficient for a serie (maturity value).

    Returns:
        dict with coefficient data or None.
    """
    db = get_db()
    row = db.execute(
        """SELECT * FROM bfp_coefficienti
           WHERE serie = ? AND tipo_tabella = 'B'
           ORDER BY (anni * 2 + semestri) DESC
           LIMIT 1""",
        (serie,),
    ).fetchone()
    db.close()
    return dict(row) if row else None


def calcola_valore_rimborso(serie, valore_nominale, data_sottoscrizione, data_calcolo=None):
    """Calculate current redemption value of a BFP.

    Args:
        serie: Serie code (e.g. 'SF165A231115')
        valore_nominale: Nominal value in euros
        data_sottoscrizione: Subscription date
        data_calcolo: Calculation date (default: today)

    Returns:
        dict with: valore_lordo, valore_netto, ritenuta, coeff_lordo, coeff_netto,
                   tasso_lordo, tasso_netto, anni_trascorsi, semestri_trascorsi
        or dict with error key.
    """
    if data_calcolo is None:
        data_calcolo = date.today()

    if not serie:
        return {"error": "Serie non specificata"}

    valore_nominale = float(valore_nominale or 0)
    if valore_nominale <= 0:
        return {"error": "Valore nominale deve essere maggiore di zero"}

    anni, semestri = _calcola_anni_semestri(data_sottoscrizione, data_calcolo)

    coeff = _get_coefficiente(serie, anni, semestri)
    if not coeff:
        return {
            "error": f"Nessun coefficiente trovato per serie {serie} al periodo {anni} anni {semestri} semestri. "
                     "Importare prima i fogli informativi PDF.",
            "anni_trascorsi": anni,
            "semestri_trascorsi": semestri,
        }

    coeff_lordo = coeff["coeff_lordo"]
    coeff_netto = coeff["coeff_netto"]
    tasso_lordo = coeff.get("tasso_lordo", 0) or 0
    tasso_netto = coeff.get("tasso_netto", 0) or 0

    valore_lordo = round(valore_nominale * coeff_lordo, 2)
    valore_netto = round(valore_nominale * coeff_netto, 2)
    ritenuta = round(valore_lordo - valore_netto, 2)

    return {
        "valore_lordo": valore_lordo,
        "valore_netto": valore_netto,
        "ritenuta": ritenuta,
        "coeff_lordo": coeff_lordo,
        "coeff_netto": coeff_netto,
        "tasso_lordo": tasso_lordo,
        "tasso_netto": tasso_netto,
        "anni_trascorsi": anni,
        "semestri_trascorsi": semestri,
    }


def _get_coefficiente_accumulo(serie, eta_sottoscrizione):
    """Get the accumulation coefficient (Tabella A) for BSF/BO65 by age.

    Returns the coefficient for the maturity value at age 65.
    """
    eta_str = _eta_to_string(eta_sottoscrizione)
    db = get_db()

    # Try exact match on eta_da
    row = db.execute(
        """SELECT * FROM bfp_coefficienti
           WHERE serie = ? AND tipo_tabella = 'A' AND eta_da = ?
           LIMIT 1""",
        (serie, eta_str),
    ).fetchone()

    if not row:
        # Try bracket match
        rows = db.execute(
            """SELECT * FROM bfp_coefficienti
               WHERE serie = ? AND tipo_tabella = 'A' AND eta_da IS NOT NULL""",
            (serie,),
        ).fetchall()
        for r in rows:
            r_dict = dict(r)
            da_num = _eta_str_to_num(r_dict.get("eta_da"))
            a_num = _eta_str_to_num(r_dict.get("eta_a"))
            if da_num is not None and a_num is not None:
                if da_num <= eta_sottoscrizione < a_num:
                    row = r
                    break

    db.close()
    return dict(row) if row else None


def calcola_valore_scadenza(serie, valore_nominale, data_sottoscrizione):
    """Calculate maturity value of a BFP using maximum period coefficient.

    Args:
        serie: Serie code
        valore_nominale: Nominal value
        data_sottoscrizione: Subscription date (unused for this calc, kept for API consistency)

    Returns:
        dict with same structure as calcola_valore_rimborso, or dict with error.
    """
    if not serie:
        return {"error": "Serie non specificata"}

    valore_nominale = float(valore_nominale or 0)
    if valore_nominale <= 0:
        return {"error": "Valore nominale deve essere maggiore di zero"}

    coeff = _get_max_coefficiente(serie)
    if not coeff:
        return {
            "error": f"Nessun coefficiente trovato per serie {serie}. "
                     "Importare prima i fogli informativi PDF."
        }

    coeff_lordo = coeff["coeff_lordo"]
    coeff_netto = coeff["coeff_netto"]
    tasso_lordo = coeff.get("tasso_lordo", 0) or 0
    tasso_netto = coeff.get("tasso_netto", 0) or 0

    valore_lordo = round(valore_nominale * coeff_lordo, 2)
    valore_netto = round(valore_nominale * coeff_netto, 2)
    ritenuta = round(valore_lordo - valore_netto, 2)

    return {
        "valore_lordo": valore_lordo,
        "valore_netto": valore_netto,
        "ritenuta": ritenuta,
        "coeff_lordo": coeff_lordo,
        "coeff_netto": coeff_netto,
        "tasso_lordo": tasso_lordo,
        "tasso_netto": tasso_netto,
        "anni_scadenza": coeff.get("anni", 0),
        "semestri_scadenza": coeff.get("semestri", 0),
    }


def calcola_bollo(valore_rimborso_lordo, totale_bfp_lordo):
    """Calculate stamp duty (bollo) for a BFP.

    Rules:
    - Bollo is 0.20% per year (2 per mille) on the redemption value
    - BFP are EXEMPT if the TOTAL value of all BFP held by the same person
      is below €5,000 (calculated on the sum of all valore_lordo_attuale)

    Args:
        valore_rimborso_lordo: Current gross redemption value of this BFP
        totale_bfp_lordo: Total gross value of ALL BFP held

    Returns:
        float: annual stamp duty (0 if exempt)
    """
    SOGLIA_ESENZIONE = 5000.0
    ALIQUOTA_BOLLO = 0.002  # 0.20% = 2 per mille

    if totale_bfp_lordo < SOGLIA_ESENZIONE:
        return 0.0

    return round(valore_rimborso_lordo * ALIQUOTA_BOLLO, 2)


def calcola_tutti_bfp(data_nascita=None):
    """Recalculate current values for all BFP records in the database.

    Updates valore_lordo_attuale, ritenuta_fiscale, valore_rimborso_netto
    for each BFP based on its serie and subscription date.
    Also updates valore_lordo_scadenza, ritenuta_scadenza, valore_netto_scadenza.
    For BSF/BO65, uses Tabella A (age-based value at 65) if data_nascita is provided.
    Calculates bollo (stamp duty) with exemption for total < 5000€.

    Args:
        data_nascita: Birth date string (YYYY-MM-DD) for BSF/BO65 age calculation.

    Returns:
        list of updated BFP records, or dict with error.
    """
    try:
        nascita = None
        if data_nascita:
            try:
                nascita = _parse_date(data_nascita)
            except Exception:
                pass

        db = get_db()
        records = db.execute("SELECT * FROM bfp ORDER BY data_sottoscrizione DESC").fetchall()
        records = [dict(r) for r in records]

        updated = []
        oggi = date.today()

        # First pass: calculate all current values
        for bfp in records:
            serie = bfp.get("serie")
            valore_nominale = bfp.get("valore_nominale", 0) or 0

            if not serie or valore_nominale <= 0:
                bfp["bollo_annuo"] = 0.0
                updated.append(bfp)
                continue

            # Calculate current redemption value
            rimborso = calcola_valore_rimborso(
                serie, valore_nominale, bfp["data_sottoscrizione"], oggi
            )

            # Calculate maturity value
            # BSF/BO65: use Tabella A (age-based value at 65) if birth date available
            serie_upper = (serie or "").upper()
            is_rendita_type = serie_upper.startswith("BO165A") or serie_upper.startswith("SF165A")
            if is_rendita_type and nascita:
                ds = _parse_date(bfp["data_sottoscrizione"])
                if ds:
                    diff_months = (ds.year - nascita.year) * 12 + (ds.month - nascita.month)
                    if ds.day < nascita.day:
                        diff_months -= 1
                    eta_anni = diff_months // 12
                    eta_mesi = diff_months % 12
                    eta = eta_anni + 0.5 if eta_mesi >= 6 else float(eta_anni)
                    scadenza = calcola_valore_al_65(serie, valore_nominale, eta)
                else:
                    scadenza = calcola_valore_scadenza(
                        serie, valore_nominale, bfp["data_sottoscrizione"]
                    )
            else:
                scadenza = calcola_valore_scadenza(
                    serie, valore_nominale, bfp["data_sottoscrizione"]
                )

            # Update record
            update_fields = {}
            if "error" not in rimborso:
                update_fields["valore_lordo_attuale"] = rimborso["valore_lordo"]
                update_fields["ritenuta_fiscale"] = rimborso["ritenuta"]
                update_fields["valore_rimborso_netto"] = rimborso["valore_netto"]

            if "error" not in scadenza:
                update_fields["valore_lordo_scadenza"] = scadenza["valore_lordo"]
                update_fields["ritenuta_scadenza"] = scadenza["ritenuta"]
                update_fields["valore_netto_scadenza"] = scadenza["valore_netto"]

            if update_fields:
                set_clause = ", ".join([f"{k} = ?" for k in update_fields.keys()])
                values = list(update_fields.values())
                values.append(bfp["id"])
                db.execute(f"UPDATE bfp SET {set_clause} WHERE id = ?", values)
                bfp.update(update_fields)

            # Add calculation metadata
            if "error" not in rimborso:
                bfp["_calc_anni"] = rimborso["anni_trascorsi"]
                bfp["_calc_semestri"] = rimborso["semestri_trascorsi"]
                bfp["_calc_coeff_lordo"] = rimborso["coeff_lordo"]
                bfp["_calc_coeff_netto"] = rimborso["coeff_netto"]

            updated.append(bfp)

        # Second pass: calculate bollo using total of all BFP
        totale_lordo = sum(b.get("valore_lordo_attuale", 0) or 0 for b in updated)
        for bfp in updated:
            val_lordo = bfp.get("valore_lordo_attuale", 0) or 0
            bfp["bollo_annuo"] = calcola_bollo(val_lordo, totale_lordo)

        db.commit()
        db.close()
        return updated

    except Exception as e:
        return {"error": str(e)}


def _eta_to_string(eta):
    """Convert a numeric age (e.g. 42 or 42.5) to Italian format.

    42 -> '42 anni'
    42.5 -> '42 anni e 6 mesi'
    """
    eta = float(eta)
    anni = int(eta)
    if eta - anni >= 0.5:
        return f"{anni} anni e 6 mesi"
    return f"{anni} anni"


def calcola_valore_al_65(serie, valore_nominale, eta_sottoscrizione):
    """Calculate the value at age 65 for BSF/BO65 using Tabella A coefficients.

    Args:
        serie: Serie code
        valore_nominale: Nominal value
        eta_sottoscrizione: Age at subscription (e.g. 44 or 44.5)

    Returns:
        dict with valore_lordo, valore_netto, ritenuta, or dict with error.
    """
    if not serie or not eta_sottoscrizione:
        return {"error": "Serie o eta non specificata"}

    valore_nominale = float(valore_nominale or 0)
    eta_sottoscrizione = float(eta_sottoscrizione)
    eta_str = _eta_to_string(eta_sottoscrizione)

    db = get_db()

    # Try exact match on eta_da
    row = db.execute(
        """SELECT * FROM bfp_coefficienti
           WHERE serie = ? AND tipo_tabella = 'A' AND eta_da = ?
           LIMIT 1""",
        (serie, eta_str),
    ).fetchone()

    if not row:
        # Try bracket match
        rows = db.execute(
            """SELECT * FROM bfp_coefficienti
               WHERE serie = ? AND tipo_tabella = 'A'""",
            (serie,),
        ).fetchall()
        for r in rows:
            r_dict = dict(r)
            da_num = _eta_str_to_num(r_dict["eta_da"])
            a_num = _eta_str_to_num(r_dict["eta_a"])
            if da_num is not None and a_num is not None:
                if da_num <= eta_sottoscrizione < a_num:
                    row = r
                    break

    db.close()

    if not row:
        return {"error": f"Nessun coefficiente Tabella A per serie {serie} ed eta {eta_str}"}

    row = dict(row)
    coeff_lordo = row["coeff_lordo"]
    coeff_netto = row["coeff_netto"]
    valore_lordo = round(valore_nominale * coeff_lordo, 2)
    valore_netto = round(valore_nominale * coeff_netto, 2)

    return {
        "valore_lordo": valore_lordo,
        "valore_netto": valore_netto,
        "ritenuta": round(valore_lordo - valore_netto, 2),
        "coeff_lordo": coeff_lordo,
        "coeff_netto": coeff_netto,
    }


def calcola_rendita(serie, valore_nominale, eta_sottoscrizione):
    """Calculate monthly/annual rendita for BSF/BO65.

    The rendita is paid from age 65 to 80 (180 monthly payments).

    Args:
        serie: Serie code (must be BSF or BO65 type)
        valore_nominale: Nominal value of the BFP
        eta_sottoscrizione: Age at subscription (e.g. 42 or 42.5 for "42 anni e 6 mesi")

    Returns:
        dict with rata_mensile_lorda/netta, rata_annua_lorda/netta,
        totale_rendita_lorda/netta, coeff_rata, eta_da, eta_a,
        durata_rendita_mesi (180), durata_rendita_anni (15),
        or dict with error key.
    """
    if not serie:
        return {"error": "Serie non specificata"}

    valore_nominale = float(valore_nominale or 0)
    if valore_nominale <= 0:
        return {"error": "Valore nominale deve essere maggiore di zero"}

    if eta_sottoscrizione is None:
        return {"error": "Eta alla sottoscrizione non specificata"}

    eta_sottoscrizione = float(eta_sottoscrizione)
    eta_str = _eta_to_string(eta_sottoscrizione)

    db = get_db()

    # Look up coefficient from bfp_coefficienti where tipo_tabella='C'
    # Match on eta_da or eta_a containing the age string
    row = db.execute(
        """SELECT * FROM bfp_coefficienti
           WHERE serie = ? AND tipo_tabella = 'C'
             AND eta_da = ?
           LIMIT 1""",
        (serie, eta_str),
    ).fetchone()

    if not row:
        # Try matching on eta_a
        row = db.execute(
            """SELECT * FROM bfp_coefficienti
               WHERE serie = ? AND tipo_tabella = 'C'
                 AND eta_a = ?
               LIMIT 1""",
            (serie, eta_str),
        ).fetchone()

    if not row:
        # Try bracket match: eta_da <= eta <= eta_a
        # Fetch all C coefficients for this serie and match manually
        rows = db.execute(
            """SELECT * FROM bfp_coefficienti
               WHERE serie = ? AND tipo_tabella = 'C'""",
            (serie,),
        ).fetchall()

        for r in rows:
            r_dict = dict(r)
            # Parse eta_da and eta_a to numeric for comparison
            da_num = _eta_str_to_num(r_dict["eta_da"])
            a_num = _eta_str_to_num(r_dict["eta_a"])
            if da_num is not None and a_num is not None:
                if da_num <= eta_sottoscrizione < a_num:
                    row = r
                    break

    db.close()

    if not row:
        return {
            "error": f"Nessun coefficiente rendita (Tabella C) trovato per serie {serie} "
                     f"ed eta {eta_str}. Importare prima i fogli informativi PDF."
        }

    row = dict(row)
    coeff_lordo = row["coeff_lordo"]
    coeff_netto = row["coeff_netto"]

    rata_mensile_lorda = round(valore_nominale * coeff_lordo, 2)
    rata_mensile_netta = round(valore_nominale * coeff_netto, 2)
    rata_annua_lorda = round(rata_mensile_lorda * 12, 2)
    rata_annua_netta = round(rata_mensile_netta * 12, 2)
    totale_rendita_lorda = round(rata_mensile_lorda * 180, 2)
    totale_rendita_netta = round(rata_mensile_netta * 180, 2)

    return {
        "rata_mensile_lorda": rata_mensile_lorda,
        "rata_mensile_netta": rata_mensile_netta,
        "rata_annua_lorda": rata_annua_lorda,
        "rata_annua_netta": rata_annua_netta,
        "totale_rendita_lorda": totale_rendita_lorda,
        "totale_rendita_netta": totale_rendita_netta,
        "coeff_rata": coeff_lordo,
        "coeff_rata_netto": coeff_netto,
        "eta_da": row["eta_da"],
        "eta_a": row["eta_a"],
        "durata_rendita_mesi": 180,
        "durata_rendita_anni": 15,
    }


def _eta_str_to_num(eta_str):
    """Convert Italian age string to numeric value.

    '42 anni' -> 42.0
    '42 anni e 6 mesi' -> 42.5
    """
    if not eta_str:
        return None
    m = re.match(r"(\d+)\s+anni(?:\s+e\s+6\s+mesi)?", eta_str)
    if not m:
        return None
    val = float(m.group(1))
    if "6 mesi" in eta_str:
        val += 0.5
    return val


def get_piano_rimborso(serie, valore_nominale, data_sottoscrizione):
    """Generate full amortization/interest schedule for a BFP.

    For each semester until maturity, shows coefficient and calculated values.

    Args:
        serie: Serie code
        valore_nominale: Nominal value
        data_sottoscrizione: Subscription date

    Returns:
        dict with 'piano' (list of period entries) and 'riepilogo', or dict with error.
    """
    if not serie:
        return {"error": "Serie non specificata"}

    valore_nominale = float(valore_nominale or 0)
    if valore_nominale <= 0:
        return {"error": "Valore nominale deve essere maggiore di zero"}

    db = get_db()
    rows = db.execute(
        """SELECT * FROM bfp_coefficienti
           WHERE serie = ? AND tipo_tabella = 'B'
           ORDER BY anni, semestri""",
        (serie,),
    ).fetchall()
    db.close()

    if not rows:
        return {
            "error": f"Nessun coefficiente trovato per serie {serie}. "
                     "Importare prima i fogli informativi PDF."
        }

    piano = []
    for row in rows:
        r = dict(row)
        coeff_lordo = r["coeff_lordo"]
        coeff_netto = r["coeff_netto"]
        val_lordo = round(valore_nominale * coeff_lordo, 2)
        val_netto = round(valore_nominale * coeff_netto, 2)
        ritenuta = round(val_lordo - val_netto, 2)
        interessi_lordi = round(val_lordo - valore_nominale, 2)
        interessi_netti = round(val_netto - valore_nominale, 2)

        piano.append({
            "anni": r["anni"],
            "semestri": r["semestri"],
            "periodo_label": f"{r['anni']}a {r['semestri']}s",
            "coeff_lordo": coeff_lordo,
            "coeff_netto": coeff_netto,
            "valore_lordo": val_lordo,
            "valore_netto": val_netto,
            "ritenuta": ritenuta,
            "interessi_lordi": interessi_lordi,
            "interessi_netti": interessi_netti,
            "tasso_lordo": r.get("tasso_lordo", 0) or 0,
            "tasso_netto": r.get("tasso_netto", 0) or 0,
        })

    # Summary
    ultimo = piano[-1] if piano else {}
    riepilogo = {
        "serie": serie,
        "valore_nominale": valore_nominale,
        "data_sottoscrizione": str(data_sottoscrizione),
        "durata_massima_anni": ultimo.get("anni", 0),
        "durata_massima_semestri": ultimo.get("semestri", 0),
        "valore_lordo_scadenza": ultimo.get("valore_lordo", 0),
        "valore_netto_scadenza": ultimo.get("valore_netto", 0),
        "ritenuta_scadenza": ultimo.get("ritenuta", 0),
        "totale_periodi": len(piano),
    }

    # Check if this serie is BSF or BO65 (has rendita phase)
    serie_upper = serie.upper() if serie else ""
    has_rendita = serie_upper.startswith("BO165A") or serie_upper.startswith("SF165A")
    riepilogo["has_rendita"] = has_rendita

    return {
        "piano": piano,
        "riepilogo": riepilogo,
    }

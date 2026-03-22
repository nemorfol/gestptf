"""
Fineco Portfolio Export Importer

Parses Fineco .xls export files and maps them to GestPTF sections:
- ETF -> etf table + patrimonio.etf
- Obbligazione -> bond table + patrimonio.btp
- Cash/XEON -> patrimonio.cash / patrimonio.cd

The import can:
1. Update the ETF and Bond tables with current positions
2. Generate patrimonio values for the imported date
"""

import xlrd
from datetime import date
from database import get_db


# Column mapping from Fineco export
COL_TITOLO = 0
COL_ISIN = 1
COL_SIMBOLO = 2
COL_MERCATO = 3
COL_STRUMENTO = 4
COL_VALUTA = 5
COL_QUANTITA = 6
COL_PREZZO_CARICO = 7
COL_CAMBIO_CARICO = 8
COL_VALORE_CARICO = 9
COL_PREZZO_MERCATO = 10
COL_CAMBIO_MERCATO = 11
COL_VALORE_MERCATO = 12
COL_VAR_PCT = 13
COL_VAR_EUR = 14
COL_VAR_VALUTA = 15
COL_RATEO = 16

# ISIN patterns for classification
XEON_ISINS = ["LU0290358497"]  # Xtrackers EUR Overnight Rate Swap

# ISIN mapping: old emission ISIN -> current market ISIN
# Some BTP change ISIN when they move from emission to secondary market
ISIN_ALIASES = {
    "IT0005547408": "IT0005547390",  # BTP-VAL 13GN27 -> BTP-13GN27 VALSU CUM
    "IT0005532723": "IT0005532715",  # BTP-ITALIA 14MZ28CUM -> BTP-14MZ28 ITALIACUM
}


def parse_fineco_xls(filepath):
    """Parse a Fineco portfolio export .xls file.

    Returns dict with:
        - etf: list of ETF positions
        - bond: list of bond positions
        - totale_etf: total ETF market value
        - totale_btp: total bond market value
        - totale_cash_xeon: total XEON value (treated as liquidity)
        - errors: list of parsing errors
    """
    try:
        wb = xlrd.open_workbook(filepath)
    except Exception as e:
        return {"error": f"Errore apertura file: {e}"}

    ws = wb.sheet_by_index(0)

    etf_positions = []
    bond_positions = []
    errors = []

    # Find header row (contains "ISIN")
    header_row = None
    for r in range(min(ws.nrows, 10)):
        for c in range(ws.ncols):
            if str(ws.cell_value(r, c)).upper().strip() == "ISIN":
                header_row = r
                break
        if header_row is not None:
            break

    if header_row is None:
        return {"error": "Header row con 'ISIN' non trovato nel file"}

    # Parse data rows
    for r in range(header_row + 1, ws.nrows):
        titolo = str(ws.cell_value(r, COL_TITOLO)).strip()
        isin = str(ws.cell_value(r, COL_ISIN)).strip()
        strumento = str(ws.cell_value(r, COL_STRUMENTO)).strip()

        if not isin or isin.lower() == "isin" or titolo.lower() == "totale":
            continue

        try:
            quantita = float(ws.cell_value(r, COL_QUANTITA) or 0)
            prezzo_carico = float(ws.cell_value(r, COL_PREZZO_CARICO) or 0)
            valore_carico = float(ws.cell_value(r, COL_VALORE_CARICO) or 0)
            prezzo_mercato = float(ws.cell_value(r, COL_PREZZO_MERCATO) or 0)
            valore_mercato = float(ws.cell_value(r, COL_VALORE_MERCATO) or 0)
            rateo = float(ws.cell_value(r, COL_RATEO) or 0)
        except (ValueError, TypeError) as e:
            errors.append(f"Riga {r + 1}: errore parsing valori per {titolo}: {e}")
            continue

        position = {
            "titolo": titolo,
            "isin": isin,
            "strumento": strumento,
            "quantita": quantita,
            "prezzo_carico": prezzo_carico,
            "valore_carico": round(valore_carico, 2),
            "prezzo_mercato": prezzo_mercato,
            "valore_mercato": round(valore_mercato, 2),
            "rateo": round(rateo, 2),
        }

        if strumento.upper() == "ETF":
            # Classify XEON as cash/CD, not ETF
            position["is_xeon"] = isin in XEON_ISINS
            etf_positions.append(position)
        elif strumento.upper() in ("OBBLIGAZIONE", "BOND"):
            bond_positions.append(position)
        else:
            errors.append(f"Riga {r + 1}: strumento non riconosciuto '{strumento}' per {titolo}")

    # Calculate totals
    totale_etf = round(sum(
        p["valore_mercato"] for p in etf_positions if not p.get("is_xeon")
    ), 2)
    totale_xeon = round(sum(
        p["valore_mercato"] for p in etf_positions if p.get("is_xeon")
    ), 2)
    totale_btp = round(sum(p["valore_mercato"] for p in bond_positions), 2)

    return {
        "etf": etf_positions,
        "bond": bond_positions,
        "totale_etf": totale_etf,
        "totale_btp": totale_btp,
        "totale_cash_xeon": totale_xeon,
        "totale_portafoglio": round(totale_etf + totale_xeon + totale_btp, 2),
        "errors": errors,
    }


def import_fineco_to_db(parsed_data, data_import=None, update_positions=True):
    """Import parsed Fineco data into GestPTF database.

    Args:
        parsed_data: result from parse_fineco_xls
        data_import: date for the import (default: today)
        update_positions: if True, update ETF and Bond tables

    Returns dict with import results.
    """
    if "error" in parsed_data:
        return parsed_data

    if data_import is None:
        data_import = date.today().isoformat()

    db = get_db()
    results = {
        "data": data_import,
        "etf_updated": 0,
        "etf_created": 0,
        "bond_updated": 0,
        "bond_created": 0,
        "patrimonio_values": {},
    }

    if update_positions:
        # Update/create ETF positions (skip XEON)
        for pos in parsed_data["etf"]:
            if pos.get("is_xeon"):
                continue

            existing = db.execute(
                "SELECT id FROM etf WHERE isin = ?", (pos["isin"],)
            ).fetchone()

            if existing:
                db.execute(
                    """UPDATE etf SET nome = ?, quantita = ?, prezzo_acquisto = ?,
                       costo_totale = ? WHERE isin = ?""",
                    (pos["titolo"], pos["quantita"], pos["prezzo_carico"],
                     pos["valore_carico"], pos["isin"]),
                )
                results["etf_updated"] += 1
            else:
                db.execute(
                    """INSERT INTO etf (isin, nome, data_acquisto, quantita,
                       prezzo_acquisto, commissioni, costo_totale)
                       VALUES (?, ?, ?, ?, ?, 0, ?)""",
                    (pos["isin"], pos["titolo"], data_import,
                     pos["quantita"], pos["prezzo_carico"], pos["valore_carico"]),
                )
                results["etf_created"] += 1

        # Update/create Bond positions
        for pos in parsed_data["bond"]:
            # Check both current ISIN and aliases
            existing = db.execute(
                "SELECT id FROM bond WHERE isin = ?", (pos["isin"],)
            ).fetchone()
            if not existing:
                # Check if any existing bond has an old ISIN that maps to this one
                for old_isin, new_isin in ISIN_ALIASES.items():
                    if new_isin == pos["isin"]:
                        existing = db.execute(
                            "SELECT id FROM bond WHERE isin = ?", (old_isin,)
                        ).fetchone()
                        if existing:
                            # Update the old ISIN to the new one
                            db.execute("UPDATE bond SET isin = ? WHERE id = ?",
                                       (pos["isin"], existing["id"]))
                            break

            uscita_calc = round(pos["quantita"] * pos["prezzo_carico"] / 100, 2)

            if existing:
                db.execute(
                    """UPDATE bond SET nome = ?, quantita = ?, prezzo_acquisto = ?,
                       rateo_lordo = ?, uscita_per_calcolo = ?, uscita = ? WHERE isin = ?""",
                    (pos["titolo"], pos["quantita"], pos["prezzo_carico"],
                     pos["rateo"], uscita_calc, uscita_calc, pos["isin"]),
                )
                results["bond_updated"] += 1
            else:
                db.execute(
                    """INSERT INTO bond (isin, nome, data_acquisto, quantita,
                       prezzo_acquisto, commissioni, rateo_lordo, uscita, uscita_per_calcolo)
                       VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)""",
                    (pos["isin"], pos["titolo"], data_import,
                     pos["quantita"], pos["prezzo_carico"], pos["rateo"],
                     uscita_calc, uscita_calc),
                )
                results["bond_created"] += 1

    db.commit()
    db.close()

    # Update existing patrimonio record at this date if it exists
    db = get_db()
    existing_pat = db.execute(
        "SELECT id FROM patrimonio WHERE data = ? OR data = ?",
        (data_import, data_import + " 00:00:00"),
    ).fetchone()
    if existing_pat:
        db.execute(
            "UPDATE patrimonio SET etf = ?, btp = ?, cd = ? WHERE id = ?",
            (parsed_data["totale_etf"], parsed_data["totale_btp"],
             parsed_data["totale_cash_xeon"], existing_pat["id"]),
        )
        db.commit()
        results["patrimonio_updated"] = True
    db.close()

    # Save patrimonio values from Fineco in parametri for valori-live
    for chiave, valore in [
        ("fineco_etf", parsed_data["totale_etf"]),
        ("fineco_btp", parsed_data["totale_btp"]),
        ("fineco_cd", parsed_data["totale_cash_xeon"]),
        ("fineco_data", data_import),
    ]:
        db = get_db()
        existing = db.execute(
            "SELECT id FROM parametri WHERE chiave = ?", (chiave,)
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE parametri SET valore = ? WHERE chiave = ?",
                (str(valore), chiave),
            )
        else:
            db.execute(
                "INSERT INTO parametri (chiave, valore, descrizione, categoria) VALUES (?, ?, ?, ?)",
                (chiave, str(valore), f"Ultimo import Fineco - {chiave}", "fineco"),
            )
        db.commit()
        db.close()

    results["patrimonio_values"] = {
        "etf": parsed_data["totale_etf"],
        "btp": parsed_data["totale_btp"],
        "cd": parsed_data["totale_cash_xeon"],
    }

    return results

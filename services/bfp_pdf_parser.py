"""
BFP PDF Parser - Parses "fogli informativi" PDFs to extract coefficient tables.

Extracts Tabella B (rimborso anticipato) and Tabella A (al 65 anno) from
Buoni Fruttiferi Postali information sheets.
"""

import os
import re
from database import get_db


# Mapping of serie code prefixes to tipologia names
SERIE_TIPOLOGIA_MAP = {
    "BO165A": "Buono Obiettivo 65",
    "SF165A": "Buono Soluzione Futuro",
    "IL110A": "Buono Indicizzato Inflazione Italiana",
    "TC005A": "Buono a Cedola",
    "TF004A": "Buono Premium 4 anni",
    "TF106M": "Buono 6 mesi",
    "TF120A": "Buono Ordinario 20 anni",
    "TF212A": "Buono 3x4",
    "TF504A": "Buono 4 Anni",
    "TF604A": "Buono Rinnova 4 anni",
    "TF904A": "Buono 100",
    "EL107A": "Buono Risparmio Sostenibile",
    "TF116A": "Buono 4x4",
}


def _parse_italian_number(s):
    """Convert Italian number format (comma as decimal) to float.
    E.g. '1,00751877' -> 1.00751877, '0,25%' -> 0.25
    """
    if s is None:
        return 0.0
    s = str(s).strip().replace("%", "").replace(" ", "")
    if not s:
        return 0.0
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _extract_serie_from_filename(filepath):
    """Extract serie code from PDF filename.
    E.g. 'fi-SF165A231115-240625.pdf' -> 'SF165A231115'
    """
    basename = os.path.basename(filepath)
    # Remove .pdf extension
    name = os.path.splitext(basename)[0]
    # Remove 'fi-' prefix
    if name.lower().startswith("fi-"):
        name = name[3:]
    # The serie code is the first part before any dash
    parts = name.split("-")
    if parts:
        return parts[0].upper()
    return name.upper()


def _get_tipologia(serie, text):
    """Determine tipologia from serie code or PDF text content."""
    serie_upper = serie.upper()
    for prefix, tipologia in SERIE_TIPOLOGIA_MAP.items():
        if serie_upper.startswith(prefix):
            return tipologia

    # Try to extract from text
    tipologia_patterns = [
        r"Buono\s+(?:fruttifero\s+postale\s+)?(?:dedicato\s+ai\s+minori\s+)?([\w\s]+?)(?:\s*\n|\s*-|\s*\.)",
        r'"(Buono[^"]+)"',
    ]
    for pattern in tipologia_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return serie


def _extract_durata_massima(text):
    """Extract maximum duration from PDF text.
    Looks for patterns like 'durata massima di 20 anni' or 'durata 4 anni'.
    """
    patterns = [
        r"durata\s+(?:massima\s+)?(?:di\s+)?(\d+)\s+anni",
        r"(\d+)\s+anni\s+dalla\s+data\s+di\s+sottoscrizione",
        r"scadenza\s+(?:al\s+)?(\d+).?\s*anno",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0


def _extract_tabella_b(text):
    """Extract Tabella B (rimborso anticipato) coefficients.

    Pattern: anni semestri coeff_lordo coeff_netto tasso_lordo% tasso_netto%
    E.g.: '3 0 1,00751877 1,00657892 0,25% 0,22%'
    Also handles: '0 1 1,00000000 1,00000000 0,00% 0,00%'
    """
    coefficienti = []

    # Pattern for standard Tabella B rows
    # anni semestri coeff_lordo coeff_netto tasso_lordo% tasso_netto%
    pattern = re.compile(
        r"^\s*(\d+)\s+(\d+)\s+"
        r"(\d+[,\.]\d+)\s+"
        r"(\d+[,\.]\d+)\s+"
        r"(\d+[,\.]\d+)\s*%?\s+"
        r"(\d+[,\.]\d+)\s*%?",
        re.MULTILINE,
    )

    for match in pattern.finditer(text):
        anni = int(match.group(1))
        semestri = int(match.group(2))
        coeff_lordo = _parse_italian_number(match.group(3))
        coeff_netto = _parse_italian_number(match.group(4))
        tasso_lordo = _parse_italian_number(match.group(5))
        tasso_netto = _parse_italian_number(match.group(6))

        coefficienti.append({
            "anni": anni,
            "semestri": semestri,
            "coeff_lordo": coeff_lordo,
            "coeff_netto": coeff_netto,
            "tasso_lordo": tasso_lordo,
            "tasso_netto": tasso_netto,
        })

    # If no results, try alternative format (Ordinario, 4x4, Indicizzato, etc.)
    # Format: "anni mesi coeff_lordo coeff_netto" (no tasso columns)
    # Multiple triplets per line, e.g.: "0 0 1,00000000 1,00000000 6 8 1,09432 1,08253 ..."
    if not coefficienti:
        alt_pattern = re.compile(
            r"(\d{1,2})\s*(\d{1,2})\s+"
            r"(\d+[,\.]\d{4,})\s+"
            r"(\d+[,\.]\d{4,})"
        )
        for match in alt_pattern.finditer(text):
            anni = int(match.group(1))
            mesi = int(match.group(2))
            coeff_lordo = _parse_italian_number(match.group(3))
            coeff_netto = _parse_italian_number(match.group(4))
            # Convert months to semesters (0-1)
            semestri = 1 if mesi >= 6 else 0
            # Skip duplicates and obviously wrong entries
            if coeff_lordo < 0.5 or coeff_lordo > 10:
                continue
            coefficienti.append({
                "anni": anni,
                "semestri": semestri,
                "coeff_lordo": coeff_lordo,
                "coeff_netto": coeff_netto,
                "tasso_lordo": 0,
                "tasso_netto": 0,
            })

    return coefficienti


def _extract_tabella_a(text):
    """Extract Tabella A (al 65 anno) age-based coefficients.

    Pattern: 'eta_da eta_a coeff_lordo coeff_netto tasso_lordo% tasso_netto%'
    E.g.: '18 anni 18 anni e 6 mesi 1,03456 1,02345 3,45% 2,34%'
    Also handles: 'da 18 anni a 18 anni e 6 mesi ...'
    """
    coefficienti = []

    # Pattern for age-based rows
    pattern = re.compile(
        r"(\d+\s+anni(?:\s+e\s+6\s+mesi)?)\s+"
        r"(\d+\s+anni(?:\s+e\s+6\s+mesi)?)\s+"
        r"(\d+[,\.]\d+)\s+"
        r"(\d+[,\.]\d+)\s+"
        r"(\d+[,\.]\d+)\s*%?\s+"
        r"(\d+[,\.]\d+)\s*%?",
        re.MULTILINE,
    )

    for match in pattern.finditer(text):
        eta_da = match.group(1).strip()
        eta_a = match.group(2).strip()
        coeff_lordo = _parse_italian_number(match.group(3))
        coeff_netto = _parse_italian_number(match.group(4))
        tasso_lordo = _parse_italian_number(match.group(5))
        tasso_netto = _parse_italian_number(match.group(6))

        coefficienti.append({
            "eta_da": eta_da,
            "eta_a": eta_a,
            "coeff_lordo": coeff_lordo,
            "coeff_netto": coeff_netto,
            "tasso_lordo": tasso_lordo,
            "tasso_netto": tasso_netto,
        })

    return coefficienti


def _extract_tabella_c(text):
    """Extract Tabella C (rata rendita) coefficients for BSF/BO65.

    These are single coefficients per age bracket used to calculate monthly
    annuity payments from age 65 to 80. The coefficients are small numbers
    (typically 0.009-0.015) unlike Tabella A coefficients (typically > 1.0).

    Pattern in PDF: 'eta_da eta_a coeff_rata_lordo'
    E.g.: '54 anni e 6 mesi 55 anni 0,00921235'

    Two columns may appear side by side on the same line.
    """
    coefficienti = []

    # Pattern for a single age-bracket + coefficient triplet.
    # We match all occurrences of: age_from age_to coefficient
    # where coefficient is a small number (< 0.1, i.e. starts with 0,0...)
    pattern = re.compile(
        r"(\d+\s+anni(?:\s+e\s+6\s+mesi)?)\s+"
        r"(\d+\s+anni(?:\s+e\s+6\s+mesi)?)\s+"
        r"(\d+[,\.]\d{6,})",
        re.MULTILINE,
    )

    # Collect all matches with their positions so we can exclude Tabella A matches
    # Tabella A lines have 4 numeric values + 2 percentages after the age pair,
    # while Tabella C lines have only 1 coefficient.
    # Strategy: match the pattern, then check if the coefficient is < 0.1
    # (Tabella C rata coefficients are ~0.009-0.015, Tabella A montante coefficients are > 1.0)
    for match in pattern.finditer(text):
        eta_da = match.group(1).strip()
        eta_a = match.group(2).strip()
        coeff_value = _parse_italian_number(match.group(3))

        # Filter: Tabella C coefficients are small (< 0.1), Tabella A are > 1.0
        if coeff_value < 0.1:
            coefficienti.append({
                "eta_da": eta_da,
                "eta_a": eta_a,
                "coeff_lordo": coeff_value,
            })

    return coefficienti


def parse_bfp_pdf(filepath):
    """Parse a BFP foglio informativo PDF and extract coefficient tables.

    Args:
        filepath: Path to the PDF file.

    Returns:
        dict with keys: serie, tipologia, tabella_b, tabella_a, durata_massima, error (if any)
    """
    try:
        import PyPDF2
    except ImportError:
        try:
            import pypdf as PyPDF2
        except ImportError:
            return {"error": "PyPDF2 o pypdf non installato. Installare con: pip install PyPDF2"}

    if not os.path.exists(filepath):
        return {"error": f"File non trovato: {filepath}"}

    try:
        text = ""
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        if not text.strip():
            return {"error": f"Impossibile estrarre testo dal PDF: {filepath}"}

        serie = _extract_serie_from_filename(filepath)
        tipologia = _get_tipologia(serie, text)
        durata_massima = _extract_durata_massima(text)

        tabella_b = _extract_tabella_b(text)
        tabella_a = _extract_tabella_a(text)
        tabella_c = _extract_tabella_c(text)

        # If no duration found, infer from tabella_b
        if durata_massima == 0 and tabella_b:
            last = tabella_b[-1]
            durata_massima = last["anni"]
            if last["semestri"] > 0:
                durata_massima += 1

        return {
            "serie": serie,
            "tipologia": tipologia,
            "tabella_b": tabella_b,
            "tabella_a": tabella_a,
            "tabella_c": tabella_c,
            "durata_massima": durata_massima,
        }

    except Exception as e:
        return {"error": f"Errore parsing PDF {filepath}: {str(e)}"}


def import_all_bfp_pdfs(pdf_dir):
    """Scan pdf_dir for BFP PDF files, parse each, and store coefficients in DB.

    Clears existing coefficients for each serie before importing.

    Args:
        pdf_dir: Directory containing BFP PDF files.

    Returns:
        dict with summary: total files processed, coefficients imported per serie, errors.
    """
    if not os.path.isdir(pdf_dir):
        return {"error": f"Directory non trovata: {pdf_dir}"}

    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]
    if not pdf_files:
        return {"error": f"Nessun file PDF trovato in: {pdf_dir}"}

    db = get_db()
    results = []
    total_coefficienti = 0
    errors = []

    for pdf_file in sorted(pdf_files):
        filepath = os.path.join(pdf_dir, pdf_file)
        parsed = parse_bfp_pdf(filepath)

        if "error" in parsed:
            errors.append({"file": pdf_file, "error": parsed["error"]})
            continue

        serie = parsed["serie"]
        tipologia = parsed["tipologia"]
        durata_massima = parsed["durata_massima"]

        # Clear existing coefficients for this serie
        db.execute("DELETE FROM bfp_coefficienti WHERE serie = ?", (serie,))

        count = 0

        # Insert Tabella B coefficients
        for row in parsed["tabella_b"]:
            db.execute(
                """INSERT INTO bfp_coefficienti
                   (serie, tipologia, tipo_tabella, anni, semestri,
                    coeff_lordo, coeff_netto, tasso_lordo, tasso_netto, durata_massima)
                   VALUES (?, ?, 'B', ?, ?, ?, ?, ?, ?, ?)""",
                (
                    serie, tipologia, row["anni"], row["semestri"],
                    row["coeff_lordo"], row["coeff_netto"],
                    row["tasso_lordo"], row["tasso_netto"],
                    durata_massima,
                ),
            )
            count += 1

        # Insert Tabella A coefficients (age-based, for BSF/BO65)
        for row in parsed["tabella_a"]:
            db.execute(
                """INSERT INTO bfp_coefficienti
                   (serie, tipologia, tipo_tabella, eta_da, eta_a,
                    coeff_lordo, coeff_netto, tasso_lordo, tasso_netto, durata_massima)
                   VALUES (?, ?, 'A', ?, ?, ?, ?, ?, ?, ?)""",
                (
                    serie, tipologia, row["eta_da"], row["eta_a"],
                    row["coeff_lordo"], row["coeff_netto"],
                    row["tasso_lordo"], row["tasso_netto"],
                    durata_massima,
                ),
            )
            count += 1

        # Insert Tabella C coefficients (rata rendita, for BSF/BO65)
        # NOTE: PDF Tabella C coefficients are already NETTI (net of 12.5% tax)
        # as stated: "Coefficienti per la determinazione della rata netta"
        for row in parsed["tabella_c"]:
            coeff_netto = row["coeff_lordo"]  # The extracted value IS the net coefficient
            coeff_lordo = round(coeff_netto / 0.875, 10)  # Gross = net / (1 - 12.5%)
            db.execute(
                """INSERT INTO bfp_coefficienti
                   (serie, tipologia, tipo_tabella, eta_da, eta_a,
                    coeff_lordo, coeff_netto, tasso_lordo, tasso_netto, durata_massima)
                   VALUES (?, ?, 'C', ?, ?, ?, ?, 0, 0, ?)""",
                (
                    serie, tipologia, row["eta_da"], row["eta_a"],
                    coeff_lordo, coeff_netto,
                    durata_massima,
                ),
            )
            count += 1

        total_coefficienti += count
        results.append({
            "file": pdf_file,
            "serie": serie,
            "tipologia": tipologia,
            "coefficienti_importati": count,
            "tabella_b": len(parsed["tabella_b"]),
            "tabella_a": len(parsed["tabella_a"]),
            "tabella_c": len(parsed["tabella_c"]),
            "durata_massima": durata_massima,
        })

    db.commit()
    db.close()

    return {
        "success": True,
        "files_processati": len(results),
        "totale_coefficienti": total_coefficienti,
        "dettaglio": results,
        "errori": errors,
    }


def get_coefficienti_serie(serie):
    """Return all coefficients for a given serie from DB.

    Args:
        serie: The serie code (e.g. 'SF165A231115').

    Returns:
        list of dicts with coefficient data, or dict with error.
    """
    try:
        db = get_db()
        rows = db.execute(
            """SELECT * FROM bfp_coefficienti
               WHERE serie = ?
               ORDER BY tipo_tabella, anni, semestri""",
            (serie,),
        ).fetchall()
        db.close()

        if not rows:
            return {"error": f"Nessun coefficiente trovato per la serie: {serie}"}

        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}

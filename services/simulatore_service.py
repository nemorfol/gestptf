from database import get_db


def simula_bsf_vs_bfp(importo, tasso_bsf, tasso_bfp_ord, anni):
    """Simulate BSF vs BFP using compound interest.

    BSF = importo * (1 + tasso_bsf/100)^anno
    BFP = importo * (1 + tasso_bfp_ord/100)^anno

    Returns list of dicts {anno, importo_bsf, importo_bfp_ord, differenza}.
    """
    try:
        importo = float(importo)
        tasso_bsf = float(tasso_bsf)
        tasso_bfp_ord = float(tasso_bfp_ord)
        anni = int(anni)

        risultati = []
        for anno in range(1, anni + 1):
            importo_bsf = importo * (1 + tasso_bsf / 100) ** anno
            importo_bfp_ord = importo * (1 + tasso_bfp_ord / 100) ** anno
            differenza = importo_bsf - importo_bfp_ord

            risultati.append({
                "anno": anno,
                "importo_bsf": round(importo_bsf, 2),
                "importo_bfp_ord": round(importo_bfp_ord, 2),
                "differenza": round(differenza, 2),
            })

        return risultati
    except Exception as e:
        return {"error": str(e)}


def simula_btpi(
    valore_nominale,
    quotazione,
    coeff_indicizz,
    inflazione_prevista,
    anno_rimborso,
    anno_corrente,
):
    """Project BTPi value over years until rimborso.

    Returns list of yearly projections.
    """
    try:
        valore_nominale = float(valore_nominale)
        quotazione = float(quotazione)
        coeff_indicizz = float(coeff_indicizz)
        inflazione_prevista = float(inflazione_prevista)
        anno_rimborso = int(anno_rimborso)
        anno_corrente = int(anno_corrente)

        risultati = []
        anni_rimanenti = anno_rimborso - anno_corrente

        for i in range(anni_rimanenti + 1):
            anno = anno_corrente + i
            coeff_proiettato = coeff_indicizz * (
                1 + inflazione_prevista / 100
            ) ** i
            valore_reale = valore_nominale * coeff_proiettato
            valore_mercato = valore_nominale * (quotazione / 100) * coeff_proiettato

            risultati.append({
                "anno": anno,
                "anni_al_rimborso": anni_rimanenti - i,
                "coeff_indicizz": round(coeff_proiettato, 6),
                "valore_reale": round(valore_reale, 2),
                "valore_mercato": round(valore_mercato, 2),
            })

        return risultati
    except Exception as e:
        return {"error": str(e)}


def calcola_rata_mensile_btpi(importo_netto, speranza_vita_anni):
    """Calculate monthly income from BTPi investment.

    monthly income = importo_netto / (speranza_vita_anni * 12)
    """
    try:
        importo_netto = float(importo_netto)
        speranza_vita_anni = float(speranza_vita_anni)

        if speranza_vita_anni <= 0:
            return {"error": "Speranza di vita deve essere maggiore di zero"}

        mesi_totali = speranza_vita_anni * 12
        rata_mensile = importo_netto / mesi_totali

        return {
            "importo_netto": round(importo_netto, 2),
            "speranza_vita_anni": speranza_vita_anni,
            "mesi_totali": int(mesi_totali),
            "rata_mensile": round(rata_mensile, 2),
        }
    except Exception as e:
        return {"error": str(e)}


def calcola_irpef(reddito_imponibile, reddito_base=0):
    """Calculate IRPEF using 2024-2026 Italian tax brackets.

    Args:
        reddito_imponibile: the additional income to tax (e.g. VRP installments)
        reddito_base: existing annual income (to determine marginal bracket)

    Returns dict with irpef, aliquota_marginale, aliquota_effettiva.
    """
    # Scaglioni IRPEF 2024-2026
    scaglioni = [
        (28000, 0.23),   # fino a 28.000€: 23%
        (50000, 0.35),   # da 28.001 a 50.000€: 35%
        (float("inf"), 0.43),  # oltre 50.000€: 43%
    ]

    def _irpef_su_reddito(reddito):
        imposta = 0
        precedente = 0
        for limite, aliquota in scaglioni:
            if reddito <= precedente:
                break
            imponibile_scaglione = min(reddito, limite) - precedente
            if imponibile_scaglione > 0:
                imposta += imponibile_scaglione * aliquota
            precedente = limite
        return round(imposta, 2)

    # IRPEF on base income alone
    irpef_base = _irpef_su_reddito(reddito_base)
    # IRPEF on base + additional income
    irpef_totale = _irpef_su_reddito(reddito_base + reddito_imponibile)
    # Marginal IRPEF = difference
    irpef_marginale = round(irpef_totale - irpef_base, 2)

    # Marginal rate
    aliquota_marginale = 0
    reddito_totale = reddito_base + reddito_imponibile
    for limite, aliquota in scaglioni:
        if reddito_totale <= limite:
            aliquota_marginale = aliquota
            break

    aliquota_effettiva = round(
        irpef_marginale / reddito_imponibile * 100, 2
    ) if reddito_imponibile > 0 else 0

    return {
        "irpef": irpef_marginale,
        "aliquota_marginale": aliquota_marginale * 100,
        "aliquota_effettiva": aliquota_effettiva,
    }


def simula_vendita_riserva(params):
    """Simulate sale with retention of title (vendita con riserva di proprietà).

    Calculates amortization schedule, taxes, cash flow, and comparison
    with immediate sale.
    """
    try:
        import datetime

        valore_vendita = float(params.get("valore_vendita", 0))
        prezzo_acquisto = float(params.get("prezzo_acquisto", 0))
        data_acquisto = params.get("data_acquisto", "")
        anticipo = float(params.get("anticipo", 0))
        durata_anni = int(params.get("durata_anni", 10))
        tasso_interesse = float(params.get("tasso_interesse", 3.0))
        spese_notarili = float(params.get("spese_notarili", 3000))
        aliquota_plusvalenza = float(params.get("aliquota_plusvalenza", 26))
        reddito_annuo = float(params.get("reddito_annuo", 0))
        addizionale_regionale = float(params.get("addizionale_regionale", 1.73))
        addizionale_comunale = float(params.get("addizionale_comunale", 0.8))
        imposta_registro = float(params.get("imposta_registro", 200))
        imu_annuale = float(params.get("imu_annuale", 0))
        costo_assicurazione = float(params.get("costo_assicurazione", 0))
        tasso_investimento = float(params.get("tasso_investimento", 3.0))

        # --- Ownership duration and capital gains tax ---
        oggi = datetime.date.today()
        anni_possesso = 0
        esente_plusvalenza = True
        if data_acquisto:
            dt_acquisto = datetime.datetime.strptime(
                data_acquisto[:10], "%Y-%m-%d"
            ).date()
            anni_possesso = (oggi - dt_acquisto).days / 365.25
            esente_plusvalenza = anni_possesso >= 5

        plusvalenza = max(valore_vendita - prezzo_acquisto, 0)
        imposta_plusvalenza = 0
        if not esente_plusvalenza and plusvalenza > 0:
            imposta_plusvalenza = round(plusvalenza * aliquota_plusvalenza / 100, 2)

        # --- French amortization schedule ---
        importo_finanziato = valore_vendita - anticipo
        n_mesi = durata_anni * 12

        if tasso_interesse == 0:
            rata_mensile = importo_finanziato / n_mesi if n_mesi > 0 else 0
        else:
            r = tasso_interesse / 100 / 12
            rata_mensile = importo_finanziato * r / (1 - (1 + r) ** (-n_mesi))

        rata_mensile = round(rata_mensile, 2)

        piano_ammortamento = []
        debito_residuo = importo_finanziato
        totale_interessi = 0

        for mese in range(1, n_mesi + 1):
            if tasso_interesse == 0:
                quota_interessi = 0
            else:
                quota_interessi = round(debito_residuo * tasso_interesse / 100 / 12, 2)
            quota_capitale = round(rata_mensile - quota_interessi, 2)

            # Last payment adjustment
            if mese == n_mesi:
                quota_capitale = round(debito_residuo, 2)
                rata_effettiva = quota_capitale + quota_interessi
            else:
                rata_effettiva = rata_mensile

            debito_residuo = round(debito_residuo - quota_capitale, 2)
            if debito_residuo < 0:
                debito_residuo = 0
            totale_interessi += quota_interessi

            anno = (mese - 1) // 12 + 1
            piano_ammortamento.append({
                "mese": mese,
                "anno": anno,
                "rata": round(rata_effettiva, 2),
                "quota_capitale": quota_capitale,
                "quota_interessi": round(quota_interessi, 2),
                "debito_residuo": debito_residuo,
            })

        totale_interessi = round(totale_interessi, 2)
        totale_rate = round(sum(p["rata"] for p in piano_ammortamento), 2)

        # --- Year-by-year cash flow ---
        costi_annuali = imposta_registro + imu_annuale + costo_assicurazione
        cash_flow_annuale = []
        flusso_cumulato = 0

        # --- Year-by-year cash flow with IRPEF ---
        totale_irpef = 0
        totale_addizionali = 0

        # Year 0: anticipo (not taxed as income - it's a capital payment)
        flusso_anno0 = anticipo - spese_notarili - imposta_plusvalenza
        flusso_cumulato = round(flusso_anno0, 2)
        cash_flow_annuale.append({
            "anno": 0,
            "entrate_rate": round(anticipo, 2),
            "spese_notarili": round(spese_notarili, 2),
            "imposta_plusvalenza": round(imposta_plusvalenza, 2),
            "imposta_registro": 0,
            "imu": 0,
            "assicurazione": 0,
            "irpef": 0,
            "addizionali": 0,
            "flusso_netto": round(flusso_anno0, 2),
            "flusso_cumulato": flusso_cumulato,
        })

        for anno in range(1, durata_anni + 1):
            rate_anno = [p for p in piano_ammortamento if p["anno"] == anno]
            entrate = round(sum(p["rata"] for p in rate_anno), 2)
            # Only interest portion is taxable income
            interessi_anno = round(sum(p["quota_interessi"] for p in rate_anno), 2)

            # IRPEF on interest income
            irpef_anno = 0
            addiz_anno = 0
            if reddito_annuo > 0 and interessi_anno > 0:
                irpef_result = calcola_irpef(interessi_anno, reddito_annuo)
                irpef_anno = irpef_result["irpef"]
                addiz_anno = round(
                    interessi_anno * (addizionale_regionale + addizionale_comunale) / 100, 2
                )
            elif interessi_anno > 0:
                # No base income: IRPEF on interest alone
                irpef_result = calcola_irpef(interessi_anno, 0)
                irpef_anno = irpef_result["irpef"]
                addiz_anno = round(
                    interessi_anno * (addizionale_regionale + addizionale_comunale) / 100, 2
                )

            totale_irpef += irpef_anno
            totale_addizionali += addiz_anno

            tasse_anno = irpef_anno + addiz_anno
            flusso_netto = round(entrate - costi_annuali - tasse_anno, 2)
            flusso_cumulato = round(flusso_cumulato + flusso_netto, 2)

            cash_flow_annuale.append({
                "anno": anno,
                "entrate_rate": entrate,
                "interessi_anno": interessi_anno,
                "spese_notarili": 0,
                "imposta_plusvalenza": 0,
                "imposta_registro": round(imposta_registro, 2),
                "imu": round(imu_annuale, 2),
                "assicurazione": round(costo_assicurazione, 2),
                "irpef": round(irpef_anno, 2),
                "addizionali": round(addiz_anno, 2),
                "flusso_netto": flusso_netto,
                "flusso_cumulato": flusso_cumulato,
            })

        totale_irpef = round(totale_irpef, 2)
        totale_addizionali = round(totale_addizionali, 2)

        # --- Totals ---
        totale_costi_annuali = round(costi_annuali * durata_anni, 2)
        totale_tasse = round(totale_irpef + totale_addizionali, 2)
        totale_costi = round(
            spese_notarili + imposta_plusvalenza + totale_costi_annuali + totale_tasse, 2
        )
        ricavo_netto_vrp = round(
            anticipo + totale_rate - totale_costi, 2
        )

        # --- Immediate sale comparison ---
        valore_vendita_immediata = float(params.get("valore_vendita_immediata", 0))
        if valore_vendita_immediata <= 0:
            valore_vendita_immediata = valore_vendita
        ricavo_immediato = round(
            valore_vendita_immediata - spese_notarili - imposta_plusvalenza, 2
        )

        # --- Opportunity cost: invest immediate proceeds ---
        confronto = []
        for anno in range(durata_anni + 1):
            valore_investito = round(
                ricavo_immediato * (1 + tasso_investimento / 100) ** anno, 2
            )
            cf = next((c for c in cash_flow_annuale if c["anno"] == anno), None)
            cumulato_vrp = cf["flusso_cumulato"] if cf else 0

            confronto.append({
                "anno": anno,
                "cumulato_vrp": cumulato_vrp,
                "cumulato_investimento": valore_investito,
            })

        valore_investito_finale = confronto[-1]["cumulato_investimento"]
        differenza_vrp_vs_immediata = round(
            ricavo_netto_vrp - ricavo_immediato, 2
        )
        differenza_vrp_vs_investito = round(
            ricavo_netto_vrp - valore_investito_finale, 2
        )

        # --- Break-even point: when VRP cumulated >= invested cumulated ---
        break_even_anno = None
        for c in confronto:
            if c["cumulato_vrp"] >= c["cumulato_investimento"] and c["anno"] > 0:
                break_even_anno = c["anno"]
                break
        # If VRP never catches up, no break-even
        if break_even_anno is None and confronto:
            # Check if VRP is ahead at any point
            for c in confronto[1:]:
                if c["cumulato_vrp"] >= c["cumulato_investimento"]:
                    break_even_anno = c["anno"]
                    break

        # Add difference column to confronto
        for c in confronto:
            c["differenza"] = round(c["cumulato_vrp"] - c["cumulato_investimento"], 2)

        # --- TIR (IRR) calculation ---
        # Cash flows: year 0 = -ricavo_immediato (opportunity cost of not selling immediately)
        # years 1..N = net cash flow from VRP each year
        tir = None
        try:
            irr_flows = [-ricavo_immediato]
            for anno in range(1, durata_anni + 1):
                cf = next((c for c in cash_flow_annuale if c["anno"] == anno), None)
                irr_flows.append(cf["flusso_netto"] if cf else 0)

            # Newton-Raphson IRR calculation
            def npv(rate, flows):
                return sum(f / (1 + rate) ** t for t, f in enumerate(flows))

            def npv_deriv(rate, flows):
                return sum(-t * f / (1 + rate) ** (t + 1) for t, f in enumerate(flows))

            guess = 0.05
            for _ in range(200):
                n = npv(guess, irr_flows)
                d = npv_deriv(guess, irr_flows)
                if abs(d) < 1e-12:
                    break
                new_guess = guess - n / d
                if abs(new_guess - guess) < 1e-10:
                    guess = new_guess
                    break
                guess = new_guess

            if abs(npv(guess, irr_flows)) < 1:
                tir = round(guess * 100, 2)
        except Exception:
            tir = None

        return {
            "riepilogo": {
                "valore_vendita": round(valore_vendita, 2),
                "valore_vendita_immediata": round(valore_vendita_immediata, 2),
                "prezzo_acquisto": round(prezzo_acquisto, 2),
                "anticipo": round(anticipo, 2),
                "importo_finanziato": round(importo_finanziato, 2),
                "anni_possesso": round(anni_possesso, 1),
                "esente_plusvalenza": esente_plusvalenza,
                "plusvalenza": round(plusvalenza, 2),
                "imposta_plusvalenza": imposta_plusvalenza,
                "rata_mensile": rata_mensile,
                "totale_rate": totale_rate,
                "totale_interessi": totale_interessi,
                "totale_costi": totale_costi,
                "totale_irpef": totale_irpef,
                "totale_addizionali": totale_addizionali,
                "totale_tasse_reddito": totale_tasse,
                "ricavo_netto_vrp": ricavo_netto_vrp,
                "ricavo_immediato": ricavo_immediato,
                "differenza_vrp_vs_immediata": differenza_vrp_vs_immediata,
                "valore_investito_finale": valore_investito_finale,
                "differenza_vrp_vs_investito": differenza_vrp_vs_investito,
                "break_even_anno": break_even_anno,
                "tir": tir,
            },
            "piano_ammortamento": piano_ammortamento,
            "cash_flow_annuale": cash_flow_annuale,
            "confronto": confronto,
        }
    except Exception as e:
        return {"error": str(e)}


def simula_sostenibilita(params):
    """Simulate portfolio sustainability over time.

    Takes current patrimonio, applies discount to immobili,
    subtracts a BSF investment, then projects how long the
    remaining liquid patrimony lasts given annual spending,
    inflation, and investment return.
    """
    try:
        patrimonio = params.get("patrimonio", {})
        sconto_esteri = float(params.get("sconto_esteri", 20))
        sconto_italia = float(params.get("sconto_italia", 20))
        investimento_bsf = float(params.get("investimento_bsf", 0))
        spesa_annuale = float(params.get("spesa_annuale", 20000))
        inflazione = float(params.get("inflazione", 3.0))
        rendimento = float(params.get("rendimento", 3.0))

        asset_keys = [
            "immobili_esteri", "immobile_italia", "fondo_pensione",
            "etf", "bfp", "btp", "cash", "cd", "tfr_netto",
        ]
        asset_labels = {
            "immobili_esteri": "Imm. Esteri",
            "immobile_italia": "Imm. Italia",
            "fondo_pensione": "Fondo Pens.",
            "etf": "ETF", "bfp": "BFP", "btp": "BTP",
            "cash": "Cash", "cd": "CD", "tfr_netto": "TFR Netto",
        }
        imm_illiquidi = ["immobili_esteri", "immobile_italia"]

        # --- Breakdown nominale e adjusted ---
        nominale = {}
        adjusted = {}
        for k in asset_keys:
            val = float(patrimonio.get(k, 0) or 0)
            nominale[k] = val
            if k == "immobili_esteri":
                adjusted[k] = round(val * (1 - sconto_esteri / 100), 2)
            elif k == "immobile_italia":
                adjusted[k] = round(val * (1 - sconto_italia / 100), 2)
            else:
                adjusted[k] = val

        tot_nominale = round(sum(nominale.values()), 2)
        tot_adjusted = round(sum(adjusted.values()), 2)

        # Percentuali
        pct_nominale = {}
        pct_adjusted = {}
        for k in asset_keys:
            pct_nominale[k] = round(nominale[k] / tot_nominale * 100, 2) if tot_nominale > 0 else 0
            pct_adjusted[k] = round(adjusted[k] / tot_adjusted * 100, 2) if tot_adjusted > 0 else 0

        # Tabella allocazione
        allocazione = []
        for k in asset_keys:
            allocazione.append({
                "asset": asset_labels[k],
                "key": k,
                "nominale": nominale[k],
                "pct_nominale": pct_nominale[k],
                "adjusted": adjusted[k],
                "pct_adjusted": pct_adjusted[k],
            })
        allocazione.append({
            "asset": "TOTALE",
            "key": "_totale",
            "nominale": tot_nominale,
            "pct_nominale": 100.0,
            "adjusted": tot_adjusted,
            "pct_adjusted": 100.0,
        })

        # --- Somma rimanente dopo investimento BSF ---
        somma_rimanente = round(tot_adjusted - investimento_bsf, 2)

        # Somma liquida (tutto tranne immobili adjusted)
        tot_immobili_adj = adjusted.get("immobili_esteri", 0) + adjusted.get("immobile_italia", 0)
        somma_liquida = round(tot_adjusted - tot_immobili_adj - investimento_bsf, 2)

        # --- Proiezione sostenibilità anno per anno ---
        proiezione = []
        capitale = somma_liquida
        spesa = spesa_annuale
        anno = 0

        proiezione.append({
            "anno": 0,
            "capitale_inizio": round(capitale, 2),
            "rendimento_anno": 0,
            "spesa_anno": 0,
            "capitale_fine": round(capitale, 2),
        })

        max_anni = 100  # safety limit
        while capitale > 0 and anno < max_anni:
            anno += 1
            rendimento_anno = round(capitale * rendimento / 100, 2)
            capitale_dopo_rend = capitale + rendimento_anno
            spesa = round(spesa_annuale * (1 + inflazione / 100) ** (anno - 1), 2)
            capitale_fine = round(capitale_dopo_rend - spesa, 2)

            proiezione.append({
                "anno": anno,
                "capitale_inizio": round(capitale, 2),
                "rendimento_anno": rendimento_anno,
                "spesa_anno": spesa,
                "capitale_fine": max(capitale_fine, 0),
            })

            if capitale_fine <= 0:
                break
            capitale = capitale_fine

        anni_sostenibilita = anno if capitale <= 0 or (len(proiezione) > 1 and proiezione[-1]["capitale_fine"] <= 0) else max_anni

        return {
            "allocazione": allocazione,
            "tot_nominale": tot_nominale,
            "tot_adjusted": tot_adjusted,
            "investimento_bsf": investimento_bsf,
            "somma_rimanente": somma_rimanente,
            "somma_liquida": somma_liquida,
            "spesa_annuale": spesa_annuale,
            "inflazione": inflazione,
            "rendimento": rendimento,
            "anni_sostenibilita": anni_sostenibilita,
            "proiezione": proiezione,
        }
    except Exception as e:
        return {"error": str(e)}


VRP_FIELDS = [
    "immobile_id", "nome", "data_simulazione", "data_inizio_piano",
    "attiva", "valore_vendita", "valore_vendita_immediata",
    "prezzo_acquisto", "data_acquisto",
    "anticipo", "durata_anni", "tasso_interesse", "spese_notarili",
    "aliquota_plusvalenza", "imposta_registro", "imu_annuale",
    "costo_assicurazione", "tasso_investimento",
    "reddito_annuo", "addizionale_regionale", "addizionale_comunale",
    "rata_mensile", "ricavo_netto", "anni_sostenibilita", "note",
]


def get_all_vrp():
    """Returns all saved VRP simulations with immobile name."""
    try:
        db = get_db()
        rows = db.execute(
            """SELECT v.*, i.nome as immobile_nome
               FROM vendita_riserva v
               LEFT JOIN immobili i ON i.id = v.immobile_id
               ORDER BY v.data_simulazione DESC"""
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


def get_vrp_by_id(id):
    """Returns a single VRP simulation by id."""
    try:
        db = get_db()
        row = db.execute(
            """SELECT v.*, i.nome as immobile_nome
               FROM vendita_riserva v
               LEFT JOIN immobili i ON i.id = v.immobile_id
               WHERE v.id = ?""",
            (id,),
        ).fetchone()
        db.close()
        if row is None:
            return {"error": "Record non trovato"}
        return dict(row)
    except Exception as e:
        return {"error": str(e)}


def save_vrp(data):
    """Save a VRP simulation to the database."""
    try:
        import datetime

        db = get_db()
        data.setdefault("data_simulazione", datetime.date.today().isoformat())
        data.setdefault("nome", "Simulazione VRP")

        placeholders = ", ".join(["?"] * len(VRP_FIELDS))
        columns = ", ".join(VRP_FIELDS)
        values = [data.get(f) for f in VRP_FIELDS]

        cursor = db.execute(
            f"INSERT INTO vendita_riserva ({columns}) VALUES ({placeholders})",
            values,
        )
        db.commit()
        new_id = cursor.lastrowid
        db.close()
        return {"id": new_id}
    except Exception as e:
        return {"error": str(e)}


def delete_vrp(id):
    """Delete a VRP simulation by id."""
    try:
        db = get_db()
        db.execute("DELETE FROM vendita_riserva WHERE id = ?", (id,))
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def get_vrp_attive():
    """Returns all active VRP simulations."""
    try:
        db = get_db()
        rows = db.execute(
            """SELECT v.*, i.nome as immobile_nome, i.tipo as immobile_tipo
               FROM vendita_riserva v
               LEFT JOIN immobili i ON i.id = v.immobile_id
               WHERE v.attiva = 1"""
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


def calcola_vrp_a_data(vrp, data_target):
    """Given a saved VRP and a target date, calculate the state of the plan.

    Returns dict with:
        - mesi_trascorsi: months since plan start
        - credito_residuo: remaining debt (buyer owes you)
        - rate_incassate_cumulate: total installments received
        - anticipo: down payment received
        - piano_completato: True if plan is finished
    """
    import datetime

    data_inizio = vrp.get("data_inizio_piano") or vrp.get("data_simulazione")
    if isinstance(data_inizio, str):
        data_inizio = datetime.datetime.strptime(data_inizio[:10], "%Y-%m-%d").date()
    if isinstance(data_target, str):
        data_target = datetime.datetime.strptime(data_target[:10], "%Y-%m-%d").date()

    # Months elapsed
    mesi = (data_target.year - data_inizio.year) * 12 + (data_target.month - data_inizio.month)
    if mesi < 0:
        mesi = 0

    valore_vendita = float(vrp.get("valore_vendita", 0))
    anticipo = float(vrp.get("anticipo", 0))
    durata_anni = int(vrp.get("durata_anni", 10))
    tasso = float(vrp.get("tasso_interesse", 0))
    n_mesi = durata_anni * 12
    importo_finanziato = valore_vendita - anticipo

    # Calculate monthly payment (French amortization)
    if tasso == 0:
        rata_mensile = importo_finanziato / n_mesi if n_mesi > 0 else 0
    else:
        r = tasso / 100 / 12
        rata_mensile = importo_finanziato * r / (1 - (1 + r) ** (-n_mesi))

    # Walk through amortization to find state at mesi_trascorsi
    debito = importo_finanziato
    rate_incassate = 0
    mesi_effettivi = min(mesi, n_mesi)

    for m in range(1, mesi_effettivi + 1):
        if tasso == 0:
            quota_int = 0
        else:
            quota_int = debito * tasso / 100 / 12
        quota_cap = rata_mensile - quota_int

        if m == n_mesi:
            quota_cap = debito
            rata_eff = quota_cap + quota_int
        else:
            rata_eff = rata_mensile

        debito -= quota_cap
        rate_incassate += rata_eff

        if debito <= 0:
            debito = 0
            break

    piano_completato = mesi >= n_mesi or debito <= 0

    return {
        "mesi_trascorsi": mesi,
        "credito_residuo": round(max(debito, 0), 2),
        "rate_incassate_cumulate": round(rate_incassate, 2),
        "anticipo": round(anticipo, 2),
        "totale_incassato": round(anticipo + rate_incassate, 2),
        "rata_mensile": round(rata_mensile, 2),
        "piano_completato": piano_completato,
        "immobile_id": vrp.get("immobile_id"),
        "immobile_tipo": vrp.get("immobile_tipo"),
        "valore_vendita": valore_vendita,
    }


def calcola_impatto_vrp_patrimonio(data_target):
    """Calculate the impact of all active VRP plans on patrimonio at a given date.

    Returns dict with adjustments to apply:
        - immobile_italia_adj: new value for immobile_italia (credito residuo)
        - cash_aggiuntivo: cash to add from anticipo + rate
        - dettagli: list of per-VRP details
    """
    vrp_list = get_vrp_attive()
    if isinstance(vrp_list, dict) and "error" in vrp_list:
        return {"error": vrp_list["error"]}

    if not vrp_list:
        return {"has_vrp": False, "dettagli": []}

    dettagli = []
    adjustments = {}  # immobile_id -> { credito_residuo, totale_incassato }

    for vrp in vrp_list:
        stato = calcola_vrp_a_data(vrp, data_target)
        dettagli.append({
            "nome": vrp.get("nome", ""),
            "immobile_nome": vrp.get("immobile_nome", ""),
            **stato,
        })
        imm_id = vrp.get("immobile_id")
        if imm_id:
            if imm_id not in adjustments:
                adjustments[imm_id] = {
                    "credito_residuo": 0,
                    "totale_incassato": 0,
                    "immobile_tipo": vrp.get("immobile_tipo"),
                }
            adjustments[imm_id]["credito_residuo"] += stato["credito_residuo"]
            adjustments[imm_id]["totale_incassato"] += stato["totale_incassato"]

    return {
        "has_vrp": True,
        "adjustments": adjustments,
        "dettagli": dettagli,
    }


def get_parametro(chiave, default=None):
    """Read a single parameter value by key."""
    try:
        db = get_db()
        row = db.execute(
            "SELECT valore FROM parametri WHERE chiave = ?", (chiave,)
        ).fetchone()
        db.close()
        return row["valore"] if row else default
    except Exception:
        return default


def get_parametri_simulazione():
    """Read simulation parameters from parametri table. Returns dict."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT chiave, valore, descrizione, categoria FROM parametri WHERE categoria IN ('simulazione', 'generale')"
        ).fetchall()
        db.close()

        parametri = {}
        for row in rows:
            parametri[row["chiave"]] = {
                "valore": row["valore"],
                "descrizione": row["descrizione"],
                "categoria": row["categoria"],
            }

        return parametri
    except Exception as e:
        return {"error": str(e)}


def save_parametri_simulazione(params):
    """Save simulation parameters dict to parametri table.

    params is a dict where keys are chiave and values are the new valore.
    """
    try:
        db = get_db()
        for chiave, valore in params.items():
            db.execute(
                "UPDATE parametri SET valore = ? WHERE chiave = ? AND categoria = 'simulazione'",
                (str(valore), chiave),
            )
        db.commit()
        db.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

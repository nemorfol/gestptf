import os
import json
from flask import Flask
from database import init_db
from config import BASE_DIR, UPLOAD_FOLDER, EXPORT_FOLDER

def create_app():
    app = Flask(__name__)
    app.secret_key = 'gestptf-secret-key-2025'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

    # Ensure directories exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(EXPORT_FOLDER, exist_ok=True)

    # Initialize database
    init_db()

    # Load i18n
    i18n_path = os.path.join(BASE_DIR, 'i18n', 'it.json')
    with open(i18n_path, 'r', encoding='utf-8') as f:
        translations = json.load(f)

    @app.context_processor
    def inject_i18n():
        return {'t': translations}

    @app.context_processor
    def inject_now():
        from datetime import datetime
        return {'now': datetime.now}

    # Template filters
    @app.template_filter('currency')
    def currency_filter(value):
        try:
            v = float(value or 0)
            formatted = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"€ {formatted}"
        except (ValueError, TypeError):
            return "€ 0,00"

    @app.template_filter('percent')
    def percent_filter(value):
        try:
            v = float(value or 0)
            sign = "+" if v > 0 else ""
            return f"{sign}{v:.2f}%"
        except (ValueError, TypeError):
            return "0,00%"

    @app.template_filter('number')
    def number_filter(value, decimals=2):
        try:
            v = float(value or 0)
            formatted = f"{v:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return formatted
        except (ValueError, TypeError):
            return "0"

    @app.template_filter('date')
    def date_filter(value):
        """Strip time part from date strings (e.g. '2025-01-01 00:00:00' -> '2025-01-01')."""
        if value:
            return str(value)[:10]
        return ''

    # Also expose as functions for templates that use PM_fmt_currency() style
    @app.context_processor
    def inject_formatters():
        return {
            'fmt_currency': currency_filter,
            'fmt_percent': percent_filter,
            'fmt_number': number_filter,
        }

    # Register blueprints
    from routes.dashboard import dashboard_bp
    from routes.etf import etf_bp
    from routes.bond import bond_bp
    from routes.patrimonio import patrimonio_bp
    from routes.simulatore import simulatore_bp
    from routes.liquidita import liquidita_bp
    from routes.simulazione_inv import simulazione_inv_bp
    from routes.import_export import import_export_bp
    from routes.bfp import bfp_bp
    from routes.immobili import immobili_bp
    from routes.fondo_pensione import fp_bp
    from routes.tfr_route import tfr_bp
    from routes.liquidita_nuova import liquidita_nuova_bp
    from routes.debiti import debiti_bp
    from routes.impostazioni import impostazioni_bp
    from routes.help import help_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(etf_bp)
    app.register_blueprint(bond_bp)
    app.register_blueprint(bfp_bp)
    app.register_blueprint(immobili_bp)
    app.register_blueprint(fp_bp)
    app.register_blueprint(tfr_bp)
    app.register_blueprint(liquidita_nuova_bp)
    app.register_blueprint(debiti_bp)
    app.register_blueprint(patrimonio_bp)
    app.register_blueprint(simulatore_bp)
    app.register_blueprint(liquidita_bp)
    app.register_blueprint(simulazione_inv_bp)
    app.register_blueprint(import_export_bp)
    app.register_blueprint(impostazioni_bp)
    app.register_blueprint(help_bp)

    return app


if __name__ == '__main__':
    app = create_app()
    print("=" * 50)
    print("  GestPTF - Gestione Patrimonio")
    print("  http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)

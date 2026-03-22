from flask import Blueprint, render_template

help_bp = Blueprint("help_bp", __name__, url_prefix="/guida")

@help_bp.route("/", methods=["GET"])
def index():
    return render_template("guida.html", active_page="guida")

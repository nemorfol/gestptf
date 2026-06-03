from flask import Blueprint, redirect, url_for

liquidita_bp = Blueprint("liquidita_bp", __name__, url_prefix="/piano-liquidita")


@liquidita_bp.route("/", methods=["GET"])
def index():
    """Redirect to unified liquidita page, piano tab."""
    return redirect(url_for("liquidita_nuova_bp.index") + "?tab=piano")

from flask import Blueprint, jsonify
from flask_login import login_required
from app.database import db_session
from app.models import Management, District, Plot

api_bp = Blueprint('api', __name__)


@api_bp.route('/management-relations')
@login_required
def get_management_relations():
    """
    Returns mapping between Managements and their associated Districts and Plots.
    "в Управление может входить несколько округов, в управление может входить несколько участков"
    """
    managements = db_session.query(Management).filter_by(is_active=True).all()
    data = {}
    for m in managements:
        data[m.id] = {
            'id': m.id,
            'name': m.name,
            'district_ids': [d.id for d in m.districts if d.is_active],
            'plot_ids': [p.id for p in m.plots if p.is_active],
        }
    return jsonify(data)

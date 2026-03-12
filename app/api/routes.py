from flask import Blueprint, request, jsonify
from sqlalchemy import func

from app.db.models import Server, get_engine, get_session

api = Blueprint('api', __name__, url_prefix='/api')


def get_db_session():
    engine = get_engine()
    return get_session(engine)


@api.route('/servers', methods=['GET'])
def get_servers():
    session = get_db_session()

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 20

    search = request.args.get('search', '', type=str)
    sort_by = request.args.get('sort_by', 'last_updated', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str)
    version_filter = request.args.get('version', '', type=str)
    min_players = request.args.get('min_players', None, type=int)
    max_players = request.args.get('max_players', None, type=int)
    modded_only = request.args.get('modded_only', 'false', type=str).lower() == 'true'

    query = session.query(Server)

    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            (Server.ip.like(search_pattern)) |
            (Server.motd.like(search_pattern)) |
            (Server.version.like(search_pattern))
        )

    if version_filter:
        query = query.filter(Server.version.ilike(f'%{version_filter}%'))

    if min_players is not None:
        query = query.filter(Server.players_online >= min_players)

    if max_players is not None:
        query = query.filter(Server.players_online <= max_players)

    if modded_only:
        query = query.filter(Server.is_modded == True)

    valid_sort_columns = {
        'last_updated': Server.last_updated,
        'players_online': Server.players_online,
        'version': Server.version,
        'ip': Server.ip,
    }

    sort_column = valid_sort_columns.get(sort_by, Server.last_updated)

    if sort_order.lower() == 'asc':
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    total = query.count()
    servers = query.offset((page - 1) * per_page).limit(per_page).all()

    session.close()

    return jsonify({
        'servers': [s.to_dict() for s in servers],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    })


@api.route('/servers/<ip>', methods=['GET'])
def get_server(ip):
    session = get_db_session()
    server = session.query(Server).filter_by(ip=ip).first()
    session.close()

    if not server:
        return jsonify({'error': 'Server not found'}), 404

    return jsonify(server.to_dict())


@api.route('/stats', methods=['GET'])
def get_stats():
    session = get_db_session()

    total_servers = session.query(func.count(Server.ip)).scalar()
    total_players = session.query(func.sum(Server.players_online)).scalar() or 0
    modded_servers = session.query(func.count(Server.ip)).filter(
        Server.is_modded == True
    ).scalar()

    session.close()

    return jsonify({
        'total_servers': total_servers,
        'total_players': total_players,
        'modded_servers': modded_servers,
    })


@api.route('/filters', methods=['GET'])
def get_filters():
    session = get_db_session()

    versions = session.query(Server.version).filter(
        Server.version.isnot(None)
    ).distinct().all()

    session.close()

    return jsonify({
        'versions': [v[0] for v in versions if v[0]]
    })

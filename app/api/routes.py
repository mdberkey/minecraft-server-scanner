from flask import Blueprint, request, jsonify
from sqlalchemy import func

from app.db.models import MinecraftServer, get_engine, get_session

api = Blueprint('api', __name__, url_prefix='/api')


def get_db_session():
    engine = get_engine()
    return get_session(engine)


@api.route('/servers', methods=['GET'])
def get_servers():
    session = get_db_session()
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '', type=str)
    sort_by = request.args.get('sort_by', 'date_added', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str)
    version_filter = request.args.get('version', '', type=str)
    min_players = request.args.get('min_players', None, type=int)
    max_players = request.args.get('max_players', None, type=int)
    vanilla_only = request.args.get('vanilla_only', 'false', type=str).lower() == 'true'
    modded_only = request.args.get('modded_only', 'false', type=str).lower() == 'true'
    whitelist = request.args.get('whitelist', 'false', type=str).lower() == 'true'
    no_whitelist = request.args.get('no_whitelist', 'false', type=str).lower() == 'true'
    
    query = session.query(MinecraftServer)
    
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            (MinecraftServer.ip.like(search_pattern)) |
            (MinecraftServer.motd.like(search_pattern)) |
            (MinecraftServer.version.like(search_pattern))
        )
    
    if version_filter:
        query = query.filter(MinecraftServer.version.ilike(f'%{version_filter}%'))
    
    if min_players is not None:
        query = query.filter(MinecraftServer.players_online >= min_players)
    
    if max_players is not None:
        query = query.filter(MinecraftServer.players_online <= max_players)
    
    if vanilla_only:
        query = query.filter(MinecraftServer.is_modded == False)
    
    if modded_only:
        query = query.filter(MinecraftServer.is_modded == True)
    
    if whitelist:
        query = query.filter(MinecraftServer.whitelist == True)
    
    if no_whitelist:
        query = query.filter(MinecraftServer.whitelist == False)
    
    valid_sort_columns = {
        'date_added': MinecraftServer.date_added,
        'players_online': MinecraftServer.players_online,
        'version': MinecraftServer.version,
        'ip': MinecraftServer.ip,
    }
    
    sort_column = valid_sort_columns.get(sort_by, MinecraftServer.date_added)
    
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


@api.route('/servers/<int:server_id>', methods=['GET'])
def get_server(server_id):
    session = get_db_session()
    server = session.query(MinecraftServer).filter_by(id=server_id).first()
    session.close()
    
    if not server:
        return jsonify({'error': 'Server not found'}), 404
    
    return jsonify(server.to_dict())


@api.route('/stats', methods=['GET'])
def get_stats():
    session = get_db_session()
    
    total_servers = session.query(func.count(MinecraftServer.id)).scalar()
    total_players = session.query(func.sum(MinecraftServer.players_online)).scalar() or 0
    modded_servers = session.query(func.count(MinecraftServer.id)).filter(
        MinecraftServer.is_modded == True
    ).scalar()
    whitelist_servers = session.query(func.count(MinecraftServer.id)).filter(
        MinecraftServer.whitelist == True
    ).scalar()
    
    session.close()
    
    return jsonify({
        'total_servers': total_servers,
        'total_players': total_players,
        'modded_servers': modded_servers,
        'whitelist_servers': whitelist_servers,
    })


@api.route('/filters', methods=['GET'])
def get_filters():
    session = get_db_session()
    
    versions = session.query(MinecraftServer.version).filter(
        MinecraftServer.version.isnot(None)
    ).distinct().all()
    
    session.close()
    
    return jsonify({
        'versions': [v[0] for v in versions if v[0]]
    })

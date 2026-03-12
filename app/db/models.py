import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone

Base = declarative_base()


class MinecraftServer(Base):
    __tablename__ = 'minecraft_servers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(45), nullable=False, index=True)
    port = Column(Integer, nullable=False, default=25565)
    favicon = Column(Text, nullable=True)
    whitelist = Column(String(10), default='Unknown')
    motd = Column(String(512), nullable=True)
    version = Column(String(128), nullable=True)
    is_modded = Column(Boolean, default=False)
    players_online = Column(Integer, default=0)
    players_max_ever = Column(Integer, default=0)
    players_min_ever = Column(Integer, default=0)
    date_added = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'port': self.port,
            'favicon': self.favicon,
            'whitelist': self.whitelist,
            'motd': self.motd,
            'version': self.version,
            'is_modded': self.is_modded,
            'players_online': self.players_online,
            'players_max_ever': self.players_max_ever,
            'players_min_ever': self.players_min_ever,
            'date_added': self.date_added.isoformat() if self.date_added else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
        }


def get_engine(db_path=None):
    if db_path is None:
        db_path = os.environ.get('DB_PATH', 'servers.db')
    return create_engine(f'sqlite:///{db_path}', echo=False, future=True)


def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()

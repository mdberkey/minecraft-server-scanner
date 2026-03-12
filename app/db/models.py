import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone

Base = declarative_base()


class Server(Base):
    __tablename__ = 'servers'

    ip = Column(String(45), primary_key=True)
    json = Column(Text, nullable=False)
    motd = Column(String(512), nullable=True)
    version = Column(String(128), nullable=True)
    is_modded = Column(Boolean, default=False)
    players_online = Column(Integer, default=0)
    players_max = Column(Integer, default=0)
    favicon = Column(Text, nullable=True)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'ip': self.ip,
            'motd': self.motd,
            'version': self.version,
            'is_modded': self.is_modded,
            'players_online': self.players_online,
            'players_max': self.players_max,
            'favicon': self.favicon,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
        }


def get_engine(db_path=None):
    if db_path is None:
        db_path = os.environ.get('DB_PATH', 'servers.db')
    return create_engine(f'sqlite:///{db_path}', echo=False, future=True)


def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()

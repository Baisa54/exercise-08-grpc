"""
Database configuration and ORM models for the Node Registry service.
"""

import os
from datetime import datetime
import uuid

from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://noderegistry:noderegistry@db:5432/noderegistry"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class NodeModel(Base):
    """SQLAlchemy database model for a registered node."""
    __tablename__ = "nodes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Create database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)

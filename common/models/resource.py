import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON

from common.database import Base


class Resource(Base):
    __tablename__ = 'resources'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=True)
    region = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    discovered_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
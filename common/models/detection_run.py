import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey

from common.database import Base


class DetectionRun(Base):
    __tablename__ = "detection_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    status = Column(String, nullable=False, default="running")
    infrastructure_finding_count = Column(Integer, nullable=False, default=0)
    record_finding_count = Column(Integer, nullable=False, default=0)
    error = Column(String, nullable=True)
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    finished_at = Column(DateTime(timezone=True), nullable=True)

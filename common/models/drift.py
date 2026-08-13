import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON

from common.database import Base


class DriftFinding(Base):
    __tablename__ = "drift_findings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    finding_type = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    region = Column(String, nullable=True)
    previous_value = Column(JSON, nullable=True)
    current_value = Column(JSON, nullable=True)
    detected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )



#finding_type	              Meaning	                         Kind
#resource_appeared	    In latest scan, not in previous	         Infrastructure
#resource_disappeared	In previous scan, not in latest	         Infrastructure
#resource_changed	    Same resource, different details	     Infrastructure
#missing_ci	            In AWS, no active CI in CMDB	         Record
#orphaned_ci	        Active CI, not in AWS	                 Record


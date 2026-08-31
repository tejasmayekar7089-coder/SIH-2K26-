from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class RegistryStatus(str, Enum):
    VALID = "VALID"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    LOST = "LOST"
    STOLEN = "STOLEN"
    WATCHLIST = "WATCHLIST"
    NOT_FOUND = "NOT_FOUND"

class DatabaseResult(BaseModel):
    is_simulated_data: bool = True
    document_number_queried: Optional[str] = None
    status: RegistryStatus = RegistryStatus.NOT_FOUND
    issuer_country: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    remarks: Optional[str] = None
    notice: str = "SIMULATED / MOCK DATA ONLY — Zero live government database access."

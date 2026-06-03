from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Numeric
from app.db.base import Base

class TransactionRecord(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True)
    store_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    basket_value_inr = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

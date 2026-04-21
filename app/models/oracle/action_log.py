from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, Float
from app.db.oracle import Base


class ActionLog(Base):
    __tablename__ = "action_log"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("growth_batch.id"))

    action_type = Column(String(50))     # water / nutrient
    action_mode = Column(String(20))     # auto / manual

    trigger_value = Column(Float)
    threshold = Column(Float)

    status = Column(String(20))          # success / fail
    message = Column(String(255))

    recorded_at = Column(DateTime)
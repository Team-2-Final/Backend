from sqlalchemy import Column, Integer, String, Date
from app.db.oracle import Base


class GrowthBatch(Base):
    __tablename__ = "growth_batch"

    id = Column(Integer, primary_key=True)
    crop_type = Column(String(50))
    start_date = Column(Date)
    end_date = Column(Date)
    description = Column(String(255))
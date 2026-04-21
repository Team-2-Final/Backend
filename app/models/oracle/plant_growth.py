from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, Float
from app.db.oracle import Base


class PlantGrowth(Base):
    __tablename__ = "plant_growth"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("growth_batch.id"))

    inference_id = Column(String(100))
    model_version = Column(String(50))

    plant_height = Column(Float)
    leaf_length = Column(Float)
    leaf_width = Column(Float)
    leaf_count = Column(Integer)

    captured_at = Column(DateTime)
    inferred_at = Column(DateTime)

    recorded_at = Column(DateTime)
from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime, text
from app.db.oracle import Base


class EnvironmentData(Base):
    __tablename__ = "environment_data"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("growth_batch.id"))

    temperature = Column(Float)
    humidity = Column(Float)
    co2 = Column(Float)
    radiation = Column(Float)

    soil_ec = Column(Float)
    soil_moisture = Column(Float)
    ph = Column(Float)

    recorded_at = Column(
        DateTime,
        nullable=False,
        server_default=text("SYSTIMESTAMP")
    )
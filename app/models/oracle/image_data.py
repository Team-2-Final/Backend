from sqlalchemy import Column, Integer, ForeignKey, String, DateTime
from app.db.oracle import Base


class ImageData(Base):
    __tablename__ = "image_data"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("growth_batch.id"))

    inference_id = Column(String(100))

    file_path = Column(String(255), nullable=False)

    captured_at = Column(DateTime)
    recorded_at = Column(DateTime)
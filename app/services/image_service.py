import os
import uuid
from datetime import datetime


class ImageService:

    def save_image(self, file, batch_id: int) -> str:
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)

        filename = f"{batch_id}_{uuid.uuid4().hex}.jpg"
        path = os.path.join(upload_dir, filename)

        with open(path, "wb") as buffer:
            buffer.write(file.file.read())

        return path
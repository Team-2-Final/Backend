from pathlib import Path
import uuid
import os


class ImageService:

    def save_image(self, file, batch_id, category):
        base_dir = Path("images") / f"batch_{batch_id}" / category
        base_dir.mkdir(parents=True, exist_ok=True)

        ext = os.path.splitext(file.filename)[1]
        filename = f"{uuid.uuid4()}{ext}"
        file_path = base_dir / filename

        with open(file_path, "wb") as f:
            f.write(file.file.read())

        return str(file_path)
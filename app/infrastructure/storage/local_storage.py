import uuid
from pathlib import Path

from app.application.interfaces.file_storage import FileStorage

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MIME_EXTENSION_MAP = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class LocalDiskFileStorage(FileStorage):
    def __init__(
        self,
        base_directory: Path | str,
        public_url_prefix: str = "/media",
    ) -> None:
        self.base_directory = Path(base_directory).resolve()
        self.public_url_prefix = public_url_prefix.rstrip("/")

    def _determine_extension(self, filename: str, content_type: str) -> str:
        ext = Path(filename).suffix.lower()
        if ext in ALLOWED_EXTENSIONS:
            return ".jpg" if ext == ".jpeg" else ext
        mime_ext = MIME_EXTENSION_MAP.get(content_type.lower())
        if mime_ext:
            return mime_ext
        return ".png"

    async def save_file(
        self,
        content: bytes,
        filename: str,
        content_type: str,
        folder: str = "avatars",
    ) -> str:
        safe_folder = folder.strip("/\\").replace("..", "")
        target_dir = (self.base_directory / safe_folder).resolve()

        if not str(target_dir).startswith(str(self.base_directory)):
            raise ValueError("invalid_storage_path")

        target_dir.mkdir(parents=True, exist_ok=True)

        ext = self._determine_extension(filename, content_type)
        file_name = f"{uuid.uuid4()}{ext}"
        file_path = target_dir / file_name

        file_path.write_bytes(content)

        return f"{self.public_url_prefix}/{safe_folder}/{file_name}"

    async def delete_file(self, public_path: str) -> None:
        if not public_path:
            return

        expected_prefix = f"{self.public_url_prefix}/"
        if not public_path.startswith(expected_prefix):
            return

        relative_part = public_path[len(expected_prefix) :]
        target_file = (self.base_directory / relative_part).resolve()

        if not str(target_file).startswith(str(self.base_directory)):
            return

        if target_file.is_file():
            target_file.unlink(missing_ok=True)

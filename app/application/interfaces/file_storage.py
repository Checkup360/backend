from typing import Protocol


class FileStorage(Protocol):
    async def save_file(
        self,
        content: bytes,
        filename: str,
        content_type: str,
        folder: str = "avatars",
    ) -> str:
        """Saves a file and returns its public relative URL path."""
        ...

    async def delete_file(self, public_path: str) -> None:
        """Deletes a file given its public path if it exists."""
        ...

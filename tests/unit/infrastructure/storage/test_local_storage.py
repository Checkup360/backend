import pytest
from pathlib import Path

from app.infrastructure.storage.local_storage import LocalDiskFileStorage


@pytest.mark.asyncio
async def test_save_and_delete_file(tmp_path: Path):
    storage = LocalDiskFileStorage(base_directory=tmp_path, public_url_prefix="/media")

    content = b"fake-png-content"
    url = await storage.save_file(
        content=content,
        filename="test.png",
        content_type="image/png",
        folder="avatars",
    )

    assert url.startswith("/media/avatars/")
    assert url.endswith(".png")

    file_name = url.replace("/media/avatars/", "")
    saved_path = tmp_path / "avatars" / file_name
    assert saved_path.is_file()
    assert saved_path.read_bytes() == content

    await storage.delete_file(url)
    assert not saved_path.exists()


@pytest.mark.asyncio
async def test_delete_nonexistent_or_invalid_path(tmp_path: Path):
    storage = LocalDiskFileStorage(base_directory=tmp_path, public_url_prefix="/media")

    await storage.delete_file("")
    await storage.delete_file("/other/path/file.png")
    await storage.delete_file("/media/avatars/nonexistent.png")


@pytest.mark.asyncio
async def test_path_traversal_prevention(tmp_path: Path):
    storage = LocalDiskFileStorage(base_directory=tmp_path, public_url_prefix="/media")

    outside_file = tmp_path.parent / "secret.txt"
    outside_file.write_text("secret")

    await storage.delete_file(f"/media/../../{outside_file.name}")
    assert outside_file.is_file()
    outside_file.unlink(missing_ok=True)

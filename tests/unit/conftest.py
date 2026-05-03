import pytest
from unittest.mock import AsyncMock


@pytest.fixture
def mock_db():
    """Fixture para un mock de AsyncSession."""
    return AsyncMock()

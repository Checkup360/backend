import os

from tests.config import TEST_ENV


for key, value in TEST_ENV.items():
    os.environ.setdefault(key, value)

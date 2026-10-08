import asyncio
from apps.api.src.config.settings import settings
from apps.api.src.api.dependencies.auth import create_access_token
import uuid
import datetime

token = create_access_token({"sub": "cbda287c-b640-476c-8d7c-5bb66bad1d0f"})
print(token)

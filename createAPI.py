import asyncio
from database import async_session
from utils.api_auth import store_api_key

async def create_api_key():
    async with async_session() as session:
        user_id = "1bd5e9c7-afb7-4259-a8c6-817c8ec218c1"
        api_key = await store_api_key(user_id, session)
        print("Your API Key:", api_key)

asyncio.run(create_api_key())

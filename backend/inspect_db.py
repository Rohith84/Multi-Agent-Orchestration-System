import asyncio
from sqlalchemy import select
from app.db.database import async_session_factory, engine
from app.models.chat import ChatMessage

async def main():
    async with async_session_factory() as session:
        result = await session.execute(select(ChatMessage).order_by(ChatMessage.created_at.asc()))
        messages = result.scalars().all()
        print(f"Total messages: {len(messages)}")
        for i, msg in enumerate(messages):
            print(f"[{i}] ID: {msg.id} | Session: {msg.session_id} | Role: {msg.role} | Length: {len(msg.message)} | Created: {msg.created_at}")
            print(f"Content: {msg.message[:200]}...")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())

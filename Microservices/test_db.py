import asyncio
import asyncpg
import os

async def test_conn():
    dsn = "postgresql://postgres:anuroop%401373@localhost:5432/causalmedfusion"
    print(f"Testing connection to: {dsn}")
    try:
        conn = await asyncpg.connect(dsn)
        print("Successfully connected!")
        await conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_conn())

import asyncio
import asyncpg

async def create_db():
    try:
        # Connect to the default 'postgres' database
        conn = await asyncpg.connect(user='postgres', password='postgres', database='postgres', host='localhost', port=5432)
        
        # Check if database exists
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'aturmodal'")
        if not exists:
            # We must use execute for CREATE DATABASE
            print("Creating database 'aturmodal'...")
            await conn.execute('CREATE DATABASE aturmodal')
            print("Database 'aturmodal' created successfully!")
        else:
            print("Database 'aturmodal' already exists.")
            
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(create_db())

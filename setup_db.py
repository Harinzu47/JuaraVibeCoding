"""
Setup script untuk Sprint 2 — jalankan ini setelah PostgreSQL terinstall.

Cara pakai:
    py setup_db.py

Script ini akan:
1. Membuat database 'aturmodal' jika belum ada
2. Menjalankan alembic revision --autogenerate
3. Menjalankan alembic upgrade head
4. Memverifikasi tabel terbentuk
"""

import subprocess
import sys
import os

# Pastikan .env terbaca
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    os.environ[parts[0].strip()] = parts[1].strip()

DB_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/aturmodal")

print("=" * 60)
print("AturModal - Database Setup Sprint 2")
print("=" * 60)

# Step 1: Buat database
print("\n[1/3] Membuat database 'aturmodal'...")
try:
    import asyncio
    import asyncpg

    async def create_db():
        # Connect ke postgres (default db) untuk buat aturmodal
        conn_str = DB_URL.replace("postgresql+asyncpg://", "postgresql://").replace("/aturmodal", "/postgres")
        
        # Parse credentials
        parts = conn_str.replace("postgresql://", "").split("@")
        user_pass = parts[0].split(":")
        host_db = parts[1].split("/")
        
        user = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ""
        host = host_db[0].split(":")[0]
        port = int(host_db[0].split(":")[1]) if ":" in host_db[0] else 5432

        conn = await asyncpg.connect(
            host=host, port=port, user=user, password=password, database="postgres"
        )
        
        # Check if database exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'aturmodal'"
        )
        if not exists:
            await conn.execute("CREATE DATABASE aturmodal")
            print("   Database 'aturmodal' berhasil dibuat!")
        else:
            print("   Database 'aturmodal' sudah ada, skip.")
        
        await conn.close()

    asyncio.run(create_db())
except Exception as e:
    print(f"   ERROR: {e}")
    print("   Pastikan PostgreSQL berjalan dan credentials di .env benar.")
    sys.exit(1)

# Step 2: Alembic autogenerate
print("\n[2/3] Membuat migration awal...")
result = subprocess.run(
    [sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", "initial_schema"],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("   Migration file berhasil dibuat!")
    print(f"   {result.stdout.strip()}")
else:
    # Mungkin sudah ada migration
    if "already exists" in result.stderr or "up to date" in result.stderr:
        print("   Migration sudah ada, skip.")
    else:
        print(f"   Output: {result.stdout}")
        print(f"   Error: {result.stderr}")

# Step 3: Alembic upgrade
print("\n[3/3] Menerapkan migration ke database...")
result = subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("   Tabel berhasil dibuat!")
    print(f"   {result.stdout.strip()}")
else:
    print(f"   ERROR: {result.stderr}")
    sys.exit(1)

# Verifikasi
print("\n[Verifikasi] Mengecek tabel...")
try:
    import asyncio
    import asyncpg

    async def verify():
        conn_str = DB_URL.replace("postgresql+asyncpg://", "postgresql://")
        parts = conn_str.replace("postgresql://", "").split("@")
        user_pass = parts[0].split(":")
        host_db = parts[1].split("/")
        
        conn = await asyncpg.connect(
            host=host_db[0].split(":")[0],
            port=int(host_db[0].split(":")[1]) if ":" in host_db[0] else 5432,
            user=user_pass[0],
            password=user_pass[1] if len(user_pass) > 1 else "",
            database="aturmodal"
        )
        
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        table_names = [t["tablename"] for t in tables]
        print(f"   Tabel yang ada: {table_names}")
        
        expected = {"users", "daily_sessions", "chat_messages", "alembic_version"}
        missing = expected - set(table_names)
        if missing:
            print(f"   PERINGATAN: Tabel berikut tidak ditemukan: {missing}")
        else:
            print("   Semua tabel terbentuk dengan benar!")
        
        await conn.close()

    asyncio.run(verify())
except Exception as e:
    print(f"   Tidak dapat verifikasi: {e}")

print("\n" + "=" * 60)
print("Setup selesai! Sekarang jalankan:")
print("  py -m uvicorn main:app --port 8082 --reload")
print("=" * 60)

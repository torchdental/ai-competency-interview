"""Drop the database and reseed from scratch."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = Path(__file__).parent.parent / "claims.db"


async def reset() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Deleted {DB_PATH}")

    from scripts.seed import seed
    await seed()


if __name__ == "__main__":
    asyncio.run(reset())

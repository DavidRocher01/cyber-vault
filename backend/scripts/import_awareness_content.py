"""
Charge le contenu YAML/Markdown du module sensibilisation en DB.
Usage: python scripts/import_awareness_content.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.services.awareness_content_importer import import_from_directory

CONTENT_DIR = Path(__file__).parent.parent.parent / "content" / "fr"


async def main() -> None:
    print(f"Import depuis : {CONTENT_DIR}")
    async with AsyncSessionLocal() as db:
        summary = await import_from_directory(db, CONTENT_DIR)
    print(f"Programmes importes : {summary['programs']}")
    print(f"Modules importes    : {summary['modules']}")
    if summary["errors"]:
        print("Erreurs :")
        for e in summary["errors"]:
            print(f"  - {e}")
    else:
        print("OK - aucune erreur")


if __name__ == "__main__":
    asyncio.run(main())

from app.db.base import init_db
from app.db.session import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        init_db(db)
        print("Database initialized and seed data applied.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

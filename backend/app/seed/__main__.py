"""python -m app.seed  — idempotent seeding of base accounts (+ official data / demo data once available)."""
from app.db.session import SessionLocal
from app.seed.base import seed_roles_and_staff


def main() -> None:
    with SessionLocal() as db:
        seed_roles_and_staff(db)
        db.commit()
    print("Seed complete.")


if __name__ == "__main__":
    main()

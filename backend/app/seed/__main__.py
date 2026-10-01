"""python -m app.seed  — idempotent seeding: roles/staff, official qualifications, task bank."""
from app.db.session import SessionLocal
from app.seed.base import seed_roles_and_staff
from app.seed.consistency import load_consistency
from app.seed.official import load_qualifications, load_task_banks


def main() -> None:
    with SessionLocal() as db:
        seed_roles_and_staff(db)
        qs = load_qualifications(db)
        n = load_task_banks(db)
        c = load_consistency(db)
        db.commit()
    print(f"Seed complete: {len(qs)} qualifications, {n} tasks, {c} consistency ratings (simulation).")


if __name__ == "__main__":
    main()

"""python -m app.seed [--demo] [--reset-demo]

Base seed (always, idempotent): roles + demo staff accounts, official qualifications, task bank, consistency ratings.
--demo        also create the 40 SYNTHETIC demo workers through the real API (skips ones that exist)
--reset-demo  rebuild the synthetic demo workers from data/demo/*.csv
"""
import argparse

from app.db.session import SessionLocal
from app.seed.base import seed_roles_and_staff
from app.seed.consistency import load_consistency
from app.seed.official import load_qualifications, load_task_banks


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m app.seed")
    ap.add_argument("--demo", action="store_true", help="create synthetic demo workers")
    ap.add_argument("--reset-demo", action="store_true", help="rebuild synthetic demo workers")
    args = ap.parse_args()
    with SessionLocal() as db:
        seed_roles_and_staff(db)
        qs = load_qualifications(db)
        n = load_task_banks(db)
        c = load_consistency(db)
        db.commit()
    print(f"Base seed: {len(qs)} qualifications, {n} tasks, {c} consistency ratings (simulation).")
    if args.demo or args.reset_demo:
        from app.seed.demo import seed_demo
        r = seed_demo(reset=args.reset_demo)
        print(f"Demo seed: {r['created']} synthetic workers created, {r['skipped']} already present.")


if __name__ == "__main__":
    main()

"""Load the SIMULATION consistency dataset (data/demo/consistency_test_set.csv) into consistency_ratings."""
import csv

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import DATA_DIR
from app.models import ConsistencyRating


def load_consistency(db: Session) -> int:
    path = DATA_DIR / "demo" / "consistency_test_set.csv"
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(line for line in f if not line.startswith("#")))
    if db.scalar(select(func.count()).select_from(ConsistencyRating)) == len(rows):
        return len(rows)
    db.execute(delete(ConsistencyRating))
    db.add_all(ConsistencyRating(case_id=r["case_id"], task_code=r["task_code"], criterion_code=r["criterion_code"],
                                 assessor_id=r["assessor_id"], mode=r["mode"], score=int(r["score"]), data_origin="simulation")
               for r in rows)
    db.flush()
    return len(rows)

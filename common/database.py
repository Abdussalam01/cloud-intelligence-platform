import time
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError

from common.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def wait_for_db(retries: int = 10, delay_seconds: float = 1.0):
    for attempt in range(1, retries + 1):
        try:
            with engine.connect():
                return
        except OperationalError:
            print(f"DB not ready (attempt {attempt}/{retries}), retrying...")
            time.sleep(delay_seconds)
    raise RuntimeError("Database never became ready")
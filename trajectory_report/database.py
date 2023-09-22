from trajectory_report.config import DB, REDIS
from sqlalchemy import create_engine
import redis

DB_ENGINE = create_engine(DB, pool_recycle=300, pool_pre_ping=True)
REDIS_CONN = redis.Redis(REDIS)

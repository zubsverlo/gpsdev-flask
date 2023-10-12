from trajectory_report.config import DB, ASYNC_DB, REDIS
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
import redis

DB_ENGINE = create_engine(DB, pool_recycle=300, pool_pre_ping=True)
ASYNC_DB_ENGINE = create_async_engine(ASYNC_DB, pool_recycle=300)
REDIS_CONN = redis.Redis(REDIS)

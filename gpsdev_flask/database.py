from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from greenlet import getcurrent
# from trajectory_report.models import Base


def create_db_session(config):
    engine = create_engine(config.DB, echo=config.DATABASE_ECHO,
                           pool_recycle=300)
    db_session = scoped_session(
        sessionmaker(autocommit=False,
                     autoflush=False,
                     bind=engine),
        scopefunc=getcurrent
    )
    return db_session
# Base.query = db_session.query_property()

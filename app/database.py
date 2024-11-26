# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./hailuo_video_proxy.db"

engine = create_engine(
    DATABASE_URL,
    pool_size=30,  # 设置连接池的大小
    max_overflow=50,  # 设置溢出连接的数量
    pool_timeout=30,  # 设置连接超时时间
    pool_recycle=1800  # 设置连接回收时间
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
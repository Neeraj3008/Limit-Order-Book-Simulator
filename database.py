import sqlalchemy
from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Connection Setup
DATABASE_URL = "sqlite:///./exchange.db"
engine = sqlalchemy.create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Sessionlocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. Schema Setup
Base = declarative_base()

class Traderecord(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    price = Column(Float)
    quantity = Column(Integer)
    side = Column(String)
    # Using the string-based default to completely bypass Python-side logic
    timestamp = Column(DateTime, server_default=func.now())

# 3. Initialization
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Database created successfully!")
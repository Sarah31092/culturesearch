from sqlalchemy import Column, Float, Integer, String, Text

from .database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    source = Column(String(100), nullable=False)
    event_type = Column(String(50), nullable=True)
    region = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    venue = Column(String(300), nullable=True)
    start_date = Column(String(10), nullable=True)
    end_date = Column(String(10), nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    target = Column(String(200), nullable=True)
    fee = Column(String(300), nullable=True)
    phone = Column(String(200), nullable=True)
    homepage = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    image_url = Column(Text, nullable=True)
    detail_url = Column(Text, nullable=True)

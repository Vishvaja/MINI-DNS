from sqlalchemy import Column, String, Enum, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class RecordType(enum.Enum):
    A = "A"
    CNAME = "CNAME"
    MX = "MX"
    TXT = "TXT"
    AAAA = "AAAA"

class DNSRecord(Base):
    __tablename__ = "dns_records"

    hostname = Column(String, nullable=False)  
    type = Column(Enum(RecordType), nullable=False)
    value = Column(JSON, nullable=False) 
    timestamp_created = Column(DateTime, default=datetime.utcnow)
    ttl_seconds = Column(Integer, default=3600)
    id = Column(Integer, primary_key=True, autoincrement=True) 

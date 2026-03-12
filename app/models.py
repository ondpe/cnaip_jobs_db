from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Source(Base):
    """Table for storing job scraping sources"""
    __tablename__ = "sources"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), nullable=False)
    name = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationship to jobs
    jobs = relationship("Job", back_populates="source")
    
    def __repr__(self):
        return f"<Source(name={self.name}, url={self.url}, is_active={self.is_active})>"


class Job(Base):
    """Table for storing scraped job postings"""
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    company = Column(String(200))
    location = Column(String(200))
    keywords = Column(String(500))  # Comma-separated keywords
    summary = Column(Text)
    raw_content = Column(Text)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to source
    source = relationship("Source", back_populates="jobs")
    
    def __repr__(self):
        return f"<Job(title={self.title}, company={self.company}, location={self.location})>"
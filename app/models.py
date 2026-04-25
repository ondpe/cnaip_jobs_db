from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Setting(Base):
    """Table for application settings (like API keys)"""
    __tablename__ = "settings"
    key = Column(String(100), primary_key=True)
    value = Column(String(500))

class Source(Base):
    """Table for storing job scraping sources"""
    __tablename__ = "sources"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), nullable=False)
    name = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_crawled_at = Column(DateTime, nullable=True)
    last_scrape_count = Column(Integer, nullable=True)
    last_scrape_found = Column(Integer, nullable=True)
    
    # Relationship to jobs
    jobs = relationship("Job", back_populates="source")

class Job(Base):
    """Table for storing scraped job postings"""
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    company = Column(String(200))
    location = Column(String(200))
    keywords = Column(String(500))
    summary = Column(Text)
    raw_content = Column(Text)
    link = Column(Text) # Nový sloupec pro odkaz na inzerát
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_analyzed_at = Column(DateTime, nullable=True)
    
    # Relationship to source
    source = relationship("Source", back_populates="jobs")
# utils/db.py

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from datetime import datetime
from typing import Optional, Dict, Any, List

Base = declarative_base()

# Database Models
class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add relationships to new models
    networks = relationship("NetworkStructure", back_populates="project", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="project", cascade="all, delete-orphan")

class NetworkStructure(Base):
    __tablename__ = 'network_structures'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    mermaid_content = Column(String)
    components_json = Column(JSON)
    connections_json = Column(JSON)
    paths_json = Column(JSON, nullable=True)
    diagnostics_json = Column(JSON, nullable=True)
    analysis_date = Column(DateTime, nullable=True)
    
    project = relationship("Project", back_populates="networks")
    components = relationship("NetworkComponent", back_populates="network", cascade="all, delete-orphan")

class NetworkComponent(Base):
    __tablename__ = 'network_components'
    
    id = Column(Integer, primary_key=True)
    network_id = Column(Integer, ForeignKey('network_structures.id'), nullable=False)
    component_id = Column(String)  # e.g., 'DP1', 'MC1'
    component_type = Column(String)  # e.g., 'Distribution Point', 'Canal'
    label = Column(String)
    properties = Column(JSON)
    
    network = relationship("NetworkStructure", back_populates="components")

class Analysis(Base):
    __tablename__ = 'analyses'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    analysis_date = Column(DateTime, default=datetime.utcnow)
    file_path = Column(String)
    status = Column(String)
    
    confidence_level = Column(Float)
    signal_threshold = Column(Float)
    use_detrending = Column(Boolean, default=False)
    detrending_method = Column(String)
    
    project = relationship("Project", back_populates="analyses")
    results = relationship("AnalysisResult", back_populates="analysis", cascade="all, delete-orphan")

class AnalysisResult(Base):
    __tablename__ = 'analysis_results'
    
    id = Column(Integer, primary_key=True)
    analysis_id = Column(Integer, ForeignKey('analyses.id'), nullable=False)
    
    timestamp = Column(DateTime)
    original_value = Column(Float)
    processed_value = Column(Float)
    anomaly_score = Column(Float)
    is_anomaly = Column(Boolean, default=False)
    
    mean = Column(Float)
    std_dev = Column(Float)
    min_value = Column(Float)
    max_value = Column(Float)
    
    analysis = relationship("Analysis", back_populates="results")

# Database Operations
class DatabaseManager:
    def __init__(self, db_url: str = "sqlite:///qushtepa_irrigation.db"):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        return self.SessionLocal()

# Global database manager instance
db_manager = DatabaseManager()

def get_db() -> Session:
    """Dependency to get database session"""
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()
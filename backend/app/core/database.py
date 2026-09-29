"""SQLAlchemy database foundation; SQLite by default, PostgreSQL-ready via DATABASE_URL."""
from datetime import datetime, timezone
from pathlib import Path
import os
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.types import JSON
ROOT = Path(__file__).resolve().parents[2]
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'cybertrace.db'}")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
class Base(DeclarativeBase): pass
def now(): return datetime.now(timezone.utc)
class TelemetryBatch(Base):
    __tablename__="telemetry_batches"; id:Mapped[int]=mapped_column(primary_key=True); filename:Mapped[str]=mapped_column(String(255),default="telemetry.json"); source_type:Mapped[str]=mapped_column(String(40),default="json"); event_count:Mapped[int]=mapped_column(Integer,default=0); uploaded_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); events:Mapped[list["TelemetryEvent"]]=relationship(back_populates="batch")
class TelemetryEvent(Base):
    __tablename__="telemetry_events"; id:Mapped[int]=mapped_column(primary_key=True); event_id:Mapped[str]=mapped_column(String(100),unique=True,index=True); timestamp:Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True); event_type:Mapped[str]=mapped_column(String(30),index=True); source_host:Mapped[str|None]=mapped_column(String(100),nullable=True); destination_host:Mapped[str|None]=mapped_column(String(100),nullable=True); host:Mapped[str|None]=mapped_column(String(100),index=True,nullable=True); username:Mapped[str|None]=mapped_column(String(100),nullable=True); source_ip:Mapped[str|None]=mapped_column(String(50),nullable=True); destination_ip:Mapped[str|None]=mapped_column(String(50),nullable=True); action:Mapped[str|None]=mapped_column(String(100),nullable=True); severity:Mapped[str]=mapped_column(String(20),default="low"); raw_data:Mapped[dict]=mapped_column(JSON,default=dict); batch_id:Mapped[int]=mapped_column(ForeignKey("telemetry_batches.id")); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); batch:Mapped[TelemetryBatch]=relationship(back_populates="events")
class Host(Base):
    __tablename__="hosts"; id:Mapped[int]=mapped_column(primary_key=True); hostname:Mapped[str]=mapped_column(String(100),unique=True,index=True); ip_address:Mapped[str|None]=mapped_column(String(50),nullable=True); asset_type:Mapped[str]=mapped_column(String(40),default="endpoint"); criticality:Mapped[int]=mapped_column(Integer,default=50); status:Mapped[str]=mapped_column(String(30),default="normal"); risk_score:Mapped[float]=mapped_column(Float,default=0); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class UserIdentity(Base):
    __tablename__="user_identities"; id:Mapped[int]=mapped_column(primary_key=True); username:Mapped[str]=mapped_column(String(100),index=True); domain:Mapped[str|None]=mapped_column(String(100),nullable=True); privilege_level:Mapped[str]=mapped_column(String(30),default="standard")
class Incident(Base):
    __tablename__="incidents"; id:Mapped[int]=mapped_column(primary_key=True); title:Mapped[str]=mapped_column(String(200)); severity:Mapped[str]=mapped_column(String(30),default="medium"); status:Mapped[str]=mapped_column(String(30),default="analysis_started"); confidence:Mapped[float]=mapped_column(Float,default=0); root_cause_host:Mapped[str|None]=mapped_column(String(100),nullable=True); batch_id:Mapped[int|None]=mapped_column(ForeignKey("telemetry_batches.id"),nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
class AttackTechnique(Base):
    __tablename__="attack_techniques"; id:Mapped[int]=mapped_column(primary_key=True); technique_id:Mapped[str]=mapped_column(String(20),unique=True); name:Mapped[str]=mapped_column(String(150)); tactic:Mapped[str]=mapped_column(String(80)); description:Mapped[str]=mapped_column(Text,default="")
class IncidentTechnique(Base):
    __tablename__="incident_techniques"; id:Mapped[int]=mapped_column(primary_key=True); incident_id:Mapped[int]=mapped_column(ForeignKey("incidents.id")); technique_id:Mapped[int]=mapped_column(ForeignKey("attack_techniques.id")); host_id:Mapped[int|None]=mapped_column(ForeignKey("hosts.id"),nullable=True); confidence:Mapped[float]=mapped_column(Float,default=0); evidence:Mapped[str]=mapped_column(Text,default="")
class Relationship(Base):
    __tablename__="relationships"; id:Mapped[int]=mapped_column(primary_key=True); source_type:Mapped[str]=mapped_column(String(30)); source_id:Mapped[str]=mapped_column(String(100)); target_type:Mapped[str]=mapped_column(String(30)); target_id:Mapped[str]=mapped_column(String(100)); relationship_type:Mapped[str]=mapped_column(String(60)); timestamp:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); confidence:Mapped[float]=mapped_column(Float,default=0)
class Prediction(Base):
    __tablename__="predictions"; id:Mapped[int]=mapped_column(primary_key=True); incident_id:Mapped[int]=mapped_column(ForeignKey("incidents.id")); target_host_id:Mapped[int]=mapped_column(ForeignKey("hosts.id")); score:Mapped[float]=mapped_column(Float); confidence:Mapped[float]=mapped_column(Float); reasons:Mapped[list]=mapped_column(JSON,default=list); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
def init_db(): Path(ROOT/"data").mkdir(exist_ok=True); Base.metadata.create_all(engine)

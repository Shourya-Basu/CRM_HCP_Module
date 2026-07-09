import uuid
import datetime as dt
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Float, Integer
from sqlalchemy.orm import relationship

from app.database import Base

def gen_id() -> str:
    return str(uuid.uuid4())

class HCP(Base):
    __tablename__ = "hcps"

    id = Column(String(36), primary_key=True, default=gen_id)
    name = Column(String(255), nullable=False)
    specialty = Column(String(255))
    institution = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    interactions = relationship("Interaction", back_populates="hcp")


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(String(36), primary_key=True, default=gen_id)
    hcp_id = Column(String(36), ForeignKey("hcps.id"), nullable=False)
    interaction_type = Column(String(50), default="Meeting")  
    date = Column(String(20))
    time = Column(String(20))
    attendees = Column(Text) 
    topics_discussed = Column(Text)
    sentiment = Column(String(20), default="Neutral")  
    outcomes = Column(Text)
    follow_up_actions = Column(Text)
    source = Column(String(20), default="form") 
    raw_transcript = Column(Text)  
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")
    materials = relationship("InteractionMaterial", back_populates="interaction", cascade="all, delete-orphan")
    samples = relationship("InteractionSample", back_populates="interaction", cascade="all, delete-orphan")


class Material(Base):
    __tablename__ = "materials"

    id = Column(String(36), primary_key=True, default=gen_id)
    name = Column(String(255), nullable=False)
    product = Column(String(255))


class InteractionMaterial(Base):
    __tablename__ = "interaction_materials"

    id = Column(String(36), primary_key=True, default=gen_id)
    interaction_id = Column(String(36), ForeignKey("interactions.id"))
    material_id = Column(String(36), ForeignKey("materials.id"))
    material_name = Column(String(255))

    interaction = relationship("Interaction", back_populates="materials")


class Sample(Base):
    __tablename__ = "samples"

    id = Column(String(36), primary_key=True, default=gen_id)
    name = Column(String(255), nullable=False)
    lot_number = Column(String(100))
    quantity_available = Column(Integer, default=0)


class InteractionSample(Base):
    __tablename__ = "interaction_samples"

    id = Column(String(36), primary_key=True, default=gen_id)
    interaction_id = Column(String(36), ForeignKey("interactions.id"))
    sample_id = Column(String(36), ForeignKey("samples.id"))
    sample_name = Column(String(255))
    quantity = Column(Integer, default=1)
    lot_number = Column(String(100))

    interaction = relationship("Interaction", back_populates="samples")

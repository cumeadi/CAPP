from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

    wallet = relationship("Wallet", back_populates="owner", uselist=False)
    contacts = relationship("Contact", back_populates="user")

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    address = Column(String)
    network = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="contacts")

class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, unique=True, index=True)
    encrypted_private_key = Column(String) # Simulated simulation
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="wallet")

class AgentLog(Base):
    __tablename__ = "agent_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    agent_type = Column(String) # 'MARKET', 'COMPLIANCE', 'LIQUIDITY'
    details = Column(String)
    action = Column(String)

class MarketAnalysisLog(Base):
    __tablename__ = "market_analysis_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    symbol = Column(String)
    risk_level = Column(String)
    recommendation = Column(String)
    reasoning = Column(String)

class AgentChatLog(Base):
    __tablename__ = "agent_chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_query = Column(String)
    agent_response = Column(String)

class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id = Column(String, primary_key=True, index=True) # sub_abc123
    agent_id = Column(String, index=True)
    event_type = Column(String, index=True)
    corridor = Column(String, index=True)
    threshold = Column(String) # JSON string
    webhook_url = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CorridorMetricsHistory(Base):
    __tablename__ = "corridor_metrics_history"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    corridor = Column(String, index=True) # e.g. "USDC-NGN"
    liquidity_depth = Column(Float)
    avg_fee_pct = Column(Float)
    success_rate = Column(Float)
    tx_volume_usd = Column(Float)

class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    agent_id = Column(String, index=True)
    severity = Column(String) # LOW, MEDIUM, HIGH, CRITICAL
    rule_triggered = Column(String) # e.g. "VELOCITY_SPIKE", "CORRIDOR_ABUSE"
    details = Column(String) # JSON string
    resolved = Column(Boolean, default=False)

class PaymentMemoryRecord(Base):
    __tablename__ = "payment_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    tx_hash = Column(String, index=True)
    corridor = Column(String, index=True) # e.g. "USD-KES"
    target_chain = Column(String)
    amount_usd = Column(Float)
    execution_time_ms = Column(Integer)
    success = Column(Boolean)
    error_reason = Column(String, nullable=True)

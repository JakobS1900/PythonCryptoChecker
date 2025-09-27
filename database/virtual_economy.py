"""Virtual economy models for CryptoChecker Version3"""

from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from .models import Base
import uuid

class VirtualWallet(Base):
    """Virtual wallet for storing GEM coins and related stats."""
    __tablename__ = "virtual_wallets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Currency balances
    gem_coins = Column(Float, default=1000.0)
    experience_points = Column(Integer, default=0)
    premium_tokens = Column(Integer, default=0)
    
    # Statistics
    total_gems_earned = Column(Float, default=1000.0)
    total_gems_spent = Column(Float, default=0.0)
    level = Column(Integer, default=1)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VirtualTransaction(Base):
    """Record of virtual currency transactions."""
    __tablename__ = "virtual_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_id = Column(String, ForeignKey("virtual_wallets.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Transaction details
    amount = Column(Float, nullable=False)
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False)
    source = Column(String, nullable=False)
    description = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
"""
Peer-to-Peer Trading Marketplace - Enables users to trade cryptocurrencies directly with each other.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, Integer

from database import get_db_session, Base, VirtualCryptoHolding
from virtual_economy import virtual_economy_engine
from .portfolio_manager import portfolio_manager, PortfolioError, InsufficientFundsError, InvalidTradeError
from logger import logger


class TradeOfferStatus(Enum):
    ACTIVE = "ACTIVE"
    MATCHED = "MATCHED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class TradeOfferType(Enum):
    BUY = "BUY"    # User wants to buy crypto with GEMs
    SELL = "SELL"  # User wants to sell crypto for GEMs
    SWAP = "SWAP"  # User wants to swap one crypto for another


class P2PTradeOffer(Base):
    """Peer-to-peer trade offer model."""
    __tablename__ = "p2p_trade_offers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    creator_id = Column(String, nullable=False, index=True)
    
    # Trade Details
    offer_type = Column(String, nullable=False)  # BUY, SELL, SWAP
    crypto_symbol = Column(String, nullable=False, index=True)
    crypto_amount = Column(Float, nullable=False)
    
    # Pricing (for BUY/SELL orders)
    price_per_unit = Column(Float)  # GEMs per crypto unit
    total_gems = Column(Float)  # Total GEM value
    
    # Swap Details (for SWAP orders)
    wanted_crypto_symbol = Column(String)  # What they want in exchange
    wanted_crypto_amount = Column(Float)   # Amount they want
    
    # Offer Configuration
    min_trade_amount = Column(Float, default=0.0)
    max_trade_amount = Column(Float)
    is_partial_fill_allowed = Column(Boolean, default=True)
    
    # Status and Timing
    status = Column(String, default=TradeOfferStatus.ACTIVE.value, index=True)
    expires_at = Column(DateTime)
    
    # Metadata
    description = Column(Text)
    tags = Column(Text)  # Comma-separated tags
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class P2PTrade(Base):
    """Completed peer-to-peer trade record."""
    __tablename__ = "p2p_trades"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    offer_id = Column(String, nullable=False, index=True)
    
    # Trade Participants
    seller_id = Column(String, nullable=False, index=True)
    buyer_id = Column(String, nullable=False, index=True)
    
    # Trade Details
    crypto_symbol = Column(String, nullable=False)
    crypto_amount = Column(Float, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    total_gems = Column(Float, nullable=False)
    
    # Fees and Costs
    marketplace_fee = Column(Float, default=0.0)
    seller_fee = Column(Float, default=0.0)
    buyer_fee = Column(Float, default=0.0)
    
    # Status
    status = Column(String, default="PENDING")
    completed_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class P2PMarketplace:
    """Manages peer-to-peer cryptocurrency trading marketplace."""
    
    def __init__(self):
        self.marketplace_fee_rate = 0.01  # 1% marketplace fee
        self.min_offer_duration_hours = 1
        self.max_offer_duration_hours = 168  # 7 days
        self.default_offer_duration_hours = 24
    
    async def create_trade_offer(
        self,
        user_id: str,
        offer_type: TradeOfferType,
        crypto_symbol: str,
        crypto_amount: float,
        price_per_unit: Optional[float] = None,
        wanted_crypto_symbol: Optional[str] = None,
        wanted_crypto_amount: Optional[float] = None,
        duration_hours: int = 24,
        min_trade_amount: float = 0.0,
        is_partial_fill_allowed: bool = True,
        description: str = "",
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """Create a new peer-to-peer trade offer."""
        try:
            async with get_db_session() as session:
                # Validate inputs
                if duration_hours < self.min_offer_duration_hours or duration_hours > self.max_offer_duration_hours:
                    raise InvalidTradeError(f"Duration must be between {self.min_offer_duration_hours} and {self.max_offer_duration_hours} hours")
                
                if crypto_amount <= 0:
                    raise InvalidTradeError("Crypto amount must be positive")
                
                # Validate offer type specific requirements
                if offer_type == TradeOfferType.SWAP:
                    if not wanted_crypto_symbol or not wanted_crypto_amount:
                        raise InvalidTradeError("Swap offers require wanted crypto symbol and amount")
                    if wanted_crypto_amount <= 0:
                        raise InvalidTradeError("Wanted crypto amount must be positive")
                else:
                    if not price_per_unit or price_per_unit <= 0:
                        raise InvalidTradeError("Buy/Sell offers require positive price per unit")
                
                # Check user's available balance/holdings
                await self._validate_user_resources(session, user_id, offer_type, crypto_symbol, crypto_amount, price_per_unit)
                
                # Calculate expiration
                expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
                
                # Create offer
                total_gems = (crypto_amount * price_per_unit) if price_per_unit else None
                
                offer = P2PTradeOffer(
                    creator_id=user_id,
                    offer_type=offer_type.value,
                    crypto_symbol=crypto_symbol.upper(),
                    crypto_amount=crypto_amount,
                    price_per_unit=price_per_unit,
                    total_gems=total_gems,
                    wanted_crypto_symbol=wanted_crypto_symbol.upper() if wanted_crypto_symbol else None,
                    wanted_crypto_amount=wanted_crypto_amount,
                    min_trade_amount=min_trade_amount,
                    max_trade_amount=crypto_amount,
                    is_partial_fill_allowed=is_partial_fill_allowed,
                    expires_at=expires_at,
                    description=description,
                    tags=",".join(tags) if tags else ""
                )
                
                session.add(offer)
                await session.commit()
                await session.refresh(offer)
                
                logger.info(f"User {user_id} created {offer_type.value} offer for {crypto_amount} {crypto_symbol}")
                
                return {
                    "offer_id": offer.id,
                    "offer_type": offer.offer_type,
                    "crypto_symbol": offer.crypto_symbol,
                    "crypto_amount": offer.crypto_amount,
                    "price_per_unit": offer.price_per_unit,
                    "total_gems": offer.total_gems,
                    "wanted_crypto_symbol": offer.wanted_crypto_symbol,
                    "wanted_crypto_amount": offer.wanted_crypto_amount,
                    "expires_at": offer.expires_at.isoformat(),
                    "status": offer.status,
                    "created_at": offer.created_at.isoformat()
                }
                
        except (InvalidTradeError, InsufficientFundsError) as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to create trade offer: {e}")
            raise PortfolioError(f"Failed to create trade offer: {e}")
    
    async def _validate_user_resources(
        self,
        session: AsyncSession,
        user_id: str,
        offer_type: TradeOfferType,
        crypto_symbol: str,
        crypto_amount: float,
        price_per_unit: Optional[float]
    ):
        """Validate that user has sufficient resources for the offer."""
        if offer_type == TradeOfferType.SELL:
            # Check crypto holdings for sell orders
            holding_query = select(VirtualCryptoHolding).where(
                and_(
                    VirtualCryptoHolding.user_id == user_id,
                    VirtualCryptoHolding.crypto_symbol == crypto_symbol.upper()
                )
            )
            result = await session.execute(holding_query)
            holding = result.scalar_one_or_none()
            
            if not holding or holding.amount < crypto_amount:
                raise InsufficientFundsError(f"Insufficient {crypto_symbol} balance for sell offer")
        
        elif offer_type == TradeOfferType.BUY and price_per_unit:
            # Check GEM balance for buy orders
            wallet = await virtual_economy_engine.get_user_wallet(session, user_id)
            total_cost = crypto_amount * price_per_unit
            
            if not wallet or wallet.gem_balance < total_cost:
                raise InsufficientFundsError("Insufficient GEM balance for buy offer")
    
    async def get_marketplace_offers(
        self,
        offer_type: Optional[TradeOfferType] = None,
        crypto_symbol: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get marketplace trade offers with filtering."""
        try:
            async with get_db_session() as session:
                query = select(P2PTradeOffer).where(
                    P2PTradeOffer.status == TradeOfferStatus.ACTIVE.value
                )
                
                # Apply filters
                if offer_type:
                    query = query.where(P2PTradeOffer.offer_type == offer_type.value)
                
                if crypto_symbol:
                    query = query.where(P2PTradeOffer.crypto_symbol == crypto_symbol.upper())
                
                if min_amount:
                    query = query.where(P2PTradeOffer.crypto_amount >= min_amount)
                
                if max_amount:
                    query = query.where(P2PTradeOffer.crypto_amount <= max_amount)
                
                if min_price:
                    query = query.where(P2PTradeOffer.price_per_unit >= min_price)
                
                if max_price:
                    query = query.where(P2PTradeOffer.price_per_unit <= max_price)
                
                if user_id:
                    query = query.where(P2PTradeOffer.creator_id == user_id)
                
                # Remove expired offers
                query = query.where(P2PTradeOffer.expires_at > datetime.utcnow())
                
                # Sort by creation date (newest first)
                query = query.order_by(P2PTradeOffer.created_at.desc())
                
                # Get total count
                count_query = select(func.count(P2PTradeOffer.id)).select_from(query.subquery())
                total_result = await session.execute(count_query)
                total_count = total_result.scalar()
                
                # Apply pagination
                query = query.limit(limit).offset(offset)
                
                result = await session.execute(query)
                offers = result.scalars().all()
                
                # Convert to dict format
                offer_list = []
                for offer in offers:
                    offer_dict = {
                        "offer_id": offer.id,
                        "creator_id": offer.creator_id,
                        "offer_type": offer.offer_type,
                        "crypto_symbol": offer.crypto_symbol,
                        "crypto_amount": offer.crypto_amount,
                        "price_per_unit": offer.price_per_unit,
                        "total_gems": offer.total_gems,
                        "wanted_crypto_symbol": offer.wanted_crypto_symbol,
                        "wanted_crypto_amount": offer.wanted_crypto_amount,
                        "min_trade_amount": offer.min_trade_amount,
                        "is_partial_fill_allowed": offer.is_partial_fill_allowed,
                        "description": offer.description,
                        "tags": offer.tags.split(",") if offer.tags else [],
                        "expires_at": offer.expires_at.isoformat(),
                        "created_at": offer.created_at.isoformat(),
                        "time_remaining_hours": (offer.expires_at - datetime.utcnow()).total_seconds() / 3600
                    }
                    offer_list.append(offer_dict)
                
                return {
                    "offers": offer_list,
                    "total_count": total_count,
                    "page_info": {
                        "limit": limit,
                        "offset": offset,
                        "has_more": offset + len(offers) < total_count
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get marketplace offers: {e}")
            raise PortfolioError(f"Failed to retrieve offers: {e}")
    
    async def accept_trade_offer(
        self,
        user_id: str,
        offer_id: str,
        trade_amount: Optional[float] = None
    ) -> Dict[str, Any]:
        """Accept a trade offer and execute the trade."""
        try:
            async with get_db_session() as session:
                # Get the offer
                offer_query = select(P2PTradeOffer).where(
                    and_(
                        P2PTradeOffer.id == offer_id,
                        P2PTradeOffer.status == TradeOfferStatus.ACTIVE.value
                    )
                )
                result = await session.execute(offer_query)
                offer = result.scalar_one_or_none()
                
                if not offer:
                    raise InvalidTradeError("Trade offer not found or not active")
                
                if offer.creator_id == user_id:
                    raise InvalidTradeError("Cannot accept your own trade offer")
                
                if offer.expires_at <= datetime.utcnow():
                    # Mark as expired
                    offer.status = TradeOfferStatus.EXPIRED.value
                    await session.commit()
                    raise InvalidTradeError("Trade offer has expired")
                
                # Determine trade amount
                if trade_amount is None:
                    trade_amount = offer.crypto_amount
                else:
                    if not offer.is_partial_fill_allowed and trade_amount != offer.crypto_amount:
                        raise InvalidTradeError("Partial fills not allowed for this offer")
                    
                    if trade_amount < offer.min_trade_amount:
                        raise InvalidTradeError(f"Trade amount below minimum: {offer.min_trade_amount}")
                    
                    if trade_amount > offer.crypto_amount:
                        raise InvalidTradeError("Trade amount exceeds offer amount")
                
                # Execute the trade based on offer type
                if offer.offer_type == TradeOfferType.SELL.value:
                    # User is buying crypto from offer creator
                    await self._execute_p2p_buy_trade(session, offer, user_id, trade_amount)
                elif offer.offer_type == TradeOfferType.BUY.value:
                    # User is selling crypto to offer creator
                    await self._execute_p2p_sell_trade(session, offer, user_id, trade_amount)
                elif offer.offer_type == TradeOfferType.SWAP.value:
                    # Crypto swap between users
                    await self._execute_p2p_swap_trade(session, offer, user_id, trade_amount)
                
                # Update offer status
                if trade_amount == offer.crypto_amount:
                    offer.status = TradeOfferStatus.COMPLETED.value
                else:
                    offer.crypto_amount -= trade_amount
                    if offer.total_gems:
                        offer.total_gems = offer.crypto_amount * offer.price_per_unit
                
                offer.updated_at = datetime.utcnow()
                await session.commit()
                
                logger.info(f"User {user_id} accepted trade offer {offer_id} for {trade_amount} {offer.crypto_symbol}")
                
                return {
                    "trade_id": str(uuid.uuid4()),  # Generate trade ID
                    "offer_id": offer_id,
                    "trade_type": offer.offer_type,
                    "crypto_symbol": offer.crypto_symbol,
                    "trade_amount": trade_amount,
                    "price_per_unit": offer.price_per_unit,
                    "status": "COMPLETED",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except (InvalidTradeError, InsufficientFundsError) as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to accept trade offer: {e}")
            raise PortfolioError(f"Failed to execute trade: {e}")
    
    async def _execute_p2p_buy_trade(
        self,
        session: AsyncSession,
        offer: P2PTradeOffer,
        buyer_id: str,
        trade_amount: float
    ):
        """Execute a P2P buy trade (buyer buys crypto from seller)."""
        total_cost = trade_amount * offer.price_per_unit
        marketplace_fee = total_cost * self.marketplace_fee_rate
        seller_receives = total_cost - marketplace_fee
        
        # Check buyer's GEM balance
        buyer_wallet = await virtual_economy_engine.get_user_wallet(session, buyer_id)
        if not buyer_wallet or buyer_wallet.gem_balance < total_cost:
            raise InsufficientFundsError("Insufficient GEM balance")
        
        # Check seller's crypto balance
        seller_holding_query = select(VirtualCryptoHolding).where(
            and_(
                VirtualCryptoHolding.user_id == offer.creator_id,
                VirtualCryptoHolding.crypto_symbol == offer.crypto_symbol
            )
        )
        result = await session.execute(seller_holding_query)
        seller_holding = result.scalar_one_or_none()
        
        if not seller_holding or seller_holding.amount < trade_amount:
            raise InsufficientFundsError(f"Seller has insufficient {offer.crypto_symbol}")
        
        # Execute transfers
        # Buyer pays GEMs
        await virtual_economy_engine.update_wallet_balance(
            session, buyer_id, "GEM_COINS", -total_cost,
            f"P2P buy {trade_amount} {offer.crypto_symbol} @ {offer.price_per_unit}"
        )
        
        # Seller receives GEMs (minus fee)
        await virtual_economy_engine.update_wallet_balance(
            session, offer.creator_id, "GEM_COINS", seller_receives,
            f"P2P sell {trade_amount} {offer.crypto_symbol} @ {offer.price_per_unit}"
        )
        
        # Transfer crypto from seller to buyer
        await self._transfer_crypto(session, offer.creator_id, buyer_id, offer.crypto_symbol, trade_amount, offer.price_per_unit)
        
        # Record marketplace fee
        # Note: In a full system, you'd track marketplace revenue
    
    async def _execute_p2p_sell_trade(
        self,
        session: AsyncSession,
        offer: P2PTradeOffer,
        seller_id: str,
        trade_amount: float
    ):
        """Execute a P2P sell trade (seller sells crypto to buyer)."""
        total_cost = trade_amount * offer.price_per_unit
        marketplace_fee = total_cost * self.marketplace_fee_rate
        seller_receives = total_cost - marketplace_fee
        
        # Check seller's crypto balance
        seller_holding_query = select(VirtualCryptoHolding).where(
            and_(
                VirtualCryptoHolding.user_id == seller_id,
                VirtualCryptoHolding.crypto_symbol == offer.crypto_symbol
            )
        )
        result = await session.execute(seller_holding_query)
        seller_holding = result.scalar_one_or_none()
        
        if not seller_holding or seller_holding.amount < trade_amount:
            raise InsufficientFundsError(f"Insufficient {offer.crypto_symbol} balance")
        
        # Check buyer's GEM balance
        buyer_wallet = await virtual_economy_engine.get_user_wallet(session, offer.creator_id)
        if not buyer_wallet or buyer_wallet.gem_balance < total_cost:
            raise InsufficientFundsError("Buyer has insufficient GEM balance")
        
        # Execute transfers
        # Buyer (offer creator) pays GEMs
        await virtual_economy_engine.update_wallet_balance(
            session, offer.creator_id, "GEM_COINS", -total_cost,
            f"P2P buy {trade_amount} {offer.crypto_symbol} @ {offer.price_per_unit}"
        )
        
        # Seller receives GEMs (minus fee)
        await virtual_economy_engine.update_wallet_balance(
            session, seller_id, "GEM_COINS", seller_receives,
            f"P2P sell {trade_amount} {offer.crypto_symbol} @ {offer.price_per_unit}"
        )
        
        # Transfer crypto from seller to buyer
        await self._transfer_crypto(session, seller_id, offer.creator_id, offer.crypto_symbol, trade_amount, offer.price_per_unit)
    
    async def _execute_p2p_swap_trade(
        self,
        session: AsyncSession,
        offer: P2PTradeOffer,
        swapper_id: str,
        trade_amount: float
    ):
        """Execute a P2P swap trade (crypto for crypto)."""
        # Calculate proportional wanted amount for partial fills
        wanted_amount = (trade_amount / offer.crypto_amount) * offer.wanted_crypto_amount
        
        # Check both users' crypto balances
        # Offer creator has the offered crypto
        creator_holding_query = select(VirtualCryptoHolding).where(
            and_(
                VirtualCryptoHolding.user_id == offer.creator_id,
                VirtualCryptoHolding.crypto_symbol == offer.crypto_symbol
            )
        )
        result = await session.execute(creator_holding_query)
        creator_holding = result.scalar_one_or_none()
        
        if not creator_holding or creator_holding.amount < trade_amount:
            raise InsufficientFundsError(f"Creator has insufficient {offer.crypto_symbol}")
        
        # Swapper has the wanted crypto
        swapper_holding_query = select(VirtualCryptoHolding).where(
            and_(
                VirtualCryptoHolding.user_id == swapper_id,
                VirtualCryptoHolding.crypto_symbol == offer.wanted_crypto_symbol
            )
        )
        result = await session.execute(swapper_holding_query)
        swapper_holding = result.scalar_one_or_none()
        
        if not swapper_holding or swapper_holding.amount < wanted_amount:
            raise InsufficientFundsError(f"Insufficient {offer.wanted_crypto_symbol} balance")
        
        # Execute the swap
        # Transfer offered crypto: creator -> swapper
        await self._transfer_crypto(session, offer.creator_id, swapper_id, offer.crypto_symbol, trade_amount, 0)
        
        # Transfer wanted crypto: swapper -> creator
        await self._transfer_crypto(session, swapper_id, offer.creator_id, offer.wanted_crypto_symbol, wanted_amount, 0)
    
    async def _transfer_crypto(
        self,
        session: AsyncSession,
        from_user_id: str,
        to_user_id: str,
        crypto_symbol: str,
        amount: float,
        price: float
    ):
        """Transfer cryptocurrency between users."""
        # Remove from sender
        await portfolio_manager._update_crypto_holding(
            session, from_user_id, crypto_symbol, -amount, price, "SELL"
        )
        
        # Add to recipient
        await portfolio_manager._update_crypto_holding(
            session, to_user_id, crypto_symbol, amount, price, "BUY"
        )
    
    async def cancel_trade_offer(self, user_id: str, offer_id: str) -> bool:
        """Cancel a user's trade offer."""
        try:
            async with get_db_session() as session:
                # Get and validate offer
                offer_query = select(P2PTradeOffer).where(
                    and_(
                        P2PTradeOffer.id == offer_id,
                        P2PTradeOffer.creator_id == user_id,
                        P2PTradeOffer.status == TradeOfferStatus.ACTIVE.value
                    )
                )
                result = await session.execute(offer_query)
                offer = result.scalar_one_or_none()
                
                if not offer:
                    raise InvalidTradeError("Trade offer not found or cannot be cancelled")
                
                # Cancel the offer
                offer.status = TradeOfferStatus.CANCELLED.value
                offer.updated_at = datetime.utcnow()
                await session.commit()
                
                logger.info(f"User {user_id} cancelled trade offer {offer_id}")
                return True
                
        except InvalidTradeError:
            raise
        except Exception as e:
            logger.error(f"Failed to cancel trade offer: {e}")
            raise PortfolioError(f"Failed to cancel offer: {e}")
    
    async def get_user_offers(self, user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all trade offers created by a user."""
        try:
            async with get_db_session() as session:
                query = select(P2PTradeOffer).where(P2PTradeOffer.creator_id == user_id)
                
                if status:
                    query = query.where(P2PTradeOffer.status == status)
                
                query = query.order_by(P2PTradeOffer.created_at.desc())
                
                result = await session.execute(query)
                offers = result.scalars().all()
                
                offer_list = []
                for offer in offers:
                    offer_dict = {
                        "offer_id": offer.id,
                        "offer_type": offer.offer_type,
                        "crypto_symbol": offer.crypto_symbol,
                        "crypto_amount": offer.crypto_amount,
                        "price_per_unit": offer.price_per_unit,
                        "total_gems": offer.total_gems,
                        "wanted_crypto_symbol": offer.wanted_crypto_symbol,
                        "wanted_crypto_amount": offer.wanted_crypto_amount,
                        "status": offer.status,
                        "expires_at": offer.expires_at.isoformat(),
                        "created_at": offer.created_at.isoformat(),
                        "is_expired": offer.expires_at <= datetime.utcnow()
                    }
                    offer_list.append(offer_dict)
                
                return offer_list
                
        except Exception as e:
            logger.error(f"Failed to get user offers: {e}")
            raise PortfolioError(f"Failed to retrieve user offers: {e}")
    
    async def cleanup_expired_offers(self) -> int:
        """Clean up expired trade offers."""
        try:
            async with get_db_session() as session:
                # Find expired active offers
                expired_query = select(P2PTradeOffer).where(
                    and_(
                        P2PTradeOffer.status == TradeOfferStatus.ACTIVE.value,
                        P2PTradeOffer.expires_at <= datetime.utcnow()
                    )
                )
                
                result = await session.execute(expired_query)
                expired_offers = result.scalars().all()
                
                # Mark as expired
                for offer in expired_offers:
                    offer.status = TradeOfferStatus.EXPIRED.value
                    offer.updated_at = datetime.utcnow()
                
                await session.commit()
                
                logger.info(f"Cleaned up {len(expired_offers)} expired trade offers")
                return len(expired_offers)
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired offers: {e}")
            return 0
    
    async def get_marketplace_stats(self) -> Dict[str, Any]:
        """Get marketplace statistics."""
        try:
            async with get_db_session() as session:
                # Active offers count
                active_count_query = select(func.count(P2PTradeOffer.id)).where(
                    P2PTradeOffer.status == TradeOfferStatus.ACTIVE.value
                )
                active_result = await session.execute(active_count_query)
                active_offers = active_result.scalar()
                
                # Completed trades count (last 24 hours)
                yesterday = datetime.utcnow() - timedelta(days=1)
                completed_count_query = select(func.count(P2PTrade.id)).where(
                    P2PTrade.created_at >= yesterday
                )
                completed_result = await session.execute(completed_count_query)
                recent_trades = completed_result.scalar()
                
                # Popular crypto symbols
                crypto_popularity_query = select(
                    P2PTradeOffer.crypto_symbol,
                    func.count(P2PTradeOffer.id).label('count')
                ).where(
                    P2PTradeOffer.status == TradeOfferStatus.ACTIVE.value
                ).group_by(P2PTradeOffer.crypto_symbol).order_by(func.count(P2PTradeOffer.id).desc()).limit(10)
                
                crypto_result = await session.execute(crypto_popularity_query)
                popular_cryptos = [{"symbol": row.crypto_symbol, "active_offers": row.count} for row in crypto_result]
                
                return {
                    "active_offers": active_offers,
                    "trades_24h": recent_trades,
                    "marketplace_fee_rate": self.marketplace_fee_rate * 100,  # As percentage
                    "popular_cryptocurrencies": popular_cryptos,
                    "last_updated": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get marketplace stats: {e}")
            return {}


# Global instance
p2p_marketplace = P2PMarketplace()
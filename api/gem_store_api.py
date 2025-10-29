"""
GEM Store API endpoints for CryptoChecker Marketplace.

Handles GEM package purchases (simulated/educational only).
No real payment processing - this is for demonstration purposes.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

from database.database import get_db
from database.models import User, GemPurchase, Wallet, Transaction, TransactionType
from api.auth_api import require_authentication
from config.gem_packages import GEM_PACKAGES, get_package, get_all_packages, validate_package_id

router = APIRouter()


# ==================== REQUEST/RESPONSE MODELS ====================

class PackageInfo(BaseModel):
    """GEM package details."""
    id: str
    name: str
    description: str
    gems: int
    bonus_gems: int
    total_gems: int
    price_usd: float
    badge: Optional[str]
    popular: bool
    best_value: bool
    icon: str
    color: str


class PurchaseRequest(BaseModel):
    """GEM purchase request."""
    package_id: str
    payment_method: str  # 'demo_card', 'demo_crypto', 'demo_paypal'


class PurchaseResponse(BaseModel):
    """GEM purchase response."""
    success: bool
    transaction_id: str
    package: PackageInfo
    gems_received: int
    bonus_gems: int
    total_gems: int
    new_balance: float
    purchase_date: str


class PurchaseHistoryItem(BaseModel):
    """Purchase history entry."""
    id: int
    package_id: str
    package_name: str
    gems_amount: int
    bonus_gems: int
    total_gems: int
    price_usd: float
    payment_method: str
    transaction_id: str
    status: str
    created_at: str


class PurchaseHistoryResponse(BaseModel):
    """Purchase history list."""
    purchases: List[PurchaseHistoryItem]
    total_purchased: int
    total_spent: float


# ==================== ENDPOINTS ====================

@router.get("/packages", response_model=List[PackageInfo])
async def get_gem_packages():
    """
    Get all available GEM packages.
    Public endpoint - no authentication required.
    """
    packages = get_all_packages()
    return [PackageInfo(**pkg) for pkg in packages]


@router.post("/purchase", response_model=PurchaseResponse)
async def purchase_gem_package(
    request: PurchaseRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Purchase a GEM package (simulated/educational only).

    **Note**: This is a simulated purchase system for educational purposes.
    No real payment processing occurs. All transactions are virtual.
    """
    # Validate package
    if not validate_package_id(request.package_id):
        raise HTTPException(status_code=400, detail="Invalid package ID")

    package = get_package(request.package_id)

    # Validate payment method
    valid_methods = ['demo_card', 'demo_crypto', 'demo_paypal']
    if request.payment_method not in valid_methods:
        raise HTTPException(status_code=400, detail="Invalid payment method")

    # Generate transaction ID
    transaction_id = f"GEM-{uuid.uuid4().hex[:16].upper()}"

    # Get user's wallet
    wallet_result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id)
    )
    wallet = wallet_result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    # Calculate total GEM
    total_gems = package['gems'] + package['bonus_gems']
    balance_before = wallet.gem_balance

    # Update wallet balance
    wallet.gem_balance += total_gems
    wallet.total_deposited += total_gems

    # Create purchase record
    purchase = GemPurchase(
        user_id=current_user.id,
        package_id=package['id'],
        gems_amount=package['gems'],
        bonus_gems=package['bonus_gems'],
        total_gems=total_gems,
        price_usd=package['price_usd'],
        payment_method=request.payment_method,
        transaction_id=transaction_id,
        status='completed',
        created_at=datetime.utcnow()
    )
    db.add(purchase)

    # Create transaction record
    transaction = Transaction(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        transaction_type=TransactionType.GEM_PURCHASE.value,
        amount=total_gems,
        balance_before=balance_before,
        balance_after=wallet.gem_balance,
        description=f"GEM Purchase - {package['name']} ({transaction_id})",
        created_at=datetime.utcnow()
    )
    db.add(transaction)

    # Commit all changes
    await db.commit()
    await db.refresh(wallet)

    return PurchaseResponse(
        success=True,
        transaction_id=transaction_id,
        package=PackageInfo(**package),
        gems_received=package['gems'],
        bonus_gems=package['bonus_gems'],
        total_gems=total_gems,
        new_balance=wallet.gem_balance,
        purchase_date=datetime.utcnow().isoformat()
    )


@router.get("/purchase-history", response_model=PurchaseHistoryResponse)
async def get_purchase_history(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's GEM purchase history.
    """
    # Get all purchases for user
    result = await db.execute(
        select(GemPurchase)
        .where(GemPurchase.user_id == current_user.id)
        .order_by(desc(GemPurchase.created_at))
    )
    purchases = result.scalars().all()

    # Format response
    purchase_items = []
    total_spent = 0.0

    for purchase in purchases:
        # Get package name
        package = get_package(purchase.package_id)
        package_name = package['name'] if package else purchase.package_id

        purchase_items.append(PurchaseHistoryItem(
            id=purchase.id,
            package_id=purchase.package_id,
            package_name=package_name,
            gems_amount=purchase.gems_amount,
            bonus_gems=purchase.bonus_gems,
            total_gems=purchase.total_gems,
            price_usd=purchase.price_usd,
            payment_method=purchase.payment_method or 'N/A',
            transaction_id=purchase.transaction_id,
            status=purchase.status,
            created_at=purchase.created_at.isoformat()
        ))

        total_spent += purchase.price_usd

    return PurchaseHistoryResponse(
        purchases=purchase_items,
        total_purchased=len(purchases),
        total_spent=total_spent
    )


@router.get("/stats")
async def get_purchase_stats(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's purchase statistics.
    """
    result = await db.execute(
        select(GemPurchase).where(GemPurchase.user_id == current_user.id)
    )
    purchases = result.scalars().all()

    total_purchases = len(purchases)
    total_gems = sum(p.total_gems for p in purchases)
    total_spent = sum(p.price_usd for p in purchases)
    total_bonus = sum(p.bonus_gems for p in purchases)

    # Get most popular package
    package_counts = {}
    for p in purchases:
        package_counts[p.package_id] = package_counts.get(p.package_id, 0) + 1

    favorite_package = max(package_counts.items(), key=lambda x: x[1])[0] if package_counts else None

    return {
        "total_purchases": total_purchases,
        "total_gems_purchased": total_gems,
        "total_bonus_gems": total_bonus,
        "total_spent_usd": total_spent,
        "favorite_package": favorite_package,
        "average_purchase_value": total_spent / total_purchases if total_purchases > 0 else 0
    }

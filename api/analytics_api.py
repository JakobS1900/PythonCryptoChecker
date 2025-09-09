"""
Analytics and monitoring API endpoints.
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from database.database_manager import get_db_session
from auth.auth_manager import get_current_user, require_admin
from analytics.analytics_engine import analytics_engine
from analytics.monitoring import monitoring_system
from logger import logger

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ==================== PYDANTIC MODELS ====================

class UserMetricsResponse(BaseModel):
    """Response model for user metrics."""
    user_id: str
    period_days: int
    profile: dict
    gaming: dict
    achievements: dict
    social: dict
    engagement: dict
    ranking: dict


class PlatformMetricsResponse(BaseModel):
    """Response model for platform metrics."""
    period_days: int
    users: dict
    gaming: dict
    achievements: dict
    social: dict
    onboarding: dict
    engagement: dict
    economy: dict


class RealTimeMetricsResponse(BaseModel):
    """Response model for real-time metrics."""
    timestamp: str
    users_online: int
    games_last_hour: int
    new_signups_24h: int
    achievements_last_hour: int
    system_status: str
    server_uptime: str


class AlertResponse(BaseModel):
    """Response model for system alerts."""
    id: str
    level: str
    title: str
    message: str
    metric: str
    value: float
    threshold: float
    timestamp: str
    resolved: bool


class SystemStatusResponse(BaseModel):
    """Response model for system status."""
    status: str
    timestamp: str
    metrics: dict
    alerts: dict
    uptime: float


# ==================== USER ANALYTICS ENDPOINTS ====================

@router.get("/user/metrics", response_model=Dict[str, Any])
async def get_user_metrics(
    days: int = Query(default=30, ge=1, le=365),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get comprehensive metrics for the current user."""
    try:
        metrics = await analytics_engine.get_user_metrics(db, current_user.id, days)
        
        if "error" in metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=metrics["error"]
            )
        
        return {
            "success": True,
            "data": metrics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/user/{user_id}/metrics", response_model=Dict[str, Any])
async def get_specific_user_metrics(
    user_id: str,
    days: int = Query(default=30, ge=1, le=365),
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """Get metrics for a specific user (admin only)."""
    try:
        metrics = await analytics_engine.get_user_metrics(db, user_id, days)
        
        if "error" in metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=metrics["error"]
            )
        
        return {
            "success": True,
            "data": metrics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# ==================== PLATFORM ANALYTICS ENDPOINTS ====================

@router.get("/platform/metrics", response_model=Dict[str, Any])
async def get_platform_metrics(
    days: int = Query(default=30, ge=1, le=365),
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """Get platform-wide analytics metrics (admin only)."""
    try:
        metrics = await analytics_engine.get_platform_metrics(db, days)
        
        if "error" in metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=metrics["error"]
            )
        
        return {
            "success": True,
            "data": metrics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get platform metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/platform/realtime", response_model=Dict[str, Any])
async def get_realtime_metrics(
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """Get real-time platform metrics (admin only)."""
    try:
        metrics = await analytics_engine.get_real_time_metrics(db)
        
        if "error" in metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=metrics["error"]
            )
        
        return {
            "success": True,
            "data": metrics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get real-time metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/platform/cohort-analysis", response_model=Dict[str, Any])
async def get_cohort_analysis(
    period: str = Query(default="weekly", regex="^(daily|weekly|monthly)$"),
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """Get user cohort analysis (admin only)."""
    try:
        analysis = await analytics_engine.get_user_cohort_analysis(db, period)
        
        if "error" in analysis:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=analysis["error"]
            )
        
        return {
            "success": True,
            "data": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cohort analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/platform/funnel-analysis", response_model=Dict[str, Any])
async def get_funnel_analysis(
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """Get user funnel analysis (admin only)."""
    try:
        analysis = await analytics_engine.get_funnel_analysis(db)
        
        if "error" in analysis:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=analysis["error"]
            )
        
        return {
            "success": True,
            "data": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get funnel analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# ==================== MONITORING ENDPOINTS ====================

@router.get("/monitoring/status", response_model=Dict[str, Any])
async def get_system_status(
    current_user=Depends(require_admin)
):
    """Get current system status and health (admin only)."""
    try:
        status = await monitoring_system.get_current_status()
        
        return {
            "success": True,
            "data": status
        }
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/monitoring/health", response_model=Dict[str, Any])
async def health_check():
    """Public health check endpoint."""
    try:
        health = await monitoring_system.health_check()
        
        if not health["healthy"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="System unhealthy"
            )
        
        return health
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check error"
        )


@router.get("/monitoring/metrics/history", response_model=Dict[str, Any])
async def get_metrics_history(
    hours: int = Query(default=24, ge=1, le=168),
    current_user=Depends(require_admin)
):
    """Get historical metrics data (admin only)."""
    try:
        history = await monitoring_system.get_metrics_history(hours)
        
        return {
            "success": True,
            "data": {
                "hours": hours,
                "metrics": history,
                "total_datapoints": len(history)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get metrics history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/monitoring/alerts", response_model=Dict[str, Any])
async def get_active_alerts(
    current_user=Depends(require_admin)
):
    """Get active system alerts (admin only)."""
    try:
        alerts = monitoring_system.alert_manager.get_active_alerts()
        
        formatted_alerts = []
        for alert in alerts:
            formatted_alerts.append({
                "id": alert.id,
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "metric": alert.metric,
                "value": alert.value,
                "threshold": alert.threshold,
                "timestamp": alert.timestamp.isoformat(),
                "resolved": alert.resolved
            })
        
        return {
            "success": True,
            "data": {
                "total_alerts": len(formatted_alerts),
                "alerts": formatted_alerts
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/monitoring/alerts/{alert_id}/resolve", response_model=Dict[str, Any])
async def resolve_alert(
    alert_id: str,
    current_user=Depends(require_admin)
):
    """Resolve a system alert (admin only)."""
    try:
        resolved = monitoring_system.alert_manager.resolve_alert(alert_id)
        
        if not resolved:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        return {
            "success": True,
            "message": f"Alert {alert_id} resolved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/monitoring/thresholds", response_model=Dict[str, Any])
async def update_alert_thresholds(
    thresholds: Dict[str, Dict[str, float]],
    current_user=Depends(require_admin)
):
    """Update alert thresholds (admin only)."""
    try:
        for metric, values in thresholds.items():
            warning = values.get("warning")
            critical = values.get("critical")
            monitoring_system.set_alert_threshold(metric, warning, critical)
        
        return {
            "success": True,
            "message": f"Updated thresholds for {len(thresholds)} metrics"
        }
        
    except Exception as e:
        logger.error(f"Failed to update thresholds: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# ==================== EVENT TRACKING ENDPOINTS ====================

@router.post("/track/user-action", response_model=Dict[str, Any])
async def track_user_action(
    action: str,
    properties: Optional[Dict[str, Any]] = None,
    current_user=Depends(get_current_user)
):
    """Track a user action for analytics."""
    try:
        await analytics_engine.track_user_action(
            current_user.id, action, properties or {}
        )
        
        return {
            "success": True,
            "message": "Action tracked successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to track user action: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/track/game-event", response_model=Dict[str, Any])
async def track_game_event(
    game_type: str,
    event_type: str,
    properties: Optional[Dict[str, Any]] = None,
    current_user=Depends(get_current_user)
):
    """Track a gaming event for analytics."""
    try:
        await analytics_engine.track_game_event(
            current_user.id, game_type, event_type, properties or {}
        )
        
        return {
            "success": True,
            "message": "Game event tracked successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to track game event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# ==================== DASHBOARD DATA ENDPOINTS ====================

@router.get("/dashboard/summary", response_model=Dict[str, Any])
async def get_dashboard_summary(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get summary data for user dashboard."""
    try:
        # Get user metrics for last 7 days
        user_metrics = await analytics_engine.get_user_metrics(db, current_user.id, 7)
        
        if "error" in user_metrics:
            user_metrics = {
                "gaming": {"total_games": 0, "total_winnings": 0, "win_rate": 0},
                "achievements": {"new_achievements": 0},
                "social": {"total_friends": 0},
                "engagement": {"daily_streak": 0},
                "ranking": {"current_level": 1, "global_rank": 0}
            }
        
        return {
            "success": True,
            "data": {
                "period": "7_days",
                "summary": {
                    "games_played": user_metrics["gaming"]["total_games"],
                    "total_winnings": user_metrics["gaming"]["total_winnings"],
                    "win_rate": user_metrics["gaming"]["win_rate"],
                    "new_achievements": user_metrics["achievements"]["new_achievements"],
                    "friends_count": user_metrics["social"]["total_friends"],
                    "daily_streak": user_metrics["engagement"]["daily_streak"],
                    "current_level": user_metrics["ranking"]["current_level"],
                    "global_rank": user_metrics["ranking"]["global_rank"]
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/dashboard/admin", response_model=Dict[str, Any])
async def get_admin_dashboard(
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """Get admin dashboard data."""
    try:
        # Get platform metrics and system status
        platform_metrics = await analytics_engine.get_platform_metrics(db, 7)
        realtime_metrics = await analytics_engine.get_real_time_metrics(db)
        system_status = await monitoring_system.get_current_status()
        
        return {
            "success": True,
            "data": {
                "platform": platform_metrics,
                "realtime": realtime_metrics,
                "system": system_status,
                "timestamp": system_status.get("timestamp")
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get admin dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
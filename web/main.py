"""
FastAPI Web Application for Crypto Analytics Platform.
Provides REST API endpoints and serves the web interface.
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import json
from datetime import datetime
import os
import sys

# Add parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_providers import DataManager
from models import CoinData, ApplicationState
from config import config
from logger import logger
import asyncio
import os

# Initialize FastAPI app
app = FastAPI(
    title="Crypto Analytics Platform",
    description="Professional cryptocurrency analytics and trading platform with real-time data and paper trading",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Add CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core components
data_manager = DataManager()
app_state = ApplicationState()

# Static files and templates
templates = Jinja2Templates(directory="web/templates")

# Mount static files after we create some
# app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Include trading API routes
from web.trading_api import router as trading_router
app.include_router(trading_router)

# Background task: evaluate risk triggers periodically
RISK_EVAL_INTERVAL_SEC = 5

@app.on_event("startup")
async def _start_background_tasks():
    async def _risk_loop():
        while True:
            try:
                # Lazy import to avoid circulars
                from trading.engine import trading_engine
                executed = await trading_engine.evaluate_risk_triggers()
                if executed:
                    logger.info(f"Risk triggers executed {executed} orders")
            except Exception as e:
                logger.error(f"Risk evaluation loop error: {e}")
            await asyncio.sleep(RISK_EVAL_INTERVAL_SEC)

    # Store task so it can be cancelled on shutdown
    try:
        app.state.risk_task = asyncio.create_task(_risk_loop())
    except Exception as e:
        logger.error(f"Failed to start risk evaluation task: {e}")


@app.on_event("shutdown")
async def _stop_background_tasks():
    task = getattr(app.state, "risk_task", None)
    if task:
        task.cancel()
        try:
            await task
        except Exception:
            pass


# Pydantic models for API
class CoinResponse(BaseModel):
    id: str
    name: str
    symbol: str
    price: float
    emoji: str
    price_change_24h: float
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None


class CoinsListResponse(BaseModel):
    coins: List[CoinResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
    api_source: str
    last_updated: str


class HistoricalDataResponse(BaseModel):
    coin_id: str
    timeframe: str
    prices: List[List[float]]  # [timestamp, price] pairs
    count: int


class ConversionRequest(BaseModel):
    amount: float = Field(gt=0, description="Amount to convert")
    from_currency: str = Field(min_length=3, max_length=3, description="Source currency code")
    to_coin: str = Field(min_length=1, description="Target cryptocurrency ID")


class ConversionResponse(BaseModel):
    amount_input: float
    from_currency: str
    to_coin: str
    crypto_amount: float
    price_per_unit: float
    timestamp: str


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send message to WebSocket: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()


# API Routes
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main web application."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/trading", response_class=HTMLResponse)
async def read_trading(request: Request):
    """Serve the paper trading dashboard."""
    return templates.TemplateResponse("trading.html", {"request": request})


@app.get("/gaming/inventory", response_class=HTMLResponse)
async def read_inventory(request: Request):
    """Serve the full inventory page (gamification)."""
    return templates.TemplateResponse("gaming/inventory.html", {"request": request})


# Dev-only shutdown endpoint
@app.post("/api/admin/shutdown")
async def admin_shutdown(request: Request):
    """Gracefully stop the server (dev only). Requires admin token when not in debug mode."""
    debug = config.get("DEBUG_MODE", False)
    token_required = not debug
    if token_required:
        expected = os.environ.get("ADMIN_TOKEN") or config.get("ADMIN_TOKEN")
        provided = request.headers.get("X-Admin-Token")
        if not expected or provided != expected:
            raise HTTPException(status_code=401, detail="Unauthorized")

    # Cancel background tasks if any
    try:
        task = getattr(app.state, "risk_task", None)
        if task:
            task.cancel()
    except Exception:
        pass

    async def _delayed_exit():
        await asyncio.sleep(0.2)
        os._exit(0)

    asyncio.create_task(_delayed_exit())
    return {"status": "shutting_down"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "api_sources": [data_manager.coinlist_primary_api]
    }


@app.get("/api/coins", response_model=CoinsListResponse)
async def get_coins(
    page: int = 1,
    per_page: int = 50,
    currency: str = "usd"
):
    """Get paginated list of cryptocurrencies."""
    try:
        logger.info(f"API request: get_coins page={page}, per_page={per_page}, currency={currency}")
        
        # Validate parameters
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be >= 1")
        if per_page < 1 or per_page > 100:
            raise HTTPException(status_code=400, detail="Per_page must be between 1 and 100")
        
        # Get coins data
        coins_data, api_source = data_manager.get_top_coins(currency, limit=100)
        
        if not coins_data:
            raise HTTPException(status_code=503, detail="Unable to fetch cryptocurrency data")
        
        # Pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_coins = coins_data[start_idx:end_idx]
        
        total_pages = (len(coins_data) + per_page - 1) // per_page
        
        # Convert to response format
        coin_responses = [
            CoinResponse(
                id=coin.id,
                name=coin.name,
                symbol=coin.symbol,
                price=coin.price,
                emoji=coin.emoji,
                price_change_24h=coin.price_change_24h,
                market_cap=coin.market_cap,
                volume_24h=coin.volume_24h
            )
            for coin in paginated_coins
        ]
        
        response = CoinsListResponse(
            coins=coin_responses,
            total=len(coins_data),
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            api_source=api_source,
            last_updated=datetime.now().isoformat()
        )
        
        logger.info(f"Successfully returned {len(coin_responses)} coins from {api_source}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_coins: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/coins/{coin_id}/history", response_model=HistoricalDataResponse)
async def get_coin_history(
    coin_id: str,
    timeframe: str = "7d",
    currency: str = "usd"
):
    """Get historical price data for a cryptocurrency."""
    try:
        logger.info(f"API request: get_coin_history coin_id={coin_id}, timeframe={timeframe}")
        
        # Validate timeframe
        valid_timeframes = ["1d", "7d", "30d", "90d", "365d", "max"]
        if timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}"
            )
        
        # Convert timeframe to API format
        days_mapping = {
            "1d": "1",
            "7d": "7", 
            "30d": "30",
            "90d": "90",
            "365d": "365",
            "max": "max"
        }
        
        days = days_mapping[timeframe]
        prices = data_manager.get_historical_data(coin_id, days, currency)
        
        if not prices:
            raise HTTPException(status_code=404, detail=f"No historical data found for {coin_id}")
        
        # Convert price points to list format
        price_data = [[point.timestamp, point.price] for point in prices]
        
        response = HistoricalDataResponse(
            coin_id=coin_id,
            timeframe=timeframe,
            prices=price_data,
            count=len(price_data)
        )
        
        logger.info(f"Successfully returned {len(price_data)} price points for {coin_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_coin_history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/convert", response_model=ConversionResponse)
async def convert_currency(conversion: ConversionRequest):
    """Convert fiat currency to cryptocurrency."""
    try:
        logger.info(f"API request: convert {conversion.amount} {conversion.from_currency} to {conversion.to_coin}")
        
        # Get current coin data
        coins_data, _ = data_manager.get_top_coins(conversion.from_currency.lower(), limit=100)
        
        # Find the target coin
        target_coin = None
        for coin in coins_data:
            if coin.id == conversion.to_coin or coin.symbol.lower() == conversion.to_coin.lower():
                target_coin = coin
                break
        
        if not target_coin:
            raise HTTPException(status_code=404, detail=f"Cryptocurrency '{conversion.to_coin}' not found")
        
        # Calculate conversion
        crypto_amount = conversion.amount / target_coin.price
        
        response = ConversionResponse(
            amount_input=conversion.amount,
            from_currency=conversion.from_currency.upper(),
            to_coin=target_coin.id,
            crypto_amount=crypto_amount,
            price_per_unit=target_coin.price,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Successfully converted {conversion.amount} {conversion.from_currency} to {crypto_amount:.8f} {target_coin.symbol}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in convert_currency: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/coins/search")
async def search_coins(
    query: str,
    limit: int = 10,
    currency: str = "usd"
):
    """Search cryptocurrencies by name or symbol."""
    try:
        logger.info(f"API request: search_coins query='{query}', limit={limit}")
        
        if len(query.strip()) < 2:
            raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
        
        # Get all coins data
        coins_data, api_source = data_manager.get_top_coins(currency, limit=100)
        
        # Search logic (same as terminal version)
        query_lower = query.strip().lower()
        results = []
        
        for coin in coins_data:
            symbol_lower = coin.symbol.lower()
            id_lower = coin.id.lower()
            name_lower = coin.name.lower()
            
            if (query_lower == symbol_lower) or (query_lower == id_lower) or (query_lower in name_lower):
                results.append(coin)
                if len(results) >= limit:
                    break
        
        # Convert to response format
        coin_responses = [
            CoinResponse(
                id=coin.id,
                name=coin.name,
                symbol=coin.symbol,
                price=coin.price,
                emoji=coin.emoji,
                price_change_24h=coin.price_change_24h,
                market_cap=coin.market_cap,
                volume_24h=coin.volume_24h
            )
            for coin in results
        ]
        
        logger.info(f"Search returned {len(coin_responses)} results for '{query}'")
        return {
            "query": query,
            "results": coin_responses,
            "count": len(coin_responses),
            "api_source": api_source
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in search_coins: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# WebSocket endpoint for real-time updates
@app.websocket("/ws/prices")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time price updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Send periodic price updates
            coins_data, api_source = data_manager.get_top_coins("usd", limit=20)
            
            if coins_data:
                update_data = {
                    "type": "price_update",
                    "timestamp": datetime.now().isoformat(),
                    "api_source": api_source,
                    "coins": [
                        {
                            "id": coin.id,
                            "symbol": coin.symbol,
                            "price": coin.price,
                            "change_24h": coin.price_change_24h
                        }
                        for coin in coins_data[:10]  # Top 10 for real-time
                    ]
                }
                
                await manager.send_personal_message(json.dumps(update_data), websocket)
            
            # Wait before next update
            await asyncio.sleep(30)  # Update every 30 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Background task for broadcasting updates
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Crypto Analytics Platform Web API starting up...")
    
    # Pre-fetch some data to warm up the cache
    try:
        coins_data, api_source = data_manager.get_top_coins("usd", limit=10)
        logger.info(f"Warmed up cache with {len(coins_data) if coins_data else 0} coins from {api_source}")
    except Exception as e:
        logger.warning(f"Failed to warm up cache: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Crypto Analytics Platform Web API shutting down...")


if __name__ == "__main__":
    import uvicorn
    
    # Configuration
    host = config.get("WEB_HOST", "127.0.0.1")
    port = config.get("WEB_PORT", 8000)
    debug = config.get("DEBUG_MODE", False)
    
    logger.info(f"Starting web server at http://{host}:{port}")
    
    uvicorn.run(
        "web.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )

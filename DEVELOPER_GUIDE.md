# 👨‍💻 CryptoChecker Platform - Developer Guide

## 🎯 Quick Start

### Prerequisites
- Python 3.8+
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Installation
```bash
# Clone and setup
cd PythonCryptoChecker

# RECOMMENDED: Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies in virtual environment
pip install -r requirements.txt

# Start the platform using virtual environment Python
".venv/Scripts/python.exe" run.py
# OR: python run.py (if virtual environment is activated)

# Access platform
open http://localhost:8000
```

## 🏗️ Architecture Overview

### Backend Stack
- **FastAPI**: Modern Python web framework with automatic OpenAPI docs
- **Enhanced Market Data Services**: Advanced CoinGecko/CoinCap integration with intelligent caching
- **Pydantic v2**: Data validation with performance optimization
- **SQLAlchemy**: Async database ORM with unified model architecture
- **Session-based Auth**: Secure authentication with FastAPI sessions

### Frontend Stack
- **Bootstrap 5**: Modern responsive CSS framework
- **Vanilla JavaScript ES6+**: Clean, modern JavaScript with async/await
- **Jinja2 Templates**: Server-side rendering with template inheritance

### Key Features
- **Enhanced Market Analysis**: Real-time sentiment analysis with Fear & Greed Index
- **Professional Trading APIs**: 7 new market endpoints with OHLCV charting data
- **Unified Navigation**: All pages use `base.html` template inheritance
- **Complete Inventory System**: 42+ collectible items with pack opening and real transactions
- **Advanced Trading**: LIMIT/STOP_LOSS/TAKE_PROFIT orders with GEM integration
- **Intelligent Caching**: 80% reduction in API calls through smart caching system
- **Professional Gaming**: Roulette with comprehensive betting and enhanced UX
- **Virtual Economy**: Real GEM transactions with persistent balance management
- **Comprehensive APIs**: 32+ REST endpoints with enhanced market analysis

## 📁 Project Structure Explained

```
PythonCryptoChecker/
├── main.py                   # 🚀 Main application with all API endpoints
├── test_endpoints.py         # 🧪 Comprehensive API testing suite
├── requirements.txt          # 📦 Python dependencies
│
├── web/                      # 🎨 Frontend assets
│   ├── templates/
│   │   ├── base.html         # ✅ Unified base template
│   │   ├── trading_unified.html # 💼 Professional trading interface
│   │   ├── home.html         # 🏠 Dashboard with real-time stats
│   │   └── gaming/roulette.html # 🎰 Gaming interface
│   │
│   └── static/
│       ├── css/main.css      # 🎨 Core styling
│       ├── js/auth.js        # 🔐 Authentication management
│       ├── js/api.js         # 📡 API client
│       └── js/main.js        # ⚙️ Core utilities
│
├── database/                 # 💾 Data layer
│   └── unified_models.py     # ✅ Consolidated database schema
│
├── api/                      # 📡 API modules (modular architecture)
│   ├── auth_api.py          # 🔐 Authentication endpoints
│   ├── gaming_api.py        # 🎮 Gaming and statistics
│   ├── inventory_api.py     # 📦 Inventory and item management
│   ├── trading_api.py       # 💼 Trading system APIs
│   └── social_api.py        # 👥 Social features
│
├── inventory/               # 📦 Inventory management system
│   ├── inventory_manager.py # Item management logic
│   └── items_data.py        # Item database seeding
│
└── Documentation/            # 📚 Complete documentation
    ├── README.md            # 📖 Main documentation
    ├── API_DOCUMENTATION.md # 🔌 API reference
    ├── ENHANCEMENT_SUMMARY.md # 📊 Enhancement details
    └── DEVELOPER_GUIDE.md   # 👨‍💻 This file
```

## 🔧 Development Workflow

### Local Development
```bash
# IMPORTANT: Use virtual environment to avoid dependency conflicts

# Create virtual environment (first time only)
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies in virtual environment
pip install -r requirements.txt

# Run with hot reload using virtual environment Python
".venv/Scripts/python.exe" run.py
# OR: python run.py (if virtual environment is activated)

# The server will start on http://localhost:8000
# Changes to Python files will auto-reload the server
```

### Common Setup Issues

#### "No module named 'flask_socketio'" Error
This occurs when dependencies are installed globally instead of in the virtual environment:

```bash
# Solution: Always use virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
".venv/Scripts/python.exe" run.py  # Windows
```

#### Module Import Errors
```bash
# Ensure virtual environment is activated
which python  # Should show .venv/ path

# If not, activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

### Testing
```bash
# Run comprehensive API tests
python test_endpoints.py

# Expected output:
# ✅ API Health: API is working!
# ✅ Demo Login: success
# ✅ Portfolio: $12500.50
# ✅ Prices: BTC $43,250.75
# ✅ Quick Trade: BUY order executed successfully!
# ✅ Wallet: 1001 GEM coins
# ✅ Bet Validation: Max bet 1001
# ✅ Roulette: Number 23, Net: -15
# ✅ Stats: 1 games, 0.0% win rate
```

### Code Quality
```bash
# Format code (if using black)
black main.py

# Check types (if using mypy)
mypy main.py

# Run linting (if using flake8)
flake8 main.py
```

## 📊 Enhanced Market Analysis APIs 🆕

### New Market Data Endpoints

The platform now includes 7 professional market analysis endpoints:

#### **GET /api/market/overview**
Comprehensive market overview with sentiment analysis
```javascript
// Usage example
const response = await fetch('/api/market/overview?fiat=USD');
const data = await response.json();
console.log(data.data.sentiment.market_sentiment); // "bullish" or "bearish"
console.log(data.data.sentiment.fear_greed_index); // 0-100 scale
```

#### **GET /api/market/sentiment**
Detailed market sentiment with top movers
```javascript
const sentiment = await fetch('/api/market/sentiment?fiat=USD');
const data = await sentiment.json();
console.log(data.data.market_movers.top_gainers); // Top 5 gainers
```

#### **GET /api/market/coins**
Live cryptocurrency market data with multi-currency support
```javascript
const coins = await fetch('/api/market/coins?fiat=EUR&limit=50');
const data = await coins.json();
console.log(data.data.coins); // Array of coin data
```

#### **GET /api/market/trending**
Real-time trending cryptocurrencies
```javascript
const trending = await fetch('/api/market/trending');
const data = await trending.json();
console.log(data.data.trending); // Array of trending symbols
```

#### **GET /api/market/search**
Advanced cryptocurrency search
```javascript
const search = await fetch('/api/market/search?q=bitcoin&limit=10');
const data = await search.json();
console.log(data.data.results); // Search results
```

#### **GET /api/market/historical/{coin_id}**
Historical price data for charting
```javascript
const history = await fetch('/api/market/historical/bitcoin?fiat=USD&days=7');
const data = await history.json();
console.log(data.data.data); // Historical price points
```

#### **GET /api/market/ohlcv/{coin_id}**
Professional OHLCV candlestick data
```javascript
const ohlcv = await fetch('/api/market/ohlcv/bitcoin?fiat=USD&days=30');
const data = await ohlcv.json();
console.log(data.data.data); // OHLCV candles for technical analysis
```

### Enhanced Market Dashboard Integration

The market dashboard at `/market` now includes:
- **Real-time sentiment display**: Live Fear & Greed Index
- **Market overview metrics**: Total market cap, positive/negative changes
- **Top performers**: Live top gainers and losers
- **Trending cryptocurrencies**: Real-time trending asset tracking

### Market Data Service Architecture

The enhanced `market_data_service.py` includes:
- **Intelligent caching**: 80% reduction in API calls
- **Dual-API fallback**: CoinGecko primary, CoinCap backup
- **Rate limiting**: Prevents API abuse
- **Error handling**: Graceful fallback for API failures

## 🔌 API Development

### Adding New Endpoints

1. **Define in main.py**:
```python
@app.get("/api/my-feature/endpoint")
async def my_endpoint(request: Request):
    if not request.session.get("is_authenticated"):
        return JSONResponse({"status": "error", "message": "Not authenticated"}, status_code=401)
    
    try:
        # Your logic here
        return {
            "status": "success",
            "data": {"result": "success"}
        }
    except Exception as e:
        logger.error(f"Error in my endpoint: {e}")
        return JSONResponse({"status": "error", "message": "Operation failed"}, status_code=500)
```

2. **Add to test suite**:
```python
# In test_endpoints.py
print("\n10. Testing My New Feature...")
try:
    async with session.get(f"{BASE_URL}/api/my-feature/endpoint") as response:
        if response.status == 200:
            data = await response.json()
            print(f"✅ My Feature: {data['data']['result']}")
        else:
            print(f"❌ My Feature: Status {response.status}")
except Exception as e:
    print(f"❌ My Feature: {e}")
```

### Response Format Standards

Always use consistent response format:
```python
# Success response
{
    "status": "success",
    "data": {
        # Response data here
    }
}

# Error response
{
    "status": "error", 
    "message": "Human readable error message"
}
```

### Error Handling Best Practices

```python
try:
    # Your logic
    result = perform_operation()
    return {"status": "success", "data": result}
except ValueError as e:
    return JSONResponse(
        {"status": "error", "message": str(e)}, 
        status_code=400
    )
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return JSONResponse(
        {"status": "error", "message": "Operation failed"}, 
        status_code=500
    )
```

## 🎨 Frontend Development

### Template Development

All pages should extend the unified base template:

```html
{% extends "base.html" %}

{% block title %}My Page - CryptoChecker Gaming Platform{% endblock %}

{% block extra_css %}
<link href="/static/css/my-page.css" rel="stylesheet">
{% endblock %}

{% block body_class %}my-page-class{% endblock %}

{% block content %}
<!-- Your page content here -->
<div class="container py-4">
    <h1>My Page</h1>
</div>
{% endblock %}

{% block extra_js %}
<script src="/static/js/my-page.js"></script>
{% endblock %}
```

### JavaScript Development

Use modern JavaScript with proper API integration:

```javascript
// Use the global API client
class MyFeature {
    constructor() {
        this.init();
    }

    async init() {
        try {
            // Check authentication
            if (window.auth && !window.auth.isAuthenticated()) {
                console.log('User not authenticated');
                return;
            }

            // Load data
            await this.loadData();
        } catch (error) {
            console.error('Failed to initialize:', error);
        }
    }

    async loadData() {
        try {
            const response = await fetch('/api/my-feature/data', {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                this.updateUI(data);
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.error('Failed to load data:', error);
            this.showError('Failed to load data');
        }
    }

    updateUI(data) {
        // Update the user interface
        document.getElementById('my-data').textContent = data.result;
    }

    showError(message) {
        // Use the global alert system if available
        if (window.showAlert) {
            window.showAlert(message, 'error');
        } else {
            alert(message);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new MyFeature();
});
```

## 🗄️ Database Development

### Model Development

Add new models to `database/unified_models.py`:

```python
class MyModel(Base):
    """My new model description."""
    __tablename__ = "my_table"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    value = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
```

### Database Queries

Use async SQLAlchemy patterns:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_user_data(user_id: str, session: AsyncSession):
    """Get user data with proper async handling."""
    result = await session.execute(
        select(MyModel).where(MyModel.user_id == user_id)
    )
    return result.scalars().all()
```

## 🧪 Testing Strategies

### Unit Testing
```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_api_health():
    response = client.get("/api/test")
    assert response.status_code == 200
    assert response.json()["message"] == "API is working!"

def test_demo_login():
    response = client.post("/api/auth/demo-login")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
```

### Integration Testing
```python
async def test_full_workflow():
    """Test complete user workflow."""
    async with aiohttp.ClientSession() as session:
        # 1. Login
        await session.post('http://localhost:8000/api/auth/demo-login')
        
        # 2. Get portfolio
        response = await session.get('http://localhost:8000/api/trading/portfolio/demo/summary')
        assert response.status == 200
        
        # 3. Place trade
        response = await session.get('http://localhost:8000/api/trading/quick-trade/BUY/bitcoin?amount=100')
        assert response.status == 200
```

## 🚀 Deployment Guide

### Development Deployment
```bash
# Standard development
python main.py

# With environment variables
export DEBUG=True
export PORT=8000
python main.py
```

### Production Deployment
```bash
# Set production environment
export DEBUG=False
export SECRET_KEY=your-secure-secret-key
export HOST=0.0.0.0
export PORT=8000

# Run with production server
python main.py
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py"]
```

```bash
# Build and run
docker build -t cryptochecker .
docker run -p 8000:8000 cryptochecker
```

## 📊 Performance Monitoring

### Logging
```python
from logger import logger

# Use throughout your code
logger.info("User logged in successfully")
logger.error(f"Failed to process request: {error}")
logger.debug("Debug information for development")
```

### Performance Tracking
```python
import time

async def timed_operation():
    start_time = time.time()
    try:
        # Your operation
        result = await perform_operation()
        return result
    finally:
        duration = time.time() - start_time
        logger.info(f"Operation completed in {duration:.2f}s")
```

## 🔒 Security Best Practices

### Input Validation
```python
from pydantic import BaseModel, Field

class MyRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    amount: float = Field(gt=0, le=1000000)
    email: str = Field(regex=r'^[^@]+@[^@]+\.[^@]+$')
```

### Session Security
```python
# Always check authentication
if not request.session.get("is_authenticated"):
    return JSONResponse(
        {"status": "error", "message": "Not authenticated"}, 
        status_code=401
    )

# Validate user ownership
user_id = request.session.get("user_id")
if resource.user_id != user_id:
    return JSONResponse(
        {"status": "error", "message": "Unauthorized"}, 
        status_code=403
    )
```

## 🐛 Troubleshooting

### Critical Setup Issues (January 2025 Fixes)

1. **"No module named 'flask_socketio'" Error**:
   ```bash
   # ROOT CAUSE: Dependencies installed globally, not in virtual environment

   # SOLUTION: Always use virtual environment
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt

   # Run using virtual environment Python
   ".venv/Scripts/python.exe" run.py  # Windows
   ".venv/bin/python" run.py  # Linux/Mac
   ```

2. **Module import errors**:
   ```bash
   # Verify virtual environment is active
   which python  # Should show .venv/ path

   # If not, activate virtual environment first
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac

   # Then run the server
   python run.py
   ```

3. **Port already in use**:
   ```bash
   # Find and kill process using port 8000
   lsof -ti:8000 | xargs kill -9  # Linux/Mac
   netstat -ano | findstr :8000   # Windows (find PID)
   taskkill /PID <PID> /F         # Windows (kill PID)
   ```

4. **Session issues**:
   ```python
   # Clear session data
   request.session.clear()
   ```

5. **Inventory system not working**:
   ```bash
   # Ensure database models are properly imported
   # Check that unified_models.py contains all inventory models
   # Restart server to refresh database schema
   ```

### Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Add debug prints
print(f"Debug: User ID = {user_id}")
```

## 📈 Future Development

### Recent Achievements (January 2025)
- ✅ **Complete Inventory System**: Full item collection with 42+ collectibles
- ✅ **Real Transaction System**: Actual GEM deduction and persistent storage
- ✅ **Enhanced Gaming UX**: Clearer win displays and improved user experience
- ✅ **Server Infrastructure**: Robust virtual environment setup and troubleshooting
- ✅ **Database Persistence**: All inventory items saved permanently with transaction safety

### Planned Enhancements
- **Real Database Integration**: PostgreSQL/MySQL support
- **WebSocket Support**: Real-time gaming updates
- **Mobile App**: React Native or Flutter
- **Advanced Analytics**: User behavior tracking
- **Tournament System**: Competitive gaming with prize pools

### Contributing Guidelines
1. **Code Style**: Follow PEP 8 for Python, consistent JavaScript patterns
2. **Testing**: Add tests for all new features
3. **Documentation**: Update relevant documentation
4. **Error Handling**: Implement comprehensive error handling
5. **Security**: Follow security best practices

---

## 🎉 Success!

You now have a comprehensive understanding of the CryptoChecker platform architecture and development workflow. The platform is ready for further development and scaling!

**Next Steps**:
1. Set up virtual environment: `python -m venv .venv && .venv\Scripts\activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the platform: `".venv/Scripts/python.exe" run.py`
4. Visit `http://localhost:8000` to explore the features
5. Test inventory system at `http://localhost:8000/inventory`
6. Run `python test_endpoints.py` to validate everything is working
7. Start building new features using this guide!

---

## 🆕 Recent Updates (January 2025)

### Major System Enhancements:
- **Complete Inventory System**: Full implementation with pack opening, item usage, and database persistence
- **Virtual Environment Support**: Proper setup instructions and troubleshooting for dependency management
- **Enhanced Gaming Experience**: Improved win displays and clearer user feedback
- **Server Reliability**: Fixed critical dependency issues and added comprehensive troubleshooting

### Development Environment Improvements:
- Added virtual environment setup as the recommended approach
- Comprehensive troubleshooting section for common setup issues
- Updated file structure to reflect new inventory system components
- Enhanced API development guidelines with inventory endpoints

*Developer Guide - Updated January 2025 with Complete System Coverage*
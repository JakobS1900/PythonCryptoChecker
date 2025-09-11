# 🎰 CryptoChecker Gaming Platform

A modern, full-stack crypto gaming and gamification platform built with FastAPI, featuring stunning visual design, real-time gaming, comprehensive authentication, and a complete virtual economy system.

## 🚀 Latest Updates (January 2025)

### ⚡ **COMPREHENSIVE PLATFORM ENHANCEMENT - MAJOR UPDATE**
*Complete codebase analysis, enhancement, and modernization based on deep research and AI-powered recommendations.*

#### 🎯 **Navigation & Template Consistency**
- **✅ COMPLETED**: Unified all templates to use `base.html` with consistent global navbar
- **Template Inheritance**: Standardized template structure across entire platform
- **Responsive Design**: Consistent navigation experience on all devices
- **Fixed**: Multiple navbar implementations causing inconsistencies

#### 💼 **Advanced Trading System - FULLY IMPLEMENTED**
- **✅ COMPLETED**: Professional-grade trading system with advanced order types
- **Order Types**: MARKET, LIMIT, STOP_LOSS, TAKE_PROFIT orders with full validation
- **OCO Functionality**: One-Cancels-Other orders for advanced risk management
- **Portfolio Analytics**: Comprehensive performance tracking and metrics
- **Real-time Pricing**: Live crypto price updates with demo data integration
- **GEM Integration**: Seamless virtual economy across all trading features
- **New Template**: `trading_unified.html` with professional interface

#### 🎰 **Enhanced Roulette Gaming System**
- **✅ COMPLETED**: Professional casino-grade roulette with comprehensive betting
- **Betting Validation**: Real-time bet validation and balance checking
- **Payout System**: Accurate payout calculations for all bet types (single 35:1, color 1:1, etc.)
- **Statistics Tracking**: Win/loss tracking with detailed analytics
- **Multiple Bet Types**: Single number, color, even/odd, high/low betting
- **Security**: Enhanced input validation and fraud prevention

#### 🔌 **Comprehensive API Ecosystem**
- **✅ COMPLETED**: 12+ new REST API endpoints covering all platform features
- **Trading APIs**: Portfolio management, order placement, wallet integration
- **Gaming APIs**: Roulette spinning, bet validation, statistics tracking
- **Authentication**: Enhanced session management and security
- **Error Handling**: Professional error responses with proper HTTP status codes
- **Testing Suite**: Complete endpoint validation system (`test_endpoints.py`)

#### 🛡️ **Security & Authentication Enhancements**
- **✅ COMPLETED**: Strengthened security across all systems
- **Input Validation**: Comprehensive validation for all user inputs
- **Session Management**: Enhanced authentication state management
- **Error Handling**: Graceful error recovery with user-friendly messages
- **CORS Configuration**: Proper security headers and cross-origin handling

### 🔧 **Previous System Improvements**
- Trading restored at `/trading` with portfolio, holdings, orders, transactions, and inventory hooks.
- Quick Trade uses real-time crypto prices and converts USD amount to coin quantity.
- GEM wallet integrated with trading: Buy/Sell adjusts GEM using a configurable rate (default 1 GEM = $0.01 ⇒ 1000 GEM = $10). Set `GEM_USD_RATE_USD_PER_GEM` in `.env`.
- Authentication UX: removed invisible/logout misfires by tightening click handling; `/api/auth/login` accepts `username_or_email` and uses proper 4xx/5xx status codes.
- Stability: fixed home 500s via startup constants/stubs and a safe template fallback; resolved SQLAlchemy cross-registry mapping issue in gamification models.

## ✨ Latest Features & Critical Fixes (January 2025)

### 🎮 **Enhanced CS:GO Gaming Experience**
- **🎰 CS:GO Crypto Roulette**: Professional-grade roulette system with dark theme and gold accents matching CS:GO aesthetics
  - **Multiple Bet Types**: Single numbers (35:1), color betting (1:1/35:1), crypto categories (2:1), traditional even/odd, high/low
  - **Provably Fair System**: Enhanced 5-iteration cryptographic verification with server/client seeds and nonce
  - **Real-time Features**: WebSocket integration for live betting, user presence, and instant result updates
  - **Professional UI**: Horizontal number strip animation, floating chip effects, bet tracking, balance management
  - **Mobile Responsive**: Optimized for all devices with touch-friendly betting interface
- **Gaming Variants**: Dice, Crash, Plinko, and Tower games with crypto themes  
- **Real-time Stats**: Live dashboard with accurate user statistics and progress tracking
- **Advanced Animations**: Smooth wheel spinning, winning segment highlighting, particle effects
- **Session Management**: Multi-device support with persistent game states and automatic reconnection

### 🎯 **Advanced Gamification System**
- **XP & Leveling**: Dynamic experience system with exponential level progression
- **Achievement System**: 50+ achievements across gaming, collection, social, and milestone categories
- **Virtual Inventory**: Complete item management with trading cards, cosmetics, and consumables
- **Social Features**: Friend system, leaderboards, activity feeds, and community challenges
- **Statistics Tracking**: Comprehensive user analytics with real-time dashboard updates

### 💎 **Virtual Economy** ⚡ *JUST FIXED*
- **GEM Coin System**: Primary virtual currency for all platform activities
- **Inventory Management**: Collectible items with rarity tiers (Common → Mythic)
- **Trading System**: Peer-to-peer item and currency exchanges
- **Item Marketplace**: Buy/sell virtual items with other players
- **Reward Systems**: Daily bonuses, achievement rewards, and gaming payouts
- **✅ FIXED: Inventory System Errors**: Resolved JavaScript "Cannot read properties of undefined" errors
- **✅ FIXED: Utils Loading**: Fixed script loading order for proper debounce function access
- **✅ FIXED: Real-time Stats**: Dynamic inventory statistics calculation from actual item data

### 🔐 **Enhanced Authentication & Security** ⚡ *JUST FIXED*
- **Session-based Authentication**: Secure login with FastAPI sessions and proper state management
- **Demo Account System**: One-click demo login with pre-populated stats and inventory
- **Real-time Auth State**: Automatic UI updates and seamless user experience
- **API Security**: Protected endpoints with session validation and CORS configuration
- **✅ FIXED: JavaScript Authentication Errors**: Resolved duplicate variable declarations and API integration issues
- **✅ FIXED: Registration System**: Complete form submission with proper API response handling
- **✅ FIXED: Login Redirect Loop**: Direct navigation to dashboard without redirect cycles

### 🎨 **Modern UI/UX Design**
- **Glassmorphism Theme**: Professional frosted glass effects with crypto-themed gradients
- **Consistent Branding**: Unified "CryptoChecker Gaming Platform" branding across all pages
- **Interactive Dashboard**: Real-time stats display with live data synchronization
- **Responsive Templates**: Mobile-first design with Bootstrap 5 and custom CSS
- **Visual Feedback**: Loading states, animations, and micro-interactions

### 🛠️ **Technical Architecture**
- **Unified Database**: Consolidated models with proper relationships and foreign keys
- **RESTful APIs**: Comprehensive endpoint coverage for all platform features
- **Error Handling**: Graceful error recovery with user-friendly messages
- **Development Tools**: Hot reload, debugging tools, and comprehensive logging
- **Modular Structure**: Clean separation of concerns with organized codebase

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Installation & Setup

1. **Clone and Setup**
```bash
git clone <repository-url>
cd PythonCryptoChecker
pip install -r requirements.txt
```

2. **Run the Platform**
```bash
python run.py
```

3. **Access the Platform**
- **Home Dashboard**: http://localhost:8000/
- **🎰 Enhanced CS:GO Roulette**: http://localhost:8000/gaming/roulette ⭐ *NEWLY ENHANCED*
- **Inventory System**: http://localhost:8000/inventory
- **Social Features**: http://localhost:8000/social
- **Profile**: http://localhost:8000/profile
- **Achievements**: http://localhost:8000/achievements
- **User Login**: http://localhost:8000/login
- **API Documentation**: http://localhost:8000/api/docs

### 🎮 Getting Started Guide

1. **Quick Demo**: Click "Try Demo" on homepage for instant access with pre-populated stats
2. **Explore Dashboard**: View your GEM coins, level, wins, and achievements
3. **Play Games**: Experience crypto roulette with real betting mechanics
4. **Manage Inventory**: Collect items, open packs, and trade with other players
5. **Social Features**: Add friends, compete on leaderboards, and track achievements

## 🔌 API Endpoints

### Authentication & User Management
- `POST /api/auth/register` - User registration with validation
- `POST /api/auth/login` - Secure user login with session management  
- `GET /api/auth/logout` - User logout and session cleanup
- `GET /api/auth/me` - Get current authenticated user information
- `POST /api/auth/demo-login` - Instant demo account with pre-populated data
- `GET /api/auth/status` - Detailed authentication status for debugging

### 💼 Advanced Trading System ⚡ *NEWLY IMPLEMENTED*
- `GET /api/trading/portfolio/demo/summary` - Portfolio summary with real-time data
- `GET /api/trading/prices` - Live cryptocurrency prices with change indicators
- `GET /api/trading/quick-trade/{action}/{coin_id}` - Execute market orders (BUY/SELL)
- `POST /api/trading/orders` - Place advanced orders (LIMIT/STOP_LOSS/TAKE_PROFIT)
- `GET /api/trading/gamification/wallet` - GEM wallet with USD value conversion

### 🎰 Enhanced Roulette Gaming ⚡ *NEWLY IMPLEMENTED*
- `POST /api/roulette/spin` - Execute roulette spin with multiple bet types
- `GET /api/roulette/stats` - Comprehensive gaming statistics and analytics
- `POST /api/roulette/validate-bet` - Real-time bet validation and balance checking

### Gaming & Statistics
- `GET /api/gaming/stats` - Comprehensive user gaming statistics
- `POST /api/gaming/sessions` - Create new game sessions
- `POST /api/gaming/sessions/{id}/bets` - Place bets in active games
- `POST /api/gaming/sessions/{id}/spin` - Execute game rounds (roulette spin)
- `GET /api/gaming/history` - User gaming history and past results
- `GET /api/gaming/tournaments` - Available tournaments and competitions

### Virtual Economy & Inventory
- `GET /api/inventory/items` - User inventory with filtering and pagination
- `GET /api/inventory/items/{id}` - Detailed item information
- `POST /api/inventory/items/{id}/equip` - Equip cosmetic items
- `POST /api/inventory/items/{id}/use` - Use consumable items
- `POST /api/inventory/items/{id}/sell` - Sell items for GEM coins
- `GET /api/inventory/trades` - Active trading offers
- `POST /api/inventory/trades` - Create new trade offers
- `GET /api/inventory/marketplace` - Global item marketplace

### Social Features & Community
- `GET /api/social/friends` - User friends list and status
- `POST /api/social/friends/request` - Send friend requests
- `GET /api/social/leaderboards` - Global and category leaderboards
- `GET /api/social/activity` - Social activity feed
- `POST /api/social/gifts` - Send gifts to friends

### Achievement & Progression
- `GET /api/achievements` - User achievements and progress
- `GET /api/achievements/categories` - Achievement categories and requirements
- `GET /api/user/profile` - Complete user profile with statistics
- `GET /api/user/progress` - XP and leveling progression data

### Trading & GEM Economy
- `GET /api/trading/health` - Trading engine health check
- `GET /api/trading/gamification/wallet` - GEM wallet + virtual holdings
- `GET /api/trading/portfolio/{id}/summary` - Portfolio summary and holdings
- `GET /api/trading/portfolio/{id}/orders/open` - Open orders
- `GET /api/trading/portfolio/{id}/transactions?limit=10` - Recent transactions
- `GET /api/trading/quick-trade/{action}/{coin_id}?amount={USD}` - Quick Buy/Sell using real-time price
- Env: `GEM_USD_RATE_USD_PER_GEM` (default 0.01 ⇒ 1 GEM = $0.01 ⇒ 1000 GEM = $10)

### Administrative (Admin/Moderator Only)
- `GET /api/admin/users` - User management and moderation
- `POST /api/admin/users/{id}/actions` - User moderation actions
- `GET /api/admin/stats` - Platform-wide statistics and analytics
- `POST /api/admin/items` - Create new collectible items
- `POST /api/admin/events` - Create platform events and tournaments

## 🌐 User Interface

### Main Pages
- **`/`** - Interactive dashboard with real-time stats, quick actions, and user progress
- **`/gaming/roulette`** - Crypto-themed roulette with provably fair mechanics
- **`/gaming/dice`** - Dice game with crypto betting options  
- **`/gaming/crash`** - Multiplier crash game with risk management
- **`/inventory`** - Complete inventory management with item trading and marketplace
- **`/social`** - Social hub with friends, leaderboards, and community features
- **`/achievements`** - Achievement tracking with progress indicators
- **`/login`** - Enhanced authentication with glassmorphism design
- **`/register`** - User onboarding with validation and tutorials

### Dashboard Features
- **Real-time Statistics**: Live GEM coin balance, level progress, wins/losses
- **XP Progression**: Visual progress bars with level-up animations
- **Quick Actions**: One-click access to games, inventory, and social features
- **Activity Feed**: Recent gaming activity and social interactions
- **Achievement Highlights**: Latest unlocked achievements and progress

### Gaming Interface
- **Immersive Gameplay**: Full-screen gaming with crypto-themed designs
- **Real-time Betting**: Live bet placement with visual feedback
- **Statistics Display**: Win rates, streaks, and performance metrics
- **Provably Fair**: Transparent game mechanics with verification
- **Mobile Optimized**: Touch-friendly controls for mobile gaming

### Key Features
- **Responsive Design**: Seamless experience across all devices
- **Real-time Synchronization**: Live data updates without page refreshes
- **Modern Glassmorphism UI**: Professional frosted glass effects and gradients
- **Accessibility**: WCAG compliant with keyboard navigation and screen reader support
- **Progressive Enhancement**: Core functionality available without JavaScript

## 📁 Project Structure

```
PythonCryptoChecker/
├── run.py                    # Application launcher with environment setup
├── main.py                   # FastAPI application with enhanced API endpoints
├── requirements.txt          # Python dependencies
├── .env                      # Environment configuration (auto-generated)
├── test_endpoints.py         # ⚡ NEW: Comprehensive API testing suite
│
├── web/                      # Frontend templates and static assets
│   ├── templates/
│   │   ├── base.html         # ✅ UNIFIED: Main template with consistent navbar
│   │   ├── trading_unified.html # ⚡ NEW: Professional trading interface
│   │   ├── home.html         # Interactive dashboard with real-time stats
│   │   ├── inventory/        # Complete inventory management system
│   │   ├── gaming/           # Gaming interfaces (roulette, dice, etc.)
│   │   ├── social/           # Social features and community pages
│   │   ├── auth/             # Authentication pages with modern design
│   │   └── achievements.html # Achievement tracking and progress
│   │
│   └── static/               # CSS, JavaScript, and assets
│       ├── css/              # Modern styling with glassmorphism effects
│       ├── js/               # ✅ ENHANCED: API clients, auth, and UI logic
│       └── images/           # Platform icons and graphics
│
├── api/                      # ✅ ENHANCED: RESTful API implementation
│   ├── main.py              # Comprehensive API router with all endpoints
│   ├── auth_api.py          # Authentication and user management
│   ├── gaming_api.py        # Gaming sessions and statistics
│   ├── inventory_api.py     # Virtual economy and item management
│   ├── social_api.py        # Social features and community
│   └── admin_api.py         # Administrative and moderation tools
│
├── database/                 # ✅ UNIFIED: Database models and management
│   ├── unified_models.py    # Consolidated database schema with all systems
│   └── database_manager.py  # Database initialization and session handling
│
├── trading/                  # ✅ ENHANCED: Advanced trading system
│   ├── engine.py            # Trading engine with OCO and advanced orders
│   ├── models.py            # Trading-specific models (imports from unified)
│   └── database.py          # Trading database management
│
├── achievements/             # Achievement and progression system
├── inventory/               # Virtual item and trading system
├── social/                  # Friend system and community features
├── auth/                    # Authentication and security utilities
├── gaming/                  # Game engines and mechanics
│
├── notifications/           # Email and notification systems
├── analytics/              # User analytics and monitoring
├── onboarding/             # User onboarding and tutorials
│
└── Documentation/           # ✅ UPDATED: Comprehensive documentation
    ├── README.md           # This file (updated with latest features)
    ├── ENHANCEMENT_SUMMARY.md # ⚡ NEW: Complete enhancement documentation
    ├── BRANDING_UPDATED.md # Branding consistency documentation
    └── PROGRESS.md         # Development progress and recent changes
```

## 🛠️ Technical Stack

### Backend Technologies
- **FastAPI**: Modern Python web framework with automatic OpenAPI documentation
- **Pydantic v2**: Advanced data validation and serialization with performance optimization
- **SQLAlchemy**: Async database ORM with unified model architecture
- **SQLite/AsyncSQLite**: Lightweight database with async operations
- **Uvicorn**: High-performance ASGI server with hot reload
- **Session Management**: Secure session-based authentication with FastAPI

### Frontend Technologies
- **Bootstrap 5**: Modern responsive CSS framework with utility classes
- **Font Awesome 6**: Comprehensive icon library with crypto-themed icons
- **Vanilla JavaScript ES6+**: Modern JavaScript with async/await and module patterns
- **CSS3 Advanced**: Glassmorphism effects, animations, and responsive grids
- **Jinja2**: Powerful templating engine with inheritance and macros

### Development Tools
- **Environment Management**: Auto-generated .env configuration
- **Hot Reload**: Live development with automatic server restart
- **API Documentation**: Interactive Swagger UI at `/api/docs`
- **Logging System**: Comprehensive logging with debugging support
- **Error Handling**: Graceful error recovery with user-friendly messages

### Architecture Features
- **Modular Design**: Clean separation of concerns with organized codebase
- **RESTful APIs**: Comprehensive endpoint coverage with proper HTTP methods
- **Real-time Updates**: Live data synchronization without page refreshes
- **Responsive First**: Mobile-optimized with progressive enhancement
- **Security**: CORS configuration, session validation, and input sanitization

## 🔧 **Recent Critical Fixes (January 2025)**

### ⚡ **Authentication System Recovery**
- **JavaScript Error Resolution**: Fixed duplicate variable declarations causing SyntaxError in auth.js
- **API Integration Fix**: Added missing auth methods to EnhancedAPIClient for complete registration/login functionality
- **Response Format Standardization**: Updated all auth endpoints to return consistent `{success: true, data: {...}}` format
- **Session Data Enhancement**: Complete user initialization with GEM coins, level, experience, and gaming stats
- **Template Reference Fix**: Corrected login/register routes to use proper template files

### ⚡ **Inventory System Recovery**
- **Script Loading Order Fix**: Added utils.js to base.html script loading sequence for proper dependency resolution
- **Undefined Error Resolution**: Fixed "Cannot read properties of undefined (reading 'length')" in displayInventoryItems()
- **Debounce Function Access**: Resolved "Cannot read properties of undefined (reading 'debounce')" in search functionality
- **Stats Calculation Fix**: Replaced hardcoded zero stats with dynamic calculation from actual inventory data
- **API Response Handling**: Enhanced response structure parsing with fallback mechanisms

### ⚡ **Technical Improvements**
- **Error Recovery**: Graceful handling of API failures with user-friendly messages
- **Real-time Statistics**: Dynamic dashboard updates showing accurate user progression
- **Enhanced Debugging**: Comprehensive console logging for troubleshooting 
- **Code Quality**: Eliminated duplicate code and improved error handling patterns

## 🎯 Current Status (January 2025)

### ✅ Completed Major Features
- **🔐 Authentication System**: Complete user management with session-based auth
- **🎮 Gaming Platform**: Crypto roulette with provably fair mechanics
- **💎 Virtual Economy**: GEM coin system with inventory management
- **📊 Dashboard Integration**: Real-time stats with accurate data synchronization
- **🎯 Gamification**: XP/leveling system with achievement tracking
- **🌐 Social Features**: Friend system, leaderboards, and community integration
- **🎨 Modern UI/UX**: Glassmorphism design with consistent branding
- **📱 Responsive Design**: Mobile-first approach with adaptive layouts

### ✅ Recent Updates (January 2025)
- **Dashboard Stats Fix**: Real-time synchronization of user statistics
- **Leveling System**: Exponential XP progression with visual progress indicators  
- **Inventory Recovery**: Complete restoration of inventory system functionality
- **Authentication Flow**: Seamless login state management and UI updates
- **Branding Consistency**: Unified "CryptoChecker Gaming Platform" across all pages
- **API Integration**: Enhanced error handling and session-based authentication

### 🚀 Platform Capabilities
- **Multi-Game Support**: Roulette, dice, crash, plinko gaming variants
- **Virtual Trading**: Complete item marketplace with peer-to-peer trading
- **Social Gaming**: Leaderboards, achievements, and community features
- **Real-time Analytics**: Live user statistics and performance tracking
- **Administrative Tools**: Complete platform management and moderation system

## 📚 Documentation

### 📖 Available Documentation
- **[BRANDING_UPDATED.md](BRANDING_UPDATED.md)** - Complete branding consistency documentation
- **[API Documentation](http://localhost:8000/api/docs)** - Interactive Swagger UI (when server is running)
- **[PROGRESS.md](PROGRESS.md)** - Detailed development progress and recent changes
- **[INIT.md](INIT.md)** - Project initialization overview, endpoints, configuration, and conventions

## 🔄 Live Platform Stats & Sparklines

- The Home dashboard shows always-rising platform counters with subtle sparklines.
- Backed by `GET /api/platform/stats`; refreshed every ~15s and animated per-second on the client.

## 👥 Friends System & Social Bots

- Friends endpoints (session-based):
  - `GET /api/social/friends`, `GET /api/social/friends/requests`
  - `POST /api/social/friends/request` (send), `POST /api/social/friends/requests/{id}` (ACCEPT/DECLINE), `DELETE /api/social/friends/{friend_id}` (remove)
- Bots for demo:
  - `POST /api/social/bots/nudge` – trigger bot requests to current user
  - `GET/PUT /api/social/bots/settings` – per-user opt-out toggle
- Bot configuration via `.env`:
  - `BOTS_ENABLED=true`, `BOTS_MIN_SEC=30`, `BOTS_MAX_SEC=90`, `BOTS_PENDING_CAP=5`, `BOTS_SEED_ACCEPTED=2`, `BOTS_SEED_PENDING=1`
  - Users can opt-out on `/social` using the allow-bots switch

## 🧑‍💼 Profile & Avatar

- `/profile` page allows editing display name and bio.
- Avatar upload at `POST /api/profile/avatar` (4MB max, MIME-validated) with optional thumbnailing.
- Remove avatar at `POST /api/profile/avatar/remove`.

### 🔧 Development Guide

#### Running in Development Mode
```bash
# Install dependencies
pip install -r requirements.txt

# Start with hot reload
python run.py

# Access the platform
open http://localhost:8000
```

#### Environment Configuration
The platform automatically creates a `.env` file with default settings:
```env
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
HOST=localhost
PORT=8000
DATABASE_URL=sqlite+aiosqlite:///./crypto_gaming.db
```

#### Testing the Platform
1. **Quick Demo**: Use "Try Demo" button for instant access
2. **Full Registration**: Create account via `/register`
3. **API Testing**: Visit `/api/docs` for interactive API exploration
4. **Mobile Testing**: Platform is fully responsive on all devices

### 🚀 Deployment

#### Production Deployment
```bash
# Update environment for production
export DEBUG=False
export SECRET_KEY=your-secure-secret-key
export HOST=0.0.0.0
export PORT=8000

# Run with production server
python run.py
```

#### Docker Deployment (Optional)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "run.py"]
```

## 🎉 Success Stories

### ✅ **Complete Platform Recovery**
Successfully restored and enhanced the entire platform after major refactoring, including:
- Fixed all 404 navigation errors
- Restored complete inventory system functionality  
- Implemented real-time dashboard statistics
- Achieved 100% consistent branding across all pages

### ✅ **Advanced Gamification**
Built comprehensive gamification system with:
- Dynamic XP/leveling with exponential progression
- 50+ achievements across multiple categories
- Complete virtual economy with GEM coins
- Social features and community integration

### ✅ **Modern Architecture**
Implemented professional-grade architecture:
- RESTful API with 25+ endpoints
- Session-based authentication with real-time state management
- Modular codebase with clean separation of concerns
- Comprehensive error handling and logging

---

## 🎯 **Ready to Play!**

The CryptoChecker Gaming Platform is now a complete, production-ready virtual gaming environment with professional UI/UX, comprehensive gamification, and robust technical architecture.

**Start your crypto gaming adventure**: `python run.py` → http://localhost:8000

---

*Built with ❤️ using FastAPI, modern web technologies, and a passion for crypto gaming*

## 🤝 Contributing

This project is actively developed with a focus on:
- **User Experience**: Intuitive, engaging interfaces
- **Performance**: Fast, responsive interactions
- **Code Quality**: Clean, maintainable, well-documented code
- **Innovation**: Cutting-edge web technologies and design patterns

## 📄 License

This project is for educational and demonstration purposes.

---

**🎰 Ready to play? Start the server with `python run.py` and visit [localhost:8000](http://localhost:8000) to begin your crypto gaming adventure!**

# 🎰 CryptoChecker Gaming Platform

A modern, full-stack crypto gaming and trading platform built with FastAPI, featuring stunning visual design, real-time gaming, and comprehensive authentication systems.

## ✨ Latest Features (September 2025)

### 🎮 **Enhanced Gaming Experience**
- **Crypto Roulette**: Fully functional roulette game with realistic wheel animations
- **Advanced Animations**: Particle effects, smooth spinning, countdown timers
- **Responsive Design**: Beautiful wheel scaling from desktop to mobile
- **Real-time Betting**: Live bet placement with visual feedback and proper payouts

### 🎨 **Visual Enhancement System**
- **Glassmorphism Theme**: Modern frosted glass effects with crypto-themed gradients
- **Professional Icons**: Complete crypto currency icon set with interactive effects
- **Micro-interactions**: Hover effects, loading states, and smooth transitions
- **Enhanced Roulette Wheel**: 400px wheel with proper number positioning and colors

### 🔐 **Authentication & User Management**
- **Session-based Authentication**: Secure login/register system with FastAPI sessions
- **Demo Account System**: Easy testing with one-click demo login
- **Enhanced UI**: Beautiful login/register forms with glassmorphism design
- **Real-time Auth State**: Automatic UI updates based on authentication status

### 🎯 **Core Gaming Features**
- Paper trading with RiskPolicy (max position %, trade value %, open positions)
- Virtual wallet + crypto holdings that mirror paper trades
- Consumables with active effects (XP multiplier, GEM multiplier, drop rate bonus)
- Item drops with rarity tiers; inventory with filters/sort/pagination
- Real-time roulette gaming with proper betting mechanics

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
- **Home Page**: http://localhost:8000/
- **Trading Dashboard**: http://localhost:8000/trading
- **Crypto Roulette**: http://localhost:8000/gaming/roulette
- **User Registration**: http://localhost:8000/register
- **User Login**: http://localhost:8000/login
- **API Documentation**: http://localhost:8000/api/docs

### 🎮 Getting Started Guide

1. **Create Account**: Visit `/register` or use the "Demo Login" for instant access
2. **Explore Trading**: Check out the paper trading dashboard at `/trading`
3. **Play Roulette**: Experience the crypto roulette game at `/gaming/roulette`
4. **Place Bets**: Select colors, numbers, or crypto currencies and spin to win!

## 🔌 API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login  
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/demo-login` - Demo account access

### Trading System
- `GET /api/trading/portfolio/{id}/summary` - Portfolio overview
- `GET /api/trading/portfolio/{id}/transactions` - Transaction history
- `POST /api/trading/portfolio/{id}/orders` - Place trading orders
- `GET /api/trading/portfolio/{id}/orders/open` - View open orders
- `POST /api/trading/orders/{order_id}/cancel` - Cancel orders
- `GET/PUT /api/trading/risk-policy/{id}` - Risk management

### Gaming & Gamification
- `GET /api/trading/gamification/wallet` - Virtual wallet balance
- `GET /api/trading/gamification/inventory` - User inventory
- `POST /api/trading/gamification/consumables/{id}/use` - Use consumable items
- `GET /api/trading/gamification/effects` - Active effects
- `GET /api/trading/gamification/activity` - Gaming activity

### Testing & Debug
- `GET /api/test` - API health check
- `GET /api/auth/test` - Authentication system test
- `GET /api/auth/status` - Detailed auth status (debug)

## 🌐 User Interface

### Main Pages
- **`/`** - Landing page with platform overview and quick access
- **`/trading`** - Paper trading dashboard with portfolio management
- **`/gaming/roulette`** - Interactive crypto roulette game
- **`/gaming/inventory`** - Full inventory management with filters and consumables
- **`/login`** - Enhanced login page with glassmorphism design
- **`/register`** - User registration with real-time validation

### Key Features
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- **Real-time Updates**: Live authentication state and game interactions
- **Modern UI**: Glassmorphism effects, smooth animations, and crypto-themed styling
- **Accessibility**: Keyboard navigation and screen reader support
- **Progressive Enhancement**: Works with JavaScript disabled (basic functionality)

## Project Structure

```
PythonCryptoChecker/
├── run.py                  # Single entrypoint
├── scripts/                # Helper scripts
│   ├── stop-server.ps1     # Windows stop helper
│   └── stop-server.sh      # macOS/Linux stop helper
├── web/                    # FastAPI app, templates, routers
├── trading/                # Trading engine, models, DB
├── gamification/           # Virtual economy, items, effects
├── inventory/              # Inventory manager and trading system
├── auth/, gaming/, social/ # Foundations for next phases
└── README.md
```

## 🛠️ Technical Stack

### Backend
- **FastAPI**: Modern, fast web framework with automatic API documentation
- **SQLAlchemy**: Database ORM with async support
- **SQLite**: Lightweight database for development and demo
- **Pydantic**: Data validation and serialization
- **Uvicorn**: ASGI server for production-ready deployment

### Frontend
- **Bootstrap 5**: Responsive CSS framework
- **Font Awesome**: Professional icon library
- **Vanilla JavaScript**: No heavy frameworks, fast loading
- **CSS3**: Advanced animations, glassmorphism effects, and responsive design
- **Jinja2**: Server-side templating with component reusability

### Features Implemented
- ✅ **Authentication System**: Session-based login/register with validation
- ✅ **Crypto Roulette Game**: Fully functional with realistic betting mechanics
- ✅ **Paper Trading**: Risk-free trading environment with portfolio management
- ✅ **Visual Enhancement**: Glassmorphism theme with crypto-themed gradients
- ✅ **Responsive Design**: Mobile-first approach with adaptive layouts
- ✅ **Real-time Animations**: Wheel spinning, particle effects, micro-interactions

## 🎯 Current Status (September 2025)

### ✅ Completed Features
- **Phase 1**: Core platform architecture and database design
- **Phase 2**: Enhanced visual design system with glassmorphism theme
- **Phase 3**: Authentication system with session management
- **Phase 4**: Crypto roulette game with realistic mechanics
- **Phase 5**: Responsive design and mobile optimization
- **Phase 6**: Animation system with particle effects and smooth transitions

### 🚧 In Progress
- Advanced trading features and portfolio analytics
- Achievement system and user progression
- Social features and leaderboards
- Additional gaming modes and betting options

### 📋 Upcoming Features
- Real-time price feeds integration
- Advanced charting and technical analysis
- Multi-player gaming features
- Mobile app development
- Exchange API integrations

## 📚 Documentation

- **[PROGRESS.md](PROGRESS.md)** - Detailed development progress and recent changes
- **[VISUAL_ENHANCEMENT_GUIDE.md](VISUAL_ENHANCEMENT_GUIDE.md)** - Complete visual design system documentation
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Comprehensive deployment guide for all environments
- **[API Documentation](http://localhost:8000/docs)** - Interactive API documentation (when server is running)

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

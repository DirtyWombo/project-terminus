# CARDEA COMPLETE SYSTEM GUIDE

**DOCUMENT STATUS**: FULLY OPERATIONAL  
**DATE**: 2025-07-29  
**PROJECT**: Operation Badger - Sprint 19  
**SYSTEM**: Cardea Guardian - Complete Monitoring Solution  

---

## OVERVIEW

Cardea is now a **complete monitoring ecosystem** for Bull Call Spread options trading, featuring both Slack integration and a professional web interface identical to Janus. Named after the Roman goddess of hinges and thresholds, Cardea works alongside Janus to protect and monitor trades.

**System Status**: ✅ **FULLY OPERATIONAL**  
**Components**: 3 (Slack Agent + Web UI + Launcher)  
**Integration**: ✅ **Live Trading System**  
**UI Style**: 🎨 **Janus Carbon Copy** (with blue theme)  

---

## COMPLETE SYSTEM ARCHITECTURE

```
Cardea Guardian Ecosystem:
├── cardea_slack_agent.py         # Slack monitoring & control
├── cardea_web_ui.html             # Professional web dashboard  
├── cardea_web_server.py           # Flask API server
├── launch_cardea_complete.py      # Complete system launcher
└── Integration with:
    ├── live_trader.py             # Trading engine state
    ├── order_management_system.py # Order data
    ├── live_trader_config.json    # Configuration
    └── live_trader_state.json     # Real-time data
```

---

## COMPONENT DETAILS

### 1. Cardea Slack Agent (`cardea_slack_agent.py`)
**Purpose**: Real-time Slack monitoring and control  
**Commands**: 7 comprehensive commands  
**Integration**: Direct access to trading system state files  
**Features**:
- Real-time portfolio tracking
- Position monitoring with P&L
- Emergency stop capabilities
- Background alert system
- Performance analytics

### 2. Cardea Web UI (`cardea_web_ui.html` + `cardea_web_server.py`)
**Purpose**: Professional web dashboard (Janus-style)  
**Theme**: Deep blue background with purple gradients  
**Features**:
- Identical layout to Janus UI
- Real-time data integration
- Bull Call Spread specific metrics
- Sprint 19 validation tracking
- Responsive design

### 3. Complete System Launcher (`launch_cardea_complete.py`)
**Purpose**: Orchestrated system deployment  
**Features**:
- Prerequisites checking
- Component lifecycle management
- System health monitoring
- Automatic crash recovery
- Graceful shutdown

---

## DEPLOYMENT INSTRUCTIONS

### Quick Start (Recommended)
```bash
# Launch complete Cardea system
python launch_cardea_complete.py

# System will start:
# ✅ Cardea Slack Agent
# ✅ Cardea Web UI (http://localhost:5001)  
# ✅ System monitoring
```

### Individual Components
```bash
# Slack agent only
python cardea_slack_agent.py

# Web UI only  
python cardea_web_server.py

# Check status
curl http://localhost:5001/api/cardea/status
```

### Prerequisites
- Python 3.7+
- Required packages: `pip install flask flask-cors python-dotenv slack-bolt yfinance`
- Environment variables in `.env`:
  - `CARDEA_SLACK_BOT_TOKEN`
  - `CARDEA_SLACK_APP_TOKEN`
- Trading system files present

---

## USER INTERFACES

### 1. Slack Interface
**Commands Available**:
- `/cardea-status` - Complete system health + portfolio overview
- `/cardea-positions` - All open positions with real-time P&L
- `/cardea-logs` - Recent trading activity and system logs
- `/cardea-performance` - Trading metrics and strategy analytics
- `/cardea-market` - Current SPY data and entry conditions
- `/cardea-emergency-stop` - 🚨 Liquidate all positions and halt system
- `/cardea-help` - Show complete command reference

### 2. Web Interface
**URL**: http://localhost:5001  
**Style**: Professional dashboard identical to Janus  
**Sections**:
- **Header**: Cardea branding with search and user info
- **System Status**: Bull Call Spread system metrics
- **Strategy Performance**: Live validation tracking
- **Positions Table**: Real-time position monitoring
- **Portfolio Analytics**: Equity, cash, returns, drawdown
- **Success Criteria**: 30-day validation progress
- **Market Data**: Live SPY price and technical indicators

### 3. API Interface
**Base URL**: http://localhost:5001/api/cardea/  
**Endpoints**:
- `GET /status` - System status
- `GET /positions` - Position details
- `GET /market` - Market data  
- `GET /performance` - Performance metrics

---

## REAL-TIME DATA INTEGRATION

### Data Sources
Cardea pulls live data from the same sources as the trading system:
- **Portfolio Data**: `live_trader_state.json`
- **Order Data**: `oms_state.json`
- **Configuration**: `live_trader_config.json`
- **Logs**: `live_trader.log`
- **Market Data**: yfinance API (SPY)

### Update Frequency
- **Web UI**: 30-second refresh cycle
- **Slack Agent**: On-demand + 5-minute alert monitoring
- **API**: Real-time (no caching)

### Data Flow
```
Live Trading System → State Files → Cardea → User Interfaces
                                      ↓
                              Background Monitoring
                                      ↓
                              Automated Alerts
```

---

## DIFFERENCES FROM JANUS

### Visual Differences
- **Background**: Deep blue (#0A0B1E) instead of pure black
- **Accents**: Blue-tinted cards instead of white-tinted
- **Branding**: Cardea shield logo instead of robot
- **Theme**: Blue-purple gradients instead of pure purple

### Functional Differences
- **Focus**: Options trading instead of crypto
- **Strategy**: Bull Call Spread specific metrics
- **Validation**: Sprint 19 validation tracking
- **Data**: Options positions, spreads, DTE, Greeks
- **Commands**: Options-focused Slack commands

### Similarities
- **Layout**: Identical component arrangement
- **Style**: Same professional dashboard design
- **Architecture**: Flask API + HTML frontend
- **Responsiveness**: Same mobile breakpoints

---

## MONITORING CAPABILITIES

### System Health Monitoring
- **Uptime Tracking**: System running status
- **Component Health**: All services operational
- **Data Freshness**: Real-time data validation
- **Error Detection**: Automatic failure alerts

### Trading Performance Monitoring
- **Portfolio Metrics**: Equity, cash, returns
- **Position Tracking**: Open/closed positions with P&L
- **Strategy Analytics**: Win rate, profit factor, Sharpe ratio
- **Risk Metrics**: Drawdown, VaR, exposure limits

### Alert System
- **Drawdown Alerts**: >5% portfolio decline
- **System Alerts**: Component failures or crashes
- **Position Alerts**: Max position limits reached
- **Performance Alerts**: Success criteria deviations

---

## SPRINT 19 VALIDATION SUPPORT

### Success Criteria Tracking
1. **System Stability**: Uptime monitoring and crash detection
2. **Execution Fidelity**: Signal accuracy vs strategy logic
3. **Performance Tracking**: Returns correlation with backtest
4. **Order Fill Rate**: Successful execution percentage

### Validation Dashboard
- **Progress Tracking**: Day X/30 validation progress
- **Criteria Status**: Real-time success criteria evaluation
- **Performance Comparison**: Live vs backtest correlation
- **Milestone Reporting**: Weekly validation summaries

### Reporting Capabilities
- **Daily Reports**: Automated daily performance summaries
- **Weekly Reports**: Comprehensive validation progress
- **Alert Reports**: Critical event notifications
- **Final Report**: 30-day validation conclusion

---

## OPERATIONAL PROCEDURES

### Daily Operations
1. **Morning Checklist**:
   - Check system status via `/cardea-status`
   - Review overnight activity in web UI
   - Verify market data connectivity
   - Confirm position accuracy

2. **Intraday Monitoring**:
   - Monitor web dashboard for real-time updates
   - Watch for Slack alerts
   - Track position P&L changes
   - Verify signal generation

3. **End-of-Day Review**:
   - Generate daily performance report
   - Review all executed trades
   - Update validation progress
   - Document any issues

### Weekly Operations
- Generate weekly validation report
- Review success criteria progress
- Analyze system performance trends
- Update stakeholders on validation status

### Emergency Procedures
- **System Crash**: Use launcher to restart components
- **Trading Issues**: Use `/cardea-emergency-stop` command
- **Data Issues**: Check trading system state files
- **Network Issues**: Verify API connectivity

---

## TROUBLESHOOTING

### Common Issues

**Issue**: Web UI not loading  
**Solution**: Check if `cardea_web_server.py` is running, restart if needed

**Issue**: Slack commands not responding  
**Solution**: Check environment variables and restart `cardea_slack_agent.py`

**Issue**: No data in dashboard  
**Solution**: Ensure trading system is running and state files exist

**Issue**: API returning empty data  
**Solution**: Check trading system state files and restart components

### Diagnostic Commands
```bash
# Check system status
python launch_cardea_complete.py --status

# Test web API
curl http://localhost:5001/health

# Check log files
tail -f cardea_agent.log
```

---

## SYSTEM STATUS

**Cardea Guardian System**: ✅ **FULLY OPERATIONAL**

### Completed Features
- ✅ Complete Slack integration (7 commands)
- ✅ Professional web UI (Janus-style)
- ✅ Real-time data integration
- ✅ API endpoints for external access
- ✅ System health monitoring
- ✅ Automated alert system
- ✅ Sprint 19 validation support
- ✅ Complete system launcher
- ✅ Documentation and guides

### System Readiness
- **Technical**: ✅ All components tested and operational
- **Integration**: ✅ Live trading system integration complete
- **Monitoring**: ✅ Real-time monitoring active
- **Alerting**: ✅ Automated alert system functional
- **Documentation**: ✅ Complete operational guides provided

---

## CONCLUSION

Cardea is now a **complete monitoring ecosystem** for Bull Call Spread options trading, providing both Slack and web interfaces for comprehensive system oversight. As the sister AI to Janus, Cardea brings the same professional monitoring capabilities to equity options trading.

**Key Achievements**:
- 🎨 **Professional UI**: Janus-style web interface with options focus
- 💬 **Complete Slack Integration**: 7 comprehensive monitoring commands
- 📊 **Real-time Monitoring**: Live data from trading system
- 🛡️ **Guardian Capabilities**: Emergency controls and automated alerts
- 🚀 **Production Ready**: Complete deployment and monitoring solution

Cardea is ready to guard your Bull Call Spread trades during the critical 30-day Sprint 19 validation period, providing the oversight and control needed for successful strategy validation.

---

**Deployment Status**: ✅ **READY FOR PRODUCTION**  
**Launch Command**: `python launch_cardea_complete.py`  
**Web Access**: http://localhost:5001  
**Slack Access**: `/cardea-help` for commands  
**Sister to**: Janus AI (Crypto Trading)  
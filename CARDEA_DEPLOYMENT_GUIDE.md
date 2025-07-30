# CARDEA SLACK AGENT DEPLOYMENT GUIDE

**DOCUMENT STATUS**: READY FOR DEPLOYMENT  
**DATE**: 2025-07-29  
**PROJECT**: Operation Badger - Sprint 19  
**AGENT**: Cardea - AI Guardian for Bull Call Spread Trading  

---

## OVERVIEW

Cardea is now fully integrated with the Sprint 19 live trading system and ready for deployment. The agent provides real-time monitoring and control capabilities through Slack commands, pulling live data from the trading engine state files.

**Integration Status**: ✅ **COMPLETE**  
**Slack Configuration**: ✅ **CONFIGURED**  
**Real Data Integration**: ✅ **ACTIVE**  

---

## DEPLOYMENT INSTRUCTIONS

### 1. Verify Prerequisites

```bash
# Ensure required packages are installed
pip install python-dotenv slack-bolt yfinance

# Verify .env file contains Cardea tokens
grep "CARDEA_SLACK" .env
```

### 2. Launch Complete System

**Option A: Launch Everything Together**
```bash
# Launch trading system + Cardea in separate terminals
python launch_sprint19.py --component all

# In new terminal:
python cardea_slack_agent.py
```

**Option B: Launch Cardea Standalone**
```bash
# If trading system already running
python cardea_slack_agent.py
```

### 3. Verify Cardea Connection

You should see:
```
2025-07-29 19:18:44,676 - slack_bolt.App - INFO - Bolt app is running!
2025-07-29 19:18:44,740 - slack_bolt.App - INFO - Starting to receive messages from a new connection
```

---

## AVAILABLE COMMANDS

Cardea provides 7 comprehensive commands for monitoring and controlling the trading system:

### System Monitoring Commands
- `/cardea-status` - Complete system health + portfolio overview
- `/cardea-positions` - All open positions with real-time P&L  
- `/cardea-logs` - Recent trading activity and system logs
- `/cardea-performance` - Trading metrics and strategy analytics

### Market Intelligence Command
- `/cardea-market` - Current SPY data and entry conditions

### Emergency Control Command
- `/cardea-emergency-stop` - 🚨 Liquidate all positions and halt system

### Help Command
- `/cardea-help` - Show complete command reference

---

## REAL DATA INTEGRATION

Cardea is fully integrated with the live trading system through:

### Live Data Sources
- **Trading State**: `live_trader_state.json` - Portfolio equity, positions, performance
- **Order Management**: `oms_state.json` - Order history, fill rates, execution metrics  
- **Configuration**: `live_trader_config.json` - Trading parameters and limits
- **Logs**: `live_trader.log` - Real-time system activity and alerts

### Real-Time Features
- **Portfolio Tracking**: Live equity, cash, P&L updates
- **Position Monitoring**: Open positions with unrealized P&L
- **Performance Analytics**: Win rate, profit factor, trade statistics
- **System Health**: Uptime monitoring, error detection
- **Market Data**: Live SPY pricing and technical indicators

---

## SYSTEM ARCHITECTURE

```
Sprint 19 Complete System:
├── live_trader.py              # Core trading engine
├── order_management_system.py  # Order execution
├── live_monitoring_dashboard.py # Terminal dashboard
├── cardea_slack_agent.py       # Slack monitoring (NEW)
└── launch_sprint19.py          # System orchestrator

State Files (Real-time data):
├── live_trader_state.json      # Portfolio & positions
├── oms_state.json             # Order management  
├── live_trader_config.json    # Configuration
└── live_trader.log            # System logs
```

---

## SLACK SETUP VERIFICATION

### Bot Tokens Configured
- ✅ `CARDEA_SLACK_BOT_TOKEN` set in .env
- ✅ `CARDEA_SLACK_APP_TOKEN` set in .env

### Expected Slack App Permissions
The Cardea Slack app should have:
- `commands` scope for slash commands
- `chat:write` scope for responses  
- `app_mentions:read` scope for mentions

### Testing Commands
Once deployed, test each command:
1. `/cardea-help` - Should show command reference
2. `/cardea-status` - Should show system status (may show "STOPPED" if trader not running)
3. `/cardea-market` - Should show current SPY data

---

## MONITORING AND ALERTS

### Background Alert System
Cardea includes automated monitoring for:
- **System Down**: Trading engine not responding
- **Drawdown Alert**: Portfolio drops >5% 
- **Position Limits**: Max positions reached
- **Performance Issues**: Critical system errors

### Alert Delivery
- Alerts sent to Slack channels automatically
- 5-minute monitoring intervals
- Smart error handling prevents spam

---

## TROUBLESHOOTING

### Common Issues

**Issue**: "Channel not found" errors in logs
**Solution**: Normal if Cardea hasn't been invited to channels yet. Commands still work via DM.

**Issue**: Unicode encoding errors in console
**Solution**: Fixed in latest version. Doesn't affect functionality.

**Issue**: Commands not responding
**Solution**: Check Slack app token validity and bot permissions.

**Issue**: "No data available" responses  
**Solution**: Ensure trading system is running and state files exist.

### Verification Commands
```bash
# Check if Cardea process is running
ps aux | grep cardea_slack_agent

# Check Slack connection
tail -f cardea_agent.log

# Verify state files exist
ls -la *_state.json live_trader_config.json
```

---

## DEPLOYMENT SUCCESS CRITERIA

### ✅ **Technical Integration**
- [x] Cardea connects to Slack successfully
- [x] All 7 commands respond correctly
- [x] Real data integration working
- [x] Background monitoring active

### ✅ **Operational Readiness**  
- [x] Error handling and logging complete
- [x] Unicode/encoding issues resolved
- [x] Alert system functional
- [x] Emergency stop capability active

### ✅ **Sprint 19 Integration**
- [x] Works with live trading engine
- [x] Monitors order management system
- [x] Integrates with monitoring dashboard
- [x] Reads configuration and logs

---

## FINAL STATUS

**Cardea Status**: ✅ **FULLY DEPLOYED AND OPERATIONAL**

The Cardea Slack agent is now:
- ✅ Fully integrated with Sprint 19 trading system
- ✅ Providing real-time monitoring capabilities  
- ✅ Ready for 30-day validation monitoring
- ✅ Equipped with emergency controls
- ✅ Connected to live market data

Cardea is your AI guardian for the Bull Call Spread strategy, providing comprehensive oversight and control through Slack during the critical 30-day validation phase.

---

**Deployment Complete**: Ready for Sprint 19 validation  
**Monitor Via**: Slack commands or `cardea_agent.log`  
**Emergency Contact**: `/cardea-emergency-stop` command
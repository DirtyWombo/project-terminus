# Project Terminus 🚀

**Automated Futures Trading System for Proprietary Firm Evaluations**

[![Status](https://img.shields.io/badge/Status-Sprint%201%20Development-orange)](https://github.com/DirtyWombo/project-terminus)
[![Target](https://img.shields.io/badge/Target-Apex%2025K%20Evaluation-blue)](https://apextraderfunding.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> *"Disciplined automation meets systematic risk management"*

---

## 📋 Table of Contents

- [🎯 Project Overview](#-project-overview)
- [🏆 Mission & Goals](#-mission--goals)
- [⚡ Key Features](#-key-features)
- [🛠️ Technical Specifications](#️-technical-specifications)
- [📊 Trading Strategy](#-trading-strategy)
- [🛡️ Risk Management](#️-risk-management)
- [🗺️ Development Roadmap](#️-development-roadmap)
- [🚀 Getting Started](#-getting-started)
- [📈 Performance Targets](#-performance-targets)
- [🔗 Links & Resources](#-links--resources)

---

## 🎯 Project Overview

**Project Terminus** is a cutting-edge automated futures trading system engineered specifically to pass proprietary trading firm evaluations. Built with institutional-grade architecture and systematic risk management, Terminus represents a complete paradigm shift from discretionary trading to fully automated, rule-based execution.

### What Makes Terminus Different

- **🎯 Single Purpose Focus**: Designed exclusively for prop firm evaluations
- **🛡️ Risk-First Architecture**: The Terminus Governor ensures rule compliance at all times  
- **⚡ Lightning Fast Execution**: Microsecond-precision trade execution via Tradovate API
- **📊 Professional Data**: Institutional-quality market data through Databento
- **🤖 Full Automation**: Zero human intervention required during trading hours

### The Problem We Solve

Most prop firm candidates fail due to emotional decision-making and inadequate risk management. Project Terminus eliminates human psychology from trading by implementing systematic, rule-based automation with real-time compliance monitoring.

---

## 🏆 Mission & Goals

### Primary Mission
**Pass the Apex Trader Funding 25K evaluation by achieving $1,500 profit while maintaining strict adherence to all risk management rules.**

### Success Criteria
- ✅ **Profit Target**: Reach $26,500 account balance (+$1,500 profit)
- ✅ **Risk Compliance**: Never breach $1,500 trailing threshold 
- ✅ **Rule Adherence**: 100% compliance with all Apex evaluation rules
- ✅ **Trading Days**: Complete minimum 7 trading days requirement
- ✅ **System Reliability**: Maintain 99.9% uptime during evaluation period

### Long-term Vision
1. **Phase 1**: Pass Apex 25K evaluation *(Current Focus)*
2. **Phase 2**: Scale to larger evaluation accounts (50K, 100K, 250K)
3. **Phase 3**: Deploy across multiple prop firms simultaneously
4. **Phase 4**: Develop multi-strategy portfolio approach

---

## ⚡ Key Features

### 🛡️ **The Terminus Governor**
Our proprietary risk management system that makes Project Terminus unique:

```
RISK CALCULATIONS (Real-time):
Current Risk Budget = Account Balance - (Highest Balance - $1,500)

PROTECTION LEVELS:
🟢 Normal: Risk Budget > $500 (Full trading enabled)
🟡 Caution: Risk Budget $100-$500 (Reduced position sizing)
🔴 Emergency: Risk Budget < $100 (No new trades)
🚨 Critical: Risk Budget < $50 (Force close all positions)
```

### 📊 **Directional Futures Strategy**
- **Instrument**: /MES (Micro E-mini S&P 500 Futures)
- **Signal Generation**: 200-day MA regime filter + 20-day EMA pullbacks
- **Position Sizing**: Conservative 1 micro contract starting approach
- **Market Coverage**: Nearly 24/5 trading availability

### 🚀 **Professional Infrastructure**
- **Market Data**: Databento professional-grade feeds
- **Execution**: Tradovate modern futures platform
- **Monitoring**: Real-time Slack integration + web dashboard
- **Compliance**: Automated rule validation and enforcement

### 🔄 **Full Automation**
- Zero manual intervention required
- Automated position management
- Real-time risk monitoring
- Emergency shutdown protocols
- Comprehensive audit trails

---

## 🛠️ Technical Specifications

### **Core Architecture**

```
Project Terminus System:
├── 📡 Data Layer: Databento API
├── 🧠 Strategy Engine: 200MA/20EMA Directional Signals  
├── 🛡️ Terminus Governor: Real-time risk management
├── ⚡ Execution Layer: Tradovate OMS
├── 📊 Monitoring: Slack + Web Dashboard
└── 💾 State Management: JSON persistence
```

### **Technology Stack**

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Market Data** | Databento API | Professional CME futures data |
| **Execution** | Tradovate API | Modern futures broker platform |
| **Runtime** | Python 3.11+ | Core application framework |
| **Risk Engine** | Custom Governor | Proprietary risk management |
| **Monitoring** | Slack Bot + Flask | Real-time oversight |
| **Storage** | JSON + LFS | State persistence |

### **System Requirements**

- **Python**: 3.11 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 10GB available space
- **Network**: Stable internet connection (10Mbps+)
- **OS**: Windows 10/11, macOS 12+, or Linux

---

## 📊 Trading Strategy

### **The Directional Futures Approach**

Our strategy is built on time-tested institutional methods:

#### **Market Regime Detection**
```python
# Bull Market Condition
SPY_Price > 200_Day_Moving_Average

# Entry Signal  
Price_touches_20_Day_EMA_after_pullback_in_bull_market
```

#### **Position Management**
- **Entry**: Directional bias confirmed by dual moving average system
- **Size**: 1 Micro /MES contract ($5/point, ~$300 margin)
- **Risk**: Maximum $50 risk per trade (10-point stop loss)
- **Target**: Variable based on market conditions

#### **Trade Logic Flow**
1. **Regime Check**: Confirm bull market (SPY > 200MA)
2. **Signal Generation**: Wait for 20EMA pullback completion  
3. **Governor Approval**: Risk budget validation
4. **Position Entry**: Execute /MES long position
5. **Management**: Automated stop loss and profit targets
6. **Exit**: Systematic position closure

---

## 🛡️ Risk Management

### **Apex Trader Funding 25K Rules**

| Parameter | Limit | Terminus Implementation |
|-----------|-------|------------------------|
| **Starting Capital** | $25,000 | Baseline account balance |
| **Profit Target** | $1,500 | Automated achievement tracking |
| **Trailing Threshold** | $1,500 | Real-time Governor monitoring |
| **Daily Loss Limit** | None | N/A (rule doesn't exist) |
| **Min Trading Days** | 7 | Automated day counter |
| **Max Contracts** | 4 Mini/40 Micro | Conservative 1 Micro limit |

### **The Terminus Governor Protocol**

Our proprietary risk management system operates on multiple levels:

#### **Level 1: Position-Based Risk**
- Maximum 1 micro contract position
- $50 maximum risk per trade
- 2% portfolio risk limit

#### **Level 2: Account-Based Risk**  
- Real-time trailing threshold monitoring
- Automated position sizing based on risk budget
- Emergency shutdown protocols

#### **Level 3: System-Based Risk**
- Connection monitoring and failsafes  
- Data quality validation
- Execution error handling

---

## 🗺️ Development Roadmap

### **3-Sprint Focused Development Plan**

| Sprint | Timeline | Focus | Deliverables | Success Criteria |
|--------|----------|-------|--------------|------------------|
| **Sprint 1** | Weeks 1-2 | Core Integration | • Databento connection<br/>• Tradovate sandbox<br/>• Signal generation | Live /MES data + directional signals |
| **Sprint 2** | Weeks 3-4 | Terminus Governor | • Risk management module<br/>• Trailing threshold monitoring<br/>• Trade approval system | 100% rule compliance in all scenarios |
| **Sprint 3** | Weeks 5-6 | System Validation | • Enhanced backtester<br/>• Full integration test<br/>• Live deployment prep | Profitable backtest + ready for evaluation |

### **Current Status: Sprint 1 Development**

**🔧 In Progress:**
- [ ] Databento API integration
- [ ] Tradovate sandbox connection  
- [ ] Basic 200MA/20EMA signal generation
- [ ] Development environment setup

**📋 Next Up:**
- Sprint 2: Terminus Governor development
- Sprint 3: Comprehensive system validation

---

## 🚀 Getting Started

### **Prerequisites**

```bash
# Core Dependencies
pip install databento pandas numpy python-dotenv requests websocket-client

# Tradovate Integration  
pip install tradovate-api-client

# Monitoring & Alerts
pip install slack-bolt flask flask-cors schedule pytz psutil
```

### **Environment Configuration**

Create a `.env` file with your API credentials:

```bash
# Databento (Professional Market Data)
DATABENTO_API_KEY=your-databento-api-key

# Tradovate (Futures Execution)
TRADOVATE_API_KEY=your-tradovate-api-key
TRADOVATE_API_SECRET=your-tradovate-api-secret
TRADOVATE_ACCOUNT_ID=your-account-id
TRADOVATE_ENVIRONMENT=sandbox  # Start with sandbox

# Apex Evaluation Parameters
APEX_STARTING_CAPITAL=25000
APEX_PROFIT_TARGET=1500
APEX_TRAILING_THRESHOLD=1500
APEX_MIN_TRADING_DAYS=7

# Optional: Slack Monitoring
TERMINUS_SLACK_BOT_TOKEN=xoxb-your-bot-token
TERMINUS_SLACK_APP_TOKEN=xapp-your-app-token
```

### **Development Workflow**

```bash
# Sprint 1: Test Connections
python test_connections.py              # Validate API access
python databento_client.py --test       # Test market data feed
python tradovate_oms.py --sandbox       # Test execution platform

# Sprint 2: Governor Development  
python governor_apex.py --test          # Test risk management
python trailing_threshold_monitor.py    # Test drawdown tracking

# Sprint 3: Full Validation
python terminus_launcher.py --validate  # Complete system test
python validation_report.py --apex      # Generate compliance report
```

---

## 📈 Performance Targets

### **Evaluation Success Metrics**

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Profit Achievement** | $1,500+ | Account balance ≥ $26,500 |
| **Rule Compliance** | 100% | Zero rule violations |
| **System Uptime** | 99.9% | Continuous operation |
| **Trade Accuracy** | 95%+ | Execution vs. signal fidelity |
| **Risk Management** | Perfect | Never breach trailing threshold |

### **System Performance KPIs**

- **Latency**: < 100ms order execution
- **Data Quality**: 99.99% feed reliability  
- **Governor Response**: < 10ms risk calculations
- **Monitoring**: Real-time alert delivery
- **Recovery**: < 30s system restart capability

---

## 🔗 Links & Resources

### **🏢 Prop Firm & Trading**
- [Apex Trader Funding](https://apextraderfunding.com/) - Our target prop firm
- [Tradovate Platform](https://www.tradovate.com/) - Futures execution platform
- [Databento](https://databento.com/) - Professional market data

### **📚 Documentation & APIs**
- [Databento API Docs](https://docs.databento.com/) - Market data integration
- [Tradovate API Docs](https://api.tradovate.com/) - Trading platform API
- [CME /MES Specs](https://www.cmegroup.com/trading/equity-index/us-index/micro-e-mini-sandp500.html) - Contract specifications

### **🛠️ Development & Monitoring**
- [GitHub Repository](https://github.com/DirtyWombo/project-terminus) - Source code
- [Issues & Feature Requests](https://github.com/DirtyWombo/project-terminus/issues) - Development tracking
- [Wiki & Documentation](https://github.com/DirtyWombo/project-terminus/wiki) - Detailed guides

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Project Terminus is currently in focused development for Apex evaluation. Contributions will be welcomed after successful evaluation completion.

---

## ⚠️ Disclaimer

**IMPORTANT**: This software is for educational and research purposes. Trading futures involves substantial risk of loss. Past performance does not guarantee future results. Only trade with capital you can afford to lose.

---

<div align="center">

### 🎯 **Project Terminus: Where Discipline Meets Automation**

**Built for Success • Engineered for Compliance • Designed for Scale**

[🚀 **Get Started**](https://github.com/DirtyWombo/project-terminus) | [📊 **Documentation**](https://github.com/DirtyWombo/project-terminus/wiki) | [🛠️ **Issues**](https://github.com/DirtyWombo/project-terminus/issues)

</div>

---

*🤖 Generated with [Claude Code](https://claude.ai/code)*  
*Co-Authored-By: Claude <noreply@anthropic.com>*  
*Last Updated: July 31, 2025 - Project Terminus Launch*
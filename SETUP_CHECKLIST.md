# Project Terminus - Setup Checklist & Placeholder Guide

**IMPORTANT**: This document lists all placeholders that need to be replaced with actual values before the system can run.

---

## 🚨 Critical Placeholders - Must Update Before Running

### 1. **Databento API Credentials**
**File**: `.env`
```bash
DATABENTO_API_KEY=your-databento-api-key-here  # ❌ PLACEHOLDER
```
**Action Required**:
1. Sign up at https://databento.com/
2. Create an account and subscribe to CME futures data
3. Generate API key from dashboard
4. Replace placeholder with actual key

**Cost**: Check current Databento pricing for professional data feeds

---

### 2. **Tradovate API Credentials**
**File**: `.env`
```bash
TRADOVATE_API_KEY=your-tradovate-api-key-here        # ❌ PLACEHOLDER
TRADOVATE_API_SECRET=your-tradovate-api-secret-here  # ❌ PLACEHOLDER
TRADOVATE_ACCOUNT_ID=your-tradovate-account-id-here  # ❌ PLACEHOLDER
TRADOVATE_CID=your-tradovate-cid-here                # ❌ PLACEHOLDER
```
**Action Required**:
1. Sign up at https://www.tradovate.com/
2. Start with SANDBOX/DEMO account (free)
3. Navigate to API Management in account settings
4. Create new API application
5. Copy all credentials to .env file

**Important**: Always start with `TRADOVATE_ENVIRONMENT=sandbox`

---

## 📧 Optional Placeholders - For Enhanced Features

### 3. **Slack Integration** (Optional)
**File**: `.env`
```bash
TERMINUS_SLACK_BOT_TOKEN=xoxb-your-slack-bot-token-here  # ❌ PLACEHOLDER
TERMINUS_SLACK_APP_TOKEN=xapp-your-slack-app-token-here  # ❌ PLACEHOLDER
TERMINUS_SLACK_CHANNEL_ID=your-channel-id-here           # ❌ PLACEHOLDER
```
**If Using Slack**:
1. Go to https://api.slack.com/apps
2. Create new app "Project Terminus"
3. Add OAuth scopes: `chat:write`, `channels:read`
4. Install to workspace
5. Copy tokens from OAuth & Permissions page

---

### 4. **Emergency Contacts**
**File**: `.env`
```bash
EMERGENCY_EMAIL=your-email@example.com    # ❌ PLACEHOLDER
EMERGENCY_SMS=+1-your-phone-number        # ❌ PLACEHOLDER
```
**Action**: Replace with your actual contact information

---

### 5. **Security Keys**
**File**: `.env`
```bash
SECRET_KEY=generate-a-secure-random-key-here  # ❌ PLACEHOLDER
```
**Generate Key**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

### 6. **Database** (Future Enhancement)
**File**: `.env`
```bash
POSTGRES_PASSWORD=your-secure-password-here  # ❌ PLACEHOLDER
```
**Note**: Database is disabled by default (`DATABASE_ENABLED=false`)

---

## 🛠️ Required Software Installation

### Python Dependencies
```bash
# Core requirements
pip install databento
pip install websocket-client
pip install pandas numpy
pip install python-dotenv
pip install asyncio

# Tradovate (when available)
# pip install tradovate-api-client

# Optional monitoring
pip install slack-bolt
pip install flask flask-cors
```

### System Requirements
- Python 3.11 or higher
- 4GB RAM minimum
- Stable internet connection
- Windows 10/11, macOS 12+, or Linux

---

## ✅ Setup Verification Steps

### 1. **Environment Check**
```bash
python test_connections.py
```
This will verify all placeholders and connections.

### 2. **Individual Component Tests**
```bash
# Test market data
python databento_client.py --test

# Test execution platform
python tradovate_oms.py --sandbox

# Test strategy
python directional_futures_strategy.py
```

---

## 📋 Implementation TODOs in Code

### `databento_client.py`
- Line 35-37: Implement actual Databento SDK connection
- Line 65-73: Implement real subscription logic
- Line 91-104: Implement historical data fetch

### `tradovate_oms.py`
- Line 68-75: Implement OAuth authentication
- Line 76-78: Establish WebSocket connection
- Line 121-122: Send actual order to API
- Line 186: Fetch real contract ID

### `test_connections.py`
- Line 41-47: Add Databento SDK test
- Line 71-77: Add Tradovate WebSocket test

---

## 🚀 Quick Start After Setup

1. **Update all placeholders in `.env`**
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Test connections**: `python test_connections.py`
4. **Run strategy backtest**: `python directional_futures_strategy.py`
5. **Start paper trading**: `python terminus_launcher.py --paper`

---

## ⚠️ Important Reminders

1. **NEVER commit `.env` file to version control**
2. **Always start with SANDBOX/PAPER trading**
3. **Test thoroughly before using real money**
4. **Monitor the first 24 hours closely**
5. **Have emergency contacts ready**

---

## 📞 Support Resources

- **Databento Support**: https://databento.com/support
- **Tradovate Help**: https://www.tradovate.com/resources/
- **CME /MES Info**: https://www.cmegroup.com/trading/equity-index/us-index/micro-e-mini-sandp500.html
- **Project Issues**: https://github.com/DirtyWombo/project-terminus/issues

---

*Last Updated: July 31, 2025 - Project Terminus Sprint 1*
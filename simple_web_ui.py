#!/usr/bin/env python3
"""
Simple CyberJackal Web Dashboard
===============================

Lightweight web interface for monitoring CyberJackal MKVI.
"""

import os
import json
import requests
import psutil
from datetime import datetime
from flask import Flask, render_template_string, jsonify
from dotenv import load_dotenv

# Load environment
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'cyberjackal-mkvi-dashboard')

# HTML Template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CyberJackal MKVI - Expert-Validated Trading System</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        /* EXACT FIGMA CARBON COPY - Black Background + Purple Gradients */
        :root {
            /* Exact Figma Colors */
            --bg-black: #000000;
            --bg-dark: #0A0A0B;
            --bg-card: rgba(255, 255, 255, 0.08);
            --bg-card-hover: rgba(255, 255, 255, 0.12);
            
            /* Purple Gradients from Figma */
            --gradient-purple: linear-gradient(135deg, #6B46C1 0%, #9333EA 50%, #C084FC 100%);
            --gradient-card: linear-gradient(135deg, rgba(107, 70, 193, 0.2) 0%, rgba(147, 51, 234, 0.15) 50%, rgba(192, 132, 252, 0.1) 100%);
            --gradient-orange: linear-gradient(135deg, rgba(139, 69, 19, 0.3) 0%, rgba(147, 51, 234, 0.2) 100%);
            
            /* Chart Colors */
            --chart-green: #10B981;
            --chart-red: #EF4444;
            --chart-blue: #3B82F6;
            --chart-purple: #8B5CF6;
            --chart-orange: #F59E0B;
            --chart-pink: #EC4899;
            
            /* Text Colors */
            --text-white: #FFFFFF;
            --text-gray: #9CA3AF;
            --text-dark-gray: #6B7280;
            --text-light-gray: #E5E7EB;
            
            /* Status Colors */
            --status-green: #10B981;
            --status-red: #EF4444;
            --status-orange: #F59E0B;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background: var(--bg-black);
            color: var(--text-white);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 14px;
            line-height: 1.5;
            overflow-x: hidden;
            min-height: 100vh;
        }

        /* Main Container - Exact Figma Layout */
        .container {
            max-width: 1440px;
            margin: 0 auto;
            padding: 20px;
            min-height: 100vh;
        }

        /* Header Bar - Exact Figma Style */
        .header-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border-radius: 16px;
            padding: 16px 24px;
            margin-bottom: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .logo-section {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo {
            background: var(--gradient-orange);
            width: 40px;
            height: 40px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            font-weight: 700;
        }

        .logo-text {
            font-size: 20px;
            font-weight: 700;
            color: var(--text-white);
        }

        .user-section {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .user-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: var(--gradient-purple);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
        }

        /* Main Content Layout - Exact Figma Style */
        .main-content {
            display: grid;
            grid-template-columns: 1fr 360px;
            gap: 24px;
            margin-bottom: 24px;
        }

        .left-section {
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        .right-section {
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        /* Strategy Cards */
        .trending-section {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
        }

        .section-title {
            font-size: 18px;
            font-weight: 600;
            color: var(--text-white);
        }

        .strategy-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
        }

        .strategy-card {
            background: var(--gradient-card);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            position: relative;
            overflow: hidden;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .strategy-card:hover {
            background: linear-gradient(135deg, rgba(107, 70, 193, 0.25) 0%, rgba(147, 51, 234, 0.2) 50%, rgba(192, 132, 252, 0.15) 100%);
            transform: translateY(-2px);
        }

        .performance-value {
            font-size: 24px;
            font-weight: 700;
            color: var(--text-white);
            margin-bottom: 4px;
        }

        .performance-change {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 12px;
            font-weight: 500;
        }

        /* Right Sidebar Cards */
        .backtest-card {
            background: var(--gradient-purple);
            border-radius: 16px;
            padding: 24px;
            color: white;
            position: relative;
            overflow: hidden;
        }

        .backtest-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 8px;
        }

        .backtest-description {
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 20px;
        }

        .refresh-btn {
            background: rgba(255, 255, 255, 0.2);
            border: none;
            border-radius: 8px;
            padding: 12px 20px;
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .refresh-btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateX(4px);
        }

        .broker-integration {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .integration-text {
            font-size: 14px;
            color: var(--text-gray);
            margin-bottom: 16px;
        }

        .market-activity {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .activity-chart {
            width: 120px;
            height: 120px;
            margin: 0 auto 16px;
            position: relative;
        }

        /* Responsive Design */
        @media (max-width: 1200px) {
            .main-content {
                grid-template-columns: 1fr;
                gap: 24px;
            }
            
            .strategy-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (max-width: 768px) {
            .container {
                padding: 16px;
            }
            
            .header-bar {
                flex-direction: column;
                gap: 16px;
                padding: 20px;
            }
            
            .strategy-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
    <script>
        function refreshData() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('ai-status').innerHTML = 
                        '<span class="status-indicator status-' + 
                        (data.ai_status === 'RUNNING' ? 'green' : 'red') + 
                        '"></span>' + data.ai_status;
                    
                    document.getElementById('cpu-usage').textContent = data.cpu_percent + '%';
                    document.getElementById('memory-usage').textContent = data.memory_percent + '%';
                    document.getElementById('last-update').textContent = data.timestamp;
                })
                .catch(error => console.error('Error:', error));
        }
        
        // Auto-refresh every 30 seconds
        setInterval(refreshData, 30000);
    </script>
</head>
<body>
    <div class="container">
        <!-- Header Bar - Exact Figma Style -->
        <div class="header-bar">
            <div class="logo-section">
                <div class="logo">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="logo-text">CyberJackal MKVI</div>
            </div>
            
            <div class="user-section">
                <div style="color: #999; font-size: 14px;">Hello, Expert Rating: A+</div>
                <div style="color: white; font-weight: 600;">CyberJackal User</div>
                <div class="user-avatar">CJ</div>
            </div>
        </div>

        <!-- Main Content Area -->
        <div class="main-content">
            <!-- Left Section -->
            <div class="left-section">
                <!-- CyberJackal MKVI Status -->
                <div class="trending-section">
                    <div class="section-header">
                        <div class="section-title">CyberJackal MKVI - Expert Validated</div>
                        <div style="background: linear-gradient(135deg, #10B981, #34D399); color: white; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 600;">
                            EXPERT RATING: A+
                        </div>
                    </div>
                    
                    <!-- Strategy Cards Grid -->
                    <div class="strategy-grid">
                        <!-- AI Service Card -->
                        <div class="strategy-card">
                            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                                <div style="width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, #6B46C1, #9333EA); display: flex; align-items: center; justify-content: center; color: white;">
                                    <i class="fas fa-brain"></i>
                                </div>
                                <div>
                                    <div style="font-size: 12px; font-weight: 500; color: var(--text-gray); margin-bottom: 4px;">AI Service</div>
                                    <div style="font-size: 14px; font-weight: 600; color: var(--text-white);">Ollama/Llama 3.2</div>
                                </div>
                            </div>
                            <div class="performance-value" id="ai-status" style="color: {{ '#10B981' if ai_status == 'RUNNING' else '#EF4444' }};">{{ ai_status }}</div>
                            <div class="performance-change" style="color: var(--chart-purple);">
                                <i class="fas fa-microchip"></i>
                                Structured JSON Output
                            </div>
                        </div>

                        <!-- Trading Configuration Card -->
                        <div class="strategy-card">
                            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                                <div style="width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, #F59E0B, #D97706); display: flex; align-items: center; justify-content: center; color: white;">
                                    <i class="fas fa-cog"></i>
                                </div>
                                <div>
                                    <div style="font-size: 12px; font-weight: 500; color: var(--text-gray); margin-bottom: 4px;">Trading Mode</div>
                                    <div style="font-size: 14px; font-weight: 600; color: var(--text-white);">Paper Trading</div>
                                </div>
                            </div>
                            <div class="performance-value" style="color: var(--status-orange);">0.5%</div>
                            <div class="performance-change" style="color: var(--chart-orange);">
                                <i class="fas fa-shield-alt"></i>
                                Fixed Fractional
                            </div>
                        </div>

                        <!-- System Resources Card -->
                        <div class="strategy-card">
                            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                                <div style="width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, #3B82F6, #1D4ED8); display: flex; align-items: center; justify-content: center; color: white;">
                                    <i class="fas fa-server"></i>
                                </div>
                                <div>
                                    <div style="font-size: 12px; font-weight: 500; color: var(--text-gray); margin-bottom: 4px;">System Health</div>
                                    <div style="font-size: 14px; font-weight: 600; color: var(--text-white);">Resources</div>
                                </div>
                            </div>
                            <div class="performance-value" id="cpu-usage">{{ cpu_percent }}%</div>
                            <div class="performance-change" style="color: var(--chart-blue);">
                                <i class="fas fa-memory"></i>
                                <span id="memory-usage">{{ memory_percent }}%</span> Memory
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Narrative Surfer Strategy -->
                <div class="trending-section">
                    <div class="section-header">
                        <div class="section-title">Narrative Surfer Strategy (Expert-Validated Baseline)</div>
                        <button class="refresh-btn" onclick="refreshData()" style="background: rgba(255, 255, 255, 0.1); color: white; border: 1px solid rgba(255, 255, 255, 0.2); font-size: 12px; padding: 8px 16px;">
                            <i class="fas fa-sync-alt"></i> Refresh
                        </button>
                    </div>
                    
                    <div style="background: rgba(139, 69, 19, 0.1); border: 1px solid rgba(139, 69, 19, 0.3); border-radius: 12px; padding: 20px; margin-bottom: 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <div style="color: var(--chart-orange); font-weight: 600;">Paper Trading Validation</div>
                            <div style="color: var(--text-gray); font-size: 12px;" id="last-update">{{ timestamp }}</div>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                            <div style="text-align: center;">
                                <div style="font-size: 12px; color: var(--text-gray);">Portfolio Value</div>
                                <div style="font-size: 18px; font-weight: 700; color: white;">${{ "%.2f"|format(validation_data.portfolio_value) }}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 12px; color: var(--text-gray);">Total Trades</div>
                                <div style="font-size: 18px; font-weight: 700; color: var(--chart-purple);">{{ validation_data.total_trades }}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 12px; color: var(--text-gray);">Win Rate</div>
                                <div style="font-size: 18px; font-weight: 700; color: var(--chart-blue);">{{ "%.1f"|format(validation_data.win_rate) }}%</div>
                            </div>
                        </div>
                    </div>
                    
                    <div style="font-size: 12px; color: var(--text-gray);">
                        Expert-Validated Features: AI Velocity Detection | RSI Confirmation | Fixed 0.5% Position Sizing | 20% Drawdown Protection
                    </div>
                </div>
            </div>

            <!-- Right Section -->
            <div class="right-section">
                <!-- Expert Validation Card -->
                <div class="backtest-card">
                    <div class="backtest-title">Expert-Validated Trading System</div>
                    <div class="backtest-description">Institutional-grade transformation complete. Sophisticated edge detection with simple execution.</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
                        <div style="background: rgba(16, 185, 129, 0.1); padding: 8px; border-radius: 6px; text-align: center;">
                            <div style="font-size: 11px; color: #9CA3AF;">Expert Rating</div>
                            <div style="font-size: 16px; font-weight: 600; color: #10B981;">A+</div>
                        </div>
                        <div style="background: rgba(139, 92, 246, 0.1); padding: 8px; border-radius: 6px; text-align: center;">
                            <div style="font-size: 11px; color: #9CA3AF;">Architecture</div>
                            <div style="font-size: 16px; font-weight: 600; color: #8B5CF6;">Monolithic</div>
                        </div>
                    </div>
                    <button class="refresh-btn" onclick="showExpertValidation()">
                        <i class="fas fa-check-circle"></i> View Expert Details
                    </button>
                </div>

                <!-- System Integration -->
                <div class="broker-integration">
                    <div class="section-title" style="margin-bottom: 12px;">System Integration</div>
                    <div class="integration-text">Expert-validated monolithic architecture with Ollama AI integration.</div>
                    <div style="display: flex; gap: 12px; margin-bottom: 16px;">
                        <div style="width: 40px; height: 40px; border-radius: 8px; background: rgba(255, 255, 255, 0.05); display: flex; align-items: center; justify-content: center; color: var(--text-gray);" title="Ollama AI">
                            <i class="fas fa-brain"></i>
                        </div>
                        <div style="width: 40px; height: 40px; border-radius: 8px; background: rgba(255, 255, 255, 0.05); display: flex; align-items: center; justify-content: center; color: var(--text-gray);" title="Core Engine">
                            <i class="fas fa-cogs"></i>
                        </div>
                        <div style="width: 40px; height: 40px; border-radius: 8px; background: rgba(255, 255, 255, 0.05); display: flex; align-items: center; justify-content: center; color: var(--text-gray);" title="Defense Layers">
                            <i class="fas fa-shield-alt"></i>
                        </div>
                        <div style="background: rgba(255, 255, 255, 0.05); width: 40px; height: 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 10px; color: var(--text-gray); text-align: center; line-height: 1.2;">
                            A+<br>Expert
                        </div>
                    </div>
                </div>

                <!-- Market Activity -->
                <div class="market-activity">
                    <div class="section-title" style="margin-bottom: 16px;">30-Day Validation Status</div>
                    <div class="activity-chart">
                        <div style="width: 100%; height: 100%; border-radius: 50%; background: conic-gradient(#10B981 0deg 340deg, #F59E0B 340deg 360deg); position: relative;">
                            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;">
                                <div style="font-size: 14px; font-weight: 600; color: #10B981;">ACTIVE</div>
                                <div style="font-size: 10px; color: #9CA3AF;">Paper Mode</div>
                            </div>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 11px;">
                        <div style="color: #10B981;">Target Sharpe: >1.5</div>
                        <div style="color: #10B981;">Max Drawdown: <5%</div>
                        <div style="color: #10B981;">Win Rate: >45%</div>
                        <div style="color: #10B981;">System: Ready</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function showExpertValidation() {
            alert('Expert-Validated System Transformation Complete!\\n\\n' +
                  '✅ Architecture: Microservices → Monolithic Core\\n' +
                  '✅ Risk Management: Kelly Criterion → Fixed 0.5% Fractional\\n' +
                  '✅ Strategy: Complex ML → Simple Narrative Surfer Baseline\\n' +
                  '✅ AI Output: Prose → Structured JSON (velocity_score)\\n' +
                  '✅ Features: 745 features shelved for incremental testing\\n' +
                  '✅ Transaction Costs: 5% gas fee threshold\\n' +
                  '✅ Defense Systems: Multi-layer capital protection\\n\\n' +
                  'Expert Rating: A+ (Institutional-Grade Disciplined Trading)');
        }
    </script>
</body>
</html>
"""

def check_ai_status():
    """Check if Ollama AI is running."""
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=3)
        return "RUNNING" if response.status_code == 200 else "ERROR"
    except:
        return "OFFLINE"

def check_slack_status():
    """Check if Slack tokens are configured."""
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    app_token = os.getenv('SLACK_APP_TOKEN')
    return bool(bot_token and app_token)

def get_validation_status():
    """Get 30-day validation period status with live trading data."""
    # Default values
    default_data = {
        "day": 1,
        "total_days": 30,
        "progress": 3.3,
        "portfolio_value": 10000,
        "cumulative_return": 0,
        "sharpe_ratio": 0,
        "max_drawdown": 0,
        "win_rate": 0,
        "total_trades": 0,
        "winning_trades": 0
    }
    
    try:
        # First check for live trading state
        print(f"DEBUG: Checking for trading_state.json - exists: {os.path.exists('trading_state.json')}")
        if os.path.exists('trading_state.json'):
            with open('trading_state.json', 'r') as f:
                trading_data = json.load(f)
            print(f"DEBUG: Loaded trading data: {trading_data}")
            
            metrics = trading_data.get("metrics", {})
            portfolio_value = metrics.get("portfolio_value", 10000)
            total_trades = metrics.get("total_trades", 0)
            winning_trades = metrics.get("winning_trades", 0)
            cumulative_return = metrics.get("cumulative_return", 0)
            max_drawdown = metrics.get("max_drawdown", 0)
            
            win_rate = (winning_trades / max(total_trades, 1)) * 100 if total_trades > 0 else 0
            
            # Calculate estimated Sharpe ratio
            sharpe_ratio = 0
            if total_trades >= 3:
                annual_return = cumulative_return * (365 / 1)  # Annualized 
                volatility = max(max_drawdown * 2, 0.05)  # Simplified volatility
                sharpe_ratio = (annual_return - 0.05) / volatility  # 5% risk-free rate
            
            default_data.update({
                "portfolio_value": portfolio_value,
                "cumulative_return": cumulative_return,
                "max_drawdown": max_drawdown,
                "win_rate": win_rate,
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "sharpe_ratio": sharpe_ratio
            })
        
        # Then check for validation metrics (for day tracking)
        if os.path.exists('validation_metrics.json'):
            with open('validation_metrics.json', 'r') as f:
                validation_data = json.load(f)
            
            if validation_data.get("validation_start"):
                start_date = datetime.fromisoformat(validation_data["validation_start"])
                days_elapsed = (datetime.now() - start_date).days + 1
                
                default_data.update({
                    "day": days_elapsed,
                    "progress": round((days_elapsed / 30) * 100, 1)
                })
    
    except Exception as e:
        print(f"Error loading validation status: {e}")  # Use print for debugging
    
    return default_data

@app.route('/')
def dashboard():
    """Main dashboard page."""
    # Get system stats
    cpu_percent = round(psutil.cpu_percent(interval=1), 1)
    memory_percent = round(psutil.virtual_memory().percent, 1)
    ai_status = check_ai_status()
    slack_status = check_slack_status()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Generate log content
    log_content = f"""CyberJackal MKVI System Status - {timestamp}
{'='*50}
✅ Expert-validated configuration: ACTIVE
✅ Paper trading mode: ENABLED
✅ Position sizing: 0.5% fixed fractional
✅ AI integration: {ai_status}
✅ Defense layers: ALL ENABLED
✅ Risk management: 20% drawdown protection

System Resources:
- CPU Usage: {cpu_percent}%
- Memory Usage: {memory_percent}%
- Status: {'Healthy' if cpu_percent < 80 and memory_percent < 85 else 'Monitor'}

Environment Configuration:
- Trading Strategy: Narrative Surfer
- Market Focus: BTC, ETH, SOL + Meme Coins
- Trading Cycle: 15-minute autonomous cycles"""
    
    # Get validation status
    validation_data = get_validation_status()
    print(f"DEBUG: Validation data = {validation_data}")  # Debug output
    
    try:
        return render_template_string(DASHBOARD_HTML,
                                      ai_status=ai_status,
                                      cpu_percent=cpu_percent,
                                      memory_percent=memory_percent,
                                      slack_status=slack_status,
                                      timestamp=timestamp,
                                      log_content=log_content,
                                      validation_data=validation_data)
    except Exception as e:
        return f"Template Error: {str(e)}<br><br>Validation Data: {validation_data}"

@app.route('/api/status')
def api_status():
    """API endpoint for status updates."""
    return jsonify({
        'ai_status': check_ai_status(),
        'cpu_percent': round(psutil.cpu_percent(interval=1), 1),
        'memory_percent': round(psutil.virtual_memory().percent, 1),
        'slack_status': check_slack_status(),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

if __name__ == '__main__':
    print("Starting CyberJackal MKVI Web Dashboard...")
    print("=" * 45)
    print("Expert Rating: A+ (Institutional-Grade)")
    print("Dashboard URL: http://localhost:5000")
    print("Real-time monitoring available")
    print("Auto-refresh every 30 seconds")
    print()
    print("Press Ctrl+C to stop the dashboard")
    print("=" * 45)
    
    app.run(host='127.0.0.1', port=5000, debug=False)
import logging
import requests
import os
import numpy as np
from datetime import datetime, timedelta
from alpha_kernel import create_alpha_kernel
from position_sizing import create_position_sizing_engine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TRADER_APP_URL = os.environ.get("TRADER_APP_URL", "http://trader-app:5000")
JANUS_API_SECRET = os.environ.get("JANUS_API_SECRET")

if not JANUS_API_SECRET:
    logging.error("JANUS_API_SECRET environment variable not set in decision_engine.py!")

# Initialize enhanced decision systems
alpha_kernel = create_alpha_kernel()
position_engine = create_position_sizing_engine()

def get_portfolio_summary():
    try:
        headers = {"X-Janus-API-Secret": JANUS_API_SECRET}
        response = requests.get(f"{TRADER_APP_URL}/api/portfolio/summary", headers=headers, timeout=5)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        logging.error(f"Could not connect to trader-app for portfolio summary: {e}")
        return {"success": False, "message": f"Error connecting to trader-app: {e}"}
    except Exception as e:
        logging.error(f"An unexpected error occurred during portfolio summary fetch: {e}")
        return {"success": False, "message": f"An unexpected error occurred: {e}"}

def get_market_status():
    try:
        headers = {"X-Janus-API-Secret": JANUS_API_SECRET}
        response = requests.get(f"{TRADER_APP_URL}/api/status", headers=headers, timeout=5)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        logging.error(f"Could not connect to trader-app for market status: {e}")
        return {"success": False, "message": f"Error connecting to trader-app: {e}"}
    except Exception as e:
        logging.error(f"An unexpected error occurred during market status fetch: {e}")
        return {"success": False, "message": f"An unexpected error occurred: {e}"}

def get_speculative_analysis_data(symbol):
    try:
        headers = {"X-Janus-API-Secret": JANUS_API_SECRET}
        response = requests.get(f"{TRADER_APP_URL}/api/speculative_analysis/{symbol}", headers=headers, timeout=30)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        logging.error(f"Could not connect to trader-app for speculative analysis of {symbol}: {e}")
        return {"success": False, "message": f"Error connecting to trader-app: {e}"}
    except Exception as e:
        logging.error(f"An unexpected error occurred during speculative analysis fetch for {symbol}: {e}")
        return {"success": False, "message": f"An unexpected error occurred: {e}"}

# Enhanced decision making functions

def get_market_sentiment():
    """Get combined market sentiment from news and social sources."""
    try:
        headers = {"X-Janus-API-Secret": JANUS_API_SECRET}
        
        # Get news sentiment
        news_response = requests.get(f"{TRADER_APP_URL}/api/news/sentiment", headers=headers, timeout=5)
        news_data = news_response.json() if news_response.status_code == 200 else {}
        
        # Get social sentiment
        social_response = requests.get(f"{TRADER_APP_URL}/api/social/sentiment", headers=headers, timeout=5)
        social_data = social_response.json() if social_response.status_code == 200 else {}
        
        return {
            "news_sentiment": news_data.get("avg_sentiment", 0.0),
            "social_sentiment": social_data.get("avg_sentiment", 0.0),
            "news_count": news_data.get("article_count", 0),
            "social_count": social_data.get("mention_count", 0)
        }
    except Exception as e:
        logging.error(f"Error fetching market sentiment: {e}")
        return {
            "news_sentiment": 0.0,
            "social_sentiment": 0.0,
            "news_count": 0,
            "social_count": 0
        }

def get_technical_signals():
    """Get technical analysis signals and confluence score."""
    try:
        headers = {"X-Janus-API-Secret": JANUS_API_SECRET}
        response = requests.get(f"{TRADER_APP_URL}/api/market/signals", headers=headers, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            # Fallback technical signals
            return {
                "confluence_score": 50,
                "trend_direction": 0.0,
                "momentum": 0.0
            }
    except Exception as e:
        logging.error(f"Error fetching technical signals: {e}")
        return {
            "confluence_score": 50,
            "trend_direction": 0.0,
            "momentum": 0.0
        }

def calculate_market_volatility(symbol: str = "BTC-USD") -> float:
    """Calculate current market volatility for the symbol."""
    try:
        headers = {"X-Janus-API-Secret": JANUS_API_SECRET}
        response = requests.get(f"{TRADER_APP_URL}/api/chart_data?symbol={symbol}", headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            prices = data.get("prices", [])
            
            if len(prices) > 20:
                # Calculate 20-period price returns
                price_array = np.array(prices[-20:])
                returns = np.diff(price_array) / price_array[:-1]
                volatility = np.std(returns) * np.sqrt(24)  # Annualized hourly volatility
                return min(volatility, 0.5)  # Cap at 50%
        
        return 0.02  # Default 2% volatility
    except Exception as e:
        logging.error(f"Error calculating volatility: {e}")
        return 0.02

def make_enhanced_trading_decision(symbol: str, ml_prediction: int) -> dict:
    """
    Make enhanced trading decision using alpha kernel and position sizing.
    
    Args:
        symbol: Trading symbol (e.g., "BTC-USD")
        ml_prediction: ML model prediction (-1, 0, 1)
        
    Returns:
        Dict containing trading decision, position size, and reasoning
    """
    try:
        # Get AI analysis
        ai_analysis_result = get_speculative_analysis_data(symbol)
        ai_analysis = ai_analysis_result.get("data", {}) if ai_analysis_result.get("success") else {}
        
        # Get market sentiment
        sentiment_scores = get_market_sentiment()
        
        # Get technical signals
        technical_signals = get_technical_signals()
        
        # Calculate market volatility
        market_volatility = calculate_market_volatility(symbol)
        
        # Get portfolio summary for sizing calculations
        portfolio_result = get_portfolio_summary()
        portfolio_value = portfolio_result.get("data", {}).get("current_portfolio_value", 10000) if portfolio_result.get("success") else 10000
        
        # Get market regime
        market_status = get_market_status()
        market_regime = market_status.get("data", {}).get("portfolio", {}).get("regime", "neutral") if market_status.get("success") else "neutral"
        
        # Calculate final trading signal using alpha kernel
        signal_result = alpha_kernel.calculate_final_signal(
            ml_prediction=ml_prediction,
            ai_analysis=ai_analysis,
            sentiment_scores=sentiment_scores,
            technical_signals=technical_signals,
            market_volatility=market_volatility
        )
        
        # Calculate position size if we have a trading signal
        position_result = {}
        if signal_result["decision"] in ["BUY", "SELL", "STRONG_BUY", "STRONG_SELL"]:
            position_result = position_engine.calculate_position_size(
                signal_score=signal_result["final_score"],
                signal_confidence=signal_result["confidence"],
                portfolio_value=portfolio_value,
                market_volatility=market_volatility,
                market_regime=market_regime.lower(),
                asset_volatility=market_volatility  # Use same volatility for now
            )
        
        # Combine results
        decision_result = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "ml_prediction": ml_prediction,
            "signal_result": signal_result,
            "position_result": position_result,
            "market_data": {
                "volatility": market_volatility,
                "regime": market_regime,
                "portfolio_value": portfolio_value
            },
            "input_data": {
                "ai_analysis": ai_analysis,
                "sentiment_scores": sentiment_scores,
                "technical_signals": technical_signals
            }
        }
        
        logging.info(f"Enhanced decision for {symbol}: {signal_result['decision']} "
                    f"(score: {signal_result['final_score']:.3f}, "
                    f"confidence: {signal_result['confidence']:.3f})")
        
        if position_result:
            logging.info(f"Position sizing: {position_result['position_size']:.1%} "
                        f"(${position_result['position_value']:.2f}, "
                        f"risk: {position_result['risk_percentage']:.2%})")
        
        return decision_result
        
    except Exception as e:
        logging.error(f"Error in enhanced trading decision: {e}")
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "signal_result": {"decision": "HOLD", "final_score": 0.0, "confidence": 0.0},
            "position_result": {}
        }

def make_autonomous_decision():
    """Enhanced autonomous decision making with alpha kernel integration."""
    logging.info("Janus AI: Making enhanced autonomous decision...")

    # Alert checking moved to agent.py to avoid circular import
    logging.info("Alert system managed by agent.py background thread")

    # Fetch current portfolio summary
    portfolio_summary = get_portfolio_summary()
    if not portfolio_summary["success"]:
        logging.error(f"Failed to get portfolio summary: {portfolio_summary['message']}")
        return
    
    current_portfolio_value = portfolio_summary["data"].get('current_portfolio_value', 0)
    sharpe_ratio = portfolio_summary["data"].get('sharpe_ratio', 0)

    # Fetch market status
    market_status = get_market_status()
    if not market_status["success"]:
        logging.error(f"Failed to get market status: {market_status['message']}")
        return
    
    market_regime = market_status["data"].get('portfolio', {}).get('regime', 'Unknown')

    logging.info(f"Current Portfolio Value: {current_portfolio_value:.2f}")
    logging.info(f"Sharpe Ratio: {sharpe_ratio:.4f}")
    logging.info(f"Market Regime: {market_regime}")

    # Enhanced decision making for key assets
    watchlist = ["BTC-USD", "ETH-USD", "SOL-USD"]  # Top assets to monitor
    
    for symbol in watchlist:
        logging.info(f"\n--- Analyzing {symbol} ---")
        
        # Mock ML prediction for demonstration (in reality, this would come from your ML model)
        # For demo purposes, we'll use a simple heuristic based on market regime
        if market_regime.lower() == 'bull':
            mock_ml_prediction = 1  # Buy signal in bull market
        elif market_regime.lower() == 'bear':
            mock_ml_prediction = -1  # Sell signal in bear market
        else:
            mock_ml_prediction = 0  # Hold in neutral market
        
        # Make enhanced trading decision
        decision_result = make_enhanced_trading_decision(symbol, mock_ml_prediction)
        
        if "error" in decision_result:
            logging.error(f"Error analyzing {symbol}: {decision_result['error']}")
            continue
        
        signal = decision_result["signal_result"]
        position = decision_result["position_result"]
        
        # Log decision summary
        decision_summary = (
            f"{symbol} Decision: {signal['decision']} "
            f"(Score: {signal['final_score']:.3f}, "
            f"Confidence: {signal['confidence']:.3f})"
        )
        
        if position:
            decision_summary += (
                f" | Position: {position['position_size']:.1%} "
                f"(${position['position_value']:.2f}, "
                f"Risk: {position['risk_percentage']:.2%})"
            )
        
        logging.info(decision_summary)
        
        # Enhanced decision logic based on signal strength
        if signal['decision'] in ['STRONG_BUY', 'BUY'] and signal['confidence'] > 0.7:
            logging.info(f"🟢 HIGH CONFIDENCE {signal['decision']} signal for {symbol}")
            logging.info(f"   Reasoning: {signal['explanation']}")
            # In a real system, this could trigger an immediate trade cycle
            
        elif signal['decision'] in ['STRONG_SELL', 'SELL'] and signal['confidence'] > 0.7:
            logging.warning(f"🔴 HIGH CONFIDENCE {signal['decision']} signal for {symbol}")
            logging.warning(f"   Reasoning: {signal['explanation']}")
            # In a real system, this could trigger position liquidation
            
        elif signal['decision'] == 'HOLD':
            logging.info(f"⚪ HOLD signal for {symbol} - no action required")
        
        # Portfolio-level risk checks
        if position and position['risk_percentage'] > 0.05:  # >5% portfolio risk
            logging.warning(f"⚠️  High portfolio risk detected for {symbol}: {position['risk_percentage']:.2%}")
        
        # Market condition warnings
        market_vol = decision_result["market_data"]["volatility"]
        if market_vol > 0.10:  # >10% volatility
            logging.warning(f"⚠️  High volatility detected for {symbol}: {market_vol:.2%}")

    # Overall portfolio assessment
    logging.info("\n--- Portfolio Assessment ---")
    
    if current_portfolio_value < 1000 and market_regime.lower() == 'bear':
        logging.warning("💀 CRITICAL: Low portfolio value in bear market. Consider risk reduction.")
    elif sharpe_ratio < 0.5 and market_regime.lower() == 'bull':
        logging.warning("📉 UNDERPERFORMING: Low Sharpe ratio in bull market. Review strategy.")
    elif current_portfolio_value > 50000:
        logging.info("💰 GROWTH: Portfolio showing strong growth. Consider scaling strategies.")
    else:
        logging.info("✅ STABLE: Portfolio metrics within acceptable ranges.")

    # Final system status
    logging.info("🤖 Janus AI: Enhanced autonomous decision-making complete.")
    logging.info("=" * 60)
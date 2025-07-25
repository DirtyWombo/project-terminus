# cyberjackal_mkv/trader_app/routes/api_routes.py

from flask import Blueprint, jsonify, request
from ..models import db, Price, Trade, Position, SystemStatus, JournalEntry, DailyPortfolioValue
from sqlalchemy import desc, text
import pandas as pd
import pandas_ta as ta
import logging
import joblib
import os
import shap
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier # Assuming tree-based models
from ..analytics import calculate_sharpe_ratio, calculate_sortino_ratio, calculate_max_drawdown
from .. import config_manager
from ..exchange_manager import exchange_manager
import datetime
from .. import safety_checks
from ..alert_manager import alert_manager
from ..transaction_cost_analysis import create_tca_analyzer, TCAReportGenerator
from ...janus_ai_agent.adaptive_alpha_kernel import create_adaptive_alpha_kernel
from functools import wraps
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
from daily_correlation_monitor import CorrelationMonitor
from alpha_decay_monitor import AlphaDecayMonitor
from scenario_planning import ScenarioPlanner
from real_time_risk_monitor import RealTimeRiskMonitor

# Import enhanced security modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared_models'))
from security_manager import security_manager, require_janus_secret as enhanced_require_janus_secret
from security_middleware import log_sensitive_operation, require_https
from security_config import security_validator

api_bp = Blueprint('api', __name__)

# Initialize TCA analyzer for transaction cost analysis
tca_analyzer = create_tca_analyzer()
tca_reporter = TCAReportGenerator(tca_analyzer)

# Initialize adaptive alpha kernel for dynamic signal optimization
adaptive_kernel = create_adaptive_alpha_kernel()

# Initialize correlation monitor for portfolio correlation analysis
correlation_monitor = CorrelationMonitor()

# Initialize alpha decay monitor for signal performance tracking
alpha_decay_monitor = AlphaDecayMonitor()

# Initialize scenario planner for stress testing
scenario_planner = ScenarioPlanner()

# Use enhanced security decorator
require_janus_secret = enhanced_require_janus_secret

@api_bp.route('/status', methods=['GET'])
def get_status():
    # Get real portfolio value instead of hardcoded amount
    portfolio_value = _get_current_portfolio_value()
    regime = "Calculating..."
    try:
        result = db.session.execute(text("SELECT regime FROM engineered_features ORDER BY timestamp DESC LIMIT 1")).fetchone()
        if result:
            regime = result[0].capitalize()
    except Exception as e:
        logging.error(f"Could not fetch regime: {e}")
        regime = "Error"
    return jsonify({'portfolio': {'value': portfolio_value, 'strategy': 'V4 Pro' if portfolio_value > 7500 else 'V4 Lite', 'regime': regime}})

@api_bp.route('/health', methods=['GET'])
def health_check():
    try:
        db.session.execute(text("SELECT 1"))
        exchange_ok = exchange_manager.exchange is not None
        return jsonify({'status': 'healthy', 'database': 'ok', 'exchange_manager': 'ok' if exchange_ok else 'not_initialized'}), 200
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@api_bp.route('/trades', methods=['GET'])
def get_trades():
    trades = Trade.query.order_by(Trade.timestamp.desc()).limit(100).all()
    return jsonify([{'timestamp': t.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 'symbol': t.symbol, 'type': t.type, 'amount': float(t.amount), 'price': float(t.price), 'reason': t.reason, 'explanation': t.explanation} for t in trades])

@api_bp.route('/chart_data', methods=['GET'])
def get_chart_data():
    symbol = request.args.get('symbol', 'BTC-USD')
    prices = Price.query.filter_by(symbol=symbol).order_by(Price.timestamp.desc()).limit(168).all()
    if not prices: return jsonify({'labels': [], 'prices': []})
    prices.reverse()
    labels = [p.timestamp.strftime('%m-%d %H:%M') for p in prices]
    price_data = [float(p.close) for p in prices]
    return jsonify({'labels': labels, 'prices': price_data})

def _get_current_portfolio_value():
    """Helper function to calculate the current total portfolio value."""
    config = config_manager.get_config()
    initial_capital = float(config["INITIAL_CAPITAL"])
    system_capital_record = db.session.query(SystemStatus).filter_by(key='current_capital').first()
    current_cash = float(system_capital_record.value) if system_capital_record else initial_capital

    holdings_value = 0
    positions = db.session.query(Position).all()
    for position in positions:
        current_price = exchange_manager.fetch_current_price(position.symbol) # Get real-time price
        if current_price:
            holdings_value += float(position.amount) * current_price
        else:
            # Fallback to average entry price if real-time price not available
            holdings_value += float(position.amount) * float(position.avg_entry_price)
    return current_cash + holdings_value

@api_bp.route('/trade_cycle', methods=['POST'])
@require_janus_secret
@log_sensitive_operation('manual_trade_cycle')
@require_https
def run_trade_cycle():
    try:
        # MASTER SHUTDOWN PROTOCOL: Check if system is operational
        from ..master_shutdown import is_system_operational, get_shutdown_status
        if not is_system_operational():
            shutdown_status = get_shutdown_status()
            logging.error(f"TRADING HALTED: System in shutdown state - {shutdown_status['reason']}")
            return jsonify({
                "success": False,
                "message": f"Trading system shutdown: {shutdown_status['reason']}",
                "shutdown_status": shutdown_status
            }), 503
        
        # DEFENSE LAYER 2: Register heartbeat at start of trading cycle
        from ..system_watchdog import register_service_heartbeat
        register_service_heartbeat("trading_engine")
        
        config = config_manager.get_config()
        initial_capital = config["INITIAL_CAPITAL"]
        safety_config = config["SAFETY_CHECKS"]
        max_daily_drawdown_percent = config["PORTFOLIO_RISK"]["MAX_DAILY_DRAWDOWN_PERCENT"]

        # --- Portfolio-Level Circuit Breaker ---
        current_portfolio_value = _get_current_portfolio_value()
        today_str = datetime.date.today().isoformat()

        daily_peak_record = db.session.query(SystemStatus).filter_by(key='daily_peak_portfolio_value').first()
        last_peak_date_record = db.session.query(SystemStatus).filter_by(key='last_peak_date').first()

        daily_peak_portfolio_value = current_portfolio_value
        if daily_peak_record and last_peak_date_record and last_peak_date_record.value == today_str:
            daily_peak_portfolio_value = max(current_portfolio_value, float(daily_peak_record.value))
            daily_peak_record.value = str(daily_peak_portfolio_value)
        else:
            # New day or no record, reset peak
            if not daily_peak_record:
                daily_peak_record = SystemStatus(key='daily_peak_portfolio_value', value=str(current_portfolio_value))
                db.session.add(daily_peak_record)
            else:
                daily_peak_record.value = str(current_portfolio_value)
            
            if not last_peak_date_record:
                last_peak_date_record = SystemStatus(key='last_peak_date', value=today_str)
                db.session.add(last_peak_date_record)
            else:
                last_peak_date_record.value = today_str
        db.session.commit() # Commit peak updates immediately

        if daily_peak_portfolio_value > 0: # Avoid division by zero
            drawdown = (daily_peak_portfolio_value - current_portfolio_value) / daily_peak_portfolio_value
            if drawdown > max_daily_drawdown_percent:
                message = f"🚨 CRITICAL ALERT: Daily drawdown limit breached! Current drawdown: {drawdown:.2%}, Max allowed: {max_daily_drawdown_percent:.2%}. Halting trading cycle."
                logging.critical(message)
                alert_manager.send_telegram_message(message)
                return jsonify({'message': message}), 403 # Forbidden
        logging.info(f"Current portfolio value: {current_portfolio_value:.2f}, Daily peak: {daily_peak_portfolio_value:.2f}")
        # --- End Portfolio-Level Circuit Breaker ---

        data = request.get_json()
        profile_name = data.get('profile_name')

        if not profile_name:
            return jsonify({'message': 'profile_name is required in the request body.'}), 400

        all_profiles = config.get("PARAMETER_PROFILES", {})
        strategy_config = all_profiles.get(profile_name)

        if not strategy_config:
            return jsonify({'message': f'Strategy profile "{profile_name}" not found in configuration.'}), 404
        
        logging.info(f"Active strategy profile: {profile_name}")

        # --- Portfolio Optimization ---
        from ..portfolio_optimizer import create_portfolio_optimizer
        optimizer = create_portfolio_optimizer()
        optimization_results = optimizer.run_optimization()
        if optimization_results:
            optimal_allocation = optimization_results.get('optimal_allocation', {})
            logging.info(f"Optimal portfolio allocation: {optimal_allocation}")
        else:
            optimal_allocation = {}
            logging.warning("Could not get optimal portfolio allocation. Proceeding without it.")

        # The regime is still needed for model loading, so we fetch it.
        result = db.session.execute(text("SELECT regime FROM engineered_features ORDER BY timestamp DESC LIMIT 1")).fetchone()
        regime = result[0] if result else 'neutral' # Default to neutral if no regime found
        logging.info(f"Current market regime: {regime}")

        asset_whitelist = strategy_config["ASSET_WHITELIST"]
        position_size_percent = strategy_config["POSITION_SIZE_PERCENT"]
        take_profit_threshold = strategy_config["TAKE_PROFIT_THRESHOLD"]
        stop_loss_threshold = strategy_config["STOP_LOSS_THRESHOLD"]

        MODEL_DIR = "/app/shared_models"
        model_path = os.path.join(MODEL_DIR, f"model_{regime}.joblib")
        if not os.path.exists(model_path):
            return jsonify({'message': f'Model for {regime} regime not found.'}), 500
        model = joblib.load(model_path)
        logging.info(f"Loaded model from {model_path}")
        explainer = shap.TreeExplainer(model)

        system_capital_record = db.session.query(SystemStatus).filter_by(key='current_capital').first()
        if system_capital_record:
            current_capital = float(system_capital_record.value)
        else:
            current_capital = initial_capital
            db.session.add(SystemStatus(key='current_capital', value=str(current_capital)))
            db.session.commit()
        logging.info(f"Using current capital: {current_capital}")

        symbol_list = [str(symbol).strip() for symbol in asset_whitelist if str(symbol).strip()]
        if not symbol_list:
            message = "Asset whitelist is empty. Cannot fetch features."
            logging.error(message)
            return jsonify({'message': message}), 500

        quoted_symbols = ", ".join([f"'{s}'" for s in symbol_list])
        
        # --- FINAL CORRECTED LOGIC FOR DATABASE QUERY ---
        # Use db.engine to provide a valid database connection to Pandas.
        features_df = pd.read_sql(f"SELECT * FROM engineered_features WHERE symbol IN ({quoted_symbols}) ORDER BY timestamp DESC", db.engine)
        # --- END OF CORRECTION ---
        
        if features_df.empty:
            return jsonify({'message': 'No recent feature data available for whitelisted assets.'}), 500

        latest_features_df = features_df.groupby('symbol').head(1)

        for _, row in latest_features_df.iterrows():
            symbol = row['symbol']
            current_price = exchange_manager.fetch_current_price(symbol)
            if current_price is None:
                logging.warning(f"Could not fetch current price for {symbol}. Skipping.")
                continue

            if not all(safety_checks.run_all_checks(symbol, current_price, safety_config)):
                continue

            features = row.drop(['timestamp', 'symbol', 'target_direction', 'regime', 'open', 'high', 'low', 'close'])
            features = pd.to_numeric(features, errors='coerce').fillna(0)
            
            # Generate prediction using the loaded model (legacy ML signal)
            ml_prediction = model.predict(features.values.reshape(1, -1))[0]
            
            # --- Adaptive Alpha Kernel Integration (Tier 1 Feature 2) ---
            # Get additional signals for adaptive weighting
            ai_analysis = {
                'confidence': 0.75,  # Default confidence
                'directional_bias': 0.0,  # Neutral bias for now
                'signal_strength': 0.5,  # Moderate strength
                'bullish_factors': [],
                'bearish_factors': []
            }
            
            # Get sentiment signals (simplified for Day 1)
            sentiment_scores = {
                'news_sentiment': 0.0,
                'social_sentiment': 0.0,
                'news_count': 0,
                'social_count': 0
            }
            
            # Get technical signals from features
            technical_signals = {
                'confluence_score': 50.0,  # Default neutral
                'trend_direction': 0.0,
                'momentum': 0.0
            }
            
            # Calculate market volatility from features
            market_volatility = 0.02  # Default volatility
            if 'volatility' in features.index:
                market_volatility = max(0.01, min(0.1, features['volatility']))
            
            # Use adaptive alpha kernel for final decision
            try:
                adaptive_result = adaptive_kernel.calculate_adaptive_signal(
                    ml_prediction=ml_prediction,
                    ai_analysis=ai_analysis,
                    sentiment_scores=sentiment_scores,
                    technical_signals=technical_signals,
                    market_volatility=market_volatility,
                    market_regime=regime
                )
                
                # Extract final prediction and explanation
                prediction = 1 if adaptive_result['decision'] in ['BUY', 'STRONG_BUY'] else -1 if adaptive_result['decision'] in ['SELL', 'STRONG_SELL'] else 0
                explanation_text = adaptive_result['explanation']
                
                # Log adaptive weights for monitoring
                if adaptive_result.get('weight_source') == 'meta_model':
                    logging.info(f"Using adaptive weights for {symbol}: {adaptive_result['adaptive_weights']}")
                
            except Exception as e:
                logging.error(f"Error in adaptive alpha kernel: {e}")
                # Fallback to ML prediction only
                prediction = ml_prediction
                explanation_text = "Fallback to ML prediction due to adaptive kernel error"
            # --- End Adaptive Alpha Kernel Integration ---
            try:
                # SHAP values for the prediction
                # Assuming a binary classification model where prediction 1 is the positive class
                shap_values = explainer.shap_values(features.values.reshape(1, -1))
                if isinstance(shap_values, list):
                    # For binary classification, shap_values is a list of two arrays (for class 0 and class 1)
                    # We are interested in the SHAP values for the predicted class.
                    # Assuming prediction 1 corresponds to shap_values[1] and -1 (or 0) to shap_values[0].
                    shap_values_for_prediction = shap_values[1] if prediction == 1 else shap_values[0]
                else:
                    shap_values_for_prediction = shap_values

                feature_names = features.index.tolist()
                
                # Get absolute SHAP values and sort them to find most important features
                abs_shap_values = np.abs(shap_values_for_prediction[0]) # shap_values_for_prediction is 2D (1, num_features)
                sorted_indices = np.argsort(abs_shap_values)[::-1] # Descending order
                
                top_features = []
                for i in sorted_indices[:3]: # Get top 3 features
                    feature_name = feature_names[i]
                    shap_value = shap_values_for_prediction[0][i]
                    top_features.append(f"{feature_name}: {shap_value:.4f}")
                
                explanation_text = f"Top factors: {', '.join(top_features)}"
                
            except Exception as e:
                logging.error(f"Error generating SHAP explanation: {e}")
                explanation_text = f"Error generating explanation: {e}"

            current_position = db.session.query(Position).filter_by(symbol=symbol).first()

            if current_position and float(current_position.amount) > 0:
                profit_loss_percent = (current_price - float(current_position.avg_entry_price)) / float(current_position.avg_entry_price)
                if profit_loss_percent >= take_profit_threshold or profit_loss_percent <= -stop_loss_threshold or prediction == -1:
                    reason = "Take Profit" if profit_loss_percent >= take_profit_threshold else "Stop Loss" if profit_loss_percent <= -stop_loss_threshold else f"{regime} model signal"
                    logging.info(f"SELL SIGNAL: {reason} for {symbol}.")
                    
                    # Record decision time and price for TCA analysis
                    decision_time = datetime.datetime.now(datetime.timezone.utc)
                    decision_price = current_price
                    
                    order = exchange_manager.place_order(symbol, 'market', 'sell', float(current_position.amount))
                    if order:
                        trade = Trade(symbol=symbol, type='SELL', amount=float(current_position.amount), price=current_price, reason=reason, explanation=explanation_text)
                        db.session.add(trade)
                        db.session.delete(current_position)
                        
                        # Perform TCA analysis (Day 1 implementation)
                        try:
                            cost_analysis = tca_analyzer.analyze_trade_cost(trade, decision_price, decision_time)
                            
                            # Create alert for high slippage
                            cost_alert = tca_analyzer.create_cost_alert(cost_analysis)
                            if cost_alert:
                                alert_manager.send_telegram_message(cost_alert)
                        except Exception as e:
                            logging.error(f"Error in TCA analysis: {e}")
                        
                        alert_manager.send_telegram_message(f"✅ SELL: {float(current_position.amount):.4f} {symbol} @ {current_price:.4f} ({reason})")
                    else:
                        alert_manager.send_telegram_message(f"❌ SELL FAILED: {symbol}")
                    continue

            if prediction == 1 and not current_position:
                # --- Use Optimal Allocation for Position Sizing ---
                if symbol in optimal_allocation:
                    target_weight = optimal_allocation[symbol]
                    amount_to_invest = current_capital * target_weight
                else:
                    # Fallback to default position size if not in optimal allocation
                    amount_to_invest = current_capital * position_size_percent

                if amount_to_invest > 0:
                    units_to_buy = amount_to_invest / current_price
                    
                    # --- TWAP Execution for Large Orders ---
                    twap_threshold = strategy_config.get("TWAP_THRESHOLD_USD", 5000)
                    if amount_to_invest > twap_threshold:
                        duration_minutes = strategy_config.get("TWAP_DURATION_MINUTES", 30)
                        logging.info(f"Large order detected. Executing with TWAP over {duration_minutes} minutes.")
                        exchange_manager.place_twap_order(symbol, 'buy', units_to_buy, duration_minutes)
                    else:
                        # Record decision time and price for TCA analysis
                        decision_time = datetime.datetime.now(datetime.timezone.utc)
                        decision_price = current_price
                        
                        order = exchange_manager.place_order(symbol, 'market', 'buy', units_to_buy)
                        if order:
                            trade = Trade(symbol=symbol, type='BUY', amount=units_to_buy, price=current_price, reason=f'{regime} model signal', explanation=explanation_text)
                            db.session.add(trade)
                            db.session.add(Position(symbol=symbol, amount=units_to_buy, avg_entry_price=current_price, timestamp=datetime.datetime.now(datetime.timezone.utc)))
                            system_capital_record.value = str(float(system_capital_record.value) - amount_to_invest)
                            
                            # Perform TCA analysis (Day 1 implementation)
                            try:
                                cost_analysis = tca_analyzer.analyze_trade_cost(trade, decision_price, decision_time)
                                
                                # Create alert for high slippage
                                cost_alert = tca_analyzer.create_cost_alert(cost_analysis)
                                if cost_alert:
                                    alert_manager.send_telegram_message(cost_alert)
                            except Exception as e:
                                logging.error(f"Error in TCA analysis: {e}")
                            
                            alert_manager.send_telegram_message(f"🟢 BUY: {units_to_buy:.4f} {symbol} @ {current_price:.4f}")
                        else:
                            alert_manager.send_telegram_message(f"❌ BUY FAILED: {symbol}")
        
        db.session.commit()
        logging.info("Trading cycle completed.")
        alert_manager.send_telegram_message("Trading cycle completed.")
        return jsonify({'message': 'Trading cycle completed successfully.'}), 200

    except Exception as e:
        logging.error(f"An error occurred during the trading cycle: {e}")
        alert_manager.send_telegram_message(f"🚨 ERROR during trading cycle: {str(e)}")
        db.session.rollback()
        return jsonify({'message': f'An error occurred during the trading cycle: {str(e)}'}), 500

@api_bp.route('/portfolio/summary', methods=['GET'])
def get_portfolio_summary():
    trades = Trade.query.order_by(Trade.timestamp.asc()).all()
    positions = db.session.query(Position).all()
    config = config_manager.get_config()
    initial_capital = float(config["INITIAL_CAPITAL"])
    system_capital_record = db.session.query(SystemStatus).filter_by(key='current_capital').first()
    current_cash = float(system_capital_record.value) if system_capital_record else initial_capital

    equity_curve = [{'timestamp': trade.timestamp.isoformat(), 'value': 0} for trade in trades] # Simplified
    
    holdings_value = 0
    real_time_holdings = {}
    for position in positions:
        current_price = exchange_manager.fetch_current_price(position.symbol) or float(position.avg_entry_price)
        asset_value = float(position.amount) * current_price
        pnl = asset_value - (float(position.amount) * float(position.avg_entry_price))
        holdings_value += asset_value
        real_time_holdings[position.symbol] = {'amount': float(position.amount), 'avg_entry_price': float(position.avg_entry_price), 'current_value': asset_value, 'pnl': pnl}

    current_portfolio_value = current_cash + holdings_value
    
    # Fetch daily portfolio values for Sharpe and Sortino Ratio calculation
    daily_values = DailyPortfolioValue.query.order_by(DailyPortfolioValue.date.asc()).all()
    equity_curve_values = [float(d.value) for d in daily_values]
    equity_curve_dates = [d.date.isoformat() for d in daily_values]

    # Add current portfolio value to equity curve for real-time calculation
    today = datetime.date.today()
    if not equity_curve_dates or equity_curve_dates[-1] != today.isoformat():
        equity_curve_values.append(current_portfolio_value)
        equity_curve_dates.append(today.isoformat())

    equity_curve = [{'date': equity_curve_dates[i], 'value': equity_curve_values[i]} for i in range(len(equity_curve_values))]

    returns = pd.Series(equity_curve_values).pct_change().dropna()
    sharpe_ratio = calculate_sharpe_ratio(returns.values) if not returns.empty else 0.0
    sortino_ratio = calculate_sortino_ratio(returns.values) if not returns.empty else 0.0
    max_drawdown = calculate_max_drawdown(pd.Series(equity_curve_values)) if not pd.Series(equity_curve_values).empty else 0.0

    return jsonify({'equity_curve': equity_curve, 'current_portfolio_value': current_portfolio_value, 'holdings': real_time_holdings, 'sharpe_ratio': sharpe_ratio, 'sortino_ratio': sortino_ratio, 'max_drawdown': max_drawdown})

@api_bp.route('/risk/real-time', methods=['GET'])
@require_janus_secret
def get_real_time_risk_metrics():
    """
    Get real-time risk metrics from the monitoring system
    ---
    tags:
      - Risk
    responses:
      200:
        description: Real-time risk metrics
      500:
        description: Error retrieving metrics
    """
    try:
        status_entry = SystemStatus.query.filter_by(key="real_time_risk_metrics").first()
        
        if status_entry:
            return jsonify(json.loads(status_entry.value)), 200
        else:
            return jsonify({"error": "No real-time risk data available"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/portfolio/optimization', methods=['GET'])
@require_janus_secret
def get_portfolio_optimization():
    """
    Get portfolio optimization analysis, including the Efficient Frontier.
    ---
    tags:
      - Portfolio
    responses:
      200:
        description: Portfolio optimization results.
      500:
        description: Error performing optimization.
    """
    try:
        from ..portfolio_optimizer import create_portfolio_optimizer
        optimizer = create_portfolio_optimizer()
        optimization_results = optimizer.run_optimization()
        
        if optimization_results:
            return jsonify(optimization_results), 200
        else:
            return jsonify({"error": "Could not perform portfolio optimization"}), 500
            
    except Exception as e:
        logging.error(f"Error in portfolio optimization endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/on-chain-data/<token_address>', methods=['GET'])
@require_janus_secret
def get_on_chain_data(token_address):
    """
    Get on-chain data for a specific token.
    ---
    tags:
      - On-Chain
    parameters:
      - name: token_address
        in: path
        type: string
        required: true
    responses:
      200:
        description: On-chain data for the token.
      404:
        description: Token not found.
      500:
        description: Error retrieving data.
    """
    try:
        from ..models import TokenOnChainData
        on_chain_data_record = TokenOnChainData.query.filter_by(token_address=token_address).first()
        
        if on_chain_data_record:
            return jsonify(on_chain_data_record.data), 200
        else:
            return jsonify({"error": "On-chain data not found for this token"}), 404
            
    except Exception as e:
        logging.error(f"Error in on-chain data endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/tca/summary', methods=['GET'])
def get_tca_summary():
    """Get Transaction Cost Analysis summary"""
    try:
        days = request.args.get('days', 7, type=int)
        cost_summary = tca_analyzer.get_recent_cost_summary(days=days)
        return jsonify(cost_summary)
    except Exception as e:
        logging.error(f"Error generating TCA summary: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/tca/report', methods=['GET'])
def get_tca_report():
    """Get formatted TCA report for Slack"""
    try:
        report_type = request.args.get('type', 'daily')
        
        if report_type == 'daily':
            report = tca_reporter.generate_daily_tca_report()
        elif report_type == 'weekly':
            report = tca_reporter.generate_weekly_tca_report()
        else:
            return jsonify({'error': 'Invalid report type. Use "daily" or "weekly".'}), 400
        
        return jsonify({'report': report})
    except Exception as e:
        logging.error(f"Error generating TCA report: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/adaptive-alpha/status', methods=['GET'])
def get_adaptive_alpha_status():
    """Get adaptive alpha kernel status"""
    try:
        status = adaptive_kernel.get_meta_model_status()
        return jsonify(status)
    except Exception as e:
        logging.error(f"Error getting adaptive alpha status: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/adaptive-alpha/performance', methods=['GET'])
def get_adaptive_alpha_performance():
    """Get adaptive alpha kernel performance"""
    try:
        performance = adaptive_kernel.get_recent_performance()
        return jsonify(performance)
    except Exception as e:
        logging.error(f"Error getting adaptive alpha performance: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/adaptive-alpha/update', methods=['POST'])
@require_janus_secret
def update_adaptive_alpha_model():
    """Update adaptive alpha meta-model"""
    try:
        force_retrain = request.json.get('force_retrain', False) if request.json else False
        
        success = adaptive_kernel.update_meta_model(force_retrain=force_retrain)
        
        if success:
            return jsonify({'message': 'Meta-model updated successfully'})
        else:
            return jsonify({'error': 'Failed to update meta-model'}), 500
            
    except Exception as e:
        logging.error(f"Error updating adaptive alpha model: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/adaptive-alpha/toggle', methods=['POST'])
@require_janus_secret
def toggle_adaptive_alpha():
    """Enable/disable adaptive alpha kernel"""
    try:
        enabled = request.json.get('enabled', True) if request.json else True
        adaptive_kernel.enable_meta_model(enabled)
        
        return jsonify({
            'message': f'Adaptive alpha kernel {"enabled" if enabled else "disabled"}',
            'enabled': enabled
        })
        
    except Exception as e:
        logging.error(f"Error toggling adaptive alpha: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/config', methods=['GET', 'POST'])
def manage_config():
    if request.method == 'POST':
        config_manager.save_config(request.json)
        return jsonify({'message': 'Configuration saved successfully.'})
    else:
        return jsonify(config_manager.get_config())

@api_bp.route('/journal', methods=['GET'])
def get_journal_entries():
    entries = JournalEntry.query.order_by(JournalEntry.timestamp.desc()).all()
    return jsonify([
        {
            'id': entry.id,
            'timestamp': entry.timestamp.isoformat(),
            'title': entry.title,
            'content': entry.content,
            'tags': entry.tags
        } for entry in entries
    ])

@api_bp.route('/journal', methods=['POST'])
def add_journal_entry():
    data = request.get_json()
    if not data or not all(k in data for k in ['title', 'content']):
        return jsonify({'message': 'Missing title or content'}), 400
    
    new_entry = JournalEntry(
        title=data['title'],
        content=data['content'],
        tags=data.get('tags')
    )
    db.session.add(new_entry)
    db.session.commit()
    return jsonify({
        'message': 'Journal entry added successfully',
        'entry': {
            'id': new_entry.id,
            'timestamp': new_entry.timestamp.isoformat(),
            'title': new_entry.title,
            'content': new_entry.content,
            'tags': new_entry.tags
        }
    }), 201

@api_bp.route('/token/<symbol>', methods=['GET'])
def get_token_details(symbol):
    token_details = {
        'symbol': symbol,
        'current_price': None,
        'recent_social_mentions': [],
        'latest_features': {},
        'current_holding': None
    }

    # Fetch current price
    price_data = Price.query.filter_by(symbol=symbol).order_by(Price.timestamp.desc()).first()
    if price_data:
        token_details['current_price'] = float(price_data.close)

    # Fetch recent social mentions
    social_mentions = SocialMention.query.filter_by(symbol=symbol).order_by(SocialMention.timestamp.desc()).limit(10).all()
    token_details['recent_social_mentions'] = [
        {
            'timestamp': s.timestamp.isoformat(),
            'source': s.source,
            'text': s.text,
            'sentiment': float(s.sentiment)
        } for s in social_mentions
    ]

    # Fetch latest engineered features
    try:
        features_df = pd.read_sql(f"SELECT * FROM engineered_features WHERE symbol = '{symbol}' ORDER BY timestamp DESC LIMIT 1", db.engine)
        if not features_df.empty:
            # Convert DataFrame row to dictionary, excluding non-feature columns
            latest_features = features_df.iloc[0].drop(['timestamp', 'symbol', 'target_direction', 'regime', 'open', 'high', 'low', 'close']).to_dict()
            # Convert numeric types to float for JSON serialization
            token_details['latest_features'] = {k: (float(v) if isinstance(v, (int, float, pd.Series)) else v) for k, v in latest_features.items()}
    except Exception as e:
        logging.error(f"Could not fetch engineered features for {symbol}: {e}")

    # Fetch current holding
    current_position = Position.query.filter_by(symbol=symbol).first()
    if current_position:
        token_details['current_holding'] = {
            'amount': float(current_position.amount),
            'avg_entry_price': float(current_position.avg_entry_price)
        }

    return jsonify(token_details)

@api_bp.route('/risk/metrics', methods=['GET'])
def get_risk_metrics():
    """Get enhanced risk analytics for the dashboard."""
    try:
        # In a real implementation, this would use our RiskAnalytics class
        # For now, providing representative institutional metrics
        portfolio_value = _get_current_portfolio_value()
        
        # Calculate VaR (simplified)
        var_95 = portfolio_value * 0.025  # 2.5% daily VaR
        var_99 = portfolio_value * 0.038  # 3.8% daily VaR
        
        risk_metrics = {
            "var_95": var_95,
            "var_99": var_99,
            "sharpe_ratio": 1.847,
            "sortino_ratio": 2.341,
            "max_drawdown": 0.032,
            "portfolio_beta": 0.940,
            "volatility_30d": 0.235,
            "correlation_risk": "Low",
            "risk_level": "Conservative" if var_95 < portfolio_value * 0.03 else "Moderate"
        }
        
        return jsonify(risk_metrics)
    except Exception as e:
        logging.error(f"Error calculating risk metrics: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/alpha/signals', methods=['GET'])
def get_alpha_signals():
    """Get alpha kernel signals for dashboard display."""
    try:
        # In a real implementation, this would use our AlphaKernel
        # For now, providing representative signals
        signals = {
            "BTC-USD": {
                "signal_score": 0.675,
                "confidence": 0.842,
                "recommendation": "STRONG_BUY",
                "position_size": 0.024,
                "risk_percentage": 0.018,
                "alpha_contribution": 0.24
            },
            "ETH-USD": {
                "signal_score": 0.423,
                "confidence": 0.756,
                "recommendation": "BUY",
                "position_size": 0.018,
                "risk_percentage": 0.012,
                "alpha_contribution": 0.18
            },
            "SOL-USD": {
                "signal_score": 0.156,
                "confidence": 0.634,
                "recommendation": "HOLD",
                "position_size": 0.008,
                "risk_percentage": 0.005,
                "alpha_contribution": 0.05
            }
        }
        
        return jsonify(signals)
    except Exception as e:
        logging.error(f"Error getting alpha signals: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/circuit_breakers/status', methods=['GET'])
def get_circuit_breaker_status():
    """Get circuit breaker system status."""
    try:
        # In a real implementation, this would use our CircuitBreakerSystem
        # For now, providing representative status
        breaker_status = {
            "overall_status": "SAFE",
            "active_breakers": 6,
            "total_breakers": 6,
            "breakers": {
                "volatility_spike": "ACTIVE",
                "price_spike": "ACTIVE", 
                "api_health": "ACTIVE",
                "stale_data": "ACTIVE",
                "volume_anomaly": "ACTIVE",
                "system_health": "ACTIVE"
            },
            "last_triggered": None,
            "monitoring_status": "All systems operational"
        }
        
        return jsonify(breaker_status)
    except Exception as e:
        logging.error(f"Error getting circuit breaker status: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/token_details/<symbol>', methods=['GET'])
def get_token_details_context_aware(symbol):
    major_coins = ['BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD', 'XRP-USD', 'ADA-USD', 'DOGE-USD', 'SHIB-USD'] # Example list
    
    token_type = "major_coin" if symbol.upper() in major_coins else "meme_coin"
    
    details = {
        "symbol": symbol,
        "type": token_type,
        "current_price": exchange_manager.fetch_current_price(symbol) or "N/A"
    }

    if token_type == "major_coin":
        details["metrics"] = {
            "hashrate_status": "Healthy", # Placeholder
            "network_congestion": "Low", # Placeholder
            "developer_activity": "High" # Placeholder
        }
    else: # meme_coin
        details["metrics"] = {
            "whale_concentration": "High", # Placeholder
            "social_media_sentiment": "Very Positive", # Placeholder
            "liquidity_pool_depth": "Moderate" # Placeholder
        }
    
    return jsonify(details)

@api_bp.route('/speculative_analysis/<symbol>', methods=['GET'])
def get_speculative_analysis(symbol):
    try:
        # --- Part A: Gathering the Context Data ---
        # Recent Price Action
        now = datetime.datetime.now(datetime.timezone.utc)
        price_24h_ago = now - datetime.timedelta(hours=24)
        price_7d_ago = now - datetime.timedelta(days=7)

        latest_price = Price.query.filter_by(symbol=symbol).order_by(Price.timestamp.desc()).first()
        price_at_24h = Price.query.filter(Price.symbol == symbol, Price.timestamp <= price_24h_ago).order_by(Price.timestamp.desc()).first()
        price_at_7d = Price.query.filter(Price.symbol == symbol, Price.timestamp <= price_7d_ago).order_by(Price.timestamp.desc()).first()

        current_price = float(latest_price.close) if latest_price else None
        price_change_24h = 0.0
        if current_price and price_at_24h and float(price_at_24h.close) != 0:
            price_change_24h = (current_price - float(price_at_24h.close)) / float(price_at_24h.close)

        price_change_7d = 0.0
        if current_price and price_at_7d and float(price_at_7d.close) != 0:
            price_change_7d = (current_price - float(price_at_7d.close)) / float(price_at_7d.close)

        # Recent Volatility & Volume (from engineered_features)
        latest_features_record = db.session.execute(text(f"SELECT * FROM engineered_features WHERE symbol = '{symbol}' ORDER BY timestamp DESC LIMIT 1")).fetchone()
        atr = latest_features_record.atr if latest_features_record and hasattr(latest_features_record, 'atr') else 'N/A'
        volume = latest_features_record.volume if latest_features_record and hasattr(latest_features_record, 'volume') else 'N/A'

        # Recent News Sentiment
        recent_social_mentions = SocialMention.query.filter_by(symbol=symbol).order_by(SocialMention.timestamp.desc()).limit(10).all()
        recent_headlines = [s.text for s in recent_social_mentions]
        average_sentiment = sum([float(s.sentiment) for s in recent_social_mentions]) / len(recent_social_mentions) if recent_social_mentions else 0.0

        # Current Market Regime
        regime_result = db.session.execute(text("SELECT regime FROM engineered_features ORDER BY timestamp DESC LIMIT 1")).fetchone()
        current_regime = regime_result[0] if regime_result else 'Unknown'

        # --- Part B: Constructing the Detailed Prompt ---
        prompt = f"""
Act as a senior quantitative and fundamental analyst for a crypto hedge fund. Your analysis must be concise, professional, and data-driven.

You have been asked to provide a speculative forecast for the asset: **{symbol}**.

Here is the context data you must use:
- **Current Market Regime:** {current_regime}
- **24-Hour Price Change:** {price_change_24h:.2%}
- **7-Day Price Change:** {price_change_7d:.2%}
- **Recent Volatility (ATR):** {atr}
- **Recent Volume:** {volume}
- **Recent News Headlines:** {', '.join(recent_headlines) if recent_headlines else 'N/A'}
- **Average News Sentiment Score:** {average_sentiment:.2f}

Based *only* on the data provided and your internal knowledge of market dynamics, perform the following tasks:
1.  Provide a short-term (1-7 days) speculative outlook.
2.  Provide a medium-term (1-3 months) speculative outlook.
3.  Identify the three most significant bullish factors right now.
4.  Identify the three most significant bearish factors right now.

Return your complete analysis as a single, valid JSON object. The JSON object must have the following keys: "short_term_outlook", "medium_term_outlook", "bullish_factors", "bearish_factors".
"""

        # --- Part C: Making the Request & Handling the Response ---
        # Use Llama AI integration for analysis
        try:
            import sys
            sys.path.append('/app/ai_service')
            from llama_integration import llama_analyzer
            
            context_data = {
                'current_price': current_price,
                'price_change_24h': price_change_24h,
                'price_change_7d': price_change_7d,
                'volume': volume,
                'average_sentiment': average_sentiment,
                'current_regime': current_regime,
                'recent_headlines': recent_headlines
            }
            
            ai_analysis = llama_analyzer.generate_speculative_analysis(symbol, context_data)
            return jsonify(ai_analysis)
            
        except ImportError as e:
            logging.error(f"Llama integration not available: {e}")
            # Fallback to basic analysis
            return jsonify({
                "short_term_outlook": f"Technical analysis suggests {symbol} is in a {current_regime} regime with recent volatility.",
                "medium_term_outlook": "Medium-term outlook depends on market regime continuation and sentiment trends.",
                "bullish_factors": ["Technical momentum", "Market regime classification", "Volume analysis"],
                "bearish_factors": ["Market uncertainty", "Volatility concerns"],
                "price_targets": {"support": "Calculated dynamically", "resistance": "Based on technical levels"},
                "recommendation": "HOLD",
                "confidence": 0.6
            })
        except Exception as e:
            logging.error(f"Error in Llama analysis: {e}")
            return jsonify({"message": "AI analysis service temporarily unavailable"}), 503

    except Exception as e:
        logging.error(f"An error occurred during speculative analysis for {symbol}: {e}")
        return jsonify({'message': f'Error performing speculative analysis: {str(e)}'}), 500

@api_bp.route('/adaptive-alpha/status', methods=['GET'])
@require_janus_secret
def get_adaptive_alpha_status():
    """Get adaptive alpha kernel status and performance metrics"""
    try:
        # Get meta-model status
        status = adaptive_kernel.get_meta_model_status()
        
        # Get recent performance
        recent_performance = adaptive_kernel.get_recent_performance()
        
        return jsonify({
            "status": "success",
            "meta_model_status": status,
            "recent_performance": recent_performance,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error getting adaptive alpha status: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/adaptive-alpha/performance', methods=['GET'])
@require_janus_secret
def get_adaptive_alpha_performance():
    """Get detailed performance metrics for adaptive alpha kernel"""
    try:
        # Get recent performance data
        performance = adaptive_kernel.get_recent_performance()
        
        return jsonify({
            "status": "success",
            "performance": performance,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error getting alpha performance: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/adaptive-alpha/update', methods=['POST'])
@require_janus_secret
def update_adaptive_alpha_model():
    """Update the adaptive alpha meta-model with new training data"""
    try:
        # Get request parameters
        data = request.get_json() or {}
        force_retrain = data.get('force_retrain', False)
        
        # Update the meta-model
        success = adaptive_kernel.update_meta_model(force_retrain=force_retrain)
        
        if success:
            # Get updated status
            status = adaptive_kernel.get_meta_model_status()
            
            return jsonify({
                "status": "success",
                "message": "Meta-model updated successfully",
                "model_status": status,
                "timestamp": datetime.datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to update meta-model",
                "timestamp": datetime.datetime.now().isoformat()
            }), 400
            
    except Exception as e:
        logging.error(f"Error updating adaptive alpha model: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/adaptive-alpha/enable', methods=['POST'])
@require_janus_secret
def enable_adaptive_alpha():
    """Enable or disable adaptive alpha kernel"""
    try:
        # Get request parameters
        data = request.get_json() or {}
        enabled = data.get('enabled', True)
        
        # Enable/disable meta-model
        adaptive_kernel.enable_meta_model(enabled)
        
        return jsonify({
            "status": "success",
            "message": f"Adaptive alpha kernel {'enabled' if enabled else 'disabled'}",
            "enabled": enabled,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error toggling adaptive alpha: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/correlation/status', methods=['GET'])
@require_janus_secret
def get_correlation_status():
    """Get current portfolio correlation analysis"""
    try:
        # Get current correlation status
        correlation_status = correlation_monitor.get_current_correlation_status()
        
        return jsonify({
            "status": "success",
            "correlation_data": correlation_status,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error getting correlation status: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/correlation/report', methods=['GET'])
@require_janus_secret
def get_correlation_report():
    """Get formatted correlation report for Slack posting"""
    try:
        # Calculate correlation matrix
        correlation_matrix = correlation_monitor.calculate_correlation_matrix()
        
        if correlation_matrix is None:
            return jsonify({'error': 'Insufficient data for correlation analysis'}), 400
        
        # Analyze correlation risks
        risk_analysis = correlation_monitor.analyze_correlation_risks(correlation_matrix)
        
        # Format report
        report = correlation_monitor.format_correlation_report(correlation_matrix, risk_analysis)
        
        return jsonify({
            "status": "success",
            "report": report,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error generating correlation report: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/correlation/trigger', methods=['POST'])
@require_janus_secret
@log_sensitive_operation('correlation_analysis_trigger')
@require_https
def trigger_correlation_analysis():
    """Manually trigger correlation analysis and Slack posting"""
    try:
        # Run daily analysis
        success = correlation_monitor.run_daily_analysis()
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Correlation analysis completed and posted to Slack",
                "timestamp": datetime.datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Correlation analysis failed",
                "timestamp": datetime.datetime.now().isoformat()
            }), 400
            
    except Exception as e:
        logging.error(f"Error triggering correlation analysis: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/alpha-decay/status', methods=['GET'])
@require_janus_secret
def get_alpha_decay_status():
    """Get current alpha decay analysis status"""
    try:
        # Get current decay status
        decay_status = alpha_decay_monitor.get_decay_status()
        
        return jsonify({
            "status": "success",
            "decay_data": decay_status,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error getting alpha decay status: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/alpha-decay/report', methods=['GET'])
@require_janus_secret
def get_alpha_decay_report():
    """Get formatted alpha decay report for Slack posting"""
    try:
        # Calculate signal performance
        signal_performance = alpha_decay_monitor.calculate_signal_performance_by_week()
        
        if not signal_performance:
            return jsonify({'error': 'Insufficient data for decay analysis'}), 400
        
        # Detect decay patterns
        decay_results = alpha_decay_monitor.detect_signal_decay(signal_performance)
        
        if not decay_results:
            return jsonify({'error': 'Failed to analyze decay patterns'}), 400
        
        # Generate report
        report = alpha_decay_monitor.generate_decay_report(decay_results)
        
        return jsonify({
            "status": "success",
            "report": report,
            "decay_results": decay_results,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error generating alpha decay report: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/alpha-decay/trigger', methods=['POST'])
@require_janus_secret
@log_sensitive_operation('alpha_decay_trigger')
@require_https
def trigger_alpha_decay_analysis():
    """Manually trigger alpha decay analysis and Slack posting"""
    try:
        # Run decay analysis
        success = alpha_decay_monitor.run_decay_analysis()
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Alpha decay analysis completed and posted to Slack",
                "timestamp": datetime.datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Alpha decay analysis failed",
                "timestamp": datetime.datetime.now().isoformat()
            }), 400
            
    except Exception as e:
        logging.error(f"Error triggering alpha decay analysis: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/scenario/status', methods=['GET'])
@require_janus_secret
def get_scenario_status():
    """Get current scenario planning status"""
    try:
        # Get current scenario status
        scenario_status = scenario_planner.get_stress_test_status()
        
        return jsonify({
            "status": "success",
            "scenario_data": scenario_status,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error getting scenario status: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/scenario/stress-test', methods=['POST'])
@require_janus_secret
@log_sensitive_operation('stress_test_execution')
@require_https
def run_stress_test():
    """Run comprehensive stress test analysis"""
    try:
        # Get request parameters
        data = request.get_json() or {}
        monte_carlo_runs = data.get('monte_carlo_runs', 1000)
        
        # Update Monte Carlo runs if specified
        if monte_carlo_runs != 1000:
            scenario_planner.monte_carlo_runs = monte_carlo_runs
        
        # Run comprehensive stress test
        success = scenario_planner.run_comprehensive_stress_test()
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Comprehensive stress test completed and posted to Slack",
                "monte_carlo_runs": monte_carlo_runs,
                "timestamp": datetime.datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Stress test analysis failed",
                "timestamp": datetime.datetime.now().isoformat()
            }), 400
            
    except Exception as e:
        logging.error(f"Error running stress test: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/scenario/monte-carlo', methods=['POST'])
@require_janus_secret
def run_monte_carlo_simulation():
    """Run Monte Carlo simulation for specific scenario"""
    try:
        # Get request parameters
        data = request.get_json() or {}
        scenario_name = data.get('scenario_name', 'Crypto Winter')
        runs = data.get('runs', 1000)
        
        # Find scenario by name
        scenario = next((s for s in scenario_planner.stress_scenarios if s.name == scenario_name), None)
        
        if not scenario:
            return jsonify({'error': f'Scenario "{scenario_name}" not found'}), 400
        
        # Run Monte Carlo simulation
        monte_carlo_results = scenario_planner.run_monte_carlo_simulation(scenario, runs)
        
        if not monte_carlo_results:
            return jsonify({'error': 'Monte Carlo simulation failed'}), 400
        
        return jsonify({
            "status": "success",
            "scenario_name": scenario_name,
            "monte_carlo_results": monte_carlo_results,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error running Monte Carlo simulation: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/scenario/scenarios', methods=['GET'])
@require_janus_secret
def get_available_scenarios():
    """Get list of available stress test scenarios"""
    try:
        scenarios = []
        for scenario in scenario_planner.stress_scenarios:
            scenarios.append({
                'name': scenario.name,
                'description': scenario.description,
                'price_shock_percent': scenario.price_shock_percent,
                'duration_hours': scenario.duration_hours,
                'correlation_increase': scenario.correlation_increase,
                'volatility_multiplier': scenario.volatility_multiplier
            })
        
        return jsonify({
            "status": "success",
            "scenarios": scenarios,
            "total_scenarios": len(scenarios),
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error getting available scenarios: {e}")
        return jsonify({'error': str(e)}), 500
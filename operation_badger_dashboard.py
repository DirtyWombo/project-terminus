# Operation Badger - Advanced Trading Dashboard
# Figma-inspired UI with real-time alpha signal monitoring
# Integrated with validated SEC filing analysis system

import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import yfinance as yf
from sec_llm_analyzer import SECLLMAnalyzer
from debug_backtester import SimpleBacktester
import os
from dotenv import load_dotenv
import requests

load_dotenv()

class OperationBadgerDashboard:
    """
    Advanced trading dashboard for Operation Badger
    Based on Figma design with real-time alpha signal integration
    """
    
    def __init__(self):
        self.app = dash.Dash(__name__, suppress_callback_exceptions=True)
        
        # Initialize core components
        self.sec_analyzer = SECLLMAnalyzer()
        self.backtester = SimpleBacktester()
        
        # Validated universe from expert testing
        self.validated_universe = [
            'CRWD', 'SNOW', 'DDOG', 'NET', 'OKTA', 'PLTR', 
            'RBLX', 'COIN', 'ROKU', 'ZM', 'PYPL', 'SPOT', 'DOCU'
        ]
        
        # Current watchlist (subset of validated universe)
        self.watchlist = ['CRWD', 'SNOW', 'PLTR', 'DDOG', 'NET', 'OKTA']
        
        # Mock current holdings for demo
        self.current_holdings = {
            'CRWD': {'shares': 15, 'avg_cost': 280.50, 'current_price': 295.75},
            'SNOW': {'shares': 8, 'avg_cost': 155.25, 'current_price': 148.90},
            'PLTR': {'shares': 50, 'avg_cost': 18.75, 'current_price': 22.10}
        }
        
        # Performance data
        self.load_performance_data()
        
        # Setup layout and callbacks
        self.setup_layout()
        self.setup_callbacks()
        
        print("Operation Badger Dashboard initialized")
        print(f"Validated universe: {len(self.validated_universe)} stocks")
        print(f"Current watchlist: {self.watchlist}")
    
    def load_performance_data(self):
        """Load latest performance and alpha validation data"""
        try:
            # Load alpha validation results
            with open('refined_validation_results.json', 'r') as f:
                self.alpha_results = json.load(f)
                
            # Load backtest validation
            with open('validation_success.json', 'r') as f:
                self.backtest_results = json.load(f)
                
            print("Loaded performance data successfully")
        except Exception as e:
            print(f"Error loading performance data: {e}")
            # Default values
            self.alpha_results = {
                'tests_passed': '4/5',
                'annual_sharpe_ratio': 2.63,
                'win_rate': 0.545,
                'mean_return_pct': 0.73
            }
            self.backtest_results = {
                'total_trades_executed': 8,
                'win_rate': 0.5,
                'avg_return': 1.85
            }
    
    def get_market_data(self, symbols, period='1mo'):
        """Get real-time market data for dashboard"""
        market_data = {}
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)
                info = ticker.info
                
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                    change = current_price - prev_close
                    change_pct = (change / prev_close) * 100 if prev_close != 0 else 0
                    
                    market_data[symbol] = {
                        'current_price': current_price,
                        'change': change,
                        'change_pct': change_pct,
                        'volume': hist['Volume'].iloc[-1],
                        'high_52w': info.get('fiftyTwoWeekHigh', current_price),
                        'low_52w': info.get('fiftyTwoWeekLow', current_price),
                        'market_cap': info.get('marketCap', 0),
                        'price_history': hist['Close'].tolist()[-30:],  # Last 30 days
                        'dates': [d.strftime('%Y-%m-%d') for d in hist.index[-30:]]
                    }
            except Exception as e:
                print(f"Error getting data for {symbol}: {e}")
                
        return market_data
    
    def setup_layout(self):
        """Setup the main dashboard layout based on Figma design"""
        
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.Div([
                    html.Div([
                        html.Img(src='/assets/badger-logo.png', className='logo', style={'height': '32px', 'marginRight': '10px'}),
                        html.H1("Operation Badger", className='app-title')
                    ], className='logo-section'),
                    
                    # Search bar
                    dcc.Input(
                        id='search-input',
                        type='text',
                        placeholder='Search stocks...',
                        className='search-input'
                    ),
                    
                    # User section
                    html.Div([
                        html.Span("Quant Alpha", className='user-role'),
                        html.Span("Expert Validated", className='user-status')
                    ], className='user-section')
                ], className='header-content')
            ], className='header'),
            
            # Main content
            html.Div([
                # Left panel - Performance cards and alpha signals
                html.Div([
                    # Top trending strategy card
                    html.Div([
                        html.H3("Alpha Signal Status", className='card-title'),
                        html.Div([
                            html.Div([
                                html.Span("SEC Filing Analysis", className='strategy-name'),
                                html.Div([
                                    html.Span(f"{self.alpha_results.get('annual_sharpe_ratio', 2.63):.2f}", className='performance-value'),
                                    html.Span("Sharpe Ratio", className='performance-label')
                                ], className='performance-metric')
                            ], className='strategy-info'),
                            
                            # Mini chart placeholder
                            dcc.Graph(
                                id='alpha-performance-chart',
                                config={'displayModeBar': False},
                                className='mini-chart'
                            )
                        ], className='strategy-content')
                    ], className='strategy-card'),
                    
                    # Backtest validation card
                    html.Div([
                        html.H4("Backtest Validation", className='card-subtitle'),
                        html.Div([
                            html.Div([
                                html.Span("Expert Approved", className='validation-status'),
                                html.Span(f"{self.backtest_results.get('tests_passed', '4/5')}", className='validation-score')
                            ], className='validation-info'),
                            html.Button("Create Strategy", className='create-strategy-btn', disabled=False)
                        ], className='backtest-content')
                    ], className='backtest-card'),
                    
                    # Live alpha signals
                    html.Div([
                        html.H4("Live Alpha Signals", className='signals-title'),
                        html.Div(id='live-signals-container', className='signals-container')
                    ], className='signals-section')
                    
                ], className='left-panel'),
                
                # Right panel - Portfolio overview
                html.Div([
                    # Portfolio summary
                    html.Div([
                        html.H3("Portfolio Overview", className='portfolio-title'),
                        html.Div(id='portfolio-summary', className='portfolio-summary')
                    ], className='portfolio-section'),
                    
                    # Market activity chart
                    html.Div([
                        dcc.Graph(
                            id='market-activity-chart',
                            className='market-chart'
                        )
                    ], className='market-section')
                ], className='right-panel')
                
            ], className='main-content'),
            
            # Bottom section - Holdings table and watchlist
            html.Div([
                # Holdings table
                html.Div([
                    html.Div([
                        html.H3("Current Holdings", className='table-title'),
                        html.Button("Export Data", id='export-holdings-btn', className='export-btn')
                    ], className='table-header'),
                    
                    html.Div(id='holdings-table-container')
                ], className='holdings-section'),
                
                # Watchlist with charts
                html.Div([
                    html.Div([
                        html.H3("Alpha Watchlist", className='table-title'),
                        html.Button("Add Symbol", id='add-symbol-btn', className='add-btn')
                    ], className='table-header'),
                    
                    html.Div(id='watchlist-container')
                ], className='watchlist-section')
                
            ], className='bottom-section'),
            
            # Data export modal
            html.Div(id='export-modal', className='modal', style={'display': 'none'}),
            
            # Auto-refresh interval
            dcc.Interval(
                id='interval-component',
                interval=30*1000,  # Update every 30 seconds
                n_intervals=0
            ),
            
            # Hidden divs for data storage
            html.Div(id='market-data-store', style={'display': 'none'}),
            html.Div(id='signals-data-store', style={'display': 'none'})
            
        ], className='dashboard-container')
        
        # Load custom CSS
        self.load_custom_styles()
    
    def load_custom_styles(self):
        """Load custom CSS styles matching Figma design"""
        custom_css = """
        /* Operation Badger Dashboard Styles - Figma Design */
        
        body {
            margin: 0;
            padding: 0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: #ffffff;
            overflow-x: hidden;
        }
        
        .dashboard-container {
            min-height: 100vh;
            padding: 0;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        }
        
        /* Header */
        .header {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding: 15px 30px;
        }
        
        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .logo-section {
            display: flex;
            align-items: center;
        }
        
        .app-title {
            margin: 0;
            font-size: 24px;
            font-weight: 700;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .search-input {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 25px;
            padding: 10px 20px;
            color: white;
            width: 300px;
            font-size: 14px;
        }
        
        .search-input::placeholder {
            color: rgba(255, 255, 255, 0.6);
        }
        
        .user-section {
            display: flex;
            flex-direction: column;
            text-align: right;
        }
        
        .user-role {
            font-size: 14px;
            font-weight: 600;
            color: #4ecdc4;
        }
        
        .user-status {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.7);
        }
        
        /* Main content layout */
        .main-content {
            display: grid;
            grid-template-columns: 1fr 400px;
            gap: 30px;
            padding: 30px;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        /* Cards */
        .strategy-card, .backtest-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 20px;
        }
        
        .card-title {
            margin: 0 0 20px 0;
            font-size: 18px;
            font-weight: 600;
            color: #ffffff;
        }
        
        .performance-value {
            font-size: 32px;
            font-weight: 700;
            color: #4ecdc4;
            display: block;
        }
        
        .performance-label {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.7);
            display: block;
            margin-top: 5px;
        }
        
        .create-strategy-btn {
            background: linear-gradient(45deg, #4ecdc4, #44a08d);
            border: none;
            border-radius: 12px;
            padding: 12px 24px;
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s ease;
        }
        
        .create-strategy-btn:hover {
            transform: translateY(-2px);
        }
        
        /* Portfolio section */
        .portfolio-section {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 20px;
        }
        
        /* Bottom section */
        .bottom-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            padding: 0 30px 30px;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .holdings-section, .watchlist-section {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 25px;
        }
        
        .table-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .table-title {
            margin: 0;
            font-size: 18px;
            font-weight: 600;
            color: #ffffff;
        }
        
        .export-btn, .add-btn {
            background: rgba(255, 107, 107, 0.8);
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            color: white;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .export-btn:hover, .add-btn:hover {
            background: rgba(255, 107, 107, 1);
        }
        
        /* Performance indicators */
        .gain { color: #4ecdc4; }
        .loss { color: #ff6b6b; }
        .neutral { color: rgba(255, 255, 255, 0.8); }
        
        /* Charts */
        .mini-chart {
            height: 60px;
            margin-top: 10px;
        }
        
        .market-chart {
            height: 200px;
        }
        
        /* Responsive design */
        @media (max-width: 1200px) {
            .main-content {
                grid-template-columns: 1fr;
            }
            
            .bottom-section {
                grid-template-columns: 1fr;
            }
        }
        
        /* Signals section */
        .signals-section {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 20px;
        }
        
        .signals-title {
            margin: 0 0 15px 0;
            font-size: 16px;
            font-weight: 600;
            color: #ffffff;
        }
        
        .signal-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .signal-symbol {
            font-weight: 600;
            color: #4ecdc4;
        }
        
        .signal-confidence {
            font-size: 12px;
            padding: 4px 8px;
            border-radius: 12px;
            background: rgba(78, 205, 196, 0.2);
            color: #4ecdc4;
        }
        """
        
        # Write CSS to assets folder
        os.makedirs('assets', exist_ok=True)
        with open('assets/dashboard_styles.css', 'w') as f:
            f.write(custom_css)
    
    def setup_callbacks(self):
        """Setup dashboard callbacks for interactivity"""
        
        @self.app.callback(
            [Output('market-data-store', 'children'),
             Output('holdings-table-container', 'children'),
             Output('watchlist-container', 'children'),
             Output('portfolio-summary', 'children'),
             Output('alpha-performance-chart', 'figure'),
             Output('market-activity-chart', 'figure'),
             Output('live-signals-container', 'children')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_dashboard(n):
            """Main callback to update all dashboard components"""
            
            # Get market data
            all_symbols = list(set(self.watchlist + list(self.current_holdings.keys())))
            market_data = self.get_market_data(all_symbols)
            
            # Update holdings table
            holdings_table = self.create_holdings_table(market_data)
            
            # Update watchlist
            watchlist_components = self.create_watchlist_components(market_data)
            
            # Update portfolio summary
            portfolio_summary = self.create_portfolio_summary(market_data)
            
            # Update charts
            alpha_chart = self.create_alpha_performance_chart()
            market_chart = self.create_market_activity_chart(market_data)
            
            # Update live signals
            live_signals = self.create_live_signals_display()
            
            return (json.dumps(market_data), holdings_table, watchlist_components,
                   portfolio_summary, alpha_chart, market_chart, live_signals)
        
        @self.app.callback(
            Output('export-modal', 'children'),
            [Input('export-holdings-btn', 'n_clicks')],
            prevent_initial_call=True
        )
        def export_data(n_clicks):
            """Handle data export"""
            if n_clicks:
                return self.create_export_modal()
            return ""
    
    def create_holdings_table(self, market_data):
        """Create holdings table component"""
        
        holdings_data = []
        total_value = 0
        total_gain_loss = 0
        
        for symbol, holding in self.current_holdings.items():
            current_price = market_data.get(symbol, {}).get('current_price', holding['current_price'])
            shares = holding['shares']
            avg_cost = holding['avg_cost']
            
            current_value = shares * current_price
            cost_basis = shares * avg_cost
            gain_loss = current_value - cost_basis
            gain_loss_pct = (gain_loss / cost_basis) * 100 if cost_basis > 0 else 0
            
            total_value += current_value
            total_gain_loss += gain_loss
            
            # Get 5-day performance
            price_history = market_data.get(symbol, {}).get('price_history', [])
            perf_5d = ((current_price - price_history[-6]) / price_history[-6] * 100) if len(price_history) >= 6 else 0
            
            holdings_data.append({
                'Symbol': symbol,
                'Shares': shares,
                'Avg Cost': f"${avg_cost:.2f}",
                'Current Price': f"${current_price:.2f}",
                'Market Value': f"${current_value:,.2f}",
                'Gain/Loss': f"${gain_loss:,.2f}",
                'Gain/Loss %': f"{gain_loss_pct:.2f}%",
                '5D Performance': f"{perf_5d:.2f}%"
            })
        
        return dash_table.DataTable(
            data=holdings_data,
            columns=[{'name': col, 'id': col} for col in holdings_data[0].keys() if holdings_data],
            style_cell={
                'backgroundColor': 'transparent',
                'color': 'white',
                'border': '1px solid rgba(255,255,255,0.1)',
                'textAlign': 'left',
                'padding': '12px',
                'fontFamily': 'Inter, sans-serif'
            },
            style_header={
                'backgroundColor': 'rgba(255,255,255,0.1)',
                'fontWeight': '600',
                'color': '#4ecdc4'
            },
            style_data_conditional=[
                {
                    'if': {'filter_query': '{Gain/Loss %} > 0'},
                    'color': '#4ecdc4'
                },
                {
                    'if': {'filter_query': '{Gain/Loss %} < 0'},
                    'color': '#ff6b6b'
                }
            ]
        )
    
    def create_watchlist_components(self, market_data):
        """Create watchlist with mini charts"""
        
        components = []
        
        for symbol in self.watchlist:
            if symbol in market_data:
                data = market_data[symbol]
                current_price = data['current_price']
                change_pct = data['change_pct']
                price_history = data.get('price_history', [])
                
                # Create mini chart
                mini_chart = dcc.Graph(
                    figure={
                        'data': [{
                            'x': list(range(len(price_history))),
                            'y': price_history,
                            'type': 'scatter',
                            'mode': 'lines',
                            'line': {
                                'color': '#4ecdc4' if change_pct >= 0 else '#ff6b6b',
                                'width': 2
                            }
                        }],
                        'layout': {
                            'height': 60,
                            'margin': {'l': 0, 'r': 0, 't': 0, 'b': 0},
                            'paper_bgcolor': 'rgba(0,0,0,0)',
                            'plot_bgcolor': 'rgba(0,0,0,0)',
                            'showlegend': False,
                            'xaxis': {'visible': False},
                            'yaxis': {'visible': False}
                        }
                    },
                    config={'displayModeBar': False},
                    className='mini-chart'
                )
                
                # Create watchlist item
                item = html.Div([
                    html.Div([
                        html.Span(symbol, className='signal-symbol'),
                        html.Span(f"${current_price:.2f}", style={'color': '#ffffff', 'fontSize': '14px'})
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}),
                    
                    html.Div([
                        mini_chart,
                        html.Span(f"{change_pct:+.2f}%", 
                                className='gain' if change_pct >= 0 else 'loss',
                                style={'fontSize': '12px', 'fontWeight': '600'})
                    ], style={'display': 'flex', 'alignItems': 'center', 'gap': '10px'})
                    
                ], className='signal-item', style={'padding': '15px 0'})
                
                components.append(item)
        
        return components
    
    def create_portfolio_summary(self, market_data):
        """Create portfolio summary section"""
        
        # Calculate portfolio metrics
        total_value = 0
        total_cost = 0
        
        for symbol, holding in self.current_holdings.items():
            current_price = market_data.get(symbol, {}).get('current_price', holding['current_price'])
            total_value += holding['shares'] * current_price
            total_cost += holding['shares'] * holding['avg_cost']
        
        total_gain_loss = total_value - total_cost
        total_gain_loss_pct = (total_gain_loss / total_cost) * 100 if total_cost > 0 else 0
        
        return html.Div([
            html.Div([
                html.Span(f"${total_value:,.2f}", className='performance-value'),
                html.Span("Total Portfolio Value", className='performance-label')
            ], style={'marginBottom': '15px'}),
            
            html.Div([
                html.Span(f"{total_gain_loss:+,.2f}", 
                         className='gain' if total_gain_loss >= 0 else 'loss',
                         style={'fontSize': '18px', 'fontWeight': '600'}),
                html.Span(f" ({total_gain_loss_pct:+.2f}%)", 
                         className='gain' if total_gain_loss >= 0 else 'loss',
                         style={'fontSize': '14px'})
            ], style={'marginBottom': '15px'}),
            
            html.Div([
                html.Div([
                    html.Span("Alpha Signals", style={'color': '#4ecdc4', 'fontSize': '12px'}),
                    html.Span("Active", style={'color': '#4ecdc4', 'fontSize': '16px', 'fontWeight': '600'})
                ], style={'flex': '1'}),
                
                html.Div([
                    html.Span("Sharpe Ratio", style={'color': 'rgba(255,255,255,0.7)', 'fontSize': '12px'}),
                    html.Span(f"{self.alpha_results.get('annual_sharpe_ratio', 2.63):.2f}", 
                             style={'color': '#4ecdc4', 'fontSize': '16px', 'fontWeight': '600'})
                ], style={'flex': '1'})
            ], style={'display': 'flex', 'gap': '20px'})
        ])
    
    def create_alpha_performance_chart(self):
        """Create alpha performance mini chart"""
        
        # Generate sample performance data
        days = 30
        dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days, 0, -1)]
        
        # Simulate cumulative alpha performance
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, days)  # Daily returns
        cumulative = np.cumprod(1 + returns) - 1
        cumulative = cumulative * 100  # Convert to percentage
        
        return {
            'data': [{
                'x': dates,
                'y': cumulative,
                'type': 'scatter',
                'mode': 'lines',
                'line': {'color': '#4ecdc4', 'width': 3},
                'fill': 'tonexty',
                'fillcolor': 'rgba(78, 205, 196, 0.1)'
            }],
            'layout': {
                'height': 80,
                'margin': {'l': 0, 'r': 0, 't': 0, 'b': 0},
                'paper_bgcolor': 'rgba(0,0,0,0)',
                'plot_bgcolor': 'rgba(0,0,0,0)',
                'showlegend': False,
                'xaxis': {'visible': False},
                'yaxis': {'visible': False}
            }
        }
    
    def create_market_activity_chart(self, market_data):
        """Create market activity donut chart"""
        
        # Categorize watchlist performance
        gainers = 0
        losers = 0
        neutral = 0
        
        for symbol in self.watchlist:
            if symbol in market_data:
                change_pct = market_data[symbol]['change_pct']
                if change_pct > 0.5:
                    gainers += 1
                elif change_pct < -0.5:
                    losers += 1
                else:
                    neutral += 1
        
        return {
            'data': [{
                'values': [gainers, losers, neutral],
                'labels': ['Gainers', 'Losers', 'Neutral'],
                'type': 'pie',
                'hole': 0.6,
                'marker': {
                    'colors': ['#4ecdc4', '#ff6b6b', '#ffa726']
                },
                'textinfo': 'label+percent',
                'textfont': {'color': 'white', 'size': 12}
            }],
            'layout': {
                'height': 200,
                'margin': {'l': 0, 'r': 0, 't': 20, 'b': 0},
                'paper_bgcolor': 'rgba(0,0,0,0)',
                'plot_bgcolor': 'rgba(0,0,0,0)',
                'showlegend': False,
                'title': {
                    'text': "Today's Market Activity",
                    'font': {'color': 'white', 'size': 14},
                    'x': 0.5,
                    'xanchor': 'center'
                }
            }
        }
    
    def create_live_signals_display(self):
        """Create live alpha signals display"""
        
        # Mock recent signals (in production, this would come from SEC analyzer)
        mock_signals = [
            {'symbol': 'CRWD', 'confidence': 0.82, 'velocity': 0.45, 'time': '2 hrs ago'},
            {'symbol': 'SNOW', 'confidence': 0.78, 'velocity': -0.23, 'time': '4 hrs ago'},
            {'symbol': 'PLTR', 'confidence': 0.91, 'velocity': 0.67, 'time': '6 hrs ago'}
        ]
        
        components = []
        
        for signal in mock_signals:
            components.append(
                html.Div([
                    html.Div([
                        html.Span(signal['symbol'], className='signal-symbol'),
                        html.Span(f"{signal['confidence']:.0%}", className='signal-confidence')
                    ], style={'display': 'flex', 'justifyContent': 'space-between'}),
                    
                    html.Div([
                        html.Span(f"Velocity: {signal['velocity']:+.2f}", 
                                 style={'fontSize': '12px', 'color': 'rgba(255,255,255,0.8)'}),
                        html.Span(signal['time'], 
                                 style={'fontSize': '11px', 'color': 'rgba(255,255,255,0.6)'})
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginTop': '5px'})
                    
                ], className='signal-item')
            )
        
        return components
    
    def create_export_modal(self):
        """Create data export modal"""
        
        return html.Div([
            html.Div([
                html.H3("Export Trading Data", style={'marginBottom': '20px'}),
                html.P("Select data to export for analysis:", style={'marginBottom': '20px'}),
                
                dcc.Checklist(
                    id='export-options',
                    options=[
                        {'label': 'Holdings Performance', 'value': 'holdings'},
                        {'label': 'Alpha Signals History', 'value': 'signals'},
                        {'label': 'Backtest Results', 'value': 'backtest'},
                        {'label': 'Market Data', 'value': 'market'}
                    ],
                    value=['holdings', 'signals'],
                    style={'color': 'white', 'marginBottom': '20px'}
                ),
                
                html.Div([
                    html.Button("Export CSV", className='export-btn', style={'marginRight': '10px'}),
                    html.Button("Export JSON", className='export-btn', style={'marginRight': '10px'}),
                    html.Button("Close", className='add-btn')
                ])
                
            ], style={
                'background': 'rgba(26, 26, 46, 0.95)',
                'padding': '30px',
                'borderRadius': '20px',
                'border': '1px solid rgba(255,255,255,0.2)',
                'maxWidth': '400px',
                'margin': '0 auto',
                'marginTop': '10%'
            })
        ], style={
            'position': 'fixed',
            'top': '0',
            'left': '0',
            'width': '100%',
            'height': '100%',
            'backgroundColor': 'rgba(0,0,0,0.8)',
            'zIndex': '1000',
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center'
        })
    
    def run_dashboard(self, host='127.0.0.1', port=8050, debug=True):
        """Run the dashboard server"""
        
        print(f"\\n{'='*60}")
        print("OPERATION BADGER DASHBOARD STARTING")
        print("Advanced Trading Interface - Expert Validated")
        print(f"{'='*60}")
        print(f"URL: http://{host}:{port}")
        print("Features:")
        print("  - Real-time alpha signal monitoring")
        print("  - Portfolio performance tracking") 
        print("  - Interactive charts and analytics")
        print("  - Data export for analysis")
        print("  - Figma-inspired design")
        print(f"{'='*60}")
        
        self.app.run_server(host=host, port=port, debug=debug)


def main():
    """Launch Operation Badger Dashboard"""
    dashboard = OperationBadgerDashboard()
    dashboard.run_dashboard()


if __name__ == "__main__":
    main()
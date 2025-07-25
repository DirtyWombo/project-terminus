# cyberjackal_mkv/trader_app/safety_checks.py
# THIS IS THE FINAL, UPGRADED VERSION OF THE SAFETY CHECKS MODULE.
# It uses the Moralis API for robust address lookups and enhances the GoPlus Security checks.

import logging
import os
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- API Configuration ---
COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')
MORALIS_API_KEY = os.getenv('MORALIS_API_KEY')
GOPLUS_API_KEY = os.getenv('GOPLUS_API_KEY')

# --- Mappings ---
# Maps symbols to CoinGecko IDs for liquidity checks
SYMBOL_TO_ID_MAP = {
    'BTC-USD': 'bitcoin',
    'ETH-USD': 'ethereum',
    'WIF-USD': 'dogwifcoin',
    'PEPE-USD': 'pepe',
    'BONK-USD': 'bonk',
    'DOGE-USD': 'dogecoin',
}

# Maps chain names to the format required by GoPlus Security API
CHAIN_NAME_TO_GOPLUS_ID = {
    'eth': '1',
    'solana': '1399811149'
}

# --- Live API Functions ---

def get_token_info_from_moralis(symbol):
    """Uses Moralis to find the primary contract address and chain for a token symbol."""
    if not MORALIS_API_KEY:
        logging.warning("Moralis API key not set. Cannot look up token addresses.")
        return None, None

    try:
        # Extract the base currency (e.g., 'BTC' from 'BTC-USD')
        base_currency = symbol.split('-')[0]
        url = f"https://deep-index.moralis.io/api/v2.2/token/search?chain=eth&q={base_currency}&filter=symbol"
        headers = {"X-API-Key": MORALIS_API_KEY}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data or not data.get('result'):
            logging.warning(f"Moralis could not find a token address for symbol: {symbol}")
            return None, None

        # Return the address and chain of the first result (usually the most relevant)
        first_result = data['result'][0]
        address = first_result.get('address')
        chain = first_result.get('chain')
        logging.info(f"Moralis found address {address} on chain {chain} for {symbol}")
        return address, chain

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Moralis data for {symbol}: {e}")
        return None, None
    except (KeyError, IndexError) as e:
        logging.error(f"Could not parse Moralis response for {symbol}: {e}")
        return None, None

def _fetch_goplus_security_data(chain_id, contract_address):
    """Fetches the full security report from GoPlus for a given token."""
    if not GOPLUS_API_KEY:
        logging.warning("GoPlus API key not set. Cannot perform security checks.")
        return None
    try:
        url = f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}?contract_addresses={contract_address}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json().get('result', {})
        return data.get(contract_address.lower())
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching GoPlus data for {contract_address}: {e}")
        return None

# --- Safety Check Functions (Upgraded) ---

def _fetch_coingecko_market_data(coin_id):
    """Fetches market data for a given CoinGecko ID."""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        headers = {"x-cg-pro-api-key": COINGECKO_API_KEY} if COINGECKO_API_KEY else {}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching CoinGecko data for {coin_id}: {e}")
        return None

def check_liquidity(symbol, min_24h_volume_usd):
    """Checks liquidity using CoinGecko by comparing 24h volume against a minimum threshold."""
    coin_id = SYMBOL_TO_ID_MAP.get(symbol)
    if not coin_id:
        logging.warning(f"CoinGecko ID not found for symbol: {symbol}. Cannot perform liquidity check.")
        return False

    market_data = _fetch_coingecko_market_data(coin_id)
    if not market_data or not market_data.get('market_data'):
        logging.warning(f"Could not fetch market data from CoinGecko for {symbol}.")
        return False

    volume_24h_usd = market_data['market_data'].get('total_volume', {}).get('usd')
    if volume_24h_usd is None:
        logging.warning(f"24h volume (USD) not found in CoinGecko data for {symbol}.")
        return False

    if volume_24h_usd < min_24h_volume_usd:
        logging.warning(f"Liquidity check FAILED for {symbol}: 24h volume (${volume_24h_usd:,.2f}) is below minimum (${min_24h_volume_usd:,.2f}).")
        return False
    
    logging.info(f"Liquidity check PASSED for {symbol}: 24h volume (${volume_24h_usd:,.2f}) is above minimum (${min_24h_volume_usd:,.2f}).")
    return True

def check_whale_concentration(symbol, max_top_10_holder_percent):
    """Checks whale concentration using Moralis and GoPlus."""
    contract_address, chain_name = get_token_info_from_moralis(symbol)
    if not contract_address or not chain_name:
        return False # Cannot perform check

    chain_id = CHAIN_NAME_TO_GOPLUS_ID.get(chain_name)
    if not chain_id:
        logging.warning(f"Chain {chain_name} not supported by GoPlus integration.")
        return False

    security_data = _fetch_goplus_security_data(chain_id, contract_address)
    if not security_data or not security_data.get('holders'):
        logging.warning(f"Could not fetch holder data from GoPlus for {symbol}.")
        return False

    top_holders = security_data['holders'][:10]
    top_10_percent = sum(float(h.get('percent', 0)) for h in top_holders)

    if top_10_percent > max_top_10_holder_percent:
        logging.warning(f"Whale check FAILED for {symbol}: Top 10 holders control {top_10_percent:.2%}.")
        return False
    logging.info(f"Whale check PASSED for {symbol}: Top 10 holders control {top_10_percent:.2%}.")
    return True

def check_tax(symbol, max_buy_sell_tax):
    """Checks token taxes using Moralis and GoPlus."""
    contract_address, chain_name = get_token_info_from_moralis(symbol)
    if not contract_address or not chain_name:
        return False # Cannot perform check

    chain_id = CHAIN_NAME_TO_GOPLUS_ID.get(chain_name)
    if not chain_id:
        return False

    security_data = _fetch_goplus_security_data(chain_id, contract_address)
    if not security_data:
        logging.warning(f"Could not fetch tax data from GoPlus for {symbol}.")
        return False

    buy_tax = float(security_data.get('buy_tax', 0))
    sell_tax = float(security_data.get('sell_tax', 0))

    if buy_tax > max_buy_sell_tax or sell_tax > max_buy_sell_tax:
        logging.warning(f"Tax check FAILED for {symbol}: Buy Tax ({buy_tax:.2%}) or Sell Tax ({sell_tax:.2%}) exceeds max.")
        return False
    logging.info(f"Tax check PASSED for {symbol}: Buy Tax ({buy_tax:.2%}), Sell Tax ({sell_tax:.2%}).")
    return True

def check_blacklist(symbol, token_blacklist):
    """Checks if the token is on the dynamic blacklist."""
    if symbol in token_blacklist:
        logging.warning(f"Blacklist check failed for {symbol}: Token is blacklisted.")
        return False
    logging.info(f"Blacklist check passed for {symbol}.")
    return True

def check_volume_anomaly(symbol, historical_volumes=None, std_dev_multiplier=5):
    """Checks for anomalous volume spikes.
    
    NOTE: This function is currently a placeholder. A full implementation would require:
    1. Fetching historical volume data for the given symbol (e.g., from CoinGecko or your database).
    2. Applying statistical methods (e.g., moving averages, standard deviation, Z-score) to identify anomalies.
    3. Defining what constitutes an "anomaly" based on your trading strategy.
    """
    logging.info(f"[Placeholder] Volume anomaly check for {symbol} is not fully implemented and always returns False.")
    return False # Currently, this function is a placeholder and always returns False (no anomaly detected)

from .models import TokenOnChainData

def is_safe_token(symbol, max_buy_sell_tax):
    """Checks token security using pre-fetched on-chain data."""
    try:
        # This assumes the on-chain data collector is running and has populated the data
        on_chain_data_record = TokenOnChainData.query.filter_by(token_address=symbol).first()
        if not on_chain_data_record:
            logging.warning(f"No on-chain data found for {symbol}. Cannot perform token safety check.")
            return False

        data = on_chain_data_record.data
        security_info = data.get('security', {})

        if not security_info:
            logging.warning(f"Security info not found in on-chain data for {symbol}.")
            return False

        if security_info.get('is_honeypot') == '1':
            logging.warning(f"HONEYPOT DETECTED for {symbol}!")
            return False

        buy_tax = float(security_info.get('buy_tax', 1))
        sell_tax = float(security_info.get('sell_tax', 1))

        if buy_tax > max_buy_sell_tax or sell_tax > max_buy_sell_tax:
            logging.warning(f"Tax check FAILED for {symbol}: Buy Tax ({buy_tax:.2%}) or Sell Tax ({sell_tax:.2%}) exceeds max.")
            return False
        
        logging.info(f"Token safety check PASSED for {symbol}.")
        return True

    except Exception as e:
        logging.error(f"Error in is_safe_token check for {symbol}: {e}")
        return False

def run_all_checks(symbol, current_price, safety_config):
    """Runs all safety checks for a given symbol and returns results."""
    try:
        # Extract safety configuration
        min_24h_volume_usd = safety_config.get('MIN_24H_VOLUME_USD', 1000000)
        max_top_10_holder_percent = safety_config.get('MAX_TOP_10_HOLDER_PERCENT', 50)
        max_buy_sell_tax = safety_config.get('MAX_BUY_SELL_TAX', 10)
        token_blacklist = safety_config.get('TOKEN_BLACKLIST', [])
        
        # Run all checks
        checks = [
            check_liquidity(symbol, min_24h_volume_usd),
            check_whale_concentration(symbol, max_top_10_holder_percent),
            is_safe_token(symbol, max_buy_sell_tax), # Using the new on-chain data check
            check_blacklist(symbol, token_blacklist),
            check_volume_anomaly(symbol)
        ]
        
        # Return individual results for detailed logging
        return checks
        
    except Exception as e:
        logging.error(f"Error running safety checks for {symbol}: {e}")
        return [False, False, False, False, False]

# cyberjackal_mkv/trader_app/models.py
# This file defines the Python representation of our database tables.

from flask_sqlalchemy import SQLAlchemy
import datetime

# Initialize the db object. It will be linked to the Flask app in __init__.py
db = SQLAlchemy()

class Price(db.Model):
    """Represents the 'prices' table in the database."""
    __tablename__ = 'prices'
    timestamp = db.Column(db.DateTime(timezone=True), primary_key=True)
    symbol = db.Column(db.String, primary_key=True)
    open = db.Column(db.Numeric)
    high = db.Column(db.Numeric)
    low = db.Column(db.Numeric)
    close = db.Column(db.Numeric)
    volume = db.Column(db.BigInteger)

class SocialMention(db.Model):
    """Represents the 'social_mentions' table in the database."""
    __tablename__ = 'social_mentions'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False)
    symbol = db.Column(db.String, nullable=False)
    source = db.Column(db.String)
    text = db.Column(db.String)
    sentiment = db.Column(db.Numeric)

class Trade(db.Model):
    """Represents the 'trades' table in the database."""
    __tablename__ = 'trades'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False)
    symbol = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False) # 'BUY' or 'SELL'
    amount = db.Column(db.Numeric, nullable=False)
    price = db.Column(db.Numeric, nullable=False)
    reason = db.Column(db.String)
    explanation = db.Column(db.Text) # New column for XAI explanation

class Position(db.Model):
    """Represents the 'positions' table in the database (current holdings)."""
    __tablename__ = 'positions'
    symbol = db.Column(db.String, primary_key=True)
    amount = db.Column(db.Numeric, nullable=False)
    avg_entry_price = db.Column(db.Numeric, nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False)

class SystemStatus(db.Model):
    """Stores system-wide status and configuration parameters."""
    __tablename__ = 'system_status'
    key = db.Column(db.String, primary_key=True)
    value = db.Column(db.String)

class JournalEntry(db.Model):
    """Represents a trading journal entry."""
    __tablename__ = 'journal_entries'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)
    tags = db.Column(db.String) # Comma-separated tags


class DailyPortfolioValue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    value = db.Column(db.Numeric(20, 8), nullable=False)

class TokenOnChainData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token_address = db.Column(db.String(255), unique=True, nullable=False)
    data = db.Column(db.JSON, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


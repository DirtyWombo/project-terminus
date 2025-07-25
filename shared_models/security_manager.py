"""
CyberJackal MKVI - Security Manager
Centralized security utilities for the trading platform
"""

import os
import hashlib
import secrets
import time
import logging
from functools import wraps
from typing import Dict, Optional
import jwt
from datetime import datetime, timedelta

class SecurityManager:
    """Centralized security management for CyberJackal MKVI"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.failed_attempts = {}  # IP -> (count, last_attempt_time)
        self.rate_limits = {}      # IP -> (requests, window_start)
        
        # Security configuration
        self.MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5))
        self.LOCKOUT_DURATION = int(os.environ.get('LOCKOUT_DURATION_MINUTES', 15)) * 60
        self.RATE_LIMIT_PER_MINUTE = int(os.environ.get('API_RATE_LIMIT_PER_MINUTE', 60))
        self.RATE_LIMIT_BURST = int(os.environ.get('API_RATE_LIMIT_BURST', 10))
        
    def generate_secure_key(self, length: int = 32) -> str:
        """Generate cryptographically secure random key"""
        return secrets.token_urlsafe(length)
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> tuple:
        """Hash password with salt using PBKDF2"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        pwdhash = hashlib.pbkdf2_hmac('sha256', 
                                     password.encode('utf-8'), 
                                     salt.encode('utf-8'), 
                                     100000)  # 100k iterations
        return pwdhash.hex(), salt
    
    def verify_password(self, password: str, pwdhash: str, salt: str) -> bool:
        """Verify password against hash"""
        return self.hash_password(password, salt)[0] == pwdhash
    
    def generate_jwt_token(self, payload: Dict, expiration_hours: int = 24) -> str:
        """Generate JWT token with expiration"""
        secret_key = os.environ.get('JANUS_API_SECRET')
        if not secret_key:
            raise ValueError("JANUS_API_SECRET not configured")
            
        payload['exp'] = datetime.utcnow() + timedelta(hours=expiration_hours)
        payload['iat'] = datetime.utcnow()
        
        return jwt.encode(payload, secret_key, algorithm='HS256')
    
    def verify_jwt_token(self, token: str) -> Optional[Dict]:
        """Verify and decode JWT token"""
        try:
            secret_key = os.environ.get('JANUS_API_SECRET')
            if not secret_key:
                raise ValueError("JANUS_API_SECRET not configured")
                
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            self.logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError:
            self.logger.warning("Invalid JWT token")
            return None
    
    def is_ip_locked(self, ip_address: str) -> bool:
        """Check if IP is locked due to failed attempts"""
        if ip_address not in self.failed_attempts:
            return False
            
        count, last_attempt = self.failed_attempts[ip_address]
        
        # Check if lockout period has expired
        if time.time() - last_attempt > self.LOCKOUT_DURATION:
            del self.failed_attempts[ip_address]
            return False
            
        return count >= self.MAX_LOGIN_ATTEMPTS
    
    def record_failed_attempt(self, ip_address: str):
        """Record failed authentication attempt"""
        current_time = time.time()
        
        if ip_address in self.failed_attempts:
            count, _ = self.failed_attempts[ip_address]
            self.failed_attempts[ip_address] = (count + 1, current_time)
        else:
            self.failed_attempts[ip_address] = (1, current_time)
            
        self.logger.warning(f"Failed authentication attempt from {ip_address}")
    
    def clear_failed_attempts(self, ip_address: str):
        """Clear failed attempts for successful authentication"""
        if ip_address in self.failed_attempts:
            del self.failed_attempts[ip_address]
    
    def check_rate_limit(self, ip_address: str) -> bool:
        """Check if request is within rate limits"""
        current_time = time.time()
        
        if ip_address not in self.rate_limits:
            self.rate_limits[ip_address] = (1, current_time)
            return True
            
        count, window_start = self.rate_limits[ip_address]
        
        # Reset window if minute has passed
        if current_time - window_start > 60:
            self.rate_limits[ip_address] = (1, current_time)
            return True
            
        # Check if within limits
        if count < self.RATE_LIMIT_PER_MINUTE:
            self.rate_limits[ip_address] = (count + 1, window_start)
            return True
        else:
            self.logger.warning(f"Rate limit exceeded for {ip_address}")
            return False
    
    def sanitize_input(self, input_string: str) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not isinstance(input_string, str):
            return str(input_string)
            
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '|', '`', '$']
        sanitized = input_string
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
            
        return sanitized.strip()
    
    def validate_api_key_format(self, api_key: str) -> bool:
        """Validate API key format"""
        if not api_key or len(api_key) < 32:
            return False
            
        # Check if it looks like a valid key (alphanumeric + some special chars)
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.')
        return all(c in allowed_chars for c in api_key)
    
    def mask_sensitive_data(self, data: str, mask_char: str = '*', visible_chars: int = 4) -> str:
        """Mask sensitive data for logging"""
        if not data or len(data) <= visible_chars * 2:
            return mask_char * 8
            
        return data[:visible_chars] + mask_char * (len(data) - visible_chars * 2) + data[-visible_chars:]

# Global security manager instance
security_manager = SecurityManager()

def require_authentication(f):
    """Decorator to require JWT authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, jsonify
        
        # Get client IP
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Check if IP is locked
        if security_manager.is_ip_locked(client_ip):
            return jsonify({"error": "IP temporarily locked due to failed attempts"}), 429
            
        # Check rate limiting
        if not security_manager.check_rate_limit(client_ip):
            return jsonify({"error": "Rate limit exceeded"}), 429
            
        # Get token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            security_manager.record_failed_attempt(client_ip)
            return jsonify({"error": "Missing or invalid authorization header"}), 401
            
        token = auth_header.split(' ')[1]
        payload = security_manager.verify_jwt_token(token)
        
        if not payload:
            security_manager.record_failed_attempt(client_ip)
            return jsonify({"error": "Invalid or expired token"}), 401
            
        # Clear failed attempts on successful auth
        security_manager.clear_failed_attempts(client_ip)
        
        # Add payload to request context
        request.jwt_payload = payload
        
        return f(*args, **kwargs)
    return decorated_function

def require_janus_secret(f):
    """Enhanced decorator with security features"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, jsonify
        
        # Get client IP
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Check if IP is locked
        if security_manager.is_ip_locked(client_ip):
            return jsonify({"error": "IP temporarily locked"}), 429
            
        # Check rate limiting
        if not security_manager.check_rate_limit(client_ip):
            return jsonify({"error": "Rate limit exceeded"}), 429
            
        # Verify Janus secret
        janus_secret = os.environ.get("JANUS_API_SECRET")
        if not janus_secret:
            logging.error("JANUS_API_SECRET not configured")
            return jsonify({"error": "Server configuration error"}), 500

        provided_secret = request.headers.get('X-Janus-API-Secret')
        if not provided_secret or provided_secret != janus_secret:
            security_manager.record_failed_attempt(client_ip)
            logging.warning(f"Unauthorized access attempt from {client_ip}")
            return jsonify({"error": "Unauthorized"}), 401
            
        # Clear failed attempts on successful auth
        security_manager.clear_failed_attempts(client_ip)
        
        return f(*args, **kwargs)
    return decorated_function
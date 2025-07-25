"""
CyberJackal MKVI - Security Middleware
Flask middleware for comprehensive security protection
"""

import os
import time
import logging
from flask import request, jsonify, g
from functools import wraps
try:
    from .security_manager import security_manager
except ImportError:
    from security_manager import security_manager

class SecurityMiddleware:
    """Comprehensive security middleware for Flask applications"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        # Security headers
        @app.after_request
        def add_security_headers(response):
            # Prevent clickjacking
            response.headers['X-Frame-Options'] = 'DENY'
            
            # Prevent MIME type sniffing
            response.headers['X-Content-Type-Options'] = 'nosniff'
            
            # XSS protection
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # Referrer policy
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # Content Security Policy
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' wss: https:; "
                "font-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
            
            # HTTPS enforcement in production
            if os.environ.get('ENFORCE_HTTPS', 'false').lower() == 'true':
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
            return response
            
        return app
    
    def before_request(self):
        """Execute before each request"""
        # Get client IP
        client_ip = self.get_client_ip()
        g.client_ip = client_ip
        
        # Log request
        self.log_request(client_ip)
        
        # Skip security checks for health endpoints
        if request.endpoint in ['api.health', 'health']:
            return
            
        # Check if IP is blocked
        if security_manager.is_ip_locked(client_ip):
            self.logger.warning(f"Blocked request from locked IP: {client_ip}")
            return jsonify({"error": "Access temporarily restricted"}), 429
        
        # Apply rate limiting to API endpoints
        if request.path.startswith('/api/'):
            if not security_manager.check_rate_limit(client_ip):
                self.logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429
        
        # Validate request size
        max_content_length = 10 * 1024 * 1024  # 10MB
        if request.content_length and request.content_length > max_content_length:
            self.logger.warning(f"Request too large from IP: {client_ip}")
            return jsonify({"error": "Request entity too large"}), 413
        
        # Sanitize query parameters
        if request.args:
            sanitized_args = {}
            for key, value in request.args.items():
                sanitized_key = security_manager.sanitize_input(key)
                sanitized_value = security_manager.sanitize_input(value)
                sanitized_args[sanitized_key] = sanitized_value
            request.args = sanitized_args
    
    def after_request(self, response):
        """Execute after each request"""
        # Remove sensitive headers
        response.headers.pop('Server', None)
        response.headers.pop('X-Powered-By', None)
        
        return response
    
    def get_client_ip(self):
        """Get real client IP address"""
        # Check for forwarded headers (common in load balancer setups)
        forwarded_ips = request.environ.get('HTTP_X_FORWARDED_FOR')
        if forwarded_ips:
            # Take the first IP (client IP)
            return forwarded_ips.split(',')[0].strip()
        
        # Check other common headers
        real_ip = request.environ.get('HTTP_X_REAL_IP')
        if real_ip:
            return real_ip
            
        # Fallback to remote address
        return request.environ.get('REMOTE_ADDR', 'unknown')
    
    def log_request(self, client_ip):
        """Log incoming request for security monitoring"""
        sensitive_paths = ['/api/trade_cycle', '/api/adaptive-alpha/update', '/api/correlation/trigger']
        
        log_data = {
            'ip': client_ip,
            'method': request.method,
            'path': request.path,
            'user_agent': request.headers.get('User-Agent', 'unknown'),
            'timestamp': time.time()
        }
        
        # Log sensitive endpoint access
        if request.path in sensitive_paths:
            self.logger.warning(f"Sensitive endpoint access: {log_data}")
        
        # Log failed authentication attempts
        if 'X-Janus-API-Secret' in request.headers:
            secret = request.headers.get('X-Janus-API-Secret')
            expected_secret = os.environ.get('JANUS_API_SECRET')
            if secret != expected_secret:
                self.logger.error(f"Invalid API secret from {client_ip} for {request.path}")

def require_api_key(f):
    """Decorator to require valid API key for external API access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({"error": "API key required"}), 401
        
        # Validate API key format
        if not security_manager.validate_api_key_format(api_key):
            security_manager.record_failed_attempt(g.client_ip)
            return jsonify({"error": "Invalid API key format"}), 401
        
        # Here you would validate against your API key database
        # For now, we'll use environment variable
        valid_api_key = os.environ.get('EXTERNAL_API_KEY')
        if valid_api_key and api_key != valid_api_key:
            security_manager.record_failed_attempt(g.client_ip)
            return jsonify({"error": "Invalid API key"}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def require_https(f):
    """Decorator to enforce HTTPS in production"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if os.environ.get('ENFORCE_HTTPS', 'false').lower() == 'true':
            if not request.is_secure and not request.headers.get('X-Forwarded-Proto') == 'https':
                return jsonify({"error": "HTTPS required"}), 400
        return f(*args, **kwargs)
    return decorated_function

def log_sensitive_operation(operation_name: str):
    """Decorator to log sensitive operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = g.get('client_ip', 'unknown')
            
            logging.info(f"Sensitive operation '{operation_name}' initiated by {client_ip}")
            
            try:
                result = f(*args, **kwargs)
                logging.info(f"Sensitive operation '{operation_name}' completed successfully")
                return result
            except Exception as e:
                logging.error(f"Sensitive operation '{operation_name}' failed: {str(e)}")
                raise
                
        return decorated_function
    return decorator
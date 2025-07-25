"""
CyberJackal MKVI - Security Configuration
Centralized security settings and validation
"""

import os
import logging
import secrets
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class SecurityConfig:
    """Security configuration settings"""
    # Authentication
    jwt_secret: str
    janus_api_secret: str
    session_timeout_minutes: int = 30
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    
    # Rate limiting
    api_rate_limit_per_minute: int = 60
    api_rate_limit_burst: int = 10
    
    # HTTPS enforcement
    enforce_https: bool = False
    
    # API security
    max_request_size_mb: int = 10
    allowed_origins: List[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_sensitive_operations: bool = True
    
    def __post_init__(self):
        if self.allowed_origins is None:
            self.allowed_origins = ["http://localhost:5000", "https://localhost:5000"]

class SecurityValidator:
    """Validates security configuration and credentials"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.required_env_vars = [
            'JANUS_API_SECRET',
            'SECRET_KEY',
            'POSTGRES_PASSWORD',
            'EXCHANGE_API_KEY',
            'EXCHANGE_SECRET'
        ]
        
        self.sensitive_env_vars = [
            'PRIVATE_KEY',
            'POSTGRES_PASSWORD',
            'EXCHANGE_SECRET',
            'JANUS_API_SECRET',
            'SECRET_KEY',
            'SLACK_BOT_TOKEN',
            'SLACK_APP_TOKEN',
            'TELEGRAM_BOT_TOKEN',
            'TWITTER_BEARER_TOKEN',
            'NEWS_API_KEY',
            'COINGECKO_API_KEY',
            'MORALIS_API_KEY',
            'SENTRY_DSN'
        ]
    
    def validate_environment(self) -> Dict[str, bool]:
        """Validate all required environment variables are set"""
        validation_results = {}
        
        for var in self.required_env_vars:
            value = os.environ.get(var)
            is_valid = value is not None and len(value) > 0
            validation_results[var] = is_valid
            
            if not is_valid:
                self.logger.error(f"Required environment variable {var} is not set or empty")
        
        return validation_results
    
    def check_weak_credentials(self) -> Dict[str, List[str]]:
        """Check for weak or default credentials"""
        issues = {"weak": [], "default": []}
        
        # Check for weak passwords/secrets
        weak_patterns = ['password', '123456', 'admin', 'secret', 'default']
        
        for var in self.sensitive_env_vars:
            value = os.environ.get(var, '')
            if value:
                value_lower = value.lower()
                
                # Check for weak patterns
                for pattern in weak_patterns:
                    if pattern in value_lower:
                        issues["weak"].append(f"{var}: contains '{pattern}'")
                
                # Check minimum length
                if len(value) < 16:
                    issues["weak"].append(f"{var}: too short (< 16 characters)")
        
        # Check for default values that should be changed
        default_checks = {
            'SECRET_KEY': 'your_secret_key_here',
            'JANUS_API_SECRET': 'your_jwt_secret_here',
            'POSTGRES_PASSWORD': 'password'
        }
        
        for var, default_val in default_checks.items():
            if os.environ.get(var) == default_val:
                issues["default"].append(f"{var}: using default value")
        
        return issues
    
    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate API key formats"""
        validations = {}
        
        # Exchange API validation
        exchange_key = os.environ.get('EXCHANGE_API_KEY', '')
        exchange_secret = os.environ.get('EXCHANGE_SECRET', '')
        
        validations['EXCHANGE_API_KEY'] = len(exchange_key) > 32
        validations['EXCHANGE_SECRET'] = len(exchange_secret) > 32
        
        # Slack token validation
        slack_bot_token = os.environ.get('SLACK_BOT_TOKEN', '')
        slack_app_token = os.environ.get('SLACK_APP_TOKEN', '')
        
        validations['SLACK_BOT_TOKEN'] = slack_bot_token.startswith('xoxb-')
        validations['SLACK_APP_TOKEN'] = slack_app_token.startswith('xapp-')
        
        # Private key validation (should be hex or start with 0x)
        private_key = os.environ.get('PRIVATE_KEY', '')
        if private_key:
            is_hex = all(c in '0123456789abcdefABCDEF' for c in private_key.replace('0x', ''))
            validations['PRIVATE_KEY'] = is_hex and len(private_key.replace('0x', '')) == 64
        
        return validations
    
    def check_file_permissions(self) -> Dict[str, bool]:
        """Check file permissions for sensitive files"""
        sensitive_files = ['.env', 'requirements.txt', 'docker-compose.yml']
        permissions = {}
        
        for filename in sensitive_files:
            try:
                if os.path.exists(filename):
                    stat = os.stat(filename)
                    # Check if file is world-readable (should not be for .env)
                    if filename == '.env':
                        is_secure = (stat.st_mode & 0o077) == 0  # No group/other permissions
                        permissions[filename] = is_secure
                    else:
                        permissions[filename] = True
                else:
                    permissions[filename] = False
            except Exception as e:
                self.logger.error(f"Error checking permissions for {filename}: {e}")
                permissions[filename] = False
        
        return permissions
    
    def generate_security_report(self) -> Dict:
        """Generate comprehensive security report"""
        report = {
            "timestamp": os.environ.get("TZ", "UTC"),
            "environment_validation": self.validate_environment(),
            "credential_issues": self.check_weak_credentials(),
            "api_key_validation": self.validate_api_keys(),
            "file_permissions": self.check_file_permissions(),
            "recommendations": []
        }
        
        # Add recommendations based on findings
        env_validation = report["environment_validation"]
        if not all(env_validation.values()):
            report["recommendations"].append("Set all required environment variables")
        
        credential_issues = report["credential_issues"]
        if credential_issues["weak"] or credential_issues["default"]:
            report["recommendations"].append("Replace weak or default credentials")
        
        api_validation = report["api_key_validation"]
        if not all(api_validation.values()):
            report["recommendations"].append("Verify API key formats")
        
        file_perms = report["file_permissions"]
        if not file_perms.get('.env', True):
            report["recommendations"].append("Secure .env file permissions (chmod 600)")
        
        return report

def load_security_config() -> SecurityConfig:
    """Load security configuration from environment"""
    return SecurityConfig(
        jwt_secret=os.environ.get('JANUS_API_SECRET', ''),
        janus_api_secret=os.environ.get('JANUS_API_SECRET', ''),
        session_timeout_minutes=int(os.environ.get('SESSION_TIMEOUT_MINUTES', 30)),
        max_login_attempts=int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5)),
        lockout_duration_minutes=int(os.environ.get('LOCKOUT_DURATION_MINUTES', 15)),
        api_rate_limit_per_minute=int(os.environ.get('API_RATE_LIMIT_PER_MINUTE', 60)),
        api_rate_limit_burst=int(os.environ.get('API_RATE_LIMIT_BURST', 10)),
        enforce_https=os.environ.get('ENFORCE_HTTPS', 'false').lower() == 'true',
        max_request_size_mb=int(os.environ.get('MAX_REQUEST_SIZE_MB', 10)),
        log_level=os.environ.get('LOG_LEVEL', 'INFO'),
        log_sensitive_operations=os.environ.get('LOG_SENSITIVE_OPERATIONS', 'true').lower() == 'true'
    )

def generate_secure_secrets() -> Dict[str, str]:
    """Generate secure secrets for initial setup"""
    return {
        'SECRET_KEY': secrets.token_urlsafe(32),
        'JANUS_API_SECRET': secrets.token_urlsafe(32),
        'POSTGRES_PASSWORD': secrets.token_urlsafe(24),
        'EXTERNAL_API_KEY': secrets.token_urlsafe(24)
    }

# Global security validator instance
security_validator = SecurityValidator()
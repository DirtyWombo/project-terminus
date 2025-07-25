"""
CyberJackal MKVI - Security Monitoring Routes
Administrative endpoints for security monitoring and management
"""

import os
import logging
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared_models'))
from security_manager import security_manager, require_authentication
from security_config import security_validator, generate_secure_secrets
from security_middleware import require_api_key, log_sensitive_operation

security_bp = Blueprint('security', __name__)
logger = logging.getLogger(__name__)

@security_bp.route('/security/status', methods=['GET'])
@require_api_key
def get_security_status():
    """Get comprehensive security status report"""
    try:
        # Generate security report
        report = security_validator.generate_security_report()
        
        # Add runtime security stats
        runtime_stats = {
            "active_rate_limits": len(security_manager.rate_limits),
            "locked_ips": len([ip for ip, (count, _) in security_manager.failed_attempts.items() 
                              if count >= security_manager.MAX_LOGIN_ATTEMPTS]),
            "total_failed_attempts": sum(count for count, _ in security_manager.failed_attempts.values())
        }
        
        report["runtime_stats"] = runtime_stats
        report["security_level"] = _calculate_security_level(report)
        
        return jsonify(report), 200
        
    except Exception as e:
        logger.error(f"Error generating security status: {e}")
        return jsonify({"error": "Failed to generate security status"}), 500

@security_bp.route('/security/failed-attempts', methods=['GET'])
@require_api_key
def get_failed_attempts():
    """Get recent failed authentication attempts"""
    try:
        failed_attempts = []
        current_time = datetime.now()
        
        for ip, (count, last_attempt_time) in security_manager.failed_attempts.items():
            last_attempt = datetime.fromtimestamp(last_attempt_time)
            is_locked = count >= security_manager.MAX_LOGIN_ATTEMPTS
            
            failed_attempts.append({
                "ip_address": security_manager.mask_sensitive_data(ip, '*', 2),
                "attempt_count": count,
                "last_attempt": last_attempt.isoformat(),
                "is_locked": is_locked,
                "minutes_since_last": int((current_time - last_attempt).total_seconds() / 60)
            })
        
        # Sort by most recent
        failed_attempts.sort(key=lambda x: x["last_attempt"], reverse=True)
        
        return jsonify({
            "failed_attempts": failed_attempts,
            "total_locked_ips": len([f for f in failed_attempts if f["is_locked"]]),
            "lockout_duration_minutes": security_manager.LOCKOUT_DURATION / 60
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting failed attempts: {e}")
        return jsonify({"error": "Failed to retrieve failed attempts"}), 500

@security_bp.route('/security/rate-limits', methods=['GET'])
@require_api_key
def get_rate_limit_status():
    """Get current rate limiting status"""
    try:
        rate_limit_info = []
        current_time = datetime.now()
        
        for ip, (count, window_start) in security_manager.rate_limits.items():
            window_start_dt = datetime.fromtimestamp(window_start)
            seconds_in_window = (current_time - window_start_dt).total_seconds()
            
            rate_limit_info.append({
                "ip_address": security_manager.mask_sensitive_data(ip, '*', 2),
                "requests_in_window": count,
                "window_start": window_start_dt.isoformat(),
                "seconds_in_current_window": int(seconds_in_window),
                "remaining_requests": max(0, security_manager.RATE_LIMIT_PER_MINUTE - count)
            })
        
        return jsonify({
            "rate_limits": rate_limit_info,
            "rate_limit_per_minute": security_manager.RATE_LIMIT_PER_MINUTE,
            "burst_limit": security_manager.RATE_LIMIT_BURST
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting rate limit status: {e}")
        return jsonify({"error": "Failed to retrieve rate limit status"}), 500

@security_bp.route('/security/unlock-ip', methods=['POST'])
@require_api_key
@log_sensitive_operation('ip_unlock')
def unlock_ip():
    """Manually unlock a locked IP address"""
    try:
        data = request.get_json()
        if not data or 'ip_address' not in data:
            return jsonify({"error": "IP address required"}), 400
        
        ip_address = data['ip_address']
        
        # Validate IP format (basic check)
        if not _is_valid_ip_format(ip_address):
            return jsonify({"error": "Invalid IP address format"}), 400
        
        # Clear failed attempts for this IP
        if ip_address in security_manager.failed_attempts:
            del security_manager.failed_attempts[ip_address]
            logger.info(f"Manually unlocked IP address: {security_manager.mask_sensitive_data(ip_address)}")
            return jsonify({"message": f"IP address {security_manager.mask_sensitive_data(ip_address)} unlocked successfully"}), 200
        else:
            return jsonify({"message": "IP address was not locked"}), 200
            
    except Exception as e:
        logger.error(f"Error unlocking IP: {e}")
        return jsonify({"error": "Failed to unlock IP address"}), 500

@security_bp.route('/security/generate-secrets', methods=['POST'])
@require_api_key
@log_sensitive_operation('secret_generation')
def generate_new_secrets():
    """Generate new secure secrets (for setup/rotation)"""
    try:
        secrets = generate_secure_secrets()
        
        # Mask the secrets for response (show only first/last few characters)
        masked_secrets = {}
        for key, value in secrets.items():
            masked_secrets[key] = security_manager.mask_sensitive_data(value, '*', 4)
        
        logger.info("New security secrets generated")
        
        return jsonify({
            "message": "New secrets generated successfully",
            "secrets": masked_secrets,
            "note": "Full secrets are not returned for security. Use the generated values from logs or console."
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating secrets: {e}")
        return jsonify({"error": "Failed to generate secrets"}), 500

@security_bp.route('/security/validate-config', methods=['POST'])
@require_api_key
def validate_security_config():
    """Validate current security configuration"""
    try:
        # Run comprehensive validation
        validation_results = {
            "environment_variables": security_validator.validate_environment(),
            "credential_strength": security_validator.check_weak_credentials(),
            "api_key_formats": security_validator.validate_api_keys(),
            "file_permissions": security_validator.check_file_permissions()
        }
        
        # Calculate overall security score
        total_checks = len(validation_results["environment_variables"]) + len(validation_results["api_key_formats"])
        passed_checks = sum(validation_results["environment_variables"].values()) + sum(validation_results["api_key_formats"].values())
        
        security_score = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        
        # Determine security level
        if security_score >= 90:
            security_level = "HIGH"
        elif security_score >= 70:
            security_level = "MEDIUM"
        else:
            security_level = "LOW"
        
        return jsonify({
            "validation_results": validation_results,
            "security_score": round(security_score, 2),
            "security_level": security_level,
            "recommendations": _generate_security_recommendations(validation_results)
        }), 200
        
    except Exception as e:
        logger.error(f"Error validating security config: {e}")
        return jsonify({"error": "Failed to validate security configuration"}), 500

def _calculate_security_level(report):
    """Calculate overall security level based on report"""
    issues = 0
    
    # Count environment variable issues
    env_validation = report.get("environment_validation", {})
    issues += len([k for k, v in env_validation.items() if not v])
    
    # Count credential issues
    credential_issues = report.get("credential_issues", {})
    issues += len(credential_issues.get("weak", [])) + len(credential_issues.get("default", []))
    
    # Count API key issues
    api_validation = report.get("api_key_validation", {})
    issues += len([k for k, v in api_validation.items() if not v])
    
    # Determine level
    if issues == 0:
        return "HIGH"
    elif issues <= 3:
        return "MEDIUM"
    else:
        return "LOW"

def _generate_security_recommendations(validation_results):
    """Generate specific security recommendations"""
    recommendations = []
    
    # Environment variable recommendations
    env_issues = [k for k, v in validation_results["environment_variables"].items() if not v]
    if env_issues:
        recommendations.append(f"Set missing environment variables: {', '.join(env_issues)}")
    
    # Credential recommendations
    weak_creds = validation_results["credential_strength"]["weak"]
    default_creds = validation_results["credential_strength"]["default"]
    
    if weak_creds:
        recommendations.append("Replace weak credentials with stronger alternatives")
    
    if default_creds:
        recommendations.append("Change default credentials to custom values")
    
    # API key recommendations
    api_issues = [k for k, v in validation_results["api_key_formats"].items() if not v]
    if api_issues:
        recommendations.append(f"Fix API key formats for: {', '.join(api_issues)}")
    
    # File permission recommendations
    file_issues = [k for k, v in validation_results["file_permissions"].items() if not v]
    if file_issues:
        recommendations.append(f"Secure file permissions for: {', '.join(file_issues)}")
    
    return recommendations

def _is_valid_ip_format(ip_address):
    """Basic IP address format validation"""
    try:
        parts = ip_address.split('.')
        if len(parts) != 4:
            return False
        
        for part in parts:
            if not part.isdigit() or int(part) > 255:
                return False
        
        return True
    except:
        return False
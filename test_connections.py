"""
Project Terminus - Sprint 1: API Connection Testing
This script validates connectivity to Databento and Tradovate APIs
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ConnectionTester:
    """Test connections to all required APIs"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "databento": {"status": "pending", "details": {}},
            "tradovate": {"status": "pending", "details": {}},
            "overall": "pending"
        }
    
    async def test_databento_connection(self):
        """Test Databento market data connection"""
        print("\n🔍 Testing Databento Connection...")
        
        api_key = os.getenv('DATABENTO_API_KEY')
        
        if not api_key or api_key == 'your-databento-api-key-here':
            self.results["databento"]["status"] = "failed"
            self.results["databento"]["details"] = {
                "error": "Missing or placeholder API key",
                "action": "Please update DATABENTO_API_KEY in .env file"
            }
            print("❌ Databento: Missing API key")
            return False
        
        try:
            # TODO: Implement actual Databento connection test
            # import databento as db
            # client = db.Historical(api_key)
            # dataset = client.metadata.list_datasets()
            
            print("⚠️  Databento: Connection test placeholder")
            print("   Please implement actual Databento SDK test")
            self.results["databento"]["status"] = "not_implemented"
            self.results["databento"]["details"] = {
                "message": "Databento SDK integration pending",
                "next_step": "Install databento package and implement connection"
            }
            return False
            
        except Exception as e:
            self.results["databento"]["status"] = "error"
            self.results["databento"]["details"] = {"error": str(e)}
            print(f"❌ Databento: Connection failed - {e}")
            return False
    
    async def test_tradovate_connection(self):
        """Test Tradovate trading platform connection"""
        print("\n🔍 Testing Tradovate Connection...")
        
        api_key = os.getenv('TRADOVATE_API_KEY')
        api_secret = os.getenv('TRADOVATE_API_SECRET')
        account_id = os.getenv('TRADOVATE_ACCOUNT_ID')
        environment = os.getenv('TRADOVATE_ENVIRONMENT', 'sandbox')
        
        if not all([api_key, api_secret, account_id]) or api_key == 'your-tradovate-api-key-here':
            self.results["tradovate"]["status"] = "failed"
            self.results["tradovate"]["details"] = {
                "error": "Missing or placeholder credentials",
                "action": "Please update Tradovate credentials in .env file"
            }
            print("❌ Tradovate: Missing credentials")
            return False
        
        try:
            # TODO: Implement actual Tradovate connection test
            # The Tradovate API requires WebSocket connections
            
            print("⚠️  Tradovate: Connection test placeholder")
            print(f"   Environment: {environment}")
            print("   Please implement actual Tradovate API test")
            self.results["tradovate"]["status"] = "not_implemented"
            self.results["tradovate"]["details"] = {
                "environment": environment,
                "message": "Tradovate API integration pending",
                "next_step": "Implement WebSocket connection to Tradovate"
            }
            return False
            
        except Exception as e:
            self.results["tradovate"]["status"] = "error"
            self.results["tradovate"]["details"] = {"error": str(e)}
            print(f"❌ Tradovate: Connection failed - {e}")
            return False
    
    def check_environment_setup(self):
        """Verify all required environment variables are set"""
        print("\n🔍 Checking Environment Configuration...")
        
        required_vars = [
            'DATABENTO_API_KEY',
            'TRADOVATE_API_KEY',
            'TRADOVATE_API_SECRET',
            'TRADOVATE_ACCOUNT_ID',
            'APEX_STARTING_CAPITAL',
            'APEX_PROFIT_TARGET'
        ]
        
        missing_vars = []
        placeholder_vars = []
        
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing_vars.append(var)
            elif 'your-' in value or 'placeholder' in value:
                placeholder_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        
        if placeholder_vars:
            print(f"⚠️  Placeholder values found: {', '.join(placeholder_vars)}")
        
        if not missing_vars and not placeholder_vars:
            print("✅ All required environment variables are set")
            return True
        
        return False
    
    async def run_all_tests(self):
        """Execute all connection tests"""
        print("=" * 60)
        print("🚀 PROJECT TERMINUS - CONNECTION TEST SUITE")
        print("=" * 60)
        
        # Check environment first
        env_ok = self.check_environment_setup()
        
        # Run connection tests
        databento_ok = await self.test_databento_connection()
        tradovate_ok = await self.test_tradovate_connection()
        
        # Determine overall status
        if databento_ok and tradovate_ok:
            self.results["overall"] = "success"
            print("\n✅ All connections successful!")
        else:
            self.results["overall"] = "failed"
            print("\n❌ Some connections failed. Please check the details above.")
        
        # Save results
        self.save_results()
        
        return self.results["overall"] == "success"
    
    def save_results(self):
        """Save test results to file"""
        with open('connection_test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📄 Results saved to connection_test_results.json")

async def main():
    """Main entry point"""
    tester = ConnectionTester()
    success = await tester.run_all_tests()
    
    print("\n" + "=" * 60)
    print("📋 NEXT STEPS:")
    print("=" * 60)
    print("1. Update all placeholder values in .env file")
    print("2. Install required packages:")
    print("   pip install databento tradovate-api-client websocket-client")
    print("3. Implement actual API connection logic")
    print("4. Re-run this script to verify connections")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
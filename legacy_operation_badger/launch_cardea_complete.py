#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Complete Cardea System Launcher
Launches the full Cardea monitoring ecosystem:
- Cardea Slack Agent
- Cardea Web UI
- Integration with Live Trading System

This provides comprehensive monitoring for Sprint 19 validation.
"""

import os
import sys
import time
import subprocess
import threading
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CardeaSystemLauncher:
    """
    Complete Cardea system launcher and manager
    Sister system to Janus for Bull Call Spread monitoring
    """
    
    def __init__(self):
        self.processes = {}
        self.running = False
        
        # Component definitions
        self.components = {
            'slack_agent': {
                'script': 'cardea_slack_agent.py',
                'description': 'Cardea Slack Agent',
                'port': None,
                'required': True
            },
            'web_ui': {
                'script': 'cardea_web_server.py', 
                'description': 'Cardea Web UI',
                'port': 5001,
                'required': False
            }
        }
        
    def print_banner(self):
        """Print Cardea system banner"""
        banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                              CARDEA GUARDIAN SYSTEM                          ║
║                         Bull Call Spread Trading Monitor                     ║
║                           Sister to Janus • Sprint 19                        ║
╠══════════════════════════════════════════════════════════════════════════════╣ 
║                                                                              ║
║  🛡️  AI-Powered Options Trading Guardian                                     ║
║  📊  Real-time Bull Call Spread Monitoring                                   ║
║  💬  Comprehensive Slack Integration                                         ║
║  🌐  Professional Web Dashboard                                              ║
║  ⚡  30-Day Validation Support                                               ║
║                                                                              ║
║  Roman Goddess of Hinges and Thresholds                                     ║
║  "While Janus opens doors to opportunity,                                   ║
║   Cardea executes and protects the trades"                                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """
        print(banner)
        
    def check_prerequisites(self):
        """Check system prerequisites"""
        logger.info("Checking Cardea system prerequisites...")
        
        required_files = [
            'cardea_slack_agent.py',
            'cardea_web_server.py', 
            'cardea_web_ui.html',
            '.env'
        ]
        
        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)
                
        if missing_files:
            logger.error(f"Missing required files: {missing_files}")
            return False
            
        # Check environment variables
        if not os.environ.get("CARDEA_SLACK_BOT_TOKEN"):
            logger.warning("CARDEA_SLACK_BOT_TOKEN not found in environment - Slack agent may fail")
            
        if not os.environ.get("CARDEA_SLACK_APP_TOKEN"):
            logger.warning("CARDEA_SLACK_APP_TOKEN not found in environment - Slack agent may fail")
            
        logger.info("✅ Prerequisites check completed")
        return True
        
    def launch_component(self, component_name: str):
        """Launch a Cardea component"""
        if component_name not in self.components:
            logger.error(f"Unknown component: {component_name}")
            return False
            
        component = self.components[component_name]
        
        logger.info(f"Launching {component['description']}...")
        
        try:
            # Start component process
            process = subprocess.Popen(
                [sys.executable, component['script']],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.processes[component_name] = process
            
            # Give it time to start
            time.sleep(3)
            
            # Check if still running
            if process.poll() is None:
                logger.info(f"✅ {component['description']} started successfully (PID: {process.pid})")
                
                if component['port']:
                    logger.info(f"🌐 {component['description']} available at: http://localhost:{component['port']}")
                    
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"❌ {component['description']} failed to start")
                if stderr:
                    logger.error(f"Error: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error launching {component_name}: {e}")
            return False
            
    def stop_component(self, component_name: str):
        """Stop a Cardea component"""
        if component_name not in self.processes:
            return True
            
        process = self.processes[component_name]
        if process and process.poll() is None:
            logger.info(f"Stopping {self.components[component_name]['description']}...")
            process.terminate()
            
            try:
                process.wait(timeout=10)
                logger.info(f"✅ {self.components[component_name]['description']} stopped")
            except subprocess.TimeoutExpired:
                process.kill()
                logger.info(f"🔴 {self.components[component_name]['description']} force killed")
                
        del self.processes[component_name]
        return True
        
    def get_system_status(self):
        """Get current status of all components"""
        status = {}
        
        for component_name, component_info in self.components.items():
            if component_name in self.processes:
                process = self.processes[component_name]
                if process.poll() is None:
                    status[component_name] = {
                        'status': 'RUNNING',
                        'pid': process.pid,
                        'description': component_info['description']
                    }
                else:
                    status[component_name] = {
                        'status': 'CRASHED',
                        'pid': None,
                        'description': component_info['description']
                    }
                    # Clean up crashed process
                    del self.processes[component_name]
            else:
                status[component_name] = {
                    'status': 'STOPPED',
                    'pid': None,
                    'description': component_info['description']
                }
                
        return status
        
    def print_status(self):
        """Print system status"""
        status = self.get_system_status()
        
        print("\n" + "=" * 80)
        print("CARDEA GUARDIAN SYSTEM STATUS")
        print("=" * 80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        for component_name, component_status in status.items():
            status_color = component_status['status']
            pid_info = f" (PID: {component_status['pid']})" if component_status['pid'] else ""
            
            print(f"{component_status['description']:.<50} {status_color}{pid_info}")
            
        # Show access information
        print("\n" + "=" * 80)
        print("ACCESS INFORMATION:")
        print("🌐 Cardea Web UI: http://localhost:5001")
        print("💬 Slack Commands: /cardea-help")
        print("📊 API Status: http://localhost:5001/api/cardea/status")
        print("=" * 80)
        
    def launch_complete_system(self):
        """Launch the complete Cardea system"""
        self.print_banner()
        
        if not self.check_prerequisites():
            logger.error("Prerequisites check failed - cannot launch Cardea")
            return False
            
        logger.info("🚀 Launching complete Cardea Guardian System...")
        
        # Launch components in order
        success_count = 0
        
        # Start Slack agent first
        if self.launch_component('slack_agent'):
            success_count += 1
        else:
            logger.warning("Slack agent failed - continuing with web UI only")
            
        # Start web UI
        if self.launch_component('web_ui'):
            success_count += 1
        else:
            logger.warning("Web UI failed - continuing with available components")
            
        if success_count == 0:
            logger.error("❌ No components started successfully")
            return False
            
        self.running = True
        logger.info(f"✅ Cardea system launched with {success_count}/2 components")
        
        # Print status
        time.sleep(2)
        self.print_status()
        
        return True
        
    def monitor_system(self):
        """Monitor system components"""
        logger.info("🔍 Starting Cardea system monitoring...")
        
        while self.running:
            try:
                time.sleep(30)  # Check every 30 seconds
                
                # Check for crashed components
                status = self.get_system_status()
                for component_name, component_status in status.items():
                    if component_status['status'] == 'CRASHED':
                        logger.error(f"💥 Component {component_name} has crashed!")
                        
                        # Attempt restart for critical components
                        if self.components[component_name].get('required', False):
                            logger.info(f"🔄 Attempting to restart {component_name}...")
                            time.sleep(5)
                            self.launch_component(component_name)
                            
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                time.sleep(60)
                
    def shutdown_system(self):
        """Shutdown all components"""
        logger.info("🛑 Shutting down Cardea Guardian System...")
        self.running = False
        
        for component_name in list(self.processes.keys()):
            self.stop_component(component_name)
            
        logger.info("✅ Cardea system shutdown complete")
        print("\n🛡️ Cardea Guardian offline. Bull Call Spread monitoring ended.")

def main():
    """Main entry point"""
    launcher = CardeaSystemLauncher()
    
    try:
        # Launch system
        if launcher.launch_complete_system():
            # Start monitoring in background
            monitor_thread = threading.Thread(target=launcher.monitor_system, daemon=True)
            monitor_thread.start()
            
            print("\n🛡️ Cardea Guardian System is online and monitoring your trades!")
            print("📋 Available interfaces:")
            print("   • Web UI: http://localhost:5001")
            print("   • Slack: Use /cardea-help for commands")
            print("\n⌨️ Press Ctrl+C to shutdown system")
            
            # Keep main thread alive
            try:
                while launcher.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🔔 Shutdown requested by user...")
                
        else:
            logger.error("Failed to launch Cardea system")
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        
    finally:
        launcher.shutdown_system()

if __name__ == "__main__":
    main()
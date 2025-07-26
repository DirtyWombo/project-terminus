#!/usr/bin/env python3
"""
GitHub Automation Script for Operation Badger
Automates common GitHub operations using credentials from .env file
"""

import os
import subprocess
import json
from datetime import datetime
from dotenv import load_dotenv

class GitHubAutomation:
    """
    Automated GitHub operations for Operation Badger project.
    Handles commits, pushes, pull requests, and repository management.
    """
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        self.username = os.getenv('GITHUB_USERNAME')
        self.token = os.getenv('GITHUB_TOKEN')
        
        if not self.username or not self.token:
            raise ValueError("GitHub credentials not found in .env file")
        
        # Configure git with credentials
        self._configure_git()
        
        print(f"GitHub Automation initialized for user: {self.username}")
    
    def _configure_git(self):
        """Configure git with credentials from .env file"""
        try:
            # Set git config
            subprocess.run(['git', 'config', 'user.name', self.username], check=True)
            subprocess.run(['git', 'config', 'user.email', f'{self.username}@users.noreply.github.com'], check=True)
            
            # Configure remote URL with token authentication
            remote_url = f"https://{self.username}:{self.token}@github.com/{self.username}/cyberjackal-stocks.git"
            subprocess.run(['git', 'remote', 'set-url', 'origin', remote_url], check=True)
            
            print("SUCCESS: Git configured with GitHub credentials")
            
        except subprocess.CalledProcessError as e:
            print(f"Warning: Git configuration failed: {e}")
    
    def get_status(self):
        """Get current git status"""
        try:
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True, check=True)
            
            if result.stdout.strip():
                print("Modified files:")
                for line in result.stdout.strip().split('\n'):
                    print(f"  {line}")
                return result.stdout.strip().split('\n')
            else:
                print("Working directory clean - no changes to commit")
                return []
                
        except subprocess.CalledProcessError as e:
            print(f"Error getting git status: {e}")
            return None
    
    def add_all_changes(self):
        """Add all changes to staging area"""
        try:
            subprocess.run(['git', 'add', '.'], check=True)
            print("SUCCESS: All changes staged for commit")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error staging changes: {e}")
            return False
    
    def commit_changes(self, message=None):
        """Create a commit with all staged changes"""
        if not message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"Automated commit - Operation Badger updates {timestamp}"
        
        # Add Claude attribution
        full_message = f"""{message}

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""
        
        try:
            subprocess.run(['git', 'commit', '-m', full_message], check=True)
            print(f"SUCCESS: Changes committed with message: {message}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error committing changes: {e}")
            return False
    
    def push_changes(self, branch='main'):
        """Push committed changes to remote repository"""
        try:
            subprocess.run(['git', 'push', 'origin', branch], check=True)
            print(f"SUCCESS: Changes pushed to {branch} branch")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error pushing changes: {e}")
            return False
    
    def create_and_push_commit(self, commit_message=None):
        """Full workflow: stage, commit, and push all changes"""
        print("=" * 80)
        print("AUTOMATED GITHUB WORKFLOW")
        print("=" * 80)
        
        # Check for changes
        changes = self.get_status()
        if not changes:
            print("No changes to commit")
            return True
        
        # Stage all changes
        if not self.add_all_changes():
            return False
        
        # Create commit
        if not self.commit_changes(commit_message):
            return False
        
        # Push to remote
        if not self.push_changes():
            return False
        
        print("=" * 80)
        print("SUCCESS: All changes committed and pushed to GitHub")
        print("=" * 80)
        return True
    
    def create_sprint_report_commit(self, sprint_number):
        """Create a specialized commit for sprint completion"""
        message = f"Complete Sprint {sprint_number} - Operation Badger Development"
        
        # Get current sprint results
        results_dir = f"results/sprint_{sprint_number}"
        if os.path.exists(results_dir):
            files = os.listdir(results_dir)
            if files:
                message += f" ({len(files)} result files)"
        
        return self.create_and_push_commit(message)
    
    def sync_repository(self):
        """Pull latest changes from remote and push local changes"""
        print("Synchronizing repository with remote...")
        
        try:
            # Pull latest changes
            subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
            print("SUCCESS: Repository synchronized with remote")
            
            # Push any local changes
            return self.create_and_push_commit("Sync repository - automated update")
            
        except subprocess.CalledProcessError as e:
            print(f"Error synchronizing repository: {e}")
            return False
    
    def create_release_tag(self, version, description):
        """Create and push a release tag"""
        try:
            # Create annotated tag
            subprocess.run(['git', 'tag', '-a', version, '-m', description], check=True)
            
            # Push tag to remote
            subprocess.run(['git', 'push', 'origin', version], check=True)
            
            print(f"SUCCESS: Release tag {version} created and pushed")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating release tag: {e}")
            return False
    
    def get_commit_history(self, count=10):
        """Get recent commit history"""
        try:
            result = subprocess.run([
                'git', 'log', f'--oneline', f'-{count}'
            ], capture_output=True, text=True, check=True)
            
            print(f"Recent {count} commits:")
            print(result.stdout)
            return result.stdout.strip().split('\n')
            
        except subprocess.CalledProcessError as e:
            print(f"Error getting commit history: {e}")
            return None

def main():
    """Main function for command-line usage"""
    import sys
    
    try:
        gh = GitHubAutomation()
        
        if len(sys.argv) < 2:
            print("GitHub Automation Commands:")
            print("  status     - Show repository status")
            print("  commit     - Stage, commit, and push all changes")
            print("  sync       - Pull remote changes and push local changes")
            print("  history    - Show recent commit history")
            print("  sprint <N> - Create sprint completion commit")
            print("  tag <ver> <desc> - Create release tag")
            return
        
        command = sys.argv[1].lower()
        
        if command == 'status':
            gh.get_status()
            
        elif command == 'commit':
            message = sys.argv[2] if len(sys.argv) > 2 else None
            gh.create_and_push_commit(message)
            
        elif command == 'sync':
            gh.sync_repository()
            
        elif command == 'history':
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            gh.get_commit_history(count)
            
        elif command == 'sprint':
            if len(sys.argv) < 3:
                print("Usage: python github_automation.py sprint <sprint_number>")
                return
            sprint_num = sys.argv[2]
            gh.create_sprint_report_commit(sprint_num)
            
        elif command == 'tag':
            if len(sys.argv) < 4:
                print("Usage: python github_automation.py tag <version> <description>")
                return
            version = sys.argv[2]
            description = ' '.join(sys.argv[3:])
            gh.create_release_tag(version, description)
            
        else:
            print(f"Unknown command: {command}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
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
    
    def create_repository_if_needed(self):
        """Create GitHub repository if it doesn't exist"""
        repo_name = "cyberjackal-stocks"
        
        try:
            # Try to create repository using GitHub API
            import requests
            
            url = "https://api.github.com/user/repos"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }
            data = {
                "name": repo_name,
                "description": "Operation Badger - Quantitative Trading System",
                "private": False,
                "auto_init": False
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 201:
                print(f"SUCCESS: Repository {repo_name} created on GitHub")
                return True
            elif response.status_code == 422:
                print(f"Repository {repo_name} already exists")
                return True
            else:
                print(f"Error creating repository: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Error creating repository: {e}")
            return False

    def pull_latest_changes(self, branch='main'):
        """Pull latest changes from remote repository"""
        try:
            print("Pulling latest changes from remote...")
            result = subprocess.run(['git', 'pull', 'origin', branch], 
                                  capture_output=True, text=True, check=True)
            print("SUCCESS: Latest changes pulled from remote")
            if result.stdout.strip():
                print(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            if "couldn't find remote ref" in str(e.stderr):
                print("Remote branch doesn't exist yet - this is normal for new repositories")
                return True
            print(f"Error pulling changes: {e}")
            print(f"stderr: {e.stderr}")
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
        
        # Try to push, create repo if needed
        if not self.push_changes():
            print("Push failed - attempting to create repository...")
            if self.create_repository_if_needed():
                print("Retrying push...")
                if not self.push_changes():
                    return False
            else:
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
        print("=" * 80)
        print("REPOSITORY SYNCHRONIZATION")
        print("=" * 80)
        
        # Step 1: Pull latest changes from remote
        if not self.pull_latest_changes():
            print("Warning: Failed to pull remote changes, continuing with local changes...")
        
        # Step 2: Check if there are local changes to push
        changes = self.get_status()
        if changes:
            print("Local changes detected - committing and pushing...")
            return self.create_and_push_commit("Sync repository - automated update")
        else:
            print("Repository is up to date - no local changes to push")
            return True

    def force_sync(self):
        """Force sync by handling merge conflicts automatically"""
        print("=" * 80)
        print("FORCE REPOSITORY SYNCHRONIZATION")
        print("=" * 80)
        
        try:
            # Add all changes first
            self.add_all_changes()
            
            # Try to pull with auto-merge
            result = subprocess.run(['git', 'pull', '--rebase', 'origin', 'main'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print("SUCCESS: Repository synchronized with rebase")
            else:
                print("Rebase failed, trying merge strategy...")
                subprocess.run(['git', 'pull', '--no-rebase', 'origin', 'main'], check=True)
                print("SUCCESS: Repository synchronized with merge")
            
            # Push any remaining changes
            return self.push_changes()
            
        except subprocess.CalledProcessError as e:
            print(f"Force sync failed: {e}")
            print("Manual intervention may be required")
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
            print("Git Helper Commands:")
            print('  python git_helper.py "message" - Commit and push with message')
            print("  python git_helper.py pull      - Pull from GitHub")
            print("  python git_helper.py sync      - Full synchronization")
            return
        
        command = sys.argv[1].lower()
        
        # Handle the three main commands as specified
        if command == 'pull':
            gh.pull_latest_changes()
            
        elif command == 'sync':
            gh.sync_repository()
            
        else:
            # If it's not 'pull' or 'sync', treat it as a commit message
            commit_message = sys.argv[1]  # First argument is the commit message
            gh.create_and_push_commit(commit_message)
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
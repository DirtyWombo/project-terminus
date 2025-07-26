# Git Helper Guide - Operation Badger

This guide explains how to use the simplified Git automation system for Operation Badger project management.

## Overview

The Git Helper provides three simple commands to handle all common Git/GitHub operations without needing to remember complex git commands or manage credentials manually.

## Setup

### Prerequisites
- Python 3.x installed
- GitHub username and personal access token in `.env` file:
  ```
  GITHUB_USERNAME=your_username
  GITHUB_TOKEN=your_personal_access_token
  ```

### Installation
The automation system is already set up and ready to use. Required packages are installed automatically.

## Commands

There are only three commands you need to remember:

### 1. Commit and Push
Stage all changes, create a commit with your message, and push to GitHub.
```bash
python git_helper.py "Your commit message here"
```

Examples:
```bash
python git_helper.py "Fix trading strategy bug"
python git_helper.py "Add new backtest results"  
python git_helper.py "Complete Sprint 12 development"
```

### 2. Pull from GitHub
Pull the latest changes from the remote repository.
```bash
python git_helper.py pull
```

### 3. Full Synchronization  
Pull remote changes first, then commit and push any local changes.
```bash
python git_helper.py sync
```

## Examples

### Daily Development Workflow
```bash
# Start work: sync with remote
python git_helper.py sync

# Make changes, then commit and push
python git_helper.py "Implement new trading strategy"

# End of day: final sync to ensure everything is up to date
python git_helper.py sync
```

### Collaboration Workflow
```bash
# Before starting work
python git_helper.py pull

# After making changes
python git_helper.py "Add Sprint 12 backtest results"

# Before ending work session
python git_helper.py sync
```

### Sprint Completion Workflow
```bash
# Complete sprint work
python git_helper.py "Complete Sprint 12 - Enhanced Multi-Factor Strategy"

# Ensure everything is synchronized
python git_helper.py sync
```

## Features

### Automatic Repository Creation
If the GitHub repository doesn't exist, the system will automatically create it on first push.

### Smart Commit Messages
All commits include:
- Custom message or automatic timestamp
- Claude Code attribution
- Co-authorship credit

### Credential Management
- Credentials loaded automatically from `.env` file
- Git configured automatically with proper authentication
- No need to enter credentials repeatedly

### Error Handling
- Automatic retry logic for common failures
- Repository creation on push failures
- Conflict resolution strategies for sync operations

### Caching and Performance
- Git credentials cached for session
- Efficient API usage
- Minimal network calls

## Troubleshooting

### Repository Not Found
The automation will automatically create the repository if it doesn't exist.

### Authentication Errors
Verify that:
1. `GITHUB_USERNAME` and `GITHUB_TOKEN` are set in `.env`
2. Personal access token has proper permissions (repo, contents, metadata)
3. Token has not expired

### Merge Conflicts
Use `force-sync` command to automatically resolve conflicts:
```bash
python github_automation.py force-sync
```

### Permission Errors
Ensure your GitHub token has these permissions:
- repo (Full control of private repositories)
- workflow (Update GitHub Action workflows)
- write:packages (Upload packages to GitHub Package Registry)

## Security

- Credentials stored in `.env` file (not committed to repository)
- Tokens use HTTPS authentication
- No credentials stored in git history
- Local credential caching only

## Advanced Usage

### Custom Scripts
The `GitHubAutomation` class can be imported and used in custom Python scripts:

```python
from git_helper import GitHubAutomation

gh = GitHubAutomation()
gh.create_and_push_commit("Custom commit message")
gh.sync_repository()
```

### Batch Operations
Multiple commands can be chained:
```bash
python git_helper.py pull && python git_helper.py "Batch update with latest changes" && python git_helper.py sync
```

## Integration with Operation Badger

### Sprint Management
Each sprint completion should use descriptive commit messages:
```bash
python git_helper.py "Complete Sprint 12 - Enhanced Multi-Factor Strategy with Risk Management"
```

### Result Archiving
Results are automatically detected and included in commits when using sync.

### Regular Synchronization
Use sync frequently to keep the repository up to date:
```bash
python git_helper.py sync
```

## Maintenance

The automation system is self-maintaining and includes:
- Automatic dependency installation
- Error recovery mechanisms
- Logging and status reporting
- Cross-platform compatibility

For issues or enhancements, the system is fully open-source and can be modified as needed.
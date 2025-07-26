# GitHub Automation Guide - Operation Badger

This guide explains how to use the automated GitHub system for Operation Badger project management.

## Overview

The GitHub automation system provides simple commands to handle all common Git/GitHub operations without needing to remember complex git commands or manage credentials manually.

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

### Basic Usage

**Windows Users:**
```batch
github.bat <command>
```

**All Users:**
```bash
python github_automation.py <command>
```

### Available Commands

#### `status`
Check the current repository status and see which files have been modified.
```bash
python github_automation.py status
```

#### `commit [message]`
Stage all changes, create a commit, and push to GitHub. Automatically creates the repository if it doesn't exist.
```bash
python github_automation.py commit "Your commit message"
python github_automation.py commit  # Uses automatic timestamp message
```

#### `pull`
Pull the latest changes from the remote repository.
```bash
python github_automation.py pull
```

#### `sync`
Full synchronization: pull remote changes first, then commit and push any local changes.
```bash
python github_automation.py sync
```

#### `force-sync`
Force synchronization with automatic conflict resolution using rebase/merge strategies.
```bash
python github_automation.py force-sync
```

#### `history [count]`
Show recent commit history (default: 10 commits).
```bash
python github_automation.py history
python github_automation.py history 20
```

#### `sprint <number>`
Create a specialized commit for sprint completion with automatic result file detection.
```bash
python github_automation.py sprint 11
```

#### `tag <version> <description>`
Create and push a release tag.
```bash
python github_automation.py tag v1.0.0 "Sprint 11 Release - First Valid Multi-Factor Strategy"
```

## Examples

### Daily Development Workflow
```bash
# Check what's changed
python github_automation.py status

# Commit and push changes
python github_automation.py commit "Implement new trading strategy"

# Sync with remote (pull first, then push any changes)
python github_automation.py sync
```

### Sprint Completion Workflow
```bash
# Complete a sprint with specialized commit
python github_automation.py sprint 11

# Create a release tag for the sprint
python github_automation.py tag v11.0 "Sprint 11 - PIT Multi-Factor Strategy Complete"
```

### Collaboration Workflow
```bash
# Start work: sync with remote
python github_automation.py sync

# During work: commit frequently
python github_automation.py commit "Work in progress on feature X"

# End work: final sync
python github_automation.py sync
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
from github_automation import GitHubAutomation

gh = GitHubAutomation()
gh.create_and_push_commit("Custom commit message")
gh.sync_repository()
```

### Batch Operations
Multiple commands can be chained:
```bash
python github_automation.py status && python github_automation.py commit "Batch update" && python github_automation.py sync
```

## Integration with Operation Badger

### Sprint Management
Each sprint completion should use the sprint command:
```bash
python github_automation.py sprint 11
```

### Result Archiving
Results are automatically detected and included in sprint commits.

### Release Management
Major milestones should be tagged:
```bash
python github_automation.py tag v11.0 "First Valid Multi-Factor Strategy"
```

## Maintenance

The automation system is self-maintaining and includes:
- Automatic dependency installation
- Error recovery mechanisms
- Logging and status reporting
- Cross-platform compatibility

For issues or enhancements, the system is fully open-source and can be modified as needed.
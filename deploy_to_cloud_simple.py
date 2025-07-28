#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Operation Badger - Simple Cloud Deployment (Per Official Directive)
Follows the exact steps from the infrastructure directive

Usage:
    python deploy_to_cloud_simple.py
"""

import subprocess
import sys
import os
from datetime import datetime

# Import cloud configuration
try:
    from cloud_config import PROJECT_ID, LOCATION, REPO_NAME, IMAGE_NAME, TAG, RESULTS_BUCKET_SUFFIX
except ImportError:
    # Fallback to hardcoded values if config not found
    PROJECT_ID = "operation-badger-quant"
    LOCATION = "us-central1"
    REPO_NAME = "badger-containers"
    IMAGE_NAME = "backtester"
    TAG = "latest"
    RESULTS_BUCKET_SUFFIX = "-results"

def run_command(command, description=""):
    """Run a shell command and handle errors"""
    print(f"\n[*] {description}")
    print(f"$ {command}")
    
    try:
        # Use Windows cmd for better compatibility
        if os.name == 'nt':
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace',
                executable='cmd.exe'
            )
        else:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"[+] Success")
            if result.stdout.strip():
                print(result.stdout.strip())
            return True
        else:
            print(f"[-] Failed")
            if result.stderr.strip():
                print(f"Error: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"[-] Exception: {str(e)}")
        return False

def main():
    print("Operation Badger - Cloud Deployment")
    print("=" * 60)
    print("Following the official infrastructure directive")
    print("=" * 60)
    
    # Step 1: Verify prerequisites
    print("\nSTEP 1: Checking prerequisites...")
    
    if not run_command("docker --version", "Checking Docker"):
        print("[-] Docker is not installed. Please install Docker Desktop.")
        sys.exit(1)
    
    if not run_command("gcloud --version | head -1", "Checking gcloud CLI"):
        print("[-] gcloud CLI is not installed. Please install Google Cloud SDK.")
        sys.exit(1)
    
    # Step 2: Set project
    print(f"\nSTEP 2: Setting project to {PROJECT_ID}...")
    
    if not run_command(f"gcloud config set project {PROJECT_ID}", "Setting default project"):
        print("[-] Failed to set project. Make sure you have access to this project.")
        sys.exit(1)
    
    # Step 3: Enable APIs
    print("\nSTEP 3: Enabling required APIs...")
    
    apis = ["compute.googleapis.com", "artifactregistry.googleapis.com", "storage.googleapis.com"]
    for api in apis:
        run_command(f"gcloud services enable {api}", f"Enabling {api}")
    
    # Step 4: Configure Docker authentication
    print("\nSTEP 4: Configuring Docker authentication...")
    
    if not run_command(f"gcloud auth configure-docker {LOCATION}-docker.pkg.dev", 
                      "Configuring Docker for Artifact Registry"):
        print("[-] Failed to configure Docker authentication")
        sys.exit(1)
    
    # Step 5: Create Artifact Registry repository (if it doesn't exist)
    print("\nSTEP 5: Creating Artifact Registry repository...")
    
    create_repo_cmd = f"""gcloud artifacts repositories create {REPO_NAME} \\
    --repository-format=docker \\
    --location={LOCATION} \\
    --description="Docker containers for Operation Badger" """
    
    run_command(create_repo_cmd, "Creating repository (may already exist)")
    
    # Step 6: Build Docker image
    print("\nSTEP 6: Building Docker image...")
    
    image_uri = f"{LOCATION}-docker.pkg.dev/{PROJECT_ID}/{REPO_NAME}/{IMAGE_NAME}:{TAG}"
    
    if not run_command(f"docker build -t {image_uri} .", "Building Docker image"):
        print("[-] Failed to build Docker image")
        sys.exit(1)
    
    # Step 7: Push to Artifact Registry
    print("\nSTEP 7: Pushing image to Artifact Registry...")
    
    if not run_command(f"docker push {image_uri}", "Pushing Docker image"):
        print("[-] Failed to push Docker image")
        sys.exit(1)
    
    # Step 8: Create GCS bucket for results
    print("\nSTEP 8: Creating GCS bucket for results...")
    
    bucket_name = f"{PROJECT_ID}{RESULTS_BUCKET_SUFFIX}"
    run_command(f"gsutil mb -p {PROJECT_ID} gs://{bucket_name}", 
                f"Creating bucket gs://{bucket_name} (may already exist)")
    
    # Step 9: Verify deployment
    print("\nSTEP 9: Verifying deployment...")
    
    if run_command(f"gcloud artifacts docker images list {LOCATION}-docker.pkg.dev/{PROJECT_ID}/{REPO_NAME}", 
                   "Listing images in Artifact Registry"):
        print(f"\n[+] Image successfully deployed: {image_uri}")
    
    # Final instructions
    print("\n" + "=" * 60)
    print("[+] DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print("\nYour container is now available in the cloud at:")
    print(f"  {image_uri}")
    print("\nTo run the parallel backtest:")
    print(f"  python cloud_orchestrator_simple.py --bucket {bucket_name}")
    print("\nTo run a test with 10 stocks first:")
    print(f"  python cloud_orchestrator_simple.py --bucket {bucket_name} --test-run")
    print("\nIMPORTANT: The backtest scripts have been modified to:")
    print("  1. Accept --ticker argument for single stock backtests")
    print("  2. Save results directly to Google Cloud Storage")
    print("\nVMs will automatically delete themselves after completion to save costs.")

if __name__ == '__main__':
    main()
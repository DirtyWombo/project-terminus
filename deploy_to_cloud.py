#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Operation Badger - Cloud Deployment Script
Builds and deploys the Docker image to Google Container Registry

This script:
1. Builds the Docker image locally
2. Tags it for Google Container Registry  
3. Pushes it to GCR
4. Verifies deployment
5. Optionally runs a test orchestration

Usage:
    python deploy_to_cloud.py --project-id your-project-id
"""

import argparse
import subprocess
import sys
import os
from datetime import datetime

def run_command(command, description=""):
    """Run a shell command and handle errors"""
    print(f"🔧 {description}")
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Success: {description}")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Failed: {description}")
            print(f"Error: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during: {description}")
        print(f"Error: {str(e)}")
        return False

def check_prerequisites():
    """Check if required tools are installed"""
    print("🔍 Checking prerequisites...")
    
    required_tools = [
        ('docker', 'docker --version'),
        ('gcloud', 'gcloud --version'),
    ]
    
    all_good = True
    for tool, command in required_tools:
        if not run_command(command, f"Checking {tool}"):
            print(f"❌ {tool} is not installed or not in PATH")
            all_good = False
    
    return all_good

def authenticate_gcloud():
    """Ensure gcloud is authenticated"""
    print("🔐 Configuring Google Cloud authentication...")
    
    # Configure Docker to use gcloud as credential helper
    if not run_command('gcloud auth configure-docker', 'Configuring Docker for GCR'):
        return False
    
    # Check if user is authenticated
    if not run_command('gcloud auth list', 'Checking authentication'):
        print("❌ Please run 'gcloud auth login' first")
        return False
    
    return True

def build_docker_image(project_id, tag='latest'):
    """Build the Docker image"""
    image_name = f"gcr.io/{project_id}/operation-badger:{tag}"
    
    print(f"🐳 Building Docker image: {image_name}")
    
    # Build the image
    build_command = f"docker build -t {image_name} ."
    if not run_command(build_command, f"Building Docker image"):
        return None
    
    return image_name

def push_docker_image(image_name):
    """Push the Docker image to Google Container Registry"""
    print(f"📤 Pushing Docker image to GCR...")
    
    push_command = f"docker push {image_name}"
    if not run_command(push_command, f"Pushing image to GCR"):
        return False
    
    return True

def verify_deployment(project_id, tag='latest'):
    """Verify the image is available in GCR"""
    print("✅ Verifying deployment...")
    
    image_name = f"gcr.io/{project_id}/operation-badger:{tag}"
    list_command = f"gcloud container images list-tags gcr.io/{project_id}/operation-badger"
    
    if run_command(list_command, "Listing container images"):
        print(f"✅ Image {image_name} successfully deployed to GCR")
        return True
    else:
        print(f"❌ Failed to verify image deployment")
        return False

def create_gcs_bucket(project_id, bucket_name):
    """Create Google Cloud Storage bucket for results"""
    print(f"🪣 Creating GCS bucket: {bucket_name}")
    
    # Check if bucket already exists
    check_command = f"gsutil ls gs://{bucket_name}"
    if run_command(check_command, "Checking if bucket exists"):
        print(f"✅ Bucket {bucket_name} already exists")
        return True
    
    # Create the bucket
    create_command = f"gsutil mb -p {project_id} gs://{bucket_name}"
    if run_command(create_command, f"Creating bucket {bucket_name}"):
        print(f"✅ Bucket {bucket_name} created successfully")
        return True
    
    return False

def setup_universe_file():
    """Ensure the universe file exists for cloud processing"""
    universe_file = 'data/sprint_12/curated_sp500_universe.txt'
    
    if os.path.exists(universe_file):
        print(f"✅ Universe file found: {universe_file}")
        return True
    
    print(f"📝 Creating universe file: {universe_file}")
    
    # Create directories if needed
    os.makedirs(os.path.dirname(universe_file), exist_ok=True)
    
    # Create a representative S&P 500 universe
    sample_universe = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'BRK-B',
        'UNH', 'JNJ', 'JPM', 'V', 'PG', 'HD', 'MA', 'CVX', 'LLY', 'ABBV',
        'PFE', 'KO', 'AVGO', 'PEP', 'TMO', 'COST', 'WMT', 'MRK', 'BAC',
        'DIS', 'ABT', 'DHR', 'VZ', 'ADBE', 'NKE', 'NEE', 'CRM', 'TXN',
        'ACN', 'LIN', 'ORCL', 'MDT', 'BMY', 'HON', 'QCOM', 'PM', 'RTX',
        'NFLX', 'UPS', 'T', 'LOW', 'IBM', 'SPGI', 'INTU', 'GS', 'BLK',
        'AMD', 'CAT', 'BKNG', 'AMGN', 'DE', 'AXP', 'GILD', 'MU', 'MDLZ',
        'TJX', 'ISRG', 'NOW', 'SYK', 'ZTS', 'ADP', 'MMM', 'TMUS', 'CI',
        'MO', 'CSX', 'PYPL', 'SBUX', 'DUK', 'SO', 'PLD', 'AON', 'CB',
        'ICE', 'USB', 'GE', 'TGT', 'COP', 'NSC', 'BSX', 'FIS', 'CME'
    ]
    
    try:
        with open(universe_file, 'w') as f:
            f.write("# S&P 500 Universe for Operation Badger\n")
            f.write("# Created for cloud parallel processing\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("\n")
            for ticker in sample_universe:
                f.write(f"{ticker}\n")
        
        print(f"✅ Created universe file with {len(sample_universe)} stocks")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create universe file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Deploy Operation Badger to Google Cloud')
    parser.add_argument('--project-id', required=True, help='Google Cloud Project ID')
    parser.add_argument('--bucket-name', help='GCS bucket name (defaults to project-id-badger-results)')
    parser.add_argument('--tag', default='latest', help='Docker image tag')
    parser.add_argument('--skip-build', action='store_true', help='Skip Docker build step')
    parser.add_argument('--test-run', action='store_true', help='Run a test orchestration after deployment')
    
    args = parser.parse_args()
    
    # Default bucket name
    if not args.bucket_name:
        args.bucket_name = f"{args.project_id}-badger-results"
    
    print("🚀 Operation Badger - Cloud Deployment")
    print("="*60)
    print(f"Project ID: {args.project_id}")
    print(f"Bucket: {args.bucket_name}")
    print(f"Tag: {args.tag}")
    print("="*60)
    
    # Check prerequisites
    if not check_prerequisites():
        print("❌ Prerequisites not met. Please install Docker and gcloud CLI.")
        sys.exit(1)
    
    # Authenticate
    if not authenticate_gcloud():
        print("❌ Authentication failed")
        sys.exit(1)
    
    # Setup universe file
    if not setup_universe_file():
        print("❌ Failed to setup universe file")
        sys.exit(1)
    
    # Build and push Docker image
    if not args.skip_build:
        image_name = build_docker_image(args.project_id, args.tag)
        if not image_name:
            print("❌ Docker build failed")
            sys.exit(1)
        
        if not push_docker_image(image_name):
            print("❌ Docker push failed")
            sys.exit(1)
        
        if not verify_deployment(args.project_id, args.tag):
            print("❌ Deployment verification failed")
            sys.exit(1)
    else:
        print("⏭️  Skipping Docker build step")
    
    # Create GCS bucket
    if not create_gcs_bucket(args.project_id, args.bucket_name):
        print("❌ Failed to create GCS bucket")
        sys.exit(1)
    
    print("\n🎉 Deployment completed successfully!")
    print("\nNext steps:")
    print(f"1. Run orchestrator: python cloud_orchestrator.py --project-id {args.project_id} --bucket-name {args.bucket_name}")
    print("2. Monitor progress in Google Cloud Console")
    print("3. Review aggregated results when complete")
    
    # Optional test run
    if args.test_run:
        print("\n🧪 Running test orchestration...")
        test_command = f"python cloud_orchestrator.py --project-id {args.project_id} --bucket-name {args.bucket_name} --num-workers 2 --dry-run"
        run_command(test_command, "Test orchestration (dry run)")

if __name__ == '__main__':
    main()
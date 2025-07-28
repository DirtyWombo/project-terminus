#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Operation Badger - Cloud Setup Verification
Quick script to verify your GCP environment is correctly configured
"""

import subprocess
import sys
from cloud_config import PROJECT_ID, IMAGE_URI, LOCATION, REPO_NAME

def check_command(command, description, required=True):
    """Run a command and check if it succeeds"""
    print(f"\n🔍 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Success")
            if result.stdout.strip():
                print(f"   {result.stdout.strip()[:100]}")
            return True
        else:
            if required:
                print(f"❌ Failed")
                if result.stderr.strip():
                    print(f"   Error: {result.stderr.strip()[:200]}")
            else:
                print(f"⚠️  Not found (optional)")
            return False
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def main():
    print(f"🚀 Operation Badger - Cloud Setup Verification")
    print("=" * 60)
    print(f"Project ID: {PROJECT_ID}")
    print(f"Image URI: {IMAGE_URI}")
    print("=" * 60)
    
    all_good = True
    
    # Check gcloud CLI
    if not check_command("gcloud --version | head -1", "Checking gcloud CLI"):
        print("\n❌ Please install gcloud CLI")
        all_good = False
    
    # Check current project
    print(f"\n🔍 Checking current project...")
    result = subprocess.run("gcloud config get-value project", shell=True, capture_output=True, text=True)
    current_project = result.stdout.strip()
    if current_project == PROJECT_ID:
        print(f"✅ Current project is correct: {current_project}")
    else:
        print(f"⚠️  Current project is: {current_project}")
        print(f"   Expected: {PROJECT_ID}")
        print(f"   Run: gcloud config set project {PROJECT_ID}")
        all_good = False
    
    # Check authentication
    if not check_command("gcloud auth list --filter=status:ACTIVE --format='value(account)'", 
                        "Checking authentication"):
        print("\n❌ Not authenticated. Run: gcloud auth login")
        all_good = False
    
    # Check if project exists
    if not check_command(f"gcloud projects describe {PROJECT_ID} --format='value(name)'", 
                        f"Checking if project '{PROJECT_ID}' exists"):
        print(f"\n❌ Project '{PROJECT_ID}' not found")
        print("   Run: python setup_gcp_project.py")
        all_good = False
    
    # Check billing
    check_command(f"gcloud beta billing projects describe {PROJECT_ID} --format='value(billingEnabled)'",
                 "Checking billing status", required=False)
    
    # Check enabled APIs
    print("\n🔍 Checking enabled APIs...")
    apis = ["compute.googleapis.com", "artifactregistry.googleapis.com", "storage.googleapis.com"]
    for api in apis:
        if not check_command(f"gcloud services list --enabled --filter='config.name:{api}' --format='value(config.name)'",
                            f"Checking {api}"):
            print(f"   Run: gcloud services enable {api}")
            all_good = False
    
    # Check Docker
    if not check_command("docker --version", "Checking Docker"):
        print("\n❌ Please install Docker Desktop")
        all_good = False
    
    # Check Artifact Registry repository
    check_command(f"gcloud artifacts repositories describe {REPO_NAME} --location={LOCATION} --format='value(name)'",
                 f"Checking Artifact Registry repository '{REPO_NAME}'", required=False)
    
    # Check for existing Docker images
    check_command(f"gcloud artifacts docker images list {LOCATION}-docker.pkg.dev/{PROJECT_ID}/{REPO_NAME} --limit=1",
                 "Checking for existing Docker images", required=False)
    
    # Check GCS bucket
    bucket_name = f"{PROJECT_ID}-results"
    check_command(f"gsutil ls gs://{bucket_name}", 
                 f"Checking GCS bucket '{bucket_name}'", required=False)
    
    # Summary
    print("\n" + "=" * 60)
    if all_good:
        print("✅ All critical checks passed!")
        print("\nNext steps:")
        print("1. Run: python deploy_to_cloud_simple.py")
        print("2. Run: python cloud_orchestrator_simple.py --bucket operation-badger-quant-results --test-run")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("\nQuick setup:")
        print("1. Run: python setup_gcp_project.py")
        print("2. Link billing in the GCP Console")
        print("3. Run this verification again")
    
    print("=" * 60)

if __name__ == '__main__':
    main()
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Operation Badger - GCP Project Setup Script
Helps set up the correct Google Cloud project for Sprint 13

This script guides you through:
1. Creating the operation-badger-quant project
2. Setting it as default
3. Enabling required APIs
4. Verifying the setup
"""

import subprocess
import sys
import time

def run_command(command, description="", check_success=True):
    """Run a shell command and handle output"""
    print(f"\n🔧 {description}")
    print(f"$ {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Success")
            if result.stdout.strip():
                print(result.stdout.strip())
            return True, result.stdout
        else:
            if check_success:
                print("❌ Failed")
                if result.stderr.strip():
                    print(f"Error: {result.stderr.strip()}")
            return False, result.stderr
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False, str(e)

def main():
    print("🚀 Operation Badger - GCP Project Setup")
    print("=" * 60)
    print("This script will help you set up the correct GCP project")
    print("Project ID: operation-badger-quant")
    print("=" * 60)
    
    # Step 1: Check if gcloud is installed
    print("\n📋 STEP 1: Checking gcloud CLI...")
    success, _ = run_command("gcloud --version | head -1", "Checking if gcloud is installed")
    
    if not success:
        print("\n❌ gcloud CLI is not installed!")
        print("Please install it from: https://cloud.google.com/sdk/docs/install")
        sys.exit(1)
    
    # Step 2: Check authentication
    print("\n📋 STEP 2: Checking authentication...")
    success, output = run_command("gcloud auth list --filter=status:ACTIVE --format='value(account)'", 
                                 "Checking active account")
    
    if not success or not output.strip():
        print("\n⚠️  You are not logged in to gcloud")
        print("Please run: gcloud auth login")
        sys.exit(1)
    else:
        print(f"Logged in as: {output.strip()}")
    
    # Step 3: Check if project already exists
    print("\n📋 STEP 3: Checking if project already exists...")
    success, _ = run_command("gcloud projects describe operation-badger-quant", 
                            "Checking for existing project", check_success=False)
    
    if success:
        print("✅ Project 'operation-badger-quant' already exists!")
        use_existing = input("\nDo you want to use the existing project? (yes/no): ").lower()
        if use_existing != 'yes':
            print("Please delete the existing project first or choose a different project ID")
            sys.exit(1)
    else:
        # Step 4: Create the project
        print("\n📋 STEP 4: Creating new project...")
        create_project = input("\nDo you want to create project 'operation-badger-quant'? (yes/no): ").lower()
        
        if create_project == 'yes':
            success, _ = run_command(
                'gcloud projects create operation-badger-quant --name="Operation Badger"',
                "Creating new project"
            )
            
            if not success:
                print("\n❌ Failed to create project")
                print("Possible reasons:")
                print("- Project ID already taken by another organization")
                print("- You don't have permission to create projects")
                print("- Billing account restrictions")
                sys.exit(1)
            
            print("\n⏳ Waiting for project to be ready...")
            time.sleep(5)
        else:
            print("Setup cancelled")
            sys.exit(0)
    
    # Step 5: Set as default project
    print("\n📋 STEP 5: Setting as default project...")
    success, _ = run_command("gcloud config set project operation-badger-quant", 
                            "Setting default project")
    
    if not success:
        print("❌ Failed to set default project")
        sys.exit(1)
    
    # Step 6: Check billing
    print("\n📋 STEP 6: Checking billing account...")
    success, output = run_command(
        "gcloud beta billing projects describe operation-badger-quant --format='value(billingAccountName)'",
        "Checking billing status", check_success=False
    )
    
    if not success or not output.strip():
        print("\n⚠️  WARNING: No billing account linked!")
        print("\nTo link billing:")
        print("1. Go to: https://console.cloud.google.com")
        print("2. Select 'Operation Badger' project")
        print("3. Navigate to Billing")
        print("4. Click 'Link a billing account'")
        print("\nPress Enter to continue after linking billing...")
        input()
    else:
        print(f"✅ Billing account linked: {output.strip()}")
    
    # Step 7: Enable APIs
    print("\n📋 STEP 7: Enabling required APIs...")
    print("This may take a few minutes...")
    
    apis = [
        ("compute.googleapis.com", "Compute Engine API"),
        ("artifactregistry.googleapis.com", "Artifact Registry API"),
        ("storage.googleapis.com", "Cloud Storage API")
    ]
    
    all_success = True
    for api, name in apis:
        success, _ = run_command(f"gcloud services enable {api}", f"Enabling {name}")
        if not success:
            all_success = False
            print(f"⚠️  Failed to enable {name}")
    
    if not all_success:
        print("\n⚠️  Some APIs failed to enable. They may already be enabled or require billing.")
    
    # Step 8: Final verification
    print("\n📋 STEP 8: Final verification...")
    
    # Verify project
    success, output = run_command("gcloud config get-value project", "Current project")
    if output.strip() == "operation-badger-quant":
        print("✅ Project is set correctly")
    else:
        print("❌ Project is not set correctly")
    
    # Verify enabled APIs
    print("\nChecking enabled APIs...")
    success, output = run_command(
        "gcloud services list --enabled --filter='config.name:(compute OR artifactregistry OR storage)' --format='value(config.name)'",
        "Listing enabled APIs"
    )
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SETUP SUMMARY")
    print("=" * 60)
    print(f"Project ID: operation-badger-quant")
    print(f"Project Name: Operation Badger")
    print("\nNext steps:")
    print("1. Ensure billing is linked (check warnings above)")
    print("2. Run: python deploy_to_cloud_simple.py")
    print("3. Run: python cloud_orchestrator_simple.py --bucket operation-badger-quant-results --test-run")
    print("\n✅ GCP project setup is complete!")

if __name__ == '__main__':
    main()
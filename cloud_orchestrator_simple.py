#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Operation Badger - Simple Cloud Orchestrator (Per Official Directive)
One VM per ticker for maximum fault isolation and simplicity

This implementation follows the official directive for Sprint 13:
- One VM per ticker (216 VMs for full S&P 500)
- Fire-and-forget approach with auto-delete
- Container-Optimized OS
- e2-medium instances for cost efficiency
"""

import google.cloud.compute_v1 as compute_v1
import os
import time

# Import cloud configuration
try:
    from cloud_config import PROJECT_ID, ZONE, IMAGE_URI, MACHINE_TYPE, SERVICE_ACCOUNT, COS_IMAGE
except ImportError:
    # Fallback to hardcoded values if config not found
    PROJECT_ID = "operation-badger-quant"
    ZONE = "us-central1-a"
    IMAGE_URI = "us-central1-docker.pkg.dev/operation-badger-quant/badger-containers/backtester:latest"
    MACHINE_TYPE = "e2-medium"
    SERVICE_ACCOUNT = "default"
    COS_IMAGE = "projects/cos-cloud/global/images/cos-stable-101-17162-40-55"

def load_sp500_universe():
    """Load the S&P 500 universe from file"""
    universe_file = 'data/sprint_12/curated_sp500_universe.txt'
    universe = []
    
    if os.path.exists(universe_file):
        with open(universe_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    universe.append(line)
    else:
        # Use the example from the directive if file not found
        print("Warning: Using example universe. Create curated_sp500_universe.txt for full S&P 500")
        universe = ['CRWD', 'SNOW', 'PLTR', 'U', 'RBLX', 'NET', 'DDOG', 'MDB', 'OKTA', 'ZS']
    
    return universe

def run_parallel_backtests(bucket_name, universe=None, rebalance_freq='biweekly'):
    """
    Launches a separate GCE VM for each ticker to run a backtest in parallel.
    """
    instance_client = compute_v1.InstancesClient()
    
    # Load universe if not provided
    if universe is None:
        universe = load_sp500_universe()
    
    print(f"Launching {len(universe)} VMs for parallel backtesting...")
    print(f"Rebalancing frequency: {rebalance_freq}")
    print(f"Results bucket: {bucket_name}")
    
    for ticker in universe:
        instance_name = f"backtest-worker-{ticker.lower()}-{int(time.time())}"
        print(f"Launching VM: {instance_name} for ticker: {ticker}")

        # This is the command the VM will run on startup.
        # It pulls the latest Docker image and executes our backtest script inside the container.
        startup_script = f"""#!/bin/bash
echo "Starting worker for {ticker}"

# Pull the Docker image
docker pull {IMAGE_URI}

# Run the backtest inside the container
# The backtest script will save results directly to GCS bucket
docker run \\
    -e GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json \\
    {IMAGE_URI} \\
    backtests/sprint_13/ticker_qvm_backtest.py \\
    --ticker {ticker} \\
    --bucket {bucket_name} \\
    --rebalance-freq {rebalance_freq}

echo "Backtest for {ticker} complete. Shutting down."

# Automatically delete the VM when done to save costs
gcloud compute instances delete {instance_name} --zone={ZONE} -q
"""

        # Define the VM instance configuration
        instance_config = {{
            "name": instance_name,
            "machine_type": f"zones/{ZONE}/machineTypes/{MACHINE_TYPE}",
            "disks": [{{
                "boot": True,
                "auto_delete": True,
                "initialize_params": {{
                    "source_image": COS_IMAGE,  # Container-Optimized OS
                }},
            }}],
            "network_interfaces": [{{
                "name": "global/networks/default",
                "access_configs": [{{"type": "ONE_TO_ONE_NAT"}}],
            }}],
            "service_accounts": [{{
                "email": SERVICE_ACCOUNT,
                "scopes": ["https://www.googleapis.com/auth/cloud-platform"],
            }}],
            "metadata": {{
                "items": [{{"key": "startup-script", "value": startup_script}}]
            }},
            "tags": {{
                "items": ["operation-badger", f"ticker-{ticker.lower()}"]
            }}
        }}

        # Create and start the VM instance
        operation = instance_client.insert(project=PROJECT_ID, zone=ZONE, instance_resource=instance_config)
        # We don't wait for it to finish, we just launch the next one. This is the parallel part.

    print(f"\nSuccessfully launched {len(universe)} backtest workers.")
    print("\nVMs will run their backtests and auto-delete when complete.")
    print(f"Monitor progress in GCP Console: https://console.cloud.google.com/compute/instances?project={PROJECT_ID}")
    print(f"Results will appear in: gs://{bucket_name}/sprint13_results/")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Operation Badger Simple Cloud Orchestrator')
    parser.add_argument('--bucket', required=True, help='GCS bucket name for results')
    parser.add_argument('--rebalance-freq', default='biweekly', 
                       choices=['weekly', 'biweekly', 'monthly'], 
                       help='Rebalancing frequency (default: biweekly)')
    parser.add_argument('--test-run', action='store_true', 
                       help='Run with 10-stock test universe instead of full S&P 500')
    
    args = parser.parse_args()
    
    # Use test universe if specified
    test_universe = None
    if args.test_run:
        test_universe = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'JNJ', 'V']
        print("TEST MODE: Using 10-stock universe")
    
    # Run the orchestrator
    run_parallel_backtests(args.bucket, test_universe, args.rebalance_freq)
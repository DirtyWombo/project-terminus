#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Operation Badger - Cloud Orchestrator
Google Cloud Platform Parallel Backtest Orchestrator

This script launches multiple Google Cloud VMs in parallel to execute
the Sprint 13 backtest across the full S&P 500 universe.

Each VM processes a subset of stocks and uploads results to Google Cloud Storage.
Results are then aggregated for comprehensive analysis.

Usage:
    python cloud_orchestrator.py --project-id your-project-id --bucket-name your-bucket
"""

import argparse
import time
import json
import os
from datetime import datetime
from google.cloud import compute_v1
from google.cloud import storage
import concurrent.futures
import subprocess

class CloudOrchestrator:
    """
    Manages parallel execution of backtests across Google Cloud VMs
    """
    
    def __init__(self, project_id, zone='us-central1-a'):
        self.project_id = project_id
        self.zone = zone
        self.compute_client = compute_v1.InstancesClient()
        self.storage_client = storage.Client()
        
        # Configuration
        self.vm_config = {
            'machine_type': 'n1-standard-2',  # 2 vCPUs, 7.5GB RAM
            'disk_size_gb': 20,
            'image_family': 'ubuntu-2004-lts',
            'image_project': 'ubuntu-os-cloud'
        }
        
        self.docker_image = f"gcr.io/{project_id}/operation-badger:latest"
        
    def create_startup_script(self, worker_id, start_idx, end_idx, bucket_name, rebalance_freq='biweekly'):
        """Generate startup script for VM instances"""
        
        return f"""#!/bin/bash
# Operation Badger Cloud Worker Startup Script
# Worker ID: {worker_id}
# Processing stocks {start_idx}-{end_idx}

set -e

# Install Docker
apt-get update
apt-get install -y docker.io

# Start Docker service
systemctl start docker
systemctl enable docker

# Authenticate with Google Container Registry
gcloud auth configure-docker

# Pull the Operation Badger Docker image
docker pull {self.docker_image}

# Create local results directory
mkdir -p /tmp/results

# Run the backtest container
docker run --rm \\
    -v /tmp/results:/app/results \\
    -e GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json \\
    {self.docker_image} \\
    backtests/sprint_13/cloud_qvm_backtest.py \\
    --start-idx {start_idx} \\
    --end-idx {end_idx} \\
    --worker-id {worker_id} \\
    --rebalance-freq {rebalance_freq} \\
    --bucket {bucket_name}

# Signal completion
echo "Worker {worker_id} completed successfully" > /tmp/completion_marker.txt

# Upload completion marker
gsutil cp /tmp/completion_marker.txt gs://{bucket_name}/completion_markers/worker_{worker_id}_complete.txt

# Shutdown the VM after completion
shutdown -h now
"""

    def create_vm_instance(self, worker_id, start_idx, end_idx, bucket_name, rebalance_freq='biweekly'):
        """Create a new VM instance for parallel processing"""
        
        instance_name = f"badger-worker-{worker_id}"
        
        startup_script = self.create_startup_script(worker_id, start_idx, end_idx, bucket_name, rebalance_freq)
        
        # VM configuration
        config = {
            'name': instance_name,
            'machine_type': f"zones/{self.zone}/machineTypes/{self.vm_config['machine_type']}",
            'disks': [
                {
                    'boot': True,
                    'auto_delete': True,
                    'initialize_params': {
                        'source_image': f"projects/{self.vm_config['image_project']}/global/images/family/{self.vm_config['image_family']}",
                        'disk_size_gb': str(self.vm_config['disk_size_gb'])
                    }
                }
            ],
            'network_interfaces': [
                {
                    'network': 'global/networks/default',
                    'access_configs': [
                        {
                            'type': 'ONE_TO_ONE_NAT',
                            'name': 'External NAT'
                        }
                    ]
                }
            ],
            'metadata': {
                'items': [
                    {
                        'key': 'startup-script',
                        'value': startup_script
                    }
                ]
            },
            'service_accounts': [
                {
                    'email': 'default',
                    'scopes': [
                        'https://www.googleapis.com/auth/cloud-platform'
                    ]
                }
            ],
            'tags': {
                'items': ['operation-badger', 'backtest-worker']
            }
        }
        
        print(f"Creating VM {instance_name} for stocks {start_idx}-{end_idx}...")
        
        operation = self.compute_client.insert(
            project=self.project_id,
            zone=self.zone,
            instance_resource=config
        )
        
        return {
            'worker_id': worker_id,
            'instance_name': instance_name,
            'operation': operation,
            'start_idx': start_idx,
            'end_idx': end_idx
        }

    def wait_for_operation(self, operation):
        """Wait for a compute operation to complete"""
        while True:
            result = self.compute_client.get(
                project=self.project_id,
                zone=self.zone,
                instance=operation['instance_name']
            )
            
            if result.status == 'RUNNING':
                break
            elif result.status in ['TERMINATED', 'STOPPED']:
                raise Exception(f"VM {operation['instance_name']} failed to start properly")
            
            time.sleep(10)
        
        print(f"VM {operation['instance_name']} is now running")

    def load_universe(self, universe_file='data/sprint_12/curated_sp500_universe.txt'):
        """Load the S&P 500 universe for parallel processing"""
        universe = []
        
        if os.path.exists(universe_file):
            with open(universe_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        universe.append(line)
        else:
            # Fallback - create a representative universe
            print(f"Universe file {universe_file} not found, using fallback universe")
            universe = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'BRK-B',
                'UNH', 'JNJ', 'JPM', 'V', 'PG', 'HD', 'MA', 'CVX', 'LLY', 'ABBV',
                'PFE', 'KO', 'AVGO', 'PEP', 'TMO', 'COST', 'WMT', 'MRK', 'BAC',
                'DIS', 'ABT', 'DHR', 'VZ', 'ADBE', 'NKE', 'NEE', 'CRM', 'TXN'
            ]
        
        return universe

    def split_universe(self, universe, num_workers=8):
        """Split the universe into chunks for parallel processing"""
        chunk_size = len(universe) // num_workers
        chunks = []
        
        for i in range(num_workers):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size
            
            # Last worker gets any remaining stocks
            if i == num_workers - 1:
                end_idx = len(universe)
            
            chunks.append({
                'worker_id': f"w{i+1:02d}",
                'start_idx': start_idx,
                'end_idx': end_idx,
                'stocks': universe[start_idx:end_idx]
            })
        
        return chunks

    def monitor_completion(self, bucket_name, worker_ids, timeout_minutes=60):
        """Monitor worker completion by checking GCS markers"""
        print(f"\nMonitoring {len(worker_ids)} workers for completion...")
        
        start_time = time.time()
        completed_workers = set()
        
        while len(completed_workers) < len(worker_ids):
            for worker_id in worker_ids:
                if worker_id not in completed_workers:
                    marker_path = f"completion_markers/worker_{worker_id}_complete.txt"
                    
                    try:
                        bucket = self.storage_client.bucket(bucket_name)
                        blob = bucket.blob(marker_path)
                        
                        if blob.exists():
                            completed_workers.add(worker_id)
                            print(f"✅ Worker {worker_id} completed")
                    except Exception:
                        pass  # Marker doesn't exist yet
            
            # Check timeout
            elapsed_minutes = (time.time() - start_time) / 60
            if elapsed_minutes > timeout_minutes:
                print(f"⚠️  Timeout reached ({timeout_minutes} minutes)")
                break
            
            if len(completed_workers) < len(worker_ids):
                remaining = len(worker_ids) - len(completed_workers)
                print(f"⏳ Waiting for {remaining} workers... ({elapsed_minutes:.1f}min elapsed)")
                time.sleep(30)
        
        return completed_workers

    def cleanup_vms(self, instance_names):
        """Clean up VM instances after completion"""
        print("\nCleaning up VM instances...")
        
        for instance_name in instance_names:
            try:
                print(f"Deleting {instance_name}...")
                self.compute_client.delete(
                    project=self.project_id,
                    zone=self.zone,
                    instance=instance_name
                )
            except Exception as e:
                print(f"Failed to delete {instance_name}: {e}")

    def aggregate_results(self, bucket_name):
        """Download and aggregate results from all workers"""
        print("\nAggregating results from all workers...")
        
        bucket = self.storage_client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix='sprint13_results/')
        
        all_results = []
        for blob in blobs:
            if blob.name.endswith('.json'):
                try:
                    content = blob.download_as_text()
                    result = json.loads(content)
                    all_results.append(result)
                    print(f"📥 Downloaded: {blob.name}")
                except Exception as e:
                    print(f"Failed to download {blob.name}: {e}")
        
        if all_results:
            # Create aggregated summary
            summary = {
                'orchestration_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_workers': len(all_results),
                'individual_results': all_results,
                'aggregated_metrics': self.calculate_aggregate_metrics(all_results)
            }
            
            # Save aggregated results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = f'sprint13_cloud_aggregated_{timestamp}.json'
            
            with open(results_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            print(f"📊 Aggregated results saved to: {results_file}")
            return summary
        
        return None

    def calculate_aggregate_metrics(self, results):
        """Calculate overall metrics from individual worker results"""
        if not results:
            return {}
        
        # Calculate weighted averages and totals
        total_trades = sum(r.get('total_trades', 0) for r in results)
        total_rebalances = sum(r.get('rebalances', 0) for r in results)
        
        # Universe coverage
        total_universe_size = sum(r.get('universe_size', 0) for r in results)
        total_data_coverage = sum(r.get('data_coverage', 0) for r in results)
        
        # Performance metrics (simple average for now)
        returns = [r.get('annualized_return_pct', 0) for r in results if r.get('annualized_return_pct')]
        sharpe_ratios = [r.get('sharpe_ratio', 0) for r in results if r.get('sharpe_ratio')]
        drawdowns = [r.get('max_drawdown_pct', 0) for r in results if r.get('max_drawdown_pct')]
        
        return {
            'total_universe_size': total_universe_size,
            'total_data_coverage': total_data_coverage,
            'total_trades': total_trades,
            'total_rebalances': total_rebalances,
            'avg_annualized_return_pct': sum(returns) / len(returns) if returns else 0,
            'avg_sharpe_ratio': sum(sharpe_ratios) / len(sharpe_ratios) if sharpe_ratios else 0,
            'avg_max_drawdown_pct': sum(drawdowns) / len(drawdowns) if drawdowns else 0,
            'coverage_percentage': (total_data_coverage / total_universe_size * 100) if total_universe_size > 0 else 0
        }

def main():
    parser = argparse.ArgumentParser(description='Operation Badger Cloud Orchestrator')
    parser.add_argument('--project-id', required=True, help='Google Cloud Project ID')
    parser.add_argument('--bucket-name', required=True, help='Google Cloud Storage bucket name')
    parser.add_argument('--zone', default='us-central1-a', help='GCP zone for VMs')
    parser.add_argument('--num-workers', type=int, default=8, help='Number of parallel workers')
    parser.add_argument('--rebalance-freq', default='biweekly', choices=['weekly', 'biweekly', 'monthly'],
                       help='Rebalancing frequency')
    parser.add_argument('--dry-run', action='store_true', help='Show plan without executing')
    parser.add_argument('--cleanup-only', action='store_true', help='Only cleanup existing VMs')
    
    args = parser.parse_args()
    
    print("🚀 Operation Badger - Cloud Orchestrator")
    print("="*60)
    print(f"Project ID: {args.project_id}")
    print(f"Bucket: {args.bucket_name}")
    print(f"Zone: {args.zone}")
    print(f"Workers: {args.num_workers}")
    print(f"Rebalancing: {args.rebalance_freq}")
    print("="*60)
    
    orchestrator = CloudOrchestrator(args.project_id, args.zone)
    
    if args.cleanup_only:
        # Just cleanup existing instances
        print("Cleanup mode - removing existing badger worker VMs...")
        # This would need to be implemented based on naming convention
        return
    
    # Load and split universe
    universe = orchestrator.load_universe()
    print(f"📈 Loaded universe: {len(universe)} stocks")
    
    chunks = orchestrator.split_universe(universe, args.num_workers)
    
    print(f"\n📋 Execution Plan:")
    for chunk in chunks:
        print(f"  Worker {chunk['worker_id']}: {len(chunk['stocks'])} stocks ({chunk['start_idx']}-{chunk['end_idx']})")
    
    if args.dry_run:
        print("\n🔍 Dry run mode - no VMs will be created")
        return
    
    # Create and launch VMs
    print(f"\n🔧 Creating {len(chunks)} VM instances...")
    operations = []
    
    for chunk in chunks:
        operation = orchestrator.create_vm_instance(
            chunk['worker_id'],
            chunk['start_idx'],
            chunk['end_idx'],
            args.bucket_name,
            args.rebalance_freq
        )
        operations.append(operation)
        time.sleep(5)  # Stagger VM creation
    
    # Wait for VMs to start
    print("\n⏳ Waiting for VMs to start...")
    for operation in operations:
        orchestrator.wait_for_operation(operation)
    
    # Monitor completion
    worker_ids = [op['worker_id'] for op in operations]
    completed = orchestrator.monitor_completion(args.bucket_name, worker_ids)
    
    print(f"\n✅ {len(completed)}/{len(worker_ids)} workers completed")
    
    # Aggregate results
    summary = orchestrator.aggregate_results(args.bucket_name)
    
    if summary:
        metrics = summary['aggregated_metrics']
        print(f"\n📊 Sprint 13 Cloud Results Summary:")
        print(f"  Universe: {metrics['total_universe_size']} stocks")
        print(f"  Data Coverage: {metrics['coverage_percentage']:.1f}%")
        print(f"  Total Trades: {metrics['total_trades']}")
        print(f"  Avg Return: {metrics['avg_annualized_return_pct']:.2f}%")
        print(f"  Avg Sharpe: {metrics['avg_sharpe_ratio']:.2f}")
        print(f"  Avg Drawdown: {metrics['avg_max_drawdown_pct']:.2f}%")
    
    # Cleanup VMs
    instance_names = [op['instance_name'] for op in operations]
    orchestrator.cleanup_vms(instance_names)
    
    print("\n🎉 Cloud orchestration completed successfully!")

if __name__ == '__main__':
    main()
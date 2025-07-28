# Operation Badger - Google Cloud Infrastructure

**Sprint 13 Parallel Backtesting Platform**

This directory contains the complete cloud infrastructure for running Sprint 13 backtests at scale using Google Cloud Platform.

## 🚀 Quick Start

### 1. Prerequisites
- Google Cloud Project with billing enabled
- Docker installed locally
- Google Cloud SDK (`gcloud`) installed and authenticated
- Python environment with requirements.txt installed

### 2. Deploy to Cloud
```bash
# Deploy the infrastructure
python deploy_to_cloud.py --project-id your-project-id

# Run the parallel backtest
python cloud_orchestrator.py --project-id your-project-id --bucket-name your-project-id-badger-results
```

### 3. Monitor Results
- Check Google Cloud Console for VM status
- Monitor Google Cloud Storage for result files
- Review aggregated results in generated JSON files

## 📁 File Structure

### Core Infrastructure
- **`Dockerfile`** - Container configuration for cloud deployment
- **`cloud_orchestrator.py`** - Main orchestration script for parallel VM execution
- **`deploy_to_cloud.py`** - Deployment automation script
- **`requirements.txt`** - Updated with Google Cloud dependencies

### Backtest Scripts
- **`backtests/sprint_13/cloud_qvm_backtest.py`** - Cloud-optimized backtest worker
- **`backtests/sprint_13/composite_qvm_backtest_sp500_weekly.py`** - Local weekly backtest
- **`test_sprint13_shorter.py`** - 2-year validation test

### Configuration
- **`data/sprint_12/curated_sp500_universe.txt`** - S&P 500 stock universe (auto-generated if missing)

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Orchestrator  │───▶│   8 Cloud VMs    │───▶│  Cloud Storage  │
│                 │    │   (Parallel)     │    │   (Results)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Aggregated      │
                       │  Results         │
                       └──────────────────┘
```

### Parallel Execution Strategy
1. **Universe Splitting**: 216 S&P 500 stocks divided across 8 workers
2. **VM Deployment**: Each worker runs on dedicated n1-standard-2 VM
3. **Result Collection**: Individual results uploaded to Google Cloud Storage
4. **Aggregation**: Combined analysis of all worker results

## ⚙️ Configuration Options

### Rebalancing Frequency
```bash
# Weekly rebalancing (high computational load)
--rebalance-freq weekly

# Bi-weekly rebalancing (recommended)
--rebalance-freq biweekly

# Monthly rebalancing (low trade count)
--rebalance-freq monthly
```

### Worker Configuration
```bash
# Default: 8 workers (27 stocks each)
--num-workers 8

# High-throughput: 16 workers (13-14 stocks each)
--num-workers 16

# Test mode: 2 workers (108 stocks each)
--num-workers 2
```

## 🔧 Advanced Usage

### Dry Run (Planning)
```bash
python cloud_orchestrator.py --project-id your-project --bucket-name your-bucket --dry-run
```

### Custom VM Configuration
Edit `cloud_orchestrator.py`:
```python
self.vm_config = {
    'machine_type': 'n1-standard-4',  # More powerful VMs
    'disk_size_gb': 50,               # Larger disk
}
```

### Manual Cleanup
```bash
# Remove all badger worker VMs
gcloud compute instances list --filter="name~'badger-worker'" --format="value(name)" | xargs -I {} gcloud compute instances delete {} --zone=us-central1-a --quiet
```

## 📊 Expected Results

### Sprint 13 Success Criteria
- **Returns**: >15% annualized (Target: ✅)
- **Sharpe Ratio**: >1.0 (Target: ✅) 
- **Max Drawdown**: <25% (Target: ✅)
- **Total Trades**: >50 (Target: ✅)

### Performance Estimates
- **Bi-weekly rebalancing**: 50-80 trades over 6 years
- **Full universe**: 216 S&P 500 stocks
- **Execution time**: 15-30 minutes on cloud
- **Cost**: ~$2-5 per full backtest run

## 🛟 Troubleshooting

### Common Issues

1. **Authentication Error**
   ```bash
   gcloud auth login
   gcloud auth configure-docker
   ```

2. **Docker Build Fails**
   ```bash
   # Check Dockerfile and requirements.txt
   docker build -t test-image .
   ```

3. **VM Creation Fails**
   ```bash
   # Check quotas in GCP Console
   gcloud compute project-info describe --project=your-project
   ```

4. **Results Not Aggregating**
   ```bash
   # Check bucket permissions
   gsutil ls gs://your-bucket-name/sprint13_results/
   ```

### Monitoring Commands
```bash
# List running VMs
gcloud compute instances list --filter="labels.purpose=operation-badger"

# Check VM logs
gcloud compute instances get-serial-port-output badger-worker-w01

# Monitor bucket activity
gsutil ls -r gs://your-bucket-name/
```

## 💰 Cost Management

### VM Costs (n1-standard-2)
- **Per hour**: ~$0.10
- **Per backtest**: ~$1-3 (15-30 minutes × 8 VMs)
- **Auto-shutdown**: VMs self-terminate after completion

### Storage Costs
- **Results**: ~1MB per worker
- **Monthly cost**: <$0.01

### Optimization Tips
1. Use preemptible VMs for 80% cost reduction
2. Clean up results after analysis
3. Use regional buckets for lower costs

## 🎯 Production Considerations

### For Live Trading
1. **Security**: Use service accounts with minimal permissions
2. **Monitoring**: Implement alerting for failed backtests
3. **Scheduling**: Use Cloud Scheduler for automated runs
4. **Scaling**: Consider Cloud Run for serverless execution

### Performance Tuning
1. **Caching**: Implement Redis for fundamental data
2. **Parallelization**: Increase worker count for larger universes
3. **Optimization**: Pre-compute factor scores for faster execution

## 📈 Next Steps

After successful Sprint 13 execution:

1. **Production Deployment**: Move to live trading environment
2. **Strategy Enhancement**: Implement additional factors
3. **Risk Management**: Add position sizing and risk controls
4. **Monitoring**: Build real-time performance dashboard

---

**Operation Badger**: Systematic Trading at Scale 🚀
# Operation Badger - GCP Project Setup Commands

**Execute these commands in order to set up the correct GCP project**

## 📋 Step 1: Login to Google Cloud
```bash
gcloud auth login
```
This will open your browser for authentication.

## 📋 Step 2: Create the Project
```bash
gcloud projects create operation-badger-quant --name="Operation Badger"
```

**Expected output:**
```
Create in progress for [https://cloudresourcemanager.googleapis.com/v1/projects/operation-badger-quant].
Waiting for [operations/cp.xxxxxx] to finish...done.
Enabling service [cloudapis.googleapis.com] on project [operation-badger-quant]...
```

## 📋 Step 3: Set as Default Project
```bash
gcloud config set project operation-badger-quant
```

**Expected output:**
```
Updated property [core/project].
```

## 📋 Step 4: Verify Project is Set
```bash
gcloud config get-value project
```

**Expected output:**
```
operation-badger-quant
```

## 📋 Step 5: Enable Required APIs
```bash
# Enable Compute Engine API
gcloud services enable compute.googleapis.com

# Enable Artifact Registry API
gcloud services enable artifactregistry.googleapis.com

# Enable Cloud Storage API
gcloud services enable storage.googleapis.com
```

## 📋 Step 6: Link Billing (Via Console)
1. Go to: https://console.cloud.google.com
2. Select "Operation Badger" project from the dropdown
3. Navigate to Billing in the menu
4. Click "Link a billing account"
5. Select your billing account
6. Click "Set account"

## ✅ Verification Commands

After setup, run these to verify:

```bash
# Check current project
gcloud config get-value project

# List enabled APIs
gcloud services list --enabled

# Check billing (may require beta)
gcloud beta billing projects describe operation-badger-quant
```

## 🚀 Next Steps

Once the project is created and billing is linked:

```bash
# Deploy the infrastructure
python deploy_to_cloud_simple.py

# Run a test backtest (10 stocks)
python cloud_orchestrator_simple.py --bucket operation-badger-quant-results --test-run

# Run full Sprint 13 (216 stocks)
python cloud_orchestrator_simple.py --bucket operation-badger-quant-results
```

---

**Note**: If you get an error that the project ID already exists, it may be taken by another organization. You can either:
1. Use a different project ID (update `cloud_config.py`)
2. Use your existing project (if you own it)
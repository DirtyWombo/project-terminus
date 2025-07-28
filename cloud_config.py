#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Operation Badger - Cloud Configuration
Central configuration for all cloud scripts
"""

# Google Cloud Project Configuration
PROJECT_ID = "operation-badger-quant"  # Official project ID from directive
ZONE = "us-central1-a"
LOCATION = "us-central1"

# Artifact Registry Configuration
REPO_NAME = "badger-containers"
IMAGE_NAME = "backtester"
TAG = "latest"

# Compute Configuration
MACHINE_TYPE = "e2-medium"  # Cost-effective instance type
SERVICE_ACCOUNT = "default"

# Storage Configuration
RESULTS_BUCKET_SUFFIX = "-results"  # Will create: {PROJECT_ID}-results

# Full Image URI
IMAGE_URI = f"{LOCATION}-docker.pkg.dev/{PROJECT_ID}/{REPO_NAME}/{IMAGE_NAME}:{TAG}"

# Container-Optimized OS image
COS_IMAGE = "projects/cos-cloud/global/images/cos-stable-101-17162-40-55"
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Run Sprint 12 backtest with proper Unicode handling
"""

import sys
import os

# Force UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

# Add path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run
from backtests.sprint_12.test_smaller_universe import test_smaller_universe

if __name__ == "__main__":
    test_smaller_universe()
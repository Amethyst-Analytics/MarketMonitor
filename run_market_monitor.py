#!/usr/bin/env python3
"""MarketMonitor entrypoint: delegates to src/setup.py."""

from __future__ import annotations
from src.setup import main as setup_main

if __name__ == "__main__":
    setup_main()

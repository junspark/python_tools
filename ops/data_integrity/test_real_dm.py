#!/usr/bin/env python3
"""Quick test: query real DM for experiments and test dm_integrity functions."""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import dm_integrity as di

print("Testing real DM API connectivity...")

try:
    status = di.get_upload_status("s1id_2024_test", "SOJOURNER")
    print(f"✓ get_upload_status works")
    print(f"  Status: {status.get('status', 'unknown')}")
    print(f"  Upload complete: {status.get('upload_complete', False)}")
except Exception as e:
    print(f"✗ get_upload_status failed: {e}")

try:
    files = di.get_catalog_files("s1id_2024_test")
    print(f"✓ get_catalog_files works")
    print(f"  Files found: {len(files)}")
    if files:
        sample = list(files.items())[0]
        print(f"  Sample: {sample[0]} (size: {sample[1].get('size', 'N/A')})")
except Exception as e:
    print(f"✗ get_catalog_files failed: {e}")

print("\nDM API test complete.")

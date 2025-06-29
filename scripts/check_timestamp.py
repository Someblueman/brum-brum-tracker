#!/usr/bin/env python3
"""
Quick script to check and convert timestamps.
"""

import time
from datetime import datetime, timezone

def check_timestamp(ts: int):
    """Convert and analyze a timestamp."""
    print(f"\nTimestamp: {ts}")
    
    # Convert to datetime
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    print(f"UTC Time: {dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Local time
    dt_local = datetime.fromtimestamp(ts)
    print(f"Local Time: {dt_local.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Current time
    current_ts = int(time.time())
    current_dt = datetime.now(timezone.utc)
    print(f"\nCurrent Timestamp: {current_ts}")
    print(f"Current UTC Time: {current_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Time difference
    diff_seconds = current_ts - ts
    diff_hours = diff_seconds / 3600
    diff_days = diff_seconds / 86400
    
    print(f"\nTime Difference:")
    print(f"  Seconds: {diff_seconds:,}")
    print(f"  Hours: {diff_hours:.1f}")
    print(f"  Days: {diff_days:.1f}")
    
    if diff_seconds > 0:
        print(f"\nThis timestamp is {diff_hours:.1f} hours in the past")
    else:
        print(f"\nThis timestamp is {abs(diff_hours):.1f} hours in the future!")

# Check the timestamp from the logs
print("=" * 60)
print("  Timestamp Analysis")
print("=" * 60)

# The timestamp from your logs
check_timestamp(1751161801)

# Also check a timestamp from around 2025 for comparison
print("\n" + "=" * 60)
print("  Expected 2025 Timestamp Range")
print("=" * 60)

# January 1, 2025
jan_2025 = int(datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp())
check_timestamp(jan_2025)

# June 29, 2025 (today's date according to the environment)
june_2025 = int(datetime(2025, 6, 29, 0, 0, 0, tzinfo=timezone.utc).timestamp())
check_timestamp(june_2025)
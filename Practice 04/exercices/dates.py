from datetime import datetime, timedelta
# 1. Minus 5 days
print("5 days ago:", (datetime.now() - timedelta(days=5)).date())
# 2. Yesterday, Today, Tomorrow
today = datetime.now().date()
print(f"Yesterday: {today - timedelta(days=1)} | Today: {today} | Tomorrow: {today + timedelta(days=1)}")
# 3. No microseconds
print("No micros:", datetime.now().replace(microsecond=0))
# 4. Seconds difference
d1, d2 = datetime(2026, 2, 25), datetime(2026, 2, 24)
print("Diff in sec:", (d1 - d2).total_seconds())
import rpm
import os
import sqlite3
from collections import Counter
import json
import sys

# ----------------------------
# Configuration
# ----------------------------
RPMDB_PATH = "/var/lib/rpm"
RPMDB_FILE = os.path.join(RPMDB_PATH, "rpmdb.sqlite")

# ----------------------------
# Sanity check
# ----------------------------
if not os.path.isfile(RPMDB_FILE):
    print("ERROR: rpmdb.sqlite not found in", RPMDB_PATH)
    sys.exit(1)

# ----------------------------
# Point librpm to external rpmdb
# ----------------------------
os.environ["RPM_DBPATH"] = RPMDB_PATH

score = 100
issues = []
packages = []

# ----------------------------
# Check #1: librpm readability
# ----------------------------
try:
    ts = rpm.TransactionSet()
    ts.setVSFlags(
        rpm._RPMVSF_NOSIGNATURES |
        rpm._RPMVSF_NODIGESTS
    )
    headers = list(ts.dbMatch())
except rpm.error as e:
    print("RPMDB CORRUPT:", e)
    sys.exit(1)

# ----------------------------
# Decode RPM headers
# ----------------------------
decode_failures = 0

for h in headers:
    try:
        packages.append({
            "name": h['name'],
            "version": h['version'],
            "release": h['release'],
            "arch": h['arch'],
            "nevra": f"{h['name']}-{h['version']}-{h['release']}.{h['arch']}",
            "vendor": h['vendor'],
            "installtime": h['installtime']
        })
    except Exception:
        decode_failures += 1

if decode_failures:
    score -= 20
    issues.append(f"{decode_failures} RPM headers failed to decode")

# ----------------------------
# Check #2: SQLite integrity
# ----------------------------
try:
    db = sqlite3.connect(RPMDB_FILE)
    cur = db.cursor()
    cur.execute("PRAGMA integrity_check;")
    if cur.fetchone()[0] != "ok":
        score -= 10
        issues.append("SQLite integrity check failed")
except Exception as e:
    score -= 10
    issues.append(f"SQLite access error: {e}")

# ----------------------------
# Check #3: Name ↔ Packages consistency
# ----------------------------
cur.execute("SELECT COUNT(*) FROM Name;")
name_count = cur.fetchone()[0]

if abs(len(packages) - name_count) > 10:
    score -= 10
    issues.append("Mismatch between Name table and RPM headers")

# ----------------------------
# Check #4: Duplicate package names
# ----------------------------
name_counts = Counter(p['name'] for p in packages)
duplicates = {k: v for k, v in name_counts.items() if v > 1}

if len(duplicates) > 10:
    score -= 10
    issues.append(f"Excessive duplicate package names: {len(duplicates)}")

# ----------------------------
# Check #5: Kernel sanity
# ----------------------------
kernels = [p for p in packages if p['name'] == 'kernel']

if not kernels:
    score -= 10
    issues.append("No kernel package installed")
elif len(kernels) > 5:
    score -= 5
    issues.append("Too many kernel versions installed")

# ----------------------------
# Final health status
# ----------------------------
if score >= 90:
    status = "HEALTHY"
elif score >= 70:
    status = "DEGRADED"
elif score >= 40:
    status = "UNSTABLE"
else:
    status = "CORRUPT"

# ----------------------------
# Output report
# ----------------------------
print("\n===== RPMDB HEALTH REPORT =====")
print("Health Score :", score)
print("Status       :", status)
print("RPM Count    :", len(packages))
print("Unique Names :", len(set(p['name'] for p in packages)))
print("Duplicates   :", len(duplicates))

if issues:
    print("\nIssues detected:")
    for i in issues:
        print(" -", i)

# ----------------------------
# JSON export
# ----------------------------
report = {
    "health_score": score,
    "status": status,
    "rpm_count": len(packages),
    "unique_names": len(set(p['name'] for p in packages)),
    "duplicates": duplicates,
    "issues": issues
}

with open("rpmdb_health_report.json", "w") as f:
    json.dump(report, f, indent=2)

print("\nJSON report written to rpmdb_health_report.json")


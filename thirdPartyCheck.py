#!/usr/bin/env python3
import rpm
import os
import json
import sys
from collections import defaultdict

# ----------------------------
# Configuration
# ----------------------------
RPMDB_PATH = "/var/lib/rpm"
RPMDB_FILE = os.path.join(RPMDB_PATH, "rpmdb.sqlite")
OUTPUT_JSON = "third_party_rpms.json"

# Canonical Red Hat vendors
REDHAT_VENDORS = {
    "Red Hat, Inc.",
    "Red Hat Inc.",
    "Red Hat Enterprise Linux"
}

# ----------------------------
# Sanity checks
# ----------------------------
if not os.path.isfile(RPMDB_FILE):
    print(f"ERROR: rpmdb.sqlite not found in {RPMDB_PATH}")
    sys.exit(1)

# ----------------------------
# Point librpm to external rpmdb
# ----------------------------
os.environ["RPM_DBPATH"] = RPMDB_PATH

# ----------------------------
# Read rpmdb via librpm
# ----------------------------
try:
    ts = rpm.TransactionSet()
    ts.setVSFlags(
        rpm._RPMVSF_NOSIGNATURES |
        rpm._RPMVSF_NODIGESTS
    )
    headers = list(ts.dbMatch())
except rpm.error as e:
    print("ERROR: Unable to read rpmdb:", e)
    sys.exit(1)

# ----------------------------
# Detect third-party packages
# ----------------------------
third_party = []
vendors = defaultdict(list)

for h in headers:
    try:
        name = h['name']
        version = h['version']
        release = h['release']
        arch = h['arch']
        vendor = (h['vendor'] or "").strip()

        nevra = f"{name}-{version}-{release}.{arch}"

        if not vendor or vendor not in REDHAT_VENDORS:
            pkg = {
                "name": name,
                "version": version,
                "release": release,
                "arch": arch,
                "vendor": vendor if vendor else "UNKNOWN",
                "nevra": nevra
            }
            third_party.append(pkg)
            vendors[pkg["vendor"]].append(pkg["nevra"])

    except Exception:
        # Ignore malformed headers
        continue

print("\n===== THIRD-PARTY RPM REPORT =====")
print("Total installed RPMs :", len(headers))
print("Third-party RPMs     :", len(third_party))

if not third_party:
    print("\nNo third-party packages detected.")
else:
    for v, pkgs in vendors.items():
        print(f"\nVendor: {v}")
        for p in sorted(pkgs):
            print("  ", p)

# ----------------------------
# Output: JSON
# ----------------------------
with open(OUTPUT_JSON, "w") as f:
    json.dump({
        "total_rpms": len(headers),
        "third_party_count": len(third_party),
        "third_party_packages": third_party
    }, f, indent=2)

print(f"\nJSON report written to {OUTPUT_JSON}")


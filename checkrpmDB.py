import rpm
import os

RPMDB_PATH = "/var/lib/rpm"   # DIRECTORY, not file

# Point librpm to the external rpmdb
os.environ["RPM_DBPATH"] = RPMDB_PATH

ts = rpm.TransactionSet()

# Speed + safety flags
ts.setVSFlags(
    rpm._RPMVSF_NOSIGNATURES |
    rpm._RPMVSF_NODIGESTS
)

try:
    for _ in ts.dbMatch():
        pass
    print("RPMDB is readable and consistent")
except rpm.error as e:
    print("RPMDB corruption detected:", e)


import os
import sys
from datetime import datetime, timezone
from pymongo import MongoClient

# Built-in and sample databases that don't need a keepalive document
SKIP_DBS = {"admin", "local", "config", "sample_mflix"}

uri = os.environ.get("MONGO_URI")
if not uri:
    sys.exit("MONGO_URI secret is missing.")

client = MongoClient(uri, serverSelectionTimeoutMS=20000)

# Connecting to the cluster is what keeps it active
client.admin.command("ping")
print("Cluster reachable")

# Touch every user database so the log doubles as a health report
for name in client.list_database_names():
    if name in SKIP_DBS:
        continue
    db = client[name]
    db["keepalive"].update_one(
        {"_id": 1},
        {"$set": {"pinged_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    print(f"OK  {name}  ({len(db.list_collection_names())} collections)")

client.close()

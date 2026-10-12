import os, ssl
from sqlalchemy import create_engine, URL, text

url = URL.create(
    drivername=os.environ["DRIVERNAME"],      # e.g. mysql+pymysql
    username=os.environ["USERNAME"],
    password=os.environ["PASSWORD"],
    host=os.environ["HOSTNAME"],
    port=int(os.environ.get("PORT", 3306)),
    database=os.environ["DATABASE"],
)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

engine = create_engine(url, connect_args={"ssl": ctx})
with engine.begin() as conn:
    conn.execute(text("""CREATE TABLE IF NOT EXISTS keepalive (
        id INT PRIMARY KEY, pinged_at DATETIME)"""))
    conn.execute(text("REPLACE INTO keepalive VALUES (1, NOW())"))
    jobs = conn.execute(text("SELECT COUNT(*) FROM jobs")).scalar()
print(f"DB alive, {jobs} jobs stored")

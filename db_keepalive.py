import os, ssl
from sqlalchemy import create_engine, URL, text

url = URL.create(
    drivername=os.environ["DB_DRIVERNAME"],
    username=os.environ["DB_USERNAME"],
    password=os.environ["DB_PASSWORD"],
    host=os.environ["DB_HOST"],
    port=int(os.environ["DB_PORT"]),
    database=os.environ["DB_DATABASE"],
)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

engine = create_engine(url, connect_args={"ssl": ctx})
with engine.begin() as conn:
    conn.execute(text("CREATE TABLE IF NOT EXISTS keepalive (id INT PRIMARY KEY, pinged_at DATETIME)"))
    conn.execute(text("REPLACE INTO keepalive VALUES (1, NOW())"))
print("DB is alive")

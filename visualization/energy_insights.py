import boto3
import pandas as pd
import matplotlib.pyplot as plt
from decimal import Decimal
from pathlib import Path

# ---------- Load data from DynamoDB ----------
table = boto3.resource("dynamodb").Table("EnergyData")
rows  = table.scan()["Items"]

# Convert Decimal → float
for r in rows:
    for k, v in r.items():
        if isinstance(v, Decimal):
            r[k] = float(v)

df = pd.DataFrame(rows)
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Make sure output dir exists
Path("visualization").mkdir(exist_ok=True)

# 1. ─── Generation vs Consumption (site-1) ───────────────────────
site = "site-1"
sub  = df[df["site_id"] == site].sort_values("timestamp")

plt.figure(figsize=(9, 4))
plt.plot(sub["timestamp"], sub["energy_generated_kwh"], label="generated")
plt.plot(sub["timestamp"], sub["energy_consumed_kwh"], label="consumed")
plt.title(f"{site}: generation vs consumption")
plt.xlabel("timestamp")
plt.ylabel("kWh")
plt.legend()
plt.tight_layout()
plt.savefig("visualization/site1_gen_vs_cons.png")
plt.close()

# 2. ─── Anomaly counts per site ─────────────────────────────────
counts = df[df["anomaly"]].groupby("site_id").size()

plt.figure(figsize=(9, 4))
counts.plot(kind="bar", color="tomato")
plt.title("Anomalies per site")
plt.xlabel("site_id")
plt.ylabel("count")
plt.tight_layout()
plt.savefig("visualization/anomaly_counts.png")
plt.close()

# 3. ─── Net-energy daily trend (all sites) ──────────────────────
daily = (
    df.set_index("timestamp")          # make timestamp the index
      .resample("D")["net_energy_kwh"] # daily sum
      .sum()
)

plt.figure(figsize=(9, 4))
plt.plot(daily.index, daily.values, marker="o")
plt.title("Net energy per day")
plt.xlabel("date")
plt.ylabel("kWh")
plt.tight_layout()
plt.savefig("visualization/net_energy_trend.png")
plt.close()

print("✅ Charts regenerated in visualization/ folder")

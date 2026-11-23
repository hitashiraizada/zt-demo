"""One chart from results/bench/summary.csv: median bar + p95 tick per path."""
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

with open("/results/summary.csv") as f:
    rows = list(csv.DictReader(f))[::-1]          # first path on top

names = [r["path"] for r in rows]
med = [float(r["median_ms"]) for r in rows]
p95 = [float(r["p95_ms"]) for r in rows]

fig, ax = plt.subplots(figsize=(8, 3.6), dpi=150)
ax.barh(names, med, height=0.5, color="#4C6EF5", label="median")
ax.scatter(p95, names, marker="|", s=300, linewidths=2, color="#1F2933", label="p95", zorder=3)
for y, (m, p) in enumerate(zip(med, p95)):
    ax.text(p, y, f"  {m:.2f} / {p:.2f} ms", va="center", fontsize=8, color="#1F2933")
ax.set_xlabel("latency per request (ms) - bar = median, tick = p95")
ax.set_title("POST /pay latency by path (5 runs x 1000 requests)", fontsize=10, loc="left")
ax.set_xlim(0, max(p95) * 1.35)
ax.grid(axis="x", color="#E4E7EB", linewidth=0.8)
ax.set_axisbelow(True)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.legend(loc="lower right", frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig("/results/latency.png")
print("wrote /results/latency.png")

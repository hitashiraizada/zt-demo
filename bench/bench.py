"""Latency benchmark: direct vs nginx plain vs nginx mTLS, new connection vs keep-alive.

Uses the standard library http.client so it is obvious what each request does:
"new" = open TCP (+TLS handshake) for every request, then close it;
"keepalive" = one connection reused for all requests of that path in a run.
"""
import csv
import http.client
import os
import random
import ssl
import statistics
import time

SEED = 0            # last two digits of my student ID
RUNS = 5
WARMUP = 50
MEASURED = 1000
OUT = "/results"
BODY = b'{"amount": 10}'
HEADERS = {"content-type": "application/json"}

# mTLS client = the allowed identity (orders), trusting only my CA.
tls = ssl.create_default_context(cafile="/certs/ca.pem")
tls.load_cert_chain("/certs/orders.pem", "/certs/orders.key")

# name -> (host, port, use_tls, keepalive)
PATHS = {
    "direct_plain":        ("payments",       8000, False, True),
    "nginx_plain_new":     ("payments-proxy", 8080, False, False),
    "nginx_plain_keepalive": ("payments-proxy", 8080, False, True),
    "nginx_mtls_new":      ("payments-proxy", 8443, True,  False),
    "nginx_mtls_keepalive":  ("payments-proxy", 8443, True,  True),
}


def connect(host, port, use_tls):
    if use_tls:
        return http.client.HTTPSConnection(host, port, context=tls)
    return http.client.HTTPConnection(host, port)


def one_request(conn):
    conn.request("POST", "/pay", body=BODY, headers=HEADERS)
    resp = conn.getresponse()
    resp.read()
    if resp.status != 200:
        raise RuntimeError(f"unexpected HTTP {resp.status}")


def run_path(host, port, use_tls, keepalive, n):
    """Return n latencies in ms. Timing includes connect/handshake for 'new'."""
    latencies = []
    conn = connect(host, port, use_tls) if keepalive else None
    for _ in range(n):
        t0 = time.perf_counter_ns()
        if keepalive:
            one_request(conn)
        else:
            c = connect(host, port, use_tls)
            one_request(c)
            c.close()
        latencies.append((time.perf_counter_ns() - t0) / 1e6)
    if conn:
        conn.close()
    return latencies


def main():
    print(f"random seed = {SEED}")
    rng = random.Random(SEED)
    rows = []
    for run in range(1, RUNS + 1):
        order = list(PATHS)
        rng.shuffle(order)
        print(f"run {run} order: {', '.join(order)}")
        for pos, name in enumerate(order, 1):
            host, port, use_tls, keepalive = PATHS[name]
            run_path(host, port, use_tls, keepalive, WARMUP)  # discarded
            for i, ms in enumerate(run_path(host, port, use_tls, keepalive, MEASURED)):
                rows.append((run, pos, name, i, ms))

    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/raw_latencies.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run", "position_in_run", "path", "request", "latency_ms"])
        w.writerows(rows)

    lines = [f"seed={SEED} runs={RUNS} warmup={WARMUP} measured_per_run={MEASURED}",
             f"{'path':<24}{'n':>6}{'median_ms':>11}{'p95_ms':>9}{'mean_ms':>9}{'std_ms':>9}"]
    with open(f"{OUT}/summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "n", "median_ms", "p95_ms", "mean_ms", "std_ms"])
        for name in PATHS:
            xs = [r[4] for r in rows if r[2] == name]
            med = statistics.median(xs)
            p95 = statistics.quantiles(xs, n=100, method="inclusive")[94]
            mean, std = statistics.mean(xs), statistics.stdev(xs)
            w.writerow([name, len(xs), f"{med:.3f}", f"{p95:.3f}", f"{mean:.3f}", f"{std:.3f}"])
            lines.append(f"{name:<24}{len(xs):>6}{med:>11.3f}{p95:>9.3f}{mean:>9.3f}{std:>9.3f}")
    table = "\n".join(lines)
    print(table)
    with open(f"{OUT}/summary.txt", "w") as f:
        f.write(table + "\n")


if __name__ == "__main__":
    main()

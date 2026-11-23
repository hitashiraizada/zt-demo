# Commands

Every command used to produce the files in `results/`, in order, starting from a
clean clone. Run them from the repository root.

Requirements: Docker with Compose v2, `git`, `bash`, `openssl`, `curl`.
Host ports used: 8001.

## 0. Clone

```bash
git clone <repo-url> zt-demo
cd zt-demo
```

## 1. Baseline: orders -> payments over plain HTTP (no proxy)

The baseline only exists in the Step 1 commit, so check that commit out first.

```bash
git checkout $(git log --format=%h --grep='^Step 1:')
docker compose up -d --build
```

Produces `results/baseline/step1_baseline.txt`:

```bash
mkdir -p results/baseline && {
echo '$ curl -sS -i -X POST localhost:8001/order'; curl -sS -i -X POST localhost:8001/order; echo
echo; echo '$ curl -sS -m 3 -X POST localhost:8000/pay   # payments is NOT published to the host'; curl -sS -m 3 -X POST localhost:8000/pay; echo "exit code: $?"
echo; echo '$ docker compose ps'; docker compose ps
echo; echo '$ docker compose logs payments'; docker compose logs payments
} 2>&1 | tee results/baseline/step1_baseline.txt
```

Stop the baseline and return to the latest version:

```bash
docker compose down
git checkout -- results/baseline
git checkout main
```

## 2. Certificates

```bash
./certs/gen_certs.sh
```

Produces `results/certs/step2_verify.txt`:

```bash
cd certs && mkdir -p ../results/certs && {
for c in payments-proxy orders attacker rogue; do echo "\$ openssl verify -CAfile ca.pem $c.pem"; openssl verify -CAfile ca.pem $c.pem 2>&1; echo; done
echo '$ openssl verify -CAfile rogue-ca.pem rogue.pem'; openssl verify -CAfile rogue-ca.pem rogue.pem 2>&1; echo
for c in ca payments-proxy orders attacker rogue-ca rogue; do echo "\$ openssl x509 -in $c.pem -noout -subject -issuer -ext subjectAltName,extendedKeyUsage,basicConstraints"; openssl x509 -in $c.pem -noout -subject -issuer -ext subjectAltName,extendedKeyUsage,basicConstraints 2>&1; echo; done
} | tee ../results/certs/step2_verify.txt; cd ..
```

## 3. Start the zero-trust setup (payments-proxy with mTLS + deny by default)

```bash
docker compose up -d --build
```

Produces `results/proxy/step3_end_to_end.txt`:

```bash
mkdir -p results/proxy && {
echo '$ curl -sS -i -X POST localhost:8001/order'; curl -sS -i -X POST localhost:8001/order; echo
echo; echo '$ docker compose exec payments-proxy nginx -t'; docker compose exec payments-proxy nginx -t 2>&1
echo; echo '$ docker compose ps'; docker compose ps
echo; echo '$ docker compose logs payments-proxy | grep verify='; docker compose logs payments-proxy | grep verify=
echo; echo '$ docker compose logs --tail 2 payments'; docker compose logs --tail 2 payments
} 2>&1 | tee results/proxy/step3_end_to_end.txt
docker network inspect zt-net --format '{{range .Containers}}{{.Name}} {{.IPv4Address}}{{"\n"}}{{end}}' | tee -a results/proxy/step3_end_to_end.txt
```

(At the Step 3 commit the network did not have a fixed name yet, so the committed
file was produced with `zt-demo_default` in place of `zt-net`.)

## 4. Allowed and blocked requests

```bash
./scripts/demo.sh
```

Produces `results/demo/*.txt` (one file per case, each holding its exact command)
and `results/demo/payments-proxy.log`, `results/demo/payments.log`.

## 5. Latency benchmark

```bash
mkdir -p results/bench && { echo '$ docker compose run --rm bench'; time docker compose run --rm bench; } 2>&1 | grep -v -E 'Container .* (Running|Waiting|Healthy|Starting|Started)' | tee results/bench/bench_stdout.txt
```

Produces `results/bench/raw_latencies.csv`, `summary.csv`, `summary.txt`,
`latency.png` and `bench_stdout.txt`. Running it again overwrites these files.

## Clean up

```bash
docker compose down
```

## Notes on how the committed results were produced

- The results were produced in a cloud sandbox whose outbound HTTPS goes through a
  TLS-intercepting proxy. To let `pip` install packages during `docker build`,
  the local `python:3.12-slim` image there was replaced with one that adds that
  proxy's CA certificate and sets `PIP_CERT`. This file and the repository do not
  contain that change, and it is not needed on a normal machine.
- All containers ran on a single host, so the benchmark has no real network
  latency between services.

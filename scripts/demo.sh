#!/usr/bin/env bash
# Runs the allow/deny cases from a throwaway curl container on the compose network.
# Each case's exact command and full output go to results/demo/<case>.txt.
# Prerequisite: ./certs/gen_certs.sh && docker compose up -d --build
set -uo pipefail
cd "$(dirname "$0")/.."

OUT=results/demo
mkdir -p "$OUT"
CURL_IMAGE=curlimages/curl:8.11.1
PROXY=https://payments-proxy:8443/pay

# run_case <name> <curl args...>
run_case() {
  local name=$1; shift
  # -u 0: the private keys are mode 600 (root only); the curl image runs as non-root.
  local cmd=(docker run --rm -u 0 --network zt-net -v "$PWD/certs:/certs:ro"
             "$CURL_IMAGE" -sS -v -w '\nHTTP_CODE=%{http_code}\n' "$@")
  {
    echo "# $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "\$ $(printf "%q " "${cmd[@]}")"
    echo
    "${cmd[@]}" 2>&1
    echo "[curl exit code: $?]"
  } > "$OUT/$name.txt"
  echo "$name: $(grep -E '^HTTP_CODE=|^curl: \(' "$OUT/$name.txt" | tail -1)"
}

PAY=(-X POST -H 'content-type: application/json' -d '{"amount": 10}' --cacert /certs/ca.pem)

run_case a_orders_cert_allowed  "${PAY[@]}" --cert /certs/orders.pem   --key /certs/orders.key   "$PROXY"
run_case b_no_client_cert       "${PAY[@]}"                                                        "$PROXY"
run_case c_attacker_cert_403    "${PAY[@]}" --cert /certs/attacker.pem --key /certs/attacker.key "$PROXY"
run_case d_rogue_ca_cert        "${PAY[@]}" --cert /certs/rogue.pem    --key /certs/rogue.key    "$PROXY"
run_case e_end_to_end_order     -X POST http://orders:8000/order

docker compose logs --no-log-prefix payments-proxy > "$OUT/payments-proxy.log" 2>&1
docker compose logs --no-log-prefix payments       > "$OUT/payments.log" 2>&1
echo "Saved to $OUT/"

# Zero-trust between two microservices (mTLS + deny by default)

## Goal

Deploy two small services, `orders` and `payments`, and put a zero-trust policy
between them:

- **mutual TLS**: both sides prove who they are with certificates from my own CA;
- **deny by default**: only the identity `CN=orders` may call payments.

Then show an allowed and a blocked request and measure the latency the policy adds.

## Architecture

```
            host :8001
                |
          +-----v------+   mTLS (client cert CN=orders)   +----------------------+         +-----------+
          |   orders   | -------------------------------> | payments-proxy :8443 |  HTTP   |  payments |
          |  (FastAPI) |                                  | (nginx)              | ------> | (FastAPI) |
          +------------+                                  |  1. cert signed by   |         |   :8000   |
                                                          |     my CA? else 400  |         +-----------+
                                                          |  2. CN == "orders"?  |               ^
                                                          |     else 403         |               |
                                                          +----------------------+               |
                                                          |        :8080         | --------------+
                                                          | plain HTTP, no rules,|
                                                          | benchmark only       |
                                                          +----------------------+
                  all containers on the Docker network "zt-net";
                  payments and payments-proxy are not published to the host
```

- `payments`: `POST /pay` returns `{"status": "paid", "amount": ...}`.
- `orders`: `POST /order` calls `https://payments-proxy:8443/pay` with httpx,
  presenting `orders.pem`/`orders.key` and trusting only `ca.pem`.
- `payments-proxy`: nginx; config in `proxy/nginx.conf`.

## How to run

```bash
./certs/gen_certs.sh            # CA, server cert, client certs (orders, attacker, rogue)
docker compose up -d --build    # payments, payments-proxy, orders
curl -X POST localhost:8001/order
./scripts/demo.sh               # allowed/blocked cases -> results/demo/
docker compose run --rm bench   # latency benchmark -> results/bench/
docker compose down
```

Every command, in order, is in [COMMANDS.md](COMMANDS.md).

## Layout

| Path | Contents |
|---|---|
| `payments/`, `orders/` | the two services (pinned `requirements.txt`) |
| `proxy/nginx.conf` | mTLS listener (8443) with the allow rule; plain listener (8080) |
| `certs/gen_certs.sh` | generates all keys and certs (they are gitignored) |
| `scripts/demo.sh` | allowed/blocked request cases |
| `bench/` | benchmark (`bench.py`) and chart (`plot.py`) |
| `results/` | raw outputs of every step |

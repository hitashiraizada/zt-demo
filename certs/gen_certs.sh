#!/usr/bin/env bash
# Generates every key and certificate used by the demo into this folder.
# Safe to re-run: it overwrites everything.
set -euo pipefail
cd "$(dirname "$0")"

DAYS=365

# new_ca <name> <CN>  -> <name>.key, <name>.pem (self-signed CA)
new_ca() {
  openssl req -x509 -newkey rsa:2048 -nodes -days "$DAYS" \
    -keyout "$1.key" -out "$1.pem" -subj "/CN=$2" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign"
}

# new_cert <name> <CN> <signing-ca> <extensions>  -> <name>.key, <name>.pem
new_cert() {
  openssl req -new -newkey rsa:2048 -nodes \
    -keyout "$1.key" -out "$1.csr" -subj "/CN=$2"
  openssl x509 -req -in "$1.csr" -days "$DAYS" \
    -CA "$3.pem" -CAkey "$3.key" -CAcreateserial \
    -out "$1.pem" -extfile <(printf '%s\n' "$4")
  rm "$1.csr"
}

SERVER_EXT="basicConstraints=CA:FALSE
extendedKeyUsage=serverAuth
subjectAltName=DNS:payments-proxy"
CLIENT_EXT="basicConstraints=CA:FALSE
extendedKeyUsage=clientAuth"

# 1. My own CA: the only CA payments-proxy trusts.
new_ca ca "zt-demo CA"

# 2. Server cert for the proxy. Clients check the hostname against the SAN.
new_cert payments-proxy payments-proxy ca "$SERVER_EXT"

# 3. Client certs signed by my CA: one allowed identity, one valid-but-wrong identity.
new_cert orders   orders   ca "$CLIENT_EXT"
new_cert attacker attacker ca "$CLIENT_EXT"

# 4. A second CA that payments-proxy does NOT trust, and a client cert from it.
#    It claims CN=orders on purpose: the right name from the wrong issuer must still fail.
new_ca rogue-ca "rogue CA"
new_cert rogue orders rogue-ca "$CLIENT_EXT"

rm -f ./*.srl
echo "Generated in $(pwd):"; ls -1 ./*.pem ./*.key

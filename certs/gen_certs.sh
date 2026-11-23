#!/usr/bin/env bash
# Generates every key and certificate used by the demo into this folder.
set -euo pipefail
cd "$(dirname "$0")"
DAYS=365

new_ca() {
  openssl req -x509 -newkey rsa:2048 -nodes -days "$DAYS" \
    -keyout "$1.key" -out "$1.pem" -subj "/CN=$2" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign"
}

new_cert() {
  openssl req -new -newkey rsa:2048 -nodes \
    -keyout "$1.key" -out "$1.csr" -subj "/CN=$2"
  printf '%s\n' "$4" > "$1.ext"
  openssl x509 -req -in "$1.csr" -days "$DAYS" \
    -CA "$3.pem" -CAkey "$3.key" -CAcreateserial \
    -out "$1.pem" -extfile "$1.ext"
  rm "$1.csr" "$1.ext"
}

SERVER_EXT="basicConstraints=CA:FALSE
extendedKeyUsage=serverAuth
subjectAltName=DNS:payments-proxy"
CLIENT_EXT="basicConstraints=CA:FALSE
extendedKeyUsage=clientAuth"

new_ca ca "zt-demo CA"
new_cert payments-proxy payments-proxy ca "$SERVER_EXT"
new_cert orders   orders   ca "$CLIENT_EXT"
new_cert attacker attacker ca "$CLIENT_EXT"
new_ca rogue-ca "rogue CA"
new_cert rogue orders rogue-ca "$CLIENT_EXT"

rm -f ./*.srl
echo "Generated in $(pwd):"; ls -1 ./*.pem ./*.key

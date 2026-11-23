import os
import ssl

import httpx
from fastapi import FastAPI

PAYMENTS_URL = os.environ["PAYMENTS_URL"]

# Trust only my CA (not the system CAs) and present the orders client cert.
ctx = ssl.create_default_context(cafile=os.environ["CA_CERT"])
ctx.load_cert_chain(os.environ["CLIENT_CERT"], os.environ["CLIENT_KEY"])

app = FastAPI()
client = httpx.Client(verify=ctx)


@app.post("/order")
def order():
    r = client.post(f"{PAYMENTS_URL}/pay", json={"amount": 42})
    r.raise_for_status()
    return r.json()

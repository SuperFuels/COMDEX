# Pilot customer-self-hosted opaque relay

The relay is optional. Local access and customer data remain on the mother when it is absent.

## Start

Use a customer-controlled TLS certificate and private key. The certificate name must match the
HTTPS relay address placed in the mother's `PILOT_RELAY_ENDPOINT` setting.

```sh
python3 -m backend.modules.pilot_unified.self_hosted_relay \
  --certificate /customer/tls/fullchain.pem \
  --private-key /customer/tls/privkey.pem \
  --address 0.0.0.0 \
  --port 8780
```

Place the service behind the customer's firewall or reverse-proxy policy. Do not terminate TLS at
an intermediary that records request bodies. Restrict log collection to status codes, timing and
aggregate capacity; never log headers, capabilities, ciphertext bodies or route descriptors.

## Security boundary

- A mother route is accepted only with a valid mother-signed descriptor.
- Phone submission and mother polling use different capabilities.
- Payloads are X25519/HKDF/AES-256-GCM ciphertext. The relay has no decryption key.
- Requests expire after at most two minutes and are bounded, rate-limited and deduplicated.
- The queue is intentionally ephemeral. Restarting it cannot delete data from the customer mother.
- Clients re-register and retry through their existing idempotency keys after relay restart.
- `/health` returns operational metadata only; it never exposes routes or customer identity.

## Production qualification still required

Before internet exposure, test certificate renewal, firewall policy, reverse-proxy body limits,
restart/re-registration, saturation, abuse limits and alerting. A successful local HTTPS test is
not evidence that a particular public deployment is secure or highly available.

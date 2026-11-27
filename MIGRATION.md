# Migration Guide

## Upgrading from `v1.10.x` to `v1.11.0`

`v1.11.0` is **backward-compatible** for all synchronous `Client` callers, builders, and `mailgun.security` imports.

### 1. Optional `httpx2` (`[async]` Extra)

Starting in `v1.11.0`, `httpx2 >= 2.7.0` is an **optional** dependency instead of a mandatory base requirement:

- **Sync-only callers (`Client`):**
  ```bash
  pip install mailgun
  ```
  Works with only `requests` installed (also unblocking `conda` and minimal container installs).

- **Async callers (`AsyncClient` / `AsyncEndpoint`):**
  ```bash
  pip install "mailgun[async]"
  ```
  If `AsyncClient` is instantiated without `httpx2` installed, it raises an `ImportError` with installation instructions.

### 2. New Testing & Webhook Helpers

- **Offline Unit Testing (`mailgun.testing`):**
  ```python
  from mailgun import MockMailgunClient

  with MockMailgunClient() as client:
      client.messages.create(domain="example.com", data={"to": "user@example.com"})
      assert len(client.sent_requests) == 1
  ```
- **Webhook Verification (`mailgun.webhooks`):**
  ```python
  from mailgun import parse_webhook_event, verify_webhook_payload
  ```
  All existing `mailgun.security.SecurityGuard.verify_webhook` calls remain unchanged.

### 3. Restored Exports & Routing Fixes

- `DeliverabilityError` is now exported directly from `mailgun` (`from mailgun import DeliverabilityError`).
- `mailgun._httpx_compat.HAS_HTTPX2` is available for runtime capability checks.
- Multi-word underscore routes (`preview_v2_*`, `reputationanalytics_v2_*`, `ip_pools_*`, `dynamic_pools_*`, `ip_warmups_*`, `ip_whitelist_*`, `maverick_score_*`), `bounce_classification` JSON headers, and `address` validation routes now resolve accurately.

# BindAuthority — Governed Policy Bind Gate

**Standalone platform** preventing silent or ungoverned policy binds before in-force.

## Problem

Bind systems auto-accept submissions above authority without immutable evidence of underwriting conditions at bind time.

## Solution

Pre-bind gate:

- **Sanctions block** — DECLINED on sanctions hit
- **Auto-bind premium band** — HELD above carrier authority
- **Manual review** — REFERRED when flagged
- **CCP crystal** — crystallize facets at evaluation; commit only on BOUND

## API

```
POST /bind/evaluate
GET  /healthz
GET  /readyz
```

## Tests

```bash
pytest insurance-governor/tests/test_bind_authority.py -q
```

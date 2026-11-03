# Production & Scale Design Document

## CamsAI Invoice Audit — Multi-Agent Orchestration Prototype

This document describes the architecture of the working prototype in this
repository, the production-scale path from it.

---

## 1. Architecture

### 1.1 Components

```
Orchestrator process (python -m app.run)
  LangGraph StateGraph
    Agent 1 (Ingestion & Extraction)
    Agent 2 (Validation & Compliance)
    Agent 3 (Reporting & Settlement) — 3 route variants
      |
      | MCP tool calls, over stdio
      v
MCP server process (mcp_server/server.py)
    API 1  fetch_payload      -> mock_data/inbox/*.json
    API 2  vector_knowledge   -> Chroma (embedded, real MiniLM embeddings)
    API 3  policy_check       -> deterministic rule function
    API 4  ledger_write       -> SQLite (ledger.db)
    API 5  notify             -> console / SMTP notifier
    (+)    extract_live_invoice -> Claude (additive, opt-in, see S6)
```

The orchestrator is the single **MCP client**; the 3 "APIs" the
assessment specifies are implemented as **MCP tools** on one server. Agents
never touch SQLite, Chroma, every side effect goes
through an MCP `tools/call`.

### 1.2 Transport: stdio today, swappable to network tomorrow

The client spawns the server as a subprocess (`sys.executable -m mcp_server.server`) and talks to it over its stdin/stdout pipes — this is
MCP's **stdio transport**. One subprocess is spawned per orchestrator run
and reused for every tool call across all three agents; it is not re-spawned
per call.

This was a deliberate choice for local development: no network port, no
Docker, no separately-managed service to start. It is a transport choice,
not an architectural ceiling — the same tool code becomes an independently
deployable, shared service with a one-line change:

```python
mcp.run(transport="streamable-http")  # instead of "stdio"
```

At that point, multiple orchestrator workers (or other teams) can share one
MCP server behind a load balancer, and the `MCPServer` constructor already
supports `token_verifier` / `auth` parameters for securing that network
boundary when it is no longer same-machine, same-process.

### 1.3 Ports and adapters

Each of the 5 tool files (`mcp_server/tools/api*.py`) is a thin adapter.
The real logic lives in sibling packages behind small interfaces:

| Tool                 | Port             | Current adapter                         | Production adapter                     |
| -------------------- | ---------------- | --------------------------------------- | -------------------------------------- |
| `ledger_write`     | `LedgerPort`   | `SQLiteLedger` (file)                 | Managed Postgres                       |
| `vector_knowledge` | —               | Chroma `PersistentClient` (embedded)  | Managed vector DB / Chroma server mode |
| `notify`           | `NotifierPort` | `ConsoleNotifier` (logs + proof file) | SMTP / Slack webhook                   |

---

## 2. State management

### 2.1 Schema

`InvoiceAuditState` (a `TypedDict`) carries: `invoice_id`, `trace_id`,
`raw_payload`, `invoice`, `is_compliant`, `compliance_reasons`,
`ledger_id`, `notification_sent`, `error`. Every node returns only the
fields it changes; LangGraph merges them into the running state. A field's
*absence* is itself meaningful — e.g. a routed-to-escalation invoice simply
has no `ledger_id` key at all, rather than `null`, making "was this ever
posted" unambiguous to inspect later.

### 2.2 Routing

```
START -> agent1 --error--> agent3_error --------> END
            |ok
            v
          agent2 --error--> agent3_error --------> END
            |compliant        |anomalous
            v                 v
      agent3_post        agent3_escalate
       |ok   |error         |ok   |error
       v     +--------> agent3_error <----+
      END                    |
                             v
                            END
```

Every branch terminates at `END`; there is no path that loops or waits
indefinitely. A failure at any stage (fetch, extraction, vector lookup,
policy check, ledger write, or notify) routes to `agent3_error`, which makes
a best-effort notification and always ends the run — a second failure in
the error path itself is swallowed rather than re-raised, so a broken
notifier can never leave an invoice run hanging.

---



## 3. Governance

- **No silent auto-pay override.** An anomalous invoice (Scenario B route)
  is escalated via notification only — there is no path in this graph that
  re-admits a flagged invoice back into the ledger automatically. Approving
  an anomaly would require a deliberate, separate, human-triggered action in
  a production system (a "pending review" state with its own approval API),
  not a retry of the same flow.
- **Full decision trail per invoice.** The final state object for every
  invoice already contains the raw payload, the extracted invoice, the
  compliance verdict and its reasons, the ledger outcome, and the
  notification outcome, correlated by `trace_id`. In production this full
  object — not just the ledger row — should be persisted as an immutable
  audit record for compliance/legal review.
- **Retrieval confidence is currently unused for decisions.** `vector_knowledge`
  returns a `similarity_distance` alongside the matched contract, but
  `policy_check` trusts the best match regardless of how distant it is. A
  hardened version would treat a low-confidence match (high distance) as
  its own flag — "no confident contract reference found for this vendor" —
  rather than silently applying a possibly irrelevant threshold.
- **Single trust boundary.** Only the MCP server holds credentials for the
  ledger DB and the notifier; agents hold no credentials, only the ability
  to invoke named tools. Scoping which caller identity may invoke which
  tool (e.g. only Agent 3 may call `ledger_write`) is a natural extension
  once the server moves off stdio to an authenticated network transport.

---

## 4. Observability

- **Correlation.** A `trace_id` (UUID) is generated once per invoice at the
  CLI entrypoint and threaded through every agent and into the
  `ledger_write` / `notify` calls, so one invoice's entire journey is
  greppable across logs by a single id.
- **Metrics worth exposing in production:** invoices processed/sec, anomaly
  rate (% routed to escalation), hard-failure rate (% routed to
  `agent3_error`), per-agent and per-tool latency, and
  `vector_knowledge`'s average `similarity_distance` (a drifting value over
  time would itself indicate the contract knowledge base is going stale).
- **Alerting** on the anomaly rate or hard-failure rate crossing a
  threshold should notify operations separately from the per-invoice
  escalation notification — one is "this invoice needs review," the other
  is "the system itself needs attention."

---

## 5. Scale path

Every production change below is a swap behind an existing boundary, not a
rewrite:

| Today (prototype)                       | Production                                                                                                                                                          |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| stdio transport, one subprocess         | Streamable HTTP/SSE transport, MCP server as its own scaled service behind a load balancer                                                                          |
| SQLite file (`ledger.db`)             | Managed Postgres, same `LedgerPort` interface                                                                                                                     |
| Chroma embedded `PersistentClient`    | Managed vector DB (Milvus / Pinecone) or Chroma server mode, once contract volume or concurrent writers exceed a single local index                                 |
| `ConsoleNotifier` (logs + proof file) | SMTP / Slack webhook via the existing `NotifierPort`                                                                                                              |
| In-memory graph run, no checkpoint      | Postgres-backed LangGraph checkpointer; resume instead of reprocess on crash                                                                                        |
| Direct function calls, no backpressure  | A durable queue (Kafka/SQS) between ingestion and the orchestrator, so bursts are absorbed and failures retry from a durable source instead of being dropped        |
| One orchestrator process                | A pool of orchestrator workers consuming the queue, each holding its own MCP client session against the shared MCP server                                           |
| One hardcoded vendor/threshold          | Multi-tenant partitioning by `vendor_id`/`tenant_id` in both the ledger and the vector store, with per-category (not just per-vendor) policy thresholds         |
| Local-only credentials                  | Secrets manager for SMTP/DB credentials; MCP server behind TLS + `token_verifier`-based auth (already supported by the installed SDK's `MCPServer` constructor) |

---

## 6. Known limitations

- Realtime invoice flow is never used, since it needs `ANTHROPIC_API_KEY` and a real network call;
- No retry/backoff around MCP tool calls yet. A transient failure (a flaky
  notify, a momentarily locked SQLite file) currently surfaces as a hard
  error rather than retrying with backoff before giving up.

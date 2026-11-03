# CamsAI Invoice Audit — Multi-Agent Orchestration Prototype

Automated vendor invoice auditing: a state-driven orchestrator (LangGraph) runs
3 agents that communicate with 5 mocked APIs through an MCP server.

## Layout

```
camsai-invoice-audit/
├── mock_data/            # Pydantic schemas + Faker generator -> mock_data/inbox/*.json
│   ├── models.py          # Invoice / LineItem schema (shared contract)
│   ├── generator.py       # produces INV-A..E-0001.json (5 scenarios - 3 required + 2 extra coverage)
│   └── inbox/              # generated payloads live here (gitignored, regenerated each run)
│
├── mcp_server/            # the 5 "APIs", each a thin MCP tool over a real backing store
│   ├── server.py           # MCPServer app (mcp SDK 2.x), registers all tools, stdio entrypoint
│   ├── tools/               # API1-API5 - thin adapters only
│   │   ├── api1_fetch_payload.py
│   │   ├── api2_vector_knowledge.py
│   │   ├── api3_policy_check.py
│   │   ├── api4_ledger_write.py
│   │   ├── api5_notify.py
│   │   └── live_extract_invoice.py  # additive 6th tool, see "Live extraction" below
│   ├── ledger/               # API4's backing store - SQLite, idempotent on invoice_id
│   ├── vectorstore/          # API2's backing store - Chroma (real MiniLM embeddings)
│   ├── notifier/             # API5's backing store - console (default) / SMTP (opt-in)
│   └── extraction/           # Claude-powered extraction for the live path
│
├── agents/                # the 3 agents, as LangGraph node functions
│   ├── state.py             # shared orchestration state (trace_id, verdict, error, ...)
│   ├── mcp_client.py        # spawns mcp_server over stdio, exposes call()
│   ├── agent1_ingestion.py   # Agent 1 -> API1 (or the live-extraction tool)
│   ├── agent2_validation.py  # Agent 2 -> API2 + API3
│   └── agent3_reporting.py   # Agent 3 -> API4 + API5 (3 route variants)
│
├── orchestrator/
│   └── graph.py             # LangGraph StateGraph wiring the 3 agents + conditional routing
│
├── app/
│   └── run.py               # CLI entrypoint: --scenario a-e | --invoice-id <id> | --invoice-file <path>
│
├── sample_invoices/        # ready-to-try real documents for the live-extraction demo
├── tests/                 # pytest-asyncio tests for scenarios A-E
├── docs/
│   └── DESIGN.md            # Production & Scale design document
├── Dockerfile              # bakes in the Chroma embedding model + seeded collection
└── docker-compose.yml      # seed -> tests (automatic), app (manual single-scenario runs)
```

## Running locally (no Docker)

```bash
python -m venv .venv
.venv/Scripts/activate        # or: source .venv/bin/activate
pip install -r requirements.txt

python -m mock_data.generator        # writes the 3 scenario fixtures
python -m app.run --scenario a       # or b / c
pytest -v
```

## Running with Docker

```bash
docker compose up --build
```

This builds the image (baking in the Chroma embedding model and seeded
vendor-contract collection so there's no mid-test model download), then runs
`seed` (regenerates the 3 scenario fixtures) followed automatically by
`tests` (the full pytest suite) — the "automated startup sequence" the
assessment requires.

For a single scenario on demand:

```bash
docker compose --profile manual run --rm app python -m app.run --scenario b
```

### Inspecting the ledger

`tests` and `app` both mount a named volume (`ledger_data`) at `/app/data`,
where `ledger.db` lives — so ledger rows persist across separate
`docker compose run` / `up` invocations instead of disappearing with each
container. To see what's in it:

```bash
docker compose --profile manual run --rm app python -c "import sqlite3; conn = sqlite3.connect('/app/data/ledger.db'); conn.row_factory = sqlite3.Row; [print(dict(r)) for r in conn.execute('SELECT * FROM ledger_entries')]"
```

To wipe it and start fresh: `docker compose down -v` (removes the volume too).

### Sending a real email instead of the console notifier

By default, notifications are logged to console and written to `outbox/*.txt`

```bash
docker compose --profile manual run --rm app python -m app.run --scenario a
```

### Live extraction: a real document instead of mock data

API1 is required to be mocked, and stays that way for the automated test
suite (deterministic, no network, no API key). As an **additive** capability,
Agent 1 can instead extract a real invoice (plain text or an image) via
Claude, using forced tool-use so the output always matches the same
`Invoice` schema the mock path produces — nothing downstream (Agent 2, Agent
3) needs to know or care which path ran.

Requires `ANTHROPIC_API_KEY` in your `.env`. Two ready-to-try examples are in
`sample_invoices/` (one compliant, one with a rate-ceiling breach, both using
the same seeded vendor so the policy check is meaningful):

```bash
# locally
python -m app.run --invoice-file sample_invoices/sample_invoice_compliant.txt

# via Docker (sample_invoices/ is mounted read-only at /app/live_invoices)
docker compose --profile manual run --rm app python -m app.run --invoice-file /app/live_invoices/sample_invoice_anomalous.txt
```

Images (`.png`/`.jpg`) work the same way — `--invoice-file` detects the media
type automatically and sends it to Claude as a vision input instead of text.

Without a valid API key, this fails gracefully through the exact same
error-handling path as a malformed mock invoice (Scenario C/E) — no crash,
no hang, a clear `error` in the final state.

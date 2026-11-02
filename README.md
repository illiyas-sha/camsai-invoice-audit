# CamsAI Invoice Audit — Multi-Agent Orchestration Prototype

Automated vendor invoice auditing: a state-driven orchestrator (LangGraph) runs
3 agents that communicate with 5 mocked APIs through an MCP server.

## Status

Fully built and tested: mock data generation, all 5 MCP tools, all 3 agents,
the LangGraph orchestrator, the CLI, the pytest suite, and Docker packaging.
See [`docs/DESIGN.md`](docs/DESIGN.md) for the architecture, state, governance,
observability, and production-scale design.

## Layout

```
camsai-invoice-audit/
├── mock_data/            # Pydantic schemas + Faker generator -> mock_data/inbox/*.json
│   ├── models.py          # Invoice / LineItem schema (shared contract)
│   ├── generator.py       # produces INV-A/B/C-0001.json (the 3 required scenarios)
│   └── inbox/              # generated payloads live here (gitignored, regenerated each run)
│
├── mcp_server/            # the 5 "APIs", each a thin MCP tool over a real backing store
│   ├── server.py           # MCPServer app (mcp SDK 2.x), registers all 5 tools, stdio entrypoint
│   ├── tools/               # API1-API5 - thin adapters only
│   │   ├── api1_fetch_payload.py
│   │   ├── api2_vector_knowledge.py
│   │   ├── api3_policy_check.py
│   │   ├── api4_ledger_write.py
│   │   └── api5_notify.py
│   ├── ledger/               # API4's backing store - SQLite, idempotent on invoice_id
│   ├── vectorstore/          # API2's backing store - Chroma (real MiniLM embeddings)
│   └── notifier/             # API5's backing store - console (default) / SMTP (opt-in)
│
├── agents/                # the 3 agents, as LangGraph node functions
│   ├── state.py             # shared orchestration state (trace_id, verdict, error, ...)
│   ├── mcp_client.py        # spawns mcp_server over stdio, exposes call()
│   ├── agent1_ingestion.py   # Agent 1 -> API1
│   ├── agent2_validation.py  # Agent 2 -> API2 + API3
│   └── agent3_reporting.py   # Agent 3 -> API4 + API5 (3 route variants)
│
├── orchestrator/
│   └── graph.py             # LangGraph StateGraph wiring the 3 agents + conditional routing
│
├── app/
│   └── run.py               # CLI entrypoint: python -m app.run --scenario a|b|c
│
├── tests/                 # pytest-asyncio tests for scenarios A/B/C
├── docs/
│   └── DESIGN.md            # Production & Scale design document
├── Dockerfile              # bakes in the Chroma embedding model + seeded collection
└── docker-compose.yml      # seed -> tests (automatic), app (manual single-scenario runs)
```

## Why this split

- **APIs = MCP tools** (`mcp_server/tools/`). Each tool is a thin adapter; the
  real logic (SQLite writes, Chroma queries, SMTP/console sends) lives in the
  sibling `ledger/`, `vectorstore/`, `notifier/` packages so the tool files stay
  a one-to-one mirror of the assessment's "API 1..5" list.
- **Agents never touch SQLite/Chroma/SMTP directly** — only through
  `agents/mcp_client.py` calling the MCP server's tools over stdio. That's the
  whole point of the assessment (agents communicate *over MCP*).
- **No Docker needed to develop or test.** Ledger is a local SQLite file,
  the vector store is Chroma's embedded `PersistentClient`, and the default
  notifier just logs to console + writes a proof file. Docker was added last,
  purely to package the already-working, already-tested app.

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
— safe, deterministic, no credentials needed for automated test runs. To send
a real email for a live demo, copy `.env.example` to `.env`, fill in your own
SMTP credentials (a Gmail App Password if using Gmail), then:

```bash
docker compose --profile manual run --rm app python -m app.run --scenario a
```

`.env` is gitignored — never commit real credentials.

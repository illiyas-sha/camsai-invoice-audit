# CamsAI Invoice Audit — Multi-Agent Orchestration Prototype

Automated vendor invoice auditing: a state-driven orchestrator (LangGraph) runs
3 agents that communicate with 5 mocked APIs through an MCP server.

## Status

Scaffold only — modules are being filled in step by step. See each file's
docstring for what it will own.

## Layout

```
camsai-invoice-audit/
├── mock_data/            # Pydantic schemas + Faker generator -> mock_data/inbox/*.json
│   ├── models.py          # Invoice / LineItem schema (shared contract)
│   ├── generator.py       # produces scenario_a/b/c.json ("invoices" API1 fetches)
│   └── inbox/              # generated payloads live here (gitignored, regenerated each run)
│
├── mcp_server/            # the 5 "APIs", each a thin MCP tool over a real backing store
│   ├── server.py           # FastMCP app, registers all 5 tools, stdio entrypoint
│   ├── tools/               # API1-API5 — thin adapters only
│   │   ├── api1_fetch_payload.py
│   │   ├── api2_vector_knowledge.py
│   │   ├── api3_policy_check.py
│   │   ├── api4_ledger_write.py
│   │   └── api5_notify.py
│   ├── ledger/               # API4's backing store — SQLite
│   ├── vectorstore/          # API2's backing store — Chroma (real embeddings)
│   └── notifier/             # API5's backing store — console (dev) / SMTP (demo)
│
├── agents/                # the 3 agents, as LangGraph node functions
│   ├── state.py             # shared orchestration state (trace_id, verdict, error, ...)
│   ├── mcp_client.py        # spawns mcp_server over stdio, exposes call_tool()
│   ├── agent1_ingestion.py   # Agent 1 -> API1
│   ├── agent2_validation.py  # Agent 2 -> API2 + API3
│   └── agent3_reporting.py   # Agent 3 -> API4 + API5
│
├── orchestrator/
│   └── graph.py             # LangGraph StateGraph wiring the 3 agents + conditional routing
│
├── app/
│   └── run.py               # CLI entrypoint: python -m app.run --scenario a|b|c
│
├── tests/                 # pytest-asyncio tests for scenarios A/B/C
├── docs/
│   └── DESIGN.md            # Production & Scale design document (written near the end)
└── docker/                # added LAST, after everything works locally
```

## Why this split

- **APIs = MCP tools** (`mcp_server/tools/`). Each tool is a thin adapter; the
  real logic (SQLite writes, Chroma queries, SMTP/console sends) lives in the
  sibling `ledger/`, `vectorstore/`, `notifier/` packages so the tool files stay
  a one-to-one mirror of the assessment's "API 1..5" list.
- **Agents never touch SQLite/Chroma/SMTP directly** — only through
  `agents/mcp_client.py` calling the MCP server's tools. That's the whole
  point of the assessment (agents communicate *over MCP*).
- **No Docker needed to develop or test.** Ledger is a local SQLite file,
  vector store is Chroma's embedded `PersistentClient`, and the dev notifier
  just logs to console. Docker is added at the very end purely to package the
  already-working app.

## Running (once implemented)

```bash
pip install -r requirements.txt
python -m mock_data.generator
python -m app.run --scenario a   # or b / c
pytest
```

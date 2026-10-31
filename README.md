# Empório da Música - AI Support Agent

Python prototype for the Artefact AI Engineer challenge. Read-only tools and the
agent loop are implemented. A real local catalog conversation has been verified;
broader live LLM evaluation and publication are pending.

## Scope

Read-only support: catalog, prices, promotions, store policies, and demo-scoped orders.
No payments, reservations, refunds, or stock writes. A stock query is not a reservation.

## Milestones

1. Deterministic catalog queries and data validation.
2. Policy retrieval, order access controls, isolated sessions.
3. Local LLM tool calling and CLI.
4. Concurrency tests, examples, and reproducibility documentation.

## AI assistance

OpenAI Codex helped inspect the assignment, define scope, and write code, tests, and
documentation. The candidate must review the implementation and validate live model
behavior before submission. No model execution results will be fabricated.

## Source data

Original challenge files are local inputs and are not committed by default.
Public tests use synthetic data. Do not commit customer contact data or credentials.

## Quick start (PowerShell)

Requirements: Python 3.11+, Ollama, and enough local memory to run the selected model.
Qwen3 8B is the initial tool-capable model choice: local execution avoids model API
costs and keeps challenge data on the machine. It has not been benchmarked here.
Smaller hardware may require a smaller tool-capable model and a fresh evaluation.

```powershell
git clone https://github.com/DeividiLuccasdev/artefact-ai-engineer-challenge.git
cd artefact-ai-engineer-challenge
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
ollama pull qwen3:8b
# Ensure the Ollama application/server is running before starting the CLI.
$env:OLLAMA_MODEL = 'qwen3:8b'
$data = 'C:\path\to\challenge\data'
.\.venv\Scripts\python.exe -m emporio.cli --data-dir $data --policies "$data\políticas_da_loja.pdf"
```

The supplied file names may retain the prefix `desafio_tecnico_ai_eng - `.
Exactly one file ending in each of categories.csv, products.csv, promotions.csv,
orders.csv and order_items.csv must exist in the data directory. The customers CSV
is not needed. Leave original files unchanged while the process starts.

For an order lookup demo, add `--demo-customer-id N`, where N is the corresponding
customer ID in the supplied orders CSV. This is a **trusted local test switch**, not
customer authentication. Without it, all order lookups are denied. Type `/quit` to exit.

The application reads environment variables from the shell. `.env.example` documents
them; `.env` is not loaded automatically. Only local HTTP Ollama hosts are allowed.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests require no Ollama process and no original source files. They validate money,
catalog filtering, order ownership, session isolation, serialization, rollback,
tool-call bounds, retrieval references and the mocked Ollama protocol.

## Architecture

`CLI -> Session -> Agent -> Ollama / explicit read-only tools`

- `data.py`: immutable CSV snapshot, Decimal pricing, scoped order lookup.
- `policies.py`: local lexical retrieval over the PDF, with page references.
- `agent.py`: tool schemas, prompt, bounded tool loop, per-session FIFO turn processing.
- `provider.py`: local Ollama HTTP adapter, no shared conversation state.
- `cli.py`: configuration and one local customer session per process.
- `web.py` / `chat.html`: optional loopback-only visual demo using local llama.cpp.

No agent framework is necessary for three tools. Explicit dispatch is easier to audit
than free-form SQL or executable model output. A simple CLI keeps the emphasis on
agent correctness. The PDF is unstructured reference content; inventory remains
structured data. Monetary rules are executed in Python rather than delegated to a model.

## Concurrency

Same-session turns are serialized over the **whole** model/tool cycle. Independent
sessions have separate histories and can execute in parallel. Responses use a single
immutable startup snapshot; returned dictionaries cannot mutate it. History commits
only after a completed answer. Complete older turns are pruned, never partial tool
exchanges. These are single-process guarantees, not distributed locks.

No stock is reserved or sold. Adding reservations would require transactional storage
and atomic stock checks; a Python lock alone would not protect multiple workers.

## Visual demo with a real local model

The initial Windows sandbox blocked Ollama's configuration directory. For the visual
demo, the same Qwen3 weights were run using the portable llama.cpp server included
in the official Ollama Windows release. Model download SHA-256 was verified against
its registry manifest. The smaller `qwen3:1.7b` variant was selected because the
machine had only approximately 3.5 GB of free RAM. This is a demo choice, not a claim
that this model meets production quality requirements.

With a compatible llama.cpp server and a local Qwen3 GGUF file:

```powershell
llama-server -m 'C:\path\to\qwen3-1.7b.gguf' --host 127.0.0.1 --port 11435 -c 8192 -t 4 -ngl 0 --parallel 1 --jinja --reasoning-budget 0 --alias qwen3:1.7b
# In another terminal, from the project directory:
.\.venv\Scripts\python.exe -m emporio.web --data-dir $data --policies "$data\políticas_da_loja.pdf"
```

Open `http://127.0.0.1:8765`. The server binds only to loopback, validates Host and
Origin, establishes random HttpOnly session cookies on page load, limits concurrent requests, and
does not expose customer identity selection. Order queries in this visual demo
always remain unauthenticated and are denied. This is a local development interface,
not a production web deployment. Chat responses never replace session cookies;
requests without an established session return HTTP 409. Active sessions cannot
expire while a turn is running or queued. Both background processes must remain running.

## Known limitations and remaining validation

- One real local catalog conversation is recorded in `examples/05_recorded_catalog.md`.
  Its names and amounts matched tool results. The UI also completed a live catalog query.
  This does not validate all routing, multilingual behavior or prompt-injection resilience.
- Examples 01-04 are acceptance scenarios, **not recorded conversations**. Execute
  them and save the real transcripts before submission.
- Prompt instructions request factual grounding but cannot guarantee it. Tool access
  controls are enforced in code; model prose still needs evaluation.
- Lexical retrieval may miss paraphrases or cut a policy across passages. On uncertain
  or conflicting rules, refer the customer to staff. No automated legal decisions.
- In-memory history disappears on exit; six complete user turns are retained.
- Data is a supplied CSV snapshot, not a live commerce or carrier integration.
- No web authentication, distributed persistence, order writes, complaint registration,
  live holiday calendar, or actual human handoff integration.

With more time: evaluate a labeled question set, test adversarial prompts with a real
model, improve retrieval recall, add validated response templates for critical values,
and implement real authentication before exposing order queries in an API.

See [design decisions](docs/DECISIONS.md) for data ambiguities, assumptions and privacy
boundaries. After live validation, prepare the requested submission document and freeze
the repository at delivery; do not modify it afterward.

## Protocol references

- [Ollama chat endpoint](https://docs.ollama.com/api/chat)
- [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling)
- [llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)

## Development verification

Local checks: 24 automated synthetic tests passed; original inputs loaded as 65
products and 20 orders; policy searches returned page references. A live Qwen3 1.7B
catalog query exposed missing category text in the search index. This was corrected,
covered by a regression test, and rerun successfully. The visual chat returned real
model answers using supplied product data. GitHub publication remains pending access.

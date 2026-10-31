# Design decisions and source ambiguities

## Data versus policies

Structured prices, stock, product state, promotions and orders use deterministic Python
tools. Manual text uses local lexical retrieval with overlapping 200-word passages
and source pages. This avoids a vector database for an eight-page manual and a small
catalog. It is deliberately a prototype; semantic retrieval and measured recall would
be useful with more documents. English query aliases help cross-language lookup but
do not replace multilingual retrieval evaluation.

The LLM decides tool routing and writes the response. Prompts request a fresh tool
call for factual claims. This is **not a hard guarantee**: model-generated prose may
still hallucinate or ignore instructions. Automated tests validate tool boundaries,
not model alignment. Production would require measured evals and stronger output
validation / deterministic templates for critical facts.

## Money and availability

Decimal with ROUND_HALF_UP to cents; no floating-point money. Active promotion flags
are authoritative within the supplied snapshot; no promotion start/end dates exist.
If several offers are active for one product, choose the greatest single discount;
this is an explicit prototype assumption. Do not stack promotions or PIX. Product
status must be active AND stock positive to be available. coming_soon and discontinued
remain visible only when the user explicitly asks to include unavailable products.

Queries read immutable startup data; they do not contact live stock or carriers.
Keep CSV inputs unchanged during startup. Reload is intentionally unsupported.
Order total is not recomputed using current catalog prices: historical price and
discount information are insufficient. Actual receipt dates and purchase channel are
absent, so the agent must ask before explaining individual return eligibility.

## Concurrent conversations

One Session belongs to one trusted application customer context. Same-session turns
receive tickets and run in ticket issuance order. The entire tool loop is serialized,
not merely history append, preventing lost context and tool/response interleaving.
Different sessions can run concurrently because all intermediate messages are local
and the provider adapter has no shared mutable request history. History is committed
only on success, with up to six complete user turns retained. Failed requests leave
the previous history unchanged. The model loop is bounded to four rounds and eight
tool calls per round; local HTTP calls have a timeout.

This protection is process-local. The CLI is a single process; it is not a distributed
web service. A future multi-worker API needs authenticated ownership of session IDs,
transactional history storage or a shared queue, and rate/concurrency limits. Stock
reservations would require database transactions and atomic conditional updates.

## Privacy boundary

The customers CSV is unnecessary and never loaded. get_order accepts only order_id;
the application supplies customer identity separately. Unauthorized and missing orders
return the same response. The tool emits only status, tracking and estimated delivery.
--demo-customer-id is a developer-controlled simulation, **not authentication**: anyone
with shell access can choose it. Do not expose this switch as a public API identity.
Local operators can read source files; the agent is not an operating-system sandbox.
The optional visual interface supplies no customer identity and denies order access.
It creates session cookies on page load, before messages can be sent. POST responses
never create/replace cookies: otherwise concurrent initial requests could create two
histories and the slower response could overwrite the browser identity. Missing or
expired sessions return HTTP 409. Registry entries track in-flight requests, preventing
expiry from replacing a session during a queued/running turn. Registry locks protect
only state changes, never model calls or response writes.
The local HTTP server disables address reuse and uses exclusive address binding
on Windows, so a second process cannot accidentally serve a separate session registry
on the same port.

Original CSV/PDF files are not included in this public repository. Use the assignment
bundle locally. If redistribution is authorized later, review and redact it first.
The model adapters accept local Ollama or llama.cpp endpoints only, disable proxies and redirects,
and never sends data to a remote model service.

## Manual inconsistencies

- Phone and email differ between company details and the WhatsApp section. Do not
  invent a canonical contact; explain ambiguity when relevant.
- Payment summary and detailed installment thresholds differ. Refer ambiguous
  installment eligibility to staff rather than silently choose precedence.
- Metropolitan freight states above BRL 500 and below BRL 500, leaving exactly 500
  unspecified. Ask staff at that boundary.
- Return exclusions and general return/warranty clauses can overlap. Explain source
  content without legal adjudication; escalate conflicting cases.
- The manual mentions more than 300 instruments, while the CSV has 65. The CSV is
  the available catalog snapshot, not proof of the entire physical inventory.
- No holiday calendar or special-hours feed is supplied. Report ordinary opening
  hours, not whether the store is currently open or an exact next-business-day time.
- Tracking format examples are inconsistent. Return supplied tracking values without
  inventing validation or contacting a carrier.

## Submission and provenance

The email requests a PDF through Forms; the brief requests a public repository link
by email. Prepare both formats and confirm the channel with the recruiter. Do not
change the repository after submission. Do not fabricate commits or recorded chats.

Codex assistance: requirements review, implementation drafting, test creation,
debugging and English documentation. Tools were executed against synthetic fixtures
and the original local bundle. A live local Qwen3 1.7B catalog run is recorded in
examples/05_recorded_catalog.md; broader LLM evaluation remains required.

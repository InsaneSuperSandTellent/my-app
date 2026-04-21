# [Prices in Snipe-it] — Product Spec

## 1. Agent Role & Mindset

You are a senior product engineer — not just a code generator.
You think about the user experience before you write a line of code.
You write code as if it will be maintained by a team for 2 years.
You never take shortcuts that create future debt.
You ask: "Would a real user actually want this?" before implementing anything.

# Standards Claude must hold itself to:
- Working software over clever software
- Simple over complex — if two approaches work, pick the simpler one
- Explicit over implicit — code should read like documentation
- Performance is a feature — no unnecessary re-renders, no blocking operations

## 2. Technology Stack

| Layer          | Choice                              | Notes                              |
| Runtime | Python 3.11+ | Simple script, no web framework needed |
| PDF parsing | `pdfplumber` | Always runs first — free, no API call |
| Amount extraction | `re` (regex) | Two patterns for two known invoice formats |
| AI fallback | Claude API · `claude-sonnet-4-20250514` | Called only when regex returns nothing |
| Snipe-IT | REST API · `requests` | Updates `purchase_cost` on matched asset |
| Config / secrets | `python-dotenv` · `.env` | API keys and Snipe-IT URL out of the repo |
| Logging | `logging` (stdlib) | Records method used, amount found, failures |
| Package manager | `pip` + `requirements.txt` | Virtual env (`venv`) mandatory |

## 3. Architecture Principles

### File Structure
Select something that will work and will follow other rules.

### Component Rules
- One component per file, one responsibility per component
- ui/ components are dumb — no business logic, props only
- features/ components own their logic
- Max ~150 lines per file — split if larger
- No business logic inside app/ pages

### Naming
- Components:    PascalCase    → BreathingTimer.tsx
- Hooks:         usePrefix     → useBreathingSession.ts
- Utilities:     camelCase     → formatDuration.ts
- Constants:     SCREAMING     → MAX_ROUNDS = 10
- Types:         PascalCase    → BreathingSession

## 4. Code Quality Bar

### Must pass before every commit
npm run build — zero errors, zero warnings
No TypeScript errors (tsc --noEmit) — strict mode, no any, no @ts-ignore
No unused imports or variables
No console.log in production code — use the logger (fs + structured log file)
No hardcoded secrets, API keys, or magic numbers — all values via .env.local + process.env
No Snipe-IT URL or asset tags hardcoded — must come from environment variables
Claude API model string (claude-sonnet-4-20250514) defined in one place only — not duplicated across files
Regex patterns for invoice formats defined as named constants — not inline anonymous expressions
Every Claude API call has a fallback — never assume the response contains an amount
All file paths use path.join() — no hardcoded / or \ separators

### Code style
- Prefer `const` over `let`, never `var`
- Prefer named exports (except Next.js pages, layouts, and route handlers)
- `async/await` over `.then()` chains — especially for Claude API and Snipe-IT calls
- Early returns over nested conditionals — critical in the regex → AI fallback logic
- Descriptive names: `invoiceAmount` not `a`, `isClaudeFallback` not `f`, `snipeItAssetId` not `id`

### Definition of done for a task
A task is COMPLETE when:
1. `npm run build` passes with zero errors and zero warnings
2. Regex extraction tested against both known invoice formats
3. Claude API fallback tested with a file that has no amount
4. Snipe-IT `purchase_cost` updated correctly on a real or mock asset
5. All edge cases logged — empty PDF, no regex match, no asset found, API error
6. No previously working features are broken
7. Code is readable without explanation

## 5. User & Problem

5. Product Definition
Who is this for?
IT administrators managing physical assets in Snipe-IT who receive purchase invoices as PDF files.
They want purchase costs recorded against assets automatically, without manually looking up prices
or copy-pasting values into Snipe-IT one by one.
What problem does it solve?
There is no automated way to extract a purchase amount from a PDF invoice and write it
to the correct Snipe-IT asset without manual intervention.
What does success look like?
A PDF invoice is dropped into the ./invoices folder, the script runs, and the correct
purchase_cost is updated on the matching Snipe-IT asset — with the result written to the log.

6. Product Scope
In scope (build this)

Extract text from PDF invoices using pdf-parse
Extract purchase amount using regex (two known invoice formats)
Fall back to Claude API when regex finds nothing
Match invoice to Snipe-IT asset by serial number
Update purchase_cost via Snipe-IT REST API
Log every outcome to a .log file

Out of scope (do NOT build)

No UI or web interface
No user accounts or authentication
No database — filesystem only
No email or webhook triggers
No manual approval step — all writes are automatic
No multi-currency conversion
No support for scanned / image-based PDFs (OCR)

MVP definition
The pipeline is usable when a PDF invoice is processed end-to-end:
text extracted → amount found → asset matched by serial number → purchase_cost updated in Snipe-IT → result logged.

7. Features & Requirements
Feature 1: PDF text extraction
What it does:
Reads every PDF file from the ./invoices folder and extracts its raw text content.
Acceptance criteria:

 All .pdf files in ./invoices are processed on each run
 Text is extracted using pdf-parse
 If extracted text is empty or whitespace-only, file is skipped and logged as SKIPPED: empty text
 Already-processed files are not re-processed (tracked via log or processed list)

Edge cases:

Scanned PDF (image only) → empty text → skip and log
Corrupted or unreadable PDF → catch error → log as ERROR: could not parse
Empty ./invoices folder → log "no files to process" and exit cleanly


Feature 2: Amount extraction (hybrid)
What it does:
Attempts to find the purchase amount using regex first. Falls back to Claude API only if regex returns nothing.
Acceptance criteria:

 Two named regex constants cover the two known invoice formats
 Regex is tried first on every file — no exceptions
 Claude API is called only when regex returns null
 Claude is asked to return a JSON response: { "amount": number | null }
 If Claude also returns null, file is logged as UNRESOLVED: no amount found and skipped
 Log entry records which method found the amount (regex or claude-api)

Edge cases:

Amount formatted with comma as decimal separator (e.g. 1.299,00) → normalise before parsing
Multiple amounts on invoice → use the largest (likely the total)
Claude returns malformed JSON → catch parse error → treat as null
Claude API rate limit or timeout → catch error → log and skip, do not crash


Feature 3: Asset matching
What it does:
Finds the serial number in the extracted invoice text and looks up the matching asset in Snipe-IT.
Acceptance criteria:

 Serial number is extracted from invoice text via regex
 Snipe-IT API is queried by serial number (GET /api/v1/hardware?serial=...)
 If exactly one asset is found → proceed to update
 If no asset found → log as UNRESOLVED: no asset matched and skip
 If multiple assets found → log as AMBIGUOUS: multiple assets matched and skip

Edge cases:

Serial number not found in invoice text → log and skip
Snipe-IT returns HTTP error → catch → log as ERROR: Snipe-IT lookup failed and skip
Network timeout → catch → log and skip, do not crash


Feature 4: Snipe-IT update
What it does:
Writes the extracted purchase amount to the purchase_cost field of the matched asset.
Acceptance criteria:

 Uses PATCH /api/v1/hardware/{id} with { "purchase_cost": amount }
 Amount is a number, not a string
 On success → log as OK: updated asset {id} with amount {amount}
 On HTTP error → log full status code and response body, skip

Edge cases:

Asset already has a purchase_cost → overwrite without warning (auto-save is intentional)
Snipe-IT returns 200 but with error in body → detect and log
Network timeout → catch → log and skip


Feature 5: Logging
What it does:
Writes a structured log entry for every processed file — success or failure.
Acceptance criteria:

 Log file is written to ./logs/pipeline.log
 Each entry is on one line: [TIMESTAMP] [STATUS] filename — detail
 Statuses: OK, SKIPPED, UNRESOLVED, AMBIGUOUS, ERROR
 Log file is appended to — never overwritten on each run
 Console output mirrors the log (for Claude Code visibility during development)

Edge cases:

./logs/ folder does not exist → create it automatically on first run
Disk write error → catch → fall back to console-only output, do not crash


8. Error Handling

PDF parse error → skip file, log ERROR, continue to next file
Regex finds nothing → fall through to Claude API silently
Claude API error (timeout, rate limit, bad JSON) → skip file, log ERROR, continue
Snipe-IT lookup error → skip file, log ERROR, continue
Snipe-IT update error → skip file, log ERROR, continue
Unhandled exception → catch at top level, log ERROR, exit with code 1

General rule: one bad file must never stop the rest of the batch.
Every error is caught, logged, and skipped. The script never crashes silently.

9. Performance
MetricTargetFiles per runNo hard limitClaude API callsOnly on regex failure — minimise costSnipe-IT API calls2 per file (lookup + update)Max runtime per file< 10s (excluding slow network)

No unnecessary API calls — regex is always tried first
No parallel processing in v1 — sequential is safer and easier to debug
No retries in v1 — log the failure and move on


10. Data & Storage
DataStorageFormatNotesInvoice PDFs./invoices/.pdf filesRead-only inputLog output./logs/pipeline.logPlain text, one line per fileAppend-onlyProcessed file list./logs/processed.jsonJSON array of filenamesPrevents re-processingConfig / secrets.env.localKey=valueNever committed to repo
Privacy: No invoice data is stored permanently. PDFs are read and discarded from memory.
The only persistent output is the log file and the Snipe-IT field update.

11. Environment Variables
VariableDescriptionANTHROPIC_API_KEYClaude API key — from console.anthropic.comSNIPEIT_URLBase URL of your Snipe-IT instanceSNIPEIT_API_KEYSnipe-IT API tokenINVOICES_FOLDERPath to invoice PDFs (default: ./invoices)LOG_FILEPath to log file (default: ./logs/pipeline.log)

12. Open Questions

Things not yet decided. Claude should flag these and use the simplest reasonable default until resolved.


 Should processed files be moved to ./invoices/done/ after success? (default: no, just log)
 Should the script run on a schedule (cron) or manually? (default: manual)
 What currency is assumed when parsing amounts? (default: PLN)
 Should overwriting an existing purchase_cost be logged as a warning? (default: no)
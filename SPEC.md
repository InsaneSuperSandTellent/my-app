# Prices in Snipe-IT — Product Spec

## 1. Agent Role & Mindset

You are a senior product engineer — not just a code generator.
You think about the user experience before you write a line of code.
You write code as if it will be maintained by a team for 2 years.
You never take shortcuts that create future debt.
You ask: "Would a real user actually want this?" before implementing anything.

**Standards to hold yourself to:**
- Working software over clever software
- Simple over complex — if two approaches work, pick the simpler one
- Explicit over implicit — code should read like documentation
- Reliability is a feature — one bad file must never crash the batch

---

## 2. Technology Stack

| Layer | Choice | Notes |
|---|---|---|
| Runtime | Python 3.11+ | Simple script, no web framework needed |
| PDF parsing | `pdfplumber` | Always runs first — free, no API call |
| Amount extraction | `re` (regex) | Two patterns for two known invoice formats |
| AI fallback | Claude API · `anthropic` SDK · model `claude-sonnet-4-5` | Called only when regex returns nothing, or for price lookup during audit |
| Snipe-IT | REST API · `requests` | Reads assets, updates `purchase_cost` |
| Config / secrets | `python-dotenv` · `.env` | API keys and Snipe-IT URL out of the repo |
| Logging | `logging` (stdlib) + file handler | Records method used, amount found, failures |
| Package manager | `pip` + `requirements.txt` | Virtual env (`venv`) mandatory |

---

## 3. Architecture Principles

### File structure
```
my-app/
├── main.py                 # entry point — runs PDF flow then audit flow
├── requirements.txt
├── .env                    # secrets — NEVER commit
├── invoices/               # input PDFs
├── logs/
│   ├── pipeline.log
│   └── processed.json
└── src/
    ├── __init__.py
    ├── config.py           # loads env vars, exports constants
    ├── logger.py           # log_ok, log_skipped, log_unresolved, log_ambiguous, log_error
    ├── pdf_extractor.py    # pdfplumber wrapper
    ├── amount_extractor.py # regex → Claude fallback
    ├── serial_extractor.py # finds S/N in invoice text
    ├── snipeit_client.py   # all Snipe-IT API calls
    ├── price_lookup.py     # Claude web-search for launch/market price
    ├── pipeline.py         # PDF → Snipe-IT flow (per file)
    ├── audit.py            # Snipe-IT → price lookup flow (per asset)
    └── processed_tracker.py
```

### Module rules
- One responsibility per module, one module per concern
- `snipeit_client.py` is the ONLY file that talks to Snipe-IT — no `requests.get(SNIPEIT_URL...)` scattered anywhere else
- `price_lookup.py` is the ONLY file that asks Claude for prices
- `logger.py` is the ONLY file that writes to the log — no `print()` in production code
- Max ~150 lines per file — split if larger
- `main.py` contains orchestration only — no business logic

### Naming
- Modules: `snake_case` → `amount_extractor.py`
- Functions: `snake_case` → `extract_amount()`, `lookup_by_serial()`
- Constants: `SCREAMING_SNAKE` → `MAX_RETRIES`, `INVOICES_FOLDER`, `LAPTOP_CATEGORY_IDS`
- Custom exceptions: `PascalCase` → `AssetNotFoundError`, `SnipeITError`
- Type hints everywhere — no untyped function signatures

---

## 4. Code Quality Bar

### Must pass before every commit
- `python3 main.py` runs without unhandled exceptions on an empty `./invoices` folder
- `python3 -m py_compile $(find . -name "*.py")` — zero syntax errors
- No `print()` in production code — use the logger
- No `TODO`, `FIXME`, `XXX` comments left in committed code
- No hardcoded secrets, API keys, URLs, or asset IDs — all values via `.env`
- Claude model string (`claude-sonnet-4-5`) defined in `config.py` only — not duplicated
- Regex patterns for invoice formats defined as named constants in `amount_extractor.py`
- Every Claude API call is wrapped in try/except — never assume the response is valid JSON
- Every Snipe-IT API call is wrapped in try/except with custom exceptions
- All file paths use `pathlib.Path` — no string concatenation with `/` or `\`
- Type hints on every function signature — no missing or `Any` types

### Code style
- Prefer `Path` objects over strings for filesystems
- `f-strings` for formatting, never `%` or `.format()`
- Early returns over nested conditionals — critical in regex → Claude → log chains
- Guard clauses at the top of functions — invalid inputs return early
- Descriptive names: `invoice_amount` not `a`, `used_fallback` not `f`, `snipe_asset_id` not `id`
- Imports grouped: stdlib → third-party → local, separated by blank lines
- Every module imports only what it needs — no wildcard imports

### Definition of done for a task
A task is COMPLETE when:
1. Script runs end-to-end without unhandled exceptions
2. Regex extraction tested against both known invoice formats (add a test PDF if missing)
3. Claude API fallback tested with a PDF that has no amount
4. Audit flow tested on at least one laptop and one phone with missing `purchase_cost`
5. Snipe-IT `purchase_cost` is actually updated and verified via API read-back
6. All new error paths logged with appropriate status (OK/SKIPPED/UNRESOLVED/AMBIGUOUS/ERROR)
7. No previously working features are broken
8. Code is readable without explanation

---

## 5. User & Problem

### Who is this for?
IT administrators managing laptops and phones in Snipe-IT who need `purchase_cost` filled in
across their asset inventory — either from incoming invoices, or by reconciling assets that
were added without a price.

### What problem does it solve?
There is no automated way to (a) extract purchase amounts from PDF invoices into Snipe-IT,
or (b) backfill missing prices on existing laptop and phone assets using external price data.
Both tasks are currently manual and do not scale.

### What does success look like?
A single `python3 main.py` run:
1. Processes every new PDF in `./invoices`, extracting the amount and writing it to the matching Snipe-IT asset
2. Then scans all laptops and phones in Snipe-IT, finds any without `purchase_cost`, looks up the likely price, and writes it

The result: Snipe-IT inventory has consistent pricing data, with zero manual data entry.

---

## 6. Product Scope

### In scope (build this)
- **PDF flow:** Extract text from PDFs in `./invoices`, find the amount (regex → Claude fallback), match to asset by serial number, update `purchase_cost`
- **Audit flow:** List all laptops and phones in Snipe-IT, filter those with missing/null/zero `purchase_cost`, look up the likely price via Claude web search, update `purchase_cost`
- Log every outcome to `./logs/pipeline.log`
- Track processed PDFs in `./logs/processed.json` to avoid re-work
- Auto-save every found price — no manual approval step

### Out of scope (do NOT build)
- No UI or web interface
- No user accounts or authentication
- No database — filesystem only
- No email or webhook triggers
- No multi-currency conversion (assume PLN)
- No OCR for scanned / image-based PDFs
- No price estimation for categories other than laptops and phones
- No retry logic in v1 — log the failure and move on

### MVP definition
The pipeline is usable when both flows run end-to-end on real data:
- At least one PDF in `./invoices` is processed and its amount written to the correct Snipe-IT asset
- At least one laptop or phone without `purchase_cost` gets a price written after the audit pass

---

## 7. Features & Requirements

### Feature 1: PDF text extraction

**What it does:**
Reads every PDF file from `./invoices` and extracts its raw text content.

**Acceptance criteria:**
- [ ] All `.pdf` files in `./invoices` are processed on each run
- [ ] Text is extracted using `pdfplumber`
- [ ] If extracted text is empty or whitespace-only, file is skipped and logged as `SKIPPED: empty text`
- [ ] Already-processed files (listed in `processed.json`) are not re-processed

**Edge cases:**
- Scanned PDF (image only) → empty text → skip and log
- Corrupted or unreadable PDF → catch error → log as `ERROR: could not parse`
- Empty `./invoices` folder → log "no files to process" and proceed to audit flow

---

### Feature 2: Amount extraction (hybrid)

**What it does:**
Finds the purchase amount in the extracted text — regex first, Claude API as fallback.

**Acceptance criteria:**
- [ ] Two named regex constants cover the two known invoice formats
- [ ] Regex is tried first on every file — no exceptions
- [ ] Claude API is called only when regex returns `None`
- [ ] Claude is asked to return JSON: `{"amount": number | null}`
- [ ] If Claude also returns `null`, file is logged as `UNRESOLVED: no amount found` and skipped
- [ ] Log entry records which method found the amount (`regex` or `claude-api`)

**Edge cases:**
- Amount formatted with comma as decimal (e.g. `1.299,00`) → normalise before parsing
- Multiple amounts on invoice → use the largest (likely the total)
- Claude returns malformed JSON → catch parse error → treat as `None`
- Claude API rate limit or timeout → catch → log and skip, do not crash

---

### Feature 3: Asset matching by serial number

**What it does:**
Finds the serial number in the extracted invoice text and looks up the matching Snipe-IT asset.

**Acceptance criteria:**
- [ ] Serial number is extracted from invoice text via regex
- [ ] Snipe-IT API is queried by serial (`GET /api/v1/hardware?serial=...`)
- [ ] Exactly one asset found → proceed to update
- [ ] No asset found → log as `UNRESOLVED: no asset matched` and skip
- [ ] Multiple assets found → log as `AMBIGUOUS: multiple assets matched` and skip

**Edge cases:**
- Serial not in invoice text → log and skip
- Snipe-IT HTTP error → catch → log as `ERROR: Snipe-IT lookup failed` and skip
- Network timeout → catch → log and skip

---

### Feature 4: Snipe-IT update

**What it does:**
Writes the extracted purchase amount to the `purchase_cost` field of the matched asset.

**Acceptance criteria:**
- [ ] Uses `PATCH /api/v1/hardware/{id}` with `{"purchase_cost": amount}`
- [ ] Amount is a number, not a string
- [ ] On success → log as `OK: updated asset {id} with amount {amount} via {method}`
- [ ] On HTTP error → log status code and response body, skip

**Edge cases:**
- Asset already has a `purchase_cost` → overwrite without warning (auto-save is intentional)
- Snipe-IT returns 200 with error in body → detect and log
- Network timeout → catch → log and skip

---

### Feature 5: Audit flow — backfill missing prices

**What it does:**
After PDF processing, scans all laptops and phones in Snipe-IT. For every asset missing a `purchase_cost`,
asks Claude to find the likely launch price or current market price based on model name. Writes the result.

**Acceptance criteria:**
- [ ] Fetches all assets in category IDs listed in `LAPTOP_CATEGORY_IDS` and `PHONE_CATEGORY_IDS` (env vars)
- [ ] Pagination handled — script walks all pages, not just the first
- [ ] Filters assets where `purchase_cost` is null, missing, zero, or empty string
- [ ] For each such asset, extracts model name / manufacturer from the asset record
- [ ] Calls Claude with web search enabled, asking for the launch price in PLN
- [ ] Claude returns JSON: `{"amount": number | null, "source": "launch_price" | "market_estimate" | "deduced_from_similar", "confidence": "high" | "medium" | "low"}`
- [ ] If `amount` is a valid number → update `purchase_cost` via Snipe-IT API (auto-save)
- [ ] If `amount` is null → log `UNRESOLVED: could not determine price for asset {id}`
- [ ] Log entry always records source and confidence level

**Edge cases:**
- Claude can't find a specific model → tries to deduce from similar/same product line → logs `deduced_from_similar`
- Claude returns non-JSON response → catch → log and skip
- Snipe-IT paginated response with >1000 assets → handle pagination correctly
- Asset has `purchase_cost` = 0 → treat as missing and attempt to backfill
- Rate limit on Claude API → catch → log and skip that asset, continue with next

---

### Feature 6: Logging

**What it does:**
Writes a structured log entry for every processed item — success or failure — in both flows.

**Acceptance criteria:**
- [ ] Log file is `./logs/pipeline.log`
- [ ] Each entry is one line: `[TIMESTAMP] [STATUS] source — detail`
  - `source` = PDF filename for PDF flow, `asset:{id}` for audit flow
- [ ] Statuses: `OK`, `SKIPPED`, `UNRESOLVED`, `AMBIGUOUS`, `ERROR`
- [ ] Log file is appended — never overwritten
- [ ] Console output mirrors the log (for visibility during long audit runs)

**Edge cases:**
- `./logs/` does not exist → create it automatically on first run
- Disk write error → fall back to console-only output, do not crash

---

## 8. Error Handling

- PDF parse error → skip file, log `ERROR`, continue
- Regex finds nothing → fall through to Claude API silently
- Claude API error (timeout, rate limit, bad JSON) → skip item, log `ERROR`, continue
- Snipe-IT lookup error → skip item, log `ERROR`, continue
- Snipe-IT update error → skip item, log `ERROR`, continue
- Unhandled exception → catch at top level of `main.py`, log `ERROR`, exit with code 1

**General rule:** one bad file or asset must never stop the rest of the batch.
Every error is caught, logged, and skipped. The script never crashes silently.

---

## 9. Performance & Limits

| Metric | Target |
|---|---|
| PDFs per run | No hard limit |
| Audit assets per run | No hard limit, but paginate safely |
| Claude API calls (PDF flow) | Only on regex failure |
| Claude API calls (audit flow) | One per asset missing price |
| Snipe-IT API calls | 2 per item (lookup + update) for PDF flow; 1 list + 1 update per asset for audit |
| Max runtime per item | < 15s |

Rules:
- Regex always tried first — Claude is fallback only
- No parallel processing in v1 — sequential is safer and easier to debug
- No retries in v1 — log failure and move on
- Rate-limit the audit flow to max 1 Claude API call per second to stay under API limits

---

## 10. Data & Storage

| Data | Storage | Format | Notes |
|---|---|---|---|
| Invoice PDFs | `./invoices/` | `.pdf` files | Read-only input |
| Log output | `./logs/pipeline.log` | Plain text, one line per event | Append-only |
| Processed file list | `./logs/processed.json` | JSON array of filenames | Prevents re-processing PDFs |
| Config / secrets | `.env` | Key=value | Never committed to repo |

**Privacy:** No invoice data or asset data is stored permanently outside the log file.
PDFs and Snipe-IT responses are held in memory only during processing.

---

## 11. Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key — from console.anthropic.com |
| `SNIPEIT_URL` | Base URL of your Snipe-IT instance |
| `SNIPEIT_API_KEY` | Snipe-IT API token |
| `INVOICES_FOLDER` | Path to invoice PDFs (default: `./invoices`) |
| `LOG_FILE` | Path to log file (default: `./logs/pipeline.log`) |
| `LAPTOP_CATEGORY_IDS` | Comma-separated Snipe-IT category IDs for laptops |
| `PHONE_CATEGORY_IDS` | Comma-separated Snipe-IT category IDs for phones |
| `CLAUDE_MODEL` | Claude model string (default: `claude-sonnet-4-5`) |

---

## 12. Open Questions

> Not yet decided. Use the simplest reasonable default until resolved.

- [ ] Should processed PDFs be moved to `./invoices/done/` after success? (default: no, just track in `processed.json`)
- [ ] Should the script run on a schedule (cron) or manually? (default: manual)
- [ ] What currency is assumed? (default: PLN)
- [ ] Should audit flow re-check assets already priced by AI in a previous run? (default: no — skip any asset with `purchase_cost` set, regardless of source)
- [ ] Should there be a `--dry-run` flag that logs proposed updates without writing? (default: no in v1, but architecture should make it easy to add)

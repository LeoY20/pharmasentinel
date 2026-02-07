
# PharmaSentinel — Implementation Guide for Coding Agents

> **Purpose**: This document is the complete specification for building a hospital pharmacy supply chain intelligence platform. It is written for AI coding agents (e.g., Claude Code) to implement from scratch. It contains NO code — only architecture, schemas, data flows, agent specifications, API contracts, and frontend requirements.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Technology Stack & Environment](#3-technology-stack--environment)
4. [Database Schema (Supabase)](#4-database-schema-supabase)
5. [Agent Specifications](#5-agent-specifications)
6. [Pipeline Orchestration](#6-pipeline-orchestration)
7. [Frontend Dashboard](#7-frontend-dashboard)
8. [File Structure](#8-file-structure)
9. [Seed Data](#9-seed-data)
10. [Error Handling & Edge Cases](#10-error-handling--edge-cases)
11. [Build Order](#11-build-order)

---

## 1. Project Overview

### What the App Does

A hospital pharmacy management system that uses a multi-agent AI pipeline to:

- **Identify and predict drug shortages** before they impact patient care
- **Find clinically appropriate substitutes** when a drug is unavailable
- **Identify vulnerabilities** in the pharmaceutical supply chain (FDA data + news analysis)
- **Suggest restocks and generate automatic purchase orders** from suppliers or nearby hospitals
- **Optimize surgery scheduling** around drug availability

### Core Decision the System Makes

> "When and what to order? How to switch to alternatives, order backups, change schedules, etc. to ensure that hospital operations can occur as efficiently as possible."

### The 10 Monitored Critical Drugs (Ranked by Criticality)

These drugs are the system's primary focus. The criticality ranking determines alert priority and decision urgency. Every agent must be aware of this ranking.

| Rank | Drug | Type/Use | Why Critical |
|------|------|----------|--------------|
| 1 | Epinephrine (Adrenaline) | Anaphylaxis / Cardiac Arrest | Immediate life-saving; minutes matter |
| 2 | Oxygen | Respiratory Support | No substitute exists; sustains life in respiratory distress |
| 3 | Levofloxacin | Broad-Spectrum Antibiotic | Critical for serious bacterial infections |
| 4 | Propofol | Anesthetic | All surgeries halt without anesthetics |
| 5 | Penicillin | Antibiotic | Foundational antibiotic for pneumonia and infections |
| 6 | IV Fluids | Hydration / Shock / Blood Loss | Essential for dehydration, shock, blood loss treatment |
| 7 | Heparin / Warfarin | Anticoagulant | Prevents blood clots, strokes, heart attacks |
| 8 | Insulin | Diabetes / DKA Management | Critical for acute diabetic ketoacidosis |
| 9 | Morphine | Analgesic / Pain Management | Vital for palliative care and severe injury |
| 10 | Vaccines (e.g., Smallpox, Polio) | Immunization | Critical long-term but less acute in hospital setting |

### Input Data the System Consumes

- **Hospital surgery schedule**: Upcoming surgeries with drug requirements per procedure
- **Current drug storage/inventory**: What is in stock right now, quantities, units
- **Hospital location**: Used for finding nearby suppliers and partner hospitals
- **FDA Drug Shortage Database**: External API, queried with 6-month sliding window
- **News articles**: Scanned for supply chain disruption signals

---

## 2. Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + TypeScript)                    │
│                                                                         │
│  ┌────────────────┐  ┌─────────────────────┐  ┌──────────────────────┐ │
│  │  Dashboard:     │  │  Alerts Page:        │  │  Drugs Page:         │ │
│  │  Summary cards  │  │  Warnings & Risks    │  │  All 10 drugs with   │ │
│  │  Top actions    │  │  Suggested actions   │  │  usage rate, stock,  │ │
│  │  Risk overview  │  │  Acknowledge/dismiss │  │  prediction, chart   │ │
│  └────────────────┘  └─────────────────────┘  └──────────────────────┘ │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                    Supabase JS Client (Realtime + REST)
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                       SUPABASE (PostgreSQL + Realtime)                  │
│                                                                         │
│   drugs │ shortages │ suppliers │ substitutes │ agent_logs │ alerts     │
│                         │ surgery_schedule                              │
└────────────────────────────────▲────────────────────────────────────────┘
                                 │
                    Python Backend (reads/writes via Supabase client)
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                        PIPELINE ORCHESTRATOR                            │
│                                                                         │
│   Phase 1 (parallel):  Agent 0 + Agent 1 + Agent 2                     │
│         │                    │                 │                         │
│         └──── all write to ──┴── agent_logs ───┘                        │
│                                    │                                    │
│   Phase 2 (sequential):    Overseer Agent                               │
│                     reads agent_logs, produces decisions                 │
│                                    │                                    │
│   Phase 3 (conditional):   Agent 3 (if substitutes needed)             │
│                                    │                                    │
│   Phase 4 (conditional):   Agent 4 (if orders needed)                  │
│                                    │                                    │
│   Final: Overseer writes alerts to `alerts` table                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Flow in Plain Language

1. Hospital staff inputs surgery schedule, current inventory, and hospital location via the frontend (or these are pre-loaded in Supabase).
2. The pipeline orchestrator generates a unique `run_id` (UUID) and launches Phase 1.
3. **Agent 0** reads the `drugs` and `surgery_schedule` tables, computes burn rates and predictions, writes structured JSON to `agent_logs`.
4. **Agent 1** queries the FDA Drug Shortage API for unresolved shortages in a 6-month window, writes findings to `agent_logs`.
5. **Agent 2** queries a news API for articles about the 10 monitored drugs + pharma supply chain, analyzes sentiment and risk, writes findings to `agent_logs`.
6. All three agents run **in parallel** and all tag their output with the same `run_id`.
7. The **Overseer Agent** reads all `agent_logs` rows for the current `run_id`, synthesizes the intelligence, and decides: which drugs need substitutes? Which need restock orders? Are any surgeries at risk?
8. If substitutes are needed → **Agent 3** is invoked with the list of drugs. It looks up the hard-coded substitution mappings + consults the `substitutes` table + uses the LLM for clinical reasoning. It writes results to `substitutes` table and `agent_logs`.
9. If orders are needed → **Agent 4** is invoked with the list of drugs + quantities + urgency. It checks the `suppliers` table (which includes nearby hospitals), selects optimal suppliers, and writes order recommendations to `agent_logs`.
10. The Overseer writes final **alerts** to the `alerts` table.
11. The frontend subscribes to Supabase Realtime on the `alerts` and `drugs` tables and updates the dashboard live.

---

## 3. Technology Stack & Environment

### Backend (Python)

- **Python 3.11+**
- **supabase-py**: Supabase client for Python (`pip install supabase`)
- **requests**: HTTP calls to FDA API, News API, Dedalus API
- **asyncio**: Parallel execution of Phase 1 agents
- **python-dotenv**: Environment variable loading
- **FastAPI** (optional): If you want a manual trigger API endpoint for the pipeline

### Frontend (TypeScript)

- **React 18+** with TypeScript
- **Vite** as the build tool (use `npm create vite@latest -- --template react-ts`)
- **@supabase/supabase-js**: Supabase client for the browser
- **recharts**: Charts for drug usage trends and predictions
- **lucide-react**: Icon library
- **Tailwind CSS**: Styling
- **react-router-dom**: Client-side routing

### Infrastructure

- **Supabase**: Hosted PostgreSQL database with Realtime subscriptions, connected via project URL + anon key (frontend) and service role key (backend)
- **Dedalus**: LLM provider for all agent reasoning. 3 API keys available. Each agent call sends a system prompt + user prompt and receives structured JSON.
- **NewsAPI** (newsapi.org): For fetching recent pharma/drug-related news articles
- **FDA openFDA API** (api.fda.gov): For drug shortage data

### Environment Variables

The `.env` file must contain:

| Variable | Used By | Description |
|----------|---------|-------------|
| `SUPABASE_URL` | Backend + Frontend | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Backend only | Service role key (bypasses RLS) |
| `SUPABASE_ANON_KEY` | Frontend only | Anon key (respects RLS) |
| `DEDALUS_API_KEY_1` | Agents 0, 1 | First Dedalus API key |
| `DEDALUS_API_KEY_2` | Agent 2, Overseer | Second Dedalus API key |
| `DEDALUS_API_KEY_3` | Agents 3, 4 | Third Dedalus API key |
| `NEWS_API_KEY` | Agent 2 | NewsAPI.org key |
| `HOSPITAL_LOCATION` | Overseer, Agent 4 | Default hospital location string |

### API Key Distribution Strategy

We have exactly 3 Dedalus API keys. To avoid rate limits when agents run in parallel:

| Key | Assigned Agents | Rationale |
|-----|----------------|-----------|
| Key 1 | Agent 0 (Inventory), Agent 1 (FDA) | Both run in Phase 1 parallel, but Agent 1 is lightweight (less token usage) |
| Key 2 | Agent 2 (News), Overseer | Agent 2 in Phase 1; Overseer in Phase 2 — never concurrent |
| Key 3 | Agent 3 (Substitutes), Agent 4 (Orders) | Both in Phase 3/4, run sequentially — never concurrent |

---

## 4. Database Schema (Supabase)

### Table: `drugs`

The primary inventory table. One row per monitored drug.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, auto-generated | |
| `name` | TEXT | NOT NULL | Drug name (e.g., "Epinephrine") |
| `type` | TEXT | NOT NULL | Category (e.g., "Anaphylaxis/Cardiac") |
| `stock_quantity` | NUMERIC | NOT NULL, DEFAULT 0 | Current units in storage |
| `unit` | TEXT | NOT NULL, DEFAULT 'units' | "units", "mL", "vials", etc. |
| `price_per_unit` | NUMERIC(10,2) | NULLABLE | Cost per unit in USD |
| `primary_supplier_id` | UUID | FK → suppliers.id, NULLABLE | |
| `usage_rate_daily` | NUMERIC | NOT NULL, DEFAULT 0 | Average daily consumption |
| `predicted_usage_rate` | NUMERIC | NULLABLE | Agent-computed predicted daily rate |
| `burn_rate_days` | NUMERIC | NULLABLE | stock_quantity / usage_rate_daily |
| `predicted_burn_rate_days` | NUMERIC | NULLABLE | stock_quantity / predicted_usage_rate |
| `reorder_threshold_days` | INTEGER | DEFAULT 14 | Alert when burn_rate drops below this |
| `criticality_rank` | INTEGER | CHECK 1–10 | From the critical drugs ranking above |
| `last_restock_date` | TIMESTAMPTZ | NULLABLE | |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | |

### Table: `shortages`

Tracks known shortages from FDA + news + internal detection.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `drug_name` | TEXT | NOT NULL | Matches drugs.name |
| `drug_id` | UUID | FK → drugs.id, NULLABLE | |
| `type` | TEXT | | "FDA_REPORTED", "NEWS_INFERRED", "INTERNAL" |
| `source` | TEXT | NOT NULL | "FDA", "Reuters", etc. |
| `source_url` | TEXT | NULLABLE | Link to original source |
| `impact_severity` | TEXT | CHECK IN ('LOW','MEDIUM','HIGH','CRITICAL') | |
| `description` | TEXT | NULLABLE | Human-readable summary |
| `reported_date` | DATE | NOT NULL | |
| `resolved` | BOOLEAN | DEFAULT FALSE | |
| `resolved_date` | DATE | NULLABLE | |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |

Index: Create index on `(resolved, reported_date DESC) WHERE resolved = FALSE` for fast unresolved-shortage queries.

### Table: `suppliers`

Includes both commercial suppliers AND nearby hospitals that can transfer drugs.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `name` | TEXT | NOT NULL | Supplier or hospital name |
| `drug_name` | TEXT | NOT NULL | Which drug they supply |
| `drug_id` | UUID | FK → drugs.id, NULLABLE | |
| `price_per_unit` | NUMERIC(10,2) | NULLABLE | |
| `location` | TEXT | NULLABLE | City/state/region |
| `lead_time_days` | INTEGER | NULLABLE | Typical delivery time |
| `reliability_score` | NUMERIC(3,2) | DEFAULT 1.00 | 0.00 to 1.00 |
| `contact_info` | TEXT | NULLABLE | |
| `is_nearby_hospital` | BOOLEAN | DEFAULT FALSE | TRUE = hospital partner, not vendor |
| `active` | BOOLEAN | DEFAULT TRUE | |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |

### Table: `substitutes`

Drug substitution mappings. One row per original→substitute pair.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `drug_id` | UUID | FK → drugs.id, NOT NULL | The drug being replaced |
| `drug_name` | TEXT | NOT NULL | Original drug name (for quick lookup) |
| `substitute_name` | TEXT | NOT NULL | Alternative drug name |
| `substitute_drug_id` | UUID | FK → drugs.id, NULLABLE | FK if we also stock it |
| `equivalence_notes` | TEXT | NULLABLE | Dosing conversion, caveats |
| `preference_rank` | INTEGER | DEFAULT 1 | 1 = best substitute |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |

Add a UNIQUE constraint on `(drug_name, substitute_name)` to allow upserts.

### Table: `agent_logs`

Temporary staging area. Every agent writes structured JSON here. The Overseer reads from here.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `agent_name` | TEXT | NOT NULL | "agent_0", "agent_1", "agent_2", "agent_3", "agent_4", "overseer" |
| `run_id` | UUID | NOT NULL | Groups all outputs from one pipeline execution |
| `payload` | JSONB | NOT NULL | Structured JSON output (schema varies per agent — see agent specs) |
| `summary` | TEXT | NULLABLE | Human-readable summary |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |

Index: Create index on `(run_id, agent_name)`.

### Table: `alerts`

Final actionable outputs displayed on the frontend.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `run_id` | UUID | NOT NULL | Which pipeline run produced this |
| `alert_type` | TEXT | NOT NULL, CHECK IN ('RESTOCK_NOW','SHORTAGE_WARNING','SUBSTITUTE_RECOMMENDED','SCHEDULE_CHANGE','SUPPLY_CHAIN_RISK','AUTO_ORDER_PLACED') | |
| `severity` | TEXT | NOT NULL, CHECK IN ('INFO','WARNING','URGENT','CRITICAL') | |
| `drug_id` | UUID | FK → drugs.id, NULLABLE | |
| `drug_name` | TEXT | NOT NULL | |
| `title` | TEXT | NOT NULL | Short headline |
| `description` | TEXT | NOT NULL | Full recommendation text |
| `action_payload` | JSONB | NULLABLE | Structured data (order details, etc.) |
| `acknowledged` | BOOLEAN | DEFAULT FALSE | |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |

Index: Create index on `(acknowledged, severity, created_at DESC) WHERE acknowledged = FALSE`.

### Table: `surgery_schedule`

Input data for burn rate calculations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `surgery_type` | TEXT | NOT NULL | |
| `scheduled_date` | DATE | NOT NULL | |
| `estimated_duration_hours` | NUMERIC | NULLABLE | |
| `drugs_required` | JSONB | NOT NULL | Array of `{"drug_name": str, "quantity": num, "unit": str}` |
| `status` | TEXT | DEFAULT 'SCHEDULED', CHECK IN ('SCHEDULED','COMPLETED','CANCELLED','RESCHEDULED') | |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |

### Row-Level Security

For the hackathon, enable RLS on all tables but create a permissive policy: `CREATE POLICY "Allow all" ON <table> FOR ALL USING (true)`. In production, scope to `hospital_id`.

---

## 5. Agent Specifications

### Shared Agent Infrastructure

Every agent needs access to:

1. **Supabase client** (using the service role key)
2. **Dedalus LLM client** (a function that takes system prompt + user prompt → returns string)
3. **`log_agent_output(agent_name, run_id, payload, summary)`** — utility function that inserts a row into `agent_logs`
4. **`MONITORED_DRUGS`** — the list of 10 drugs with names, types, and criticality rankings (defined as a constant)

Every Dedalus call must:
- Include a detailed system prompt specific to that agent's role
- End the system prompt with the exact JSON schema the LLM must respond with
- Instruct the LLM to respond with ONLY valid JSON and nothing else
- Use `temperature: 0.2` for deterministic outputs
- Parse the response as JSON with a fallback that strips markdown code fences (`\`\`\`json ... \`\`\``) before re-parsing

---

### Agent 0 — Inventory Analyzer & Burn Rate Calculator

**File**: `agents/agent_0_inventory.py`
**API Key**: Key 1 (index 0)
**Reads from DB**: `drugs`, `surgery_schedule`
**Writes to DB**: Updates `drugs` rows (predicted rates, burn rates); inserts into `agent_logs`

#### What It Does

1. Fetches the full `drugs` table (ordered by `criticality_rank`).
2. Fetches all `surgery_schedule` rows with `status = 'SCHEDULED'` in the next 30 days.
3. Computes basic burn rates locally: `stock_quantity / usage_rate_daily` for each drug.
4. Aggregates total drug demand from the surgery schedule (sum quantity per drug across all upcoming surgeries).
5. Sends all this data to Dedalus with a system prompt that instructs the LLM to:
   - Calculate predicted daily usage = current daily usage + (surgery demand ÷ 30)
   - Calculate predicted burn rate = stock / predicted daily usage
   - Flag any drug with burn_rate < 7 days as CRITICAL, < 14 days as HIGH
   - Identify specific surgeries that may be impacted by low stock
   - Consider the criticality ranking when assessing risk
6. Parses the JSON response.
7. Updates each drug's `predicted_usage_rate`, `burn_rate_days`, and `predicted_burn_rate_days` in the `drugs` table.
8. Writes the full analysis to `agent_logs`.

#### Expected LLM Output Schema

```json
{
    "drug_analysis": [
        {
            "drug_name": "string",
            "current_stock": 0,
            "daily_usage_rate": 0,
            "predicted_daily_usage_rate": 0,
            "burn_rate_days": 0,
            "predicted_burn_rate_days": 0,
            "trend": "INCREASING | STABLE | DECREASING",
            "risk_level": "LOW | MEDIUM | HIGH | CRITICAL",
            "notes": "string"
        }
    ],
    "schedule_impact": [
        {
            "surgery_date": "YYYY-MM-DD",
            "surgery_type": "string",
            "drugs_at_risk": ["drug_name"],
            "recommendation": "string"
        }
    ],
    "summary": "string"
}
```

#### System Prompt Must Include

- The full criticality ranking of the 10 drugs
- Instructions to prioritize higher-criticality drugs in analysis
- The exact JSON schema above with instructions to respond ONLY with valid JSON

---

### Agent 1 — FDA Drug Shortage Monitor

**File**: `agents/agent_1_fda.py`
**API Key**: Key 1 (index 0)
**External API**: openFDA (`api.fda.gov`)
**Reads from DB**: `shortages` (existing records)
**Writes to DB**: Inserts new rows into `shortages`; inserts into `agent_logs`

#### What It Does

1. Defines a 6-month sliding window: from `(today - 180 days)` to `today`.
2. Fetches existing unresolved shortages from the `shortages` table within this window.
3. Queries the openFDA API for each of the 10 monitored drug names. The openFDA API doesn't have a dedicated shortage endpoint, so the implementation should:
   - **Primary approach**: Query `https://api.fda.gov/drug/drugsfda.json` or `https://api.fda.gov/drug/label.json` searching by generic name
   - **Fallback**: If the FDA API doesn't return useful shortage data, the agent should note this and rely on its existing shortage DB + news (Agent 2)
   - **Important**: The implementer should check what FDA endpoints are actually available and adjust accordingly. The key thing is to query for shortage-related data per drug.
4. Sends both the existing shortages and the FDA API results to Dedalus with a system prompt asking the LLM to:
   - Match FDA data to our monitored drug list
   - Assess whether each shortage is ONGOING, RESOLVED, or WORSENING
   - Rate impact severity based on our criticality ranking
   - Identify any shortages the LLM knows about from its training data that might not appear in the API results
5. For each unresolved shortage the LLM identifies, inserts a row into the `shortages` table with `type = 'FDA_REPORTED'`.
6. Writes the full analysis to `agent_logs`.

#### Expected LLM Output Schema

```json
{
    "shortages_found": [
        {
            "drug_name": "string (matched to our monitored list)",
            "fda_drug_name": "string (exact FDA name)",
            "status": "ONGOING | RESOLVED | WORSENING",
            "impact_severity": "LOW | MEDIUM | HIGH | CRITICAL",
            "reason": "string",
            "estimated_resolution": "string or null",
            "source_url": "string"
        }
    ],
    "no_impact_drugs": ["list of monitored drugs with no shortage"],
    "summary": "string"
}
```

---

### Agent 2 — News & Supply Chain Sentiment Analyzer

**File**: `agents/agent_2_news.py`
**API Key**: Key 2 (index 1)
**External API**: NewsAPI.org (`https://newsapi.org/v2/everything`)
**Writes to DB**: Inserts high-confidence signals into `shortages` (type = 'NEWS_INFERRED'); inserts into `agent_logs`

#### What It Does

1. Builds search queries for the NewsAPI:
   - One query per monitored drug: `"<drug_name>" AND (shortage OR supply OR manufacturing OR recall)`
   - General pharma supply chain queries: `"pharmaceutical supply chain disruption"`, `"drug shortage hospital"`, `"FDA drug recall"`
2. Fetches articles from the past 7 days, sorted by relevancy, limited to 5 per query, English only.
3. Deduplicates articles by URL.
4. Sends all articles to Dedalus with a system prompt that tells the LLM to:
   - Determine if each article relates to any of the 10 monitored drugs
   - Score each article's sentiment: POSITIVE (supply expanding), NEUTRAL, NEGATIVE (early warning), CRITICAL (active disruption)
   - Assess supply chain impact: NONE, LOW, MEDIUM, HIGH, CRITICAL
   - Assign a confidence score (0.0 to 1.0)
   - Explain reasoning briefly
   - Identify emerging macro-level risks (geopolitical, regulatory, natural disaster)
5. For signals with `impact ≥ HIGH` AND `confidence ≥ 0.7`, inserts a row into `shortages` with `type = 'NEWS_INFERRED'`.
6. Writes full analysis to `agent_logs`.

#### Signals the System Prompt Should List

The system prompt should instruct the LLM to look for these specific signals:
- Manufacturing plant shutdowns or FDA warning letters
- Drug recalls
- Raw material / chemical precursor shortages
- Geopolitical events affecting pharma supply chains (tariffs, trade restrictions, conflicts in manufacturing regions)
- Natural disasters in manufacturing regions
- Transportation / logistics disruptions
- Regulatory changes affecting drug production
- Pharma company mergers/acquisitions
- Labor disputes at manufacturing facilities

#### Expected LLM Output Schema

```json
{
    "articles_analyzed": 0,
    "risk_signals": [
        {
            "drug_name": "string",
            "headline": "string",
            "source": "string",
            "url": "string",
            "sentiment": "POSITIVE | NEUTRAL | NEGATIVE | CRITICAL",
            "supply_chain_impact": "NONE | LOW | MEDIUM | HIGH | CRITICAL",
            "confidence": 0.0,
            "reasoning": "string"
        }
    ],
    "emerging_risks": [
        {
            "description": "string",
            "affected_drugs": ["list"],
            "risk_level": "LOW | MEDIUM | HIGH",
            "time_horizon": "string"
        }
    ],
    "summary": "string"
}
```

---

### Overseer Agent — Decision Synthesizer

**File**: `agents/overseer.py`
**API Key**: Key 2 (index 1)
**Reads from DB**: `agent_logs` (for current `run_id`), `drugs` (current snapshot), `shortages` (unresolved)
**Writes to DB**: `alerts` table
**Invokes**: Agent 3 and Agent 4 based on its decisions

#### What It Does

1. Reads all `agent_logs` rows matching the current `run_id` to get outputs from Agents 0, 1, and 2.
2. Fetches the current `drugs` inventory snapshot.
3. Fetches all unresolved `shortages`.
4. Sends everything to Dedalus with a system prompt that includes a decision framework:

**Decision Framework (must be in the system prompt)**:

- **IMMEDIATE (burn_rate < 7 days)**: Generate `RESTOCK_NOW` alert. If the drug has criticality ≤ 5 AND there's an active shortage, also generate `SUBSTITUTE_RECOMMENDED`. If a surgery is at risk within 48 hours, generate `SCHEDULE_CHANGE`.
- **WARNING (burn_rate 7–14 days)**: Generate `SHORTAGE_WARNING`. Combine with any FDA/news signals to escalate severity.
- **PLANNING (burn_rate 14–30 days + any risk signal)**: Generate `SUPPLY_CHAIN_RISK` with INFO/WARNING severity.
- **Severity mapping**: CRITICAL = patient care at immediate risk; URGENT = action needed within 48 hours; WARNING = action needed this week; INFO = awareness only.

5. The LLM responds with a list of decisions, plus two lists: `drugs_needing_substitutes` and `drugs_needing_orders`.
6. The Overseer writes each decision to the `alerts` table.
7. Returns the decisions (including the two lists) so the pipeline orchestrator can invoke Agent 3 and Agent 4.

#### Expected LLM Output Schema

```json
{
    "decisions": [
        {
            "action_type": "RESTOCK_NOW | SHORTAGE_WARNING | SUBSTITUTE_RECOMMENDED | SCHEDULE_CHANGE | SUPPLY_CHAIN_RISK | AUTO_ORDER_PLACED",
            "severity": "INFO | WARNING | URGENT | CRITICAL",
            "drug_name": "string",
            "title": "string (short headline)",
            "description": "string (full recommendation)",
            "requires_substitute": false,
            "requires_order": false,
            "order_details": {
                "drug_name": "string",
                "quantity_needed": 0,
                "urgency": "ROUTINE | EXPEDITED | EMERGENCY",
                "preferred_supplier_type": "PRIMARY | BACKUP | NEARBY_HOSPITAL | ANY"
            }
        }
    ],
    "drugs_needing_substitutes": ["drug_name", "..."],
    "drugs_needing_orders": [
        {"drug_name": "string", "quantity": 0, "urgency": "ROUTINE | EXPEDITED | EMERGENCY"}
    ],
    "schedule_adjustments": [
        {
            "surgery_date": "YYYY-MM-DD",
            "surgery_type": "string",
            "recommendation": "string"
        }
    ],
    "summary": "string"
}
```

---

### Agent 3 — Drug Substitute Finder

**File**: `agents/agent_3_substitutes.py`
**API Key**: Key 3 (index 2)
**Reads from DB**: `drugs` (inventory), `substitutes` (existing mappings)
**Writes to DB**: Upserts into `substitutes`; inserts into `agent_logs`
**Invoked by**: Overseer (only when `drugs_needing_substitutes` is non-empty)

#### Hard-Coded Substitution Mappings

The agent must contain a hard-coded Python dictionary of known substitution mappings. These are the medically validated defaults:

| Drug | Substitutes | Notes |
|------|-------------|-------|
| Epinephrine | Norepinephrine, Vasopressin | Norepinephrine for cardiac only (NOT anaphylaxis). Vasopressin is second-line for cardiac arrest. |
| Propofol | Etomidate, Ketamine, Midazolam | Etomidate: shorter duration. Ketamine: useful for hemodynamically unstable. Midazolam: slower onset. |
| Penicillin | Amoxicillin, Cephalexin, Azithromycin | Cephalexin: check penicillin allergy cross-reactivity. Azithromycin: use if allergy confirmed. |
| Levofloxacin | Moxifloxacin, Ciprofloxacin, Doxycycline | Same fluoroquinolone class except Doxycycline (tetracycline). |
| Heparin | Enoxaparin (Lovenox), Fondaparinux, Warfarin | Enoxaparin: LMWH, more predictable. Fondaparinux: for HIT patients. Warfarin: oral, slower onset. |
| Insulin | Insulin Lispro (Humalog), Insulin Glargine (Lantus) | Lispro: rapid-acting. Glargine: long-acting basal. |
| Morphine | Hydromorphone (Dilaudid), Fentanyl, Oxycodone | Hydromorphone: 5–7x more potent. Fentanyl: 50–100x more potent. Adjust doses carefully. |
| IV Fluids | Lactated Ringer's, Normal Saline (0.9% NaCl), D5W | LR better for large-volume resuscitation. D5W for specific indications. |
| Oxygen | *NONE* | Flag that no substitute exists — escalate for equipment/supply resolution. |
| Vaccines | *Product-specific* | Substitutions depend on specific vaccine product. |

#### What It Does

1. Receives a list of drug names from the Overseer.
2. Looks up each drug in the hard-coded mapping.
3. Checks the `drugs` table to see if any substitute is already in stock (and what quantity).
4. Fetches any existing entries from the `substitutes` table.
5. Sends all of this to Dedalus asking the LLM to:
   - Rank substitutes by clinical appropriateness
   - Note dosing conversions and contraindications
   - Flag if a substitute is in stock
   - Flag drugs with NO viable substitute (e.g., Oxygen)
6. Upserts results into the `substitutes` table (use the unique constraint on `drug_name, substitute_name`).
7. Writes to `agent_logs`.

#### Expected LLM Output Schema

```json
{
    "substitutions": [
        {
            "original_drug": "string",
            "substitutes": [
                {
                    "name": "string",
                    "preference_rank": 1,
                    "equivalence_notes": "string",
                    "dosing_conversion": "string",
                    "contraindications": "string",
                    "in_stock": true,
                    "stock_quantity": 0
                }
            ],
            "no_substitute_available": false,
            "clinical_notes": "string"
        }
    ],
    "summary": "string"
}
```

---

### Agent 4 — Order & Supplier Manager

**File**: `agents/agent_4_orders.py`
**API Key**: Key 3 (index 2)
**Reads from DB**: `suppliers`, `drugs`
**Writes to DB**: `alerts` (order-type alerts); inserts into `agent_logs`
**Invoked by**: Overseer (only when `drugs_needing_orders` is non-empty)

#### Hard-Coded Major Supplier List

The agent must contain a hard-coded list of major US pharmaceutical distributors:

| Supplier | Type | Region | Typical Lead Time |
|----------|------|--------|-------------------|
| McKesson Corporation | DISTRIBUTOR | National (US) | 1 day |
| Cardinal Health | DISTRIBUTOR | National (US) | 1 day |
| AmerisourceBergen | DISTRIBUTOR | National (US) | 1 day |
| Morris & Dickson | DISTRIBUTOR | Southeast US | 2 days |
| Henry Schein | DISTRIBUTOR | National (US) | 2 days |
| Pfizer (Direct) | MANUFACTURER | Global | 5 days |
| Teva Pharmaceuticals | MANUFACTURER | Global | 7 days |
| Mylan/Viatris | MANUFACTURER | Global | 7 days |
| Fresenius Kabi | MANUFACTURER | Global | 5 days |
| Baxter International | MANUFACTURER | Global | 3 days |

#### What It Does

1. Receives a list of `{"drug_name", "quantity", "urgency"}` objects from the Overseer.
2. Fetches all active suppliers from the `suppliers` table (which may include nearby hospitals with `is_nearby_hospital = TRUE`).
3. Merges the hard-coded supplier list with DB suppliers.
4. Fetches current pricing and criticality data from the `drugs` table.
5. Sends everything to Dedalus with a system prompt that includes this decision logic:
   - **EMERGENCY orders** (need within 24 hours): Prefer nearby hospital transfers or national distributors with express shipping
   - **EXPEDITED orders** (need within 3 days): National distributors with expedited shipping
   - **ROUTINE orders** (need within 7–14 days): Optimize for best price
   - Always include a backup supplier
   - For drugs with criticality_rank ≤ 5, recommend maintaining a 30-day supply
   - Factor in hospital location for proximity calculations
6. For each order, writes an alert to `alerts` with type `AUTO_ORDER_PLACED` or `RESTOCK_NOW`.
7. Writes full analysis to `agent_logs`.

#### Expected LLM Output Schema

```json
{
    "orders": [
        {
            "drug_name": "string",
            "quantity": 0,
            "unit": "string",
            "urgency": "EMERGENCY | EXPEDITED | ROUTINE",
            "recommended_supplier": "string",
            "supplier_type": "DISTRIBUTOR | MANUFACTURER | NEARBY_HOSPITAL",
            "estimated_cost": 0,
            "estimated_delivery_days": 0,
            "backup_supplier": "string",
            "reasoning": "string"
        }
    ],
    "hospital_transfer_requests": [
        {
            "target_hospital": "string",
            "drug_name": "string",
            "quantity": 0,
            "justification": "string"
        }
    ],
    "cost_summary": {
        "total_estimated_cost": 0,
        "emergency_orders_cost": 0,
        "routine_orders_cost": 0
    },
    "summary": "string"
}
```

---

## 6. Pipeline Orchestration

**File**: `agents/pipeline.py`

### Execution Phases

```
Phase 1 ─── Agent 0 ──┐
            Agent 1 ──┤ (parallel, all write to agent_logs with same run_id)
            Agent 2 ──┘
                │
Phase 2 ─── Overseer Agent (reads agent_logs, produces decisions)
                │
                ├── drugs_needing_substitutes? ──→ Phase 3: Agent 3
                │
                └── drugs_needing_orders? ──→ Phase 4: Agent 4
```

### Pipeline Logic

1. Generate a UUID `run_id`.
2. Run Agents 0, 1, 2 in parallel using `asyncio.gather` with `loop.run_in_executor` (since agents are synchronous). Catch exceptions per agent — one agent failing should not crash the pipeline.
3. Run the Overseer synchronously. It reads from `agent_logs` WHERE `run_id` matches.
4. If the Overseer's response contains a non-empty `drugs_needing_substitutes` list, invoke Agent 3 with that list.
5. If the Overseer's response contains a non-empty `drugs_needing_orders` list, invoke Agent 4 with that list and the hospital location.
6. Log the pipeline completion.

### Execution Modes

- **Cron loop**: A `main.py` that runs `pipeline.run()` in an infinite loop with a configurable sleep interval (default 60 minutes).
- **Manual trigger** (optional): A FastAPI endpoint `POST /api/run-pipeline` that triggers the pipeline in a background task and returns immediately.

---

## 7. Frontend Dashboard

### Pages & Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | Summary cards, active alerts, top actions |
| `/drugs` | Drugs Inventory | Full table of all 10 drugs with stock, usage rate, predicted rate, burn rate, charts |
| `/shortages` | Shortages | All shortage records with source, severity, resolved status |
| `/suppliers` | Suppliers | Supplier directory with drug, price, location, lead time, reliability |
| `/alerts` | Alert History | Full alert log with filters by severity, type, acknowledged status |

### Dashboard Page (`/`)

Must include:

**4 summary cards at the top**:
1. **Critical Alerts** (count) — red background — count of alerts where severity = CRITICAL and acknowledged = FALSE
2. **Urgent Alerts** (count) — orange background — severity = URGENT
3. **Low Stock Drugs** (count) — yellow background — drugs where burn_rate_days < 14
4. **Active Shortages** (count) — blue background — count of shortages where resolved = FALSE

**Active Alerts section**:
- List of all unacknowledged alerts, ordered by severity (CRITICAL first) then created_at DESC
- Each alert card shows: severity badge, title, description, and an "Acknowledge" button
- Color-coded border/background by severity: CRITICAL = red, URGENT = orange, WARNING = yellow, INFO = blue
- Clicking "Acknowledge" sets `acknowledged = TRUE` via Supabase update and removes the alert from the list

**Drug Inventory table**:
- Columns: Rank, Drug, Type, Stock, Daily Usage, Predicted Usage, Burn Rate (days), Predicted Burn (days), Price/Unit
- Burn rate cells color-coded: < 7 days = red, 7–14 = orange, 14–30 = yellow, 30+ = green
- Ordered by criticality_rank

### Drugs Page (`/drugs`)

- Same table as dashboard but with more detail
- Add a **Recharts line chart** per drug (or a combined chart) showing: current daily usage vs. predicted daily usage, with stock-depletion projection over time
- Each drug row expandable to show: substitutes (from `substitutes` table), associated shortages, active suppliers

### Shortages Page (`/shortages`)

- Table columns: Drug, Type (FDA/News/Internal), Source, Impact Severity, Description, Reported Date, Resolved
- Filter by: resolved/unresolved, severity level
- Severity badge color-coded

### Suppliers Page (`/suppliers`)

- Table columns: Name, Drug, Price/Unit, Location, Lead Time, Reliability Score, Type (Distributor/Hospital)
- Filter by drug name, by type (hospital vs. vendor)
- Sort by reliability score or price

### Alert History Page (`/alerts`)

- Full list of all alerts (including acknowledged)
- Filters: by severity, by alert_type, by acknowledged status, by date range
- Show action_payload as expandable JSON for order details

### Realtime Subscriptions

The frontend must subscribe to Supabase Realtime for:
- `alerts` table: INSERT events → prepend new alerts to the active alerts list
- `drugs` table: UPDATE events → update the drug row in-place in the UI

Use `supabase.channel().on('postgres_changes', ...)` syntax.

### Styling

- Use Tailwind CSS utility classes throughout
- Color scheme: medical/professional — blue primary, white background, gray borders
- Use lucide-react icons for: AlertTriangle (warnings), ShieldAlert (critical), TrendingDown (low stock), Package (shortages/inventory)
- Responsive layout using Tailwind grid

---

## 8. File Structure

```
pharmasentinel/
├── agents/
│   ├── __init__.py
│   ├── shared.py                  # Supabase client, Dedalus LLM wrapper, constants,
│   │                              #   MONITORED_DRUGS list, log_agent_output(),
│   │                              #   get_drugs_inventory(), get_surgery_schedule(),
│   │                              #   call_dedalus(prompt, system_prompt, api_key_index)
│   ├── agent_0_inventory.py       # Inventory analyzer & burn rate calculator
│   ├── agent_1_fda.py             # FDA shortage monitor
│   ├── agent_2_news.py            # News sentiment analyzer
│   ├── agent_3_substitutes.py     # Drug substitute finder
│   ├── agent_4_orders.py          # Order & supplier manager
│   ├── overseer.py                # Decision synthesizer
│   └── pipeline.py                # Orchestrator (phases 1–4)
├── db/
│   └── schema.sql                 # All CREATE TABLE + indexes + RLS policies
├── frontend/                      # React + TypeScript + Vite project
│   ├── src/
│   │   ├── lib/
│   │   │   └── supabase.ts        # createClient + TypeScript interfaces for all tables
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── DrugsPage.tsx
│   │   │   ├── ShortagesPage.tsx
│   │   │   ├── SuppliersPage.tsx
│   │   │   └── AlertsPage.tsx
│   │   ├── components/            # Reusable UI: SummaryCard, AlertCard, DrugTable, etc.
│   │   ├── App.tsx                # Router + nav layout
│   │   └── main.tsx
│   ├── .env                       # VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
│   ├── package.json
│   ├── tailwind.config.js
│   └── tsconfig.json
├── main.py                        # Pipeline entry point (cron loop)
├── api_server.py                  # Optional FastAPI manual trigger
├── requirements.txt               # supabase, requests, python-dotenv, fastapi, uvicorn
├── .env                           # All env vars (see Section 3)
└── README.md
```

---

## 9. Seed Data

The database should be seeded with initial data so the system is functional immediately.

### Seed: `drugs` table

Insert all 10 monitored drugs with realistic initial stock values:

| name | type | stock_quantity | unit | price_per_unit | usage_rate_daily | criticality_rank | reorder_threshold_days |
|------|------|---------------|------|---------------|-----------------|-----------------|----------------------|
| Epinephrine | Anaphylaxis/Cardiac | 150 | vials | 35.00 | 8 | 1 | 14 |
| Oxygen | Respiratory Support | 500 | liters | 0.50 | 120 | 2 | 7 |
| Levofloxacin | Broad-Spectrum Antibiotic | 200 | tablets | 12.00 | 15 | 3 | 14 |
| Propofol | Anesthetic | 80 | vials | 45.00 | 6 | 4 | 14 |
| Penicillin | Antibiotic | 300 | vials | 8.00 | 20 | 5 | 14 |
| IV Fluids | Hydration/Shock | 400 | bags | 3.50 | 50 | 6 | 14 |
| Heparin | Anticoagulant | 120 | vials | 28.00 | 10 | 7 | 14 |
| Insulin | Diabetes Management | 180 | vials | 55.00 | 12 | 8 | 14 |
| Morphine | Analgesic/Pain | 100 | vials | 18.00 | 7 | 9 | 14 |
| Vaccines | Immunization | 250 | doses | 22.00 | 5 | 10 | 21 |

### Seed: `surgery_schedule` table

Insert 8–12 upcoming surgeries spread across the next 30 days, each with a `drugs_required` JSONB array. Example:

- Cardiac Bypass (needs: Heparin ×10, Propofol ×3, Morphine ×5, IV Fluids ×8)
- Appendectomy (needs: Propofol ×2, Levofloxacin ×4, IV Fluids ×4, Morphine ×2)
- Hip Replacement (needs: Propofol ×2, Heparin ×6, Morphine ×4, IV Fluids ×6)
- Emergency Trauma (needs: Epinephrine ×3, IV Fluids ×12, Morphine ×6, Heparin ×4)
- Tonsillectomy (needs: Propofol ×1, Penicillin ×6, Morphine ×1, IV Fluids ×2)

### Seed: `suppliers` table

Insert the 10 hard-coded major suppliers from the Agent 4 spec, plus 2–3 nearby hospitals:

| name | drug_name | location | lead_time_days | is_nearby_hospital |
|------|-----------|----------|---------------|-------------------|
| McKesson Corporation | Multiple | National | 1 | FALSE |
| Pittsburgh General Hospital | Epinephrine | Pittsburgh, PA | 0 | TRUE |
| UPMC Mercy | Propofol | Pittsburgh, PA | 0 | TRUE |

For the major distributors, insert one row per drug they supply (or a "Multiple" entry if you prefer a simpler schema).

### Seed: `substitutes` table

Pre-populate from the hard-coded substitution mappings in the Agent 3 spec. This gives the system known-good substitutes from day 1.

---

## 10. Error Handling & Edge Cases

### Agent Failures

- If any Phase 1 agent throws an exception, catch it, log the error, and continue. The Overseer should handle missing agent data gracefully (it just won't have that signal).
- If the Dedalus API returns non-JSON, attempt to extract JSON from markdown code fences (`\`\`\`json...\`\`\``) before failing.
- If the FDA API is unreachable, Agent 1 should fall back to only analyzing existing `shortages` table data.
- If the NewsAPI is unreachable or returns 0 articles, Agent 2 should write a log saying "No articles found" and return an empty risk signals list.

### Data Edge Cases

- A drug with `usage_rate_daily = 0` should have `burn_rate_days = NULL` (not infinity), since division by zero is undefined.
- If `surgery_schedule` is empty, Agent 0 should still compute burn rates from daily usage alone.
- If the `drugs` table is empty (no seed data), the pipeline should log a warning and exit gracefully.
- Shortages with identical `drug_name` + `source` + `reported_date` should not create duplicates — use upsert logic or check before insert.

### Frontend Edge Cases

- If no alerts exist, show "No active alerts" placeholder text.
- If a drug has NULL for predicted values, display "—" not "null" or "NaN".
- Burn rate color coding must handle NULL (no color / gray).
- Realtime subscription should reconnect on disconnect.

---

## 11. Build Order

This is the recommended implementation sequence for a coding agent:

### Step 1: Database Setup
1. Create the Supabase project (or connect to existing one)
2. Run all CREATE TABLE statements from Section 4
3. Create indexes
4. Enable RLS with permissive policies
5. Insert seed data from Section 9

### Step 2: Shared Agent Infrastructure
1. Create `agents/shared.py` with: Supabase client init, Dedalus API wrapper function, `MONITORED_DRUGS` constant, `log_agent_output()`, `get_drugs_inventory()`, `get_surgery_schedule()`
2. Test the Supabase connection and Dedalus API call independently

### Step 3: Build Agents (in order)
1. **Agent 0** — Inventory (most self-contained, only reads from DB)
2. **Agent 1** — FDA (external API, test FDA endpoint availability)
3. **Agent 2** — News (external API, test NewsAPI)
4. **Overseer** — Reads from agent_logs, produces decisions
5. **Agent 3** — Substitutes (invoked conditionally)
6. **Agent 4** — Orders (invoked conditionally)

Test each agent individually before integration.

### Step 4: Pipeline Orchestrator
1. Build `agents/pipeline.py` with the 4-phase execution logic
2. Build `main.py` cron loop
3. Test full pipeline end-to-end with seed data

### Step 5: Frontend
1. Scaffold React+TypeScript+Vite project
2. Set up Supabase client + TypeScript types
3. Build Dashboard page first (highest value)
4. Build Drugs page with table + charts
5. Build Shortages, Suppliers, Alerts pages
6. Add Realtime subscriptions
7. Style with Tailwind

### Step 6: Integration Testing
1. Run the full pipeline
2. Verify alerts appear on the dashboard
3. Verify Realtime updates work
4. Test with modified seed data (e.g., very low stock) to trigger different alert types

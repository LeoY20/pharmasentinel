# PharmaSentinel

**Hospital Pharmacy Supply Chain Intelligence Platform**

A multi-agent AI system that predicts drug shortages, recommends substitutes, optimizes ordering, and prevents surgical disruptions through real-time supply chain monitoring.  
Built for **TartanHacks at Carnegie Mellon University**.

---

## Overview

PharmaSentinel monitors 10 critical hospital drugs (ranked by criticality 1-10) and uses AI agents to:

- **Predict shortages** via FDA data and web Search
- **Find clinical substitutes** using AI agents when drugs are unavailable
- **Optimize supplier selection** based on urgency, cost, reliability, and is based on potential disruption signals
- **Generate purchase orders** from distributors or nearby hospitals
- **Monitor supply chain risks** via web Search (finding news/updates)

### The 10 Monitored Drugs (Example)

1. **Epinephrine** — Anaphylaxis/Cardiac (life-saving)
2. **Oxygen** — Respiratory Support
3. **Levofloxacin** — Broad-Spectrum Antibiotic
4. **Propofol** — Anesthetic
5. **Penicillin** — Foundational antibiotic
6. **IV Fluids** — Hydration/Shock/Blood Loss
7. **Heparin** — Anticoagulant
8. **Insulin** — Diabetes Management
9. **Morphine** — Pain Management
10. **Vaccines** — Immunization

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│           FRONTEND (React + TypeScript)                  │
│   Dashboard | Drugs | Shortages | Suppliers | Alerts    │
│                 (Real-time Updates)                     │
└──────────────────────┬──────────────────────────────────┘
                       │
          Supabase (PostgreSQL + Realtime)
                       │
┌──────────────────────▼──────────────────────────────────┐
│              BACKEND SERVER (server.py)                  │
│                                                          │
│  [Continuous Pipeline Loop]                              │
│  Phase 1: Agent 0 (Inventory) + Agent 1 (FDA)            │
│  Phase 2: Agent 2 (News - Brave MCP)                     │
│  Phase 3: Overseer (Decision Synthesizer)                │
│                                                          │
│  [Order Agent]                               │
│  Agent 4: Pricing Analysis & Order Generation            │
│           (Triggered via API / User Action)              │
└─────────────────────────────────────────────────────────┘
```

The system requires `server.py` to be running. This file manages:
1.  **The Continuous Pipeline**: Runs on a schedule (e.g., every 60 mins) to check FDA data, news, and inventory.
2.  **The API**: Exposes endpoints for the frontend to trigger specific agents (like the Order Agent) on demand, independent of the main pipeline.

### Agents
-   **Agent 0 (Inventory)**: Monitors Inventory, predicts usage, plans around surgeries, and ralculates burn rates.
-   **Agent 1 (FDA)**: Monitors FDA shortage database.
-   **Agent 2 (News)**: Uses web Search to find supply chain disruption news and potential shortages.
-   **Overseer**: Synthesizes data to create alerts.
-   **Agent 3 (Substitutes)**: Finds valid clinical substitutes dynamically.
-   **Agent 4 (Orders)**: Analyze pricing and availability to build orders.

---

## Quick Start

### Prerequisites
-   **Python 3.11+**
-   **Node.js 18+**
-   **Supabase** project
-   **LLM API Keys** (Dedalus/OpenAI etc.)

<<<<<<< HEAD
### 1. Database Setup
1.  Create a Supabase project.
2.  Run `db/schema.sql` in the SQL Editor to create tables.
3.  Run `db/seed_data.sql` to populate initial example data.
=======
- **Python 3.11+**
- **Node.js 18+** and npm
- **Supabase account** ([supabase.com](https://supabase.com))
- **API Keys**:
  - At least 1 Dedalus API Key

### 1. Clone and Setup
>>>>>>> cbe4fd8ddce033cc0ab37d7ad16c55d8bb620a33

### 2. Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Setup .env
# Ensure you have SUPABASE_URL, ANTHROPIC_API_KEY/DEDALUS_KEYS, etc.

# Run the server 
python server.py
```

<<<<<<< HEAD
### 3. Frontend
=======
Update `.env` with your actual values:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key

DEDALUS_API_KEY_1=your_dedalus_key_1
DEDALUS_API_KEY_2=your_dedalus_key_2
DEDALUS_API_KEY_3=your_dedalus_key_3

HOSPITAL_LOCATION=your_location_here
PIPELINE_INTERVAL_MINUTES=60
```

### 4. Frontend Setup

>>>>>>> cbe4fd8ddce033cc0ab37d7ad16c55d8bb620a33
```bash
cd frontend
npm install
npm run dev
```

---

## Future Work

-   **Manual Drug Entry**: Allow users to manually add new drugs to the monitoring list via the UI.
-   **Database Integration**: Connect directly to existing hospital inventory databases instead of using the standalone database.

<<<<<<< HEAD
=======
- **Critical Alerts**: Count of CRITICAL severity alerts
- **Urgent Alerts**: Count of URGENT severity alerts
- **Low Stock Drugs**: Drugs with < 14 days burn rate
- **Active Shortages**: Unresolved FDA/news-reported shortages

### Active Alerts

Real-time alerts with:
- Severity badges (CRITICAL, URGENT, WARNING, INFO)
- Drug name and alert type
- Actionable recommendations
- Acknowledge button

### Drug Inventory Table

- Criticality ranking (1-10)
- Current stock levels
- Daily usage rate
- Burn rate (days until stockout)
- Color-coded risk indicators:
  - Red: < 7 days
  - Orange: 7-14 days
  - Yellow: 14-30 days
  - Green: 30+ days

### Realtime Updates

- **Alerts**: New alerts appear immediately via Supabase Realtime
- **Drug Updates**: Inventory changes update in real-time

---

## Project Structure

```
pharmasentinel/
├── agents/
│   ├── shared.py                  # Shared infrastructure (Supabase, Dedalus, constants)
│   ├── agent_0_inventory.py       # Inventory analyzer & burn rate calculator
│   ├── agent_1_fda.py             # FDA shortage monitor
│   ├── agent_2_news.py            # News sentiment analyzer
│   ├── agent_3_substitutes.py     # Drug substitute finder
│   ├── agent_4_orders.py          # Order & supplier manager
│   ├── overseer.py                # Decision synthesizer
│   └── pipeline.py                # Orchestrator (phases 1-4)
├── db/
│   ├── schema.sql                 # Database schema
│   └── seed_data.sql              # Initial data
├── frontend/
│   ├── src/
│   │   ├── lib/supabase.ts        # Supabase client + TypeScript types
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx      # Main dashboard
│   │   │   ├── DrugsPage.tsx      # Drug inventory with charts
│   │   │   ├── ShortagesPage.tsx  # Shortage tracking
│   │   │   ├── SuppliersPage.tsx  # Supplier directory
│   │   │   └── AlertsPage.tsx     # Alert history
│   │   ├── App.tsx                # Router + navigation
│   │   └── main.tsx
│   ├── package.json
│   └── .env
├── main.py                        # Pipeline entry point (cron loop)
├── requirements.txt
├── .env
└── README.md
```

---

## Agent Details

### API Key Distribution

To avoid rate limits, the 3 Dedalus API keys are distributed:

| Key   | Assigned Agents                | Rationale                           |
|-------|--------------------------------|-------------------------------------|
| Key 1 | Agent 0 (Inventory), Agent 1 (FDA) | Both run in Phase 1 parallel        |
| Key 2 | Agent 2 (News), Overseer       | Agent 2 in Phase 1; Overseer in Phase 2 — never concurrent |
| Key 3 | Agent 3 (Substitutes), Agent 4 (Orders) | Both in Phase 3/4, run sequentially  |

### Decision Framework (Overseer)

**IMMEDIATE (burn_rate < 7 days)**:
- Generate `RESTOCK_NOW` alert (URGENT/CRITICAL)
- If criticality ≤ 5 AND active shortage → `SUBSTITUTE_RECOMMENDED`
- If surgery at risk within 48 hours → `SCHEDULE_CHANGE` (CRITICAL)

**WARNING (burn_rate 7-14 days)**:
- Generate `SHORTAGE_WARNING` (WARNING severity)
- Escalate to URGENT if FDA/news signals present

**PLANNING (burn_rate 14-30 days + risk signals)**:
- Generate `SUPPLY_CHAIN_RISK` (INFO/WARNING)

### Hard-Coded Substitute Mappings

Agent 3 uses medically validated substitution mappings:

- **Epinephrine** → Norepinephrine, Vasopressin
- **Propofol** → Etomidate, Ketamine, Midazolam
- **Penicillin** → Amoxicillin, Cephalexin, Azithromycin
- **Heparin** → Enoxaparin, Fondaparinux, Warfarin
- **Morphine** → Hydromorphone, Fentanyl, Oxycodone
- **IV Fluids** → Lactated Ringer's, Normal Saline, D5W
- **Oxygen** → NO SUBSTITUTE (equipment/supply resolution required)

### Major Suppliers (Agent 4)

Hard-coded list includes:
- **National Distributors**: McKesson, Cardinal Health, AmerisourceBergen
- **Regional Distributors**: Morris & Dickson, Henry Schein
- **Manufacturers**: Pfizer, Teva, Fresenius Kabi, Baxter, Mylan/Viatris
- **Nearby Hospitals** (from database): Pittsburgh General, UPMC Mercy, Allegheny General

---

## Usage Examples

### Run Pipeline Once

```bash
python main.py --once
```

### Run Continuously

```bash
# Default 60-minute interval
python main.py

# Custom 30-minute interval
python main.py --interval 30
```

### View Logs

The pipeline prints detailed execution logs:

```
================================================================================
PHARMASENTINEL PIPELINE EXECUTION
Run ID: 123e4567-e89b-12d3-a456-426614174000
Started: 2026-02-06T10:00:00
================================================================================

================================================================================
PHASE 1: Data Collection (Parallel)
================================================================================

============================================================
Agent 0: Inventory Analyzer
...
* Agent 0 completed successfully

============================================================
Agent 1: FDA Drug Shortage Monitor
...
* Agent 1 completed successfully

============================================================
Agent 2: News & Supply Chain Analyzer
...
* Agent 2 completed successfully

================================================================================
PHASE 1 COMPLETED in 12.45s
================================================================================

...
```

---

## Security Notes

- **RLS Policies**: Currently permissive for hackathon. In production, scope to `hospital_id`.
- **API Keys**: Never commit `.env` files. Use environment-specific secrets management.
- **Service Role Key**: Backend uses service role key (bypasses RLS). Frontend uses anon key.

---

## Troubleshooting

### "Missing environment variables"

- Ensure all variables in `.env` are set
- Check that you're using actual values, not placeholders like `your_key_here`

### "Supabase connection failed"

- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are correct
- Check that you've run `schema.sql` and `seed_data.sql`

### "Dedalus API call failed"

- Verify your Dedalus API keys are valid
- Check if you've hit rate limits (the system distributes keys to avoid this)
- For development, the system will use fallback logic if LLM calls fail

### Frontend shows "Loading..." forever

- Check browser console for errors
- Verify `frontend/.env` has correct Supabase URL and anon key
- Ensure Supabase RLS policies allow reads

---

## License

This is a hackathon/educational project. No license specified.

---

## Credits

Built for the **Insolvent Hackathon** using:
- **Supabase** for database + realtime
- **Dedalus** for LLM reasoning
- **FDA openFDA API** for shortage data
- **React + TypeScript** for frontend
- **Python** for backend agents

---

## Support

For issues, please refer to the agent logs or open an issue on the repository.

---
>>>>>>> cbe4fd8ddce033cc0ab37d7ad16c55d8bb620a33

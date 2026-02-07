"""
Agent 1 — FDA Drug Shortage Monitor

Responsibilities:
- Queries openFDA API for drug shortage data
- Fetches existing shortages from database
- Uses LLM to match FDA data to monitored drugs and assess impact
- Inserts new shortage records into shortages table
- Logs analysis to agent_logs

API Key: DEDALUS_API_KEY_1 (index 0)
"""

import json
import requests
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .shared import (
    supabase,
    call_dedalus,
    log_agent_output,
    get_unresolved_shortages,
    MONITORED_DRUGS,
    MONITORED_DRUG_NAMES,
    get_criticality_rank
)

AGENT_NAME = "agent_1"
API_KEY_INDEX = 0
FDA_API_BASE = "https://api.fda.gov"

def query_fda_api(drug_name: str) -> List[Dict[str, Any]]:
    """
    Query FDA openFDA API for drug information.

    Note: The openFDA API doesn't have a dedicated shortage endpoint.
    This function attempts to gather drug data that might indicate shortages.

    Args:
        drug_name: Name of the drug to search

    Returns:
        List of FDA API results
    """
    results = []

    try:
        # Try drug enforcement endpoint (recalls, withdrawals)
        enforcement_url = f"{FDA_API_BASE}/drug/enforcement.json"
        params = {
            "search": f'product_description:"{drug_name}"',
            "limit": 5
        }

        response = requests.get(enforcement_url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            enforcement_results = data.get('results', [])
            results.extend([{
                'source': 'FDA Enforcement',
                'type': 'enforcement',
                'data': item
            } for item in enforcement_results])

    except Exception as e:
        print(f"  Warning: FDA enforcement query failed for {drug_name}: {e}")

    try:
        # Try drug event endpoint (adverse events, which might indicate issues)
        event_url = f"{FDA_API_BASE}/drug/event.json"
        params = {
            "search": f'patient.drug.openfda.generic_name:"{drug_name.lower()}"',
            "limit": 5
        }

        response = requests.get(event_url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            event_results = data.get('results', [])
            results.extend([{
                'source': 'FDA Adverse Events',
                'type': 'event',
                'data': item
            } for item in event_results[:3]])  # Limit to 3

    except Exception as e:
        print(f"  Warning: FDA event query failed for {drug_name}: {e}")

    return results

def build_system_prompt() -> str:
    """Build the system prompt for Agent 1."""
    return f"""You are an expert FDA drug shortage analyst for hospital pharmacy operations. Your role is to identify and assess drug shortages that may impact patient care.

# CONTEXT

The hospital monitors {len(MONITORED_DRUGS)} critical drugs ranked by criticality (1 = most critical):

{json.dumps(MONITORED_DRUGS, indent=2)}

# YOUR TASK

You will receive:
1. Existing shortage records from the database (last 6 months)
2. FDA API data (enforcement actions, recalls, adverse events) for each monitored drug

You must:
1. Analyze FDA data to identify potential or actual drug shortages
2. Match FDA findings to our monitored drug list
3. Assess whether each shortage is ONGOING, RESOLVED, or WORSENING
4. Rate impact severity based on criticality ranking:
   - CRITICAL: Affects drugs ranked 1-3 (life-saving)
   - HIGH: Affects drugs ranked 4-6 (surgery-critical)
   - MEDIUM: Affects drugs ranked 7-9 (important but substitutable)
   - LOW: Affects rank 10 or not in our monitored list
5. Identify any shortages you know about from your training data

# DECISION FRAMEWORK

Status Assessment:
- ONGOING: Shortage currently active, no resolution announced
- WORSENING: Existing shortage getting worse or spreading
- RESOLVED: Shortage has been resolved or supply restored

Impact Severity:
- CRITICAL: Life-saving drug (rank 1-3), immediate patient risk
- HIGH: Surgery-critical (rank 4-6), operations may be delayed
- MEDIUM: Important (rank 7-9), alternatives available
- LOW: Low priority or not in monitored list

# OUTPUT FORMAT

You MUST respond with ONLY valid JSON matching this exact schema:

{{
    "shortages_found": [
        {{
            "drug_name": "string (matched to our monitored list)",
            "fda_drug_name": "string (exact FDA name)",
            "status": "ONGOING | RESOLVED | WORSENING",
            "impact_severity": "LOW | MEDIUM | HIGH | CRITICAL",
            "reason": "string",
            "estimated_resolution": "string or null",
            "source_url": "string"
        }}
    ],
    "no_impact_drugs": ["list of monitored drugs with no shortage"],
    "summary": "string"
}}

Respond with ONLY the JSON. No markdown, no explanations."""

def run(run_id: str) -> Dict[str, Any]:
    """
    Execute Agent 1 FDA monitoring.

    Args:
        run_id: UUID of the current pipeline run

    Returns:
        Analysis results dictionary
    """
    print(f"\n{'='*60}")
    print(f"Agent 1: FDA Drug Shortage Monitor")
    print(f"Run ID: {run_id}")
    print(f"{'='*60}\n")

    try:
        # Fetch existing shortages
        print("Fetching existing shortage records...")
        existing_shortages = get_unresolved_shortages(days_back=180)
        print(f"✓ Found {len(existing_shortages)} unresolved shortages")

        # Query FDA API for each monitored drug
        print("\nQuerying FDA API...")
        fda_data = {}

        for drug in MONITORED_DRUG_NAMES:
            print(f"  Querying FDA for {drug}...")
            results = query_fda_api(drug)
            fda_data[drug] = results
            print(f"    Found {len(results)} FDA records")

        total_fda_records = sum(len(results) for results in fda_data.values())
        print(f"✓ Retrieved {total_fda_records} total FDA records")

        # Build user prompt
        user_prompt = f"""# EXISTING SHORTAGE RECORDS (Last 6 Months)

{json.dumps(existing_shortages, indent=2, default=str)}

# FDA API DATA (By Drug)

{json.dumps(fda_data, indent=2, default=str)}

# MONITORED DRUGS

{json.dumps(MONITORED_DRUG_NAMES, indent=2)}

Please analyze the FDA data and existing shortages to identify current shortage risks."""

        # Call Dedalus LLM
        print("\nCalling Dedalus LLM for analysis...")
        system_prompt = build_system_prompt()

        try:
            analysis = call_dedalus(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                api_key_index=API_KEY_INDEX,
                temperature=0.2
            )
            print("✓ Received LLM analysis")
        except Exception as e:
            print(f"WARNING: LLM call failed: {e}")
            # Provide fallback analysis
            analysis = generate_fallback_analysis(existing_shortages, fda_data)
            print("✓ Using fallback analysis")

        # Insert new shortages into database
        print("\nProcessing shortage findings...")
        shortages_found = analysis.get('shortages_found', [])
        inserted_count = 0

        for shortage in shortages_found:
            drug_name = shortage.get('drug_name')
            impact_severity = shortage.get('impact_severity', 'MEDIUM')

            # Check if this shortage already exists
            existing = next(
                (s for s in existing_shortages if s.get('drug_name') == drug_name),
                None
            )

            if not existing:
                # Insert new shortage record
                shortage_record = {
                    'drug_name': drug_name,
                    'type': 'FDA_REPORTED',
                    'source': 'FDA openFDA API',
                    'source_url': shortage.get('source_url', 'https://api.fda.gov'),
                    'impact_severity': impact_severity,
                    'description': shortage.get('reason', ''),
                    'reported_date': datetime.now().date().isoformat(),
                    'resolved': False
                }

                supabase.table('shortages').insert(shortage_record).execute()
                inserted_count += 1
                print(f"  ✓ Inserted shortage for {drug_name} (severity: {impact_severity})")

        print(f"✓ Inserted {inserted_count} new shortage records")

        # Log to agent_logs
        summary = analysis.get('summary', f'FDA monitoring completed. Found {len(shortages_found)} shortages.')
        log_agent_output(AGENT_NAME, run_id, analysis, summary)

        print(f"\n✓ Agent 1 completed successfully")
        print(f"  - Queried {len(MONITORED_DRUG_NAMES)} drugs via FDA API")
        print(f"  - Found {len(shortages_found)} shortage signals")
        print(f"  - Inserted {inserted_count} new shortage records")

        return analysis

    except Exception as e:
        print(f"\n✗ Agent 1 failed: {e}")
        error_payload = {
            "error": str(e),
            "summary": f"Agent 1 failed: {e}"
        }
        log_agent_output(AGENT_NAME, run_id, error_payload, f"ERROR: {e}")
        raise

def generate_fallback_analysis(
    existing_shortages: List[Dict[str, Any]],
    fda_data: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Generate fallback analysis when LLM is unavailable.

    Args:
        existing_shortages: Existing shortage records
        fda_data: FDA API data by drug

    Returns:
        Analysis dictionary matching expected schema
    """
    shortages_found = []
    has_shortage = set()

    # Check existing shortages
    for shortage in existing_shortages:
        drug_name = shortage.get('drug_name')
        if drug_name in MONITORED_DRUG_NAMES:
            has_shortage.add(drug_name)

    # Check FDA data for enforcement actions (potential shortages)
    for drug_name, results in fda_data.items():
        if results and drug_name not in has_shortage:
            # Found enforcement action, might indicate shortage
            criticality_rank = get_criticality_rank(drug_name)

            if criticality_rank <= 3:
                severity = "CRITICAL"
            elif criticality_rank <= 6:
                severity = "HIGH"
            elif criticality_rank <= 9:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            shortages_found.append({
                "drug_name": drug_name,
                "fda_drug_name": drug_name,
                "status": "ONGOING",
                "impact_severity": severity,
                "reason": f"FDA enforcement actions detected ({len(results)} records)",
                "estimated_resolution": None,
                "source_url": "https://api.fda.gov/drug/enforcement.json"
            })
            has_shortage.add(drug_name)

    # Drugs with no shortage
    no_impact_drugs = [drug for drug in MONITORED_DRUG_NAMES if drug not in has_shortage]

    return {
        "shortages_found": shortages_found,
        "no_impact_drugs": no_impact_drugs,
        "summary": f"Fallback analysis. Found {len(shortages_found)} potential shortages from FDA data. {len(no_impact_drugs)} drugs show no shortage signals."
    }

if __name__ == '__main__':
    # Test Agent 1
    import uuid
    test_run_id = str(uuid.uuid4())
    result = run(test_run_id)
    print("\n" + "="*60)
    print("Test Result:")
    print(json.dumps(result, indent=2, default=str))

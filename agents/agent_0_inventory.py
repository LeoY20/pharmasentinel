"""
Agent 0 — Inventory Analyzer & Burn Rate Calculator

Responsibilities:
- Fetches current drug inventory and surgery schedule
- Computes basic burn rates (stock / daily usage)
- Uses LLM to predict future usage based on scheduled surgeries
- Identifies drugs at risk based on burn rate and criticality
- Updates drugs table with predictions
- Logs analysis to agent_logs

API Key: DEDALUS_API_KEY_1 (index 0)
"""

import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .shared import (
    supabase,
    call_dedalus,
    log_agent_output,
    get_drugs_inventory,
    get_surgery_schedule,
    calculate_burn_rate,
    MONITORED_DRUGS,
    MONITORED_DRUG_NAMES
)

AGENT_NAME = "agent_0"
API_KEY_INDEX = 0

def aggregate_surgery_demand(surgeries: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Aggregate total drug demand from upcoming surgeries.

    Args:
        surgeries: List of surgery records with drugs_required JSONB

    Returns:
        Dictionary mapping drug_name -> total quantity needed
    """
    demand = {}

    for surgery in surgeries:
        drugs_required = surgery.get('drugs_required', [])

        for drug_req in drugs_required:
            drug_name = drug_req.get('drug_name')
            quantity = drug_req.get('quantity', 0)

            if drug_name:
                demand[drug_name] = demand.get(drug_name, 0) + quantity

    return demand

def build_system_prompt() -> str:
    """Build the system prompt for Agent 0."""
    return f"""You are an expert hospital pharmacy inventory analyst. Your role is to analyze drug inventory levels, predict future usage based on surgical demand, and identify supply risks.

# CONTEXT

The hospital tracks {len(MONITORED_DRUGS)} critical drugs ranked by criticality (1 = most critical):

{json.dumps(MONITORED_DRUGS, indent=2)}

# YOUR TASK

You will receive:
1. Current inventory data for all monitored drugs
2. Upcoming surgery schedule (next 30 days) with drug requirements per surgery
3. Basic burn rate calculations (stock / daily usage)

You must:
1. Calculate predicted daily usage = current daily usage + (surgery demand ÷ 30)
2. Calculate predicted burn rate = stock / predicted daily usage
3. Assess risk level for each drug considering:
   - Burn rate (< 7 days = CRITICAL, 7-14 = HIGH, 14-30 = MEDIUM, 30+ = LOW)
   - Criticality ranking (drugs ranked 1-5 are highest priority)
   - Surgery schedule impact
4. Identify specific surgeries that may be impacted by low stock
5. Determine usage trend (INCREASING, STABLE, DECREASING)

# DECISION FRAMEWORK

Risk Level Assessment:
- CRITICAL: Burn rate < 7 days OR (burn rate < 14 days AND criticality rank ≤ 3)
- HIGH: Burn rate 7-14 days OR (burn rate < 21 days AND criticality rank ≤ 5)
- MEDIUM: Burn rate 14-30 days
- LOW: Burn rate > 30 days

Surgery Impact:
- Flag any surgery scheduled within the predicted burn-out window
- Consider cumulative demand across multiple surgeries

# OUTPUT FORMAT

You MUST respond with ONLY valid JSON matching this exact schema:

{{
    "drug_analysis": [
        {{
            "drug_name": "string",
            "current_stock": 0,
            "daily_usage_rate": 0,
            "predicted_daily_usage_rate": 0,
            "burn_rate_days": 0,
            "predicted_burn_rate_days": 0,
            "trend": "INCREASING | STABLE | DECREASING",
            "risk_level": "LOW | MEDIUM | HIGH | CRITICAL",
            "notes": "string"
        }}
    ],
    "schedule_impact": [
        {{
            "surgery_date": "YYYY-MM-DD",
            "surgery_type": "string",
            "drugs_at_risk": ["drug_name"],
            "recommendation": "string"
        }}
    ],
    "summary": "string"
}}

Respond with ONLY the JSON. No markdown, no explanations."""

def run(run_id: str) -> Dict[str, Any]:
    """
    Execute Agent 0 analysis.

    Args:
        run_id: UUID of the current pipeline run

    Returns:
        Analysis results dictionary
    """
    print(f"\n{'='*60}")
    print(f"Agent 0: Inventory Analyzer")
    print(f"Run ID: {run_id}")
    print(f"{'='*60}\n")

    try:
        # Fetch data
        print("Fetching drug inventory...")
        drugs = get_drugs_inventory()
        print(f"✓ Found {len(drugs)} drugs")

        print("Fetching surgery schedule...")
        surgeries = get_surgery_schedule(days_ahead=30)
        print(f"✓ Found {len(surgeries)} scheduled surgeries")

        # Calculate basic burn rates
        print("\nCalculating burn rates...")
        for drug in drugs:
            burn_rate = calculate_burn_rate(
                float(drug.get('stock_quantity', 0)),
                float(drug.get('usage_rate_daily', 0))
            )
            drug['burn_rate_days'] = burn_rate

        # Aggregate surgery demand
        surgery_demand = aggregate_surgery_demand(surgeries)
        print(f"✓ Aggregated demand for {len(surgery_demand)} drugs from surgeries")

        # Build user prompt
        user_prompt = f"""# CURRENT INVENTORY

{json.dumps(drugs, indent=2, default=str)}

# UPCOMING SURGERIES (Next 30 Days)

{json.dumps(surgeries, indent=2, default=str)}

# AGGREGATED SURGERY DEMAND

{json.dumps(surgery_demand, indent=2)}

Please analyze the inventory, predict future usage, and identify risks."""

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
            analysis = generate_fallback_analysis(drugs, surgeries, surgery_demand)
            print("✓ Using fallback analysis")

        # Update drugs table with predictions
        print("\nUpdating drugs table with predictions...")
        drug_analysis_map = {
            item['drug_name']: item
            for item in analysis.get('drug_analysis', [])
        }

        for drug in drugs:
            drug_name = drug['name']
            analysis_data = drug_analysis_map.get(drug_name, {})

            if analysis_data:
                update_data = {
                    'predicted_usage_rate': analysis_data.get('predicted_daily_usage_rate'),
                    'predicted_burn_rate_days': analysis_data.get('predicted_burn_rate_days'),
                    'burn_rate_days': analysis_data.get('burn_rate_days'),
                    'updated_at': datetime.now().isoformat()
                }

                supabase.table('drugs').update(update_data).eq('id', drug['id']).execute()

        print(f"✓ Updated {len(drugs)} drug records")

        # Log to agent_logs
        summary = analysis.get('summary', 'Inventory analysis completed')
        log_agent_output(AGENT_NAME, run_id, analysis, summary)

        print(f"\n✓ Agent 0 completed successfully")
        print(f"  - Analyzed {len(drugs)} drugs")
        print(f"  - Evaluated {len(surgeries)} surgeries")
        print(f"  - Identified {len([d for d in analysis.get('drug_analysis', []) if d.get('risk_level') in ['HIGH', 'CRITICAL']])} high-risk drugs")

        return analysis

    except Exception as e:
        print(f"\n✗ Agent 0 failed: {e}")
        error_payload = {
            "error": str(e),
            "summary": f"Agent 0 failed: {e}"
        }
        log_agent_output(AGENT_NAME, run_id, error_payload, f"ERROR: {e}")
        raise

def generate_fallback_analysis(
    drugs: List[Dict[str, Any]],
    surgeries: List[Dict[str, Any]],
    surgery_demand: Dict[str, float]
) -> Dict[str, Any]:
    """
    Generate fallback analysis when LLM is unavailable.

    Args:
        drugs: Drug inventory
        surgeries: Surgery schedule
        surgery_demand: Aggregated surgery demand

    Returns:
        Analysis dictionary matching expected schema
    """
    drug_analysis = []

    for drug in drugs:
        drug_name = drug['name']
        current_stock = float(drug.get('stock_quantity', 0))
        daily_usage = float(drug.get('usage_rate_daily', 0))
        surgery_extra = surgery_demand.get(drug_name, 0) / 30.0

        predicted_daily = daily_usage + surgery_extra
        burn_rate = calculate_burn_rate(current_stock, daily_usage)
        predicted_burn = calculate_burn_rate(current_stock, predicted_daily) if predicted_daily > 0 else None

        # Determine risk level
        criticality_rank = drug.get('criticality_rank', 99)
        if predicted_burn:
            if predicted_burn < 7 or (predicted_burn < 14 and criticality_rank <= 3):
                risk_level = "CRITICAL"
            elif predicted_burn < 14 or (predicted_burn < 21 and criticality_rank <= 5):
                risk_level = "HIGH"
            elif predicted_burn < 30:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
        else:
            risk_level = "LOW"

        # Determine trend
        if predicted_daily > daily_usage * 1.2:
            trend = "INCREASING"
        elif predicted_daily < daily_usage * 0.8:
            trend = "DECREASING"
        else:
            trend = "STABLE"

        drug_analysis.append({
            "drug_name": drug_name,
            "current_stock": current_stock,
            "daily_usage_rate": daily_usage,
            "predicted_daily_usage_rate": predicted_daily,
            "burn_rate_days": burn_rate,
            "predicted_burn_rate_days": predicted_burn,
            "trend": trend,
            "risk_level": risk_level,
            "notes": f"Fallback analysis. Surgery demand adds {surgery_extra:.1f} units/day."
        })

    schedule_impact = []
    for surgery in surgeries[:5]:  # Top 5 upcoming
        drugs_at_risk = []
        for drug_req in surgery.get('drugs_required', []):
            drug_name = drug_req.get('drug_name')
            if drug_name:
                drug_data = next((d for d in drug_analysis if d['drug_name'] == drug_name), None)
                if drug_data and drug_data.get('risk_level') in ['HIGH', 'CRITICAL']:
                    drugs_at_risk.append(drug_name)

        if drugs_at_risk:
            schedule_impact.append({
                "surgery_date": str(surgery.get('scheduled_date')),
                "surgery_type": surgery.get('surgery_type'),
                "drugs_at_risk": drugs_at_risk,
                "recommendation": f"Restock {', '.join(drugs_at_risk)} before surgery"
            })

    return {
        "drug_analysis": drug_analysis,
        "schedule_impact": schedule_impact,
        "summary": f"Fallback analysis completed. {len([d for d in drug_analysis if d['risk_level'] in ['HIGH', 'CRITICAL']])} drugs at high risk."
    }

if __name__ == '__main__':
    # Test Agent 0
    import uuid
    test_run_id = str(uuid.uuid4())
    result = run(test_run_id)
    print("\n" + "="*60)
    print("Test Result:")
    print(json.dumps(result, indent=2, default=str))

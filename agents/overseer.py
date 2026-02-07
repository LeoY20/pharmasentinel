"""
Overseer Agent — Decision Synthesizer

Responsibilities:
- Reads all agent_logs for current run_id
- Synthesizes intelligence from Agents 0, 1, and 2
- Makes decisions using a structured framework
- Writes alerts to the alerts table
- Returns lists of drugs needing substitutes and orders for downstream agents

API Key: DEDALUS_API_KEY_2 (index 1)
"""

import json
from typing import Dict, Any, List
from datetime import datetime
from .shared import (
    supabase,
    call_dedalus,
    log_agent_output,
    get_agent_logs,
    get_drugs_inventory,
    get_unresolved_shortages,
    MONITORED_DRUGS
)

AGENT_NAME = "overseer"
API_KEY_INDEX = 1

def build_system_prompt() -> str:
    """Build the system prompt for the Overseer."""
    return f"""You are the Chief Decision Maker for a hospital pharmacy supply chain management system. Your role is to synthesize intelligence from multiple data sources and make actionable decisions to prevent drug shortages and ensure patient safety.

# CONTEXT

The hospital monitors {len(MONITORED_DRUGS)} critical drugs ranked by criticality (1 = most critical):

{json.dumps(MONITORED_DRUGS, indent=2)}

# YOUR TASK

You will receive:
1. Agent 0 output: Inventory analysis with burn rates and predicted usage
2. Agent 1 output: FDA shortage monitoring data
3. Agent 2 output: News sentiment and supply chain risk signals
4. Current drug inventory snapshot
5. Unresolved shortage records

You must synthesize this intelligence and make decisions following the framework below.

# DECISION FRAMEWORK

**IMMEDIATE ACTION (burn_rate < 7 days):**
- Generate `RESTOCK_NOW` alert with URGENT or CRITICAL severity
- If drug has criticality rank ≤ 5 AND there's an active shortage → also generate `SUBSTITUTE_RECOMMENDED` alert
- If a surgery is at risk within 48 hours → generate `SCHEDULE_CHANGE` alert with CRITICAL severity

**WARNING ZONE (burn_rate 7–14 days):**
- Generate `SHORTAGE_WARNING` alert with WARNING severity
- Combine with any FDA/news signals to escalate severity to URGENT if:
  - FDA reports ongoing shortage for this drug, OR
  - News indicates HIGH or CRITICAL supply chain impact
- For drugs ranked 1-5, recommend proactive restocking

**PLANNING ZONE (burn_rate 14–30 days + any risk signal):**
- Generate `SUPPLY_CHAIN_RISK` alert with INFO or WARNING severity
- If FDA or news signals indicate future risk → escalate to WARNING
- Recommend monitoring and advance planning

**SEVERITY MAPPING:**
- CRITICAL: Patient care at immediate risk (life-saving drug < 3 days stock, surgery at risk)
- URGENT: Action needed within 48 hours (critical drug < 7 days, surgery within week)
- WARNING: Action needed this week (burn rate 7-14 days, or risk signals present)
- INFO: Awareness only (planning zone, low-priority drugs)

**SUBSTITUTE RECOMMENDATIONS:**
Recommend substitutes when:
- Drug has criticality rank ≤ 5 AND burn_rate < 14 days
- Active FDA shortage exists for the drug
- News indicates CRITICAL supply chain disruption

**ORDER RECOMMENDATIONS:**
Recommend orders when:
- Burn rate < reorder_threshold_days (typically 14 days)
- Active shortage detected (order from backup suppliers)
- Predicted burn rate < 21 days for drugs ranked 1-5

**ORDER URGENCY:**
- EMERGENCY: Need within 24 hours (burn < 3 days, surgery tomorrow)
- EXPEDITED: Need within 3 days (burn < 7 days)
- ROUTINE: Need within 7-14 days (normal restock)

**SCHEDULE ADJUSTMENTS:**
Recommend surgery rescheduling when:
- Required drug has burn rate < surgery date offset
- High likelihood of stockout before surgery
- No immediate substitute available

# OUTPUT FORMAT

You MUST respond with ONLY valid JSON matching this exact schema:

{{
    "decisions": [
        {{
            "action_type": "RESTOCK_NOW | SHORTAGE_WARNING | SUBSTITUTE_RECOMMENDED | SCHEDULE_CHANGE | SUPPLY_CHAIN_RISK | AUTO_ORDER_PLACED",
            "severity": "INFO | WARNING | URGENT | CRITICAL",
            "drug_name": "string",
            "title": "string (short headline)",
            "description": "string (full recommendation)",
            "requires_substitute": false,
            "requires_order": false,
            "order_details": {{
                "drug_name": "string",
                "quantity_needed": 0,
                "urgency": "ROUTINE | EXPEDITED | EMERGENCY",
                "preferred_supplier_type": "PRIMARY | BACKUP | NEARBY_HOSPITAL | ANY"
            }}
        }}
    ],
    "drugs_needing_substitutes": ["drug_name", "..."],
    "drugs_needing_orders": [
        {{"drug_name": "string", "quantity": 0, "urgency": "ROUTINE | EXPEDITED | EMERGENCY"}}
    ],
    "schedule_adjustments": [
        {{
            "surgery_date": "YYYY-MM-DD",
            "surgery_type": "string",
            "recommendation": "string"
        }}
    ],
    "summary": "string"
}}

Respond with ONLY the JSON. No markdown, no explanations."""

def run(run_id: str) -> Dict[str, Any]:
    """
    Execute Overseer decision synthesis.

    Args:
        run_id: UUID of the current pipeline run

    Returns:
        Decision results dictionary
    """
    print(f"\n{'='*60}")
    print(f"Overseer: Decision Synthesizer")
    print(f"Run ID: {run_id}")
    print(f"{'='*60}\n")

    try:
        # Fetch all agent logs for this run
        print("Fetching agent outputs...")
        agent_logs = get_agent_logs(run_id)
        print(f"✓ Found {len(agent_logs)} agent log entries")

        # Organize by agent
        agent_outputs = {}
        for log in agent_logs:
            agent_name = log.get('agent_name')
            if agent_name and agent_name != AGENT_NAME:  # Don't include own logs
                agent_outputs[agent_name] = log.get('payload', {})

        print(f"  Agent 0 (Inventory): {'✓' if 'agent_0' in agent_outputs else '✗'}")
        print(f"  Agent 1 (FDA): {'✓' if 'agent_1' in agent_outputs else '✗'}")
        print(f"  Agent 2 (News): {'✓' if 'agent_2' in agent_outputs else '✗'}")

        # Fetch current state
        print("\nFetching current inventory and shortages...")
        drugs = get_drugs_inventory()
        shortages = get_unresolved_shortages(days_back=180)
        print(f"✓ Current state: {len(drugs)} drugs, {len(shortages)} unresolved shortages")

        # Build user prompt
        user_prompt = f"""# AGENT INTELLIGENCE

## Agent 0: Inventory Analysis
{json.dumps(agent_outputs.get('agent_0', {}), indent=2, default=str)}

## Agent 1: FDA Shortage Monitoring
{json.dumps(agent_outputs.get('agent_1', {}), indent=2, default=str)}

## Agent 2: News & Supply Chain Analysis
{json.dumps(agent_outputs.get('agent_2', {}), indent=2, default=str)}

# CURRENT STATE

## Drug Inventory
{json.dumps(drugs, indent=2, default=str)}

## Unresolved Shortages
{json.dumps(shortages, indent=2, default=str)}

# YOUR MISSION

Synthesize all this intelligence and make actionable decisions following the decision framework. Prioritize patient safety and operational continuity."""

        # Call Dedalus LLM
        print("\nCalling Dedalus LLM for decision synthesis...")
        system_prompt = build_system_prompt()

        try:
            decisions = call_dedalus(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                api_key_index=API_KEY_INDEX,
                temperature=0.2
            )
            print("✓ Received decision synthesis")
        except Exception as e:
            print(f"WARNING: LLM call failed: {e}")
            # Provide fallback decisions
            decisions = generate_fallback_decisions(drugs, shortages, agent_outputs)
            print("✓ Using fallback decision logic")

        # Write alerts to alerts table
        print("\nWriting alerts to database...")
        alert_decisions = decisions.get('decisions', [])
        inserted_count = 0

        for decision in alert_decisions:
            alert_record = {
                'run_id': run_id,
                'alert_type': decision.get('action_type'),
                'severity': decision.get('severity'),
                'drug_name': decision.get('drug_name'),
                'title': decision.get('title'),
                'description': decision.get('description'),
                'action_payload': decision.get('order_details'),
                'acknowledged': False
            }

            # Try to match drug_id
            drug = next((d for d in drugs if d['name'] == decision.get('drug_name')), None)
            if drug:
                alert_record['drug_id'] = drug['id']

            supabase.table('alerts').insert(alert_record).execute()
            inserted_count += 1

        print(f"✓ Inserted {inserted_count} alerts")

        # Log to agent_logs
        summary = decisions.get('summary', 'Decision synthesis completed')
        log_agent_output(AGENT_NAME, run_id, decisions, summary)

        print(f"\n✓ Overseer completed successfully")
        print(f"  - Synthesized {len(agent_outputs)} agent outputs")
        print(f"  - Generated {len(alert_decisions)} decisions/alerts")
        print(f"  - Drugs needing substitutes: {len(decisions.get('drugs_needing_substitutes', []))}")
        print(f"  - Drugs needing orders: {len(decisions.get('drugs_needing_orders', []))}")

        return decisions

    except Exception as e:
        print(f"\n✗ Overseer failed: {e}")
        error_payload = {
            "error": str(e),
            "summary": f"Overseer failed: {e}"
        }
        log_agent_output(AGENT_NAME, run_id, error_payload, f"ERROR: {e}")
        raise

def generate_fallback_decisions(
    drugs: List[Dict[str, Any]],
    shortages: List[Dict[str, Any]],
    agent_outputs: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate fallback decisions when LLM is unavailable.

    Args:
        drugs: Current drug inventory
        shortages: Unresolved shortage records
        agent_outputs: Outputs from Phase 1 agents

    Returns:
        Decision dictionary matching expected schema
    """
    decisions = []
    drugs_needing_substitutes = []
    drugs_needing_orders = []
    schedule_adjustments = []

    shortage_drug_names = {s.get('drug_name') for s in shortages}

    for drug in drugs:
        drug_name = drug['name']
        burn_rate = drug.get('predicted_burn_rate_days') or drug.get('burn_rate_days')
        criticality_rank = drug.get('criticality_rank', 99)
        reorder_threshold = drug.get('reorder_threshold_days', 14)
        stock = float(drug.get('stock_quantity', 0))
        daily_usage = float(drug.get('predicted_usage_rate') or drug.get('usage_rate_daily', 0))

        has_shortage = drug_name in shortage_drug_names

        # IMMEDIATE ACTION (< 7 days)
        if burn_rate and burn_rate < 7:
            severity = "CRITICAL" if criticality_rank <= 3 else "URGENT"

            decisions.append({
                "action_type": "RESTOCK_NOW",
                "severity": severity,
                "drug_name": drug_name,
                "title": f"URGENT: {drug_name} stock critically low",
                "description": f"{drug_name} has only {burn_rate:.1f} days of stock remaining (burn rate: {daily_usage:.1f} {drug.get('unit')}/day). Immediate restocking required.",
                "requires_substitute": criticality_rank <= 5 and has_shortage,
                "requires_order": True,
                "order_details": {
                    "drug_name": drug_name,
                    "quantity_needed": int(daily_usage * 30),  # 30-day supply
                    "urgency": "EMERGENCY" if burn_rate < 3 else "EXPEDITED",
                    "preferred_supplier_type": "NEARBY_HOSPITAL" if burn_rate < 3 else "PRIMARY"
                }
            })

            drugs_needing_orders.append({
                "drug_name": drug_name,
                "quantity": int(daily_usage * 30),
                "urgency": "EMERGENCY" if burn_rate < 3 else "EXPEDITED"
            })

            if criticality_rank <= 5 and has_shortage:
                drugs_needing_substitutes.append(drug_name)
                decisions.append({
                    "action_type": "SUBSTITUTE_RECOMMENDED",
                    "severity": "URGENT",
                    "drug_name": drug_name,
                    "title": f"Find substitute for {drug_name}",
                    "description": f"{drug_name} is critically low AND has active shortage. Clinical substitutes recommended.",
                    "requires_substitute": True,
                    "requires_order": False
                })

        # WARNING ZONE (7-14 days)
        elif burn_rate and burn_rate < 14:
            severity = "WARNING"
            if has_shortage:
                severity = "URGENT"

            decisions.append({
                "action_type": "SHORTAGE_WARNING",
                "severity": severity,
                "drug_name": drug_name,
                "title": f"{drug_name} entering shortage warning zone",
                "description": f"{drug_name} has {burn_rate:.1f} days of stock remaining. {'Active shortage reported. ' if has_shortage else ''}Recommend restocking within the week.",
                "requires_substitute": False,
                "requires_order": True,
                "order_details": {
                    "drug_name": drug_name,
                    "quantity_needed": int(daily_usage * 30),
                    "urgency": "EXPEDITED" if has_shortage else "ROUTINE",
                    "preferred_supplier_type": "PRIMARY"
                }
            })

            drugs_needing_orders.append({
                "drug_name": drug_name,
                "quantity": int(daily_usage * 30),
                "urgency": "EXPEDITED" if has_shortage else "ROUTINE"
            })

        # PLANNING ZONE (14-30 days with risk signals)
        elif burn_rate and burn_rate < 30 and has_shortage:
            decisions.append({
                "action_type": "SUPPLY_CHAIN_RISK",
                "severity": "WARNING" if criticality_rank <= 5 else "INFO",
                "drug_name": drug_name,
                "title": f"Supply chain risk detected for {drug_name}",
                "description": f"{drug_name} has {burn_rate:.1f} days of stock. Active shortage reported. Monitor closely and consider advance ordering.",
                "requires_substitute": False,
                "requires_order": False
            })

    return {
        "decisions": decisions,
        "drugs_needing_substitutes": drugs_needing_substitutes,
        "drugs_needing_orders": drugs_needing_orders,
        "schedule_adjustments": schedule_adjustments,
        "summary": f"Fallback decisions generated. {len(decisions)} alerts created, {len(drugs_needing_orders)} orders needed."
    }

if __name__ == '__main__':
    # Test Overseer
    import uuid
    test_run_id = str(uuid.uuid4())
    result = run(test_run_id)
    print("\n" + "="*60)
    print("Test Result:")
    print(json.dumps(result, indent=2, default=str))

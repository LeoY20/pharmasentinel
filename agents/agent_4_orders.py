"""
Agent 4 — Order & Supplier Manager

Responsibilities:
- Receives list of drugs needing orders from Overseer
- Merges hard-coded major suppliers with database suppliers
- Uses LLM to select optimal suppliers based on urgency, proximity, and price
- Recommends hospital transfers for emergency situations
- Writes order recommendations to alerts table
- Logs analysis to agent_logs

API Key: DEDALUS_API_KEY_3 (index 2)
"""

import json
from typing import Dict, Any, List
from .shared import (
    supabase,
    call_dedalus,
    log_agent_output,
    get_suppliers,
    get_drugs_inventory,
    MONITORED_DRUGS,
    HOSPITAL_LOCATION
)

AGENT_NAME = "agent_4"
API_KEY_INDEX = 2

# Hard-coded major US pharmaceutical distributors and manufacturers
MAJOR_SUPPLIERS = [
    {
        "name": "McKesson Corporation",
        "type": "DISTRIBUTOR",
        "region": "National (US)",
        "lead_time_days": 1,
        "reliability_score": 0.98
    },
    {
        "name": "Cardinal Health",
        "type": "DISTRIBUTOR",
        "region": "National (US)",
        "lead_time_days": 1,
        "reliability_score": 0.97
    },
    {
        "name": "AmerisourceBergen",
        "type": "DISTRIBUTOR",
        "region": "National (US)",
        "lead_time_days": 1,
        "reliability_score": 0.96
    },
    {
        "name": "Morris & Dickson",
        "type": "DISTRIBUTOR",
        "region": "Southeast US",
        "lead_time_days": 2,
        "reliability_score": 0.95
    },
    {
        "name": "Henry Schein",
        "type": "DISTRIBUTOR",
        "region": "National (US)",
        "lead_time_days": 2,
        "reliability_score": 0.94
    },
    {
        "name": "Pfizer (Direct)",
        "type": "MANUFACTURER",
        "region": "Global",
        "lead_time_days": 5,
        "reliability_score": 0.99
    },
    {
        "name": "Teva Pharmaceuticals",
        "type": "MANUFACTURER",
        "region": "Global",
        "lead_time_days": 7,
        "reliability_score": 0.93
    },
    {
        "name": "Fresenius Kabi",
        "type": "MANUFACTURER",
        "region": "Global",
        "lead_time_days": 5,
        "reliability_score": 0.95
    },
    {
        "name": "Baxter International",
        "type": "MANUFACTURER",
        "region": "Global",
        "lead_time_days": 3,
        "reliability_score": 0.96
    },
    {
        "name": "Mylan/Viatris",
        "type": "MANUFACTURER",
        "region": "Global",
        "lead_time_days": 7,
        "reliability_score": 0.94
    }
]

def build_system_prompt() -> str:
    """Build the system prompt for Agent 4."""
    return f"""You are an expert pharmaceutical procurement specialist for hospital supply chain operations. Your role is to recommend optimal suppliers and create purchase orders based on urgency, cost, reliability, and availability.

# CONTEXT

The hospital monitors {len(MONITORED_DRUGS)} critical drugs ranked by criticality (1 = most critical):

{json.dumps(MONITORED_DRUGS, indent=2)}

Hospital Location: {HOSPITAL_LOCATION}

# YOUR TASK

You will receive:
1. List of drugs needing orders with quantities and urgency levels
2. Database of available suppliers (including nearby hospitals)
3. Hard-coded list of major US pharmaceutical distributors
4. Current drug inventory and pricing

You must:
1. For each drug order, select the optimal supplier
2. Always include a backup supplier
3. Consider urgency, lead time, proximity, price, and reliability
4. Recommend hospital transfers for emergency orders
5. Estimate total costs
6. Provide justification for each recommendation

# DECISION LOGIC

**EMERGENCY Orders (need within 24 hours):**
- Prefer nearby hospital transfers (lead time = 0 days)
- If no hospital option, use national distributors with express shipping
- Cost is secondary to speed
- Always include 2+ backup options

**EXPEDITED Orders (need within 3 days):**
- National distributors with standard shipping (1-2 days)
- Consider nearby hospitals as backup
- Balance speed and cost
- Prioritize high-reliability suppliers (score > 0.95)

**ROUTINE Orders (need within 7-14 days):**
- Optimize for best price among reliable suppliers
- Can use manufacturers directly for bulk orders
- Consider lead time but not critical
- Focus on cost efficiency

**Critical Drug Considerations (rank 1-5):**
- Recommend maintaining 30-day supply
- Always order from 2 sources simultaneously for redundancy
- Use highest reliability suppliers only (score ≥ 0.95)

**Supplier Selection Priority:**
1. Urgency match (lead time ≤ time window)
2. Proximity (nearby hospitals for emergencies)
3. Reliability score
4. Price (for routine orders)
5. Historical performance

# OUTPUT FORMAT

You MUST respond with ONLY valid JSON matching this exact schema:

{{
    "orders": [
        {{
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
        }}
    ],
    "hospital_transfer_requests": [
        {{
            "target_hospital": "string",
            "drug_name": "string",
            "quantity": 0,
            "justification": "string"
        }}
    ],
    "cost_summary": {{
        "total_estimated_cost": 0,
        "emergency_orders_cost": 0,
        "routine_orders_cost": 0
    }},
    "summary": "string"
}}

Respond with ONLY the JSON. No markdown, no explanations."""

def run(run_id: str, drugs_needing_orders: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Execute Agent 4 order management.

    Args:
        run_id: UUID of the current pipeline run
        drugs_needing_orders: List of {drug_name, quantity, urgency} objects

    Returns:
        Order recommendation dictionary
    """
    print(f"\n{'='*60}")
    print(f"Agent 4: Order & Supplier Manager")
    print(f"Run ID: {run_id}")
    print(f"{'='*60}\n")

    if not drugs_needing_orders:
        print("No drugs needing orders. Skipping Agent 4.")
        return {
            "orders": [],
            "hospital_transfer_requests": [],
            "cost_summary": {"total_estimated_cost": 0, "emergency_orders_cost": 0, "routine_orders_cost": 0},
            "summary": "No orders required."
        }

    try:
        print(f"Processing orders for {len(drugs_needing_orders)} drugs:")
        for order in drugs_needing_orders:
            print(f"  - {order.get('drug_name')}: {order.get('quantity')} units ({order.get('urgency')})")

        # Fetch database suppliers
        print("\nFetching supplier database...")
        db_suppliers = get_suppliers(active_only=True)
        print(f"✓ Found {len(db_suppliers)} active suppliers in database")

        # Fetch drug inventory for pricing
        print("Fetching drug inventory for pricing...")
        drugs = get_drugs_inventory()
        drug_map = {drug['name']: drug for drug in drugs}
        print(f"✓ Loaded {len(drugs)} drugs")

        # Build user prompt
        user_prompt = f"""# ORDERS TO PROCESS

{json.dumps(drugs_needing_orders, indent=2)}

# AVAILABLE SUPPLIERS

## Database Suppliers (Including Nearby Hospitals)
{json.dumps(db_suppliers, indent=2, default=str)}

## Major US Pharmaceutical Suppliers
{json.dumps(MAJOR_SUPPLIERS, indent=2)}

# CURRENT DRUG INVENTORY & PRICING

{json.dumps(drugs, indent=2, default=str)}

# HOSPITAL LOCATION

{HOSPITAL_LOCATION}

Please recommend optimal suppliers for each order, considering urgency, cost, and reliability."""

        # Call Dedalus LLM
        print("\nCalling Dedalus LLM for supplier optimization...")
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
            analysis = generate_fallback_analysis(drugs_needing_orders, db_suppliers, drug_map)
            print("✓ Using fallback analysis")

        # Write order alerts to alerts table
        print("\nWriting order alerts to database...")
        orders = analysis.get('orders', [])
        inserted_count = 0

        for order in orders:
            alert_record = {
                'run_id': run_id,
                'alert_type': 'AUTO_ORDER_PLACED',
                'severity': 'URGENT' if order.get('urgency') == 'EMERGENCY' else 'WARNING',
                'drug_name': order.get('drug_name'),
                'title': f"Order recommended: {order.get('drug_name')}",
                'description': f"Order {order.get('quantity')} {order.get('unit')} from {order.get('recommended_supplier')}. {order.get('reasoning', '')}",
                'action_payload': order,
                'acknowledged': False
            }

            # Try to match drug_id
            drug = drug_map.get(order.get('drug_name'))
            if drug:
                alert_record['drug_id'] = drug['id']

            supabase.table('alerts').insert(alert_record).execute()
            inserted_count += 1
            print(f"  ✓ Order alert: {order.get('drug_name')} from {order.get('recommended_supplier')}")

        print(f"✓ Inserted {inserted_count} order alerts")

        # Log to agent_logs
        summary = analysis.get('summary', f'Order management completed. {len(orders)} orders processed.')
        log_agent_output(AGENT_NAME, run_id, analysis, summary)

        cost_summary = analysis.get('cost_summary', {})
        print(f"\n✓ Agent 4 completed successfully")
        print(f"  - Processed {len(drugs_needing_orders)} order requests")
        print(f"  - Generated {len(orders)} order recommendations")
        print(f"  - Hospital transfers: {len(analysis.get('hospital_transfer_requests', []))}")
        print(f"  - Total estimated cost: ${cost_summary.get('total_estimated_cost', 0):,.2f}")

        return analysis

    except Exception as e:
        print(f"\n✗ Agent 4 failed: {e}")
        error_payload = {
            "error": str(e),
            "summary": f"Agent 4 failed: {e}"
        }
        log_agent_output(AGENT_NAME, run_id, error_payload, f"ERROR: {e}")
        raise

def generate_fallback_analysis(
    drugs_needing_orders: List[Dict[str, Any]],
    db_suppliers: List[Dict[str, Any]],
    drug_map: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate fallback order analysis when LLM is unavailable.

    Args:
        drugs_needing_orders: List of order requests
        db_suppliers: Database suppliers
        drug_map: Drug inventory map

    Returns:
        Analysis dictionary matching expected schema
    """
    orders = []
    hospital_transfers = []
    total_cost = 0
    emergency_cost = 0
    routine_cost = 0

    for order_req in drugs_needing_orders:
        drug_name = order_req.get('drug_name')
        quantity = order_req.get('quantity', 0)
        urgency = order_req.get('urgency', 'ROUTINE')

        drug_info = drug_map.get(drug_name)
        unit = drug_info.get('unit', 'units') if drug_info else 'units'
        price_per_unit = float(drug_info.get('price_per_unit', 10.0)) if drug_info else 10.0

        # Find suppliers for this drug
        drug_suppliers = [s for s in db_suppliers if s.get('drug_name') == drug_name]
        nearby_hospitals = [s for s in drug_suppliers if s.get('is_nearby_hospital')]
        other_suppliers = [s for s in drug_suppliers if not s.get('is_nearby_hospital')]

        # Simple selection logic
        if urgency == 'EMERGENCY':
            if nearby_hospitals:
                recommended = nearby_hospitals[0]['name']
                supplier_type = "NEARBY_HOSPITAL"
                lead_time = 0
                backup = nearby_hospitals[1]['name'] if len(nearby_hospitals) > 1 else "McKesson Corporation"
            else:
                recommended = "McKesson Corporation"
                supplier_type = "DISTRIBUTOR"
                lead_time = 1
                backup = "Cardinal Health"

            if nearby_hospitals:
                hospital_transfers.append({
                    "target_hospital": nearby_hospitals[0]['name'],
                    "drug_name": drug_name,
                    "quantity": quantity,
                    "justification": f"Emergency order for {drug_name}. Same-day transfer required."
                })

        elif urgency == 'EXPEDITED':
            if other_suppliers:
                recommended = other_suppliers[0]['name']
                supplier_type = "DISTRIBUTOR"
                lead_time = other_suppliers[0].get('lead_time_days', 1)
                backup = other_suppliers[1]['name'] if len(other_suppliers) > 1 else "Cardinal Health"
            else:
                recommended = "McKesson Corporation"
                supplier_type = "DISTRIBUTOR"
                lead_time = 1
                backup = "Cardinal Health"

        else:  # ROUTINE
            # Find cheapest supplier
            if other_suppliers:
                sorted_suppliers = sorted(other_suppliers, key=lambda s: s.get('price_per_unit', 999))
                recommended = sorted_suppliers[0]['name']
                supplier_type = "DISTRIBUTOR"
                lead_time = sorted_suppliers[0].get('lead_time_days', 2)
                price_per_unit = sorted_suppliers[0].get('price_per_unit', price_per_unit)
                backup = sorted_suppliers[1]['name'] if len(sorted_suppliers) > 1 else "AmerisourceBergen"
            else:
                recommended = "AmerisourceBergen"
                supplier_type = "DISTRIBUTOR"
                lead_time = 1
                backup = "McKesson Corporation"

        estimated_cost = quantity * price_per_unit
        total_cost += estimated_cost

        if urgency == 'EMERGENCY':
            emergency_cost += estimated_cost
        else:
            routine_cost += estimated_cost

        orders.append({
            "drug_name": drug_name,
            "quantity": quantity,
            "unit": unit,
            "urgency": urgency,
            "recommended_supplier": recommended,
            "supplier_type": supplier_type,
            "estimated_cost": estimated_cost,
            "estimated_delivery_days": lead_time,
            "backup_supplier": backup,
            "reasoning": f"Fallback: Selected {recommended} based on urgency ({urgency}) and lead time ({lead_time} days)."
        })

    return {
        "orders": orders,
        "hospital_transfer_requests": hospital_transfers,
        "cost_summary": {
            "total_estimated_cost": total_cost,
            "emergency_orders_cost": emergency_cost,
            "routine_orders_cost": routine_cost
        },
        "summary": f"Fallback analysis. Generated {len(orders)} orders with total cost ${total_cost:,.2f}."
    }

if __name__ == '__main__':
    # Test Agent 4
    import uuid
    test_run_id = str(uuid.uuid4())
    test_orders = [
        {"drug_name": "Epinephrine", "quantity": 100, "urgency": "EMERGENCY"},
        {"drug_name": "Propofol", "quantity": 50, "urgency": "EXPEDITED"},
        {"drug_name": "Penicillin", "quantity": 200, "urgency": "ROUTINE"}
    ]
    result = run(test_run_id, test_orders)
    print("\n" + "="*60)
    print("Test Result:")
    print(json.dumps(result, indent=2, default=str))

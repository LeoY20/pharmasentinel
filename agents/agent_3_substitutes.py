"""
Agent 3 — Drug Substitute Finder

Responsibilities:
- Receives list of drugs needing substitutes from Overseer
- Uses hard-coded substitution mappings (medically validated)
- Checks inventory to see if substitutes are in stock
- Uses LLM to rank substitutes by clinical appropriateness
- Upserts results to substitutes table
- Logs analysis to agent_logs

API Key: DEDALUS_API_KEY_3 (index 2)
"""

import json
from typing import Dict, Any, List
from .shared import (
    supabase,
    call_dedalus,
    log_agent_output,
    get_drugs_inventory,
    get_substitutes,
    MONITORED_DRUGS
)

AGENT_NAME = "agent_3"
API_KEY_INDEX = 2

# Hard-coded medically validated substitution mappings
SUBSTITUTION_MAPPINGS = {
    "Epinephrine": [
        {
            "name": "Norepinephrine",
            "notes": "For cardiac use only (NOT anaphylaxis). Similar vasopressor effects.",
            "preference_rank": 1
        },
        {
            "name": "Vasopressin",
            "notes": "Second-line for cardiac arrest. Different mechanism but can support BP.",
            "preference_rank": 2
        }
    ],
    "Propofol": [
        {
            "name": "Etomidate",
            "notes": "Shorter duration. Good for rapid sequence intubation. Less hypotension.",
            "preference_rank": 1
        },
        {
            "name": "Ketamine",
            "notes": "Useful for hemodynamically unstable patients. Maintains BP. Different side effect profile.",
            "preference_rank": 2
        },
        {
            "name": "Midazolam",
            "notes": "Slower onset. Benzodiazepine class. Useful for sedation but not ideal for induction.",
            "preference_rank": 3
        }
    ],
    "Penicillin": [
        {
            "name": "Amoxicillin",
            "notes": "Similar spectrum, oral or IV. Well tolerated. First choice substitute.",
            "preference_rank": 1
        },
        {
            "name": "Cephalexin",
            "notes": "First-generation cephalosporin. Check for penicillin allergy cross-reactivity (~10%).",
            "preference_rank": 2
        },
        {
            "name": "Azithromycin",
            "notes": "Macrolide. Use if penicillin allergy confirmed. Different spectrum.",
            "preference_rank": 3
        }
    ],
    "Levofloxacin": [
        {
            "name": "Moxifloxacin",
            "notes": "Same fluoroquinolone class. Similar spectrum with better anaerobic coverage.",
            "preference_rank": 1
        },
        {
            "name": "Ciprofloxacin",
            "notes": "Same fluoroquinolone class. Better for UTIs and GI infections.",
            "preference_rank": 2
        },
        {
            "name": "Doxycycline",
            "notes": "Tetracycline class. Different mechanism. Broad spectrum alternative.",
            "preference_rank": 3
        }
    ],
    "Heparin": [
        {
            "name": "Enoxaparin",
            "notes": "Low molecular weight heparin (LMWH). More predictable dosing. Preferred by many.",
            "preference_rank": 1
        },
        {
            "name": "Fondaparinux",
            "notes": "Synthetic factor Xa inhibitor. Use for HIT patients. No cross-reactivity.",
            "preference_rank": 2
        },
        {
            "name": "Warfarin",
            "notes": "Oral anticoagulant. Slower onset (days). Requires INR monitoring. For chronic use.",
            "preference_rank": 3
        }
    ],
    "Insulin": [
        {
            "name": "Insulin Lispro",
            "notes": "Rapid-acting analog (Humalog). Onset 15 min. For meal coverage.",
            "preference_rank": 1
        },
        {
            "name": "Insulin Glargine",
            "notes": "Long-acting basal insulin (Lantus). For basal coverage, not acute DKA.",
            "preference_rank": 2
        }
    ],
    "Morphine": [
        {
            "name": "Hydromorphone",
            "notes": "5-7x more potent than morphine. Dilaudid. Adjust dose carefully. Less nausea.",
            "preference_rank": 1
        },
        {
            "name": "Fentanyl",
            "notes": "50-100x more potent. Rapid onset. Use in ICU settings. Careful dosing required.",
            "preference_rank": 2
        },
        {
            "name": "Oxycodone",
            "notes": "Oral option. ~1.5x potency of morphine. For moderate to severe pain.",
            "preference_rank": 3
        }
    ],
    "IV Fluids": [
        {
            "name": "Lactated Ringers",
            "notes": "Better for large-volume resuscitation. Contains electrolytes. Preferred for trauma.",
            "preference_rank": 1
        },
        {
            "name": "Normal Saline",
            "notes": "0.9% NaCl. Standard isotonic crystalloid. Universal for most indications.",
            "preference_rank": 2
        },
        {
            "name": "D5W",
            "notes": "5% dextrose in water. For specific indications (hypoglycemia, maintenance). Not for resuscitation.",
            "preference_rank": 3
        }
    ],
    "Oxygen": [],  # No substitutes - flag for escalation
    "Vaccines": []  # Product-specific - requires case-by-case evaluation
}

def build_system_prompt() -> str:
    """Build the system prompt for Agent 3."""
    return f"""You are an expert clinical pharmacist specializing in drug substitution and therapeutic equivalence. Your role is to identify and recommend clinically appropriate drug substitutes when primary drugs are unavailable.

# CONTEXT

The hospital monitors {len(MONITORED_DRUGS)} critical drugs ranked by criticality (1 = most critical):

{json.dumps(MONITORED_DRUGS, indent=2)}

# YOUR TASK

You will receive:
1. List of drugs requiring substitutes
2. Hard-coded substitution mappings (medically validated)
3. Current inventory status for potential substitutes
4. Existing substitute records from the database

You must:
1. For each drug, review the hard-coded substitutes
2. Rank substitutes by clinical appropriateness (preference_rank: 1 = best)
3. Note dosing conversions and contraindications
4. Flag if a substitute is currently in stock
5. Flag drugs with NO viable substitute (e.g., Oxygen)
6. Provide clinical notes for each substitution

# CLINICAL GUIDELINES

Substitution Considerations:
- Therapeutic equivalence (same mechanism vs. different class)
- Dosing conversions (especially for high-potency opioids)
- Contraindications and allergy cross-reactivity
- Route of administration (IV vs. oral)
- Onset and duration differences
- Patient-specific factors (e.g., HIT for heparin alternatives)

Preference Ranking Criteria:
- Rank 1: Most similar mechanism, easiest conversion, fewest contraindications
- Rank 2: Acceptable alternative, may require dosing adjustment
- Rank 3: Last resort or for specific indications only

# OUTPUT FORMAT

You MUST respond with ONLY valid JSON matching this exact schema:

{{
    "substitutions": [
        {{
            "original_drug": "string",
            "substitutes": [
                {{
                    "name": "string",
                    "preference_rank": 1,
                    "equivalence_notes": "string",
                    "dosing_conversion": "string",
                    "contraindications": "string",
                    "in_stock": true,
                    "stock_quantity": 0
                }}
            ],
            "no_substitute_available": false,
            "clinical_notes": "string"
        }}
    ],
    "summary": "string"
}}

Respond with ONLY the JSON. No markdown, no explanations."""

def run(run_id: str, drugs_needing_substitutes: List[str]) -> Dict[str, Any]:
    """
    Execute Agent 3 substitute finding.

    Args:
        run_id: UUID of the current pipeline run
        drugs_needing_substitutes: List of drug names requiring substitutes

    Returns:
        Substitution analysis dictionary
    """
    print(f"\n{'='*60}")
    print(f"Agent 3: Drug Substitute Finder")
    print(f"Run ID: {run_id}")
    print(f"{'='*60}\n")

    if not drugs_needing_substitutes:
        print("No drugs needing substitutes. Skipping Agent 3.")
        return {
            "substitutions": [],
            "summary": "No drugs requiring substitutes."
        }

    try:
        print(f"Finding substitutes for {len(drugs_needing_substitutes)} drugs:")
        for drug in drugs_needing_substitutes:
            print(f"  - {drug}")

        # Fetch current inventory
        print("\nFetching current drug inventory...")
        all_drugs = get_drugs_inventory()
        drug_inventory_map = {drug['name']: drug for drug in all_drugs}
        print(f"✓ Loaded {len(all_drugs)} drugs from inventory")

        # Fetch existing substitutes
        print("Fetching existing substitute records...")
        existing_substitutes = get_substitutes()
        print(f"✓ Found {len(existing_substitutes)} existing substitute records")

        # Build substitution data
        substitution_data = []

        for drug_name in drugs_needing_substitutes:
            mappings = SUBSTITUTION_MAPPINGS.get(drug_name, [])

            # Enrich with inventory data
            enriched_mappings = []
            for mapping in mappings:
                sub_name = mapping['name']
                in_stock_drug = drug_inventory_map.get(sub_name)

                enriched_mappings.append({
                    **mapping,
                    "in_stock": in_stock_drug is not None,
                    "stock_quantity": float(in_stock_drug.get('stock_quantity', 0)) if in_stock_drug else 0
                })

            substitution_data.append({
                "drug_name": drug_name,
                "hard_coded_substitutes": enriched_mappings,
                "existing_db_records": [
                    sub for sub in existing_substitutes
                    if sub.get('drug_name') == drug_name
                ]
            })

        # Build user prompt
        user_prompt = f"""# DRUGS REQUIRING SUBSTITUTES

{json.dumps(drugs_needing_substitutes, indent=2)}

# SUBSTITUTION DATA (with inventory status)

{json.dumps(substitution_data, indent=2, default=str)}

Please analyze these substitutions, rank by clinical appropriateness, and provide dosing guidance."""

        # Call Dedalus LLM
        print("\nCalling Dedalus LLM for clinical analysis...")
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
            analysis = generate_fallback_analysis(drugs_needing_substitutes, substitution_data)
            print("✓ Using fallback analysis")

        # Upsert to substitutes table
        print("\nUpserting substitutes to database...")
        upsert_count = 0

        for substitution in analysis.get('substitutions', []):
            original_drug = substitution.get('original_drug')

            # Get drug_id
            drug = drug_inventory_map.get(original_drug)
            drug_id = drug['id'] if drug else None

            for sub in substitution.get('substitutes', []):
                sub_name = sub.get('name')
                sub_drug = drug_inventory_map.get(sub_name)

                substitute_record = {
                    'drug_id': drug_id,
                    'drug_name': original_drug,
                    'substitute_name': sub_name,
                    'substitute_drug_id': sub_drug['id'] if sub_drug else None,
                    'equivalence_notes': sub.get('equivalence_notes', ''),
                    'preference_rank': sub.get('preference_rank', 99)
                }

                # Upsert (unique constraint on drug_name, substitute_name)
                supabase.table('substitutes').upsert(
                    substitute_record,
                    on_conflict='drug_name,substitute_name'
                ).execute()

                upsert_count += 1
                print(f"  ✓ Upserted substitute: {original_drug} → {sub_name} (rank {sub.get('preference_rank')})")

        print(f"✓ Upserted {upsert_count} substitute records")

        # Log to agent_logs
        summary = analysis.get('summary', f'Substitute analysis completed for {len(drugs_needing_substitutes)} drugs.')
        log_agent_output(AGENT_NAME, run_id, analysis, summary)

        print(f"\n✓ Agent 3 completed successfully")
        print(f"  - Analyzed {len(drugs_needing_substitutes)} drugs")
        print(f"  - Found substitutes for {len([s for s in analysis.get('substitutions', []) if not s.get('no_substitute_available')])} drugs")
        print(f"  - Upserted {upsert_count} substitute records")

        return analysis

    except Exception as e:
        print(f"\n✗ Agent 3 failed: {e}")
        error_payload = {
            "error": str(e),
            "summary": f"Agent 3 failed: {e}"
        }
        log_agent_output(AGENT_NAME, run_id, error_payload, f"ERROR: {e}")
        raise

def generate_fallback_analysis(
    drugs_needing_substitutes: List[str],
    substitution_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate fallback substitution analysis when LLM is unavailable.

    Args:
        drugs_needing_substitutes: List of drug names
        substitution_data: Enriched substitution data with inventory

    Returns:
        Analysis dictionary matching expected schema
    """
    substitutions = []

    for item in substitution_data:
        drug_name = item['drug_name']
        hard_coded = item['hard_coded_substitutes']

        if not hard_coded:
            # No substitutes available
            substitutions.append({
                "original_drug": drug_name,
                "substitutes": [],
                "no_substitute_available": True,
                "clinical_notes": f"No known substitutes for {drug_name}. Equipment/supply resolution required."
            })
        else:
            # Use hard-coded mappings
            subs = []
            for mapping in hard_coded:
                subs.append({
                    "name": mapping['name'],
                    "preference_rank": mapping.get('preference_rank', 99),
                    "equivalence_notes": mapping.get('notes', ''),
                    "dosing_conversion": "Consult pharmacist for exact dosing",
                    "contraindications": "Review patient-specific factors",
                    "in_stock": mapping.get('in_stock', False),
                    "stock_quantity": mapping.get('stock_quantity', 0)
                })

            substitutions.append({
                "original_drug": drug_name,
                "substitutes": subs,
                "no_substitute_available": False,
                "clinical_notes": f"Fallback analysis using hard-coded substitutions for {drug_name}."
            })

    return {
        "substitutions": substitutions,
        "summary": f"Fallback analysis. Processed {len(drugs_needing_substitutes)} drugs using hard-coded mappings."
    }

if __name__ == '__main__':
    # Test Agent 3
    import uuid
    test_run_id = str(uuid.uuid4())
    test_drugs = ["Propofol", "Heparin", "Morphine"]
    result = run(test_run_id, test_drugs)
    print("\n" + "="*60)
    print("Test Result:")
    print(json.dumps(result, indent=2, default=str))

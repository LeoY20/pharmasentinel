"""
PharmaSentinel Shared Agent Infrastructure

This module provides common utilities, constants, and functions used by all agents:
- Supabase client initialization
- Dedalus LLM API wrapper
- Database helper functions
- Monitored drugs constants
- Logging utilities
"""

import os
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
import requests

# Load environment variables
load_dotenv()

# ============================================================================
# Environment Configuration
# ============================================================================

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
DEDALUS_API_KEYS = [
    os.getenv('DEDALUS_API_KEY_1'),
    os.getenv('DEDALUS_API_KEY_2'),
    os.getenv('DEDALUS_API_KEY_3')
]
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
HOSPITAL_LOCATION = os.getenv('HOSPITAL_LOCATION', 'Pittsburgh, PA')

# ============================================================================
# Supabase Client
# ============================================================================

def get_supabase_client() -> Client:
    """Initialize and return Supabase client with service role key."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Initialize global client
supabase: Client = get_supabase_client()

# ============================================================================
# Monitored Drugs Constant
# ============================================================================

MONITORED_DRUGS = [
    {
        "rank": 1,
        "name": "Epinephrine",
        "type": "Anaphylaxis/Cardiac",
        "criticality": "Immediate life-saving; minutes matter"
    },
    {
        "rank": 2,
        "name": "Oxygen",
        "type": "Respiratory Support",
        "criticality": "No substitute exists; sustains life in respiratory distress"
    },
    {
        "rank": 3,
        "name": "Levofloxacin",
        "type": "Broad-Spectrum Antibiotic",
        "criticality": "Critical for serious bacterial infections"
    },
    {
        "rank": 4,
        "name": "Propofol",
        "type": "Anesthetic",
        "criticality": "All surgeries halt without anesthetics"
    },
    {
        "rank": 5,
        "name": "Penicillin",
        "type": "Antibiotic",
        "criticality": "Foundational antibiotic for pneumonia and infections"
    },
    {
        "rank": 6,
        "name": "IV Fluids",
        "type": "Hydration/Shock",
        "criticality": "Essential for dehydration, shock, blood loss treatment"
    },
    {
        "rank": 7,
        "name": "Heparin",
        "type": "Anticoagulant",
        "criticality": "Prevents blood clots, strokes, heart attacks"
    },
    {
        "rank": 8,
        "name": "Insulin",
        "type": "Diabetes Management",
        "criticality": "Critical for acute diabetic ketoacidosis"
    },
    {
        "rank": 9,
        "name": "Morphine",
        "type": "Analgesic/Pain",
        "criticality": "Vital for palliative care and severe injury"
    },
    {
        "rank": 10,
        "name": "Vaccines",
        "type": "Immunization",
        "criticality": "Critical long-term but less acute in hospital setting"
    }
]

MONITORED_DRUG_NAMES = [drug["name"] for drug in MONITORED_DRUGS]

# ============================================================================
# Dedalus LLM API Wrapper
# ============================================================================

def call_dedalus(
    user_prompt: str,
    system_prompt: str,
    api_key_index: int = 0,
    temperature: float = 0.2
) -> Dict[str, Any]:
    """
    Call Dedalus LLM API and return parsed JSON response.

    Args:
        user_prompt: The user message/prompt
        system_prompt: The system prompt with instructions and expected JSON schema
        api_key_index: Which API key to use (0, 1, or 2)
        temperature: Temperature for LLM (default 0.2 for deterministic outputs)

    Returns:
        Parsed JSON response from the LLM

    Raises:
        ValueError: If response is not valid JSON
        requests.RequestException: If API call fails
    """
    api_key = DEDALUS_API_KEYS[api_key_index]

    if not api_key or api_key == f'your_dedalus_key_{api_key_index + 1}_here':
        print(f"WARNING: Using placeholder Dedalus API key {api_key_index + 1}")
        # Return mock response for development
        return {"mock": True, "message": "Using placeholder API key"}

    # TODO: Replace with actual Dedalus API endpoint and request format
    # This is a placeholder - adjust based on actual Dedalus API documentation
    endpoint = "https://api.dedalus.ai/v1/chat/completions"  # Placeholder URL

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "dedalus-latest",  # Adjust based on actual model name
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature
    }

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Try to parse as JSON
        return parse_llm_json_response(content)

    except requests.RequestException as e:
        print(f"Dedalus API call failed: {e}")
        raise

def parse_llm_json_response(content: str) -> Dict[str, Any]:
    """
    Parse LLM response as JSON, handling markdown code fences.

    Args:
        content: Raw LLM response string

    Returns:
        Parsed JSON dictionary
    """
    # Try direct parse first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code fences
    json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    match = re.search(json_pattern, content, re.DOTALL)

    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find any JSON object in the content
    json_pattern = r'\{.*\}'
    match = re.search(json_pattern, content, re.DOTALL)

    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from LLM response: {content[:200]}")

# ============================================================================
# Database Helper Functions
# ============================================================================

def log_agent_output(
    agent_name: str,
    run_id: str,
    payload: Dict[str, Any],
    summary: Optional[str] = None
) -> None:
    """
    Write agent output to the agent_logs table.

    Args:
        agent_name: Name of the agent (e.g., "agent_0", "overseer")
        run_id: UUID of the current pipeline run
        payload: Structured JSON output from the agent
        summary: Optional human-readable summary
    """
    try:
        supabase.table('agent_logs').insert({
            'agent_name': agent_name,
            'run_id': run_id,
            'payload': payload,
            'summary': summary or payload.get('summary', '')
        }).execute()
        print(f"✓ {agent_name} logged output for run {run_id}")
    except Exception as e:
        print(f"ERROR logging {agent_name} output: {e}")
        raise

def get_drugs_inventory() -> List[Dict[str, Any]]:
    """
    Fetch all drugs from the drugs table, ordered by criticality rank.

    Returns:
        List of drug records
    """
    try:
        response = supabase.table('drugs').select('*').order('criticality_rank').execute()
        return response.data
    except Exception as e:
        print(f"ERROR fetching drugs inventory: {e}")
        raise

def get_surgery_schedule(days_ahead: int = 30) -> List[Dict[str, Any]]:
    """
    Fetch scheduled surgeries for the next N days.

    Args:
        days_ahead: Number of days to look ahead (default 30)

    Returns:
        List of surgery records
    """
    try:
        end_date = (datetime.now() + timedelta(days=days_ahead)).date().isoformat()

        response = supabase.table('surgery_schedule').select('*').eq(
            'status', 'SCHEDULED'
        ).lte('scheduled_date', end_date).order('scheduled_date').execute()

        return response.data
    except Exception as e:
        print(f"ERROR fetching surgery schedule: {e}")
        raise

def get_unresolved_shortages(days_back: int = 180) -> List[Dict[str, Any]]:
    """
    Fetch unresolved shortages within a time window.

    Args:
        days_back: How many days back to look (default 180 for 6 months)

    Returns:
        List of shortage records
    """
    try:
        start_date = (datetime.now() - timedelta(days=days_back)).date().isoformat()

        response = supabase.table('shortages').select('*').eq(
            'resolved', False
        ).gte('reported_date', start_date).order('reported_date', desc=True).execute()

        return response.data
    except Exception as e:
        print(f"ERROR fetching shortages: {e}")
        raise

def get_suppliers(active_only: bool = True) -> List[Dict[str, Any]]:
    """
    Fetch suppliers from the database.

    Args:
        active_only: If True, only return active suppliers

    Returns:
        List of supplier records
    """
    try:
        query = supabase.table('suppliers').select('*')

        if active_only:
            query = query.eq('active', True)

        response = query.execute()
        return response.data
    except Exception as e:
        print(f"ERROR fetching suppliers: {e}")
        raise

def get_substitutes(drug_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch drug substitutes.

    Args:
        drug_name: If provided, only return substitutes for this drug

    Returns:
        List of substitute records
    """
    try:
        query = supabase.table('substitutes').select('*')

        if drug_name:
            query = query.eq('drug_name', drug_name)

        response = query.order('preference_rank').execute()
        return response.data
    except Exception as e:
        print(f"ERROR fetching substitutes: {e}")
        raise

def get_agent_logs(run_id: str, agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch agent logs for a specific run.

    Args:
        run_id: The pipeline run ID
        agent_name: If provided, only return logs for this agent

    Returns:
        List of agent log records
    """
    try:
        query = supabase.table('agent_logs').select('*').eq('run_id', run_id)

        if agent_name:
            query = query.eq('agent_name', agent_name)

        response = query.order('created_at').execute()
        return response.data
    except Exception as e:
        print(f"ERROR fetching agent logs: {e}")
        raise

# ============================================================================
# Utility Functions
# ============================================================================

def calculate_burn_rate(stock_quantity: float, usage_rate_daily: float) -> Optional[float]:
    """
    Calculate burn rate in days.

    Args:
        stock_quantity: Current stock amount
        usage_rate_daily: Daily usage rate

    Returns:
        Burn rate in days, or None if usage_rate_daily is 0
    """
    if usage_rate_daily == 0:
        return None
    return stock_quantity / usage_rate_daily

def format_drug_summary(drug: Dict[str, Any]) -> str:
    """
    Format a drug record as a human-readable string.

    Args:
        drug: Drug record dictionary

    Returns:
        Formatted string
    """
    burn_rate = drug.get('burn_rate_days')
    burn_str = f"{burn_rate:.1f} days" if burn_rate else "N/A"

    return (
        f"{drug['name']} (Rank {drug['criticality_rank']}): "
        f"{drug['stock_quantity']} {drug['unit']} in stock, "
        f"{drug['usage_rate_daily']}/day usage, "
        f"burn rate: {burn_str}"
    )

def get_criticality_rank(drug_name: str) -> int:
    """
    Get the criticality rank for a drug name.

    Args:
        drug_name: Name of the drug

    Returns:
        Criticality rank (1-10), or 99 if not found
    """
    for drug in MONITORED_DRUGS:
        if drug['name'].lower() == drug_name.lower():
            return drug['rank']
    return 99  # Unknown drug

# ============================================================================
# Validation
# ============================================================================

def validate_environment():
    """Validate that all required environment variables are set."""
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_SERVICE_KEY',
        'DEDALUS_API_KEY_1',
        'DEDALUS_API_KEY_2',
        'DEDALUS_API_KEY_3',
        'NEWS_API_KEY'
    ]

    missing = []
    placeholder = []

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
        elif 'your_' in value.lower() and '_here' in value.lower():
            placeholder.append(var)

    if missing:
        print(f"WARNING: Missing environment variables: {', '.join(missing)}")

    if placeholder:
        print(f"WARNING: Placeholder values detected: {', '.join(placeholder)}")

    return len(missing) == 0

if __name__ == '__main__':
    # Test the shared infrastructure
    print("Testing PharmaSentinel Shared Infrastructure...")
    print(f"Hospital Location: {HOSPITAL_LOCATION}")
    print(f"Monitored Drugs: {len(MONITORED_DRUGS)}")
    print("\nValidating environment...")
    validate_environment()
    print("\nAttempting Supabase connection...")
    try:
        drugs = get_drugs_inventory()
        print(f"✓ Connected to Supabase. Found {len(drugs)} drugs in inventory.")
    except Exception as e:
        print(f"✗ Supabase connection failed: {e}")

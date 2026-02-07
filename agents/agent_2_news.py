"""
Agent 2 — News & Supply Chain Sentiment Analyzer

Responsibilities:
- Queries NewsAPI for drug-related and pharma supply chain articles
- Uses LLM to analyze sentiment and supply chain impact
- Identifies emerging risks (geopolitical, regulatory, natural disasters)
- Inserts high-confidence shortage signals into shortages table
- Logs analysis to agent_logs

API Key: DEDALUS_API_KEY_2 (index 1)
"""

import json
import os
import requests
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .shared import (
    supabase,
    call_dedalus,
    log_agent_output,
    MONITORED_DRUGS,
    MONITORED_DRUG_NAMES,
    get_criticality_rank,
    NEWS_API_KEY
)

AGENT_NAME = "agent_2"
API_KEY_INDEX = 1
NEWS_API_BASE = "https://newsapi.org/v2"

def fetch_news_articles() -> List[Dict[str, Any]]:
    """
    Fetch news articles from NewsAPI related to monitored drugs and supply chain.

    Returns:
        List of article dictionaries
    """
    if not NEWS_API_KEY or 'your_newsapi_key_here' in NEWS_API_KEY:
        print("WARNING: NewsAPI key not configured. Using mock data.")
        return []

    articles = []
    seen_urls = set()

    # Queries for each monitored drug
    for drug_name in MONITORED_DRUG_NAMES:
        query = f'"{drug_name}" AND (shortage OR supply OR manufacturing OR recall)'

        try:
            response = requests.get(
                f"{NEWS_API_BASE}/everything",
                params={
                    'q': query,
                    'apiKey': NEWS_API_KEY,
                    'language': 'en',
                    'sortBy': 'relevancy',
                    'pageSize': 5,
                    'from': (datetime.now() - timedelta(days=7)).isoformat()
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                for article in data.get('articles', []):
                    url = article.get('url')
                    if url and url not in seen_urls:
                        articles.append({
                            'drug_context': drug_name,
                            **article
                        })
                        seen_urls.add(url)
            else:
                print(f"  NewsAPI error for '{drug_name}': {response.status_code}")

        except Exception as e:
            print(f"  Warning: NewsAPI query failed for '{drug_name}': {e}")

    # General pharma supply chain queries
    general_queries = [
        "pharmaceutical supply chain disruption",
        "drug shortage hospital",
        "FDA drug recall"
    ]

    for query in general_queries:
        try:
            response = requests.get(
                f"{NEWS_API_BASE}/everything",
                params={
                    'q': query,
                    'apiKey': NEWS_API_KEY,
                    'language': 'en',
                    'sortBy': 'relevancy',
                    'pageSize': 5,
                    'from': (datetime.now() - timedelta(days=7)).isoformat()
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                for article in data.get('articles', []):
                    url = article.get('url')
                    if url and url not in seen_urls:
                        articles.append({
                            'drug_context': 'General',
                            **article
                        })
                        seen_urls.add(url)

        except Exception as e:
            print(f"  Warning: NewsAPI query failed for '{query}': {e}")

    return articles

def build_system_prompt() -> str:
    """Build the system prompt for Agent 2."""
    return f"""You are an expert pharmaceutical supply chain analyst monitoring news for early warning signals of drug shortages and disruptions.

# CONTEXT

The hospital monitors {len(MONITORED_DRUGS)} critical drugs ranked by criticality (1 = most critical):

{json.dumps(MONITORED_DRUGS, indent=2)}

# YOUR TASK

You will receive news articles from the past 7 days related to:
- Each monitored drug (by name)
- Pharmaceutical supply chain disruptions
- Drug shortages and recalls

You must:
1. Analyze each article for supply chain impact
2. Determine if it relates to any of our 10 monitored drugs
3. Score sentiment: POSITIVE (supply expanding), NEUTRAL, NEGATIVE (early warning), CRITICAL (active disruption)
4. Assess supply chain impact: NONE, LOW, MEDIUM, HIGH, CRITICAL
5. Assign confidence score (0.0 to 1.0)
6. Identify emerging macro-level risks

# SIGNAL DETECTION FRAMEWORK

Look for these specific signals:
- Manufacturing plant shutdowns or FDA warning letters
- Drug recalls (voluntary or mandated)
- Raw material / chemical precursor shortages
- Geopolitical events affecting supply chains (tariffs, trade restrictions, conflicts in manufacturing regions)
- Natural disasters in manufacturing regions
- Transportation / logistics disruptions
- Regulatory changes affecting drug production
- Pharma company mergers/acquisitions
- Labor disputes at manufacturing facilities

Sentiment Assessment:
- CRITICAL: Active disruption (plant shutdown, recall in progress)
- NEGATIVE: Early warning signal (potential future shortage)
- NEUTRAL: Informational (no supply impact)
- POSITIVE: Supply expansion (new manufacturing, shortage resolved)

Supply Chain Impact:
- CRITICAL: Immediate threat to drug availability for rank 1-3 drugs
- HIGH: Significant risk for rank 1-6 drugs or moderate risk for rank 1-3
- MEDIUM: Future risk or affects rank 7-10 drugs
- LOW: Minimal or indirect impact
- NONE: No supply chain relevance

Confidence Score:
- 0.9-1.0: Direct statement about shortage or disruption from authoritative source
- 0.7-0.9: Strong evidence from credible source
- 0.5-0.7: Moderate evidence, some uncertainty
- 0.3-0.5: Weak signal, high uncertainty
- 0.0-0.3: Speculative or unreliable

# OUTPUT FORMAT

You MUST respond with ONLY valid JSON matching this exact schema:

{{
    "articles_analyzed": 0,
    "risk_signals": [
        {{
            "drug_name": "string",
            "headline": "string",
            "source": "string",
            "url": "string",
            "sentiment": "POSITIVE | NEUTRAL | NEGATIVE | CRITICAL",
            "supply_chain_impact": "NONE | LOW | MEDIUM | HIGH | CRITICAL",
            "confidence": 0.0,
            "reasoning": "string"
        }}
    ],
    "emerging_risks": [
        {{
            "description": "string",
            "affected_drugs": ["list"],
            "risk_level": "LOW | MEDIUM | HIGH",
            "time_horizon": "string"
        }}
    ],
    "summary": "string"
}}

Respond with ONLY the JSON. No markdown, no explanations."""

def run(run_id: str) -> Dict[str, Any]:
    """
    Execute Agent 2 news analysis.

    Args:
        run_id: UUID of the current pipeline run

    Returns:
        Analysis results dictionary
    """
    print(f"\n{'='*60}")
    print(f"Agent 2: News & Supply Chain Analyzer")
    print(f"Run ID: {run_id}")
    print(f"{'='*60}\n")

    try:
        # Fetch news articles
        print("Fetching news articles from NewsAPI...")
        articles = fetch_news_articles()
        print(f"✓ Retrieved {len(articles)} articles (deduplicated)")

        if len(articles) == 0:
            print("  No articles retrieved. Skipping LLM analysis.")
            analysis = {
                "articles_analyzed": 0,
                "risk_signals": [],
                "emerging_risks": [],
                "summary": "No news articles found in the past 7 days."
            }
        else:
            # Build user prompt with article summaries
            article_summaries = []
            for i, article in enumerate(articles[:30], 1):  # Limit to 30 articles
                article_summaries.append({
                    'index': i,
                    'drug_context': article.get('drug_context'),
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'source': article.get('source', {}).get('name', 'Unknown'),
                    'url': article.get('url', ''),
                    'publishedAt': article.get('publishedAt', '')
                })

            user_prompt = f"""# NEWS ARTICLES (Past 7 Days)

Total articles: {len(article_summaries)}

{json.dumps(article_summaries, indent=2)}

Please analyze these articles for supply chain risks affecting our monitored drugs."""

            # Call Dedalus LLM
            print("\nCalling Dedalus LLM for news analysis...")
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
                analysis = generate_fallback_analysis(articles)
                print("✓ Using fallback analysis")

        # Insert high-confidence risk signals into shortages table
        print("\nProcessing risk signals...")
        risk_signals = analysis.get('risk_signals', [])
        inserted_count = 0

        for signal in risk_signals:
            impact = signal.get('supply_chain_impact', 'NONE')
            confidence = signal.get('confidence', 0.0)
            drug_name = signal.get('drug_name')

            # Insert if impact >= HIGH and confidence >= 0.7
            if impact in ['HIGH', 'CRITICAL'] and confidence >= 0.7 and drug_name:
                shortage_record = {
                    'drug_name': drug_name,
                    'type': 'NEWS_INFERRED',
                    'source': signal.get('source', 'News Media'),
                    'source_url': signal.get('url', ''),
                    'impact_severity': impact,
                    'description': signal.get('reasoning', signal.get('headline', '')),
                    'reported_date': datetime.now().date().isoformat(),
                    'resolved': False
                }

                supabase.table('shortages').insert(shortage_record).execute()
                inserted_count += 1
                print(f"  ✓ Inserted news-inferred shortage for {drug_name} (confidence: {confidence})")

        print(f"✓ Inserted {inserted_count} shortage records from news signals")

        # Log to agent_logs
        summary = analysis.get('summary', f'News analysis completed. {len(risk_signals)} signals found.')
        log_agent_output(AGENT_NAME, run_id, analysis, summary)

        print(f"\n✓ Agent 2 completed successfully")
        print(f"  - Analyzed {analysis.get('articles_analyzed', len(articles))} articles")
        print(f"  - Found {len(risk_signals)} risk signals")
        print(f"  - Identified {len(analysis.get('emerging_risks', []))} emerging risks")
        print(f"  - Inserted {inserted_count} high-confidence shortage alerts")

        return analysis

    except Exception as e:
        print(f"\n✗ Agent 2 failed: {e}")
        error_payload = {
            "error": str(e),
            "summary": f"Agent 2 failed: {e}"
        }
        log_agent_output(AGENT_NAME, run_id, error_payload, f"ERROR: {e}")
        raise

def generate_fallback_analysis(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate fallback analysis when LLM is unavailable.

    Args:
        articles: List of news articles

    Returns:
        Analysis dictionary matching expected schema
    """
    risk_signals = []

    # Simple keyword-based analysis
    negative_keywords = ['shortage', 'recall', 'disruption', 'shutdown', 'suspend']
    critical_keywords = ['critical', 'emergency', 'halt', 'stop production']

    for article in articles[:20]:
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        text = f"{title} {description}"
        drug_context = article.get('drug_context')

        # Check for negative keywords
        has_negative = any(kw in text for kw in negative_keywords)
        has_critical = any(kw in text for kw in critical_keywords)

        if has_negative or has_critical:
            drug_name = drug_context if drug_context in MONITORED_DRUG_NAMES else None

            if has_critical:
                sentiment = "CRITICAL"
                impact = "HIGH"
                confidence = 0.6
            elif has_negative:
                sentiment = "NEGATIVE"
                impact = "MEDIUM"
                confidence = 0.5
            else:
                continue

            risk_signals.append({
                "drug_name": drug_name or "Unknown",
                "headline": article.get('title', ''),
                "source": article.get('source', {}).get('name', 'Unknown'),
                "url": article.get('url', ''),
                "sentiment": sentiment,
                "supply_chain_impact": impact,
                "confidence": confidence,
                "reasoning": f"Fallback: Keywords detected in article: {', '.join([kw for kw in negative_keywords + critical_keywords if kw in text])}"
            })

    return {
        "articles_analyzed": len(articles),
        "risk_signals": risk_signals,
        "emerging_risks": [],
        "summary": f"Fallback analysis. Analyzed {len(articles)} articles using keyword detection. Found {len(risk_signals)} potential risk signals."
    }

if __name__ == '__main__':
    # Test Agent 2
    import uuid
    test_run_id = str(uuid.uuid4())
    result = run(test_run_id)
    print("\n" + "="*60)
    print("Test Result:")
    print(json.dumps(result, indent=2, default=str))

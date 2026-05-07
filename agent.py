"""
3LC Conference Finder Agent
Uses Claude Opus 4.7 + Tavily to research US conferences for 3LC.ai
"""

import json
import os
from typing import Generator
import anthropic
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()


def get_secret(key: str) -> str:
    """Read from Streamlit secrets (cloud) or environment variables (local)."""
    try:
        import streamlit as st
        return st.secrets.get(key, os.getenv(key, ""))
    except Exception:
        return os.getenv(key, "")

# Tool definition for Tavily web search
TOOLS = [
    {
        "name": "web_search",
        "description": (
            "Search the web for information about conferences, trade shows, industry events, "
            "and company attendee lists. Use this to find upcoming US conferences and "
            "research which companies will be attending them."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Be specific and include year (2025 or 2026)."
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (1-8). Default 5.",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
]

SYSTEM_PROMPT = """You are a conference research specialist for 3LC.ai, a visual data AI compression company.

Your mission: Find US conferences in 2025-2026 where 3LC.ai can network and discover new enterprise clients.

3LC.ai's ideal client profile:
- Companies with 500+ total employees
- Companies that work with visual data, AI/ML, computer vision, or large datasets
- Target industries: robotics, agriculture, automotive, retail, manufacturing, logistics, aerospace, healthcare imaging, media & entertainment

Search strategy:
1. Search for major conferences in each target industry (e.g., "robotics conference USA 2025", "agricultural technology conference 2025")
2. For each promising conference, search for the attendee/exhibitor list to identify qualifying companies
3. Focus on enterprise-level events where Fortune 1000 companies and large enterprises attend

For each conference, gather:
- Conference name
- Location (city, state)
- Date or date range
- Primary industry focus
- Companies of interest attending (500+ employee companies in visual data/AI/ML space). If unknown, write "Unknown"
- Estimated conference size (number of companies/organizations attending)

After thorough research, output ONLY a JSON array with this exact structure (no other text):
[
  {
    "conference_name": "string",
    "location": "string",
    "date": "string",
    "industry": "string",
    "companies_of_interest": "string",
    "conference_size": "string"
  }
]

Aim to find 8-15 high-quality conferences. Quality over quantity — focus on large conferences where enterprise companies with visual data needs will be present."""


def run_web_search(query: str, max_results: int = 5) -> str:
    """Execute a Tavily web search and return results as JSON string."""
    api_key = get_secret("TAVILY_API_KEY")
    if not api_key:
        return json.dumps({"error": "TAVILY_API_KEY not set"})

    try:
        tavily = TavilyClient(api_key=api_key)
        response = tavily.search(
            query=query,
            max_results=max_results,
            search_depth="advanced"
        )
        # Return cleaned results
        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", "")[:800]  # Truncate for context efficiency
            })
        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def build_user_prompt(industries: list[str], date_range: str, min_size: int, regions: list[str]) -> str:
    """Build a targeted user prompt based on UI filters."""
    industries_str = ", ".join(industries) if industries else "robotics, agriculture, automotive, retail, AI/ML"
    regions_str = ", ".join(regions) if regions else "United States (all regions)"

    return f"""Find US conferences for 3LC.ai with these filters:

Target Industries: {industries_str}
Date Range: {date_range}
Minimum Conference Size: {min_size}+ companies attending
Geographic Focus: {regions_str}

Search for conferences in each specified industry. For each conference you find, search for the exhibitor/attendee list to identify companies with 500+ employees that work with visual data or AI/ML.

Remember to output ONLY the JSON array at the end."""


def find_conferences(
    industries: list[str],
    date_range: str,
    min_size: int,
    regions: list[str],
    status_callback=None
) -> list[dict]:
    """
    Run the Claude agent to find conferences matching 3LC's criteria.

    Args:
        industries: List of target industries
        date_range: Date range string (e.g., "2025-2026")
        min_size: Minimum conference size (number of companies)
        regions: List of US regions to focus on
        status_callback: Optional function(message: str) called for progress updates

    Returns:
        List of conference dicts with keys: conference_name, location, date,
        industry, companies_of_interest, conference_size
    """
    client = anthropic.Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))

    messages = [
        {
            "role": "user",
            "content": build_user_prompt(industries, date_range, min_size, regions)
        }
    ]

    if status_callback:
        status_callback("Starting conference research with Claude Opus 4.7...")

    # Agentic tool-use loop
    while True:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=8000,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        # Check stop reason
        if response.stop_reason == "end_turn":
            # Extract the JSON from the final text response
            for block in response.content:
                if block.type == "text":
                    return _parse_json_response(block.text)
            return []

        if response.stop_reason != "tool_use":
            break

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input

                if status_callback:
                    query_preview = tool_input.get("query", "")[:60]
                    status_callback(f"Searching: {query_preview}...")

                if tool_name == "web_search":
                    result = run_web_search(
                        query=tool_input["query"],
                        max_results=tool_input.get("max_results", 5)
                    )
                else:
                    result = json.dumps({"error": f"Unknown tool: {tool_name}"})

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })

        # Append assistant response and tool results to messages
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return []


def find_conferences_streaming(
    industries: list[str],
    date_range: str,
    min_size: int,
    regions: list[str]
) -> Generator[str, None, list[dict]]:
    """
    Generator version that yields status messages during research.
    Yields strings for status updates, returns final list of conferences.
    """
    results = []

    def collect_status(msg: str):
        pass  # Will be replaced by caller

    # Use the regular function with a callback
    # For Streamlit, we'll use the non-streaming version with st.status
    return find_conferences(industries, date_range, min_size, regions)


def _parse_json_response(text: str) -> list[dict]:
    """Extract and parse JSON array from Claude's response."""
    text = text.strip()

    # Try to find JSON array in the response
    start = text.find("[")
    end = text.rfind("]") + 1

    if start == -1 or end == 0:
        return []

    json_str = text[start:end]

    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            # Normalize keys
            normalized = []
            for item in data:
                if isinstance(item, dict):
                    normalized.append({
                        "conference_name": item.get("conference_name", "Unknown"),
                        "location": item.get("location", "Unknown"),
                        "date": item.get("date", "Unknown"),
                        "industry": item.get("industry", "Unknown"),
                        "companies_of_interest": item.get("companies_of_interest", "Unknown"),
                        "conference_size": item.get("conference_size", "Unknown")
                    })
            return normalized
    except json.JSONDecodeError:
        pass

    return []

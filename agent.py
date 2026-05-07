"""
3LC Conference Finder Agent
Uses Google Gemini (free) + Tavily to research US conferences for 3LC.ai
"""

import json
import os
from google import genai
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


SYSTEM_PROMPT = """You are a conference research specialist for 3LC.ai, a visual data AI compression company.

3LC.ai's ideal client: companies with 500+ employees working with visual data, AI/ML, or computer vision.
Target industries: robotics, agriculture, automotive, retail, manufacturing, logistics, aerospace, media.

From the search results provided, extract US conferences and output ONLY a JSON array:
[
  {
    "conference_name": "string",
    "location": "City, State",
    "date": "string",
    "industry": "string",
    "companies_of_interest": "company1, company2 (500+ employee companies attending, or 'Unknown')",
    "conference_size": "e.g. '500+ companies' or 'Unknown'"
  }
]
No other text. Only the JSON array."""


def search_web(query: str, max_results: int = 4) -> str:
    """Search the web using Tavily."""
    api_key = get_secret("TAVILY_API_KEY")
    if not api_key:
        return json.dumps({"error": "TAVILY_API_KEY not set"})
    try:
        tavily = TavilyClient(api_key=api_key)
        response = tavily.search(query=query, max_results=max_results)
        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "content": r.get("content", "")[:500]
            })
        return json.dumps(results)
    except Exception as e:
        return json.dumps({"error": str(e)})


def find_conferences(
    industries: list,
    date_range: str,
    min_size: int,
    regions: list,
    status_callback=None
) -> list:
    """Use Gemini + Tavily to find conferences matching 3LC's criteria."""
    api_key = get_secret("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set. Get a free key at aistudio.google.com")

    client = genai.Client(api_key=api_key)
    industries_str = ", ".join(industries[:4])  # Limit to 4 industries

    if status_callback:
        status_callback("Searching for conferences...")

    # Run targeted searches
    all_results = []
    queries = [
        f"{industries_str} conference expo USA {date_range}",
        f"enterprise {industries_str} trade show United States 2025 2026 exhibitors",
    ]

    for query in queries:
        if status_callback:
            status_callback(f"Searching: {query[:55]}...")
        results = search_web(query, max_results=4)
        all_results.append(f"Search: {query}\n{results}")

    if status_callback:
        status_callback("Analyzing with Gemini AI...")

    combined = "\n\n".join(all_results)[:6000]  # Keep under token limit

    prompt = f"""Find US conferences for a company targeting {industries_str} industries in {date_range}.
Minimum conference size: {min_size}+ companies.
Regions: {', '.join(regions) if regions else 'All US'}.

Search results:
{combined}

Output ONLY the JSON array of conferences found."""

    response = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
        )
    )

    return _parse_json_response(response.text)


def _parse_json_response(text: str) -> list:
    """Extract and parse JSON array from Gemini's response."""
    if not text:
        return []

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    text = text.strip()
    start = text.find("[")
    end = text.rfind("]") + 1

    if start == -1 or end == 0:
        return []

    try:
        data = json.loads(text[start:end])
        if isinstance(data, list):
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

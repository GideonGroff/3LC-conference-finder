"""
3LC Conference Finder — Streamlit App
Helps 3LC.ai discover US conferences to expand their network and find enterprise clients.
"""

import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from agent import find_conferences, get_secret
from excel_export import generate_excel
from demo_data import DEMO_CONFERENCES

load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="3LC Conference Finder",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Styles ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title { font-size: 2rem; font-weight: 700; color: #0066CC; }
    .subtitle { color: #555; font-size: 1rem; margin-bottom: 1.5rem; }
    .result-count { font-size: 1.1rem; font-weight: 600; color: #0066CC; }
    .stDataFrame { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ── Search filters ─────────────────────────────────────────────────
with st.sidebar:
    st.image("https://3lc.ai/wp-content/uploads/2023/08/3LC-logo.svg",
             width=120, use_container_width=False)

    st.markdown("## 🔍 Search Filters")

    # Industries
    st.markdown("### Target Industries")
    all_industries = [
        "Robotics",
        "Agriculture / AgTech",
        "Automotive",
        "Retail / E-commerce",
        "AI / Machine Learning",
        "Computer Vision",
        "Manufacturing",
        "Logistics / Supply Chain",
        "Aerospace / Defense",
        "Healthcare Imaging",
        "Media & Entertainment"
    ]
    selected_industries = []
    for industry in all_industries:
        if st.checkbox(industry, value=industry in ["Robotics", "Automotive", "AI / Machine Learning", "Computer Vision"]):
            selected_industries.append(industry)

    st.markdown("---")

    # Date range
    st.markdown("### Date Range")
    date_range = st.selectbox(
        "Conference dates",
        options=[
            "2025 (remainder of year)",
            "2026",
            "2025-2026",
            "Q3-Q4 2025",
            "Q1-Q2 2026"
        ],
        index=2
    )

    st.markdown("---")

    # Min conference size
    st.markdown("### Minimum Conference Size")
    min_size = st.slider(
        "Minimum number of companies attending",
        min_value=50,
        max_value=1000,
        value=100,
        step=50
    )

    st.markdown("---")

    # Regions
    st.markdown("### US Regions")
    all_regions = ["Northeast", "Southeast", "Midwest", "Southwest", "West Coast", "All US"]
    selected_regions = []
    for region in all_regions:
        default = region == "All US"
        if st.checkbox(region, value=default, key=f"region_{region}"):
            selected_regions.append(region)

    if not selected_regions:
        selected_regions = ["All US"]

    st.markdown("---")

    st.markdown("---")
    st.markdown("### Mode")
    demo_mode = st.toggle("Demo Mode (no API key needed)", value=True)
    if demo_mode:
        st.info("Using pre-loaded sample data.")
    else:
        st.caption("Requires Gemini + Tavily API keys in .env")

    # Search button
    search_clicked = st.button(
        "🚀 Find Conferences",
        type="primary",
        use_container_width=True,
        disabled=not selected_industries
    )

    if not selected_industries:
        st.warning("Select at least one industry.")


# ── Main content ──────────────────────────────────────────────────────────────
st.markdown('<p class="main-title">🎯 3LC.ai Conference Finder</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Discover US conferences to grow 3LC\'s enterprise network. '
    'Targets companies with 500+ employees in visual data & AI/ML industries.</p>',
    unsafe_allow_html=True
)

# ── API key check ─────────────────────────────────────────────────────────────
gemini_key = get_secret("GEMINI_API_KEY")
tavily_key = get_secret("TAVILY_API_KEY")

if not gemini_key or not tavily_key:
    st.error(
        "⚠️ Missing API keys. Create a `.env` file with:\n"
        "```\nGEMINI_API_KEY=your_key\nTAVILY_API_KEY=your_key\n```\n\n"
        "Both are **free**:\n"
        "- Gemini: https://aistudio.google.com → Get API key\n"
        "- Tavily: https://app.tavily.com → Dashboard"
    )
    st.stop()

# ── Results state ─────────────────────────────────────────────────────────────
if "conferences" not in st.session_state:
    st.session_state.conferences = []
if "search_filters" not in st.session_state:
    st.session_state.search_filters = {}
if "searching" not in st.session_state:
    st.session_state.searching = False

# ── Run search ────────────────────────────────────────────────────────────────
if search_clicked:
    st.session_state.searching = True
    st.session_state.conferences = []

    filters = {
        "industries": selected_industries,
        "date_range": date_range,
        "min_size": min_size,
        "regions": selected_regions
    }
    st.session_state.search_filters = filters

    if demo_mode:
        # Filter demo data by selected industries
        filtered = [
            c for c in DEMO_CONFERENCES
            if any(ind.lower().split("/")[0].strip() in c["industry"].lower()
                   for ind in selected_industries)
        ] or DEMO_CONFERENCES
        st.session_state.conferences = filtered
        st.success(f"✅ Found {len(filtered)} conferences! (Demo Mode)")
    else:
        with st.status("🔍 Researching conferences...", expanded=True) as status:
            st.write("Starting AI-powered conference research...")

            def update_status(msg: str):
                st.write(msg)

            try:
                conferences = find_conferences(
                    industries=selected_industries,
                    date_range=date_range,
                    min_size=min_size,
                    regions=selected_regions,
                    status_callback=update_status
                )
                st.session_state.conferences = conferences
                status.update(
                    label=f"✅ Found {len(conferences)} conferences!",
                    state="complete"
                )
            except Exception as e:
                status.update(label=f"❌ Error: {str(e)}", state="error")
                st.error(f"Research failed: {str(e)}")

    st.session_state.searching = False

# ── Display results ───────────────────────────────────────────────────────────
conferences = st.session_state.conferences

if conferences:
    filters = st.session_state.search_filters

    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        st.metric("Conferences Found", len(conferences))
    with col2:
        known_coi = sum(
            1 for c in conferences
            if c.get("companies_of_interest", "Unknown").strip().lower() != "unknown"
        )
        st.metric("With Known Attendees", known_coi)
    with col3:
        industries_found = set(c.get("industry", "") for c in conferences)
        st.metric("Industries Covered", len(industries_found))

    st.markdown("---")

    # ── Download button ────────────────────────────────────────────────────────
    excel_bytes = generate_excel(conferences, filters)

    st.download_button(
        label="📥 Download Excel Report",
        data=excel_bytes,
        file_name="3LC_Conference_Research.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )

    st.markdown("---")

    # ── Filter / search the table ──────────────────────────────────────────────
    search_term = st.text_input("🔎 Filter results", placeholder="Search by name, industry, location...")

    # ── Results table ──────────────────────────────────────────────────────────
    df = pd.DataFrame(conferences)
    df.columns = ["Conference Name", "Location", "Date", "Industry", "Companies of Interest", "Conference Size"]

    if search_term:
        mask = df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
        df = df[mask]

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Conference Name": st.column_config.TextColumn("Conference Name", width="large"),
            "Location": st.column_config.TextColumn("Location", width="medium"),
            "Date": st.column_config.TextColumn("Date", width="medium"),
            "Industry": st.column_config.TextColumn("Industry", width="medium"),
            "Companies of Interest": st.column_config.TextColumn("Companies of Interest (500+ employees)", width="large"),
            "Conference Size": st.column_config.TextColumn("Size", width="small"),
        }
    )

    st.caption(f"Showing {len(df)} of {len(conferences)} conferences")

    # ── Expand individual conference details ───────────────────────────────────
    st.markdown("---")
    st.markdown("### 📋 Conference Details")

    for i, conf in enumerate(conferences):
        with st.expander(f"**{conf['conference_name']}** — {conf['location']} | {conf['date']}"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Industry:** {conf['industry']}")
                st.markdown(f"**Date:** {conf['date']}")
                st.markdown(f"**Location:** {conf['location']}")
                st.markdown(f"**Size:** {conf['conference_size']}")
            with col_b:
                coi = conf.get("companies_of_interest", "Unknown")
                st.markdown("**Companies of Interest (500+ employees):**")
                if coi.lower() == "unknown":
                    st.info("Attendee list not publicly available")
                else:
                    companies = [c.strip() for c in coi.split(",") if c.strip()]
                    for company in companies:
                        st.markdown(f"• {company}")

else:
    # ── Empty state ────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align: center; padding: 3rem; color: #888;">
        <h3>👈 Configure your search in the sidebar</h3>
        <p>Select target industries, date range, and minimum conference size,<br>
        then click <strong>Find Conferences</strong> to start research.</p>
        <br>
        <p><strong>What this tool does:</strong></p>
        <p>Uses AI + real-time web search to find US conferences where 3LC.ai<br>
        can meet potential enterprise clients (500+ employees) working with<br>
        visual data, AI/ML, robotics, agriculture, automotive, and retail tech.</p>
    </div>
    """, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Built for 3LC.ai · Powered by Claude Opus 4.7 + Tavily Search · CSUMB Capstone 2025")

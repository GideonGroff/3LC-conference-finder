# 3LC Conference Finder

An AI-powered tool that helps [3LC.ai](https://3lc.ai) discover US conferences to grow their enterprise network and find new clients.

Built as a CSUMB Capstone Project, 2025–2026.

---

## What It Does

Searches for US conferences where 3LC.ai can meet potential enterprise clients — companies with **500+ employees** working with visual data, AI/ML, robotics, agriculture, automotive, retail, and more.

For each conference found, the tool returns:
| Column | Description |
|---|---|
| Conference Name | Full name of the event |
| Location | City, State |
| Date | Date or date range |
| Industry | Primary industry focus |
| COI | Companies of Interest attending (500+ employees) |
| Conference Size | Estimated number of companies attending |

Results can be downloaded as a formatted Excel report.

---

## Tech Stack

- **Claude Opus 4.7** (Anthropic) — AI agent that researches and synthesizes conference data
- **Tavily** — Real-time web search API
- **Streamlit** — Web UI
- **openpyxl** — Excel export

---

## Setup (Local)

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/3lc-conference-finder.git
cd 3lc-conference-finder
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Add API keys
Create a `.env` file:
```
ANTHROPIC_API_KEY=your_anthropic_api_key
TAVILY_API_KEY=your_tavily_api_key
```

Get keys from:
- Anthropic: https://console.anthropic.com → API Keys
- Tavily: https://app.tavily.com → Dashboard

### 4. Run the app
```bash
streamlit run app.py
```

---

## Deploy to Streamlit Cloud (Recommended for 3LC)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub account
3. Select this repo and set `app.py` as the main file
4. Go to **App Settings → Secrets** and add:
```toml
ANTHROPIC_API_KEY = "your_anthropic_api_key"
TAVILY_API_KEY = "your_tavily_api_key"
```
5. Deploy — 3LC staff access the app via a public URL, no local setup required

---

## API Costs (Approximate)

| Service | Cost |
|---|---|
| Anthropic (Claude Opus 4.7) | ~$0.10–0.50 per search run |
| Tavily | Free tier: 1,000 searches/month |

---

## Project Structure

```
3lc-conference-finder/
├── app.py              # Streamlit UI
├── agent.py            # Claude agent + Tavily search logic
├── excel_export.py     # Excel report generation
├── requirements.txt
├── .env.example        # Template for API keys
└── .streamlit/
    └── secrets.toml.example
```

---

Built by [Your Name] · CSUMB IS Capstone · 2025–2026

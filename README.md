# 🛒 RetailMind — Autonomous Promotion Planner
### ET AI Hackathon · Agentic Edition · Problem 3

## Live Demo
🔗  https://retail-promo-agent-nhutbwbbuf6a8slk5uu9zh.streamlit.app/

## Demo Video
🎥 [https://your-youtube-or-loom-link-here](https://www.loom.com/share/879629d01ee949009ae65fd8ed472fa1)

## What it does
Three AI agents autonomously plan retail promotions end to end:
- **Selector Agent** identifies eligible products based on inventory surplus, holiday proximity and margin headroom
- **Optimizer Agent** calculates the best discount within hard margin constraints
- **Simulator Agent** forecasts revenue and risk before a single promotion goes live

## Self-declared 9-blocker position: D2–F2

### D2 Justification
- All inputs are structured CSV files
- Deterministic fallback paths if LLM output fails
- Mathematical margin floor enforced before LLM is called
- JSON schema validation on all LLM outputs

### F2 — 6 Features Covered
- ✅ Select which products to promote
- ✅ Determine promotion mechanism
- ✅ Optimise discount amount
- ✅ Consider inventory constraints
- ✅ Competitor awareness
- ✅ Simulate promotion before launching
- 🔲 Cannibalization modelling (not covered)
- 🔲 Geographic customization (not covered)

## Architecture
User selects date → Orchestrator (LangGraph) → Selector Agent → Optimizer Agent → Simulator Agent → Promotion Plan

## Tech Stack
Python · LangGraph · Groq (Qwen 3.8-27B) · Streamlit · Plotly · pandas

## Quick Start
pip install -r requirements.txt
Add GROQ_API_KEY to environment
streamlit run ui/app.py

## Project Structure
agents/ — selector, optimizer, simulator, orchestrator
data/ — CSV files (products, inventory, competitors, holidays, segments)
ui/ — Streamlit app
requirements.txt

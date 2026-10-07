import pandas as pd, json
from datetime import datetime
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
import os

def get_llm():
    return ChatGroq(
        api_key=os.environ["GROQ_API_KEY"],
        model="qwen/qwen3.8-27b",    # ← updated model
        temperature=0.1,
        max_tokens=4096
    )

def run_selector_agent(products_df, inventory_df, holidays_df,
                        segments_df, competitor_df, promo_date=None):
    llm = get_llm()
    promo_date = promo_date or datetime.today().strftime("%Y-%m-%d")
    today = datetime.strptime(promo_date, "%Y-%m-%d")

    merged = products_df.merge(inventory_df, on="product_id")

    # Find upcoming holiday categories (within 21 days)
    upcoming_cats = set()
    for _, row in holidays_df.iterrows():
        hdate = datetime.strptime(row["date"], "%Y-%m-%d")
        if 0 <= (hdate - today).days <= 21:
            for c in row["relevant_categories"].split("|"):
                upcoming_cats.add(c.strip())

    headroom = merged["margin_pct"] - merged["min_margin_pct"]
    candidates = merged[
        (merged["overstocked"] | merged["category"].isin(upcoming_cats)) &
        (headroom > 5)].copy()
    candidates["margin_headroom"] = headroom

    if candidates.empty:
        return {"selected_products": [], "reasoning": {}}

    cand_summary = candidates[[
        "product_id","product_name","category","mrp",
        "margin_pct","margin_headroom","stock_units",
        "days_of_supply","overstocked"]].head(20).to_dict("records")
    segs = segments_df[["name","preferred_categories","price_sensitivity"]].to_dict("records")

    prompt = f"""You are a retail category manager. Pick the BEST 5-8 products for a promotion.
PROMOTION DATE: {promo_date}
UPCOMING HOLIDAY CATEGORIES: {list(upcoming_cats) or 'None in next 21 days'}
CANDIDATES: {json.dumps(cand_summary, indent=2)}
SEGMENTS: {json.dumps(segs, indent=2)}
Priority: margin_headroom > 10%, then overstocked, then holiday-relevant.

IMPORTANT: Return ONLY a valid JSON object. No thinking, no explanation, no markdown.
Exactly this format:
{{"selected_product_ids": [1001, 1005], "reasoning": {{"1001": "reason...", "1005": "reason..."}}}}"""

    resp = llm.invoke([HumanMessage(content=prompt)])
    try:
        text = resp.content.strip()
        # Strip any markdown code fences if present
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        # Strip any <think>...</think> tags (Qwen sometimes adds these)
        if "<think>" in text:
            text = text.split("</think>")[-1].strip()
        r = json.loads(text)
        return {"selected_products": r.get("selected_product_ids", []),
                "reasoning": r.get("reasoning", {})}
    except:
        fallback = candidates.nlargest(5, "margin_headroom")["product_id"].tolist()
        return {"selected_products": fallback, "reasoning": {}}

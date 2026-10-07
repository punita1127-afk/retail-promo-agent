import pandas as pd, json, os, time
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

def get_llm():
    return ChatGroq(
        api_key=os.environ["GROQ_API_KEY"],
        model="qwen/qwen3.8-27b",
        temperature=0.1,
        max_tokens=500        # ← kept low for rate limit
    )

def simulate_one(plan, products_df, inventory_df, segments_df):
    pid = plan["product_id"]
    prod = products_df[products_df["product_id"] == pid].iloc[0]
    inv  = inventory_df[inventory_df["product_id"] == pid].iloc[0]
    seg  = segments_df[segments_df["segment_id"] == plan.get("target_segment_id", "SEG01")].iloc[0]

    disc       = plan["discount_pct"]
    disc_price = prod["mrp"] * (1 - disc / 100)
    new_margin = (disc_price - prod["cost_price"]) / disc_price * 100
    baseline_daily = inv["stock_units"] / max(inv["days_of_supply"], 1)
    lift       = disc * prod["price_elasticity"] * float(seg["discount_response_multiplier"]) / 10
    promo_daily = baseline_daily * (1 + lift / 100)
    dur        = plan.get("duration_days", 7)

    bl_rev = baseline_daily * dur * prod["mrp"]
    pr_rev = promo_daily   * dur * disc_price
    bl_mgn = bl_rev * (prod["margin_pct"] / 100)
    pr_mgn = promo_daily * dur * (disc_price - prod["cost_price"])

    risks = []
    if new_margin < prod["min_margin_pct"]:
        risks.append(f"⚠️ Margin {new_margin:.1f}% falls below floor of {prod['min_margin_pct']}%")
    if promo_daily * dur > inv["stock_units"]:
        risks.append("⚠️ Demand may exceed available stock before promo ends")
    if not risks:
        risks.append("✅ No major risks identified")

    return {
        "product_id":        pid,
        "product_name":      plan["product_name"],
        "discount_pct":      disc,
        "discounted_price":  round(disc_price, 2),
        "new_margin_pct":    round(new_margin, 1),
        "volume_lift_pct":   round(lift, 1),
        "baseline_units":    round(baseline_daily * dur, 1),
        "promo_units":       round(promo_daily * dur, 1),
        "baseline_revenue":  round(bl_rev, 2),
        "promo_revenue":     round(pr_rev, 2),
        "revenue_delta":     round(pr_rev - bl_rev, 2),
        "margin_delta":      round(pr_mgn - bl_mgn, 2),
        "risk_flags":        risks,
        "recommendation":    "APPROVE" if not any("⚠️" in r for r in risks) else "REVIEW"
    }

def run_simulator_agent(plans, products_df, inventory_df, segments_df):
    # Pure math — no LLM calls per product, so no rate limit issue here
    sims = [simulate_one(p, products_df, inventory_df, segments_df) for p in plans]

    # One single LLM call for the executive summary
    llm = get_llm()
    summary_data = [{
        "product": s["product_name"],
        "discount": s["discount_pct"],
        "revenue_delta": s["revenue_delta"],
        "recommendation": s["recommendation"]
    } for s in sims]

    prompt = f"""You are a retail analytics lead. Write a 2-sentence summary for a category director.
Cover: total revenue lift, key risks, top recommendation.
Data: {json.dumps(summary_data)}
Return plain text only. No bullet points, no markdown, no thinking tags."""

    resp = llm.invoke([HumanMessage(content=prompt)])
    text = resp.content.strip()
    if "<think>" in text:
        text = text.split("</think>")[-1].strip()

    return {"simulations": sims, "executive_summary": text}

import pandas as pd, json, os, time
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

def get_llm():
    return ChatGroq(
        api_key=os.environ["GROQ_API_KEY"],
        model="qwen/qwen3.8-27b",
        temperature=0.1,
        max_tokens=500        # ← reduced from 2048 to stay under limit
    )

def max_safe_discount(mrp, cost, min_margin_pct):
    min_price = cost * (1 + min_margin_pct / 100)
    return round(max((mrp - min_price) / mrp * 100, 0), 1)

def run_optimizer_agent(selected_ids, products_df, inventory_df,
                         segments_df, competitor_df, selector_reasoning):
    if not selected_ids:
        return []
    llm = get_llm()
    merged = (products_df[products_df["product_id"].isin(selected_ids)]
              .merge(inventory_df, on="product_id"))
    plans = []
    for i, (_, row) in enumerate(merged.iterrows()):
        pid = row["product_id"]
        max_d = max_safe_discount(row["mrp"], row["cost_price"], row["min_margin_pct"])
        comp = competitor_df[competitor_df["product_id"] == pid]
        min_comp = comp["competitor_price"].min() if not comp.empty else row["mrp"]

        # Shorter, tighter prompt to stay within token limits
        prompt = f"""Retail pricing agent. Return ONLY valid JSON, no thinking tags, no explanation.

Product: {row['product_name']} | Category: {row['category']}
MRP: {row['mrp']} | Cost: {row['cost_price']} | Current margin: {row['margin_pct']}%
MAX discount allowed: {max_d}% | Competitor lowest: {round(min_comp,2)}
Stock: {row['stock_units']} units | Overstocked: {row['overstocked']}
Segments: SEG01=Budget/HighSensitivity, SEG02=Loyalist/LowSensitivity, SEG03=Premium/MedSensitivity
Mechanisms: Flat Discount, Buy 2 Get 1, Bundle Deal, Loyalty Points

JSON format only:
{{"discount_pct": 10.0, "duration_days": 7, "target_segment_id": "SEG01", "mechanism": "Flat Discount", "reasoning": "brief reason"}}"""

        resp = llm.invoke([HumanMessage(content=prompt)])
        try:
            text = resp.content.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            if "<think>" in text:
                text = text.split("</think>")[-1].strip()
            plan = json.loads(text)
            plan["discount_pct"] = min(float(plan["discount_pct"]), max_d)
        except:
            plan = {
                "discount_pct": min(max_d * 0.5, 10),
                "duration_days": 7,
                "target_segment_id": "SEG01",
                "mechanism": "Flat Discount",
                "reasoning": "Fallback conservative plan"
            }
        plan.update({
            "product_id": pid,
            "product_name": row["product_name"],
            "category": row["category"],
            "mrp": row["mrp"],
            "max_safe_discount": max_d
        })
        plans.append(plan)
        print(f"  ✅ {i+1}/{len(selected_ids)} done: {row['product_name']}")

        # Delay between calls to respect rate limit
        time.sleep(4)

    return plans

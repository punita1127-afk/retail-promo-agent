import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from agents.orchestrator import run_pipeline

st.set_page_config(page_title="RetailMind", page_icon="🛒", layout="wide")
st.title("🛒 RetailMind — Autonomous Promotion Planner")
st.caption("3 AI agents: Select → Optimise → Simulate promotions before launch")
st.divider()

with st.sidebar:
    st.header("⚙️ Settings")
    promo_date = st.date_input("Promotion Start Date")
    st.markdown("""---
**Agent Pipeline**

1️⃣ Selector Agent — picks products

2️⃣ Optimizer Agent — sets discount

3️⃣ Simulator Agent — forecasts impact""")

col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("📁 Data Preview")
    try:
        st.dataframe(
            pd.read_csv('data/products.csv')
              [["product_name","category","mrp","margin_pct"]].head(8),
            use_container_width=True, hide_index=True)
    except:
        st.warning("Data files not found")

run_btn = st.button("🚀 Run Planning Agents", type="primary", use_container_width=True)

if run_btn:
    with st.spinner("🤖 Agents working... (~2 mins due to rate limits)"):
        out = run_pipeline(promo_date.strftime("%Y-%m-%d"))

    if out["status"] == "done":
        sims   = out["simulation_results"]["simulations"]
        plans  = out["promo_plans"]
        sim_df = pd.DataFrame(sims)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Products Selected", len(sims))
        k2.metric("Total Revenue Lift",
                  f"₹{sim_df['revenue_delta'].sum():,.0f}")
        k3.metric("Avg Discount",
                  f"{sim_df['discount_pct'].mean():.1f}%")
        k4.metric("Plans Approved",
                  f"{(sim_df['recommendation']=='APPROVE').sum()}/{len(sims)}")

        st.info("🤖 " + out["simulation_results"]["executive_summary"])
        st.divider()

        fig = go.Figure()
        fig.add_bar(name="Baseline",
                    x=sim_df["product_name"],
                    y=sim_df["baseline_revenue"],
                    marker_color="#374151")
        fig.add_bar(name="With Promo",
                    x=sim_df["product_name"],
                    y=sim_df["promo_revenue"],
                    marker_color="#3fb950")
        fig.update_layout(
            barmode="group",
            template="plotly_dark",
            title="Revenue Impact by Product",
            height=380,
            margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 Promotion Plan")
        plan_df = pd.DataFrame(plans)[[
            "product_name", "category", "mrp",
            "discount_pct", "duration_days",
            "target_segment_id", "mechanism"]]
        st.dataframe(plan_df, use_container_width=True, hide_index=True)

        st.subheader("⚠️ Risk Flags")
        for s in sims:
            label = (f"✅ {s['product_name']}"
                     if s["recommendation"] == "APPROVE"
                     else f"⚠️ {s['product_name']} — REVIEW")
            with st.expander(label):
                for flag in s["risk_flags"]:
                    st.write(flag)

        st.download_button(
            "⬇️ Download Promotion Plan (CSV)",
            plan_df.to_csv(index=False),
            "promo_plan.csv",
            "text/csv")

    elif out["status"] == "error":
        st.error(f"❌ Agent error: {out.get('error', 'Unknown error')}")
    else:
        st.warning("Pipeline did not complete. Check your API key and try again.")

import pandas as pd
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from agents.selector_agent  import run_selector_agent
from agents.optimizer_agent import run_optimizer_agent
from agents.simulator_agent import run_simulator_agent

class PromoState(TypedDict):
    products_df:    pd.DataFrame
    inventory_df:   pd.DataFrame
    holidays_df:    pd.DataFrame
    segments_df:    pd.DataFrame
    competitor_df:  pd.DataFrame
    promo_date:     str
    selected_products:   list
    selector_reasoning:  dict
    promo_plans:         list
    simulation_results:  dict
    status: str
    error:  Optional[str]

def selector_node(s):
    try:
        r = run_selector_agent(
            s["products_df"], s["inventory_df"], s["holidays_df"],
            s["segments_df"], s["competitor_df"], s["promo_date"])
        return {**s,
                "selected_products":  r["selected_products"],
                "selector_reasoning": r["reasoning"],
                "status": "selector_done"}
    except Exception as e:
        return {**s, "status": "error", "error": str(e)}

def optimizer_node(s):
    try:
        plans = run_optimizer_agent(
            s["selected_products"], s["products_df"], s["inventory_df"],
            s["segments_df"], s["competitor_df"], s["selector_reasoning"])
        return {**s, "promo_plans": plans, "status": "optimizer_done"}
    except Exception as e:
        return {**s, "status": "error", "error": str(e)}

def simulator_node(s):
    try:
        res = run_simulator_agent(
            s["promo_plans"], s["products_df"],
            s["inventory_df"], s["segments_df"])
        return {**s, "simulation_results": res, "status": "done"}
    except Exception as e:
        return {**s, "status": "error", "error": str(e)}

def build_graph():
    g = StateGraph(PromoState)
    g.add_node("selector",  selector_node)
    g.add_node("optimizer", optimizer_node)
    g.add_node("simulator", simulator_node)
    g.set_entry_point("selector")
    g.add_conditional_edges("selector",
        lambda s: "optimizer" if (s["status"] != "error" and s["selected_products"]) else "end",
        {"optimizer": "optimizer", "end": END})
    g.add_conditional_edges("optimizer",
        lambda s: "simulator" if (s["status"] != "error" and s["promo_plans"]) else "end",
        {"simulator": "simulator", "end": END})
    g.add_edge("simulator", END)
    return g.compile()

def run_pipeline(promo_date="2024-11-01"):
    BASE = 'data'
    state = {
        "products_df":   pd.read_csv(f'{BASE}/products.csv'),
        "inventory_df":  pd.read_csv(f'{BASE}/inventory.csv'),
        "holidays_df":   pd.read_csv(f'{BASE}/holidays.csv'),
        "segments_df":   pd.read_csv(f'{BASE}/customer_segments.csv'),
        "competitor_df": pd.read_csv(f'{BASE}/competitor_prices.csv'),
        "promo_date":    promo_date,
        "selected_products":  [],
        "selector_reasoning": {},
        "promo_plans":        [],
        "simulation_results": {},
        "status": "started",
        "error":  None
    }
    return build_graph().invoke(state)

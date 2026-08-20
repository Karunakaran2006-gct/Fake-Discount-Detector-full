"""
app.py — Fake Discount Detector · Streamlit UI

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from fdd.generator import generate_series, Regime
from fdd.features import extract_features, SPIKE_WINDOW_DAYS
from fdd.detection import analyze
from fdd.explain import generate_explanation
from fdd.schema import DiscountStatus


# ---------------------------------------------------------------------------
# Load real product catalog (once, cached)
# ---------------------------------------------------------------------------

@st.cache_data
def load_catalog() -> pd.DataFrame:
    """Load the Amazon product snapshot and parse prices."""
    path = os.path.join(os.path.dirname(__file__), "data", "real_snapshot_reference.csv")
    df = pd.read_csv(path)

    def parse_price(col):
        return (
            df[col]
            .astype(str)
            .str.replace(r"[₹,]", "", regex=True)
            .str.strip()
            .replace("", np.nan)
            .astype(float)
        )

    df["actual_price_clean"]    = parse_price("actual_price")
    df["discount_price_clean"]  = parse_price("discount_price")

    # Keep only rows where both prices are present and discount < actual
    df = df.dropna(subset=["actual_price_clean", "discount_price_clean"])
    df = df[df["discount_price_clean"] < df["actual_price_clean"]]
    df = df.reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Page config & global CSS
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Fake Discount Detector",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ── Main background ── */
    .stApp {
        background: radial-gradient(ellipse at 20% 0%, #0f1a2e 0%, #0d1117 50%, #0a0e15 100%);
        color: #e6edf3;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111827 0%, #0d1117 100%);
        border-right: 1px solid #1f2937;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, #1d4ed8 0%, #7c3aed 100%) !important;
        border: none !important;
        color: white !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px !important;
        border-radius: 10px !important;
        padding: 12px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(29,78,216,0.35) !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 24px rgba(29,78,216,0.55) !important;
    }

    /* ── Feature cards (landing) ── */
    .feature-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 28px 24px;
        text-align: center;
        height: 100%;
        transition: all 0.35s ease;
        position: relative;
        overflow: hidden;
    }
    .feature-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(88,166,255,0.4), transparent);
    }
    .feature-card:hover {
        border-color: rgba(88,166,255,0.3);
        transform: translateY(-4px);
        box-shadow: 0 20px 40px rgba(0,0,0,0.4), 0 0 30px rgba(88,166,255,0.08);
    }

    /* ── Generic metric card ── */
    .metric-card {
        background: rgba(22,27,34,0.8);
        border: 1px solid #30363d;
        border-radius: 14px;
        padding: 20px 24px;
        text-align: center;
        height: 100%;
        backdrop-filter: blur(8px);
    }
    .metric-card .label {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: #6e7681;
        margin-bottom: 8px;
    }
    .metric-card .value {
        font-size: 32px;
        font-weight: 800;
        line-height: 1;
    }

    /* ── Info strip (product / demo / csv) ── */
    .info-strip {
        background: linear-gradient(135deg, rgba(22,27,34,0.9) 0%, rgba(13,17,23,0.9) 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 24px;
        backdrop-filter: blur(8px);
    }

    /* ── Verdict badge ── */
    .verdict-badge {
        display: inline-flex;
        align-items: center;
        gap: 12px;
        border-radius: 14px;
        padding: 16px 36px;
        margin-bottom: 24px;
        font-size: 26px;
        font-weight: 900;
        letter-spacing: 2px;
        text-transform: uppercase;
        animation: badgePop 0.5s cubic-bezier(0.34,1.56,0.64,1) both;
    }
    @keyframes badgePop {
        from { opacity: 0; transform: scale(0.7); }
        to   { opacity: 1; transform: scale(1); }
    }
    .verdict-suspicious {
        background: linear-gradient(135deg, rgba(255,77,77,0.18), rgba(255,77,77,0.06));
        border: 1.5px solid rgba(255,77,77,0.45);
        color: #ff7b7b;
        box-shadow: 0 0 40px rgba(255,77,77,0.2), inset 0 0 20px rgba(255,77,77,0.04);
    }
    .verdict-genuine {
        background: linear-gradient(135deg, rgba(63,185,80,0.18), rgba(63,185,80,0.06));
        border: 1.5px solid rgba(63,185,80,0.45);
        color: #56d364;
        box-shadow: 0 0 40px rgba(63,185,80,0.2), inset 0 0 20px rgba(63,185,80,0.04);
    }
    .verdict-uncertain {
        background: linear-gradient(135deg, rgba(240,136,62,0.18), rgba(240,136,62,0.06));
        border: 1.5px solid rgba(240,136,62,0.45);
        color: #f0883e;
        box-shadow: 0 0 40px rgba(240,136,62,0.2), inset 0 0 20px rgba(240,136,62,0.04);
    }

    /* ── Score bars ── */
    .score-bar-wrap { margin-bottom: 18px; }
    .score-bar-header {
        display: flex;
        justify-content: space-between;
        font-size: 13px;
        margin-bottom: 6px;
    }
    .score-bar-label { font-weight: 600; color: #8b949e; }
    .score-bar-value { font-weight: 800; color: #e6edf3; font-size: 14px; }
    .score-bar-track {
        background: rgba(255,255,255,0.05);
        border-radius: 99px;
        height: 8px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.06);
    }
    .score-bar-fill {
        height: 100%;
        border-radius: 99px;
        transition: width 0.8s cubic-bezier(0.34,1.56,0.64,1);
    }

    /* ── Explanation box ── */
    .explanation-box {
        background: linear-gradient(135deg, rgba(22,27,34,0.9), rgba(13,17,23,0.9));
        border: 1px solid #30363d;
        border-left: 4px solid #58a6ff;
        border-radius: 12px;
        padding: 24px 28px;
        font-size: 14px;
        line-height: 1.9;
        white-space: pre-wrap;
        color: #c9d1d9;
        box-shadow: 0 4px 24px rgba(0,0,0,0.3), inset 0 0 30px rgba(88,166,255,0.02);
    }

    /* ── Section headers ── */
    h2 { color: #e6edf3 !important; }
    h3 {
        color: #c9d1d9 !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        letter-spacing: 0.3px !important;
        margin-bottom: 14px !important;
    }

    /* ── Divider ── */
    hr { border-color: #1f2937; margin: 20px 0; }

    /* ── Streamlit overrides ── */
    div[data-testid="stMetric"] label { color: #8b949e !important; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 10px; overflow: hidden; }
    .stDataFrame thead tr th {
        background: #161b22 !important;
        color: #8b949e !important;
        font-weight: 700 !important;
        font-size: 12px !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #30363d !important;
        border-radius: 10px !important;
        background: rgba(22,27,34,0.5) !important;
    }

    /* ── Shimmer animation for spinner context ── */
    @keyframes shimmer {
        0%   { background-position: -200% center; }
        100% { background-position:  200% center; }
    }
    .shimmer-text {
        background: linear-gradient(90deg, #58a6ff 0%, #a371f7 50%, #58a6ff 100%);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: shimmer 3s linear infinite;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Helper: Plotly price chart
# ---------------------------------------------------------------------------

def build_chart(
    df: pd.DataFrame,
    sale_date: str,
    claimed_original_price: float,
    claimed_sale_price: float,
) -> go.Figure:
    sale_ts = pd.Timestamp(sale_date)
    spike_start = sale_ts - pd.Timedelta(days=SPIKE_WINDOW_DAYS)

    fig = go.Figure()

    # Spike window highlight
    fig.add_vrect(
        x0=spike_start,
        x1=sale_ts,
        fillcolor="rgba(255,77,77,0.08)",
        layer="below",
        line_width=0,
        annotation_text="Spike window",
        annotation_position="top left",
        annotation_font_color="#ff7b7b",
        annotation_font_size=11,
    )

    # Price line
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["price"],
        mode="lines",
        name="Price",
        line=dict(color="#58a6ff", width=2),
        hovertemplate="₹%{y:.2f}<br>%{x|%d %b %Y}<extra></extra>",
    ))

    # Claimed original price line
    fig.add_hline(
        y=claimed_original_price,
        line_dash="dot",
        line_color="#8b949e",
        annotation_text=f"Claimed orig: ₹{claimed_original_price:.0f}",
        annotation_position="bottom right",
        annotation_font_color="#8b949e",
        annotation_font_size=11,
    )

    # Sale price line
    fig.add_hline(
        y=claimed_sale_price,
        line_dash="dot",
        line_color="#56d364",
        annotation_text=f"Sale price: ₹{claimed_sale_price:.0f}",
        annotation_position="top right",
        annotation_font_color="#56d364",
        annotation_font_size=11,
    )

    # Sale date vertical line
    fig.add_vline(
        x=sale_ts,
        line_dash="dash",
        line_color="#f0883e",
        annotation_text="Sale",
        annotation_position="top",
        annotation_font_color="#f0883e",
        annotation_font_size=12,
    )

    fig.update_layout(
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font=dict(color="#8b949e", family="Inter"),
        xaxis=dict(
            gridcolor="#21262d",
            showline=True,
            linecolor="#30363d",
            title="Date",
        ),
        yaxis=dict(
            gridcolor="#21262d",
            showline=True,
            linecolor="#30363d",
            title="Price (₹)",
        ),
        legend=dict(
            bgcolor="#161b22",
            bordercolor="#30363d",
            borderwidth=1,
        ),
        hovermode="x unified",
        margin=dict(l=0, r=0, t=24, b=0),
        height=380,
    )
    return fig


# ---------------------------------------------------------------------------
# Helper: render a score bar in HTML
# ---------------------------------------------------------------------------

def score_bar_html(label: str, value: float, gradient: str) -> str:
    pct = int(value * 100)
    return f"""
    <div class="score-bar-wrap">
      <div class="score-bar-header">
        <span class="score-bar-label">{label}</span>
        <span class="score-bar-value">{value:.2f}</span>
      </div>
      <div class="score-bar-track">
        <div class="score-bar-fill" style="width:{pct}%;background:{gradient};"></div>
      </div>
    </div>
    """


# ---------------------------------------------------------------------------
# Main analysis function
# ---------------------------------------------------------------------------

def run_analysis(df: pd.DataFrame, orig: float, sale: float, sale_date: str, pid: str):
    try:
        features = extract_features(df, orig, sale, sale_date, pid)
    except Exception as e:
        st.error(f"Feature extraction failed: {e}")
        return

    result = analyze(features)
    generate_explanation(features, result)

    # ── Price Chart ────────────────────────────────────────────────────────
    st.markdown("### 📈 Price History")
    fig = build_chart(df, sale_date, orig, sale)
    st.plotly_chart(fig, use_container_width=True)

    # ── Status + Scores ───────────────────────────────────────────────────
    st.markdown("### 🏷️ Verdict")
    status = result.status

    verdict_class = {
        DiscountStatus.SUSPICIOUS: "verdict-suspicious",
        DiscountStatus.GENUINE:    "verdict-genuine",
        DiscountStatus.UNCERTAIN:  "verdict-uncertain",
    }[status]

    icon = {
        DiscountStatus.SUSPICIOUS: "⚠️",
        DiscountStatus.GENUINE:    "✅",
        DiscountStatus.UNCERTAIN:  "❓",
    }[status]

    st.markdown(
        f'<div class="verdict-badge {verdict_class}">{icon}&nbsp;{status.value.upper()}</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        susp_grad = (
            "linear-gradient(90deg,#ff4d4d,#ff7b7b)" if result.suspicion_score > 0.55
            else ("linear-gradient(90deg,#56d364,#3fb950)" if result.suspicion_score < 0.25
                  else "linear-gradient(90deg,#f0883e,#f5a962)")
        )
        st.markdown(
            score_bar_html("Suspicion Score", result.suspicion_score, susp_grad),
            unsafe_allow_html=True,
        )
        st.markdown(
            score_bar_html("Confidence", result.confidence,
                           "linear-gradient(90deg,#1d4ed8,#58a6ff)"),
            unsafe_allow_html=True,
        )

    with col2:
        vol_grad = (
            "linear-gradient(90deg,#ff4d4d,#ff7b7b)" if result.volatility_score > 0.7
            else ("linear-gradient(90deg,#56d364,#3fb950)" if result.volatility_score < 0.3
                  else "linear-gradient(90deg,#f0883e,#f5a962)")
        )
        st.markdown(
            score_bar_html("Volatility Score", result.volatility_score, vol_grad),
            unsafe_allow_html=True,
        )
        st.markdown(
            score_bar_html("Days History", min(1.0, features.n_days_history / 180),
                           "linear-gradient(90deg,#7c3aed,#a371f7)"),
            unsafe_allow_html=True,
        )

    # ── Explanation ────────────────────────────────────────────────────────
    st.markdown("### 💬 Explanation")
    st.markdown(
        f'<div class="explanation-box">{result.explanation_text}</div>',
        unsafe_allow_html=True,
    )

    # ── Factor Breakdown ───────────────────────────────────────────────────
    if result.factors:
        with st.expander("🔎 Factor breakdown", expanded=True):
            factor_data = [
                {
                    "Factor": f.name.replace("_", " ").title(),
                    "Description": f.description,
                    "Contribution": f"{f.contribution:+.2f}",
                }
                for f in result.factors
            ]
            st.dataframe(
                pd.DataFrame(factor_data),
                use_container_width=True,
                hide_index=True,
            )

    # ── Raw Features ──────────────────────────────────────────────────────
    with st.expander("🔬 Raw extracted features"):
        feat_data = {
            "Feature": [
                "Days of history",
                "Days original price held",
                "Pre-sale spike %",
                "Sale price percentile",
                "% below median",
                "Coefficient of variation",
                "Volatility label",
                "Trend slope (₹/day)",
            ],
            "Value": [
                features.n_days_history,
                features.days_original_price_held,
                f"{features.pre_sale_spike_pct:.2%}",
                f"{features.sale_price_percentile:.2%}",
                f"{features.pct_below_median:.2%}",
                f"{features.coefficient_of_variation:.4f}",
                features.volatility_label,
                f"{features.trend_slope_per_day:.4f}",
            ],
        }
        st.dataframe(pd.DataFrame(feat_data), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Sidebar — input mode
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div style='text-align:center;padding:20px 0 28px;'>
          <div style='font-size:44px;filter:drop-shadow(0 0 18px rgba(88,166,255,0.6));margin-bottom:10px;'>🔍</div>
          <div style='font-size:20px;font-weight:900;letter-spacing:-0.5px;
                      background:linear-gradient(90deg,#58a6ff,#a371f7);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent;'
          >Fake Discount Detector</div>
          <div style='font-size:11px;color:#6e7681;margin-top:6px;letter-spacing:0.5px;'>
            PATTERN-BASED PRICE ANALYSIS
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    mode = st.radio(
        "**Input mode**",
        options=["Real Product 🛒", "Demo (synthetic)", "Upload CSV"],
        index=0,
    )

    st.divider()

    if mode == "Real Product 🛒":
        catalog = load_catalog()
        product_names = catalog["name"].tolist()
        selected_name = st.selectbox(
            "**Pick a product**",
            options=product_names,
            index=0,
            help="Choose any product from the Amazon catalog.",
        )
        selected_row = catalog[catalog["name"] == selected_name].iloc[0]
        actual_p  = float(selected_row["actual_price_clean"])
        discount_p = float(selected_row["discount_price_clean"])

        st.markdown(
            f"<div style='font-size:12px;color:#8b949e;margin-top:8px;'>"
            f"MRP: <b style='color:#c9d1d9;'>₹{actual_p:.0f}</b> &nbsp;→&nbsp; "
            f"Sale: <b style='color:#56d364;'>₹{discount_p:.0f}</b> &nbsp; "
            f"({((actual_p - discount_p)/actual_p*100):.0f}% off)"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.divider()
        n_days_real = st.slider("Simulated history length (days)", 60, 300, 180, 10)
        seed_real   = st.number_input("Seed", value=42, step=1)
        analyze_btn = st.button("🔍 Analyse", use_container_width=True, type="primary")

    elif mode == "Demo (synthetic)":
        regime_labels = {
            "Dark Pattern 🔴": Regime.DARK_PATTERN,
            "Genuine Discount 🟢": Regime.GENUINE_DISCOUNT,
            "Stable (cosmetic) 🟡": Regime.STABLE,
            "Gradual Drift 🟡": Regime.GRADUAL_DRIFT,
        }
        regime_choice = st.selectbox(
            "**Regime**",
            options=list(regime_labels.keys()),
            index=0,
            help="Choose a simulated pricing pattern to analyse.",
        )
        seed = st.number_input("Seed (for reproducibility)", value=42, step=1)
        n_days = st.slider("History length (days)", 60, 300, 180, 10)
        base_price = st.number_input("Base price (₹)", value=1000.0, step=50.0)

        analyze_btn = st.button("🔍 Analyse", use_container_width=True, type="primary")

    else:  # Upload CSV
        uploaded = st.file_uploader(
            "**Upload price history CSV**",
            type=["csv"],
            help="Required columns: `date`, `price`. Optional: `product_name`",
        )
        st.caption("Required: `date`, `price`. Optional: `product_name` (for multiple products in one file)")
        st.divider()
        
        analyze_btn = False
        prod_df = None
        
        if uploaded is not None:
            try:
                uploaded.seek(0)
                upload_df = pd.read_csv(uploaded)
                
                if "date" not in upload_df.columns or "price" not in upload_df.columns:
                    st.error("CSV must contain `date` and `price` columns.")
                else:
                    if "product_name" in upload_df.columns:
                        product_list = upload_df["product_name"].unique().tolist()
                        selected_product = st.selectbox(
                            "**Select Product (type to search)**", 
                            options=product_list,
                            index=0
                        )
                        prod_df = upload_df[upload_df["product_name"] == selected_product].copy()
                        pid_val = selected_product
                    else:
                        prod_df = upload_df.copy()
                        pid_val = "UPLOADED-PRODUCT"
                    
                    # Ensure date is parsed and sorted for default auto-detection
                    prod_df["date"] = pd.to_datetime(prod_df["date"])
                    prod_df = prod_df.sort_values("date")
                    
                    default_orig = float(prod_df["price"].max())
                    default_sale = float(prod_df["price"].iloc[-1])
                    
                    # Smart auto-detection for sale date:
                    # Find the first date where the price dropped to the sale price
                    sale_rows = prod_df[prod_df["price"] == default_sale]
                    if not sale_rows.empty:
                        default_date = sale_rows["date"].iloc[0].date()
                    else:
                        default_date = prod_df["date"].iloc[-1].date()
                    
                    pid_input = st.text_input("Product Name/ID", value=pid_val, key=f"pid_{pid_val}")
                    orig_input = st.number_input("Claimed MRP (₹)", value=default_orig, step=10.0, key=f"orig_{pid_val}")
                    sale_input = st.number_input("Claimed Sale Price (₹)", value=default_sale, step=10.0, key=f"sale_{pid_val}")
                    sale_date_input = st.date_input("Sale date", value=default_date, key=f"date_{pid_val}")
                    analyze_btn = st.button("🔍 Analyse", use_container_width=True, type="primary")
            except Exception as e:
                st.error(f"Error parsing CSV: {e}")

    st.divider()
    st.markdown(
        "<div style='font-size:11px;color:#8b949e;text-align:center;'>"
        "Uses rule-based statistics + Isolation Forest.<br>"
        "Three-state output: Genuine / Suspicious / Uncertain"
        "</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Main area — header + results
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div style='margin-bottom:28px;'>
      <h1 style='font-size:38px;font-weight:900;letter-spacing:-1px;margin-bottom:6px;
                  background:linear-gradient(90deg,#e6edf3 0%,#58a6ff 50%,#a371f7 100%);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;display:inline-block;'>
        Fake Discount Detector
      </h1>
      <p style='color:#6e7681;font-size:15px;margin:0 0 16px;max-width:620px;line-height:1.6;'>
        Detects misleading e-commerce discounts by analyzing historical pricing patterns —
        no machine-learning labels required.
      </p>
      <div style='display:flex;gap:8px;flex-wrap:wrap;'>
        <span style='background:rgba(88,166,255,0.12);border:1px solid rgba(88,166,255,0.25);
                     color:#58a6ff;border-radius:20px;padding:4px 14px;font-size:12px;font-weight:600;'>📊 Rule-based</span>
        <span style='background:rgba(163,113,247,0.12);border:1px solid rgba(163,113,247,0.25);
                     color:#a371f7;border-radius:20px;padding:4px 14px;font-size:12px;font-weight:600;'>🤖 Isolation Forest</span>
        <span style='background:rgba(86,211,100,0.12);border:1px solid rgba(86,211,100,0.25);
                     color:#56d364;border-radius:20px;padding:4px 14px;font-size:12px;font-weight:600;'>✅ 3-State verdict</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

if not analyze_btn:
    # Landing state
    c1, c2, c3 = st.columns(3)
    for col, icon, title, desc, accent in [
        (c1, "📊", "Pattern Recognition",
         "Detects pre-sale price spikes, short-hold 'original' prices, and cosmetic discounts.",
         "#58a6ff"),
        (c2, "🤖", "Anomaly Detection",
         "Isolation Forest cross-checks pricing against a reference population of real products.",
         "#a371f7"),
        (c3, "💬", "Plain-language Verdict",
         "Every result ships with a readable explanation — Genuine, Suspicious, or Uncertain.",
         "#56d364"),
    ]:
        with col:
            st.markdown(
                f"""
                <div class="feature-card">
                  <div style='font-size:36px;margin-bottom:16px;
                              filter:drop-shadow(0 0 12px {accent}66);'>{icon}</div>
                  <div style='font-size:15px;font-weight:700;color:#e6edf3;
                              margin-bottom:10px;'>{title}</div>
                  <div style='font-size:13px;color:#6e7681;line-height:1.7;'>{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown(
        """
        <div style='margin-top:28px;background:linear-gradient(135deg,rgba(88,166,255,0.08),rgba(163,113,247,0.06));
                    border:1px solid rgba(88,166,255,0.2);border-radius:12px;
                    padding:16px 22px;font-size:14px;color:#8b949e;'>
          💡 <b style='color:#c9d1d9;'>Get started:</b> Choose an input mode in the sidebar and click
          <b style='color:#58a6ff;'>Analyse</b> to inspect a product's pricing history.
        </div>
        """,
        unsafe_allow_html=True,
    )

else:
    # ── Real Product mode ───────────────────────────────────────────────────
    if mode == "Real Product 🛒":
        # Truncate long names for display
        display_name = selected_name if len(selected_name) <= 80 else selected_name[:77] + "..."

        st.markdown(
            f"""
            <div class="info-strip">
              <div style='font-size:10px;font-weight:700;letter-spacing:2px;
                          text-transform:uppercase;color:#6e7681;margin-bottom:8px;'>Analysing Product</div>
              <div style='font-size:17px;font-weight:700;color:#e6edf3;margin-bottom:12px;
                          line-height:1.4;'>{display_name}</div>
              <div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap;font-size:13px;'>
                <span style='color:#8b949e;'>MRP: <b style='color:#c9d1d9;'>₹{actual_p:.0f}</b></span>
                <span style='color:#30363d;'>→</span>
                <span style='color:#8b949e;'>Sale: <b style='color:#56d364;'>₹{discount_p:.0f}</b></span>
                <span style='background:rgba(86,211,100,0.12);border:1px solid rgba(86,211,100,0.3);
                             color:#56d364;border-radius:20px;padding:3px 12px;font-weight:700;font-size:12px;'>
                  {((actual_p - discount_p)/actual_p*100):.0f}% off
                </span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Auto-pick regime based on actual discount size
        discount_pct = (actual_p - discount_p) / actual_p * 100
        if discount_pct >= 25:
            auto_regime = Regime.GENUINE_DISCOUNT
            regime_reason = f"{discount_pct:.0f}% off — large discount, looks like a real sale."
            sim_base = actual_p   # history at MRP → sale price is genuinely low → GENUINE
        elif discount_pct < 5:
            auto_regime = Regime.STABLE
            regime_reason = f"{discount_pct:.0f}% off — tiny discount, basically cosmetic."
            sim_base = actual_p
        elif discount_pct < 15:
            auto_regime = Regime.GRADUAL_DRIFT
            regime_reason = f"{discount_pct:.0f}% off — moderate discount, looks like natural drift."
            sim_base = actual_p
        else:
            auto_regime = Regime.DARK_PATTERN
            regime_reason = f"{discount_pct:.0f}% off — mid-range, classic fake-discount range."
            sim_base = discount_p  # history at real price → MRP looks like an artificial spike

        st.caption(f"🤖 Auto-detected pattern: **{auto_regime.value}** — {regime_reason}")

        with st.spinner("Simulating price history for this product…"):
            series = generate_series(
                regime=auto_regime,
                product_id=selected_name[:40],
                n_days=int(n_days_real),
                base_price=float(sim_base),
                seed=int(seed_real),
            )
            # Override with real product prices
            series.claimed_original_price = actual_p
            series.claimed_sale_price     = discount_p

        df = series.to_dataframe()

        run_analysis(
            df=df,
            orig=actual_p,
            sale=discount_p,
            sale_date=series.sale_date,
            pid=selected_name[:40],
        )

    # ── Demo mode ──────────────────────────────────────────────────────────
    elif mode == "Demo (synthetic)":
        regime = regime_labels[regime_choice]
        with st.spinner("Generating synthetic price history…"):
            series = generate_series(
                regime=regime,
                product_id="DEMO-001",
                n_days=n_days,
                base_price=float(base_price),
                seed=int(seed),
            )
        df = series.to_dataframe()

        st.markdown(
            f"""
            <div style='background:#161b22;border:1px solid #30363d;border-radius:8px;
                        padding:12px 20px;margin-bottom:20px;font-size:13px;color:#8b949e;'>
              <b style='color:#c9d1d9;'>Synthetic series:</b>
              regime = <code>{series.regime.value}</code> &nbsp;|&nbsp;
              claimed orig = <b>₹{series.claimed_original_price:.2f}</b> &nbsp;|&nbsp;
              sale price = <b>₹{series.claimed_sale_price:.2f}</b> &nbsp;|&nbsp;
              ground truth = <b>{'Genuine' if series.ground_truth_genuine else 'Suspicious'}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

        run_analysis(
            df=df,
            orig=series.claimed_original_price,
            sale=series.claimed_sale_price,
            sale_date=series.sale_date,
            pid=series.product_id,
        )

    # ── CSV upload mode ────────────────────────────────────────────────────
    else:
        if uploaded is None:
            st.warning("Please upload a CSV file in the sidebar.", icon="⬆️")
        elif 'prod_df' in locals() and prod_df is not None:
            st.markdown(
                f"""
                <div style='background:#161b22;border:1px solid #30363d;border-radius:8px;
                            padding:12px 20px;margin-bottom:20px;font-size:13px;color:#8b949e;'>
                  <b style='color:#c9d1d9;'>Uploaded Data:</b>
                  Product = <code>{pid_input}</code> &nbsp;|&nbsp;
                  Rows analyzed = <b>{len(prod_df)}</b>
                </div>
                """,
                unsafe_allow_html=True,
            )
            run_analysis(
                df=prod_df,
                orig=float(orig_input),
                sale=float(sale_input),
                sale_date=str(sale_date_input),
                pid=pid_input,
            )

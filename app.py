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
from fdd.gemini_explain import gemini_explain, parse_gemini_sections
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
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }

    /* ── Main background ── */
    .stApp { background: #0a0a0a; color: #f0f0f0; }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: #111111;
        border-right: 1px solid #222;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background: #f0f0f0 !important;
        border: none !important;
        color: #0a0a0a !important;
        font-weight: 700 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 15px !important;
        border-radius: 8px !important;
        padding: 12px !important;
        transition: background 0.2s ease !important;
        letter-spacing: 0 !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #d4d4d4 !important;
        transform: none !important;
    }

    /* ── Feature cards (landing) ── */
    .feature-card {
        background: #141414;
        border: 1px solid #242424;
        border-radius: 12px;
        padding: 28px 24px;
        text-align: center;
        height: 100%;
        transition: border-color 0.2s ease;
    }
    .feature-card:hover { border-color: #444; }

    /* ── Info strip ── */
    .info-strip {
        background: #141414;
        border: 1px solid #242424;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 24px;
    }

    /* ── Verdict block + mascot ── */
    .verdict-block {
        border-radius: 16px;
        padding: 32px 40px;
        margin-bottom: 28px;
        display: flex;
        align-items: center;
        gap: 24px;
        animation: fadeUp 0.4s ease both;
    }
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(16px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .verdict-suspicious { background: #1a0a0a; border: 1.5px solid #5a1a1a; }
    .verdict-genuine    { background: #0a1a0d; border: 1.5px solid #1a5a25; }
    .verdict-uncertain  { background: #1a1500; border: 1.5px solid #5a4a00; }
    .verdict-label { font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 4px; }
    .verdict-title { font-size: 30px; font-weight: 800; line-height: 1.1; }
    .verdict-sub   { font-size: 14px; margin-top: 6px; opacity: 0.65; }

    .mascot { font-size: 90px; line-height: 1; flex-shrink: 0; display: block; }
    .mascot-genuine  { animation: mascotBounce 0.6s cubic-bezier(0.34,1.56,0.64,1) both, mascotWiggle 2s 0.8s ease-in-out infinite; }
    .mascot-susp     { animation: mascotBounce 0.6s cubic-bezier(0.34,1.56,0.64,1) both, mascotShake 0.45s 0.7s ease-in-out 4; }
    .mascot-uncertain{ animation: mascotBounce 0.6s cubic-bezier(0.34,1.56,0.64,1) both, mascotTilt 1.8s 0.8s ease-in-out infinite; }
    @keyframes mascotBounce  { from { opacity:0; transform:scale(0.3) rotate(-15deg); } to { opacity:1; transform:scale(1) rotate(0); } }
    @keyframes mascotWiggle  { 0%,100%{transform:rotate(0) scale(1);} 25%{transform:rotate(8deg) scale(1.06);} 75%{transform:rotate(-8deg) scale(1.06);} }
    @keyframes mascotShake   { 0%,100%{transform:translateX(0);} 25%{transform:translateX(-9px);} 75%{transform:translateX(9px);} }
    @keyframes mascotTilt    { 0%,100%{transform:rotate(0);} 50%{transform:rotate(12deg);} }

    /* ── Score bars ── */
    .score-bar-wrap { margin-bottom: 18px; }
    .score-bar-header { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px; }
    .score-bar-label { font-weight: 600; color: #888; }
    .score-bar-value { font-weight: 700; color: #f0f0f0; font-size: 13px; }
    .score-bar-track { background: #1e1e1e; border-radius: 99px; height: 6px; overflow: hidden; border: 1px solid #2a2a2a; }
    .score-bar-fill  { height: 100%; border-radius: 99px; transition: width 0.8s cubic-bezier(0.34,1.56,0.64,1); }

    /* ── Explanation box ── */
    .explanation-box {
        background: #141414;
        border: 1px solid #242424;
        border-left: 3px solid #555;
        border-radius: 10px;
        padding: 24px 28px;
        font-size: 15px;
        line-height: 1.8;
        white-space: pre-wrap;
        color: #c8c8c8;
    }

    /* ── Section headers ── */
    h1, h2, h3 { color: #f0f0f0 !important; font-family: 'DM Sans', sans-serif !important; }
    h3 { font-size: 16px !important; font-weight: 700 !important; margin-bottom: 14px !important; }

    /* ── Divider ── */
    hr { border-color: #222; margin: 20px 0; }

    /* ── Streamlit overrides ── */
    div[data-testid="stMetric"] label { color: #888 !important; }
    .stDataFrame { border: 1px solid #242424 !important; border-radius: 8px; overflow: hidden; }
    .stDataFrame thead tr th {
        background: #141414 !important;
        color: #888 !important;
        font-weight: 700 !important;
        font-size: 12px !important;
        letter-spacing: 0.5px !important;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #242424 !important;
        border-radius: 8px !important;
        background: #111 !important;
    }
    .stRadio label, .stSelectbox label { color: #aaa !important; font-size: 13px !important; }
    p { color: #aaa !important; }
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
        paper_bgcolor="#0a0a0a",
        plot_bgcolor="#0a0a0a",
        font=dict(color="#888", family="DM Sans, sans-serif"),
        xaxis=dict(
            gridcolor="#1e1e1e",
            showline=True,
            linecolor="#2a2a2a",
            title="Date",
        ),
        yaxis=dict(
            gridcolor="#1e1e1e",
            showline=True,
            linecolor="#2a2a2a",
            title="Price (₹)",
        ),
        legend=dict(
            bgcolor="#141414",
            bordercolor="#242424",
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

def run_analysis(df: pd.DataFrame, orig: float, sale: float, sale_date: str, pid: str, gemini_key: str = ""):
    try:
        features = extract_features(df, orig, sale, sale_date, pid)
    except Exception as e:
        st.error(f"Feature extraction failed: {e}")
        return

    result = analyze(features)
    generate_explanation(features, result)  # fallback explanation

    # Try Gemini for richer text
    explanation_body = result.explanation_text
    directive_text = ""
    ai_powered = False
    if gemini_key:
        with st.spinner("Getting AI explanation..."):
            ai_raw = gemini_explain(features, result, api_key=gemini_key)
        if ai_raw:
            explanation_body, directive_text = parse_gemini_sections(ai_raw)
            ai_powered = True

    # ── Price Chart ────────────────────────────────────────────────────────
    st.markdown("### Price History")
    fig = build_chart(df, sale_date, orig, sale)
    st.plotly_chart(fig, use_container_width=True)

    # ── Status + Mascot Verdict ───────────────────────────────────────────
    st.markdown("### Verdict")
    status = result.status

    _mascot = {
        DiscountStatus.GENUINE:    ("👍", "mascot-genuine",  "verdict-genuine",    "#4ade80", "Real deal — this discount checks out."),
        DiscountStatus.SUSPICIOUS: ("😱", "mascot-susp",     "verdict-suspicious", "#f87171", "Looks fake — the price history tells a different story."),
        DiscountStatus.UNCERTAIN:  ("🤔", "mascot-uncertain","verdict-uncertain",  "#fbbf24", "Can't call it — not enough price data to be sure."),
    }[status]
    emoji, mascot_cls, block_cls, color, subtitle = _mascot

    st.markdown(
        f"""
        <div class="verdict-block {block_cls}">
          <span class="mascot {mascot_cls}">{emoji}</span>
          <div>
            <div class="verdict-label" style="color:{color};">{status.value.upper()}</div>
            <div class="verdict-title" style="color:{color};">{status.value.capitalize()} Discount</div>
            <div class="verdict-sub">{subtitle}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        susp_grad = (
            "linear-gradient(90deg,#ef4444,#f87171)" if result.suspicion_score > 0.55
            else ("linear-gradient(90deg,#22c55e,#4ade80)" if result.suspicion_score < 0.25
                  else "linear-gradient(90deg,#f59e0b,#fbbf24)")
        )
        st.markdown(score_bar_html("Fake-deal likelihood", result.suspicion_score, susp_grad), unsafe_allow_html=True)
        st.markdown(score_bar_html("How confident we are", result.confidence, "linear-gradient(90deg,#3b82f6,#60a5fa)"), unsafe_allow_html=True)

    with col2:
        vol_grad = (
            "linear-gradient(90deg,#ef4444,#f87171)" if result.volatility_score > 0.7
            else ("linear-gradient(90deg,#22c55e,#4ade80)" if result.volatility_score < 0.3
                  else "linear-gradient(90deg,#f59e0b,#fbbf24)")
        )
        st.markdown(score_bar_html("Price instability", result.volatility_score, vol_grad), unsafe_allow_html=True)
        st.markdown(score_bar_html("Data coverage", min(1.0, features.n_days_history / 180), "linear-gradient(90deg,#8b5cf6,#a78bfa)"), unsafe_allow_html=True)

    # ── Directive card (AI only) ───────────────────────────────────────────
    if directive_text:
        _dir_color = {
            DiscountStatus.GENUINE:    "#4ade80",
            DiscountStatus.SUSPICIOUS: "#f87171",
            DiscountStatus.UNCERTAIN:  "#fbbf24",
        }[status]
        _dir_bg = {
            DiscountStatus.GENUINE:    "#0a1a0d",
            DiscountStatus.SUSPICIOUS: "#1a0a0a",
            DiscountStatus.UNCERTAIN:  "#1a1500",
        }[status]
        st.markdown(
            f"""
            <div style='background:{_dir_bg};border:1px solid {_dir_color}55;
                        border-left:4px solid {_dir_color};
                        border-radius:10px;padding:20px 24px;margin-bottom:20px;'>
              <div style='font-size:11px;font-weight:700;letter-spacing:2px;
                          text-transform:uppercase;color:{_dir_color};margin-bottom:8px;'>What should you do?</div>
              <div style='font-size:15px;line-height:1.75;color:#e0e0e0;'>{directive_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Explanation ────────────────────────────────────────────────────────
    _ai_tag = "<span style='font-size:10px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:4px;padding:2px 8px;color:#555;margin-left:8px;vertical-align:middle;'>AI</span>" if ai_powered else ""
    st.markdown(f"### What we found {_ai_tag}", unsafe_allow_html=True)
    st.markdown(
        f'<div class="explanation-box">{explanation_body}</div>',
        unsafe_allow_html=True,
    )

    # ── Factor Breakdown ───────────────────────────────────────────────────
    _FACTOR_NAME_MAP = {
        "pre_sale_spike": "Price spike before sale",
        "short_original_price_hold": "'Original' price wasn't held long",
        "long_original_price_hold": "'Original' price held for a long time",
        "sale_price_not_low": "Sale price isn't actually cheap",
        "sale_price_genuinely_low": "Sale price is genuinely low",
        "minimal_discount_vs_median": "Tiny saving vs. typical price",
        "deep_discount_vs_median": "Big saving vs. typical price",
        "rising_trend_plus_spike": "Price was already rising before the spike",
        "isolation_forest_cross_check": "Cross-check against similar products",
    }
    if result.factors:
        with st.expander("What signals did we find?", expanded=True):
            factor_data = [
                {
                    "Signal": _FACTOR_NAME_MAP.get(f.name, f.name.replace("_", " ").title()),
                    "What it means": f.description,
                    "Impact": "Suspicious" if f.contribution > 0 else ("Looks fine" if f.contribution < 0 else "Info only"),
                }
                for f in result.factors
            ]
            st.dataframe(
                pd.DataFrame(factor_data),
                use_container_width=True,
                hide_index=True,
            )

    # ── Raw Features ──────────────────────────────────────────────────────
    with st.expander("Detailed numbers (for the curious)"):
        feat_data = {
            "What we measured": [
                "Days of price history we have",
                "Days the 'original' price was held before the sale",
                "How much the price jumped just before the sale",
                "Where the sale price ranks vs. all past prices (lower = cheaper)",
                "How much cheaper the sale price is vs. the usual price",
                "How much the price fluctuates overall (higher = more chaotic)",
                "Overall price stability",
                "Price trend (positive = rising, negative = falling)",
            ],
            "Value": [
                f"{features.n_days_history} days",
                f"{features.days_original_price_held} days",
                f"{features.pre_sale_spike_pct:.1%}",
                f"{features.sale_price_percentile:.0%} percentile",
                f"{features.pct_below_median:.1%} below usual",
                f"{features.coefficient_of_variation:.2f}",
                features.volatility_label,
                f"{'Rising' if features.trend_slope_per_day > 0 else 'Falling'} (₹{abs(features.trend_slope_per_day):.2f}/day)",
            ],
        }
        st.dataframe(pd.DataFrame(feat_data), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Sidebar — input mode
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div style='padding:20px 0 24px;'>
          <div style='font-size:17px;font-weight:800;color:#f0f0f0;letter-spacing:-0.3px;'>Fake Discount Detector</div>
          <div style='font-size:11px;color:#555;margin-top:4px;letter-spacing:1px;text-transform:uppercase;'>Price Honesty Checker</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    mode = st.radio(
        "**How do you want to test it?**",
        options=["Real Product", "Try an Example", "Upload CSV"],
        index=0,
    )

    st.divider()

    if mode == "Real Product":
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
        n_days_real = st.slider("How many days of price history to simulate", 60, 300, 180, 10)
        seed_real   = st.number_input("Variation ID (change to see different simulations)", value=42, step=1)
        analyze_btn = st.button("Check this discount", use_container_width=True, type="primary")

    elif mode == "Try an Example":
        regime_labels = {
            "Fake Discount (Price inflated before sale)": Regime.DARK_PATTERN,
            "Real Discount (Genuine price drop)": Regime.GENUINE_DISCOUNT,
            "Cosmetic Discount (Barely any savings)": Regime.STABLE,
            "Gradual Drift (Slow price rise then 'sale')": Regime.GRADUAL_DRIFT,
        }
        regime_choice = st.selectbox(
            "**Pick a pricing scenario**",
            options=list(regime_labels.keys()),
            index=0,
            help="Choose a scenario to see how the detector handles it.",
        )
        seed = st.number_input("Variation ID (change to see different examples)", value=42, step=1)
        n_days = st.slider("Days of price history to show", 60, 300, 180, 10)
        base_price = st.number_input("Product price (₹)", value=1000.0, step=50.0)

        analyze_btn = st.button("Check this discount", use_container_width=True, type="primary")

    else:  # Upload CSV

        # ── CSV Guide ──────────────────────────────────────────────────────
        st.markdown(
            """
            <div style='background:#141414;border:1px solid #242424;border-radius:10px;
                        padding:16px 18px;margin-bottom:14px;font-size:12px;'>
              <div style='font-weight:700;color:#f0f0f0;margin-bottom:10px;font-size:13px;'>How to prepare your CSV</div>

              <div style='color:#888;margin-bottom:10px;line-height:1.6;'>
                Your file must have at least these two columns:
              </div>

              <div style='background:#0a0a0a;border:1px solid #2a2a2a;border-radius:6px;
                          padding:10px 14px;font-family:monospace;font-size:11px;color:#aaa;margin-bottom:12px;'>
                date, price, product_name<br>
                2024-01-01, 4999, Nike Air Max<br>
                2024-01-02, 4999, Nike Air Max<br>
                2024-03-15, 2999, Nike Air Max
              </div>

              <div style='display:flex;flex-direction:column;gap:8px;'>
                <div style='display:flex;gap:8px;align-items:flex-start;'>
                  <span style='color:#4ade80;font-size:14px;flex-shrink:0;'>✓</span>
                  <span style='color:#888;'><b style='color:#ccc;'>date</b> — any standard format works (YYYY-MM-DD preferred)</span>
                </div>
                <div style='display:flex;gap:8px;align-items:flex-start;'>
                  <span style='color:#4ade80;font-size:14px;flex-shrink:0;'>✓</span>
                  <span style='color:#888;'><b style='color:#ccc;'>price</b> — the actual price on that day (numbers only, no ₹ symbol)</span>
                </div>
                <div style='display:flex;gap:8px;align-items:flex-start;'>
                  <span style='color:#555;font-size:14px;flex-shrink:0;'>○</span>
                  <span style='color:#666;'><b style='color:#888;'>product_name</b> — optional, lets you store multiple products in one file</span>
                </div>
              </div>

              <div style='margin-top:12px;padding-top:12px;border-top:1px solid #222;display:flex;flex-direction:column;gap:6px;'>
                <div style='display:flex;gap:8px;align-items:flex-start;'>
                  <span style='color:#fbbf24;font-size:13px;flex-shrink:0;'>⚠</span>
                  <span style='color:#777;'><b style='color:#aaa;'>Min. 30 days</b> of history needed for a confident verdict. 60–180 days is ideal.</span>
                </div>
                <div style='display:flex;gap:8px;align-items:flex-start;'>
                  <span style='color:#60a5fa;font-size:13px;flex-shrink:0;'>→</span>
                  <span style='color:#777;'><b style='color:#aaa;'>Sale date</b> — set this to the day the discount was applied, not today.</span>
                </div>
                <div style='display:flex;gap:8px;align-items:flex-start;'>
                  <span style='color:#60a5fa;font-size:13px;flex-shrink:0;'>→</span>
                  <span style='color:#777;'><b style='color:#aaa;'>Claimed MRP</b> — the "original" price shown by the seller (crossed-out price).</span>
                </div>
                <div style='display:flex;gap:8px;align-items:flex-start;'>
                  <span style='color:#60a5fa;font-size:13px;flex-shrink:0;'>→</span>
                  <span style='color:#777;'><b style='color:#aaa;'>Sale price</b> — the discounted price the seller is showing right now.</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded = st.file_uploader(
            "**Upload price history CSV**",
            type=["csv"],
            help="Required columns: date, price. Optional: product_name",
        )
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
                    analyze_btn = st.button("Check this discount", use_container_width=True, type="primary")
            except Exception as e:
                st.error(f"Error parsing CSV: {e}")

    st.divider()


# ---------------------------------------------------------------------------
# Load Gemini API key from secrets (invisible to users)
# ---------------------------------------------------------------------------

try:
    _GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
except Exception:
    _GEMINI_KEY = ""


# ---------------------------------------------------------------------------
# Main area — header + results
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div style='margin-bottom:32px;'>
      <h1 style='font-size:40px;font-weight:800;letter-spacing:-1.5px;margin-bottom:8px;color:#f0f0f0;line-height:1.1;'>
        Is that discount real?</h1>
      <p style='color:#666;font-size:16px;margin:0 0 20px;max-width:560px;line-height:1.6;'>
        Paste a product, upload a price history, or try a demo — we’ll tell you if the “60% off” is genuine or manufactured.
      </p>
      <div style='display:flex;gap:8px;flex-wrap:wrap;'>
        <span style='background:#1a1a1a;border:1px solid #2a2a2a;color:#888;
                     border-radius:6px;padding:4px 14px;font-size:12px;font-weight:600;'>Price Pattern Analysis</span>
        <span style='background:#1a1a1a;border:1px solid #2a2a2a;color:#888;
                     border-radius:6px;padding:4px 14px;font-size:12px;font-weight:600;'>Anomaly Detection</span>
        <span style='background:#1a1a1a;border:1px solid #2a2a2a;color:#888;
                     border-radius:6px;padding:4px 14px;font-size:12px;font-weight:600;'>Plain-English Verdict</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

if not analyze_btn:
    # Landing state
    c1, c2, c3 = st.columns(3)
    for col, title, desc, accent in [
        (c1, "Spot the Price Spike",
         "Catches when sellers secretly raise the price before a sale, then 'discount' it back — making a fake deal look real.",
         "#58a6ff"),
        (c2, "Cross-check Against Real Products",
         "Compares pricing behaviour against hundreds of real products to catch unusual patterns that rules alone might miss.",
         "#a371f7"),
        (c3, "A Clear Answer, Not a Number",
         "You get a plain verdict — Genuine, Suspicious, or Uncertain — with a full explanation of why.",
         "#56d364"),
    ]:
        with col:
            st.markdown(
                f"""
                <div class="feature-card">
                  <div style='font-size:15px;font-weight:700;color:#f0f0f0;margin-bottom:8px;'>{title}</div>
                  <div style='font-size:13px;color:#666;line-height:1.7;'>{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown(
        """
        <div style='margin-top:28px;background:#141414;border:1px solid #242424;
                    border-radius:10px;padding:16px 22px;font-size:14px;color:#666;'>
          → <b style='color:#f0f0f0;'>How to use:</b> Pick a product (or try an example) in the sidebar,
          then click <b style='color:#f0f0f0;'>Check this discount</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

else:
    # ── Real Product mode ───────────────────────────────────────────────────
    if mode == "Real Product":
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

        st.caption(f"Auto-detected pattern: **{auto_regime.value}** — {regime_reason}")

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
            gemini_key=_GEMINI_KEY,
        )

    # ── Demo mode ──────────────────────────────────────────────────────────
    elif mode == "Try an Example":
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

        _scenario_labels = {
            "dark_pattern": "Fake Discount — price was inflated before the sale",
            "genuine_discount": "Real Discount — price genuinely dropped",
            "stable": "Cosmetic Discount — barely any real saving",
            "gradual_drift": "Gradual Drift — price slowly crept up before a 'sale'",
        }
        scenario_desc = _scenario_labels.get(series.regime.value, series.regime.value)
        gt_label = "Real deal" if series.ground_truth_genuine else "Fake deal"
        st.markdown(
            f"""
            <div style='background:#161b22;border:1px solid #30363d;border-radius:8px;
                        padding:12px 20px;margin-bottom:20px;font-size:13px;color:#8b949e;'>
              <b style='color:#c9d1d9;'>Simulated scenario:</b> {scenario_desc} &nbsp;|&nbsp;
              Listed price: <b>₹{series.claimed_original_price:.0f}</b> &nbsp;|&nbsp;
              Sale price: <b style='color:#56d364;'>₹{series.claimed_sale_price:.0f}</b> &nbsp;|&nbsp;
              Ground truth: <b>{gt_label}</b>
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
            gemini_key=_GEMINI_KEY,
        )

    # ── CSV upload mode ────────────────────────────────────────────────────
    else:
        if uploaded is None:
            st.warning("Please upload a CSV file in the sidebar.")
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
                gemini_key=_GEMINI_KEY,
            )

"""
app.py — Fake Discount Detector · Streamlit UI

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import io
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Main background */
    .stApp { background: #0d1117; color: #e6edf3; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #161b22;
        border-right: 1px solid #30363d;
    }

    /* Cards */
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
        height: 100%;
    }
    .metric-card .label {
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: #8b949e;
        margin-bottom: 8px;
    }
    .metric-card .value {
        font-size: 32px;
        font-weight: 700;
        line-height: 1;
    }

    /* Status badge */
    .badge-suspicious {
        background: linear-gradient(135deg, #ff4d4d22, #ff4d4d11);
        border: 1px solid #ff4d4d55;
        color: #ff7b7b;
    }
    .badge-genuine {
        background: linear-gradient(135deg, #3fb95022, #3fb95011);
        border: 1px solid #3fb95055;
        color: #56d364;
    }
    .badge-uncertain {
        background: linear-gradient(135deg, #f0883e22, #f0883e11);
        border: 1px solid #f0883e55;
        color: #f0883e;
    }

    /* Explanation box */
    .explanation-box {
        background: #161b22;
        border: 1px solid #30363d;
        border-left: 4px solid #58a6ff;
        border-radius: 8px;
        padding: 20px 24px;
        font-size: 14px;
        line-height: 1.8;
        white-space: pre-wrap;
        color: #c9d1d9;
    }

    /* Progress bar track */
    .score-bar-track {
        background: #21262d;
        border-radius: 99px;
        height: 10px;
        overflow: hidden;
        margin-top: 6px;
    }

    /* Section headers */
    h2 { color: #e6edf3 !important; }
    h3 { color: #c9d1d9 !important; }

    /* Divider */
    hr { border-color: #30363d; }

    /* Streamlit default overrides */
    div[data-testid="stMetric"] label { color: #8b949e !important; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
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

def score_bar_html(label: str, value: float, color: str) -> str:
    pct = int(value * 100)
    return f"""
    <div style="margin-bottom:16px;">
      <div style="display:flex;justify-content:space-between;font-size:13px;color:#8b949e;margin-bottom:4px;">
        <span style="font-weight:600;">{label}</span>
        <span style="color:#c9d1d9;font-weight:700;">{value:.2f}</span>
      </div>
      <div class="score-bar-track">
        <div style="width:{pct}%;height:100%;background:{color};border-radius:99px;
                    transition:width 0.6s ease;"></div>
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

    badge_class = {
        DiscountStatus.SUSPICIOUS: "badge-suspicious",
        DiscountStatus.GENUINE: "badge-genuine",
        DiscountStatus.UNCERTAIN: "badge-uncertain",
    }[status]

    icon = {
        DiscountStatus.SUSPICIOUS: "⚠️",
        DiscountStatus.GENUINE: "✅",
        DiscountStatus.UNCERTAIN: "❓",
    }[status]

    st.markdown(
        f"""
        <div class="metric-card {badge_class}" style="margin-bottom:20px;display:inline-block;padding:12px 32px;">
          <span style="font-size:28px;font-weight:800;letter-spacing:1px;">
            {icon} {status.value.upper()}
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        susp_color = "#ff7b7b" if result.suspicion_score > 0.55 else (
            "#56d364" if result.suspicion_score < 0.25 else "#f0883e"
        )
        st.markdown(
            score_bar_html("Suspicion Score", result.suspicion_score, susp_color),
            unsafe_allow_html=True,
        )
        st.markdown(
            score_bar_html("Confidence", result.confidence, "#58a6ff"),
            unsafe_allow_html=True,
        )

    with col2:
        vol_color = "#ff7b7b" if result.volatility_score > 0.7 else (
            "#56d364" if result.volatility_score < 0.3 else "#f0883e"
        )
        st.markdown(
            score_bar_html("Volatility Score", result.volatility_score, vol_color),
            unsafe_allow_html=True,
        )
        st.markdown(
            score_bar_html("Days History", min(1.0, features.n_days_history / 180),
                           "#a371f7"),
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
        <div style='text-align:center;padding:16px 0 24px;'>
          <div style='font-size:36px;'>🔍</div>
          <div style='font-size:18px;font-weight:700;color:#e6edf3;'>Fake Discount</div>
          <div style='font-size:18px;font-weight:700;color:#58a6ff;'>Detector</div>
          <div style='font-size:11px;color:#8b949e;margin-top:4px;'>
            Pattern-based price analysis
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    mode = st.radio(
        "**Input mode**",
        options=["Demo (synthetic)", "Upload CSV"],
        index=0,
    )

    st.divider()

    if mode == "Demo (synthetic)":
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
            help="CSV must have columns: `date`, `price`",
        )
        st.caption("Columns required: `date` (any date format), `price` (numeric)")
        st.divider()
        pid_input = st.text_input("Product ID", value="PRODUCT-001")
        orig_input = st.number_input("Claimed original price (₹)", value=1000.0, step=10.0)
        sale_input = st.number_input("Claimed sale price (₹)", value=700.0, step=10.0)
        sale_date_input = st.date_input("Sale date")
        analyze_btn = st.button("🔍 Analyse", use_container_width=True, type="primary")

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
    <h1 style='font-size:32px;font-weight:800;color:#e6edf3;margin-bottom:4px;'>
      Fake Discount Detector
    </h1>
    <p style='color:#8b949e;font-size:15px;margin-bottom:24px;'>
      Detects misleading e-commerce discounts by analyzing historical pricing patterns —
      no labels required.
    </p>
    """,
    unsafe_allow_html=True,
)

st.divider()

if not analyze_btn:
    # Landing state
    c1, c2, c3 = st.columns(3)
    for col, icon, title, desc in [
        (c1, "📊", "Pattern Recognition",
         "Detects pre-sale price spikes, short-hold 'original' prices, and cosmetic discounts."),
        (c2, "🤖", "Anomaly Cross-check",
         "Isolation Forest flags products that are statistical outliers vs a reference population."),
        (c3, "💬", "Plain-language Output",
         "Every verdict comes with an explanation you can actually read and trust."),
    ]:
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                  <div style='font-size:28px;margin-bottom:12px;'>{icon}</div>
                  <div style='font-size:15px;font-weight:600;color:#e6edf3;margin-bottom:8px;'>{title}</div>
                  <div style='font-size:13px;color:#8b949e;line-height:1.6;'>{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.info("👈 Choose an input mode in the sidebar and click **Analyse** to begin.", icon="💡")

else:
    # ── Demo mode ──────────────────────────────────────────────────────────
    if mode == "Demo (synthetic)":
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
        else:
            try:
                df = pd.read_csv(uploaded)
                if "date" not in df.columns or "price" not in df.columns:
                    st.error("CSV must contain `date` and `price` columns.")
                else:
                    run_analysis(
                        df=df,
                        orig=float(orig_input),
                        sale=float(sale_input),
                        sale_date=str(sale_date_input),
                        pid=pid_input,
                    )
            except Exception as e:
                st.error(f"Failed to read CSV: {e}")

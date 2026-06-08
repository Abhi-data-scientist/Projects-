# import streamlit as st
# import requests
# import pandas as pd

# st.set_page_config(
#     page_title="AI Product Research Agent",
#     page_icon="🔍",
#     layout="wide"
# )

# st.title("🔍 AI Product Research Agent")

# with st.form("search_form"):

#     keyword = st.text_input(
#         "Keyword",
#         placeholder="phone, water bottle, yoga mat..."
#     )

#     col1, col2 = st.columns(2)

#     with col1:
#         min_price = st.number_input(
#             "Min Price",
#             min_value=0.0,
#             value=0.0
#         )

#     with col2:
#         max_price = st.number_input(
#             "Max Price",
#             min_value=0.0,
#             value=500.0
#         )

#     num_results = st.slider(
#         "Number of Results",
#         min_value=1,
#         max_value=50,
#         value=10
#     )

#     submitted = st.form_submit_button(
#         "Search Products"
#     )

# if submitted:

#     if not keyword.strip():
#         st.error("Please enter a keyword")
#         st.stop()

#     payload = {
#         "keyword": keyword,
#         "min_price": min_price,
#         "max_price": max_price,
#         "num_results": num_results
#     }

#     try:

#         with st.spinner("Fetching products..."):

#             response = requests.post(
#                 "http://127.0.0.1:8000/search",
#                 json=payload,
#                 timeout=60
#             )

#         if response.status_code != 200:
#             st.error(f"Backend Error: {response.status_code}")
#             st.write(response.text)
#             st.stop()

#         data = response.json()

#         products = data.get("products", [])

#         if len(products) == 0:
#             st.warning("No products found")
#             st.write(data)
#             st.stop()

#         st.success(
#             f"Found {len(products)} products"
#         )

#         df = pd.DataFrame(products)

#         st.dataframe(
#             df,
#             use_container_width=True
#         )

#         csv = df.to_csv(index=False)

#         st.download_button(
#             label="📥 Download CSV",
#             data=csv,
#             file_name="products.csv",
#             mime="text/csv"
#         )

#         st.subheader("Products")

#         for product in products:

#             with st.expander(product.get("title", "Product")):

#                 st.write(
#                     f"💲 Price: {product.get('price')}"
#                 )

#                 st.write(
#                     f"⭐ Rating: {product.get('rating')}"
#                 )

#                 st.write(
#                     f"📝 Reviews: {product.get('reviews')}"
#                 )

#                 st.write(
#                     f"🏆 Score: {product.get('score')}"
#                 )

#                 if product.get("link"):
#                     st.link_button(
#                         "Open Product",
#                         product["link"]
#                     )

#     except Exception as e:
#         st.error(str(e))


import streamlit as st
import requests
import pandas as pd

# ── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Product Research Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── GLOBAL CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

/* ── ROOT & RESET ── */
:root {
    --bg: #080c10;
    --surface: #0e1318;
    --card: #131a21;
    --border: #1e2d3d;
    --accent: #00e5ff;
    --accent2: #7b61ff;
    --accent3: #ff6b35;
    --text: #e8edf2;
    --muted: #5a7080;
    --success: #00c896;
    --warn: #ffb547;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Syne', sans-serif !important;
}

/* Remove default streamlit padding */
[data-testid="stAppViewContainer"] > .main > div {
    padding-top: 2rem !important;
    padding-bottom: 4rem !important;
}

/* Hide default header & footer */
#MainMenu, footer, header { visibility: hidden !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* ── ANIMATED BACKGROUND GRID ── */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background-image:
        linear-gradient(rgba(0,229,255,.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,229,255,.025) 1px, transparent 1px);
    background-size: 44px 44px;
}

/* Glow blobs */
[data-testid="stAppViewContainer"]::after {
    content: '';
    position: fixed; top: -200px; left: -200px; z-index: 0; pointer-events: none;
    width: 600px; height: 600px; border-radius: 50%;
    background: radial-gradient(circle, rgba(123,97,255,.18) 0%, transparent 70%);
}

/* ── HEADER HERO ── */
.hero-wrap {
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 0 0 36px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 36px;
    position: relative;
}
.hero-wrap::after {
    content: '';
    position: absolute; bottom: -1px; left: 0;
    width: 220px; height: 1px;
    background: linear-gradient(90deg, var(--accent), transparent);
}
.hero-logo {
    width: 56px; height: 56px; border-radius: 16px; flex-shrink: 0;
    background: linear-gradient(135deg, var(--accent2), var(--accent));
    display: flex; align-items: center; justify-content: center;
    font-size: 1.6rem;
    box-shadow: 0 0 36px rgba(0,229,255,.28);
}
.hero-title {
    font-size: 2rem; font-weight: 800;
    letter-spacing: -.03em; line-height: 1.1;
    color: var(--text);
}
.hero-title span { color: var(--accent); }
.hero-sub {
    font-family: 'DM Mono', monospace;
    font-size: .72rem; color: var(--muted);
    letter-spacing: .1em; margin-top: 4px;
}
.hero-badge {
    margin-left: auto;
    font-family: 'DM Mono', monospace; font-size: .68rem; letter-spacing: .1em;
    color: var(--accent); border: 1px solid rgba(0,229,255,.25);
    padding: 5px 12px; border-radius: 20px;
    background: rgba(0,229,255,.06);
}

/* ── SEARCH PANEL ── */
.panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 28px 32px 32px;
    margin-bottom: 32px;
    position: relative; overflow: hidden;
}
.panel::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    opacity: .55;
}
.panel-label {
    font-family: 'DM Mono', monospace; font-size: .68rem;
    color: var(--muted); letter-spacing: .12em; text-transform: uppercase;
    margin-bottom: 20px;
}

/* ── STREAMLIT WIDGET OVERRIDES ── */

/* Text Input */
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSlider"] label {
    font-family: 'DM Mono', monospace !important;
    font-size: .68rem !important;
    color: var(--muted) !important;
    letter-spacing: .1em !important;
    text-transform: uppercase !important;
    font-weight: 400 !important;
}
[data-testid="stTextInput"] input {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    color: var(--text) !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    padding: 14px 18px !important;
    transition: border-color .2s, box-shadow .2s !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(0,229,255,.12) !important;
}
[data-testid="stTextInput"] input::placeholder { color: var(--muted) !important; font-weight: 400 !important; }

/* Number Input */
[data-testid="stNumberInput"] input {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-family: 'DM Mono', monospace !important;
    font-size: .9rem !important;
}
[data-testid="stNumberInput"] input:focus {
    border-color: var(--accent2) !important;
    box-shadow: 0 0 0 3px rgba(123,97,255,.12) !important;
}
[data-testid="stNumberInput"] button {
    background: var(--card) !important;
    border-color: var(--border) !important;
    color: var(--muted) !important;
}
[data-testid="stNumberInput"] button:hover { border-color: var(--accent) !important; color: var(--accent) !important; }

/* Slider */
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
    background: var(--accent) !important;
    border: 3px solid var(--bg) !important;
    box-shadow: 0 0 8px rgba(0,229,255,.5) !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] div[data-testid="stTickBar"] {
    display: none !important;
}

/* Form submit button */
[data-testid="stFormSubmitButton"] button,
[data-testid="baseButton-secondary"] {
    width: 100% !important;
    background: linear-gradient(135deg, var(--accent2), var(--accent)) !important;
    border: none !important;
    border-radius: 12px !important;
    color: #fff !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    letter-spacing: .04em !important;
    padding: 14px !important;
    box-shadow: 0 4px 24px rgba(0,229,255,.2) !important;
    transition: transform .15s, box-shadow .15s !important;
}
[data-testid="stFormSubmitButton"] button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 32px rgba(0,229,255,.32) !important;
}

/* Download button */
[data-testid="stDownloadButton"] button {
    background: transparent !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-family: 'Syne', sans-serif !important;
    font-size: .82rem !important;
    font-weight: 600 !important;
    transition: border-color .15s, color .15s !important;
}
[data-testid="stDownloadButton"] button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background: rgba(0,229,255,.06) !important;
}

/* Status / alerts */
[data-testid="stAlert"] {
    border-radius: 12px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    font-size: .9rem !important;
}

/* Expander */
[data-testid="stExpander"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    transition: border-color .2s !important;
}
[data-testid="stExpander"]:hover { border-color: rgba(0,229,255,.3) !important; }
[data-testid="stExpander"] summary {
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: .92rem !important;
    color: var(--text) !important;
    padding: 14px 18px !important;
}
[data-testid="stExpander"] > div > div {
    background: var(--card) !important;
    border-top: 1px solid var(--border) !important;
    padding: 16px 18px !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    overflow: hidden !important;
}

/* Spinner */
[data-testid="stSpinner"] p {
    font-family: 'DM Mono', monospace !important;
    color: var(--accent) !important;
    font-size: .8rem !important;
    letter-spacing: .08em !important;
}

/* Divider */
hr { border-color: var(--border) !important; }

/* Link button */
[data-testid="stLinkButton"] a {
    background: transparent !important;
    border: 1px solid rgba(0,229,255,.25) !important;
    border-radius: 10px !important;
    color: var(--accent) !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: .82rem !important;
    transition: background .15s !important;
}
[data-testid="stLinkButton"] a:hover { background: rgba(0,229,255,.08) !important; }

/* Metric */
[data-testid="stMetric"] {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 18px 20px;
}
[data-testid="stMetricLabel"] {
    font-family: 'DM Mono', monospace !important;
    font-size: .65rem !important;
    color: var(--muted) !important;
    letter-spacing: .1em !important;
    text-transform: uppercase !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif !important;
    font-size: 1.6rem !important;
    font-weight: 800 !important;
    color: var(--accent) !important;
}
[data-testid="stMetricDelta"] { font-family: 'DM Mono', monospace !important; }

/* Columns gap */
[data-testid="stHorizontalBlock"] { gap: 16px !important; }

/* Success/info/error colors */
div[data-baseweb="notification"] { border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)


# ── HERO HEADER ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-wrap">
    <div class="hero-logo">🔍</div>
    <div>
        <div class="hero-title">Product <span>Research</span> Agent</div>
        <div class="hero-sub">// powered by ebay finding api + rule-based scoring</div>
    </div>
    <div class="hero-badge">AI-POWERED</div>
</div>
""", unsafe_allow_html=True)


# ── SEARCH PANEL ─────────────────────────────────────────────────────────────

with st.form("search_form"):
    keyword = st.text_input("Keyword", placeholder="phone, water bottle, yoga mat...")

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        min_price = st.number_input("Min Price ($)", min_value=0.0, value=0.0, step=1.0)
    with col2:
        max_price = st.number_input("Max Price ($)", min_value=0.0, value=500.0, step=1.0)
    with col3:
        num_results = st.slider("Number of Results", min_value=1, max_value=50, value=10)

    submitted = st.form_submit_button("🔍  Search Products")

st.markdown('</div>', unsafe_allow_html=True)


# ── SEARCH LOGIC ──────────────────────────────────────────────────────────────
if submitted:

    if not keyword.strip():
        st.error("⚠  Please enter a keyword to search.")
        st.stop()

    payload = {
        "keyword": keyword,
        "min_price": min_price,
        "max_price": max_price,
        "num_results": num_results
    }

    try:
        with st.spinner("⟳  Fetching products from backend…"):
            response = requests.post(
                "http://127.0.0.1:8000/search",
                json=payload,
                timeout=60
            )

        if response.status_code != 200:
            st.error(f"⚠  Backend error {response.status_code}: {response.text}")
            st.stop()

        data = response.json()
        products = data.get("products", [])

        if not products:
            st.warning("📦  No products found. Try a different keyword or adjust your filters.")
            st.stop()

        # ── METRICS ROW ──────────────────────────────────────────────────────
        df = pd.DataFrame(products)

        avg_price = df["price"].mean() if "price" in df.columns else None
        avg_rating = df["rating"].mean() if "rating" in df.columns else None
        top_score = df["score"].max() if "score" in df.columns else None

        st.markdown("<br>", unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)

        with m1:
            st.metric("Products Found", len(products))
        with m2:
            st.metric("Avg Price", f"${avg_price:.2f}" if avg_price is not None else "—")
        with m3:
            st.metric("Avg Rating", f"⭐ {avg_rating:.1f}" if avg_rating is not None else "—")
        with m4:
            st.metric("Top Score", f"{top_score:.1f}" if top_score is not None else "—")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── ACTIONS ROW ──────────────────────────────────────────────────────
        ac1, ac2 = st.columns([6, 1])
        with ac1:
            st.success(f"✓  Found **{len(products)}** products for **\"{keyword}\"**")
        with ac2:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 CSV",
                data=csv,
                file_name=f"{keyword.replace(' ','_')}_products.csv",
                mime="text/csv",
                use_container_width=True,
            )

        # ── DATAFRAME ────────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p style="font-family:\'DM Mono\',monospace;font-size:.68rem;color:#5a7080;letter-spacing:.12em;text-transform:uppercase;margin-bottom:10px">// raw data</p>', unsafe_allow_html=True)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        # ── PRODUCT CARDS ─────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p style="font-family:\'DM Mono\',monospace;font-size:.68rem;color:#5a7080;letter-spacing:.12em;text-transform:uppercase;margin-bottom:10px">// product details</p>', unsafe_allow_html=True)

        max_score = max((p.get("score") or 0) for p in products) or 1

        for i, product in enumerate(products):
            title = product.get("title", "Unknown Product")
            price = product.get("price")
            rating = product.get("rating")
            reviews = product.get("reviews")
            score = product.get("score")
            link = product.get("link")

            score_pct = int(((score or 0) / max_score) * 100)
            score_bar_color = (
                "#00c896" if score_pct >= 70
                else "#ffb547" if score_pct >= 40
                else "#ff6b35"
            )

            with st.expander(f"#{i+1}  {title}"):

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.markdown(f"""
                    <div style="background:#131a21;border:1px solid rgba(0,200,150,.2);border-radius:10px;padding:12px 16px;text-align:center">
                        <div style="font-family:'DM Mono',monospace;font-size:.6rem;color:#5a7080;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px">Price</div>
                        <div style="font-size:1.15rem;font-weight:700;color:#00c896">{"$"+str(price) if price is not None else "—"}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""
                    <div style="background:#131a21;border:1px solid rgba(255,181,71,.2);border-radius:10px;padding:12px 16px;text-align:center">
                        <div style="font-family:'DM Mono',monospace;font-size:.6rem;color:#5a7080;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px">Rating</div>
                        <div style="font-size:1.15rem;font-weight:700;color:#ffb547">{"⭐ "+str(rating) if rating is not None else "—"}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with c3:
                    st.markdown(f"""
                    <div style="background:#131a21;border:1px solid rgba(123,97,255,.2);border-radius:10px;padding:12px 16px;text-align:center">
                        <div style="font-family:'DM Mono',monospace;font-size:.6rem;color:#5a7080;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px">Reviews</div>
                        <div style="font-size:1.15rem;font-weight:700;color:#7b61ff">{"💬 "+str(reviews) if reviews is not None else "—"}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with c4:
                    st.markdown(f"""
                    <div style="background:#131a21;border:1px solid rgba(0,229,255,.2);border-radius:10px;padding:12px 16px;text-align:center">
                        <div style="font-family:'DM Mono',monospace;font-size:.6rem;color:#5a7080;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px">AI Score</div>
                        <div style="font-size:1.15rem;font-weight:700;color:#00e5ff">{str(score) if score is not None else "—"}</div>
                    </div>
                    """, unsafe_allow_html=True)

                # Score bar
                st.markdown(f"""
                <div style="margin-top:14px">
                    <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                        <span style="font-family:'DM Mono',monospace;font-size:.62rem;color:#5a7080;letter-spacing:.08em;text-transform:uppercase">Score Percentile</span>
                        <span style="font-family:'DM Mono',monospace;font-size:.72rem;color:{score_bar_color}">{score_pct}%</span>
                    </div>
                    <div style="height:6px;background:#1e2d3d;border-radius:4px;overflow:hidden">
                        <div style="height:100%;width:{score_pct}%;background:linear-gradient(90deg,{score_bar_color}88,{score_bar_color});border-radius:4px;transition:width .8s"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                if link:
                    st.link_button("View Product →", link, use_container_width=True)

    except requests.exceptions.ConnectionError:
        st.error("⚠  Cannot connect to backend. Make sure FastAPI is running at `http://127.0.0.1:8000`")
    except Exception as e:
        st.error(f"⚠  Error: {str(e)}")
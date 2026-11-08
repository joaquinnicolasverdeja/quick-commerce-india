import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ===========================================================================
# SINGLE DATA ENTRY POINT
# ---------------------------------------------------------------------------
# This app only visualizes. Cleaned data is produced by the R pipeline in r/
# (01_clean_segment.R). Path is relative to the project root.
# ===========================================================================
DATA_PATH = 'data/clean/segmented_data.csv'

# ===========================================================================
# 1. PAGE CONFIG
# ===========================================================================
st.set_page_config(page_title="Q-Commerce Tracker — Measuring Instant Delivery Market Performance", layout="wide")

# ===========================================================================
# 2. DATA LOADING
# ===========================================================================
@st.cache_data
def load_data():
    # Reads the cleaned dataset defined in DATA_PATH (top of the file)
    df = pd.read_csv(DATA_PATH)
    return df

df_raw = load_data()

# ===========================================================================
# 3. PREPARATION FOR VISUALIZATION
# ===========================================================================
# Display-only transformations (labels, ordering, groupings). Data cleaning
# (city normalization, invalid income filter) is done in the R pipeline.

# --- 3.1 Age → Generation mapping ---
def map_generation(age):
    if age in ['18-24']:
        return 'Gen Z\n(18–24)'
    elif age in ['25-34']:
        return 'Millennials\n(25–34)'
    else:
        return 'Gen X\n(55+)'

df_raw['Generation'] = df_raw['Age'].apply(map_generation)

# --- 3.2 Income ordering ---
INCOME_ORDER = ['0-15000', '15001-25000', '25001-40000', '40001-60000',
                '60001-85000', '85001-100000', '100000+', '200000+']
INCOME_LABELS = ['₹0–15K', '₹15K–25K', '₹25K–40K', '₹40K–60K',
                 '₹60K–85K', '₹85K–1L', '+₹1L', '+₹2L']
INCOME_MAP = dict(zip(INCOME_ORDER, INCOME_LABELS))

HH_ORDER = ['Less than 1 Lakh', 'Between 1Lakh - 2Lakh',
            'Between 2 Lakh - 4 Lakh', 'More than 4 Lakh']
HH_LABELS = ['< ₹1 Lakh', '₹1L – ₹2L', '₹2L – ₹4L', '+₹4 Lakh']
HH_MAP = dict(zip(HH_ORDER, HH_LABELS))

df_raw['Income_Label']    = df_raw['Please state your monthly income.'].map(INCOME_MAP)
df_raw['HH_Income_Label'] = df_raw['Monthly Household Income'].map(HH_MAP)

# --- 3.3 Motivation to Switch ---
MOTIVATION_MAP = {
    'Better pricing and discounts':                      'Better Pricing & Discounts',
    'More extensive product selection':                  'More Extensive Product Selection',
    'Faster and more reliable delivery':                 'Faster & More Reliable Delivery',
    'Exclusive membership benefits or loyalty programs': 'Membership, Benefits & Loyalty',
    'Improved user experience and app interface':        'Improved UX & App Interface',
    "Trust in Flipkart's brand reputation":              "Trust in Flipkart's Brand",
    'Enhanced customer service':                         'Enhanced Customer Service',
    'Better payment options and flexibility':            'Better Payment Options',
    'Dont know yet':                                     "Don't Know Yet",
    'Not used yet':                                      "Don't Know Yet",
}

def normalize_motivation(val):
    val = str(val).strip()
    return MOTIVATION_MAP.get(val, 'Other')

# ===========================================================================
# 4. SEGMENT CONFIG & SIDEBAR
# ===========================================================================
SEGMENT_COLORS = {
    'Diamond Segment (Q4)': '#0ECECE',
    'Gold Segment (Q3)':    '#FFD700',
    'Silver Segment (Q2)':  '#A8A9AD',
    'Bronze Segment (Q1)':  '#FFFFFF',
}

SEGMENT_INFO = {
    'Diamond Segment (Q4)': {'tag': 'Q4', 'color': '#0ECECE', 'rev': '20,389'},
    'Gold Segment (Q3)':    {'tag': 'Q3', 'color': '#FFD700', 'rev': '2,327'},
    'Silver Segment (Q2)':  {'tag': 'Q2', 'color': '#A8A9AD', 'rev': '839'},
    'Bronze Segment (Q1)':  {'tag': 'Q1', 'color': '#FFFFFF', 'rev': '256'},
}

st.sidebar.header("Customer Segmentation Filter")

selected_segments = st.sidebar.multiselect(
    "Select Segment(s):",
    options=list(SEGMENT_COLORS.keys()),
    default=['Diamond Segment (Q4)']
)

if not selected_segments:
    st.warning("Please select at least one segment.")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.markdown("### Segment Legend")
for s, info in SEGMENT_INFO.items():
    border = "border: 0.5px solid #ccc;" if info['color'] == '#FFFFFF' else ""
    st.sidebar.markdown(
        f"<span style='background-color:{info['color']}; color:#000000; "
        f"padding: 2px 8px; border-radius: 4px; font-size:12px; font-weight:600; {border}'>"
        f"{info['tag']}</span> &nbsp; **{s}**",
        unsafe_allow_html=True
    )
    st.sidebar.markdown(f"Avg. Monthly Revenue: **₹{info['rev']}**")

filtered_df = df_raw[df_raw['Segment'].isin(selected_segments)].copy()

# ===========================================================================
# 5. HELPER FUNCTIONS
# ===========================================================================

def pct_bar_data(df_filt, col, segment_col='Segment'):
    rows = []
    for seg in selected_segments:
        sub = df_filt[df_filt[segment_col] == seg]
        counts = sub[col].value_counts(normalize=True) * 100
        for cat, pct in counts.items():
            rows.append({'Category': cat, '%': pct, 'Segment': seg})
    return pd.DataFrame(rows)

def pct_bar_data_ordered(df_filt, col, order, label_map=None, segment_col='Segment'):
    rows = []
    for seg in selected_segments:
        sub = df_filt[df_filt[segment_col] == seg]
        counts = sub[col].value_counts(normalize=True) * 100
        for cat in order:
            label = label_map[cat] if label_map and cat in label_map else cat
            rows.append({'Category': label, '%': counts.get(cat, 0), 'Segment': seg})
    return pd.DataFrame(rows)

def exploded_pct_data(df_filt, col, segment_col='Segment'):
    rows = []
    for seg in selected_segments:
        sub = df_filt[df_filt[segment_col] == seg]
        exploded = sub[col].dropna().astype(str).str.split(', ').explode()
        # TODO: this filter (drops numeric values or values shorter than
        # 3 characters) is cleaning, not visualization. Consider moving it
        # to the R pipeline.
        exploded = exploded[~exploded.str.isnumeric() & (exploded.str.len() >= 3)]
        counts = exploded.value_counts(normalize=True) * 100
        for cat, pct in counts.items():
            rows.append({'Category': cat, '%': pct, 'Segment': seg})
    return pd.DataFrame(rows)

def make_hbar(data, title, x='%', y='Category', color='Segment'):
    """Horizontal grouped bar chart — fixed 0–100% scale in steps of 20."""
    fig = go.Figure()
    for seg in selected_segments:
        seg_data = data[data['Segment'] == seg]
        fig.add_trace(go.Bar(
            x=seg_data[x].tolist(),
            y=seg_data[y].tolist(),
            name=seg,
            orientation='h',
            marker_color=SEGMENT_COLORS.get(seg, '#888888'),
            showlegend=False,
        ))
    # Invisible bar to force the scale up to 100%
    fig.add_trace(go.Bar(
        x=[100],
        y=[data[y].iloc[0]],
        orientation='h',
        marker_color='rgba(0,0,0,0)',
        showlegend=False,
        hoverinfo='skip',
    ))
    fig.update_layout(
        title=title,
        barmode='group',
        showlegend=False,
        xaxis=dict(
            tickmode='array',
            tickvals=[0, 20, 40, 60, 80, 100],
            ticktext=['0%', '20%', '40%', '60%', '80%', '100%'],
            title=''
        ),
        yaxis=dict(title='', automargin=True)
    )
    return fig

def make_vbar(data, title, x='Category', y='%', color='Segment'):
    """Vertical grouped bar chart — fixed 0–100% scale in steps of 20."""
    fig = px.bar(
        data, x=x, y=y, color=color, barmode='group',
        title=title,
        color_discrete_map=SEGMENT_COLORS,
        category_orders={color: selected_segments}
    )
    fig.update_yaxes(
        autorange=False,
        range=[0, 100],
        tickmode='array',
        tickvals=[0, 20, 40, 60, 80, 100],
        ticktext=['0%', '20%', '40%', '60%', '80%', '100%'],
        title=''
    )
    fig.update_xaxes(title='')
    fig.update_layout(legend_title_text='Segment', showlegend=False)
    return fig

# ===========================================================================
# 6. MAIN DASHBOARD
# ===========================================================================
st.title("Q-Commerce Tracker — Measuring Instant Delivery Market Performance")
segs_str = ", ".join(selected_segments)
st.markdown(f"Currently viewing: **{segs_str}**")

# ---------------------------------------------------------------------------
# MODULE 1: WHO IS THE CUSTOMER?
# ---------------------------------------------------------------------------
st.header("MODULE 1: Who is the customer?")
st.subheader("Section 1: Buyer Persona Profile")

c1, c2 = st.columns(2)

# Graph 1.1 — Gender Distribution
with c1:
    g_data = pct_bar_data(filtered_df, 'Gender')
    fig_gender = make_vbar(g_data, "Gender Distribution")
    fig_gender.update_xaxes(tickangle=0)
    st.plotly_chart(fig_gender, use_container_width=True)

# Graph 1.2 — Age & Generation Distribution
with c2:
    gen_order = ['Gen Z\n(18–24)', 'Millennials\n(25–34)', 'Gen X\n(55+)']
    gen_data = pct_bar_data(filtered_df, 'Generation')
    gen_data['Category'] = pd.Categorical(gen_data['Category'], categories=gen_order, ordered=True)
    gen_data = gen_data.sort_values('Category')
    fig_gen = make_vbar(gen_data, "Age & Generation Distribution")
    fig_gen.update_xaxes(tickangle=0)
    st.plotly_chart(fig_gen, use_container_width=True)

# Graph 1.3 — Current Residence City (horizontal, full width)
city_data = pct_bar_data(filtered_df, 'Current Residence City')
fig_city = make_hbar(city_data, "Current Residence City")
fig_city.update_yaxes(categoryorder='total ascending')
st.plotly_chart(fig_city, use_container_width=True)

c3, c4 = st.columns(2)

# Graph 1.4 — Accommodation Status
with c3:
    acc_data = pct_bar_data(filtered_df, 'Status of your accommodation in your Current City')
    fig_acc = make_vbar(acc_data, "Accommodation Status")
    fig_acc.update_xaxes(tickangle=0)
    st.plotly_chart(fig_acc, use_container_width=True)

# Graph 1.5 — Occupation
with c4:
    OCC_MAP = {
        'Business Owner': 'Business Owner',
        'Freelancing':    'Freelance',
        'Student':        'Student',
        'Employed':       'Employed',
    }
    filtered_df['Occupation_Label'] = filtered_df['Occupation'].map(OCC_MAP).fillna(filtered_df['Occupation'])
    all_occ = ['Student', 'Employed', 'Freelance', 'Business Owner']
    occ_rows = []
    for seg in selected_segments:
        sub = filtered_df[filtered_df['Segment'] == seg]
        counts = sub['Occupation_Label'].value_counts(normalize=True) * 100
        for occ in all_occ:
            occ_rows.append({'Category': occ, '%': counts.get(occ, 0), 'Segment': seg})
    occ_data = pd.DataFrame(occ_rows)
    fig_occ = make_vbar(occ_data, "Occupation")
    fig_occ.update_xaxes(tickangle=0, categoryorder='array', categoryarray=all_occ)
    st.plotly_chart(fig_occ, use_container_width=True)

st.markdown("---")

# --- Section 2: Socioeconomic Profile ---
st.subheader("Section 2: Socioeconomic Profile")

# Graph 2.1 — Personal Monthly Income (full width)
inc_data = pct_bar_data_ordered(
    filtered_df,
    'Please state your monthly income.',
    order=INCOME_ORDER,
    label_map=INCOME_MAP
)
fig_inc = make_hbar(inc_data, "Personal Monthly Income")
st.plotly_chart(fig_inc, use_container_width=True)

# Graph 2.2 — Household Income (full width)
hh_data = pct_bar_data_ordered(
    filtered_df,
    'Monthly Household Income',
    order=HH_ORDER,
    label_map=HH_MAP
)
fig_hh = make_hbar(hh_data, "Monthly Household Income")
fig_hh.add_annotation(
    text="Scale: 0–100%",
    xref="paper", yref="paper",
    x=1, y=1.05,
    showarrow=False,
    font=dict(size=11, color="gray")
)
st.plotly_chart(fig_hh, use_container_width=True)

# Graph 2.3 & 2.4 — Relationship Status + Loved Ones (shared width)
c_rel, c_love = st.columns(2)

# Graph 2.3 — Relationship Status
with c_rel:
    rel_data = pct_bar_data(filtered_df, 'Your current relationship status')
    fig_rel = make_vbar(rel_data, "Relationship Status")
    fig_rel.update_xaxes(tickangle=0)
    st.plotly_chart(fig_rel, use_container_width=True)

# Graph 2.4 — Loved ones in other cities
with c_love:
    love_data = pct_bar_data(filtered_df, 'Do you have loved ones in different city?')
    fig_love = make_vbar(love_data, "Do loved ones live in other cities?")
    fig_love.update_xaxes(tickangle=0)
    st.plotly_chart(fig_love, use_container_width=True)

# ---------------------------------------------------------------------------
# MODULE 2: ORDER TRENDS
# ---------------------------------------------------------------------------
st.header("MODULE 2: Order Trends")

# Graph 3.1 — Most Ordered Product Categories (vertical, full width)
PROD_MAP = {
    'Snacks & beverages':                  'Snacks &\nBeverages',
    'Packaged food items':                 'Packaged\nFood Items',
    'Household essentials':                'Household\nEssentials',
    'Personal care products':              'Personal Care\nProducts',
    'Fresh produce (fruits & vegetables)': 'Fruits &\nVegetables',
    'Dairy products':                      'Dairy\nProducts',
    'Medicines':                           'Medicines',
}

prod_data = exploded_pct_data(
    filtered_df,
    'What type of products do you typically order through quick commerce platforms?'
)
prod_data = prod_data[prod_data['Category'].isin(PROD_MAP.keys())]
prod_data['Category'] = prod_data['Category'].map(PROD_MAP)
fig_prod = make_vbar(prod_data, "Most Ordered Product Categories")
fig_prod.update_xaxes(tickangle=0)
st.plotly_chart(fig_prod, use_container_width=True)

# Graph 3.2 — Expected Delivery Time (full width)
DELIVERY_ORDER = [
    '5-10 minutes', '10-20 minutes', '20-30 minutes',
    '30-60 minutes', 'Over 1 hour'
]
del_col = 'What delivery time frame do you expect from a quick commerce platform?'
present_del = [v for v in DELIVERY_ORDER if v in filtered_df[del_col].values]
del_data = pct_bar_data_ordered(filtered_df, del_col, order=present_del)
fig_del = make_vbar(del_data, "Expected Delivery Time")
fig_del.update_xaxes(categoryorder='array', categoryarray=present_del, tickangle=0)
st.plotly_chart(fig_del, use_container_width=True)

# Graph 3.3 — Time of Day (Line chart, full width)
TOD_ORDER = ['Morning', 'Afternoon', 'Evening', 'Night', 'Late Night/Early Morning']
tod_col = 'At what time of the day generally do you order?'
tod_rows = []
for seg in selected_segments:
    sub = filtered_df[filtered_df['Segment'] == seg]
    counts = sub[tod_col].value_counts(normalize=True) * 100
    for tod in TOD_ORDER:
        tod_rows.append({'Time of Day': tod, '%': counts.get(tod, 0), 'Segment': seg})
tod_data = pd.DataFrame(tod_rows)

fig_tod = px.line(
    tod_data, x='Time of Day', y='%', color='Segment',
    markers=True, title="Ordering Time of Day",
    color_discrete_map=SEGMENT_COLORS,
    category_orders={'Segment': selected_segments, 'Time of Day': TOD_ORDER}
)
fig_tod.update_yaxes(
    range=[0, 100],
    tickvals=[0, 20, 40, 60, 80, 100],
    ticktext=['0%', '20%', '40%', '60%', '80%', '100%'],
    title=''
)
fig_tod.update_xaxes(title='', tickangle=0)
fig_tod.update_layout(legend_title_text='Segment')
st.plotly_chart(fig_tod, use_container_width=True)

# ---------------------------------------------------------------------------
# MODULE 3: WHAT DOES THE CUSTOMER VALUE?
# ---------------------------------------------------------------------------
st.header("MODULE 3: What does the customer value?")

# Graph 4.1 — What do our clients value? (full width)
FACTOR_LABELS = {
    'Delivery speed':             'Delivery\nSpeed',
    'Price':                      'Price',
    'Discounts/Offers':           'Discounts\n& Offers',
    'Product variety':            'Product\nVariety',
    'User interface/ease of use': 'User\nInterface',
    'Customer service':           'Customer\nService',
    'Return policy':              'Return\nPolicy',
    'Payment options':            'Payment\nOptions',
    'Product Quality':            'Product\nQuality',
}

factor_data = exploded_pct_data(
    filtered_df,
    'What factors influence your choice of a quick commerce platform?'
)
factor_data['Category'] = factor_data['Category'].map(FACTOR_LABELS).fillna(factor_data['Category'])
fig_factor = make_vbar(factor_data, "What do our clients value?")
fig_factor.update_yaxes(
    range=[0, 100],
    tickvals=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
    ticktext=['0%','10%','20%','30%','40%','50%','60%','70%','80%','90%','100%']
)
fig_factor.update_xaxes(tickangle=0)
st.plotly_chart(fig_factor, use_container_width=True)

# Graph 4.2 & 4.3 — Importance of Discounts + Live Product Feed (shared width)
c11, c12 = st.columns(2)

# Graph 4.2 — Importance of Discounts (Likert)
with c11:
    LIKERT_ORDER = [
        'Slightly important',
        'Moderately important',
        'Very important',
        'Extremely important',
    ]
    LIKERT_LABELS = {
        'Slightly important':   'Slightly\nImportant',
        'Moderately important': 'Moderately\nImportant',
        'Very important':       'Very\nImportant',
        'Extremely important':  'Extremely\nImportant',
    }
    likert_col = 'How important are discounts and offers in your decision to use a quick commerce platform?'
    likert_data = pct_bar_data_ordered(filtered_df, likert_col, order=LIKERT_ORDER, label_map=LIKERT_LABELS)
    likert_display_order = list(LIKERT_LABELS.values())
    fig_lik = make_vbar(likert_data, "Importance of Discounts")
    fig_lik.update_xaxes(categoryorder='array', categoryarray=likert_display_order, tickangle=0)
    fig_lik.update_layout(bargap=0.55, bargroupgap=0.1)
    st.plotly_chart(fig_lik, use_container_width=True)

# Graph 4.3 — Live Feed for Fresh & Perishables
with c12:
    live_col = 'Would you prefer if you have a live product feed (a short video of the product) for fruits, vegetables and other perishables on quick commerce platform?'
    live_data = pct_bar_data(filtered_df, live_col)
    fig_live = make_vbar(live_data, "Live Feed for Fresh & Perishables")
    fig_live.update_xaxes(tickangle=0)
    st.plotly_chart(fig_live, use_container_width=True)

# Graph 4.4 — Key Switching Factors (horizontal, full width)
MOTIVATION_DISPLAY = {
    'Better Pricing & Discounts':       'Better Pricing\n& Discounts',
    'More Extensive Product Selection': 'More Extensive\nProduct Selection',
    'Faster & More Reliable Delivery':  'Faster & More\nReliable Delivery',
    'Membership, Benefits & Loyalty':   'Membership\n& Loyalty',
    'Improved UX & App Interface':      'Improved UX\n& App Interface',
    "Trust in Flipkart's Brand":        "Trust in\nFlipkart's Brand",
    'Enhanced Customer Service':        'Enhanced\nCustomer Service',
    'Better Payment Options':           'Better Payment\nOptions',
}

mot_col = 'What would motivate you to switch from your current quick commerce platform to Flipkart?'
mot_rows = []
for seg in selected_segments:
    sub = filtered_df[filtered_df['Segment'] == seg]
    exploded = sub[mot_col].dropna().astype(str).str.split(', ').explode().str.strip()
    exploded = exploded.map(normalize_motivation)
    exploded = exploded[~exploded.isin(['Other', "Don't Know Yet"])]
    counts = exploded.value_counts(normalize=True) * 100
    for cat, pct in counts.items():
        display_label = MOTIVATION_DISPLAY.get(cat, cat)
        mot_rows.append({'Category': display_label, '%': pct, 'Segment': seg})

mot_data = pd.DataFrame(mot_rows)
fig_mot = make_hbar(mot_data, "Key Switching Factors")
fig_mot.update_yaxes(categoryorder='total ascending')
st.plotly_chart(fig_mot, use_container_width=True)

# Graph 4.5 — Strategic Suggestions (full width)
NLP_KEYWORDS = {
    'Pricing & Discounts':          ['discount', 'offer', 'price', 'pricing', 'cheaper', 'coupon', 'value'],
    'Delivery Speed & Cost':        ['delivery', 'fast', 'quick', 'early', 'free', 'speed', 'time'],
    'Product Range & Availability': ['product', 'range', 'variety', 'availability', 'stock', 'packs'],
    'Geographic Expansion':         ['location', 'city', 'expand', 'area', 'cover'],
    'UX & App Interface':           ['app', 'ui', 'interface', 'user', 'friendly', 'platform'],
    'Quality & Trust':              ['quality', 'trust', 'vendor', 'experience', 'reliable', 'service'],
}

NLP_DISPLAY = {
    'Pricing & Discounts':          'Pricing &\nDiscounts',
    'Delivery Speed & Cost':        'Delivery Speed\n& Cost',
    'Product Range & Availability': 'Product Range\n& Availability',
    'Geographic Expansion':         'Geographic\nExpansion',
    'UX & App Interface':           'UX & App\nInterface',
    'Quality & Trust':              'Quality\n& Trust',
}

def categorize_feedback(text):
    # TODO: this filter (drops empty, numeric or shorter-than-3-character
    # answers) is cleaning, not visualization. Consider moving it to the
    # R pipeline.
    if pd.isna(text) or str(text).replace('.', '').isnumeric() or len(str(text)) < 3:
        return []
    text = str(text).lower()
    return [cat for cat, keywords in NLP_KEYWORDS.items() if any(w in text for w in keywords)]

nlp_col = 'What would you suggest Flipkart do to become your preferred quick commerce platform?'
nlp_rows = []
for seg in selected_segments:
    sub = filtered_df[filtered_df['Segment'] == seg]
    cats = sub[nlp_col].apply(categorize_feedback).explode().dropna()
    if not cats.empty:
        counts = cats.value_counts(normalize=True) * 100
        for cat, pct in counts.items():
            display_label = NLP_DISPLAY.get(cat, cat)
            nlp_rows.append({'Category': display_label, '%': pct, 'Segment': seg})

if nlp_rows:
    nlp_data = pd.DataFrame(nlp_rows)
    fig_nlp = make_vbar(nlp_data, "Strategic Suggestions")
    fig_nlp.update_xaxes(tickangle=0)
    st.plotly_chart(fig_nlp, use_container_width=True)
else:
    st.info("No suggestion data available for the selected segment(s).")

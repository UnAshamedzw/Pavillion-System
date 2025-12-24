"""
table_styles.py - Enhanced Table Styling and Currency Formatting
Provides consistent, professional table displays throughout the system
"""

import streamlit as st
import pandas as pd


# =============================================================================
# GLOBAL STYLES - Call this once at app startup
# =============================================================================

def apply_global_styles():
    """Apply global CSS styles for tables and metrics throughout the app"""
    st.markdown("""
    <style>
    /* ===== DATAFRAME STYLING ===== */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 12px rgba(0,0,0,0.1);
    }
    
    .stDataFrame [data-testid="stDataFrameResizable"] {
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Header styling */
    .stDataFrame thead tr th {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 12px 15px !important;
        text-transform: uppercase;
        font-size: 12px;
        letter-spacing: 0.5px;
    }
    
    /* Row styling */
    .stDataFrame tbody tr {
        transition: background-color 0.2s ease;
    }
    
    .stDataFrame tbody tr:hover {
        background-color: #e3f2fd !important;
    }
    
    .stDataFrame tbody tr:nth-child(even) {
        background-color: #f8f9fa;
    }
    
    /* Cell styling */
    .stDataFrame tbody td {
        padding: 10px 15px !important;
        border-bottom: 1px solid #e9ecef !important;
        font-size: 14px;
    }
    
    /* ===== METRIC CARDS ===== */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 15px 20px;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    [data-testid="metric-container"] label {
        color: rgba(255,255,255,0.9) !important;
        font-size: 14px !important;
    }
    
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: white !important;
        font-weight: 700 !important;
    }
    
    [data-testid="metric-container"] [data-testid="stMetricDelta"] {
        color: rgba(255,255,255,0.85) !important;
    }
    
    /* Different metric colors */
    [data-testid="metric-container"]:nth-of-type(4n+1) {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3);
    }
    
    [data-testid="metric-container"]:nth-of-type(4n+2) {
        background: linear-gradient(135deg, #fc4a1a 0%, #f7b733 100%);
        box-shadow: 0 4px 15px rgba(252, 74, 26, 0.3);
    }
    
    [data-testid="metric-container"]:nth-of-type(4n+3) {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        box-shadow: 0 4px 15px rgba(79, 172, 254, 0.3);
    }
    
    /* ===== EXPANDER STYLING ===== */
    .streamlit-expanderHeader {
        background-color: #f8f9fa;
        border-radius: 8px;
        font-weight: 600;
    }
    
    .streamlit-expanderHeader:hover {
        background-color: #e9ecef;
    }
    
    /* ===== TAB STYLING ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 5px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #1e3a5f !important;
        color: white !important;
    }
    
    /* ===== BUTTON STYLING ===== */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
    }
    
    /* ===== FORM STYLING ===== */
    .stForm {
        background-color: #f8f9fa;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e9ecef;
    }
    </style>
    """, unsafe_allow_html=True)


# =============================================================================
# CURRENCY FORMATTING
# =============================================================================

def format_currency(value, currency='USD', show_symbol=True):
    """Format a number as currency with proper symbol and commas"""
    try:
        num = float(value) if value is not None else 0
    except (ValueError, TypeError):
        num = 0
    
    if show_symbol:
        if currency == 'ZiG':
            return f"ZiG {num:,.2f}"
        else:
            return f"${num:,.2f}"
    else:
        return f"{num:,.2f}"


def format_number(value, decimals=0):
    """Format a number with thousand separators"""
    try:
        num = float(value) if value is not None else 0
        if decimals == 0:
            return f"{int(num):,}"
        return f"{num:,.{decimals}f}"
    except (ValueError, TypeError):
        return "0"


def format_percentage(value, decimals=1):
    """Format a number as percentage"""
    try:
        num = float(value) if value is not None else 0
        return f"{num:,.{decimals}f}%"
    except (ValueError, TypeError):
        return "0%"


# =============================================================================
# DATAFRAME FORMATTING
# =============================================================================

def style_dataframe(df, currency_cols=None, number_cols=None, pct_cols=None, date_cols=None):
    """
    Format a dataframe for display with proper currency, number, and percentage formatting.
    Returns a new dataframe with formatted string values.
    """
    if df.empty:
        return df
    
    styled_df = df.copy()
    
    # Auto-detect currency columns if not specified
    if currency_cols is None:
        currency_cols = []
        currency_keywords = ['amount', 'revenue', 'cost', 'price', 'salary', 'pay', 'total', 
                            'gross', 'net', 'deduction', 'commission', 'bonus', 'expense',
                            'income', 'profit', 'loss', 'balance', 'fee', 'wage']
        for col in styled_df.columns:
            col_lower = col.lower().replace('_', ' ')
            if any(kw in col_lower for kw in currency_keywords):
                currency_cols.append(col)
    
    # Auto-detect number columns
    if number_cols is None:
        number_cols = []
        number_keywords = ['count', 'trips', 'passengers', 'quantity', 'qty', 'number', 'num', 'days']
        for col in styled_df.columns:
            col_lower = col.lower().replace('_', ' ')
            if any(kw in col_lower for kw in number_keywords) and col not in currency_cols:
                number_cols.append(col)
    
    # Auto-detect percentage columns
    if pct_cols is None:
        pct_cols = []
        pct_keywords = ['percent', 'pct', 'rate', '%', 'ratio', 'efficiency']
        for col in styled_df.columns:
            col_lower = col.lower().replace('_', ' ')
            if any(kw in col_lower for kw in pct_keywords):
                pct_cols.append(col)
    
    # Format currency columns
    for col in currency_cols:
        if col in styled_df.columns:
            styled_df[col] = styled_df[col].apply(lambda x: format_currency(x))
    
    # Format number columns
    for col in number_cols:
        if col in styled_df.columns:
            styled_df[col] = styled_df[col].apply(lambda x: format_number(x))
    
    # Format percentage columns
    for col in pct_cols:
        if col in styled_df.columns:
            styled_df[col] = styled_df[col].apply(lambda x: format_percentage(x))
    
    # Format date columns
    if date_cols:
        for col in date_cols:
            if col in styled_df.columns:
                styled_df[col] = pd.to_datetime(styled_df[col], errors='coerce').dt.strftime('%d %b %Y')
    
    return styled_df


def display_styled_dataframe(df, title=None, currency_cols=None, number_cols=None, 
                             hide_index=True, use_container_width=True):
    """Display a styled dataframe with automatic formatting"""
    if df.empty:
        st.info("No data to display")
        return
    
    if title:
        st.subheader(title)
    
    # Format the dataframe
    styled_df = style_dataframe(df, currency_cols=currency_cols, number_cols=number_cols)
    
    # Rename columns to be more readable
    renamed_cols = {}
    for col in styled_df.columns:
        new_name = col.replace('_', ' ').title()
        renamed_cols[col] = new_name
    styled_df = styled_df.rename(columns=renamed_cols)
    
    st.dataframe(styled_df, hide_index=hide_index, use_container_width=use_container_width)


# =============================================================================
# HTML TABLE RENDERING
# =============================================================================

def render_html_table(df, title=None, currency_cols=None, status_col=None):
    """Render a beautiful HTML table with custom styling"""
    if df.empty:
        st.info("No data to display")
        return
    
    # Apply formatting
    styled_df = style_dataframe(df, currency_cols=currency_cols)
    
    # Custom CSS
    st.markdown("""
    <style>
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
        font-size: 14px;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .custom-table thead tr {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        color: white;
        text-align: left;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 12px;
        letter-spacing: 0.5px;
    }
    
    .custom-table th, .custom-table td {
        padding: 14px 18px;
        border-bottom: 1px solid #e9ecef;
    }
    
    .custom-table tbody tr {
        background-color: #ffffff;
        transition: all 0.2s ease;
    }
    
    .custom-table tbody tr:nth-of-type(even) {
        background-color: #f8f9fa;
    }
    
    .custom-table tbody tr:hover {
        background-color: #e3f2fd;
        transform: scale(1.001);
    }
    
    .custom-table .currency {
        font-weight: 600;
        color: #28a745;
    }
    
    .custom-table .currency.negative {
        color: #dc3545;
    }
    
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        display: inline-block;
    }
    
    .status-active, .status-paid, .status-approved, .status-completed {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        color: #155724;
    }
    
    .status-pending, .status-processing, .status-scheduled {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
        color: #856404;
    }
    
    .status-inactive, .status-cancelled, .status-rejected, .status-overdue {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        color: #721c24;
    }
    </style>
    """, unsafe_allow_html=True)
    
    if title:
        st.markdown(f"**{title}**")
    
    # Build HTML table
    html = '<table class="custom-table"><thead><tr>'
    for col in styled_df.columns:
        display_col = col.replace('_', ' ').title()
        html += f'<th>{display_col}</th>'
    html += '</tr></thead><tbody>'
    
    for _, row in styled_df.iterrows():
        html += '<tr>'
        for col in styled_df.columns:
            val = row[col]
            cell_class = ''
            
            # Check if currency column
            if currency_cols and col in currency_cols:
                cell_class = 'currency'
                if isinstance(val, str) and val.startswith('-'):
                    cell_class += ' negative'
            
            # Check if status column
            if status_col and col == status_col:
                status_class = str(val).lower().replace(' ', '-')
                val = f'<span class="status-badge status-{status_class}">{val}</span>'
            
            html += f'<td class="{cell_class}">{val}</td>'
        html += '</tr>'
    
    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)


# =============================================================================
# SUMMARY CARDS
# =============================================================================

def render_summary_cards(metrics):
    """
    Render beautiful summary metric cards.
    
    Args:
        metrics: List of dicts with keys: label, value, prefix (optional), delta (optional)
    """
    st.markdown("""
    <style>
    .summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
        margin: 20px 0;
    }
    
    .summary-card {
        border-radius: 12px;
        padding: 20px;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
    }
    
    .summary-card:hover {
        transform: translateY(-3px);
    }
    
    .summary-card.purple { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .summary-card.green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .summary-card.orange { background: linear-gradient(135deg, #fc4a1a 0%, #f7b733 100%); }
    .summary-card.blue { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    .summary-card.red { background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%); }
    .summary-card.teal { background: linear-gradient(135deg, #0cebeb 0%, #20e3b2 100%); }
    
    .summary-card h2 {
        margin: 0;
        font-size: 32px;
        font-weight: 700;
    }
    
    .summary-card p {
        margin: 8px 0 0 0;
        opacity: 0.9;
        font-size: 14px;
    }
    
    .summary-card .delta {
        font-size: 13px;
        margin-top: 5px;
        opacity: 0.85;
    }
    </style>
    """, unsafe_allow_html=True)
    
    colors = ['green', 'blue', 'orange', 'purple', 'teal', 'red']
    
    html = '<div class="summary-grid">'
    for i, metric in enumerate(metrics):
        color = colors[i % len(colors)]
        prefix = metric.get('prefix', '')
        value = metric.get('value', 0)
        label = metric.get('label', '')
        delta = metric.get('delta', '')
        
        # Format value
        if isinstance(value, (int, float)):
            if prefix == '$':
                formatted_value = f"${value:,.2f}"
            elif prefix == '%':
                formatted_value = f"{value:.1f}%"
            else:
                formatted_value = f"{prefix}{value:,}"
        else:
            formatted_value = f"{prefix}{value}"
        
        delta_html = f'<div class="delta">{delta}</div>' if delta else ''
        
        html += f'''
        <div class="summary-card {color}">
            <h2>{formatted_value}</h2>
            <p>{label}</p>
            {delta_html}
        </div>
        '''
    
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)
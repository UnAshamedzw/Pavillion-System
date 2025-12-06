"""
mobile_styles.py - Mobile-Responsive Styling
Pavillion Coaches Bus Management System
CSS styles for improved mobile and tablet experience
"""

import streamlit as st


def apply_mobile_styles():
    """
    Apply mobile-responsive CSS styles to the Streamlit app.
    Call this function at the start of your main app.
    """
    
    st.markdown("""
    <style>
    /* ============================================
       MOBILE-RESPONSIVE STYLES
       Pavillion Coaches Bus Management System
       ============================================ */
    
    /* ----- ROOT VARIABLES ----- */
    :root {
        --primary-color: #1E88E5;
        --secondary-color: #43A047;
        --warning-color: #FB8C00;
        --danger-color: #E53935;
        --text-color: #333333;
        --text-light: #666666;
        --bg-light: #F5F5F5;
        --border-radius: 8px;
    }
    
    /* ----- DARK MODE VARIABLES ----- */
    [data-theme="dark"], 
    .stApp[data-theme="dark"],
    @media (prefers-color-scheme: dark) {
        :root {
            --text-color: #FFFFFF;
            --text-light: #CCCCCC;
            --bg-light: #2D2D2D;
        }
    }
    
    /* ----- DARK MODE FIXES ----- */
    
    /* Fix text readability in dark mode */
    [data-theme="dark"] .stMarkdown,
    [data-theme="dark"] .stText,
    [data-theme="dark"] p,
    [data-theme="dark"] span,
    [data-theme="dark"] label,
    [data-theme="dark"] .stMetric label,
    .stApp[data-testid="stAppViewContainer"][style*="color-scheme: dark"] p,
    .stApp[data-testid="stAppViewContainer"][style*="color-scheme: dark"] span {
        color: #FFFFFF !important;
    }
    
    /* Dark mode metric values */
    [data-theme="dark"] [data-testid="stMetricValue"],
    .stApp[data-testid="stAppViewContainer"][style*="color-scheme: dark"] [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
    }
    
    /* Dark mode metric labels */
    [data-theme="dark"] [data-testid="stMetricLabel"],
    .stApp[data-testid="stAppViewContainer"][style*="color-scheme: dark"] [data-testid="stMetricLabel"] {
        color: #CCCCCC !important;
    }
    
    /* Dark mode metric delta */
    [data-theme="dark"] [data-testid="stMetricDelta"],
    .stApp[data-testid="stAppViewContainer"][style*="color-scheme: dark"] [data-testid="stMetricDelta"] {
        opacity: 1 !important;
    }
    
    /* Dark mode table text */
    [data-theme="dark"] .stDataFrame,
    [data-theme="dark"] .stDataFrame td,
    [data-theme="dark"] .stDataFrame th,
    [data-theme="dark"] .stTable td,
    [data-theme="dark"] .stTable th {
        color: #FFFFFF !important;
    }
    
    /* Dark mode expander text */
    [data-theme="dark"] .streamlit-expanderHeader,
    [data-theme="dark"] .streamlit-expanderContent {
        color: #FFFFFF !important;
    }
    
    /* Dark mode selectbox and input text */
    [data-theme="dark"] .stSelectbox label,
    [data-theme="dark"] .stTextInput label,
    [data-theme="dark"] .stNumberInput label,
    [data-theme="dark"] .stTextArea label,
    [data-theme="dark"] .stDateInput label {
        color: #FFFFFF !important;
    }
    
    /* Dark mode info/warning boxes */
    [data-theme="dark"] .stAlert p {
        color: inherit !important;
    }
    
    /* Dark mode sidebar text */
    [data-theme="dark"] [data-testid="stSidebar"],
    [data-theme="dark"] [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    
    [data-theme="dark"] [data-testid="stSidebar"] .stRadio label {
        color: #FFFFFF !important;
    }
    
    /* ----- GENERAL MOBILE ADJUSTMENTS ----- */
    
    /* Make main content area more mobile-friendly */
    .main .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    
    /* Improve touch targets */
    button, .stButton > button {
        min-height: 44px;
        min-width: 44px;
    }
    
    /* Better form inputs on mobile */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div {
        font-size: 16px !important; /* Prevents zoom on iOS */
    }
    
    /* ----- SIDEBAR AUTO-COLLAPSE ON MOBILE ----- */
    
    @media (max-width: 768px) {
        /* Make sidebar overlay instead of push */
        [data-testid="stSidebar"] {
            position: fixed !important;
            z-index: 999 !important;
            height: 100vh !important;
            transition: transform 0.3s ease-in-out !important;
        }
        
        /* Collapsed state */
        [data-testid="stSidebar"][aria-expanded="false"] {
            transform: translateX(-100%) !important;
        }
        
        /* Expanded state */
        [data-testid="stSidebar"][aria-expanded="true"] {
            transform: translateX(0) !important;
            box-shadow: 4px 0 10px rgba(0, 0, 0, 0.2) !important;
        }
        
        /* Main content takes full width */
        .main .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            max-width: 100% !important;
        }
        
        /* Hamburger menu styling */
        [data-testid="stSidebarCollapsedControl"] {
            position: fixed !important;
            top: 0.5rem !important;
            left: 0.5rem !important;
            z-index: 1000 !important;
            background: var(--primary-color) !important;
            border-radius: 8px !important;
            padding: 8px !important;
        }
        
        [data-testid="stSidebarCollapsedControl"] svg {
            color: white !important;
        }
    }
    
    /* ----- METRIC CARDS - PREVENT NUMBER TRUNCATION ----- */
    
    /* Ensure numbers don't get cut off */
    [data-testid="stMetricValue"] {
        font-size: clamp(0.9rem, 3.5vw, 1.8rem) !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: unset !important;
        min-width: 0 !important;
        word-break: keep-all !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: clamp(0.65rem, 2vw, 0.875rem) !important;
        white-space: normal !important;
        word-wrap: break-word !important;
    }
    
    /* Metric container - allow content to fit */
    [data-testid="metric-container"] {
        overflow: visible !important;
        min-width: fit-content !important;
    }
    
    /* Stack metrics properly on mobile */
    @media (max-width: 640px) {
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 0.5rem !important;
        }
        
        /* Each metric takes half width on mobile */
        [data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            flex: 0 0 calc(50% - 0.5rem) !important;
            min-width: calc(50% - 0.5rem) !important;
            max-width: calc(50% - 0.5rem) !important;
        }
        
        /* Single column for very small screens */
        @media (max-width: 360px) {
            [data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex: 0 0 100% !important;
                min-width: 100% !important;
                max-width: 100% !important;
            }
        }
        
        /* Metric value smaller on mobile */
        [data-testid="stMetricValue"] {
            font-size: 1rem !important;
        }
        
        [data-testid="stMetricLabel"] {
            font-size: 0.7rem !important;
        }
    }
    
    /* ----- TABLES MOBILE ----- */
    
    /* Make tables scrollable on mobile */
    .stDataFrame {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
    }
    
    @media (max-width: 768px) {
        .stDataFrame > div {
            font-size: 12px !important;
        }
        
        /* Reduce padding in table cells */
        .stDataFrame td, .stDataFrame th {
            padding: 4px 8px !important;
            white-space: nowrap !important;
        }
    }
    
    /* ----- FORMS MOBILE ----- */
    
    @media (max-width: 640px) {
        /* Stack form columns */
        [data-testid="stForm"] [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
        }
        
        [data-testid="stForm"] [data-testid="stHorizontalBlock"] > div {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
        
        /* Full width buttons in forms */
        [data-testid="stForm"] button {
            width: 100% !important;
        }
    }
    
    /* ----- TABS MOBILE ----- */
    
    @media (max-width: 768px) {
        /* Make tabs scrollable */
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
            flex-wrap: nowrap !important;
            gap: 0 !important;
            padding-bottom: 5px !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            flex-shrink: 0 !important;
            padding: 8px 12px !important;
            font-size: 12px !important;
            white-space: nowrap !important;
        }
    }
    
    /* ----- CHARTS MOBILE ----- */
    
    @media (max-width: 640px) {
        /* Make charts responsive */
        .js-plotly-plot, .plotly {
            width: 100% !important;
        }
        
        .js-plotly-plot .plot-container {
            width: 100% !important;
        }
        
        /* Smaller chart fonts */
        .js-plotly-plot .gtitle,
        .js-plotly-plot .xtitle,
        .js-plotly-plot .ytitle {
            font-size: 11px !important;
        }
    }
    
    /* ----- BUTTONS MOBILE ----- */
    
    @media (max-width: 640px) {
        /* Stack buttons in horizontal blocks */
        .stButton {
            width: 100% !important;
        }
        
        .stButton > button {
            width: 100% !important;
            padding: 0.5rem 1rem !important;
            font-size: 14px !important;
        }
        
        /* Download buttons */
        .stDownloadButton {
            width: 100% !important;
        }
        
        .stDownloadButton > button {
            width: 100% !important;
        }
    }
    
    /* ----- EXPANDERS MOBILE ----- */
    
    @media (max-width: 768px) {
        .streamlit-expanderHeader {
            font-size: 14px !important;
            padding: 12px !important;
        }
        
        .streamlit-expanderContent {
            padding: 8px !important;
        }
    }
    
    /* ----- ALERTS & NOTIFICATIONS MOBILE ----- */
    
    @media (max-width: 640px) {
        .stAlert {
            padding: 12px !important;
            font-size: 14px !important;
        }
        
        /* Custom alert cards */
        div[style*="background-color: #ffebee"],
        div[style*="background-color: #fff3e0"],
        div[style*="background-color: #e3f2fd"] {
            margin: 8px 0 !important;
            padding: 12px !important;
        }
    }
    
    /* ----- HEADER MOBILE ----- */
    
    @media (max-width: 768px) {
        h1 {
            font-size: 1.4rem !important;
            margin-top: 0.5rem !important;
        }
        
        h2 {
            font-size: 1.2rem !important;
        }
        
        h3 {
            font-size: 1rem !important;
        }
        
        /* Add padding for hamburger menu */
        .main .block-container {
            padding-top: 3rem !important;
        }
    }
    
    /* ----- NAVIGATION MOBILE ----- */
    
    /* Better radio button navigation on mobile */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] .stRadio > div {
            flex-direction: column !important;
        }
        
        [data-testid="stSidebar"] .stRadio > div > label {
            padding: 12px 15px !important;
            margin: 3px 0 !important;
            border-radius: var(--border-radius) !important;
            transition: background 0.2s ease !important;
        }
        
        [data-testid="stSidebar"] .stRadio > div > label:hover {
            background: rgba(255, 255, 255, 0.1) !important;
        }
    }
    
    /* ----- SELECTBOX MOBILE ----- */
    
    @media (max-width: 640px) {
        .stSelectbox > div > div {
            min-height: 44px !important;
        }
        
        .stSelectbox label {
            font-size: 14px !important;
        }
    }
    
    /* ----- DATE/TIME INPUTS MOBILE ----- */
    
    @media (max-width: 640px) {
        .stDateInput > div > div > input,
        .stTimeInput > div > div > input {
            font-size: 16px !important;
            min-height: 44px !important;
        }
    }
    
    /* ----- FILE UPLOADER MOBILE ----- */
    
    @media (max-width: 640px) {
        .stFileUploader > div {
            padding: 15px !important;
        }
        
        .stFileUploader label {
            font-size: 14px !important;
        }
    }
    
    /* ----- MULTISELECT MOBILE ----- */
    
    @media (max-width: 640px) {
        .stMultiSelect > div > div {
            min-height: 44px !important;
        }
        
        .stMultiSelect [data-baseweb="tag"] {
            font-size: 12px !important;
            padding: 2px 6px !important;
        }
    }
    
    /* ----- CUSTOM CARD STYLES ----- */
    
    .metric-card {
        background: white;
        border-radius: var(--border-radius);
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
    
    @media (max-width: 640px) {
        .metric-card {
            padding: 12px;
        }
    }
    
    /* Dark mode card */
    [data-theme="dark"] .metric-card {
        background: #2D2D2D !important;
        color: #FFFFFF !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
    }
    
    [data-theme="dark"] .metric-card * {
        color: #FFFFFF !important;
    }
    
    /* ----- FOOTER SPACING MOBILE ----- */
    
    @media (max-width: 768px) {
        .main .block-container {
            padding-bottom: 80px !important;
        }
    }
    
    /* ----- TOUCH IMPROVEMENTS ----- */
    
    @media (max-width: 768px) {
        a, button, input, select, textarea {
            touch-action: manipulation !important;
        }
        
        /* Prevent double-tap zoom */
        * {
            touch-action: manipulation !important;
        }
    }
    
    /* ----- LANDSCAPE MOBILE ----- */
    
    @media (max-width: 900px) and (orientation: landscape) {
        .main .block-container {
            padding-top: 1rem !important;
        }
        
        [data-testid="stSidebar"] {
            max-height: 100vh !important;
            overflow-y: auto !important;
        }
    }
    
    /* ----- PRINT STYLES ----- */
    
    @media print {
        [data-testid="stSidebar"] {
            display: none !important;
        }
        
        .main .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }
        
        button, .stButton {
            display: none !important;
        }
    }
    
    /* ----- ACCESSIBILITY ----- */
    
    /* Focus states for keyboard navigation */
    button:focus, 
    input:focus, 
    select:focus, 
    textarea:focus,
    a:focus {
        outline: 2px solid var(--primary-color) !important;
        outline-offset: 2px !important;
    }
    
    /* Reduced motion preference */
    @media (prefers-reduced-motion: reduce) {
        * {
            animation: none !important;
            transition: none !important;
        }
    }
    
    /* ----- SCROLLBAR STYLING ----- */
    
    /* Custom scrollbar for webkit browsers */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
    
    @media (max-width: 768px) {
        ::-webkit-scrollbar {
            width: 4px;
            height: 4px;
        }
    }
    
    /* Dark mode scrollbar */
    [data-theme="dark"] ::-webkit-scrollbar-track {
        background: #333;
    }
    
    [data-theme="dark"] ::-webkit-scrollbar-thumb {
        background: #666;
    }
    
    </style>
    """, unsafe_allow_html=True)


def apply_compact_mobile_styles():
    """
    Apply additional compact styles for very small screens.
    Use this for data-heavy pages.
    """
    
    st.markdown("""
    <style>
    @media (max-width: 480px) {
        /* Extra compact for small phones */
        .main .block-container {
            padding-left: 0.25rem !important;
            padding-right: 0.25rem !important;
        }
        
        h1 {
            font-size: 1.2rem !important;
        }
        
        h2 {
            font-size: 1rem !important;
        }
        
        h3 {
            font-size: 0.9rem !important;
        }
        
        /* Smaller metrics */
        [data-testid="stMetricValue"] {
            font-size: 0.9rem !important;
        }
        
        [data-testid="stMetricLabel"] {
            font-size: 0.65rem !important;
        }
        
        /* Compact tables */
        .stDataFrame td, .stDataFrame th {
            padding: 2px 4px !important;
            font-size: 10px !important;
        }
        
        /* Compact forms */
        .stTextInput label,
        .stSelectbox label,
        .stNumberInput label {
            font-size: 12px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)


def format_currency_mobile(value, symbol="$"):
    """
    Format currency for mobile display - abbreviates large numbers.
    $1,234,567 becomes $1.23M on mobile
    """
    try:
        value = float(value)
        if value >= 1000000:
            return f"{symbol}{value/1000000:.1f}M"
        elif value >= 1000:
            return f"{symbol}{value/1000:.1f}K"
        else:
            return f"{symbol}{value:,.0f}"
    except:
        return f"{symbol}0"


def get_device_type():
    """
    Attempt to detect device type based on viewport.
    Note: This is a workaround as Streamlit doesn't directly expose viewport info.
    Returns a hint to use for conditional rendering.
    """
    return "desktop"  # Default assumption


def responsive_columns(num_desktop=4, num_tablet=2, num_mobile=1):
    """
    Create responsive column layout.
    Returns the appropriate number of columns based on common breakpoints.
    
    Usage:
        cols = responsive_columns(4, 2, 1)
        for i, col in enumerate(cols):
            with col:
                st.metric(...)
    
    Note: Streamlit doesn't dynamically adjust columns, so this returns
    the desktop layout. CSS handles the visual stacking on mobile.
    """
    return st.columns(num_desktop)


def mobile_metric_card(label, value, delta=None, delta_color="normal"):
    """
    Create a mobile-friendly metric card with better touch targets.
    """
    delta_html = ""
    if delta:
        color = "#43A047" if delta_color == "normal" else "#E53935"
        if delta_color == "inverse":
            color = "#E53935" if str(delta).startswith("-") else "#43A047"
        delta_html = f'<div style="color: {color}; font-size: 0.9rem;">{delta}</div>'
    
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size: 0.85rem; margin-bottom: 4px; opacity: 0.8;">{label}</div>
        <div style="font-size: 1.5rem; font-weight: bold;">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def mobile_alert(message, alert_type="info"):
    """
    Create a mobile-friendly alert with larger touch targets.
    
    alert_type: "info", "success", "warning", "error"
    """
    colors = {
        "info": ("#e3f2fd", "#1565C0", "ℹ️"),
        "success": ("#e8f5e9", "#2E7D32", "✅"),
        "warning": ("#fff3e0", "#EF6C00", "⚠️"),
        "error": ("#ffebee", "#C62828", "🔴")
    }
    
    bg_color, text_color, icon = colors.get(alert_type, colors["info"])
    
    st.markdown(f"""
    <div style="
        background-color: {bg_color}; 
        color: {text_color};
        padding: 15px; 
        border-radius: 8px; 
        margin: 10px 0;
        font-size: 14px;
    ">
        {icon} {message}
    </div>
    """, unsafe_allow_html=True)


def mobile_button_row(buttons):
    """
    Create a row of buttons that stack on mobile.
    
    buttons: list of tuples [(label, key, type), ...]
    type: "primary" or "secondary"
    
    Returns: dict of button states {key: bool}
    """
    cols = st.columns(len(buttons))
    results = {}
    
    for i, (label, key, btn_type) in enumerate(buttons):
        with cols[i]:
            results[key] = st.button(
                label, 
                key=key, 
                type=btn_type if btn_type == "primary" else "secondary",
                use_container_width=True
            )
    
    return results


def mobile_data_table(df, key=None):
    """
    Display a dataframe with mobile-optimized settings.
    """
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        key=key
    )


def mobile_expander(title, expanded=False):
    """
    Create a mobile-friendly expander with better touch targets.
    Returns the expander object for use with 'with' statement.
    """
    return st.expander(title, expanded=expanded)
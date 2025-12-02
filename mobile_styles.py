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
        --bg-light: #F5F5F5;
        --border-radius: 8px;
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
    
    /* ----- SIDEBAR MOBILE STYLES ----- */
    
    @media (max-width: 768px) {
        /* Sidebar adjustments */
        [data-testid="stSidebar"] {
            min-width: 100% !important;
            width: 100% !important;
        }
        
        [data-testid="stSidebar"] > div:first-child {
            width: 100% !important;
        }
        
        /* When sidebar is collapsed, show hamburger better */
        [data-testid="stSidebar"][aria-expanded="false"] {
            min-width: 0 !important;
            width: 0 !important;
        }
        
        /* Main content when sidebar collapsed */
        .main .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
    }
    
    /* ----- METRIC CARDS MOBILE ----- */
    
    /* Stack metrics on mobile */
    @media (max-width: 640px) {
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap;
        }
        
        [data-testid="stHorizontalBlock"] > div {
            flex: 1 1 45% !important;
            min-width: 45% !important;
        }
        
        /* Full width for single column items */
        [data-testid="stHorizontalBlock"] > div:only-child {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
    }
    
    /* Metric styling */
    [data-testid="stMetricValue"] {
        font-size: clamp(1.2rem, 4vw, 2rem);
    }
    
    [data-testid="stMetricLabel"] {
        font-size: clamp(0.75rem, 2.5vw, 0.875rem);
    }
    
    /* ----- TABLES MOBILE ----- */
    
    /* Make tables scrollable on mobile */
    .stDataFrame {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
    
    @media (max-width: 768px) {
        .stDataFrame > div {
            font-size: 12px;
        }
        
        /* Reduce padding in table cells */
        .stDataFrame td, .stDataFrame th {
            padding: 4px 8px !important;
        }
    }
    
    /* ----- FORMS MOBILE ----- */
    
    @media (max-width: 640px) {
        /* Stack form columns */
        [data-testid="stForm"] [data-testid="stHorizontalBlock"] {
            flex-direction: column;
        }
        
        [data-testid="stForm"] [data-testid="stHorizontalBlock"] > div {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
        
        /* Full width buttons in forms */
        [data-testid="stForm"] button {
            width: 100%;
        }
    }
    
    /* ----- TABS MOBILE ----- */
    
    @media (max-width: 768px) {
        /* Make tabs scrollable */
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            flex-wrap: nowrap;
            gap: 0;
        }
        
        .stTabs [data-baseweb="tab"] {
            flex-shrink: 0;
            padding: 8px 12px;
            font-size: 13px;
            white-space: nowrap;
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
    }
    
    /* ----- BUTTONS MOBILE ----- */
    
    @media (max-width: 640px) {
        /* Stack buttons in horizontal blocks */
        .stButton {
            width: 100%;
        }
        
        .stButton > button {
            width: 100%;
        }
        
        /* Download buttons */
        .stDownloadButton {
            width: 100%;
        }
        
        .stDownloadButton > button {
            width: 100%;
        }
    }
    
    /* ----- EXPANDERS MOBILE ----- */
    
    @media (max-width: 768px) {
        .streamlit-expanderHeader {
            font-size: 14px;
            padding: 12px;
        }
        
        .streamlit-expanderContent {
            padding: 8px;
        }
    }
    
    /* ----- ALERTS & NOTIFICATIONS MOBILE ----- */
    
    @media (max-width: 640px) {
        .stAlert {
            padding: 12px;
            font-size: 14px;
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
            font-size: 1.5rem !important;
        }
        
        h2 {
            font-size: 1.25rem !important;
        }
        
        h3 {
            font-size: 1.1rem !important;
        }
    }
    
    /* ----- NAVIGATION MOBILE ----- */
    
    /* Better radio button navigation on mobile */
    @media (max-width: 768px) {
        .stRadio > div {
            flex-direction: column;
        }
        
        .stRadio > div > label {
            padding: 10px 15px;
            margin: 2px 0;
            background: var(--bg-light);
            border-radius: var(--border-radius);
        }
    }
    
    /* ----- SELECTBOX MOBILE ----- */
    
    @media (max-width: 640px) {
        .stSelectbox > div > div {
            min-height: 44px;
        }
        
        .stSelectbox label {
            font-size: 14px;
        }
    }
    
    /* ----- DATE/TIME INPUTS MOBILE ----- */
    
    @media (max-width: 640px) {
        .stDateInput > div > div > input,
        .stTimeInput > div > div > input {
            font-size: 16px !important;
            min-height: 44px;
        }
    }
    
    /* ----- FILE UPLOADER MOBILE ----- */
    
    @media (max-width: 640px) {
        .stFileUploader > div {
            padding: 15px;
        }
        
        .stFileUploader label {
            font-size: 14px;
        }
    }
    
    /* ----- MULTISELECT MOBILE ----- */
    
    @media (max-width: 640px) {
        .stMultiSelect > div > div {
            min-height: 44px;
        }
        
        .stMultiSelect [data-baseweb="tag"] {
            font-size: 12px;
            padding: 2px 6px;
        }
    }
    
    /* ----- PROGRESS BAR MOBILE ----- */
    
    @media (max-width: 640px) {
        .stProgress > div > div {
            height: 8px;
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
    
    /* ----- FOOTER SPACING MOBILE ----- */
    
    @media (max-width: 768px) {
        .main .block-container {
            padding-bottom: 80px;
        }
    }
    
    /* ----- TOUCH IMPROVEMENTS ----- */
    
    /* Increase touch targets */
    @media (max-width: 768px) {
        a, button, input, select, textarea {
            touch-action: manipulation;
        }
        
        /* Prevent double-tap zoom */
        * {
            touch-action: manipulation;
        }
    }
    
    /* ----- LANDSCAPE MOBILE ----- */
    
    @media (max-width: 900px) and (orientation: landscape) {
        .main .block-container {
            padding-top: 1rem;
        }
        
        [data-testid="stSidebar"] {
            max-height: 100vh;
            overflow-y: auto;
        }
    }
    
    /* ----- PRINT STYLES ----- */
    
    @media print {
        [data-testid="stSidebar"] {
            display: none !important;
        }
        
        .main .block-container {
            padding: 0;
            max-width: 100%;
        }
        
        button, .stButton {
            display: none !important;
        }
    }
    
    /* ----- DARK MODE SUPPORT ----- */
    
    @media (prefers-color-scheme: dark) {
        .metric-card {
            background: #1E1E1E;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
    }
    
    /* ----- ACCESSIBILITY ----- */
    
    /* Focus states for keyboard navigation */
    button:focus, 
    input:focus, 
    select:focus, 
    textarea:focus,
    a:focus {
        outline: 2px solid var(--primary-color);
        outline-offset: 2px;
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
            padding-left: 0.25rem;
            padding-right: 0.25rem;
        }
        
        h1 {
            font-size: 1.3rem !important;
        }
        
        h2 {
            font-size: 1.1rem !important;
        }
        
        h3 {
            font-size: 1rem !important;
        }
        
        /* Smaller metrics */
        [data-testid="stMetricValue"] {
            font-size: 1rem;
        }
        
        [data-testid="stMetricLabel"] {
            font-size: 0.7rem;
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
            font-size: 12px;
        }
    }
    </style>
    """, unsafe_allow_html=True)


def get_device_type():
    """
    Attempt to detect device type based on viewport.
    Note: This is a workaround as Streamlit doesn't directly expose viewport info.
    Returns a hint to use for conditional rendering.
    """
    # This is a placeholder - in production, you might use JavaScript injection
    # to detect actual viewport width
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
        <div style="color: #666; font-size: 0.85rem; margin-bottom: 4px;">{label}</div>
        <div style="font-size: 1.5rem; font-weight: bold; color: #333;">{value}</div>
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

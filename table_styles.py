"""
table_styles.py - Enhanced Table Styling and Currency Formatting
Provides consistent, professional table displays throughout the system
"""

import streamlit as st
import pandas as pd


# =============================================================================
# CURRENCY FORMATTING
# =============================================================================

def format_currency(value, currency='USD', show_symbol=True):
    """
    Format a number as currency.
    
    Args:
        value: Number to format
        currency: 'USD' or 'ZiG'
        show_symbol: Whether to show currency symbol
    
    Returns:
        Formatted string like "$1,234.56" or "ZiG 1,234.56"
    """
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
# DATAFRAME STYLING
# =============================================================================

def style_dataframe(df, currency_columns=None, number_columns=None, 
                    percentage_columns=None, date_columns=None,
                    currency='USD', highlight_max=None, highlight_min=None):
    """
    Apply consistent styling to a dataframe.
    
    Args:
        df: Pandas DataFrame
        currency_columns: List of columns to format as currency
        number_columns: List of columns to format with thousand separators
        percentage_columns: List of columns to format as percentages
        date_columns: List of columns to format as dates
        currency: Default currency symbol
        highlight_max: Column name to highlight max value (green)
        highlight_min: Column name to highlight min value (red)
    
    Returns:
        Styled DataFrame ready for display
    """
    if df.empty:
        return df
    
    styled_df = df.copy()
    
    # Format currency columns
    if currency_columns:
        for col in currency_columns:
            if col in styled_df.columns:
                styled_df[col] = styled_df[col].apply(
                    lambda x: format_currency(x, currency)
                )
    
    # Format number columns
    if number_columns:
        for col in number_columns:
            if col in styled_df.columns:
                styled_df[col] = styled_df[col].apply(format_number)
    
    # Format percentage columns
    if percentage_columns:
        for col in percentage_columns:
            if col in styled_df.columns:
                styled_df[col] = styled_df[col].apply(format_percentage)
    
    # Format date columns
    if date_columns:
        for col in date_columns:
            if col in styled_df.columns:
                styled_df[col] = pd.to_datetime(styled_df[col], errors='coerce').dt.strftime('%d %b %Y')
    
    return styled_df


def get_table_style():
    """Return CSS for styled tables"""
    return """
    <style>
    .styled-table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
        font-size: 14px;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .styled-table thead tr {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        color: white;
        text-align: left;
        font-weight: 600;
    }
    
    .styled-table th,
    .styled-table td {
        padding: 12px 15px;
        border-bottom: 1px solid #e0e0e0;
    }
    
    .styled-table tbody tr {
        background-color: #ffffff;
        transition: background-color 0.2s;
    }
    
    .styled-table tbody tr:nth-of-type(even) {
        background-color: #f8f9fa;
    }
    
    .styled-table tbody tr:hover {
        background-color: #e8f4f8;
    }
    
    .styled-table tbody tr:last-of-type {
        border-bottom: 2px solid #1e3a5f;
    }
    
    /* Currency styling */
    .currency-positive {
        color: #28a745;
        font-weight: 600;
    }
    
    .currency-negative {
        color: #dc3545;
        font-weight: 600;
    }
    
    /* Status badges */
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
    }
    
    .status-active, .status-approved, .status-paid, .status-completed {
        background-color: #d4edda;
        color: #155724;
    }
    
    .status-pending, .status-processing {
        background-color: #fff3cd;
        color: #856404;
    }
    
    .status-inactive, .status-rejected, .status-cancelled {
        background-color: #f8d7da;
        color: #721c24;
    }
    
    /* Totals row */
    .totals-row {
        background-color: #1e3a5f !important;
        color: white !important;
        font-weight: bold;
    }
    
    .totals-row td {
        border-bottom: none !important;
    }
    </style>
    """


def render_styled_table(df, title=None, show_index=False, currency_columns=None,
                        number_columns=None, percentage_columns=None,
                        status_column=None, totals_row=False, currency='USD'):
    """
    Render a beautifully styled HTML table.
    
    Args:
        df: Pandas DataFrame
        title: Optional table title
        show_index: Whether to show row index
        currency_columns: Columns to format as currency
        number_columns: Columns to format with commas
        percentage_columns: Columns to format as percentages
        status_column: Column containing status values (for badge styling)
        totals_row: Whether last row is a totals row
        currency: Currency symbol to use
    """
    if df.empty:
        st.info("No data to display")
        return
    
    # Apply styling
    st.markdown(get_table_style(), unsafe_allow_html=True)
    
    # Build HTML table
    html = '<table class="styled-table">'
    
    # Header
    html += '<thead><tr>'
    if show_index:
        html += '<th>#</th>'
    for col in df.columns:
        html += f'<th>{col}</th>'
    html += '</tr></thead>'
    
    # Body
    html += '<tbody>'
    for idx, row in df.iterrows():
        row_class = 'totals-row' if totals_row and idx == len(df) - 1 else ''
        html += f'<tr class="{row_class}">'
        
        if show_index:
            html += f'<td>{idx + 1}</td>'
        
        for col in df.columns:
            value = row[col]
            cell_content = format_cell(value, col, currency_columns, number_columns, 
                                       percentage_columns, status_column, currency)
            html += f'<td>{cell_content}</td>'
        
        html += '</tr>'
    html += '</tbody></table>'
    
    if title:
        st.markdown(f"**{title}**")
    
    st.markdown(html, unsafe_allow_html=True)


def format_cell(value, column, currency_columns, number_columns, 
                percentage_columns, status_column, currency):
    """Format individual cell based on column type"""
    
    # Handle None/NaN
    if pd.isna(value) or value is None:
        return '-'
    
    # Currency formatting
    if currency_columns and column in currency_columns:
        try:
            num = float(value)
            formatted = format_currency(num, currency)
            if num >= 0:
                return f'<span class="currency-positive">{formatted}</span>'
            else:
                return f'<span class="currency-negative">{formatted}</span>'
        except (ValueError, TypeError):
            return str(value)
    
    # Number formatting
    if number_columns and column in number_columns:
        return format_number(value)
    
    # Percentage formatting
    if percentage_columns and column in percentage_columns:
        return format_percentage(value)
    
    # Status badge formatting
    if status_column and column == status_column:
        status = str(value).lower().replace(' ', '-')
        return f'<span class="status-badge status-{status}">{value}</span>'
    
    return str(value)


# =============================================================================
# METRIC CARDS
# =============================================================================

def render_metric_card(label, value, delta=None, delta_color="normal", 
                       icon=None, is_currency=True, currency='USD'):
    """
    Render an enhanced metric card.
    
    Args:
        label: Metric label
        value: Metric value
        delta: Change value (optional)
        delta_color: "normal", "inverse", or "off"
        icon: Emoji icon (optional)
        is_currency: Whether to format as currency
        currency: Currency type
    """
    if is_currency:
        formatted_value = format_currency(value, currency)
    else:
        formatted_value = format_number(value) if isinstance(value, (int, float)) else str(value)
    
    if icon:
        label = f"{icon} {label}"
    
    if delta is not None:
        st.metric(label, formatted_value, delta=delta, delta_color=delta_color)
    else:
        st.metric(label, formatted_value)


def render_summary_cards(metrics, columns=4, currency='USD'):
    """
    Render a row of summary metric cards.
    
    Args:
        metrics: List of dicts with keys: label, value, delta (optional), 
                 icon (optional), is_currency (default True)
        columns: Number of columns
        currency: Currency type
    """
    cols = st.columns(columns)
    
    for idx, metric in enumerate(metrics):
        with cols[idx % columns]:
            render_metric_card(
                label=metric.get('label', ''),
                value=metric.get('value', 0),
                delta=metric.get('delta'),
                delta_color=metric.get('delta_color', 'normal'),
                icon=metric.get('icon'),
                is_currency=metric.get('is_currency', True),
                currency=currency
            )


# =============================================================================
# QUICK DISPLAY FUNCTIONS
# =============================================================================

def display_income_table(df, title="Income Records"):
    """Display income/revenue table with proper formatting"""
    if df.empty:
        st.info("No income records to display")
        return
    
    render_styled_table(
        df,
        title=title,
        currency_columns=['amount', 'Amount', 'revenue', 'Revenue', 'total', 'Total'],
        number_columns=['passengers', 'Passengers', 'trips', 'Trips'],
        status_column='status' if 'status' in df.columns else None
    )


def display_expense_table(df, title="Expenses"):
    """Display expense table with proper formatting"""
    if df.empty:
        st.info("No expense records to display")
        return
    
    render_styled_table(
        df,
        title=title,
        currency_columns=['amount', 'Amount', 'cost', 'Cost', 'total', 'Total'],
        status_column='status' if 'status' in df.columns else None
    )


def display_employee_table(df, title="Employees"):
    """Display employee table with proper formatting"""
    if df.empty:
        st.info("No employee records to display")
        return
    
    render_styled_table(
        df,
        title=title,
        currency_columns=['salary', 'Salary', 'net_pay', 'Net Pay', 'gross', 'Gross'],
        status_column='status' if 'status' in df.columns else None
    )


def display_payroll_table(df, title="Payroll"):
    """Display payroll table with proper formatting"""
    if df.empty:
        st.info("No payroll records to display")
        return
    
    render_styled_table(
        df,
        title=title,
        currency_columns=['base_salary', 'commission_amount', 'bonuses', 'gross_earnings', 
                         'total_deductions', 'net_pay', 'Base Salary', 'Commission',
                         'Bonuses', 'Gross', 'Deductions', 'Net Pay'],
        number_columns=['total_trips', 'Trips', 'days_worked', 'Days'],
        status_column='status' if 'status' in df.columns else None
    )

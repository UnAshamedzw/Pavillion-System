"""
app.py - Main Application Entry Point
Pavillion Coaches Bus Management System
"""

import streamlit as st
from database import init_database
from auth import create_users_table, login_page, logout
from pages_operations import (
    income_entry_page, 
    maintenance_entry_page, 
    revenue_history_page,
    import_data_page,
    dashboard_page,
    routes_management_page
)
from pages_hr import (
    employee_management_page,
    employee_performance_page,
    payroll_management_page,
    leave_management_page,
    disciplinary_records_page
)
from pages_hr import get_expiring_documents, display_document_expiry_alerts

# Initialize database on startup
init_database()

# In your homepage/dashboard function:
def homepage():
    st.title("🏠 Dashboard")
    
    # Document Expiry Alerts - Shows at the top
    display_document_expiry_alerts()
    
    st.markdown("---")
from pages_users import user_management_page, my_profile_page
from pages_audit import activity_log_page, user_activity_dashboard
from pages_bus_analysis import bus_analysis_page
from pages_performance_metrics import performance_metrics_page
from fleet_management_page import fleet_management_page, show_expiry_alerts
import base64
from pathlib import Path

def get_base64_image(image_path):
    """Convert image to base64 for display"""
    try:
        with open(image_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None

def main():
    """Main application entry point"""
    
    # Page configuration
    st.set_page_config(
        page_title="Pavillion Coaches - Bus Management System",
        page_icon="🚌",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize database only once per session
    if 'initialized' not in st.session_state:
        init_database() 
        create_users_table()
        st.session_state.initialized = True
    
    # Check authentication
    if not st.session_state.get('authenticated', False):
        login_page()
        return
    
    # Custom CSS with Pavillion Coaches branding colors
    st.markdown("""
        <style>
        /* Pavillion Coaches Brand Colors */
        :root {
            --pavillion-gold: #E6A918;
            --pavillion-green: #1B4D3E;
            --pavillion-dark: #2c3e50;
            --pavillion-light: #f8f9fa;
        }
        
        .main {
            padding: 0rem 1rem;
        }
        
        h1 {
            color: var(--pavillion-green);
            padding-bottom: 1rem;
        }
        
        h2 {
            color: var(--pavillion-dark);
        }
        
        /* Branded metrics */
        .stMetric {
            background-color: var(--pavillion-light);
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid var(--pavillion-gold);
        }
        
        /* Buttons */
        .stButton>button {
            background-color: var(--pavillion-gold);
            color: white;
            border: none;
            font-weight: 600;
        }
        
        .stButton>button:hover {
            background-color: #d89a15;
            border: none;
        }
        
        /* Primary buttons */
        .stButton>button[kind="primary"] {
            background-color: var(--pavillion-green);
            color: white;
        }
        
        .stButton>button[kind="primary"]:hover {
            background-color: #153d31;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #fafafa;
        }
        
        /* Success messages */
        .element-container div[data-testid="stMarkdownContainer"] div[style*="background-color: rgb(144, 238, 144)"] {
            background-color: var(--pavillion-gold) !important;
        }
        
        /* Logo container */
        .logo-container {
            text-align: center;
            padding: 1rem 0;
            margin-bottom: 1rem;
        }
        
        /* Brand header */
        .brand-header {
            background: linear-gradient(135deg, var(--pavillion-green) 0%, var(--pavillion-gold) 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            text-align: center;
        }
        
        .brand-header h1 {
            color: white;
            margin: 0;
            font-size: 2.5rem;
        }
        
        .brand-header p {
            color: white;
            margin: 0.5rem 0 0 0;
            font-size: 1.1rem;
        }
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: var(--pavillion-light);
            border-radius: 4px 4px 0 0;
            padding: 10px 20px;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: var(--pavillion-gold);
            color: white;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Get current user info
    user = st.session_state['user']
    
    # Sidebar with logo
    # Try to load and display logo
    logo_path = Path("logo.png")
    if logo_path.exists():
        logo_base64 = get_base64_image("logo.png")
        if logo_base64:
            st.sidebar.markdown(
                f"""
                <div class="logo-container">
                    <img src="data:image/png;base64,{logo_base64}" width="200">
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        # Fallback if logo not found
        st.sidebar.markdown("""
            <div style="text-align: center; padding: 1rem 0;">
                <h2 style="color: #1B4D3E; margin: 0;">Pavillion Coaches</h2>
                <p style="color: #E6A918; margin: 0.5rem 0 0 0; font-style: italic;">smart travel</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**👤 {user['full_name']}** ({user['role']})")
    st.sidebar.markdown("---")
    
    # Initialize default page in session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "📈 Dashboard"
    
    # Main menu selection
    menu_section = st.sidebar.radio(
        "Main Menu:",
        ["🚌 Operations", "👥 HR Management", "📊 Analytics", "⚙️ System"]
    )
    
    st.sidebar.markdown("---")
    
    # Sub-menu based on main menu - with Dashboard as first option
    if menu_section == "🚌 Operations":
        page = st.sidebar.radio(
            "Operations:",
            [
                "📈 Dashboard",
                "📊 Income Entry",
                "🔧 Maintenance Entry",
                "📥 Import from Excel",
                "💰 Revenue History",
                "🚌 Fleet Management",
                "🚗 Routes"
            ]
        )
    elif menu_section == "👥 HR Management":
        page = st.sidebar.radio(
            "HR Management:",
            [
                "👥 Employee Management",
                "📊 Employee Performance",
                "💰 Payroll & Payslips",
                "📅 Leave Management",
                "⚠️ Disciplinary Records"
            ]
        )
    elif menu_section == "📊 Analytics":
        page = st.sidebar.radio(
            "Analytics:",
            [
                "🚌 Bus-by-Bus Analysis",
                "📈 Performance Metrics"
            ]
        )
    else:  # System
        pages_list = ["👤 My Profile", "📊 My Activity"]
        # Only show User Management and Activity Log for Admins
        if user['role'] == 'Admin':
            pages_list.extend(["👥 User Management", "📜 Activity Log"])
        
        page = st.sidebar.radio("System:", pages_list)
    
    st.sidebar.markdown("---")
    
    # Info boxes with branded colors
    if menu_section == "🚌 Operations":
        st.sidebar.info("""
        **Operations Features:**
        - 📈 Analytics dashboard
        - 📊 Track daily revenue
        - 🔧 Record maintenance
        - 📥 Bulk import from Excel
        - 💰 Revenue history
        - 🚌 Fleet management
        - 🚗 Routes setup
        - ⚠️ Document tracking
        - ✅ Full audit trail
        """)
    elif menu_section == "👥 HR Management":
        st.sidebar.info("""
        **HR Features:**
        - 👥 Employee database
        - 📊 Performance metrics
        - 💰 Payroll & payslips
        - 📅 Leave management
        - ⚠️ Disciplinary records
        - 💵 Commission tracking
        """)
    elif menu_section == "📊 Analytics":
        st.sidebar.info("""
        **Analytics Features:**
        - 🚌 Bus-by-bus analysis
        - 💰 Revenue vs expenses
        - 📊 Profit/loss tracking
        - 📈 Performance trends
        - 📥 Export to Excel/PDF
        """)
    else:
        st.sidebar.info(f"""
        **User Info:**
        - **Name:** {user['full_name']}
        - **Role:** {user['role']}
        - **Username:** {user['username']}
        
        **System Features:**
        - 🔐 Secure authentication
        - 📜 Complete audit trail
        - 👥 User management
        """)
    
    # Logout button
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        logout()
    
    st.sidebar.markdown("---")
    st.sidebar.caption("© 2025 Pavillion Coaches")
    st.sidebar.caption("🔒 Secure | 📊 Audited | 🚀 Efficient")
    st.sidebar.caption("*smart travel*")
    
    # Main content area with branded header
    st.markdown("""
        <div class="brand-header">
            <h1>Pavillion Coaches</h1>
            <p>Bus Management System</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Show document expiry alerts on Dashboard page
    if page == "📈 Dashboard":
        try:
            show_expiry_alerts()
            st.markdown("---")
        except Exception as e:
            # Silently fail if fleet management is not set up yet
            pass
    
    # Route to appropriate page
    if page == "📊 Income Entry":
        income_entry_page()
    elif page == "🔧 Maintenance Entry":
        maintenance_entry_page()
    elif page == "📥 Import from Excel":
        import_data_page()
    elif page == "💰 Revenue History":
        revenue_history_page()
    elif page == "📈 Dashboard":
        dashboard_page()
    elif page == "🚌 Fleet Management":
        fleet_management_page()
    elif page == "🚗 Routes":
        routes_management_page()
    elif page == "👥 Employee Management":
        employee_management_page()
    elif page == "📊 Employee Performance":
        employee_performance_page()
    elif page == "💰 Payroll & Payslips":
        payroll_management_page()
    elif page == "📅 Leave Management":
        leave_management_page()
    elif page == "⚠️ Disciplinary Records":
        disciplinary_records_page()
    elif page == "🚌 Bus-by-Bus Analysis":
        bus_analysis_page()
    elif page == "📈 Performance Metrics":
        performance_metrics_page()
    elif page == "👤 My Profile":
        my_profile_page()
    elif page == "📊 My Activity":
        user_activity_dashboard()
    elif page == "👥 User Management":
        user_management_page()
    elif page == "📜 Activity Log":
        activity_log_page()

if __name__ == "__main__":
    main()
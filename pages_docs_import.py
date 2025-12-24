"""
pages_docs_import.py - Consolidated Documents & Import Page
Combines Document Management and Excel Import into one interface
"""

import streamlit as st


def documents_import_page():
    """
    Consolidated Documents & Import page with tabs for:
    - Document Management
    - Import from Excel
    """
    
    st.title("Documents & Import")
    
    # Import existing page functions
    from pages_documents import document_management_page
    from pages_operations import import_data_page
    
    # Main tabs
    tab1, tab2 = st.tabs([
        "Documents",
        "Import Data"
    ])
    
    with tab1:
        st.subheader("Document Management")
        document_management_page()
    
    with tab2:
        st.subheader("Import from Excel")
        import_data_page()

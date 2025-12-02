"""
pages_documents.py - Document Management Module
Pavillion Coaches Bus Management System
Upload, store, and manage document scans with expiry alerts
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import get_connection, get_engine, USE_POSTGRES
from audit_logger import AuditLogger
from auth import has_permission
import base64


# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

def get_all_buses():
    """Get all buses for document association"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT bus_number, registration_number, make, model, status
        FROM buses 
        ORDER BY registration_number
    """)
    
    buses = cursor.fetchall()
    conn.close()
    return buses


def get_all_employees():
    """Get all employees for document association"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, employee_id, full_name, position, status
        FROM employees 
        ORDER BY full_name
    """)
    
    employees = cursor.fetchall()
    conn.close()
    return employees


def add_document(document_type, document_name, entity_type, entity_id, entity_name,
                issue_date, expiry_date, file_data, file_name, file_type,
                notes=None, created_by=None):
    """Add a new document record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    days_to_expiry = None
    if expiry_date:
        exp_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
        days_to_expiry = (exp_date - datetime.now().date()).days
    
    try:
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO documents (
                    document_type, document_name, entity_type, entity_id, entity_name,
                    issue_date, expiry_date, days_to_expiry, file_data, file_name, 
                    file_type, file_size, notes, status, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (document_type, document_name, entity_type, entity_id, entity_name,
                  issue_date, expiry_date, days_to_expiry, file_data, file_name,
                  file_type, len(file_data) if file_data else 0, notes, 'Active', created_by))
            result = cursor.fetchone()
            doc_id = result['id'] if hasattr(result, 'keys') else result[0]
        else:
            cursor.execute("""
                INSERT INTO documents (
                    document_type, document_name, entity_type, entity_id, entity_name,
                    issue_date, expiry_date, days_to_expiry, file_data, file_name, 
                    file_type, file_size, notes, status, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (document_type, document_name, entity_type, entity_id, entity_name,
                  issue_date, expiry_date, days_to_expiry, file_data, file_name,
                  file_type, len(file_data) if file_data else 0, notes, 'Active', created_by))
            doc_id = cursor.lastrowid
        
        conn.commit()
        return doc_id
    except Exception as e:
        print(f"Error adding document: {e}")
        return None
    finally:
        conn.close()


def get_documents(entity_type=None, entity_id=None, document_type=None, 
                 status=None, include_expired=True):
    """Get documents with optional filters"""
    conn = get_connection()
    
    query = """
        SELECT id, document_type, document_name, entity_type, entity_id, entity_name,
               issue_date, expiry_date, days_to_expiry, file_name, file_type, 
               file_size, notes, status, created_by, created_at
        FROM documents
        WHERE 1=1
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if entity_type:
        query += f" AND entity_type = {ph}"
        params.append(entity_type)
    
    if entity_id:
        query += f" AND entity_id = {ph}"
        params.append(entity_id)
    
    if document_type:
        query += f" AND document_type = {ph}"
        params.append(document_type)
    
    if status:
        query += f" AND status = {ph}"
        params.append(status)
    
    if not include_expired:
        query += f" AND (expiry_date IS NULL OR expiry_date >= {ph})"
        params.append(str(datetime.now().date()))
    
    query += " ORDER BY expiry_date ASC NULLS LAST, created_at DESC"
    
    df = pd.read_sql_query(query, get_engine(), params=params)
    conn.close()
    return df


def get_document_file(doc_id):
    """Get document file data"""
    conn = get_connection()
    cursor = conn.cursor()
    
    ph = '%s' if USE_POSTGRES else '?'
    cursor.execute(f"SELECT file_data, file_name, file_type FROM documents WHERE id = {ph}", (doc_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        if hasattr(result, 'keys'):
            return result['file_data'], result['file_name'], result['file_type']
        else:
            return result[0], result[1], result[2]
    return None, None, None


def delete_document(doc_id):
    """Delete a document record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    ph = '%s' if USE_POSTGRES else '?'
    
    try:
        cursor.execute(f"DELETE FROM documents WHERE id = {ph}", (doc_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting document: {e}")
        return False
    finally:
        conn.close()


def update_days_to_expiry():
    """Update days_to_expiry for all documents"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute("""
                UPDATE documents 
                SET days_to_expiry = expiry_date::date - CURRENT_DATE
                WHERE expiry_date IS NOT NULL
            """)
        else:
            cursor.execute("""
                UPDATE documents 
                SET days_to_expiry = CAST(julianday(expiry_date) - julianday('now') AS INTEGER)
                WHERE expiry_date IS NOT NULL
            """)
        
        conn.commit()
    except Exception as e:
        print(f"Error updating days_to_expiry: {e}")
    finally:
        conn.close()


def get_expiring_documents(days=30):
    """Get documents expiring within specified days"""
    conn = get_connection()
    
    today = datetime.now().date()
    cutoff = today + timedelta(days=days)
    
    ph = '%s' if USE_POSTGRES else '?'
    
    query = f"""
        SELECT id, document_type, document_name, entity_type, entity_name,
               expiry_date, days_to_expiry, status
        FROM documents
        WHERE expiry_date IS NOT NULL 
        AND expiry_date <= {ph}
        AND status = 'Active'
        ORDER BY expiry_date ASC
    """
    
    df = pd.read_sql_query(query, get_engine(), params=[str(cutoff)])
    conn.close()
    return df


def get_expired_documents():
    """Get all expired documents"""
    conn = get_connection()
    
    today = str(datetime.now().date())
    ph = '%s' if USE_POSTGRES else '?'
    
    query = f"""
        SELECT id, document_type, document_name, entity_type, entity_name,
               expiry_date, days_to_expiry, status
        FROM documents
        WHERE expiry_date IS NOT NULL 
        AND expiry_date < {ph}
        AND status = 'Active'
        ORDER BY expiry_date ASC
    """
    
    df = pd.read_sql_query(query, get_engine(), params=[today])
    conn.close()
    return df


def get_document_summary():
    """Get summary statistics for documents"""
    conn = get_connection()
    
    today = str(datetime.now().date())
    ph = '%s' if USE_POSTGRES else '?'
    
    try:
        total_query = "SELECT COUNT(*) as count FROM documents WHERE status = 'Active'"
        total_df = pd.read_sql_query(total_query, get_engine())
        total_docs = int(total_df['count'].values[0]) if not total_df.empty else 0
        
        expired_query = f"SELECT COUNT(*) as count FROM documents WHERE expiry_date < {ph} AND status = 'Active'"
        expired_df = pd.read_sql_query(expired_query, get_engine(), params=[today])
        expired = int(expired_df['count'].values[0]) if not expired_df.empty else 0
        
        cutoff_30 = str(datetime.now().date() + timedelta(days=30))
        expiring_30_query = f"SELECT COUNT(*) as count FROM documents WHERE expiry_date >= {ph} AND expiry_date <= {ph} AND status = 'Active'"
        expiring_30_df = pd.read_sql_query(expiring_30_query, get_engine(), params=[today, cutoff_30])
        expiring_30 = int(expiring_30_df['count'].values[0]) if not expiring_30_df.empty else 0
        
        cutoff_7 = str(datetime.now().date() + timedelta(days=7))
        expiring_7_query = f"SELECT COUNT(*) as count FROM documents WHERE expiry_date >= {ph} AND expiry_date <= {ph} AND status = 'Active'"
        expiring_7_df = pd.read_sql_query(expiring_7_query, get_engine(), params=[today, cutoff_7])
        expiring_7 = int(expiring_7_df['count'].values[0]) if not expiring_7_df.empty else 0
        
        valid = total_docs - expired
    except Exception as e:
        print(f"Error getting document summary: {e}")
        total_docs = 0
        valid = 0
        expired = 0
        expiring_7 = 0
        expiring_30 = 0
    
    conn.close()
    
    return {
        'total': total_docs,
        'valid': valid,
        'expired': expired,
        'expiring_7_days': expiring_7,
        'expiring_30_days': expiring_30
    }


# =============================================================================
# DOCUMENT TYPE DEFINITIONS
# =============================================================================

BUS_DOCUMENT_TYPES = [
    "ZINARA License",
    "Vehicle Insurance",
    "Passenger Insurance",
    "Fitness Certificate",
    "Route Permit",
    "Road Service License",
    "Registration Book",
    "Tax Clearance",
    "Police Clearance",
    "Other Bus Document"
]

EMPLOYEE_DOCUMENT_TYPES = [
    "Driver's License",
    "Defensive Driving Certificate",
    "Medical Certificate",
    "Police Clearance",
    "Employment Contract",
    "ID Copy",
    "Passport Copy",
    "Training Certificate",
    "Professional License",
    "Other Employee Document"
]

COMPANY_DOCUMENT_TYPES = [
    "Business License",
    "Tax Registration",
    "Company Registration",
    "Insurance Policy",
    "Lease Agreement",
    "Contract",
    "Permit",
    "Certificate",
    "Other Company Document"
]


# =============================================================================
# PAGE FUNCTION
# =============================================================================

def document_management_page():
    """Document management page"""
    
    st.header("📄 Document Management")
    st.markdown("Upload, store, and manage important documents with expiry tracking")
    st.markdown("---")
    
    can_add = has_permission('add_maintenance') or has_permission('manage_fleet')
    can_delete = has_permission('delete_maintenance') or has_permission('manage_fleet')
    
    # Update days to expiry on page load
    update_days_to_expiry()
    
    # Summary metrics
    summary = get_document_summary()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📄 Total Documents", summary['total'])
    with col2:
        st.metric("✅ Valid", summary['valid'])
    with col3:
        st.metric("❌ Expired", summary['expired'], 
                 delta=f"-{summary['expired']}" if summary['expired'] > 0 else None,
                 delta_color="inverse")
    with col4:
        st.metric("⚠️ Expiring (7 days)", summary['expiring_7_days'],
                 delta_color="inverse" if summary['expiring_7_days'] > 0 else "off")
    with col5:
        st.metric("🔔 Expiring (30 days)", summary['expiring_30_days'])
    
    st.markdown("---")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📤 Upload Document", 
        "📋 All Documents", 
        "🚌 Bus Documents",
        "👤 Employee Documents",
        "⚠️ Expiry Alerts"
    ])
    
    with tab1:
        if not can_add:
            st.warning("You don't have permission to upload documents")
        else:
            st.subheader("📤 Upload New Document")
            
            with st.form("upload_document_form"):
                entity_type = st.selectbox("Document For", ["Bus", "Employee", "Company"])
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if entity_type == "Bus":
                        buses = get_all_buses()
                        if buses:
                            bus_options = {}
                            for bus in buses:
                                if hasattr(bus, 'keys'):
                                    label = f"{bus['registration_number']} ({bus['make']} {bus['model']})"
                                    bus_options[label] = (bus['bus_number'], bus['registration_number'])
                                else:
                                    label = f"{bus[1]} ({bus[2]} {bus[3]})"
                                    bus_options[label] = (bus[0], bus[1])
                            
                            selected_entity = st.selectbox("Select Bus", list(bus_options.keys()))
                            entity_id, entity_name = bus_options.get(selected_entity, (None, None))
                        else:
                            st.warning("No buses found")
                            entity_id, entity_name = None, None
                        
                        document_type = st.selectbox("Document Type", BUS_DOCUMENT_TYPES)
                    
                    elif entity_type == "Employee":
                        employees = get_all_employees()
                        if employees:
                            emp_options = {}
                            for emp in employees:
                                if hasattr(emp, 'keys'):
                                    label = f"{emp['full_name']} ({emp['employee_id']}) - {emp['position']}"
                                    emp_options[label] = (emp['id'], emp['full_name'])
                                else:
                                    label = f"{emp[2]} ({emp[1]}) - {emp[3]}"
                                    emp_options[label] = (emp[0], emp[2])
                            
                            selected_entity = st.selectbox("Select Employee", list(emp_options.keys()))
                            entity_id, entity_name = emp_options.get(selected_entity, (None, None))
                        else:
                            st.warning("No employees found")
                            entity_id, entity_name = None, None
                        
                        document_type = st.selectbox("Document Type", EMPLOYEE_DOCUMENT_TYPES)
                    
                    else:
                        entity_id = "COMPANY"
                        entity_name = "Pavillion Coaches"
                        document_type = st.selectbox("Document Type", COMPANY_DOCUMENT_TYPES)
                
                with col2:
                    document_name = st.text_input("Document Name/Reference", 
                                                 placeholder="e.g., License #12345")
                    
                    issue_date = st.date_input("Issue Date", value=datetime.now().date())
                    
                    has_expiry = st.checkbox("Has Expiry Date", value=True)
                    
                    if has_expiry:
                        expiry_date = st.date_input("Expiry Date", 
                                                   value=datetime.now().date() + timedelta(days=365))
                    else:
                        expiry_date = None
                
                st.markdown("---")
                uploaded_file = st.file_uploader(
                    "Upload Document (PDF, Image, or Document)",
                    type=['pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'],
                    help="Maximum file size: 10MB"
                )
                
                notes = st.text_area("Notes", placeholder="Additional notes about this document...")
                
                submitted = st.form_submit_button("📤 Upload Document", type="primary", use_container_width=True)
                
                if submitted:
                    if not entity_id:
                        st.error("Please select an entity (Bus/Employee)")
                    elif not document_type:
                        st.error("Please select a document type")
                    else:
                        file_data = None
                        file_name = None
                        file_type = None
                        
                        if uploaded_file:
                            file_data = base64.b64encode(uploaded_file.read()).decode('utf-8')
                            file_name = uploaded_file.name
                            file_type = uploaded_file.type
                        
                        doc_id = add_document(
                            document_type=document_type,
                            document_name=document_name or document_type,
                            entity_type=entity_type,
                            entity_id=str(entity_id),
                            entity_name=entity_name,
                            issue_date=str(issue_date),
                            expiry_date=str(expiry_date) if expiry_date else None,
                            file_data=file_data,
                            file_name=file_name,
                            file_type=file_type,
                            notes=notes,
                            created_by=st.session_state.get('user', {}).get('username', 'system')
                        )
                        
                        if doc_id:
                            AuditLogger.log_action(
                                "Create", "Documents",
                                f"Uploaded {document_type} for {entity_type}: {entity_name}"
                            )
                            st.success(f"✅ Document uploaded successfully! (ID: {doc_id})")
                            st.rerun()
                        else:
                            st.error("Error uploading document")
    
    with tab2:
        st.subheader("📋 All Documents")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_entity = st.selectbox("Filter by Type", ["All", "Bus", "Employee", "Company"])
        
        with col2:
            filter_status = st.selectbox("Filter by Status", ["All", "Valid Only", "Expired Only"])
        
        with col3:
            search_term = st.text_input("Search", placeholder="Search by name...")
        
        entity_filter = filter_entity if filter_entity != "All" else None
        include_expired = filter_status != "Valid Only"
        
        docs_df = get_documents(entity_type=entity_filter, include_expired=include_expired)
        
        if filter_status == "Expired Only" and not docs_df.empty:
            docs_df = docs_df[docs_df['expiry_date'] < str(datetime.now().date())]
        
        if search_term and not docs_df.empty:
            docs_df = docs_df[
                docs_df['document_name'].str.contains(search_term, case=False, na=False) |
                docs_df['entity_name'].str.contains(search_term, case=False, na=False) |
                docs_df['document_type'].str.contains(search_term, case=False, na=False)
            ]
        
        if docs_df.empty:
            st.info("No documents found")
        else:
            today = datetime.now().date()
            
            def get_status_indicator(row):
                if pd.isna(row['expiry_date']):
                    return "🔵 No Expiry"
                try:
                    exp_date = datetime.strptime(str(row['expiry_date'])[:10], '%Y-%m-%d').date()
                    days = (exp_date - today).days
                    if days < 0:
                        return "🔴 Expired"
                    elif days <= 7:
                        return "🟠 Critical"
                    elif days <= 30:
                        return "🟡 Warning"
                    else:
                        return "🟢 Valid"
                except:
                    return "🔵 No Expiry"
            
            docs_df['Status'] = docs_df.apply(get_status_indicator, axis=1)
            
            display_df = docs_df[[
                'Status', 'document_type', 'document_name', 'entity_type', 
                'entity_name', 'issue_date', 'expiry_date', 'file_name'
            ]].copy()
            
            display_df.columns = ['Status', 'Type', 'Name/Ref', 'For', 'Entity', 
                                 'Issue Date', 'Expiry Date', 'File']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### 📥 Download Document")
            
            doc_options = {
                f"ID:{row['id']} - {row['document_type']} - {row['entity_name']}": row['id']
                for _, row in docs_df.iterrows()
            }
            
            if doc_options:
                selected_doc = st.selectbox("Select Document to Download", list(doc_options.keys()))
                
                if selected_doc:
                    doc_id = doc_options[selected_doc]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("📥 Download File"):
                            file_data, file_name, file_type = get_document_file(doc_id)
                            
                            if file_data:
                                decoded_data = base64.b64decode(file_data)
                                st.download_button(
                                    label=f"⬇️ Download {file_name}",
                                    data=decoded_data,
                                    file_name=file_name,
                                    mime=file_type
                                )
                            else:
                                st.warning("No file attached to this document")
                    
                    with col2:
                        if can_delete:
                            if st.button("🗑️ Delete Document"):
                                st.session_state[f'confirm_delete_doc_{doc_id}'] = True
                            
                            if st.session_state.get(f'confirm_delete_doc_{doc_id}', False):
                                st.warning("⚠️ Are you sure?")
                                col_y, col_n = st.columns(2)
                                with col_y:
                                    if st.button("✅ Yes", key=f"yes_{doc_id}"):
                                        if delete_document(doc_id):
                                            AuditLogger.log_action("Delete", "Documents", f"Deleted document ID:{doc_id}")
                                            st.success("Deleted!")
                                            del st.session_state[f'confirm_delete_doc_{doc_id}']
                                            st.rerun()
                                with col_n:
                                    if st.button("❌ No", key=f"no_{doc_id}"):
                                        del st.session_state[f'confirm_delete_doc_{doc_id}']
                                        st.rerun()
    
    with tab3:
        st.subheader("🚌 Bus Documents")
        
        buses = get_all_buses()
        
        if not buses:
            st.warning("No buses found")
        else:
            bus_options = {}
            for bus in buses:
                if hasattr(bus, 'keys'):
                    label = f"{bus['registration_number']} ({bus['make']} {bus['model']}) - {bus['status']}"
                    bus_options[label] = bus['bus_number']
                else:
                    label = f"{bus[1]} ({bus[2]} {bus[3]}) - {bus[4]}"
                    bus_options[label] = bus[0]
            
            selected_bus = st.selectbox("Select Bus", list(bus_options.keys()))
            
            if selected_bus:
                bus_id = bus_options[selected_bus]
                bus_docs = get_documents(entity_type="Bus", entity_id=str(bus_id))
                
                if bus_docs.empty:
                    st.info(f"No documents uploaded for this bus")
                else:
                    st.markdown("### 📋 Document Status")
                    
                    today = datetime.now().date()
                    
                    for doc_type in BUS_DOCUMENT_TYPES[:-1]:
                        doc = bus_docs[bus_docs['document_type'] == doc_type]
                        
                        if doc.empty:
                            st.markdown(f"⚪ **{doc_type}**: Not uploaded")
                        else:
                            doc_row = doc.iloc[0]
                            exp_date = doc_row['expiry_date']
                            
                            if pd.isna(exp_date):
                                st.markdown(f"🔵 **{doc_type}**: No expiry")
                            else:
                                try:
                                    exp = datetime.strptime(str(exp_date)[:10], '%Y-%m-%d').date()
                                    days = (exp - today).days
                                    
                                    if days < 0:
                                        st.markdown(f"🔴 **{doc_type}**: Expired ({abs(days)} days ago)")
                                    elif days <= 7:
                                        st.markdown(f"🟠 **{doc_type}**: Expires in {days} days! ⚠️")
                                    elif days <= 30:
                                        st.markdown(f"🟡 **{doc_type}**: Expires in {days} days")
                                    else:
                                        st.markdown(f"🟢 **{doc_type}**: Valid until {exp_date}")
                                except:
                                    st.markdown(f"🔵 **{doc_type}**: No expiry")
                    
                    st.markdown("---")
                    st.markdown("### All Documents for This Bus")
                    
                    display_bus_docs = bus_docs[[
                        'document_type', 'document_name', 'issue_date', 
                        'expiry_date', 'file_name', 'status'
                    ]].copy()
                    display_bus_docs.columns = ['Type', 'Name/Ref', 'Issue Date', 
                                                'Expiry Date', 'File', 'Status']
                    
                    st.dataframe(display_bus_docs, use_container_width=True, hide_index=True)
    
    with tab4:
        st.subheader("👤 Employee Documents")
        
        employees = get_all_employees()
        
        if not employees:
            st.warning("No employees found")
        else:
            emp_options = {}
            for emp in employees:
                if hasattr(emp, 'keys'):
                    label = f"{emp['full_name']} ({emp['employee_id']}) - {emp['position']}"
                    emp_options[label] = emp['id']
                else:
                    label = f"{emp[2]} ({emp[1]}) - {emp[3]}"
                    emp_options[label] = emp[0]
            
            selected_emp = st.selectbox("Select Employee", list(emp_options.keys()))
            
            if selected_emp:
                emp_id = emp_options[selected_emp]
                emp_docs = get_documents(entity_type="Employee", entity_id=str(emp_id))
                
                if emp_docs.empty:
                    st.info(f"No documents uploaded for this employee")
                else:
                    st.markdown("### 📋 Document Status")
                    
                    today = datetime.now().date()
                    
                    for doc_type in EMPLOYEE_DOCUMENT_TYPES[:-1]:
                        doc = emp_docs[emp_docs['document_type'] == doc_type]
                        
                        if doc.empty:
                            st.markdown(f"⚪ **{doc_type}**: Not uploaded")
                        else:
                            doc_row = doc.iloc[0]
                            exp_date = doc_row['expiry_date']
                            
                            if pd.isna(exp_date):
                                st.markdown(f"🔵 **{doc_type}**: No expiry")
                            else:
                                try:
                                    exp = datetime.strptime(str(exp_date)[:10], '%Y-%m-%d').date()
                                    days = (exp - today).days
                                    
                                    if days < 0:
                                        st.markdown(f"🔴 **{doc_type}**: Expired ({abs(days)} days ago)")
                                    elif days <= 7:
                                        st.markdown(f"🟠 **{doc_type}**: Expires in {days} days! ⚠️")
                                    elif days <= 30:
                                        st.markdown(f"🟡 **{doc_type}**: Expires in {days} days")
                                    else:
                                        st.markdown(f"🟢 **{doc_type}**: Valid until {exp_date}")
                                except:
                                    st.markdown(f"🔵 **{doc_type}**: No expiry")
                    
                    st.markdown("---")
                    st.markdown("### All Documents for This Employee")
                    
                    display_emp_docs = emp_docs[[
                        'document_type', 'document_name', 'issue_date', 
                        'expiry_date', 'file_name', 'status'
                    ]].copy()
                    display_emp_docs.columns = ['Type', 'Name/Ref', 'Issue Date', 
                                                'Expiry Date', 'File', 'Status']
                    
                    st.dataframe(display_emp_docs, use_container_width=True, hide_index=True)
    
    with tab5:
        st.subheader("⚠️ Expiry Alerts")
        
        st.markdown("### 🔴 Expired Documents")
        
        expired_docs = get_expired_documents()
        
        if expired_docs.empty:
            st.success("✅ No expired documents!")
        else:
            st.error(f"⚠️ {len(expired_docs)} document(s) have expired!")
            
            for _, doc in expired_docs.iterrows():
                days_expired = abs(int(doc['days_to_expiry'])) if pd.notna(doc['days_to_expiry']) else 0
                st.markdown(f"""
                - **{doc['document_type']}** for {doc['entity_type']}: **{doc['entity_name']}**
                  - Expired: {doc['expiry_date']} ({days_expired} days ago)
                """)
        
        st.markdown("---")
        
        st.markdown("### 🟠 Expiring Within 7 Days")
        
        expiring_7 = get_expiring_documents(days=7)
        if not expiring_7.empty:
            expiring_7 = expiring_7[expiring_7['days_to_expiry'] >= 0]
        
        if expiring_7.empty:
            st.success("✅ No documents expiring within 7 days")
        else:
            st.warning(f"⚠️ {len(expiring_7)} document(s) expiring within 7 days!")
            
            for _, doc in expiring_7.iterrows():
                days_left = int(doc['days_to_expiry']) if pd.notna(doc['days_to_expiry']) else 0
                st.markdown(f"""
                - **{doc['document_type']}** for {doc['entity_type']}: **{doc['entity_name']}**
                  - Expires: {doc['expiry_date']} ({days_left} days left)
                """)
        
        st.markdown("---")
        
        st.markdown("### 🟡 Expiring Within 30 Days")
        
        expiring_30 = get_expiring_documents(days=30)
        if not expiring_30.empty:
            expiring_30 = expiring_30[expiring_30['days_to_expiry'] > 7]
        
        if expiring_30.empty:
            st.success("✅ No additional documents expiring within 30 days")
        else:
            st.info(f"📢 {len(expiring_30)} document(s) expiring within 30 days")
            
            for _, doc in expiring_30.iterrows():
                days_left = int(doc['days_to_expiry']) if pd.notna(doc['days_to_expiry']) else 0
                st.markdown(f"""
                - **{doc['document_type']}** for {doc['entity_type']}: **{doc['entity_name']}**
                  - Expires: {doc['expiry_date']} ({days_left} days left)
                """)
        
        st.markdown("---")
        
        st.markdown("### 🔔 Expiring Within 90 Days")
        
        expiring_90 = get_expiring_documents(days=90)
        if not expiring_90.empty:
            expiring_90 = expiring_90[expiring_90['days_to_expiry'] > 30]
        
        if expiring_90.empty:
            st.success("✅ No additional documents expiring within 90 days")
        else:
            st.info(f"📋 {len(expiring_90)} document(s) expiring within 90 days")
            
            display_90 = expiring_90[[
                'document_type', 'entity_type', 'entity_name', 'expiry_date', 'days_to_expiry'
            ]].copy()
            display_90.columns = ['Document Type', 'For', 'Entity', 'Expiry Date', 'Days Left']
            st.dataframe(display_90, use_container_width=True, hide_index=True)

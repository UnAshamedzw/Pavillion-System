"""
pages_approvals.py - Centralized Approvals Center
Pavillion Coaches Bus Management System

Consolidates all pending approvals in one place:
- Payroll periods awaiting approval
- Leave requests pending
- Loan requests pending
- Employee complaints/feedback
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import get_connection, get_engine, USE_POSTGRES, get_placeholder
from audit_logger import AuditLogger
from auth import has_permission


# =============================================================================
# DATA RETRIEVAL FUNCTIONS
# =============================================================================

def get_pending_payroll():
    """Get payroll periods awaiting approval"""
    conn = get_connection()
    
    query = """
        SELECT pp.*, 
               (SELECT COUNT(*) FROM payroll_records WHERE payroll_period_id = pp.id) as employee_count,
               (SELECT SUM(net_pay) FROM payroll_records WHERE payroll_period_id = pp.id) as total_amount
        FROM payroll_periods pp
        WHERE pp.status = 'processing'
        ORDER BY pp.created_at DESC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine())
    except Exception as e:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_pending_leave():
    """Get leave requests awaiting approval"""
    conn = get_connection()
    
    query = """
        SELECT lr.*, e.full_name, e.position, e.department
        FROM leave_records lr
        JOIN employees e ON lr.employee_id = e.id
        WHERE lr.status = 'Pending'
        ORDER BY lr.start_date ASC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine())
    except Exception as e:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_pending_loan_requests():
    """Get loan requests awaiting approval"""
    conn = get_connection()
    
    query = """
        SELECT er.*, e.full_name, e.position, e.department, e.salary
        FROM employee_requests er
        JOIN employees e ON er.employee_id = e.id
        WHERE er.request_type = 'Loan Request' AND er.status = 'pending'
        ORDER BY er.created_at ASC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine())
    except Exception as e:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_open_complaints():
    """Get open complaints/feedback"""
    conn = get_connection()
    
    query = """
        SELECT ec.*, e.full_name, e.position, e.department
        FROM employee_complaints ec
        JOIN employees e ON ec.employee_id = e.id
        WHERE ec.status = 'open'
        ORDER BY ec.created_at ASC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine())
    except Exception as e:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_payroll_records(period_id):
    """Get payroll records for a period"""
    conn = get_connection()
    ph = get_placeholder()
    
    query = f"""
        SELECT * FROM payroll_records
        WHERE payroll_period_id = {ph}
        ORDER BY employee_name
    """
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=(period_id,))
    except Exception as e:
        df = pd.DataFrame()
    
    conn.close()
    return df


# =============================================================================
# ACTION FUNCTIONS
# =============================================================================

def approve_payroll(period_id, approver):
    """Approve a payroll period"""
    conn = get_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    
    try:
        if USE_POSTGRES:
            cursor.execute(f"""
                UPDATE payroll_periods 
                SET status = 'approved', approved_by = {ph}, approved_at = CURRENT_TIMESTAMP
                WHERE id = {ph}
            """, (approver, period_id))
        else:
            cursor.execute(f"""
                UPDATE payroll_periods 
                SET status = 'approved', approved_by = {ph}, approved_at = datetime('now')
                WHERE id = {ph}
            """, (approver, period_id))
        
        conn.commit()
        
        AuditLogger.log_action(
            "Approve", "Payroll",
            f"Payroll period #{period_id} approved by {approver}"
        )
        
        return True
    except Exception as e:
        conn.rollback()
        print(f"Approve payroll error: {e}")
        return False
    finally:
        conn.close()


def reject_payroll(period_id, approver, reason):
    """Reject/return a payroll period for corrections"""
    conn = get_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    
    try:
        cursor.execute(f"""
            UPDATE payroll_periods 
            SET status = 'draft', rejection_reason = {ph}
            WHERE id = {ph}
        """, (reason, period_id))
        
        conn.commit()
        
        AuditLogger.log_action(
            "Reject", "Payroll",
            f"Payroll period #{period_id} returned for corrections by {approver}: {reason}"
        )
        
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()


def approve_leave(leave_id, approver):
    """Approve a leave request"""
    conn = get_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    
    try:
        if USE_POSTGRES:
            cursor.execute(f"""
                UPDATE leave_records 
                SET status = 'Approved', approved_by = {ph}, approved_date = CURRENT_DATE
                WHERE id = {ph}
            """, (approver, leave_id))
        else:
            cursor.execute(f"""
                UPDATE leave_records 
                SET status = 'Approved', approved_by = {ph}, approved_date = date('now')
                WHERE id = {ph}
            """, (approver, leave_id))
        
        conn.commit()
        
        AuditLogger.log_action(
            "Approve", "Leave",
            f"Leave request #{leave_id} approved by {approver}"
        )
        
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()


def reject_leave(leave_id, approver, reason):
    """Reject a leave request"""
    conn = get_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    
    try:
        if USE_POSTGRES:
            cursor.execute(f"""
                UPDATE leave_records 
                SET status = 'Rejected', approved_by = {ph}, approved_date = CURRENT_DATE,
                    rejection_reason = {ph}
                WHERE id = {ph}
            """, (approver, reason, leave_id))
        else:
            cursor.execute(f"""
                UPDATE leave_records 
                SET status = 'Rejected', approved_by = {ph}, approved_date = date('now'),
                    rejection_reason = {ph}
                WHERE id = {ph}
            """, (approver, reason, leave_id))
        
        conn.commit()
        
        AuditLogger.log_action(
            "Reject", "Leave",
            f"Leave request #{leave_id} rejected by {approver}: {reason}"
        )
        
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()


def approve_loan_request(request_id, approver, monthly_deduction):
    """Approve a loan request and create the loan"""
    conn = get_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    
    try:
        # Get request details
        cursor.execute(f"SELECT * FROM employee_requests WHERE id = {ph}", (request_id,))
        request = cursor.fetchone()
        
        if not request:
            return False
        
        if hasattr(request, 'keys'):
            employee_id = request['employee_id']
            amount = request['amount']
            reason = request['request_details']
        else:
            employee_id = request[1]  # employee_id
            amount = request[4]  # amount
            reason = request[3]  # request_details
        
        # Create the loan
        if USE_POSTGRES:
            cursor.execute(f"""
                INSERT INTO employee_loans 
                (employee_id, loan_type, principal_amount, balance, monthly_deduction, 
                 date_issued, reason, status)
                VALUES ({ph}, 'Personal Loan', {ph}, {ph}, {ph}, CURRENT_DATE, {ph}, 'active')
            """, (employee_id, amount, amount, monthly_deduction, reason))
        else:
            cursor.execute(f"""
                INSERT INTO employee_loans 
                (employee_id, loan_type, principal_amount, balance, monthly_deduction, 
                 date_issued, reason, status)
                VALUES ({ph}, 'Personal Loan', {ph}, {ph}, {ph}, date('now'), {ph}, 'active')
            """, (employee_id, amount, amount, monthly_deduction, reason))
        
        # Update request status
        cursor.execute(f"""
            UPDATE employee_requests 
            SET status = 'approved', reviewed_by = {ph}, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = {ph}
        """, (approver, request_id))
        
        conn.commit()
        
        AuditLogger.log_action(
            "Approve", "Loan Request",
            f"Loan request #{request_id} approved by {approver} - Amount: ${amount}, Monthly: ${monthly_deduction}"
        )
        
        return True
    except Exception as e:
        conn.rollback()
        print(f"Approve loan error: {e}")
        return False
    finally:
        conn.close()


def reject_loan_request(request_id, approver, reason):
    """Reject a loan request"""
    conn = get_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    
    try:
        if USE_POSTGRES:
            cursor.execute(f"""
                UPDATE employee_requests 
                SET status = 'rejected', reviewed_by = {ph}, reviewed_at = CURRENT_TIMESTAMP,
                    review_notes = {ph}
                WHERE id = {ph}
            """, (approver, reason, request_id))
        else:
            cursor.execute(f"""
                UPDATE employee_requests 
                SET status = 'rejected', reviewed_by = {ph}, reviewed_at = datetime('now'),
                    review_notes = {ph}
                WHERE id = {ph}
            """, (approver, reason, request_id))
        
        conn.commit()
        
        AuditLogger.log_action(
            "Reject", "Loan Request",
            f"Loan request #{request_id} rejected by {approver}: {reason}"
        )
        
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()


def respond_complaint(complaint_id, responder, response, new_status):
    """Respond to a complaint"""
    conn = get_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    
    try:
        if USE_POSTGRES:
            cursor.execute(f"""
                UPDATE employee_complaints 
                SET status = {ph}, response = {ph}, responded_by = {ph}, 
                    responded_at = CURRENT_TIMESTAMP
                WHERE id = {ph}
            """, (new_status, response, responder, complaint_id))
        else:
            cursor.execute(f"""
                UPDATE employee_complaints 
                SET status = {ph}, response = {ph}, responded_by = {ph}, 
                    responded_at = datetime('now')
                WHERE id = {ph}
            """, (new_status, response, responder, complaint_id))
        
        conn.commit()
        
        AuditLogger.log_action(
            "Respond", "Complaint",
            f"Complaint #{complaint_id} responded by {responder} - Status: {new_status}"
        )
        
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()


# =============================================================================
# MAIN PAGE
# =============================================================================

def approvals_center_page():
    """Centralized Approvals Center"""
    
    st.header("✅ Approvals Center")
    st.markdown("Review and approve pending requests across all modules")
    st.markdown("---")
    
    # Get counts for summary
    pending_payroll = get_pending_payroll()
    pending_leave = get_pending_leave()
    pending_loans = get_pending_loan_requests()
    open_complaints = get_open_complaints()
    
    payroll_count = len(pending_payroll)
    leave_count = len(pending_leave)
    loan_count = len(pending_loans)
    complaint_count = len(open_complaints)
    total_pending = payroll_count + leave_count + loan_count + complaint_count
    
    # Summary Cards
    st.subheader("📊 Pending Items Summary")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📋 Total Pending", total_pending)
    
    with col2:
        color = "🔴" if payroll_count > 0 else "✅"
        st.metric(f"{color} Payroll", payroll_count)
    
    with col3:
        color = "🟠" if leave_count > 0 else "✅"
        st.metric(f"{color} Leave", leave_count)
    
    with col4:
        color = "🟡" if loan_count > 0 else "✅"
        st.metric(f"{color} Loans", loan_count)
    
    with col5:
        color = "🔵" if complaint_count > 0 else "✅"
        st.metric(f"{color} Complaints", complaint_count)
    
    st.markdown("---")
    
    # Tabs for each approval type
    tab1, tab2, tab3, tab4 = st.tabs([
        f"💰 Payroll ({payroll_count})",
        f"📅 Leave ({leave_count})",
        f"💳 Loans ({loan_count})",
        f"📝 Complaints ({complaint_count})"
    ])
    
    with tab1:
        payroll_approvals_tab(pending_payroll)
    
    with tab2:
        leave_approvals_tab(pending_leave)
    
    with tab3:
        loan_approvals_tab(pending_loans)
    
    with tab4:
        complaints_tab(open_complaints)


def payroll_approvals_tab(pending_payroll):
    """Payroll approvals tab"""
    
    st.subheader("💰 Payroll Awaiting Approval")
    
    can_approve = has_permission('approve_payroll')
    
    if not can_approve:
        st.warning("⚠️ You don't have permission to approve payroll. Contact your administrator.")
    
    if pending_payroll.empty:
        st.success("✅ No payroll periods awaiting approval")
        return
    
    for _, period in pending_payroll.iterrows():
        period_id = period['id']
        period_name = period.get('period_name', 'Unknown Period')
        emp_count = period.get('employee_count', 0)
        total_amount = period.get('total_amount', 0) or 0
        created_by = period.get('created_by', 'Unknown')
        created_at = period.get('created_at', 'Unknown')
        
        with st.expander(f"📋 {period_name} - ${total_amount:,.2f} ({emp_count} employees)", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"**Period:** {period_name}")
                st.markdown(f"**Employees:** {emp_count}")
            
            with col2:
                st.markdown(f"**Total Amount:** ${total_amount:,.2f}")
                st.markdown(f"**Prepared by:** {created_by}")
            
            with col3:
                st.markdown(f"**Submitted:** {created_at}")
            
            # Show employee breakdown
            records = get_payroll_records(period_id)
            
            if not records.empty:
                st.markdown("---")
                st.markdown("**Employee Breakdown:**")
                
                display_df = records[['employee_name', 'employee_role', 'gross_earnings', 
                                     'total_deductions', 'net_pay']].copy()
                display_df.columns = ['Employee', 'Role', 'Gross', 'Deductions', 'Net Pay']
                display_df['Gross'] = display_df['Gross'].apply(lambda x: f"${x:,.2f}")
                display_df['Deductions'] = display_df['Deductions'].apply(lambda x: f"${x:,.2f}")
                display_df['Net Pay'] = display_df['Net Pay'].apply(lambda x: f"${x:,.2f}")
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Approval buttons
            if can_approve:
                st.markdown("---")
                
                col_approve, col_reject = st.columns(2)
                
                with col_approve:
                    if st.button("✅ Approve Payroll", key=f"approve_payroll_{period_id}", 
                                type="primary", use_container_width=True):
                        if approve_payroll(period_id, st.session_state['user']['username']):
                            st.success("✅ Payroll approved successfully!")
                            st.rerun()
                        else:
                            st.error("Error approving payroll")
                
                with col_reject:
                    with st.popover("❌ Return for Corrections"):
                        reason = st.text_area("Reason for returning:", key=f"reject_reason_{period_id}")
                        if st.button("Submit", key=f"submit_reject_{period_id}"):
                            if reason:
                                if reject_payroll(period_id, st.session_state['user']['username'], reason):
                                    st.success("Payroll returned for corrections")
                                    st.rerun()
                            else:
                                st.warning("Please provide a reason")


def leave_approvals_tab(pending_leave):
    """Leave approvals tab"""
    
    st.subheader("📅 Leave Requests Awaiting Approval")
    
    can_approve = has_permission('approve_leave') or has_permission('edit_leave')
    
    if not can_approve:
        st.warning("⚠️ You don't have permission to approve leave requests.")
    
    if pending_leave.empty:
        st.success("✅ No leave requests awaiting approval")
        return
    
    for _, leave in pending_leave.iterrows():
        leave_id = leave['id']
        emp_name = leave.get('full_name', 'Unknown')
        position = leave.get('position', '')
        department = leave.get('department', '')
        leave_type = leave.get('leave_type', 'Unknown')
        start_date = leave.get('start_date', '')
        end_date = leave.get('end_date', '')
        reason = leave.get('reason', 'No reason provided')
        
        # Calculate days
        try:
            start = datetime.strptime(str(start_date), '%Y-%m-%d').date()
            end = datetime.strptime(str(end_date), '%Y-%m-%d').date()
            days = (end - start).days + 1
        except Exception as e:
            days = 'N/A'
        
        with st.expander(f"📅 {emp_name} - {leave_type} ({days} days)", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Employee:** {emp_name}")
                st.markdown(f"**Position:** {position}")
                st.markdown(f"**Department:** {department}")
            
            with col2:
                st.markdown(f"**Leave Type:** {leave_type}")
                st.markdown(f"**Dates:** {start_date} to {end_date}")
                st.markdown(f"**Duration:** {days} day(s)")
            
            st.info(f"**Reason:** {reason}")
            
            # Approval buttons
            if can_approve:
                st.markdown("---")
                
                col_approve, col_reject = st.columns(2)
                
                with col_approve:
                    if st.button("✅ Approve", key=f"approve_leave_{leave_id}", 
                                type="primary", use_container_width=True):
                        if approve_leave(leave_id, st.session_state['user']['username']):
                            st.success("✅ Leave approved!")
                            st.rerun()
                        else:
                            st.error("Error approving leave")
                
                with col_reject:
                    with st.popover("❌ Reject"):
                        reason_input = st.text_area("Reason for rejection:", key=f"leave_reject_{leave_id}")
                        if st.button("Submit Rejection", key=f"submit_leave_reject_{leave_id}"):
                            if reason_input:
                                if reject_leave(leave_id, st.session_state['user']['username'], reason_input):
                                    st.success("Leave request rejected")
                                    st.rerun()
                            else:
                                st.warning("Please provide a reason")


def loan_approvals_tab(pending_loans):
    """Loan request approvals tab"""
    
    st.subheader("💳 Loan Requests Awaiting Approval")
    
    can_approve = has_permission('approve_loans') or has_permission('edit_loans') or has_permission('add_loan')
    
    if not can_approve:
        st.warning("⚠️ You don't have permission to approve loan requests.")
    
    if pending_loans.empty:
        st.success("✅ No loan requests awaiting approval")
        return
    
    for _, loan in pending_loans.iterrows():
        request_id = loan['id']
        emp_name = loan.get('full_name', 'Unknown')
        position = loan.get('position', '')
        department = loan.get('department', '')
        salary = loan.get('salary', 0) or 0
        amount = loan.get('amount', 0) or 0
        reason = loan.get('request_details', 'No reason provided')
        created_at = loan.get('created_at', '')
        
        with st.expander(f"💳 {emp_name} - ${amount:,.2f} Loan Request", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Employee:** {emp_name}")
                st.markdown(f"**Position:** {position}")
                st.markdown(f"**Department:** {department}")
                st.markdown(f"**Current Salary:** ${salary:,.2f}")
            
            with col2:
                st.markdown(f"**Requested Amount:** ${amount:,.2f}")
                st.markdown(f"**Submitted:** {created_at}")
                
                # Suggested monthly deduction (10% of salary or less)
                suggested_monthly = min(amount, salary * 0.1) if salary > 0 else amount / 6
                st.markdown(f"**Suggested Monthly:** ${suggested_monthly:,.2f}")
            
            st.info(f"**Purpose:** {reason}")
            
            # Approval buttons
            if can_approve:
                st.markdown("---")
                
                col_approve, col_reject = st.columns(2)
                
                with col_approve:
                    with st.popover("✅ Approve Loan", use_container_width=True):
                        monthly = st.number_input(
                            "Monthly Deduction Amount ($)", 
                            min_value=10.0, 
                            value=float(suggested_monthly),
                            step=10.0,
                            key=f"monthly_{request_id}"
                        )
                        
                        months_to_pay = amount / monthly if monthly > 0 else 0
                        st.caption(f"Will be paid off in ~{months_to_pay:.1f} months")
                        
                        if st.button("Confirm Approval", key=f"confirm_loan_{request_id}", type="primary"):
                            if approve_loan_request(request_id, st.session_state['user']['username'], monthly):
                                st.success("✅ Loan approved and created!")
                                st.rerun()
                            else:
                                st.error("Error approving loan")
                
                with col_reject:
                    with st.popover("❌ Reject"):
                        reason_input = st.text_area("Reason for rejection:", key=f"loan_reject_{request_id}")
                        if st.button("Submit Rejection", key=f"submit_loan_reject_{request_id}"):
                            if reason_input:
                                if reject_loan_request(request_id, st.session_state['user']['username'], reason_input):
                                    st.success("Loan request rejected")
                                    st.rerun()
                            else:
                                st.warning("Please provide a reason")


def complaints_tab(open_complaints):
    """Complaints/feedback tab"""
    
    st.subheader("📝 Open Complaints & Feedback")
    
    can_respond = has_permission('view_complaints') or has_permission('edit_employees')
    
    if not can_respond:
        st.warning("⚠️ You don't have permission to respond to complaints.")
    
    if open_complaints.empty:
        st.success("✅ No open complaints or feedback")
        return
    
    for _, complaint in open_complaints.iterrows():
        complaint_id = complaint['id']
        emp_name = complaint.get('full_name', 'Anonymous')
        subject = complaint.get('subject', 'No Subject')
        category = complaint.get('category', 'General')
        description = complaint.get('description', '')
        created_at = complaint.get('created_at', '')
        
        with st.expander(f"📝 {subject} - {emp_name}", expanded=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**From:** {emp_name}")
                st.markdown(f"**Subject:** {subject}")
                st.markdown(f"**Category:** {category}")
            
            with col2:
                st.markdown(f"**Submitted:** {created_at}")
            
            st.markdown("---")
            st.markdown("**Description:**")
            st.markdown(description)
            
            # Response
            if can_respond:
                st.markdown("---")
                
                response = st.text_area("Your Response:", key=f"response_{complaint_id}")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("📧 Respond & Close", key=f"close_{complaint_id}", type="primary"):
                        if response:
                            if respond_complaint(complaint_id, st.session_state['user']['username'], 
                                                response, 'closed'):
                                st.success("Response sent and complaint closed!")
                                st.rerun()
                        else:
                            st.warning("Please provide a response")
                
                with col2:
                    if st.button("📋 Respond & Keep Open", key=f"keep_open_{complaint_id}"):
                        if response:
                            if respond_complaint(complaint_id, st.session_state['user']['username'], 
                                                response, 'in_progress'):
                                st.success("Response sent!")
                                st.rerun()
                        else:
                            st.warning("Please provide a response")
                
                with col3:
                    if st.button("🗑️ Dismiss", key=f"dismiss_{complaint_id}"):
                        if respond_complaint(complaint_id, st.session_state['user']['username'], 
                                            "Dismissed", 'dismissed'):
                            st.info("Complaint dismissed")
                            st.rerun()
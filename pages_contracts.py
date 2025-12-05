"""
pages_contracts.py - Employment Contract Generator with Editable Templates
Pavillion Coaches Bus Management System
Generate printable employment contracts with employee data auto-filled
Templates are stored in database and can be edited anytime
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from database import get_connection, get_engine, USE_POSTGRES
from audit_logger import AuditLogger
from auth import has_permission
import subprocess
import os
import tempfile
import re


# =============================================================================
# DEFAULT CONTRACT TEMPLATE
# =============================================================================

DEFAULT_CONTRACT_TEMPLATE = """FORESTVIEW ENTERPRISES

CONTRACT OF EMPLOYMENT

In this contract the terms and conditions of employment shall apply to parties mentioned herein under and be interpreted in a manner in which is consistent with NECTOI Statutory Instrument for Transport sector and Labour Act Chapter (28:01). The contract is hereby entered into between:

FORESTVIEW ENTERPRISES (PVT) LTD 3172 PROSPECT WAY HARARE

AND

===== EMPLOYEE DETAILS =====

Name of employee: {{EMPLOYEE_NAME}}

Date of Birth: {{DATE_OF_BIRTH}}

ID Number: {{NATIONAL_ID}}

Residential Address: {{ADDRESS}}

Cell: {{PHONE}}    Email address: {{EMAIL}}

Next of Kin: {{NEXT_OF_KIN}}    Contact: {{NEXT_OF_KIN_PHONE}}

Relationship: {{NEXT_OF_KIN_RELATIONSHIP}}

===== NATURE AND DURATION OF CONTRACT =====

The employee shall be on a fixed term contract commencing {{CONTRACT_START_DATE}} and expires on {{CONTRACT_END_DATE}}. In any event, renewal of this contract will solely be based on your performance. This contract is entered into with no guarantee of long term employment or any expectation of further renewals.

===== JOB TITLE AND REMUNERATION =====

The employee shall be employed in the capacity of {{POSITION}}. An employee is entitled to understand fully the job description as it is central to this contract.

Remuneration shall be paid on a weekly or monthly basis, as mutually agreed upon, and no later than seven (7) days after the designated payday.

Please note the following:
1. This is a discretionary structure that can be revoked anytime.
2. United States Dollar payroll is on condition that revenue is generated in foreign currency.
3. Should there be changes in Government laws of Zimbabwe, Pavillion will revert to payment of salaries in Zimbabwean dollars in compliance.

===== HOURS OF WORK =====

The ordinary hours of work shall be as prescribed in the CBA for the Transport Operating Industry. Currently these are 26 days per month.

===== OCCUPATIONAL HEALTH AND SAFETY RESPONSIBILITIES =====

The employee shall:
• Be formally dressed as directed by the management.
• Attend safety meetings as designed by the organisation.
• Identify and discover hazards in the work environment and report to management.
• Report incidents to the supervisor at the end of every trip attained.
• Behave in an expected accidents prevention manners.
• Give expert knowledge to ensure maximum quality of work hence carrying the image of the organisation.

===== DEDUCTIONS =====

All deductions shall be in terms of the CBA for the sector and the Labour Act Chapter 28:01

===== ABSENCE FROM WORK =====

In the event that an employee is unable to attend work for any reason, the employee shall notify the management which shall then exercise its discretion to pay for such time off. Where an employee is absent from work without valid and justifiable reason, the employer reserves the right to apply the provisions of labour regulations.

===== TERMINATION OF CONTRACT =====

This contract may be terminated mutually upon either party giving 2 weeks' notice of such termination and during probationary period 24 hours' notice.

===== CONFIDENTIALITY =====

By virtue of employment the employee will be possessed and have access to employer's trade secrets including sensitive matters which relate to the business. No employee is allowed to reveal or expose any confidential information to anyone or even the competitor. Should the employee breach this clause by divulging such information, this shall be deemed as punishable act of misconduct and appropriate disciplinary procedures shall be exercised.

===== GENERAL CONDITIONS =====

The employee specific duties shall be as defined in the employee's job description and will however include any other duties assigned by management.

I {{EMPLOYEE_NAME}} Signature ............................ Date ............................ acknowledge the receipt of this contract and agree with terms and conditions herein.

Signed by

..................................................................... Date ............/................../..................
(HUMAN RESOURCES MANAGER)

..................................................................... Date ............/................./..................
(DIRECTOR)

STAMP
"""

# Available placeholders for reference
AVAILABLE_PLACEHOLDERS = {
    "{{EMPLOYEE_NAME}}": "Employee's full name",
    "{{DATE_OF_BIRTH}}": "Date of birth (DD/MM/YYYY)",
    "{{NATIONAL_ID}}": "National ID number",
    "{{ADDRESS}}": "Residential address",
    "{{PHONE}}": "Phone number",
    "{{EMAIL}}": "Email address",
    "{{NEXT_OF_KIN}}": "Next of kin name",
    "{{NEXT_OF_KIN_PHONE}}": "Next of kin phone",
    "{{NEXT_OF_KIN_RELATIONSHIP}}": "Relationship to next of kin",
    "{{POSITION}}": "Job position/title",
    "{{DEPARTMENT}}": "Department",
    "{{EMPLOYEE_ID}}": "Employee ID",
    "{{HIRE_DATE}}": "Original hire date",
    "{{CONTRACT_START_DATE}}": "Contract start date",
    "{{CONTRACT_END_DATE}}": "Contract end date",
    "{{CONTRACT_DURATION}}": "Contract duration (e.g., 3 Months)",
    "{{TODAY_DATE}}": "Today's date",
    "{{SALARY}}": "Monthly salary"
}


# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

def get_employees_for_contract():
    """Get all active employees for contract generation"""
    conn = get_connection()
    
    query = """
        SELECT id, employee_id, full_name, position, department, 
               date_of_birth, national_id, address, phone, email,
               emergency_contact, emergency_phone, next_of_kin_relationship,
               hire_date, salary
        FROM employees 
        WHERE status = 'Active'
        ORDER BY full_name
    """
    
    df = pd.read_sql_query(query, get_engine())
    conn.close()
    return df


def get_employee_by_id(employee_id):
    """Get single employee details"""
    conn = get_connection()
    ph = '%s' if USE_POSTGRES else '?'
    
    query = f"""
        SELECT id, employee_id, full_name, position, department, 
               date_of_birth, national_id, address, phone, email,
               emergency_contact, emergency_phone, next_of_kin_relationship,
               hire_date, salary
        FROM employees 
        WHERE employee_id = {ph}
    """
    
    df = pd.read_sql_query(query, get_engine(), params=(employee_id,))
    conn.close()
    
    if not df.empty:
        return df.iloc[0].to_dict()
    return None


def get_contract_template(template_name="Employment Contract"):
    """Get contract template from database"""
    conn = get_connection()
    ph = '%s' if USE_POSTGRES else '?'
    
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT template_content FROM contract_templates 
        WHERE template_name = {ph} AND is_active = {'TRUE' if USE_POSTGRES else '1'}
    """, (template_name,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0] if isinstance(result, tuple) else result.get('template_content')
    return None


def save_contract_template(template_name, template_content, description=None, created_by=None):
    """Save or update contract template"""
    conn = get_connection()
    cursor = conn.cursor()
    ph = '%s' if USE_POSTGRES else '?'
    
    try:
        # Check if template exists
        cursor.execute(f"SELECT id FROM contract_templates WHERE template_name = {ph}", (template_name,))
        exists = cursor.fetchone()
        
        if exists:
            # Update
            cursor.execute(f"""
                UPDATE contract_templates 
                SET template_content = {ph}, description = {ph}, updated_at = CURRENT_TIMESTAMP
                WHERE template_name = {ph}
            """, (template_content, description, template_name))
        else:
            # Insert
            cursor.execute(f"""
                INSERT INTO contract_templates (template_name, template_content, description, created_by)
                VALUES ({ph}, {ph}, {ph}, {ph})
            """, (template_name, template_content, description, created_by))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving template: {e}")
        return False
    finally:
        conn.close()


def get_all_templates():
    """Get all contract templates"""
    conn = get_connection()
    
    query = """
        SELECT id, template_name, description, is_active, created_at, updated_at
        FROM contract_templates
        ORDER BY template_name
    """
    
    df = pd.read_sql_query(query, get_engine())
    conn.close()
    return df


def init_default_template():
    """Initialize default template if none exists"""
    existing = get_contract_template("Employment Contract")
    if not existing:
        save_contract_template(
            "Employment Contract",
            DEFAULT_CONTRACT_TEMPLATE,
            "Standard employment contract template",
            "system"
        )


# =============================================================================
# CONTRACT GENERATION
# =============================================================================

def replace_placeholders(template, employee, contract_start, contract_end, duration_text):
    """Replace all placeholders in template with actual values"""
    
    # Format dates
    def format_date(date_val):
        if not date_val:
            return ".................."
        try:
            if isinstance(date_val, str):
                date_obj = datetime.strptime(date_val, "%Y-%m-%d")
            else:
                date_obj = date_val
            return date_obj.strftime("%d/%m/%Y")
        except:
            return str(date_val)
    
    # Build replacements dict
    replacements = {
        "{{EMPLOYEE_NAME}}": str(employee.get('full_name', '')).upper() or "..................",
        "{{DATE_OF_BIRTH}}": format_date(employee.get('date_of_birth')),
        "{{NATIONAL_ID}}": str(employee.get('national_id', '')) or "..................",
        "{{ADDRESS}}": str(employee.get('address', '')) or "..................",
        "{{PHONE}}": str(employee.get('phone', '')) or "..................",
        "{{EMAIL}}": str(employee.get('email', '')) or "..................",
        "{{NEXT_OF_KIN}}": str(employee.get('emergency_contact', '')) or "..................",
        "{{NEXT_OF_KIN_PHONE}}": str(employee.get('emergency_phone', '')) or "..................",
        "{{NEXT_OF_KIN_RELATIONSHIP}}": str(employee.get('next_of_kin_relationship', '')) or "..................",
        "{{POSITION}}": str(employee.get('position', '')) or "..................",
        "{{DEPARTMENT}}": str(employee.get('department', '')) or "..................",
        "{{EMPLOYEE_ID}}": str(employee.get('employee_id', '')) or "..................",
        "{{HIRE_DATE}}": format_date(employee.get('hire_date')),
        "{{CONTRACT_START_DATE}}": format_date(contract_start),
        "{{CONTRACT_END_DATE}}": format_date(contract_end),
        "{{CONTRACT_DURATION}}": duration_text,
        "{{TODAY_DATE}}": datetime.now().strftime("%d/%m/%Y"),
        "{{SALARY}}": f"${float(employee.get('salary', 0)):,.2f}" if employee.get('salary') else ".................."
    }
    
    # Replace all placeholders
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    
    return result


def generate_contract_docx(content, employee_name):
    """Generate DOCX file from filled contract content"""
    
    # Split content into paragraphs
    paragraphs = content.split('\n')
    
    # Build paragraph JS array
    para_js_parts = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            # Empty paragraph for spacing
            para_js_parts.append('new Paragraph({ children: [] })')
        elif para.startswith('=====') and para.endswith('====='):
            # Section header
            header_text = para.replace('=====', '').strip()
            escaped_header = header_text.replace('\\', '\\\\').replace('"', '\\"')
            para_js_parts.append(f'''new Paragraph({{
                heading: HeadingLevel.HEADING_1,
                spacing: {{ before: 300, after: 150 }},
                children: [new TextRun({{ text: "{escaped_header}", bold: true }})]
            }})''')
        elif para.startswith('•'):
            # Bullet point
            bullet_text = para[1:].strip().replace('\\', '\\\\').replace('"', '\\"')
            para_js_parts.append(f'''new Paragraph({{
                children: [new TextRun({{ text: "• {bullet_text}", size: 22 }})]
            }})''')
        elif para in ['FORESTVIEW ENTERPRISES', 'CONTRACT OF EMPLOYMENT', 'AND', 'STAMP']:
            # Centered bold text
            para_js_parts.append(f'''new Paragraph({{
                alignment: AlignmentType.CENTER,
                spacing: {{ after: 200 }},
                children: [new TextRun({{ text: "{para}", bold: true, size: {32 if para == 'FORESTVIEW ENTERPRISES' else 28 if para == 'CONTRACT OF EMPLOYMENT' else 24} }})]
            }})''')
        else:
            # Normal paragraph
            escaped = para.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
            para_js_parts.append(f'''new Paragraph({{
                alignment: AlignmentType.JUSTIFIED,
                children: [new TextRun({{ text: "{escaped}", size: 22 }})]
            }})''')
    
    paragraphs_js = ',\n            '.join(para_js_parts)
    
    js_code = f'''
const {{ Document, Packer, Paragraph, TextRun, AlignmentType, HeadingLevel }} = require('docx');
const fs = require('fs');

const doc = new Document({{
    styles: {{
        default: {{
            document: {{
                run: {{ font: "Arial", size: 22 }}
            }}
        }},
        paragraphStyles: [
            {{
                id: "Heading1",
                name: "Heading 1",
                basedOn: "Normal",
                run: {{ size: 24, bold: true, font: "Arial" }},
                paragraph: {{ spacing: {{ before: 240, after: 120 }} }}
            }}
        ]
    }},
    sections: [{{
        properties: {{
            page: {{
                margin: {{ top: 1080, right: 1080, bottom: 1080, left: 1080 }}
            }}
        }},
        children: [
            {paragraphs_js}
        ]
    }}]
}});

Packer.toBuffer(doc).then(buffer => {{
    fs.writeFileSync(process.argv[2], buffer);
    console.log("Contract generated successfully");
}});
'''
    
    return js_code


# =============================================================================
# PAGE FUNCTIONS
# =============================================================================

def contract_generator_page():
    """Employment Contract Generator Page"""
    
    st.header("📝 Employment Contract Generator")
    st.markdown("Generate printable employment contracts with employee details auto-filled")
    
    # Initialize default template if needed
    init_default_template()
    
    # Tabs for Generate and Edit Template
    tab1, tab2 = st.tabs(["📄 Generate Contract", "✏️ Edit Template"])
    
    with tab1:
        generate_contract_tab()
    
    with tab2:
        edit_template_tab()


def generate_contract_tab():
    """Tab for generating contracts"""
    
    st.markdown("---")
    
    # Get employees
    employees_df = get_employees_for_contract()
    
    if employees_df.empty:
        st.warning("No active employees found. Please add employees first.")
        return
    
    # Employee selection
    st.subheader("1️⃣ Select Employee")
    
    employee_options = {
        f"{row['full_name']} ({row['employee_id']}) - {row['position']}": row['employee_id']
        for _, row in employees_df.iterrows()
    }
    
    selected_employee_display = st.selectbox(
        "Choose Employee",
        list(employee_options.keys())
    )
    
    selected_employee_id = employee_options[selected_employee_display]
    employee = get_employee_by_id(selected_employee_id)
    
    if employee:
        # Show employee preview
        with st.expander("👤 Employee Details Preview", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Full Name:** {employee.get('full_name', 'N/A')}")
                st.write(f"**National ID:** {employee.get('national_id') or '⚠️ Not recorded'}")
                st.write(f"**Date of Birth:** {employee.get('date_of_birth') or '⚠️ Not recorded'}")
                st.write(f"**Position:** {employee.get('position', 'N/A')}")
                st.write(f"**Address:** {employee.get('address') or '⚠️ Not recorded'}")
            
            with col2:
                st.write(f"**Phone:** {employee.get('phone') or '⚠️ Not recorded'}")
                st.write(f"**Email:** {employee.get('email') or '⚠️ Not recorded'}")
                st.write(f"**Next of Kin:** {employee.get('emergency_contact') or '⚠️ Not recorded'}")
                st.write(f"**Next of Kin Phone:** {employee.get('emergency_phone') or '⚠️ Not recorded'}")
                st.write(f"**Relationship:** {employee.get('next_of_kin_relationship') or '⚠️ Not recorded'}")
        
        # Check for missing fields
        missing_fields = []
        if not employee.get('national_id'):
            missing_fields.append("National ID")
        if not employee.get('date_of_birth'):
            missing_fields.append("Date of Birth")
        if not employee.get('address'):
            missing_fields.append("Address")
        if not employee.get('emergency_contact'):
            missing_fields.append("Next of Kin")
        
        if missing_fields:
            st.warning(f"⚠️ Missing fields: {', '.join(missing_fields)}. Update in HR → Employee Management.")
    
    st.markdown("---")
    
    # Contract dates
    st.subheader("2️⃣ Contract Period")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        contract_start = st.date_input(
            "Contract Start Date",
            value=datetime.now().date()
        )
    
    with col2:
        duration = st.selectbox(
            "Contract Duration",
            ["3 Months", "6 Months", "12 Months", "Custom"],
            index=0
        )
    
    with col3:
        if duration == "3 Months":
            contract_end = contract_start + relativedelta(months=3)
            duration_text = "3 Months"
        elif duration == "6 Months":
            contract_end = contract_start + relativedelta(months=6)
            duration_text = "6 Months"
        elif duration == "12 Months":
            contract_end = contract_start + relativedelta(months=12)
            duration_text = "12 Months"
        else:
            contract_end = st.date_input(
                "Contract End Date",
                value=contract_start + relativedelta(months=3)
            )
            delta = relativedelta(contract_end, contract_start)
            duration_text = f"{delta.months + delta.years * 12} Months"
        
        if duration != "Custom":
            st.date_input(
                "Contract End Date",
                value=contract_end,
                disabled=True
            )
    
    st.info(f"📅 Contract Period: **{contract_start.strftime('%d %B %Y')}** to **{contract_end.strftime('%d %B %Y')}** ({duration_text})")
    
    st.markdown("---")
    
    # Generate button
    st.subheader("3️⃣ Generate Contract")
    
    # Get template
    template = get_contract_template("Employment Contract")
    if not template:
        template = DEFAULT_CONTRACT_TEMPLATE
    
    # Preview option
    if st.checkbox("👁️ Preview contract before generating"):
        filled_content = replace_placeholders(template, employee, contract_start, contract_end, duration_text)
        st.text_area("Contract Preview", filled_content, height=400, disabled=True)
    
    if st.button("📄 Generate Employment Contract", type="primary", use_container_width=True):
        with st.spinner("Generating contract..."):
            try:
                # Fill template
                filled_content = replace_placeholders(template, employee, contract_start, contract_end, duration_text)
                
                # Generate JS code
                js_code = generate_contract_docx(filled_content, employee.get('full_name', 'Employee'))
                
                # Create temp files
                with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as js_file:
                    js_file.write(js_code)
                    js_path = js_file.name
                
                output_path = f"/tmp/contract_{employee.get('employee_id', 'unknown')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
                
                # Run node to generate docx
                result = subprocess.run(
                    ['node', js_path, output_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Clean up JS file
                os.unlink(js_path)
                
                if result.returncode == 0 and os.path.exists(output_path):
                    # Read the generated file
                    with open(output_path, 'rb') as f:
                        docx_data = f.read()
                    
                    # Clean up output file
                    os.unlink(output_path)
                    
                    # Log action
                    AuditLogger.log_action(
                        "Generate",
                        "Contracts",
                        f"Generated contract for {employee.get('full_name')} ({contract_start} to {contract_end})"
                    )
                    
                    st.success("✅ Contract generated successfully!")
                    
                    # Download button
                    filename = f"Contract_{employee.get('full_name', 'Employee').replace(' ', '_')}_{contract_start.strftime('%Y%m%d')}.docx"
                    
                    st.download_button(
                        label="📥 Download Contract (DOCX)",
                        data=docx_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
                    
                    st.info("💡 **Tip:** Open in Microsoft Word, print, and have the employee sign.")
                    
                else:
                    st.error(f"Error generating contract: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                st.error("Contract generation timed out. Please try again.")
            except Exception as e:
                st.error(f"Error: {str(e)}")


def edit_template_tab():
    """Tab for editing contract templates"""
    
    st.markdown("---")
    st.subheader("✏️ Edit Contract Template")
    
    st.info("""
    **How to use placeholders:**
    Use `{{PLACEHOLDER_NAME}}` in your template. These will be replaced with actual employee data when generating contracts.
    """)
    
    # Show available placeholders
    with st.expander("📋 Available Placeholders", expanded=False):
        col1, col2 = st.columns(2)
        placeholders_list = list(AVAILABLE_PLACEHOLDERS.items())
        mid = len(placeholders_list) // 2
        
        with col1:
            for placeholder, description in placeholders_list[:mid]:
                st.code(placeholder)
                st.caption(description)
        
        with col2:
            for placeholder, description in placeholders_list[mid:]:
                st.code(placeholder)
                st.caption(description)
    
    # Get current template
    current_template = get_contract_template("Employment Contract")
    if not current_template:
        current_template = DEFAULT_CONTRACT_TEMPLATE
    
    # Template editor
    st.markdown("### Contract Template")
    st.caption("Use ===== SECTION NAME ===== for section headers (will be formatted as headings)")
    
    edited_template = st.text_area(
        "Edit your contract template below:",
        value=current_template,
        height=500,
        help="Use placeholders like {{EMPLOYEE_NAME}} that will be replaced with actual data"
    )
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button("💾 Save Template", type="primary", use_container_width=True):
            if save_contract_template(
                "Employment Contract",
                edited_template,
                "Standard employment contract template",
                st.session_state.get('user', {}).get('username', 'system')
            ):
                AuditLogger.log_action(
                    "Update",
                    "Contract Templates",
                    "Updated Employment Contract template"
                )
                st.success("✅ Template saved successfully!")
            else:
                st.error("Error saving template")
    
    with col2:
        if st.button("🔄 Reset to Default", use_container_width=True):
            if save_contract_template(
                "Employment Contract",
                DEFAULT_CONTRACT_TEMPLATE,
                "Standard employment contract template",
                st.session_state.get('user', {}).get('username', 'system')
            ):
                st.success("✅ Template reset to default!")
                st.rerun()
    
    with col3:
        # Download template as text file for backup
        st.download_button(
            label="📥 Backup Template",
            data=edited_template,
            file_name="contract_template_backup.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # Test with sample data
    st.subheader("🧪 Test Template")
    
    if st.checkbox("Preview with sample data"):
        sample_employee = {
            'full_name': 'John Doe',
            'date_of_birth': '1990-05-15',
            'national_id': '63-123456-A-42',
            'address': '123 Sample Street, Harare',
            'phone': '+263 77 123 4567',
            'email': 'john.doe@example.com',
            'emergency_contact': 'Jane Doe',
            'emergency_phone': '+263 77 765 4321',
            'next_of_kin_relationship': 'Spouse',
            'position': 'Bus Driver',
            'department': 'Operations',
            'employee_id': 'DRV001',
            'hire_date': '2024-01-15',
            'salary': 500.00
        }
        
        sample_start = datetime.now().date()
        sample_end = sample_start + relativedelta(months=3)
        
        preview = replace_placeholders(edited_template, sample_employee, sample_start, sample_end, "3 Months")
        
        st.text_area("Sample Preview", preview, height=400, disabled=True)
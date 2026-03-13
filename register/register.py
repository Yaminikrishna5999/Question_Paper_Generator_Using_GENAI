import streamlit as st
from modules.auth.style_utils import C
from config import Config
from modules.database import add_user
import time

def show_register_page():
    st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)

    # Full Name
    st.markdown(f'<div style="font-size:10px; font-weight:700; color:{C.t3}; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px;">Full Name *</div>', unsafe_allow_html=True)
    full_name = st.text_input("Full Name", label_visibility="collapsed", placeholder="Dr. John Doe", key="reg_name")

    # Email
    st.markdown(f'<div style="font-size:10px; font-weight:700; color:{C.t3}; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px; margin-top:16px;">Institutional Email *</div>', unsafe_allow_html=True)
    email = st.text_input("Email", label_visibility="collapsed", placeholder="yourname@university.edu", key="reg_email")

    # Dept + Role
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div style="font-size:10px; font-weight:700; color:{C.t3}; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px; margin-top:16px;">Department *</div>', unsafe_allow_html=True)
        department = st.text_input("Department", label_visibility="collapsed", key="reg_dept", placeholder="Enter Department")
    with c2:
        st.markdown(f'<div style="font-size:10px; font-weight:700; color:{C.t3}; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px; margin-top:16px;">Designation *</div>', unsafe_allow_html=True)
        designation = st.text_input("Designation", label_visibility="collapsed", key="reg_role", placeholder="Enter Designation")

    # Password
    st.markdown(f'<div style="font-size:10px; font-weight:700; color:{C.t3}; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px; margin-top:16px;">Create Password *</div>', unsafe_allow_html=True)
    password = st.text_input("Password", label_visibility="collapsed", type="password", placeholder="At least 6 characters", key="reg_pass")

    # Repeat Password
    st.markdown(f'<div style="font-size:10px; font-weight:700; color:{C.t3}; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px; margin-top:16px;">Verify Password *</div>', unsafe_allow_html=True)
    confirm_password = st.text_input("Confirm Password", label_visibility="collapsed", type="password", placeholder="Repeat your password", key="reg_pass2")

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    
    if st.button("Complete Registration", use_container_width=True, type="primary"):
        if full_name and email and password and confirm_password and department and designation:
            if password != confirm_password:
                st.error("Passwords do not match")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                with st.spinner("Creating account..."):
                    success, message = add_user(full_name, email, department, designation, password)
                    if success:
                        st.success("Account successfully created")
                        time.sleep(1.0)
                        st.session_state.auth_screen = "login"
                        st.rerun()
                    else:
                        st.error(message)
        else:
            if not department or not designation:
                st.warning("Please select both department and designation")
            else:
                st.warning("Please fill in all fields")

    # Footer
    st.markdown(f"""
    <div style="text-align:center; margin-top:18px; font-size:12px; color:{C.t4};">
        Already registered?
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Return to Login", use_container_width=True, type="primary", key="back_login"):
        st.session_state.auth_screen = "login"
        st.rerun()

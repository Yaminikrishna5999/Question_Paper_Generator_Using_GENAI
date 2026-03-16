import streamlit as st
from modules.auth.style_utils import C
from modules.database import verify_user, add_audit_log
import time

def show_faculty_login():
    uname = st.text_input("Username (Email)", placeholder="Enter your email", key="fac_uname")
    passw = st.text_input("Password", type="password", placeholder="Enter your password", key="fac_pass")
    
    st.markdown('<div style="height:26px;"></div>', unsafe_allow_html=True)
    
    if st.button("🚀 Sign In as Faculty", use_container_width=True, type="primary"):
        with st.spinner("Authenticating..."):
            time.sleep(0.9)
            success, result = verify_user(uname, passw, role="faculty")
            if success:
                from modules.database import update_last_login
                update_last_login(uname)
                st.session_state.logged_in = True
                st.session_state.user_role = "faculty"
                st.session_state.user_data = result
                st.session_state.user_data = result
                st.session_state.faculty_name = result["name"]
                st.session_state.v5_page = "dashboard"
                add_audit_log(uname, "Login", "Faculty signed in successfully")
                st.rerun()
            else:
                add_audit_log(uname, "Login Failed", f"Failed attempt: {result}")
                st.error(f"⚠️ {result}")

    # Registration links removed as per admin-only policy
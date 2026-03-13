import streamlit as st
from modules.auth.style_utils import C
from modules.database import verify_user, add_audit_log
import time

def show_faculty_login():
    st.markdown(f"""
    <div style="display:block; font-size:10px; font-weight:700; color:{C.t3}; 
         text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px; margin-top:10px;">Username (Email)</div>
    """, unsafe_allow_html=True)
    uname = st.text_input("Username", label_visibility="collapsed", placeholder="Enter your email", key="fac_uname")
    
    st.markdown(f"""
    <div style="display:block; font-size:10px; font-weight:700; color:{C.t3}; 
         text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px; margin-top:16px;">Password</div>
    """, unsafe_allow_html=True)
    passw = st.text_input("Password", label_visibility="collapsed", type="password", placeholder="Enter your password", key="fac_pass")
    
    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
    
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
                st.session_state.faculty_name = result["name"]
                add_audit_log(uname, "Login", "Faculty signed in successfully")
                st.rerun()
            else:
                add_audit_log(uname, "Login Failed", f"Failed attempt: {result}")
                st.error(f"⚠️ {result}")

    # Registration links removed as per admin-only policy

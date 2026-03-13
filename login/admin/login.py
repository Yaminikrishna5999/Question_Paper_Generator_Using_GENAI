import streamlit as st
from modules.auth.style_utils import C
from modules.database import verify_user, add_audit_log
import time

def show_admin_login():
    # Admin access notice
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:9px; background:#E8EDFF; 
         border:1px solid #B3C0F8; border-radius:10px; padding:10px 14px; margin-bottom:18px; margin-top:10px;">
      <span style="font-size:18px;">🛡️</span>
      <div>
        <div style="font-size:12px; font-weight:700; color:{C.indigo}">Administrator Access</div>
        <div style="font-size:10px; color:{C.t3}">Full system privileges — actions are logged</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="display:block; font-size:10px; font-weight:700; color:{C.t3}; 
         text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;">Email (Standard)</div>
    """, unsafe_allow_html=True)
    uname = st.text_input("Username", label_visibility="collapsed", placeholder="admin@gmail.com", key="admin_uname")
    
    st.markdown(f"""
    <div style="display:block; font-size:10px; font-weight:700; color:{C.t3}; 
         text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px; margin-top:16px;">Password</div>
    """, unsafe_allow_html=True)
    passw = st.text_input("Password", label_visibility="collapsed", type="password", placeholder="Enter admin password", key="admin_pass")
    
    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
    
    if st.button("🛡️ Sign In as Admin", use_container_width=True, type="primary"):
        with st.spinner("Verifying Credentials..."):
            time.sleep(0.9)
            success, result = verify_user(uname, passw, role="admin")
            if success:
                st.session_state.logged_in = True
                st.session_state.user_role = "admin"
                st.session_state.user_data = result
                st.session_state.faculty_name = result["name"]
                add_audit_log(uname, "Admin Login", "Administrator signed in successfully")
                st.rerun()
            else:
                add_audit_log(uname, "Admin Login Failed", f"Failed attempt: {result}")
                st.error(f"⚠️ {result}")

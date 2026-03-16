import streamlit as st
from modules.auth.style_utils import C
from modules.database import verify_user, add_audit_log
import time

def show_admin_login():
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:12px; background:{C.admNoticeBg}; 
         border:1px solid {C.admNoticeBd}; border-radius:12px; padding:12px 14px; margin-bottom:20px; margin-top:5px;">
      <div style="background:{C.admBadgeBg}; width:32px; height:32px; border-radius:8px; display:flex; align-items:center; justify-content:center;">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{C.admNoticeTitle}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
      </div>
      <div>
        <div style="font-size:12px; font-weight:700; color:{C.admNoticeTitle}; margin-bottom:2px;">Administrator Access</div>
        <div style="font-size:10.5px; color:{C.admNoticeSub}">Full system privileges — actions are logged</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    uname = st.text_input("Email (Standard)", placeholder="admin@gmail.com", key="admin_uname")
    
    passw = st.text_input("Password", type="password", placeholder="Enter admin password", key="admin_pass")
    
    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    
    if st.button("🛡️ Sign In as Admin", use_container_width=True, type="primary"):
        with st.spinner("Verifying Credentials..."):
            time.sleep(0.9)
            success, result = verify_user(uname, passw, role="admin")
            if success:
                st.session_state.logged_in = True
                st.session_state.user_role = "admin"
                st.session_state.user_data = result
                st.session_state.faculty_name = result["name"]
                st.session_state.admin_page = "admin_dash"
                add_audit_log(uname, "Admin Login", "Administrator signed in successfully")
                st.rerun()
            else:
                add_audit_log(uname, "Admin Login Failed", f"Failed attempt: {result}")
                st.error(f"⚠️ {result}") 


import streamlit as st
import time
import re
import os
from datetime import datetime
import json
import base64

# ── Project imports ──
from config import Config
from modules.export_handler import ExportHandler
from modules.database import (
    get_all_users, get_all_papers_admin, get_admin_stats, 
    delete_paper, verify_user, get_audit_logs, get_announcements,
    add_announcement, get_system_settings, update_system_setting,
    get_db_raw_data, get_faculty_metrics, get_distinct_departments,
    update_user_status, update_user_details, add_user
)

# ═══════════════════════════════════════════════════════════════
# PaperGen AI v5.0 — Gold Standard Design Tokens (Matching Faculty)
# ═══════════════════════════════════════════════════════════════
class C:
    pageBg    = "#F8F4FD"
    sidebar   = "#FFFFFF"
    sbBd      = "#F0EBF8"
    sbLine    = "#EDE8F5"
    card      = "#FFFFFF"
    cardBd    = "#EDE8F5"
    cardSh    = "0 2px 10px rgba(114,9,183,0.07),0 1px 3px rgba(114,9,183,0.04)"
    cardShHov = "0 8px 28px rgba(114,9,183,0.14),0 2px 8px rgba(114,9,183,0.07)"
    inputBg   = "#F4F0FB"
    inputBd   = "#E4DCF5"
    pink      = "#F72585"
    violet    = "#7209B7"
    sky       = "#4CC9F0"
    blue      = "#4361EE"
    orange    = "#F8961E"
    green     = "#2DC653"
    gPinkVio  = "linear-gradient(135deg,#F72585,#7209B7)"
    gPink     = "linear-gradient(135deg,#F72585,#B5179E)"
    gViolet   = "linear-gradient(135deg,#7209B7,#560BAD)"
    gSkyBlue  = "linear-gradient(135deg,#4CC9F0,#4361EE)"
    gOrange   = "linear-gradient(135deg,#F8961E,#F3722C)"
    t1        = "#2D1B69"
    t2        = "#4A3880"
    t3        = "#6E6893"
    t4        = "#A89EC4"

# ═══════════════════════════════════════════════════════════════
# UTILS
# ═══════════════════════════════════════════════════════════════
def _normalize_paper(p):
    """Bridge dashboard paper schema -> ExportHandler schema."""
    cfg = p.get("cfg", {}) # Use paper-specific cfg if available
    
    questions = []
    for q in p.get("questions", []):
        questions.append({
            "no":         q.get("no", 0),
            "number":     q.get("no", 0),
            "type":       q.get("type", "Short Answer"),
            "difficulty": q.get("difficulty", "Medium"),
            "marks":      q.get("marks", 3),
            "q":          q.get("q", ""),
            "options":    q.get("options", []),
            "content":    q.get("content", q.get("q", "")),
            "bloom":      q.get("bloom", ""),
            "section":    q.get("section", "Section A")
        })

    return {
        "name":            p.get("name", "Paper"),
        "title":           p.get("title", cfg.get("exam_name", "Examination")),
        "exam_name":       cfg.get("exam_name", p.get("title", "Examination")),
        "inst_name":       p.get("inst_name", cfg.get("inst_name", "")),
        "institution":     p.get("inst_name", cfg.get("inst_name", "")),
        "course_name":     cfg.get("course_name", p.get("course_name", "")),
        "course_code":     cfg.get("course_code", p.get("course_code", "")),
        "department":      cfg.get("dept", p.get("department", cfg.get("department", ""))),
        "dept":            cfg.get("dept", p.get("department", cfg.get("department", ""))),
        "semester":        p.get("semester", cfg.get("semester", "")),
        "exam_date":       p.get("date", cfg.get("exam_date", "")),
        "duration":        cfg.get("duration", p.get("duration", "3 Hours")),
        "subject":         ", ".join(cfg.get("topics", [])),
        "set":             p.get("set", "A"),
        "total_questions": len(questions),
        "total_marks":     sum(q["marks"] for q in questions),
        "questions":       questions,
        "config":          cfg
    }

ADMIN_NAV = [
    ("MAIN",            [("🏠", "Dashboard", "admin_dash")]),
    ("USER MANAGEMENT", [("👨‍🏫", "Faculty Management", "fac_mgt"),
                         ("📜", "Activity Logs", "logs")]),
    ("ACADEMIC CONTROL",[("📄", "All Papers", "all_papers"),
                         ("🗂️", "Global Question Bank", "global_qbank"),
                         ("📐", "Templates Management", "adm_templates")]),
    ("ANALYTICS",       [("📊", "System Analytics", "sys_analytics"),
                         ("📈", "Usage Statistics", "usage_stats")]),
    ("COMMUNICATION",   [("📢", "Announcements Manager", "ann_mgt"),
                         ("🔔", "Admin Alerts", "admin_alerts")]),
    ("SYSTEM",          [("🔑", "API Usage Monitor", "api_monitor"),
                         ("⚙️", "System Settings", "sys_settings"),
                         ("🛡️", "Security Center", "security"),
                         ("💾", "Database Inspector", "db_inspector")]),
    ("OTHER",           [("📥", "Download Center", "adm_downloads"),
                         ("ℹ️", "About", "adm_about")]),
]

def _css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

    /* ── Global ── */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], .pg-card, .cfg-section-wrapper {{
        font-family: 'Poppins', sans-serif;
    }}
    * {{ box-sizing: border-box; }}

    /* ── Sidebar shell ── */
    section[data-testid="stSidebar"]{{
        background:{C.sidebar} !important;
        border-right:1px solid {C.sbBd} !important;
        width:252px !important;
        min-width:252px !important;
        overflow-x:hidden !important;
    }}
    section[data-testid="stSidebar"] > div,
    section[data-testid="stSidebar"] > div > div,
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{{
        gap:0 !important;
        padding:0 !important;
        margin:0 !important;
    }}

    /* ── Hide Streamlit chrome ── */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="sidebar-close-button"],
    button[kind="header"],
    [data-testid="stHeader"],[data-testid="stToolbar"],
    [data-testid="stDecoration"],footer{{display:none !important;}}

    /* ── Base nav button ── */
    div.stButton > button{{
        width:100% !important;
        border-radius:8px !important;
        border:1px solid transparent !important;
        background:transparent !important;
        color:{C.t2} !important;
        text-align:left !important;
        justify-content:flex-start !important;
        padding:7px 10px !important;
        font-size:12.5px !important;
        font-weight:500 !important;
        line-height:1.2 !important;
        height:36px !important;
        margin:0 0 1px 0 !important;
        transition:background 0.15s,color 0.15s,transform 0.15s !important;
        display:flex !important;
        align-items:center !important;
        gap:8px !important;
    }}
    div.stButton > button:hover{{
        background:#F0EBF8 !important;
        color:{C.violet} !important;
        border-color:{C.sbBd} !important;
        transform:translateX(3px) !important;
    }}

    /* ── ACTIVE: light violet matched to screenshot ── */
    div.nav-on > div.stButton > button,
    div.nav-on > div.stButton > button:hover,
    div.nav-on > div.stButton > button:focus{{
        background:#F0EBF8 !important;
        color:{C.violet} !important;
        font-weight:700 !important;
        border:none !important;
        transform:none !important;
    }}

    /* ── Sidebar section label ── */
    .sb-lbl{{
        color:{C.t4};
        font-size:8px;
        font-weight:800;
        letter-spacing:2px;
        text-transform:uppercase;
        padding:14px 12px 4px 12px;
        display:block;
    }}

    /* ── Main content ── */
    .main .block-container{{
        background:{C.pageBg};
        padding-top:0.5rem !important;
        padding-bottom:2rem !important;
        max-width:100% !important;
    }}

    /* ── Page fade-up ── */
    @keyframes fadeUp{{from{{opacity:0;transform:translateY(9px)}}to{{opacity:1;transform:translateY(0)}}}}
    .page-content{{animation:fadeUp 0.22s ease;}}

    /* ── Cards ── */
    .pg-card{{
        background:#fff;
        border:1px solid {C.cardBd};
        border-radius:13px;
        padding:16px;
        box-shadow:{C.cardSh};
        margin-bottom:14px;
        transition:transform 0.18s,box-shadow 0.18s;
    }}
    .pg-card:hover{{transform:translateY(-2px);box-shadow:{C.cardShHov};}}

    /* ── Hero banner ── */
    .pg-hero{{
        background:linear-gradient(135deg,#F72585,#7209B7);
        border-radius:16px;
        padding:24px 26px;
        color:white;
        margin-bottom:16px;
        box-shadow:0 5px 20px rgba(247,37,133,0.22);
    }}

    /* ── KPI tiles ── */
    .pg-kpi{{
        border-radius:14px;
        padding:17px 15px;
        color:white;
        height:122px;
        display:flex;
        flex-direction:column;
        justify-content:space-between;
    }}
    </style>
    """, unsafe_allow_html=True)

def show_v5_admin_dashboard():
    if "admin_page" not in st.session_state:
        st.session_state.admin_page = "admin_dash"
    
    _css()
    
    # User Data
    u = st.session_state.get("user_data", {})
    user = {
        "name":   u.get("name",  "System Admin"),
        "dept":   u.get("dept",  "Management"),
        "desig":  u.get("desig", "Administrator"),
        "avatar": "".join([w[0] for w in u.get("name","A").split() if w][:2]).upper(),
    }

    with st.sidebar:
        # ── Brand header ──
        st.markdown(f"""
        <div style="padding:14px 12px 12px;display:flex;align-items:center;gap:10px;
                    border-bottom:1px solid {C.sbBd};">
          <div style="width:33px;height:33px;border-radius:9px;flex-shrink:0;
                      background:linear-gradient(135deg,#F72585,#7209B7);
                      display:flex;align-items:center;justify-content:center;
                      font-size:15px;box-shadow:0 3px 8px rgba(247,37,133,0.3);">📋</div>
          <div>
            <div style="color:{C.t1};font-weight:800;font-size:13px;line-height:1.2;">PaperGen AI</div>
            <div style="color:{C.t4};font-size:7.5px;font-weight:700;
                        text-transform:uppercase;letter-spacing:1px;">Exam Studio v5.0</div>
          </div>
        </div>""", unsafe_allow_html=True)

        # ── Profile row ──
        st.markdown(f"""
        <div style="margin:8px 10px 4px;background:{C.pageBg};border-radius:10px;
                    padding:8px 10px;border:1px solid {C.sbBd};
                    display:flex;align-items:center;gap:8px;">
          <div style="width:30px;height:30px;border-radius:8px;flex-shrink:0;
                      background:linear-gradient(135deg,#F72585,#7209B7);
                      color:white;display:flex;align-items:center;justify-content:center;
                      font-weight:700;font-size:11px;">{user['avatar']}</div>
          <div style="flex:1;min-width:0;">
            <div style="font-size:11px;font-weight:700;color:{C.t1};
                        overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{user['name']}</div>
            <div style="font-size:8.5px;color:{C.t4};font-weight:600;
                        overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{user['desig']} · {user['dept']}</div>
          </div>
          <div style="width:7px;height:7px;background:{C.green};border-radius:50%;
                      box-shadow:0 0 0 2px #E8F7EE;flex-shrink:0;"></div>
        </div>""", unsafe_allow_html=True)

        # Fetch unread count for sidebar badge
        from modules.database import get_notifications
        unread_notifs = [n for n in get_notifications("admin@gmail.com") if not n["is_read"]]
        unread_count = len(unread_notifs)

        for section, items in ADMIN_NAV:
            st.markdown(f'<span class="sb-lbl">{section}</span>', unsafe_allow_html=True)
            for icon, label, page_id in items:
                active = (st.session_state.admin_page == page_id)
                
                # Dynamic label with unread count
                display_label = label
                if page_id == "admin_alerts" and unread_count > 0:
                    display_label = f"{label} ({unread_count})"
                
                btn_lbl = f"{icon}  {display_label}"
                cls = "nav-on" if active else "nav-off"
                st.markdown(f'<div class="{cls}" style="padding:1px 9px 0;">', unsafe_allow_html=True)
                clicked = st.button(btn_lbl, key=f"adm_nav_{page_id}", use_container_width=True)
                if clicked and not active:
                    st.session_state.admin_page = page_id
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(f'<div style="border-top:1px solid {C.sbBd};margin:10px 0 0;"></div>', unsafe_allow_html=True)
        if st.button("🚪  Sign Out", key="admin_signout", use_container_width=True):
            from modules.database import add_audit_log
            add_audit_log("admin@gmail.com", "Admin Sign Out", "Administrator logged out")
            st.session_state.logged_in = False
            st.rerun()

    # Content Area
    pg = st.session_state.admin_page
    
    # Top Bar
    lbl = pg.replace("adm_","").replace("_"," ").title()
    st.markdown(f"""
    <div style="margin-top:4px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
      <div>
        <div style="font-size:18px;font-weight:800;color:{C.t1};line-height:1.2;">{lbl}</div>
        <div style="font-size:9.5px;color:{C.t4};">PaperGen AI › Administrator › {lbl}</div>
      </div>
      <div style="background:white;padding:4px 12px;border-radius:20px;border:1px solid {C.sbBd};font-size:9px;font-weight:600;color:{C.t3};">
        🕐 {datetime.now().strftime("%I:%M %p")} · System Status: <span style="color:{C.green}">Online</span>
      </div>
    </div>
    <hr style="border:none;border-top:1px solid {C.sbBd};margin:0 0 16px 0;">
    """, unsafe_allow_html=True)

    if pg == "admin_dash":         _admin_dash()
    elif pg == "admin_alerts":       _admin_alerts()
    elif pg == "fac_mgt":          _fac_mgt()
    elif pg == "logs":             _logs()
    elif pg == "all_papers":       _all_papers()
    elif pg == "global_qbank":     _global_qbank()
    elif pg == "sys_analytics":    _sys_analytics()
    elif pg == "ann_mgt":          _ann_mgt()
    elif pg == "adm_templates":     _adm_templates()
    elif pg == "usage_stats":      _usage_stats()
    elif pg == "adm_downloads":    _adm_downloads()
    elif pg == "adm_about":        _adm_about()
    elif pg == "security":         _security()
    elif pg == "db_inspector":     _db_inspector()
    else:                          st.info(f"Page '{lbl}' is under development.")

def _admin_dash():
    # Hero
    st.markdown(f"""
    <div class="pg-hero">
      <div style="font-size:9px;font-weight:700;letter-spacing:1.2px;color:rgba(255,255,255,0.65);text-transform:uppercase;margin-bottom:5px;">CONTROL CENTER</div>
      <h1 style="font-size:25px;font-weight:800;margin:0 0 8px;">Welcome, System Admin 👋</h1>
      <p style="font-size:12.5px;opacity:0.82;max-width:500px;line-height:1.6;margin:0;">
        Monitor platform health, faculty activity, and manage system-wide academic resources.
      </p>
    </div>""", unsafe_allow_html=True)

    stats = get_admin_stats()
    k1, k2, k3, k4 = st.columns(4)
    
    kpis = [
        ("👨‍🏫", "Total Faculty", stats['total_faculty'], C.gPink),
        ("📄", "Total Papers", stats['total_papers'], C.gViolet),
        ("📅", "Generated Today", stats['today_papers'], C.gSkyBlue),
        ("✨", "Active Now", "4", C.gOrange),
    ]
    
    for col, (icon, label, val, grad) in zip([k1,k2,k3,k4], kpis):
        with col:
            st.markdown(f"""
            <div class="pg-kpi" style="background:{grad};">
              <div style="font-size:19px;">{icon}</div>
              <div>
                <div style="font-size:23px;font-weight:800;">{val}</div>
                <div style="font-size:8.5px;opacity:0.78;font-weight:700;text-transform:uppercase;">{label}</div>
              </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.markdown(f'<div class="pg-card"><h3>Recent Faculty Activity</h3><p style="color:{C.t3};font-size:12px;">Monitoring real-time actions across the platform.</p>', unsafe_allow_html=True)
        logs = get_audit_logs(limit=5)
        if not logs:
            st.info("No recent activity logged.")
        else:
            for l in logs:
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f0f0f0;">
                  <div><strong>{l['user']}</strong><br><span style="font-size:11px;color:{C.t3}">{l['action']}: {l['details']}</span></div>
                  <div style="font-size:10px;color:{C.t4}">{l['time']}</div>
                </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown(f'<div class="pg-card" style="height:100%;"><h3>System Status</h3>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="padding:10px 0;">
          <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
            <span style="font-size:12px;">Gemini API</span>
            <span style="color:{C.green};font-size:12px;font-weight:700;">Healthy</span>
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
            <span style="font-size:12px;">Database</span>
            <span style="color:{C.green};font-size:12px;font-weight:700;">Online</span>
          </div>
          <div style="display:flex;justify-content:space-between;">
            <span style="font-size:12px;">Storage</span>
            <span style="color:{C.green};font-weight:700;">92% Free</span>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- CUSTOM CSS FOR INTERACTION POLISH ---
    st.markdown("""
        <style>
            /* AGGRESSIVE HAND CURSOR FIX */
            /* Target select boxes, buttons, inputs, and their internal elements */
            .stSelectbox, .stSelectbox *, 
            .stMultiSelect, .stMultiSelect *,
            div[data-baseweb="select"], div[data-baseweb="select"] *,
            div[role="combobox"], div[role="combobox"] *,
            button, .stButton > button,
            div[data-testid="stSelectbox"] *,
            div[data-testid="stSelectbox"] div[role="button"] {
                cursor: pointer !important;
            }
            
            /* High-contrast hover effect for the 'Add Faculty' primary button */
            button[kind="primary"]:hover {
                background-color: #ff4b4b !important;
                box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4) !important;
                transform: translateY(-1px);
                transition: all 0.2s ease;
            }
            
            /* Force hand cursor on search and forms */
            input, .stTextInput *, .stTextArea * {
                cursor: pointer !important;
            }
            /* Reset cursor for text entry specifically, but only on the actual text area */
            input[type="text"], textarea {
                cursor: text !important;
            }
        </style>
    """, unsafe_allow_html=True)

def _fac_mgt():
    # --- 1. Metrics Header ---
    stats = get_admin_stats()
    users = get_all_users()
    faculty_all = [u for u in users if u['role'] == 'faculty']
    
    # Calculate Real-Time Active (Online) count
    import datetime
    now = datetime.datetime.now()
    online_count = 0
    for u in faculty_all:
        if u['last_login']:
            try:
                ll = datetime.datetime.strptime(u['last_login'], "%Y-%m-%d %H:%M:%S")
                if (now - ll).total_seconds() < 300: online_count += 1
            except: pass

    k1, k2, k3 = st.columns(3)
    metric_cards = [
        ("👥", "Total Faculty", len(faculty_all), C.gPink),
        ("✅", "Active Accounts", online_count, C.gViolet),
        ("⚡", "Papers Today", stats['today_papers'], C.gOrange)
    ]
    
    for col, (ico, lbl, val, grad) in zip([k1, k2, k3], metric_cards):
        with col:
            st.markdown(f"""
            <div style="background:{grad}; padding:15px; border-radius:12px; color:white; box-shadow:0 4px 12px rgba(0,0,0,0.08);">
                <div style="font-size:18px; margin-bottom:4px;">{ico}</div>
                <div style="font-size:22px; font-weight:800; line-height:1;">{val}</div>
                <div style="font-size:9px; font-weight:700; text-transform:uppercase; opacity:0.8; margin-top:4px;">{lbl}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Add Faculty & Filters Row
    c1, c2 = st.columns([1, 2])
    
    with c1:
        if st.button("➕ Add New Faculty", type="primary", use_container_width=True):
            st.session_state.show_add_fac = not st.session_state.get("show_add_fac", False)
            
    with c2:
        sc1, sc2 = st.columns([2, 1])
        search = sc1.text_input("🔍 Search", placeholder="Name or Email...", label_visibility="collapsed")
        depts = ["All Departments"] + get_distinct_departments()
        f_dept = sc2.selectbox("Dept", depts, label_visibility="collapsed")

    # 3. Add Faculty Form
    if st.session_state.get("show_add_fac"):
        with st.form("add_faculty_form"):
            st.markdown(f'<div style="font-size:14px; font-weight:700; color:{C.t1}; margin-bottom:10px;">Register New Faculty Account</div>', unsafe_allow_html=True)
            ac1, ac2 = st.columns(2)
            f_name = ac1.text_input("Faculty Name")
            f_email = ac2.text_input("Email Address")
            
            ac3, ac4 = st.columns(2)
            f_depts = [
                "Computer Science and Engineering (CSE)",
                "Information Technology (IT)",
                "Electronics and Communication Engineering (ECE)",
                "Electrical and Electronics Engineering (EEE)",
                "Mechanical Engineering (ME)",
                "Civil Engineering (CE)",
                "Artificial Intelligence and Data Science (AI & DS)",
                "Artificial Intelligence and Machine Learning (AI & ML)",
                "Cyber Security",
                "Data Science"
            ]
            f_dept = ac3.selectbox("Department", f_depts)
            f_desig = ac4.selectbox("Role / Designation", ["Professor", "Associate Professor", "Assistant Professor", "HOD", "Visiting Faculty", "Lecturer"])
            
            f_subjects = st.text_input("Subjects Assigned (comma separated)", placeholder="e.g. Data Structures, Algorithms")
            f_pass = st.text_input("Initial Password", type="password", value="Faculty@123")
            
            f1, f2, f3 = st.columns([1.2, 1.2, 3])
            if f1.form_submit_button("Add Faculty", type="primary"):
                if f_name and f_email and f_pass:
                    from modules.database import add_user
                    success, msg = add_user(f_name, f_email, f_dept, f_desig, f_pass, subjects=f_subjects)
                    if success:
                        st.success(f"Faculty {f_name} added successfully!")
                        # Log it
                        from modules.database import add_audit_log
                        add_audit_log("admin@gmail.com", "Faculty Added", f"Added {f_name} ({f_email}) to {f_dept}")
                        st.session_state.show_add_fac = False
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Please fill Name, Email and Password.")
            
            if f2.form_submit_button("Close Form", type="secondary"):
                st.session_state.show_add_fac = False
                st.rerun()

    # 4. Faculty List
    # Removed empty pg-card wrapper as it causes an unprofessional white bar in Streamlit
    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
    users = get_all_users()
    # Filter only faculty
    faculty = [u for u in users if u['role'] == 'faculty']
    
    # Apply search & dept filter
    filtered = []
    for u in faculty:
        match_search = not search or (search.lower() in u['name'].lower() or search.lower() in u['email'].lower())
        match_dept = f_dept == "All Departments" or u['dept'] == f_dept
        if match_search and match_dept:
            filtered.append(u)

    if not filtered:
        st.info("No faculty matching the criteria.")
    else:
        # Table Header
        th = st.columns([2.5, 1.5, 1.5, 3.5])
        headers = ["Faculty Profile", "Department", "Status", "Actions"]
        for col, head in zip(th, headers):
            col.markdown(f'<div style="font-size:11px; font-weight:700; color:{C.t4}; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:10px;">{head}</div>', unsafe_allow_html=True)
        
        for u in filtered:
            initials = "".join([w[0] for w in u['name'].split()][:2]).upper()
            
            # --- Dynamic Status Logic ---
            display_status = u['status']
            status_color = "#6c757d" # Gray default
            status_bg = "#f8f9fa"
            
            if u['last_login']:
                try:
                    last_log = datetime.datetime.strptime(u['last_login'], "%Y-%m-%d %H:%M:%S")
                    if (now - last_log).total_seconds() < 300: # 5 minutes = Active
                        display_status = "Active"
                        status_color = C.green
                        status_bg = "#E8F7EE"
                    else:
                        # Professional Date/Time format
                        display_status = last_log.strftime("%d %b, %I:%M %p")
                except:
                    display_status = "Never Logged In"
            else:
                display_status = "Never Logged In"

            # --- Data Row using Streamlit Columns for Perfect Alignment ---
            r = st.columns([2.5, 1.5, 1.5, 3.5])
            
            # Col 1: Profile
            with r[0]:
                st.markdown(f"""
                <div style="display:flex; align-items:center; gap:10px;">
                    <div style="width:34px; height:34px; border-radius:8px; background:{C.gViolet}; color:white; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700;">{initials}</div>
                    <div>
                        <div style="font-size:12.5px; font-weight:700; color:{C.t1}; line-height:1.2;">{u['name']}</div>
                        <div style="font-size:10px; color:{C.t4}; line-height:1;">{u['email']}</div>
                    </div>
                </div>""", unsafe_allow_html=True)
            
            # Col 2: Dept
            with r[1]:
                st.markdown(f"""
                <div style="margin-top:2px;">
                    <div style="font-size:11px; color:{C.t2}; font-weight:600;">{u['dept'] or 'N/A'}</div>
                    <div style="font-size:9px; color:{C.t4};">{u['desig'] or 'Faculty'}</div>
                </div>""", unsafe_allow_html=True)
            
            # Col 3: Status
            with r[2]:
                st.markdown(f"""
                <div style="margin-top:6px;">
                    <span style="background:{status_bg}; color:{status_color}; padding:3px 10px; border-radius:12px; font-size:10px; font-weight:700; border: 1px solid {status_color}22;">{display_status}</span>
                </div>""", unsafe_allow_html=True)
            
            # Col 4: Actions (Consolidated Row)
            with r[3]:
                act_cols = st.columns([1, 1, 1, 1])
                with act_cols[0]:
                    if st.button("👁️ View", key=f"v_{u['email']}", use_container_width=True):
                        st.session_state.view_fac = u['email'] if st.session_state.get("view_fac") != u['email'] else None
                with act_cols[1]:
                    if st.button("✏️ Edit", key=f"e_{u['email']}", use_container_width=True):
                        st.session_state.edit_fac = u['email'] if st.session_state.get("edit_fac") != u['email'] else None
                with act_cols[2]:
                    if st.button("🔑 Reset", key=f"r_{u['email']}", use_container_width=True):
                        st.session_state.reset_pass = u['email']
                with act_cols[3]:
                    if st.button("🗑️ Del", key=f"d_{u['email']}", use_container_width=True):
                        st.session_state.confirm_del = u['email']
            
            st.markdown('<hr style="margin:8px 0; border:0; border-top:1px solid #f0f0f0;">', unsafe_allow_html=True)

            # --- Expanded Views ---
            
            # Confirmation: Reset Password
            if st.session_state.get("reset_pass") == u['email']:
                with st.form(f"reset_form_{u['email']}"):
                    new_p = st.text_input("New Password", type="password")
                    if st.form_submit_button("Confirm Reset"):
                        from modules.database import reset_password, add_audit_log
                        reset_password(u['email'], new_p)
                        add_audit_log("admin@gmail.com", "Password Reset", f"Admin reset password for {u['email']}")
                        st.success("Password updated!")
                        st.session_state.reset_pass = None
                        st.rerun()
                    if st.form_submit_button("Cancel"):
                        st.session_state.reset_pass = None
                        st.rerun()

            # Confirmation: Delete
            if st.session_state.get("confirm_del") == u['email']:
                st.warning(f"Are you sure you want to delete {u['name']} and all associated papers?")
                d1, d2 = st.columns(2)
                if d1.button("Yes, Permanent Delete", key=f"y_del_{u['email']}"):
                    from modules.database import delete_user, add_audit_log
                    delete_user(u['email'])
                    add_audit_log("admin@gmail.com", "Faculty Removed", f"Deleted faculty account: {u['name']} ({u['email']})")
                    st.rerun()
                if d2.button("No, Cancel", key=f"n_del_{u['email']}"):
                    st.session_state.confirm_del = None
                    st.rerun()

            # View Profile Overlay
            if st.session_state.get("view_fac") == u['email']:
                with st.expander(f"Profile Details: {u['name']}", expanded=True):
                    v1, v2 = st.columns(2)
                    v1.markdown(f"**Assigned Subjects:** {u['subjects'] or 'None'}")
                    v1.markdown(f"**Last Login:** {u['last_login'] or 'Never'}")
                    v2.markdown(f"**Papers Generated:** {u['paper_count']}")
                    v2.markdown(f"**Role:** {u['role']}")

            # Edit Form
            if st.session_state.get("edit_fac") == u['email']:
                with st.expander(f"Update Details for {u['name']}", expanded=True):
                    with st.form(f"edit_form_{u['email']}"):
                        e_name = st.text_input("Name", value=u['name'])
                        
                        e_depts = [
                            "Computer Science and Engineering (CSE)",
                            "Information Technology (IT)",
                            "Electronics and Communication Engineering (ECE)",
                            "Electrical and Electronics Engineering (EEE)",
                            "Mechanical Engineering (ME)",
                            "Civil Engineering (CE)",
                            "Artificial Intelligence and Data Science (AI & DS)",
                            "Artificial Intelligence and Machine Learning (AI & ML)",
                            "Cyber Security",
                            "Data Science"
                        ]
                        # Find current index for dept
                        try:
                            d_idx = e_depts.index(u['dept']) if u['dept'] in e_depts else 0
                        except:
                            d_idx = 0
                        e_dept = st.selectbox("Department", e_depts, index=d_idx)
                        
                        desigs = ["Professor", "Associate Professor", "Assistant Professor", "HOD", "Visiting Faculty", "Lecturer"]
                        try:
                            ds_idx = desigs.index(u['desig']) if u['desig'] in desigs else 0
                        except:
                            ds_idx = 0
                        e_desig = st.selectbox("Designation", desigs, index=ds_idx)
                        
                        e_subs = st.text_input("Subjects", value=u['subjects'] or "")
                        
                        if st.form_submit_button("Save Changes"):
                            from modules.database import update_user_details
                            update_user_details(u['email'], e_name, e_dept, e_desig, e_subs)
                            st.session_state.edit_fac = None
                            st.rerun()
                        if st.form_submit_button("Cancel"):
                            st.session_state.edit_fac = None
                            st.rerun()



def _all_papers():
    # --- Professional All Papers Layout ---
    st.markdown(f'<div style="font-size:24px; font-weight:800; color:{C.t1}; margin-bottom:20px; display:flex; align-items:center; gap:12px;">📄 System-Wide Generated Papers</div>', unsafe_allow_html=True)
    
    papers = get_all_papers_admin()
    
    if not papers:
        st.info("No papers generated yet.")
        return

    # Column Headers
    st.markdown(f"""
    <div style="background:{C.pageBg}; padding:12px 20px; border-radius:12px; margin-bottom:12px; border:1px solid {C.sbBd};">
        <div style="display:flex; align-items:center;">
            <div style="flex:3; font-size:10px; font-weight:800; color:{C.t4}; letter-spacing:1.2px;">PAPER TITLE & COURSE</div>
            <div style="flex:2; font-size:10px; font-weight:800; color:{C.t4}; letter-spacing:1.2px;">FACULTY AUTHOR</div>
            <div style="flex:1.2; font-size:10px; font-weight:800; color:{C.t4}; letter-spacing:1.2px;">STATS</div>
            <div style="flex:1.8; font-size:10px; font-weight:800; color:{C.t4}; letter-spacing:1.2px;">GENERATED AT</div>
            <div style="flex:1; font-size:10px; font-weight:800; color:{C.t4}; letter-spacing:1.2px; text-align:right;">ACTIONS</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    for p in papers:
        # DATA FIX: Correcting keys to match database schema (qCnt, mks)
        q_cnt = p.get('qCnt', 0)
        mks = p.get('mks', 0)
        email = p.get('user_email', 'Unknown')
        status = p.get('approval_status', 'Pending')
        downloaded = p.get('is_downloaded', False)
        
        # Status Badge Styling
        st_colors = {
            "Pending": ("#FFF4E5", "#B45309", "#FED7AA"),
            "Approved": ("#ECFDF5", "#047857", "#A7F3D0"),
            "Changes Requested": ("#FFF1F2", "#BE123C", "#FECDD3")
        }
        bg, fg, bd = st_colors.get(status, st_colors["Pending"])
        
        # Date Formatting
        raw_date = p.get('created_at_raw', 'N/A')
        try:
            from datetime import datetime
            dt = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
            disp_date = dt.strftime("%d %b, %Y")
            disp_time = dt.strftime("%I:%M %p")
        except:
            disp_date = raw_date
            disp_time = ""

        with st.container():
            c1, c2, c3, c4, c5 = st.columns([3, 2, 1.2, 1.8, 1])
            
            with c1:
                st.markdown(f"""
                <div style="display:flex; align-items:center; gap:14px; padding:4px 0;">
                    <div style="min-width:40px; height:40px; border-radius:12px; background:linear-gradient(135deg, {C.pageBg}, #fff); 
                                display:flex; align-items:center; justify-content:center; font-size:20px; border:1px solid {C.sbBd};">📄</div>
                    <div>
                        <div style="font-size:14px; font-weight:700; color:{C.t1}; line-height:1.2;">{p.get('exam_name', 'Untitled Paper')}</div>
                        <div style="font-size:11px; color:{C.t3}; margin-top:2px; font-weight:500;">{p.get('course_name', 'General Course')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with c2:
                dl_status = "✅ Downloaded" if downloaded else "⏳ Not Downloaded"
                dl_color = C.green if downloaded else C.t4
                st.markdown(f"""
                <div style="padding-top:6px;">
                    <div style="font-size:12px; color:{C.t2}; font-weight:700;">{email.split('@')[0].title()}</div>
                    <div style="font-size:10px; color:{dl_color}; font-weight:600;">{dl_status}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with c3:
                st.markdown(f"""
                <div style="padding-top:6px;">
                    <div style="font-size:13px; color:{C.violet}; font-weight:800;">{q_cnt} <span style="font-size:9px; font-weight:600; color:{C.t4};">QS</span></div>
                    <div style="font-size:11px; color:{C.t3}; font-weight:600;">{mks} <span style="font-size:9px; font-weight:500; color:{C.t4};">MKS</span></div>
                </div>
                """, unsafe_allow_html=True)
                
            with c4:
                st.markdown(f"""
                <div style="padding-top:6px;">
                    <div style="background:{bg}; color:{fg}; border:1px solid {bd}; padding:2px 8px; 
                                border-radius:20px; font-size:9px; font-weight:800; display:inline-block; margin-bottom:4px;">{status.upper()}</div>
                    <div style="font-size:10px; color:{C.t4}; font-weight:600;">{disp_date} · {disp_time}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with c5:
                # Professional compact action layout
                st.markdown('<div style="display:flex; justify-content:flex-end; padding-top:10px; gap:8px;">', unsafe_allow_html=True)
                if st.button("👁️", key=f"rev_{p['db_id']}", help="Review Paper & Provide Feedback"):
                    if st.session_state.get("reviewing_paper") == p['db_id']:
                        st.session_state.reviewing_paper = None
                    else:
                        st.session_state.reviewing_paper = p['db_id']
                    st.rerun()
                if st.button("🗑️", key=f"del_{p['db_id']}", help="Permanently Delete Paper"):
                    delete_paper(p['db_id'], email)
                    st.success("Paper deleted successfully.")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            # --- Review Dialog (Conditional) ---
            if st.session_state.get("reviewing_paper") == p['db_id']:
                with st.form(key=f"rev_form_v5_{p['db_id']}"):
                    # Header nested directly inside the form
                    st.markdown(f'''
                        <div style="display:flex; align-items:center; gap:10px; margin-bottom:20px; border-bottom:1px solid {C.sbBd}44; padding-bottom:12px;">
                            <div style="font-size:20px;">🧐</div>
                            <div>
                                <div style="font-size:15px; font-weight:800; color:{C.t1};">Reviewing: {p.get('exam_name', 'Paper')}</div>
                                <div style="font-size:10px; color:{C.t4}; font-weight:600;">Submitted by {email}</div>
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)

                    f_col1, f_col2 = st.columns([1, 1.5])
                    with f_col1:
                        all_statuses = ["Pending", "Submitted", "Approved", "Changes Requested"]
                        s_idx = all_statuses.index(status) if status in all_statuses else 0
                        new_status = st.selectbox("Update Approval Status", all_statuses, index=s_idx)
                    with f_col2:
                        new_comments = st.text_area("Admin Feedback / Comments", value=p.get('admin_comments', "") or "", placeholder="Provide feedback or reasons for changes...")
                    
                    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
                    
                    # Form Controls: Post Update, Cancel, and Download
                    ctrl_col1, ctrl_col2, ctrl_col3, _ = st.columns([1.2, 0.8, 1.2, 1.8])
                    btn_update = ctrl_col1.form_submit_button("✅ Post Update", use_container_width=True)
                    btn_cancel = ctrl_col2.form_submit_button("❌ Cancel", use_container_width=True)
                    
                    p_norm = _normalize_paper(p)
                    fmt = p.get('submission_format', 'PDF')
                    btn_download_trigger = ctrl_col3.form_submit_button(f"📥 Download {fmt}", use_container_width=True)
                    
                    if btn_update:
                        from modules.database import update_paper_approval
                        update_paper_approval(p['db_id'], new_status, new_comments)
                        st.session_state.reviewing_paper = None
                        st.success(f"Paper status updated to {new_status}")
                        time.sleep(1)
                        st.rerun()
                    if btn_cancel:
                        st.session_state.reviewing_paper = None

                # Download Confirmation & Preview Section (Conditional)
                if btn_download_trigger or st.session_state.get(f"dl_pending_{p['db_id']}"):
                    st.session_state[f"dl_pending_{p['db_id']}"] = True
                    
                    st.markdown(f'''
                    <div style="margin-top:20px; background:#F8F9FA; border-radius:12px; border:1px solid {C.sbBd}; padding:18px;">
                        <h4 style="margin:0 0 10px 0; color:{C.t1}; font-size:14px;">📥 Confirm Download: Paper Preview</h4>
                    ''', unsafe_allow_html=True)

                    # Preview Logic
                    if fmt == "PDF":
                        try:
                            pdf_path = ExportHandler.export_to_pdf(p_norm, f"Preview_{p['db_id']}.pdf")
                            with open(pdf_path, "rb") as f:
                                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="500" type="application/pdf" style="border-radius:8px; border:1px solid #ddd;"></iframe>'
                            st.markdown(pdf_display, unsafe_allow_html=True)
                        except Exception as e:
                            st.warning(f"Could not generate inline preview: {str(e)}")
                    else:
                        st.info(f"Inline preview limited for {fmt}. Please confirm download to view.")

                    st.markdown('<div style="height:15px;"></div>', unsafe_allow_html=True)
                    
                    conf_col1, conf_col2 = st.columns([1, 1])
                    with conf_col1:
                        try:
                            if fmt == "PDF":
                                f_path = ExportHandler.export_to_pdf(p_norm, f"Final_{p['db_id']}.pdf")
                                mime, ext = "application/pdf", "pdf"
                            elif fmt == "DOCX":
                                f_path = ExportHandler.export_to_docx(p_norm, f"Final_{p['db_id']}.docx")
                                mime, ext = "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"
                            else:
                                txt_data = ExportHandler._to_txt(p_norm)
                                st.download_button(f"✅ Click to Download {fmt}", txt_data, file_name=f"Paper_{p['db_id']}.txt", 
                                                  key=f"dl_final_{p['db_id']}", use_container_width=True)
                                f_path = None
                            
                            if f_path and os.path.exists(f_path):
                                with open(f_path, "rb") as f:
                                    st.download_button(f"✅ Click to Download {fmt}", f, file_name=f"Paper_{p['db_id']}.{ext}", 
                                                      mime=mime, key=f"dl_final_{p['db_id']}", use_container_width=True)
                        except Exception as e:
                            st.error(f"Download Error: {str(e)}")
                    
                    with conf_col2:
                        if st.button("Cancel Download", key=f"cancel_dl_{p['db_id']}", use_container_width=True):
                            st.session_state[f"dl_pending_{p['db_id']}"] = False
                            st.rerun()

                    st.markdown('</div>', unsafe_allow_html=True)

                st.markdown(f'<div style="height:1px; background:{C.sbBd}; margin:12px 0; opacity:0.4;"></div>', unsafe_allow_html=True)

            st.markdown(f'<div style="height:1px; background:{C.sbBd}; margin:12px 0; opacity:0.4;"></div>', unsafe_allow_html=True)

def _global_qbank():
    st.markdown(f'<div class="pg-card"><h3>Global Question Repository</h3>', unsafe_allow_html=True)
    st.info("Aggregate view of all AI-generated questions across departments.")
    # Here we would normally query questions table, but we aggregate from papers
    papers = get_all_papers_admin()
    all_qs = []
    for p in papers:
        for q in p.get('questions', []):
            q['paper_title'] = p.get('exam_name')
            q['author'] = p['user_email']
            all_qs.append(q)
            
    if not all_qs:
        st.warning("No questions found in the system.")
    else:
        st.write(f"Total Questions in Bank: {len(all_qs)}")
        # Simple list for now
        for q in all_qs[:10]: # Limit for performance
            st.markdown(f"""
            <div style="padding:10px; border:1px solid #eee; border-radius:8px; margin-bottom:8px;">
              <small style="color:{C.t4}">{q.get('type')} · {q.get('difficulty')} · {q.get('marks')} Marks</small><br>
              <strong>{q.get('q')}</strong><br>
              <small style="color:{C.t3}">Author: {q['author']}</small>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def _sys_analytics():
    st.markdown(f'<div class="pg-card"><h3>System Analytics</h3>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.button("Total Generation Trends (Last 30 Days)")
        st.markdown("<div style='height:150px; background:#f9f9f9; border-radius:10px; display:flex; align-items:center; justify-content:center; color:#ccc;'>Chart: Generation Volatility</div>", unsafe_allow_html=True)
    with c2:
        st.button("Departmental Contribution")
        st.markdown("<div style='height:150px; background:#f9f9f9; border-radius:10px; display:flex; align-items:center; justify-content:center; color:#ccc;'>Chart: Paper Share</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def _ann_mgt():
    st.markdown(f'<div class="pg-card"><h3>Announcements Manager</h3>', unsafe_allow_html=True)
    with st.form("new_ann"):
        title = st.text_input("Announcement Title")
        body = st.text_area("Message Body")
        antype = st.selectbox("Type", ["info", "success", "warning"])
        if st.form_submit_button("Post Announcement"):
            if title and body:
                add_announcement(title, body, antype)
                st.success("Announcement posted to all faculty dashboards.")
            else:
                st.error("Please fill in all fields.")
    
    st.markdown("<h4>Current Announcements</h4>", unsafe_allow_html=True)
    anns = get_announcements()
    if not anns:
        st.info("No announcements found.")
    else:
        for a in anns:
            st.markdown(f"""
            <div style="padding:10px; border-left:4px solid {C.violet if a['type']=='info' else C.green if a['type']=='success' else C.pink}; background:#f9f9f9; margin-bottom:10px; border-radius:0 8px 8px 0;">
              <strong>{a['title']}</strong><br><small>{a['created_at']}</small><br>
              <p style="font-size:12px;">{a['message']}</p>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def _api_monitor():
    st.markdown(f'<div class="pg-card"><h3>Gemini API Usage Monitor</h3>', unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    k1.metric("Requests Today", "124", "+12%")
    k2.metric("Success Rate", "98.2%", "+0.5%")
    k3.metric("Quota Remaining", "84%", "-5%")
    
    st.markdown("<br><strong>Recent API Latency</strong>", unsafe_allow_html=True)
    st.markdown("<div style='height:100px; background:#f9f9f9; border-radius:8px;'></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def _sys_settings():
    st.markdown(f'<div class="pg-card"><h3>Platform Constraints</h3>', unsafe_allow_html=True)
    settings = get_system_settings()
    
    ai_enabled = st.toggle("Enable AI Generation", value=settings.get("enable_ai") == "true")
    uploads_allowed = st.toggle("Allow PDF/Syllabus Upload", value=settings.get("allow_uploads") == "true")
    max_qs = st.slider("Global Max Questions", 10, 100, int(settings.get("max_questions", 30)))
    
    if st.button("Save System Config", type="primary"):
        update_system_setting("enable_ai", "true" if ai_enabled else "false")
        update_system_setting("allow_uploads", "true" if uploads_allowed else "false")
        update_system_setting("max_questions", max_qs)
        st.success("System configurations updated successfully.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f'<div class="pg-card"><h3>Audit Logs</h3><p style="color:{C.t3};font-size:12px;">System-wide activity monitoring and security audits.</p>', unsafe_allow_html=True)
    logs = get_audit_logs(limit=100)
    
    if not logs:
        st.info("No audit logs available.")
    else:
        st.markdown("""
        <table style="width:100%; font-size:12px; border-collapse: collapse;">
          <tr style="background:#f8f9fa; border-bottom:1px solid #eee;">
            <th style="padding:10px; text-align:left;">Timestamp</th>
            <th style="padding:10px; text-align:left;">User</th>
            <th style="padding:10px; text-align:left;">Action</th>
            <th style="padding:10px; text-align:left;">Details</th>
          </tr>
        """, unsafe_allow_html=True)
        for l in logs:
            st.markdown(f"""
            <tr style="border-bottom:1px solid #f0f0f0;">
              <td style="padding:10px;">{l['time']}</td>
              <td style="padding:10px;"><strong>{l['user']}</strong></td>
              <td style="padding:10px;"><span style="color:{C.violet if 'Failed' not in l['action'] else C.pink}">{l['action']}</span></td>
              <td style="padding:10px; color:{C.t3}">{l['details']}</td>
            </tr>
            """, unsafe_allow_html=True)
        st.markdown("</table>")
    st.markdown("</div>", unsafe_allow_html=True)

def _adm_templates():
    st.markdown(f'<div class="pg-card"><h3>Global Templates Management</h3>', unsafe_allow_html=True)
    st.info("Manage standard question paper templates available to all faculty.")
    templates = [
        {"name": "Standard University Pattern", "qs": 25, "marks": 100},
        {"name": "Short Quiz Assessment", "qs": 10, "marks": 20},
        {"name": "End-Sem Comprehensive", "qs": 30, "marks": 100},
    ]
    for t in templates:
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; padding:12px; background:#fcfcfc; border:1px solid #efefef; border-radius:8px; margin-bottom:8px;">
          <div><strong>{t['name']}</strong><br><small>{t['qs']} Questions · {t['marks']} Marks</small></div>
          <div><button style="font-size:10px; padding:2px 8px; border-radius:4px; border:1px solid #ccc; cursor:pointer;">Edit Template</button></div>
        </div>
        """, unsafe_allow_html=True)
    st.button("➕ Create New Global Template", type="primary")
    st.markdown("</div>", unsafe_allow_html=True)

def _usage_stats():
    st.markdown(f'<div class="pg-card"><h3>Platform Usage Statistics</h3>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Papers per Month**")
        st.markdown("<div style='height:180px; background:#f5f5f5; border-radius:12px; margin-top:10px; display:flex; align-items:center; justify-content:center; color:#adb5bd;'>Growth Chart View</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("**Average Generation Time**")
        st.markdown("<div style='height:180px; background:#f5f5f5; border-radius:12px; margin-top:10px; display:flex; align-items:center; justify-content:center; color:#adb5bd;'>Latency Metrics (s)</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def _adm_downloads():
    st.markdown(f'<div class="pg-card"><h3>Master Download Center</h3><p style="color:{C.t3};font-size:12px;">Access every question paper generated on the system.</p>', unsafe_allow_html=True)
    f_dept = st.selectbox("Filter by Department", ["All Departments", "Computer Science", "Electronics", "Mechanical"])
    papers = get_all_papers_admin()
    if f_dept != "All Departments":
        papers = [p for p in papers if p.get('dept') == f_dept]
    
    for p in papers:
        st.markdown(f"""
        <div style="padding:15px; border:1px solid #eee; border-radius:10px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-weight:700; color:{C.t1};">{p.get('exam_name')}</div>
            <div style="font-size:11px; color:{C.t4};">{p.get('user_email')} · {p.get('created_at_raw')}</div>
          </div>
          <div style="display:flex; gap:5px;">
            <button style="padding:4px 10px; font-size:10px; border-radius:4px; border:1px solid {C.sbBd}; cursor:pointer;">PDF</button>
            <button style="padding:4px 10px; font-size:10px; border-radius:4px; border:1px solid {C.sbBd}; cursor:pointer;">DOCX</button>
          </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def _security():
    st.markdown(f'<div class="pg-card"><h3>Security & Access Control</h3>', unsafe_allow_html=True)
    st.warning("Monitor for suspicious activity and unauthorized access attempts.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Blocked IPs**")
        st.code("192.168.1.105 (Suspicious Logins)\n103.45.21.90 (Rate Limiting)")
    with col2:
        st.markdown(f"**Admin Actions**")
        st.button("Flush Session Cache")
        st.button("Force Logout All Users", type="secondary")
        
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<strong>Recent Login Attempts</strong>", unsafe_allow_html=True)
    st.table([
        ("Anil Gupta", "Failed", "12:15 PM", "Invalid Password"),
        ("System Admin", "Success", "11:50 AM", "Standard Login"),
        ("Prof. Mary", "Success", "10:30 AM", "Cached Session"),
    ])
    st.markdown("</div>", unsafe_allow_html=True)

def _adm_about():
    st.markdown(f"""
    <div class="pg-card">
      <h3>About PaperGen AI Admin v5.0</h3>
      <p style="color:{C.t3}; line-height:1.6;">
        The Administrative Dashboard provides high-level oversight of the AI Question Paper Generator ecosystem. 
        It is designed to ensure platform stability, monitor resource usage (API quotas), and manage the growing 
        repository of academic content generated by the system.
      </p>
      <hr style="opacity:0.1;">
      <p style="font-size:11px; color:{C.t4};">
        Built with Streamlit & Gemini Pro AI. <br>
        &copy; 2026 PaperGen AI Production Team. All rights reserved.
      </p>
    </div>
    """, unsafe_allow_html=True)

def _db_inspector():
    st.markdown(f'<div class="pg-card"><h3>Database Inspector</h3><p style="color:{C.t3};font-size:12px;">Direct browse-only access to system tables for auditing.</p>', unsafe_allow_html=True)
    
    tables = ["users", "user_papers", "audit_logs", "announcements", "system_settings"]
    target = st.selectbox("Select Table to Inspect", tables)
    
    cols, rows = get_db_raw_data(target)
    
    if cols is None:
        st.error(f"Error reading table: {rows}")
    else:
        import pandas as pd
        df = pd.DataFrame(rows, columns=cols)
        st.write(f"Displaying **{len(rows)}** records from `{target}`")
        st.dataframe(df, use_container_width=True)
    
    st.info("💡 Tip: This tool allows you to see the exact state of the database in real-time.")
    st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# PAGE: ACTIVITY LOGS (AUDIT)
# ═══════════════════════════════════════════════════════════════
def _logs():
    from modules.database import get_audit_logs
    
    # Hero Title
    st.markdown(f"""
    <div style="background:white; border-radius:12px; border:1px solid {C.sbBd}; padding:18px; margin-bottom:20px; box-shadow:{C.cardSh};">
        <h3 style="margin:0; color:{C.t1}; font-size:16px; font-weight:700;">📜 System Activity & Audit Logs</h3>
        <p style="font-size:12px; color:{C.t3}; margin-top:4px;">Monitor all administrative and faculty actions for transparency and security.</p>
    </div>
    """, unsafe_allow_html=True)

    # Controls
    c1, c2, c3 = st.columns([1.5, 1, 1])
    with c1:
        search = st.text_input("🔍 Search User Email", placeholder="user@gmail.com...").strip().lower()
    with c2:
        actions = ["All Details", "Login", "Signout", "Paper"]
        action_filter = st.selectbox("🎯 Filter Action Type", actions)
    with c3:
        rows_limit = st.selectbox("🔢 Rows", [50, 100, 250, 500])

    logs_raw = get_audit_logs(limit=rows_limit)
    
    # Safe Filtering
    filtered = logs_raw
    if search:
        filtered = [l for l in filtered if l.get('user') and search in l['user'].lower()]
    
    if action_filter != "All Details":
        # Mapping labels to search terms
        sterm = action_filter.upper()
        if sterm == "SIGNOUT": sterm = "SIGN OUT"
        
        filtered = [l for l in filtered if l.get('action') and sterm in l['action'].upper()]

    if not filtered:
        st.markdown(f'<div style="text-align:center; padding:40px; color:{C.t4}; border:1px solid {C.sbBd}; border-radius:0 0 10px 10px; background:white;">No logs recorded yet.</div>', unsafe_allow_html=True)
        return

    # Table Header Design
    st.markdown(f"""
    <div style="background:{C.pageBg}; border:1px solid {C.sbBd}; border-radius:10px 10px 0 0; 
                padding:12px 18px; display:grid; grid-template-columns: 180px 220px 180px 1fr; 
                font-size:11px; font-weight:800; color:{C.t3}; text-transform:uppercase; letter-spacing:0.5px;">
        <div>Timestamp</div>
        <div>User</div>
        <div>Action Type</div>
        <div>Details / Metadata</div>
    </div>
    """, unsafe_allow_html=True)

    # Helper for action badges
    def get_badge(act):
        act = act.upper()
        if "LOGIN" in act or "OUT" in act:
            return f'<span style="background:#F0F7FF; color:#007BFF; padding:4px 10px; border-radius:6px; font-size:9.5px; font-weight:800; border:1px solid #BEE3F8;">{act}</span>'
        if "PAPER" in act:
            return f'<span style="background:#E8F7EE; color:#28A745; padding:4px 10px; border-radius:6px; font-size:9.5px; font-weight:800; border:1px solid #BFF0D4;">{act}</span>'
        if "FACULTY" in act:
            return f'<span style="background:#FFF8F0; color:#FD7E14; padding:4px 10px; border-radius:6px; font-size:9.5px; font-weight:800; border:1px solid #FFE8CC;">{act}</span>'
        if "RESET" in act or "SECURITY" in act or "DELETE" in act:
            return f'<span style="background:#FFF5F5; color:#E53E3E; padding:4px 10px; border-radius:6px; font-size:9.5px; font-weight:800; border:1px solid #FED7D7;">{act}</span>'
        return f'<span style="background:#F8F9FA; color:#6C757D; padding:4px 10px; border-radius:6px; font-size:9.5px; font-weight:800; border:1px solid #DEE2E6;">{act}</span>'

    for l in filtered:
        details = l['details'] if l['details'] else "-"
        st.markdown(f"""
        <div style="background:white; border:1px solid {C.sbBd}; border-top:none; 
                    padding:14px 18px; display:grid; grid-template-columns: 180px 220px 180px 1fr; 
                    font-size:12px; align-items:center;">
            <div style="color:{C.t4}; font-family:monospace; font-size:11px;">{l['time']}</div>
            <div style="color:{C.t1}; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{l['user']}</div>
            <div>{get_badge(l['action'])}</div>
            <div style="color:{C.t2}; font-size:11.5px; line-height:1.4;">{details}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="height:30px;"></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# PAGE: ADMIN ALERTS
# ═══════════════════════════════════════════════════════════════
def _admin_alerts():
    from modules.database import get_notifications, mark_notification_read
    notifs = get_notifications("admin@gmail.com")
    
    st.markdown(f"""
    <div style="background:white; border-radius:12px; border:1px solid {C.sbBd}; padding:18px; margin-bottom:20px; box-shadow:{C.cardSh};">
        <h3 style="margin:0; color:{C.t1}; font-size:16px; font-weight:700;">🔔 System Alerts & Notifications</h3>
        <p style="font-size:12px; color:{C.t3}; margin-top:4px;">Relay critical system updates and paper submission alerts.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if not notifs:
        st.info("No system alerts logged.")
        return

    unread = [n for n in notifs if not n["is_read"]]
    t1, t2 = st.tabs([f"New Alerts ({len(unread)})", "Broadcast History"])
    
    with t1:
        if not unread:
            st.markdown(f'<div style="text-align:center; padding:40px; color:{C.t4};">All caught up!</div>', unsafe_allow_html=True)
        else:
            for n in unread:
                nc1, nc2 = st.columns([0.88, 0.12])
                with nc1:
                    st.markdown(f"""
                    <div style="padding:12px 16px; background:#F8F4FD; border-radius:8px; border-left:4px solid {C.violet}; margin-bottom:10px;">
                        <div style="font-size:13px; color:{C.t1}; font-weight:500;">{n['message']}</div>
                        <div style="font-size:10px; color:{C.t4}; margin-top:4px;">{n['time']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with nc2:
                    if st.button("👁️", key=f"clr_adm_pg_{n['id']}", help="View Paper & Mark as Read"):
                        mark_notification_read(n["id"])
                        if n.get("paper_id"):
                            st.session_state.admin_page = "all_papers"
                            st.session_state.reviewing_paper = n["paper_id"]
                        st.rerun()

    with t2:
        read_notifs = [n for n in notifs if n["is_read"]]
        if not read_notifs:
            st.markdown(f'<div style="text-align:center; padding:40px; color:{C.t4};">No historical alerts.</div>', unsafe_allow_html=True)
        else:
            for n in read_notifs:
                st.markdown(f"""
                <div style="padding:12px 16px; background:white; border:1px solid #f0f0f0; border-radius:8px; margin-bottom:10px; opacity:0.75;">
                    <div style="font-size:13px; color:{C.t2};">{n['message']}</div>
                    <div style="font-size:10px; color:{C.t4}; margin-top:4px;">{n['time']}</div>
                </div>
                """, unsafe_allow_html=True)

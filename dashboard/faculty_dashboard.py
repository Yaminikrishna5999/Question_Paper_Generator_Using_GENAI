import streamlit as st
import time
import re
import os
from datetime import datetime

# ── Project imports ──
from config import Config
from modules.export_handler import ExportHandler
import io
import os
from modules.database import (
    save_paper, get_user_papers, delete_paper, 
    add_audit_log, get_announcements, get_system_settings,
    get_notifications, mark_notification_read, add_notification,
    submit_paper
)

# ── Load .env (already handled by Config, but kept for safety) ──
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ═══════════════════════════════════════════════════════════════
# PaperGen AI v5.0 — Gold Standard Design Tokens
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
# STATIC DATA  (UI/display only — NOT used for question generation)
# ═══════════════════════════════════════════════════════════════
SEED_TEMPLATES = [
    {"id":1,"name":"Standard Mid-Sem",    "desc":"20 questions, 3 hrs, mixed types","q":20,"m":100,"diff":"Balanced",  "uses":12},
    {"id":2,"name":"MCQ Only Quiz",        "desc":"30 MCQs, 1 hr, fully objective",  "q":30,"m":60, "diff":"Accessible","uses":8},
    {"id":3,"name":"End-Sem Comprehensive","desc":"25 questions, 3 hrs, all types",  "q":25,"m":100,"diff":"Rigorous",  "uses":6},
    {"id":4,"name":"Lab Viva Pattern",     "desc":"15 short, 5 long, practical focus","q":20,"m":50,"diff":"Balanced",  "uses":4},
]

SEED_ANNOUNCEMENTS = [
    {"id":1,"title":"System Maintenance",    "body":"PaperGen AI will undergo maintenance on Sunday 2–4 AM. Please save your work.","type":"warning","time":"Today 9:00 AM"},
    {"id":2,"title":"New Feature: Templates","body":"Paper Templates are now available. Reuse your preferred paper configurations.","type":"info",   "time":"Yesterday"},
    {"id":3,"title":"API Upgrade Complete",  "body":"Gemini Pro API has been upgraded to the latest version.","type":"success","time":"2 days ago"},
    {"id":4,"title":"Semester End Reminder", "body":"Ensure all end-sem papers are submitted at least 5 days before exam date.","type":"warning","time":"3 days ago"},
]

# ═══════════════════════════════════════════════════════════════
# EXPORT HELPER — bridges dashboard paper schema → ExportHandler schema
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

FACULTY_NAV = [
    ("MAIN",     [("🏠","Dashboard",     "dashboard"),
                  ("🔔","Faculty Alerts", "faculty_alerts"),
                  ("⚙️","Configuration","configuration")]),
    ("ACADEMICS",[("📄","My Papers",     "papers"),
                  ("🖨️","Exam Preview",  "preview"),
                  ("🔑","Answer Keys",   "answers"),
                  ("📋","Marks Scheme",  "markscheme"),
                  ("🗂️","Question Bank","qbank"),
                  ("📐","Templates",     "templates")]),
    ("REPORTS",  [("📊","Statistics",    "statistics"),
                  ("📥","Downloads",     "downloads"),
                  ("📢","Announcements", "announcements_page")]),
    ("SYSTEM",   [("🔧","Settings",      "settings"),
                  ("ℹ️","About",         "about")]),
]

# ═══════════════════════════════════════════════════════════════
# GEMINI API  — real generation, no simulation
# ═══════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════
# UTILS
# ═══════════════════════════════════════════════════════════════
def _track_dl(dtype, pname, db_id=None):
    if "v5_downloads" not in st.session_state:
        st.session_state.v5_downloads = 0
    st.session_state.v5_downloads += 1
    user_email = st.session_state.get("user_data", {}).get("email", "unknown")
    add_audit_log(user_email, "Download", f"Downloaded {dtype}: {pname}")
    if db_id:
        from modules.database import mark_paper_downloaded
        mark_paper_downloaded(db_id)

def _get_key():
    # Priority: Session State (Manual Entry) > Config (.env) > OS Env
    return st.session_state.get("v5_api_key") or Config.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "").strip()

def _validate_key(key):
    """Returns (ok:bool, err_code:str)"""
    if not key:
        return False, "no_key"
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        # Using list_models() for more robust validation (avoids 404 model not found issues)
        models = genai.list_models()
        next(models, None) # Trigger the API call
        return True, ""
    except Exception as e:
        s = str(e)
        if "pk" in s or "API_KEY_INVALID" in s: return False, "invalid"
        if "quota" in s.lower(): return False, "quota"
        return False, f"other:{s}"

# ═══════════════════════════════════════════════════════════════
# GLOBAL CSS  — sidebar active/hover, Gold Standard palette
# ═══════════════════════════════════════════════════════════════
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

    /* ── ACTIVE: pink→violet gradient ──
       Trick: wrap active button in  <div class="nav-on">
       CSS child selector targets only that button           */
    div.nav-on > div.stButton > button,
    div.nav-on > div.stButton > button:hover,
    div.nav-on > div.stButton > button:focus{{
        background:linear-gradient(135deg,#F72585,#7209B7) !important;
        color:#ffffff !important;
        font-weight:700 !important;
        border:none !important;
        transform:none !important;
        box-shadow:0 3px 10px rgba(114,9,183,0.28) !important;
    }}

    /* ── Sign-out button ── */
    div.btn-out > div.stButton > button{{
        background:#FFF0F6 !important;
        color:{C.pink} !important;
        border:1px solid #F9C2D9 !important;
        font-weight:600 !important;
    }}
    div.btn-out > div.stButton > button:hover{{
        background:{C.pink} !important;
        color:#fff !important;
        border-color:{C.pink} !important;
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

    /* ── Progress bar ── */
    .stProgress > div > div{{background:linear-gradient(135deg,#F72585,#7209B7) !important;}}

    .cfg-section-wrapper {{
        background: white;
        border: 1px solid #EDE8F5;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 25px;
        box-shadow: 0 2px 8px rgba(114,9,183,0.03);
    }}
    .cfg-section-header {{
        background: linear-gradient(90deg, #F4F0FB 0%, #ffffff 100%);
        border-left: 4px solid #7209B7;
        padding: 12px 18px;
        margin: 0 0 20px 0;
        font-weight: 700;
        color: #2D1B69;
        font-size: 15px;
        display: flex;
        align-items: center;
        gap: 12px;
        border-radius: 0 8px 8px 0;
    }}
    .cfg-sub-label {{
        font-size: 10.5px;
        color: #6E6893;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 8px;
        display: block;
    }}
    .stMultiSelect div[role="listbox"] {{
        background: #F4F0FB !important;
    }}
    .disabled-overlay {{
        opacity: 0.5;
        pointer-events: none;
        filter: grayscale(1);
    }}
    /* ── Dropdown Hand Cursor ── */
    div[data-baseweb="select"] {{
        cursor: pointer !important;
    }}
    div[data-baseweb="select"] * {{
        cursor: pointer !important;
    }}
    .stCheckbox label, .stToggle label {{
        cursor: pointer !important;
    }}

    /* ── Expander Neat & Clean ── */
    .stExpander {{
        background: white !important;
        border: 1px solid #EDE8F5 !important;
        border-radius: 10px !important;
        margin-bottom: 12px !important;
        overflow: hidden !important;
    }}
    .stExpander > details > summary {{
        padding: 12px 16px !important;
        background: #ffffff !important;
        color: #2D1B69 !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }}
    .stExpander > details > summary:hover {{
        background: #F4F0FB !important;
    }}
    /* Force hide any leaked icon text */
    .stExpander summary svg + div {{
        display: none !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════
def show_v5_faculty_dashboard():
    # ── Multi-Tenant Isolation: Clear state if user changed ──
    cp_email = st.session_state.get("user_data", {}).get("email", "")
    if st.session_state.get("v5_user_email") != cp_email:
        st.session_state.v5_user_email = cp_email
        if "v5_papers" in st.session_state: del st.session_state.v5_papers
        if "v5_config" in st.session_state: del st.session_state.v5_config
        # Re-fetch papers for the NEW user
        st.session_state["v5_papers"] = get_user_papers(cp_email) if cp_email else []

    for k, v in [("v5_page","dashboard"), ("v5_toast",None), ("v5_downloads", 0)]:
        if k not in st.session_state:
            st.session_state[k] = v

    if "v5_templates" not in st.session_state:
        st.session_state["v5_templates"] = SEED_TEMPLATES.copy()
    if "v5_config" not in st.session_state:
        st.session_state.v5_config = {
            # Section 1: Identity
            "exam_name": "Mid Term Examination",
            "inst_name": "University of Technology",
            "dept": "Computer Science",
            "course_name": "Data Structures",
            "course_code": "CS101",
            "academic_year": "2nd Year",
            "semester": "Semester 3",
            "exam_type": "Mid Exam",
            "exam_date": datetime.now().date(),
            "duration": "3 Hours",
            "max_marks": 100,
            
            # Section 2: Structure
            "total_questions": 10,
            "num_sections": 3,
            "instructions": "1. Answer all questions.\n2. Figures to the right indicate full marks.",
            
            # Section 3: Question Config
            "question_types": ["MCQ", "Short Answer"],
            "marks_per_type": {"MCQ": 2, "Short Answer": 5, "Long Answer": 10},
            "counts_per_type": {"MCQ": 5, "Short Answer": 5},
            "difficulty": "Medium",
            "bloom": ["Remember", "Understand"],
            
            # Section 4/5: Source & Units
            "source_mode": "Manual Topic Entry",
            "topics": [],
            "file_content": None,
            "units": ["Unit 1", "Unit 2", "Unit 3"],
            "unit_dist": {"Unit 1": 3, "Unit 2": 3, "Unit 3": 4},
            
            # Section 6/7: Advanced & Batch
            "randomize": True,
            "avoid_duplicates": True,
            "include_prev": False,
            "num_sets": 1
        }
    
    if "v5_templates" not in st.session_state:
        st.session_state.v5_templates = SEED_TEMPLATES.copy()

    _css()

    u    = st.session_state.get("user_data", {})
    user = {
        "name":   u.get("name",  "Faculty Member"),
        "dept":   u.get("dept",  "Department"),
        "desig":  u.get("desig", "Specialist"),
        "avatar": "".join([w[0] for w in u.get("name","F").split() if w][:2]).upper(),
    }

    # ════════════════════════════════════════════════════════
    # SIDEBAR
    # ════════════════════════════════════════════════════════
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

        # Fetch unread count for sidebar
        from modules.database import get_notifications
        user_email = user.get('email', '')
        unread_notifs = [n for n in get_notifications(user_email) if not n["is_read"]]
        unread_count = len(unread_notifs)

        # ── Navigation ──
        for section, items in FACULTY_NAV:
            st.markdown(f'<span class="sb-lbl">{section}</span>', unsafe_allow_html=True)
            for icon, label, page_id in items:
                active  = (st.session_state.v5_page == page_id)
                
                # Dynamic label with unread count
                display_label = label
                if page_id == "faculty_alerts" and unread_count > 0:
                    display_label = f"{label} ({unread_count})"
                
                btn_lbl = f"{icon}  {display_label}"
                cls     = "nav-on" if active else "nav-off"
                st.markdown(f'<div class="{cls}" style="padding:1px 9px 0;">', unsafe_allow_html=True)
                clicked = st.button(btn_lbl, key=f"nav_{page_id}", use_container_width=True)
                if clicked and not active:
                    st.session_state.v5_page = page_id
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # ── Sign out ──
        st.markdown(f'<div style="border-top:1px solid {C.sbBd};margin:10px 0 0;"></div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="btn-out" style="padding:5px 9px 8px;">', unsafe_allow_html=True)
        if st.button("🚪  Sign Out", key="signout", use_container_width=True):
            # Log sign out
            from modules.database import add_audit_log
            user_email = st.session_state.get("user_data", {}).get("email", "unknown_faculty")
            add_audit_log(user_email, "Faculty Sign Out", "Faculty logged out")
            
            # Explicitly clear user session context
            for key in ["logged_in", "user_role", "user_data", "v5_papers", "v5_config", "v5_user_email"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════
    # TOP BAR
    # ════════════════════════════════════════════════════════
    tc1, tc2 = st.columns([3, 1])
    with tc1:
        lbl = st.session_state.v5_page.replace("_page","").replace("_"," ").title()
        st.markdown(f"""
        <div style="margin-top:4px;margin-bottom:2px;">
          <div style="font-size:18px;font-weight:800;color:{C.t1};line-height:1.2;">{lbl}</div>
          <div style="font-size:9.5px;color:{C.t4};">PaperGen AI › {lbl}</div>
        </div>""", unsafe_allow_html=True)
    with tc2:
        api_key = _get_key()
        if api_key:
            ab, ac, ad, at = "#E8F7EE", C.green, "#BFF0D4", "API Connected"
        else:
            ab, ac, ad, at = "#FFF0F0", "#E74C3C", "#FACDD0", "No API Key"
        st.markdown(f"""
        <div style="display:flex;justify-content:flex-end;gap:6px;margin-top:4px;">
          <div style="background:white;padding:4px 9px;border-radius:20px;
                      border:1px solid {C.sbBd};font-size:9px;font-weight:600;color:{C.t3};">
            🕐 {datetime.now().strftime("%I:%M %p")}</div>
          <div style="background:{ab};color:{ac};padding:4px 9px;border-radius:20px;
                      border:1px solid {ad};font-size:9px;font-weight:700;">{at}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f'<hr style="border:none;border-top:1px solid {C.sbBd};margin:8px 0 12px;">',
                unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════
    # PAGE ROUTER
    # ════════════════════════════════════════════════════════
    st.markdown('<div class="page-content">', unsafe_allow_html=True)
    pg = st.session_state.v5_page
    if   pg == "dashboard":          _dash(user)
    elif pg == "faculty_alerts":     _faculty_alerts()
    elif pg == "configuration":      _config()
    elif pg == "papers":             _papers()
    elif pg == "preview":            _preview()
    elif pg == "answers":            _answers()
    elif pg == "markscheme":         _markscheme()
    elif pg == "qbank":              _qbank()
    elif pg == "templates":          _templates()
    elif pg == "statistics":         _statistics()
    elif pg == "downloads":          _downloads()
    elif pg == "announcements_page": _announcements()
    elif pg == "settings":           _settings()
    elif pg == "about":              _about()
    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ═══════════════════════════════════════════════════════════════
def _dash(user):
    st.markdown(f"""
    <div class="pg-hero">
      <div style="font-size:9px;font-weight:700;letter-spacing:1.2px;
                  color:rgba(255,255,255,0.65);text-transform:uppercase;margin-bottom:5px;">WELCOME BACK</div>
      <h1 style="font-size:25px;font-weight:800;margin:0 0 8px;">Hello, {user['name']} 👋</h1>
      <p style="font-size:12.5px;opacity:0.82;max-width:500px;line-height:1.6;margin:0;">
        Your AI workspace is ready. Generate premium examination papers with Gemini Pro in minutes.
      </p>
    </div>""", unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    stats = [
        ("📄","My Papers",  len(st.session_state.v5_papers),                   C.gPink,   "rgba(247,37,133,0.2)"),
        ("❓","Questions",  sum(p["qCnt"] for p in st.session_state.v5_papers), C.gViolet, "rgba(114,9,183,0.2)"),
        ("📥","Downloads",  st.session_state.v5_downloads,                       C.gSkyBlue,"rgba(76,201,240,0.2)"),
        ("📢","Notices",    len(SEED_ANNOUNCEMENTS),                             C.gOrange, "rgba(248,150,30,0.2)"),
    ]
    for col, (icon, label, val, grad, glow) in zip([k1,k2,k3,k4], stats):
        with col:
            st.markdown(f"""
            <div class="pg-kpi" style="background:{grad};box-shadow:0 5px 15px {glow};">
              <div style="font-size:19px;">{icon}</div>
              <div>
                <div style="font-size:23px;font-weight:800;">{val}</div>
                <div style="font-size:8.5px;opacity:0.78;font-weight:700;text-transform:uppercase;">{label}</div>
              </div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])

    with c1:
        st.markdown(f'<div style="font-size:14px; font-weight:800; color:{C.t1}; margin-bottom:12px;">🕒 Recent Activity</div>', unsafe_allow_html=True)
        papers = st.session_state.get("v5_papers", [])
        if not papers:
            st.markdown(f"""
            <div class="pg-card" style="padding:25px; text-align:center; color:{C.t4}; border:1px dashed {C.sbBd};">
                <div style="font-size:24px; margin-bottom:10px;">📊</div>
                <div style="font-size:12px; font-weight:700;">No recent generation activity</div>
                <div style="font-size:10px;">Your generated papers will appear here in real-time.</div>
            </div>""", unsafe_allow_html=True)
        else:
            for p in papers[:4]:
                st.markdown(f"""
                <div class="pg-card" style="padding:12px; margin-bottom:10px; display:flex; align-items:center; gap:12px;">
                    <div style="width:36px; height:36px; border-radius:10px; background:{C.pageBg}; 
                                display:flex; align-items:center; justify-content:center; font-size:16px;">📄</div>
                    <div style="flex:1;">
                        <div style="display:flex; justify-content:space-between;">
                            <div style="font-size:12px; font-weight:800; color:{C.t1};">{p['name']}</div>
                            <div style="font-size:9px; color:{C.t4}; font-weight:600;">{p.get('created_at','Just now')}</div>
                        </div>
                        <div style="font-size:10px; color:{C.t3}; margin-top:2px;">
                            {p.get('course_name','')} • {p.get('qCnt',0)} Questions • {p.get('mks',0)} Marks
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f'<div style="font-size:14px; font-weight:800; color:{C.t1}; margin-bottom:12px;">🛡️ System Readiness</div>', unsafe_allow_html=True)
        
        # API Status
        api_ok = bool(_get_key())
        api_color = C.green if api_ok else C.pink
        api_ico = "✅" if api_ok else "❌"
        api_txt = "Active & Configured" if api_ok else "Key Required"
        
        st.markdown(f"""
        <div class="pg-card" style="padding:15px; margin-bottom:15px; border-left:4px solid {api_color};">
            <div style="display:flex; align-items:center; gap:10px;">
                <div style="font-size:18px;">{api_ico}</div>
                <div>
                    <div style="font-size:11px; font-weight:800; color:{C.t1};">Gemini API Status</div>
                    <div style="font-size:9px; font-weight:700; color:{api_color};">{api_txt}</div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)
        
        # Environment Status
        st.markdown(f"""
        <div class="pg-card" style="padding:15px; border-left:4px solid {C.sky};">
            <div style="display:flex; align-items:center; gap:10px;">
                <div style="font-size:18px;">🏗️</div>
                <div>
                    <div style="font-size:11px; font-weight:800; color:{C.t1};">Environment</div>
                    <div style="font-size:9px; font-weight:700; color:{C.t3};">Production v5.0 Stable</div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:14px; font-weight:800; color:{C.t1}; margin-bottom:12px;">📫 Latest Notice</div>', unsafe_allow_html=True)
        anns = get_announcements()
        if anns:
            a = anns[0]
            st.markdown(f"""
            <div class="pg-card" style="padding:15px; background:linear-gradient(to right, #ffffff, {C.pageBg});">
                <div style="font-size:11px; font-weight:800; color:{C.t1}; margin-bottom:5px;">{a['title']}</div>
                <div style="font-size:9px; color:{C.t3}; line-height:1.6;">{a['message'][:120]}...</div>
                <div style="font-size:8.5px; color:{C.t4}; margin-top:8px; font-weight:700; text-align:right;">{a['created_at']}</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="pg-card" style="padding:15px; background:linear-gradient(to right, #ffffff, {C.pageBg}); text-align:center;">
                <div style="font-size:10px; color:{C.t4};">No active announcements</div>
            </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: CONFIGURATION  (real Gemini generation)
# ═══════════════════════════════════════════════════════════════
# ── Simplified Section Helpers ──
def _sec(title, emoji):
    st.markdown(f'''
    <div class="cfg-section-wrapper">
        <div class="cfg-section-header">
            <span style="font-size:20px;">{emoji}</span>
            <span>{title.upper()}</span>
        </div>
    ''', unsafe_allow_html=True)

def _sec_end():
    st.markdown('</div>', unsafe_allow_html=True)

def _config():
    """Comprehensive 10-section configuration suite."""
    cfg = st.session_state.v5_config
    
    # ── Header ──
    hc1, hc2 = st.columns([1,1])
    with hc1:
        st.markdown(f'<div style="font-size:20px;font-weight:800;color:{C.t1};">Question Paper Factory</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:11px;color:{C.t4}; margin-bottom:20px;">Faculty Dashboard • Academic Year: {cfg["academic_year"]}</div>', unsafe_allow_html=True)
    with hc2:
        st.markdown('<div style="text-align:right; display:flex; gap:10px; justify-content:flex-end;">', unsafe_allow_html=True)
        if st.button("💾 Save Template", use_container_width=False):
            t_id = len(st.session_state.v5_templates) + 1
            st.session_state.v5_templates.append({
                "id": t_id, "name": f"Template {t_id}: {cfg['exam_name']}",
                "desc": f"{cfg['course_name']} - {cfg['exam_type']}", "q": cfg['total_questions'],
                "m": cfg['max_marks'], "diff": cfg['difficulty'], "uses": 0, "cfg": cfg.copy()
            })
            st.success("Template saved!")
        if st.button("✨ Reset", use_container_width=False):
            st.session_state.v5_config = {
                "exam_name": "Mid Term Examination",
                "inst_name": "University of Technology",
                "dept": "CSE",
                "course_name": "Data Structures",
                "course_code": "CS101",
                "academic_year": "2nd Year",
                "semester": "Semester 3",
                "exam_type": "Mid Exam",
                "exam_date": datetime.now().date(),
                "duration": "3 Hours",
                "max_marks": 100,
                "total_questions": 10,
                "num_sections": 3,
                "instructions": "1. Answer all questions.\n2. Figures to the right indicate full marks.",
                "question_types": ["MCQ", "Short Answer"],
                "marks_per_type": {"MCQ": 2, "Short Answer": 5, "Long Answer": 10},
                "counts_per_type": {"MCQ": 5, "Short Answer": 5},
                "difficulty": "Medium",
                "bloom": ["Remember", "Understand"],
                "source_mode": "Manual Topic Entry",
                "topics": [],
                "file_content": None,
                "units": ["Unit 1", "Unit 2", "Unit 3"],
                "unit_dist": {"Unit 1": 3, "Unit 2": 3, "Unit 3": 4},
                "randomize": True,
                "avoid_duplicates": True,
                "include_prev": False,
                "num_sets": 1
            }
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── SECTION 1: Basic Exam Details ──
    _sec("Exam Details", "🏛️")
    r1c1, r1c2 = st.columns(2)
    cfg["exam_name"] = r1c1.text_input("Exam Name", cfg["exam_name"])
    cfg["inst_name"] = r1c2.text_input("Institution Name", cfg["inst_name"])
    
    r2c1, r2c2, r2c3 = st.columns(3)
    dept_list = ["CSE", "IT", "ECE", "Mechanical", "Civil", "AI/ML", "Data Science", "Computer Science"]
    curr_dept = cfg.get("dept", "CSE")
    d_idx = dept_list.index(curr_dept) if curr_dept in dept_list else 0
    cfg["dept"] = r2c1.selectbox("Department / Branch", dept_list, index=d_idx)
    cfg["course_name"] = r2c2.text_input("Course Name", cfg["course_name"])
    cfg["course_code"] = r2c3.text_input("Course Code", cfg["course_code"])
    
    r3c1, r3c2, r3c3 = st.columns(3)
    ay_list = ["1st Year", "2nd Year", "3rd Year", "4th Year"]
    ay_val = cfg.get("academic_year", "2nd Year")
    cfg["academic_year"] = r3c1.selectbox("Academic Year", ay_list, index=ay_list.index(ay_val) if ay_val in ay_list else 1)
    
    sem_list = [f"Semester {i}" for i in range(1,9)]
    sem_val = cfg.get("semester", "Semester 3")
    cfg["semester"] = r3c2.selectbox("Semester", sem_list, index=sem_list.index(sem_val) if sem_val in sem_list else 2)
    
    et_list = ["Internal Exam", "Mid Exam", "Final Exam", "Supplementary"]
    et_val = cfg.get("exam_type", "Mid Exam")
    cfg["exam_type"] = r3c3.selectbox("Exam Type", et_list, index=et_list.index(et_val) if et_val in et_list else 1)
    
    r4c1, r4c2, r4c3 = st.columns(3)
    cfg["exam_date"] = r4c1.date_input("Exam Date", value=cfg.get("exam_date", datetime.now().date()))
    dur_list = ["1 Hour", "2 Hours", "3 Hours", "1.5 Hours", "2.5 Hours"]
    dur_val = cfg.get("duration", "3 Hours")
    cfg["duration"] = r4c2.selectbox("Exam Duration", dur_list, index=dur_list.index(dur_val) if dur_val in dur_list else 2)
    cfg["max_marks"] = r4c3.number_input("Maximum Marks", 1, 100, cfg["max_marks"], key="cfg_max_marks")
    _sec_end()

    # ── SECTION 2: Question Paper Structure ──
    _sec("Question Paper Structure", "📐")
    s1c1, s1c2 = st.columns(2)
    cfg["total_questions"] = s1c1.slider("Total Number of Questions", 1, 50, cfg["total_questions"], key="cfg_total_qs")
    # 🚨 LIMIT: MAX 5 SECTIONS 🚨
    cfg["num_sections"] = s1c2.number_input("Number of Sections (Section A, B, C...)", 1, 5, min(cfg["num_sections"], 5), key="cfg_num_sections", help="Max 5 sections allowed for professional formatting.")
    
    st.markdown('<div class="cfg-sub-label">14. Automatically Generated Sections</div>', unsafe_allow_html=True)
    sec_names = [f"Section {chr(65+i)}" for i in range(cfg["num_sections"])]
    st.write(" , ".join([f"**{n}**" for n in sec_names]))
    
    cfg["instructions"] = st.text_area("15. Instructions for Students", cfg["instructions"], height=100)
    _sec_end()

    # ── SECTION 3: Question Configuration ──
    _sec("Question Configuration", "🧪")
    st.markdown('<div class="cfg-sub-label">16. Question Types</div>', unsafe_allow_html=True)
    cfg["question_types"] = st.multiselect("Select options", 
        ["MCQ", "Fill in the Blanks", "Very Short Answer", "Short Answer", "Long Answer", "Descriptive Questions"],
        default=cfg["question_types"])
    
    st.divider()
    if cfg["question_types"]:
        # Initialize counts if missing
        if "counts_per_type" not in cfg: cfg["counts_per_type"] = {}
        
        st.markdown('<div class="cfg-sub-label">17. Number of Questions per Type</div>', unsafe_allow_html=True)
        q_cols = st.columns(len(cfg["question_types"]))
        for i, qt in enumerate(cfg["question_types"]):
            cfg["counts_per_type"][qt] = q_cols[i].number_input(f"Count: {qt}", 1, 50, cfg["counts_per_type"].get(qt, 5), key=f"cfg_cnt_{qt}")
            
        st.markdown('<div class="cfg-sub-label">18. Marks Allocation per Type</div>', unsafe_allow_html=True)
        m_cols = st.columns(len(cfg["question_types"]))
        for i, qt in enumerate(cfg["question_types"]):
            cfg["marks_per_type"][qt] = m_cols[i].number_input(f"Marks: {qt}", 1, 20, cfg["marks_per_type"].get(qt, 2), key=f"cfg_mks_{qt}")
    else:
        st.caption("Select question types above to allocate counts and marks.")

    st.divider()
    d1, d2 = st.columns(2)
    with d1:
        st.markdown('<div class="cfg-sub-label">18. Difficulty Level Distribution</div>', unsafe_allow_html=True)
        diff_list = ["Mixed Difficulty", "Easy", "Medium", "Hard"]
        diff_val = cfg.get("difficulty", "Mixed Difficulty")
        cfg["difficulty"] = st.selectbox("Distribution Mode", diff_list, index=diff_list.index(diff_val) if diff_val in diff_list else 0)
    with d2:
        st.markdown('<div class="cfg-sub-label">19. Bloom\'s Taxonomy Level</div>', unsafe_allow_html=True)
        cfg["bloom"] = st.multiselect("Cognitive Levels", 
            ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"],
            default=cfg["bloom"])
    _sec_end()

    # ── SECTION 4 & 5: Content Source & Selection ──
    _sec("Content Source & Units", "📚")
    
    source_r = st.radio("Choose Generation Mode", ["Manual Topic Entry", "File Upload"], horizontal=True)
    cfg["source_mode"] = source_r # Sync to state
    
    is_file = (source_r == "File Upload")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown('<div class="cfg-sub-label">20. Manual Topics / Syllabus (comma separated)</div>', unsafe_allow_html=True)
        # 🚨 MANUAL TOPIC ENTRY 🚨
        topics_str = ", ".join(cfg["topics"]) if isinstance(cfg["topics"], list) else cfg["topics"]
        new_topics = st.text_area("Enter topics to cover", 
                                 value=topics_str,
                                 placeholder="e.g. Linked Lists, Stacks, Queues",
                                 height=100,
                                 disabled=is_file)
        cfg["topics"] = [t.strip() for t in new_topics.split(",") if t.strip()]
        if is_file:
            st.warning("Manual topics disabled (File Upload active). Questions will be generated based only on the uploaded file.")
    
    with col_s2:
        st.markdown('<div class="cfg-sub-label">21. Upload Reference File</div>', unsafe_allow_html=True)
        up_file = st.file_uploader("Support: PDF, DOCX, TXT", type=["pdf", "docx", "txt"])
        if up_file:
            # 🚨 ROBUST FILE EXTRACTION 🚨
            from modules.pdf_extractor import extract_text_auto
            try:
                # Use .getvalue() instead of .read() to avoid consuming the stream
                file_bytes = up_file.getvalue()
                extracted_text = extract_text_auto(file_bytes, up_file.name)
                if extracted_text:
                    cfg["file_content"] = extracted_text
                    cfg["file_name"] = up_file.name
                    st.success(f"File '{up_file.name}' parsed successfully! ({len(extracted_text)} chars)")
                else:
                    st.error("Could not extract any text from the file.")
            except Exception as e:
                st.error(f"Error reading file: {e}")
    _sec_end()

    # ── SECTION 5: Advanced AI & Multiple Sets ──
    _sec("Advanced AI & Multi-Set", "🤖")
    a1, a2, a3 = st.columns(3)
    cfg["randomize"] = a1.toggle("22. Question Randomization", value=cfg["randomize"], key="cfg_randomize")
    cfg["avoid_duplicates"] = a2.toggle("23. Avoid Duplicate Questions", value=cfg["avoid_duplicates"], key="cfg_duplicates")
    cfg["include_prev"] = a3.toggle("24. Include Previous Year Questions", value=cfg["include_prev"], key="cfg_prev_yr")
    
    st.divider()
    st.markdown('<div class="cfg-sub-label">25. Number of Question Paper Sets</div>', unsafe_allow_html=True)
    # 🚨 LIMIT: MAX 5 SETS 🚨
    cfg["num_sets"] = st.number_input("How many sets? (Set A, B, C...)", 1, 5, min(cfg["num_sets"], 5), key="cfg_num_sets", help="Max 5 sets possible for unique generation.")
    if cfg["num_sets"] > 1:
        st.info(f"System will generate {cfg['num_sets']} different sets with consistent structure.")
    _sec_end()

    # ── SECTION 8: Generation ──
    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    g1, g2 = st.columns(2)
    if g1.button("👁️ Preview Question Paper Parameters", use_container_width=True):
        st.json(cfg)
    if g2.button("🚀 Generate Question Paper(s)", use_container_width=True, type="primary"):
        _run_generation(cfg)

def _run_generation(cfg):
    """Execution logic for multi-set generation with uniqueness."""
    api_key = _get_key()
    if not api_key:
        st.error("API Key missing! Please check your settings.")
        return

    from modules.question_generator import QuestionGenerator
    gen = QuestionGenerator(api_key)
    
    # Track generated question text to ensure NO overlap across sets
    history_for_uniqueness = "" 
    
    progress_bar = st.progress(0)
    status_msg = st.empty()
    
    for i in range(cfg.get("num_sets", 1)):
        label = chr(65 + i)
        num_sets = max(1, cfg.get("num_sets", 1))
        progress = (i) / num_sets
        progress_bar.progress(progress)
        status_msg.markdown(f"**⚡ Generating Set {label}...** (Internal processing)")
        
        try:
            # Build prompt using global history if avoid_duplicates is ON
            prev_qs = history_for_uniqueness if cfg.get("avoid_duplicates") else ""
            
            # 🚨 UI CONFIRMATION OF FILE MODE 🚨
            if cfg.get("source_mode") == "File Upload" and cfg.get("file_content"):
                status_msg.info(f"📁 Set {label}: Generating from uploaded file ({len(cfg['file_content'])} chars)")
            
            prompt = gen.build_academic_prompt(cfg, label, prev_qs=prev_qs)
            raw_response = gen.generate_batch(prompt)
            
            if raw_response:
                qs = gen.parse_academic_batch(raw_response, cfg)
                if qs:
                    paper = {
                        "id": f"P-{int(time.time())}-{label}",
                        "name": cfg.get("exam_name", "Paper") + f" - Set {label}",
                        "set": label,
                        "title": cfg.get("exam_name", "Paper"),
                        "mks": sum(q["marks"] for q in qs),
                        "qCnt": len(qs),
                        "date": str(cfg["exam_date"]),
                        "questions": qs,
                        "cfg": cfg.copy(),
                        "inst_name": cfg["inst_name"],
                        "course_name": cfg["course_name"],
                        "course_code": cfg["course_code"],
                        "department": cfg["dept"],
                        "semester": cfg["semester"],
                        "created_at": datetime.now().strftime("%I:%M %p, %B %d")
                    }
                    from modules.database import save_paper
                    user_email = st.session_state.get("user_data", {}).get("email", "")
                    if user_email:
                        paper["db_id"] = save_paper(user_email, paper)
                        add_audit_log(user_email, "Paper Generated", f"Generated Set {label} for {cfg.get('exam_name')}")
                        
                    st.session_state.v5_papers.append(paper)
                    # Add current set text to history for next set exclusion
                    history_for_uniqueness += "\n" + raw_response
                else:
                    st.error(f"Set {label}: Parsing failed. Check AI response.")
            else:
                st.error(f"Set {label}: Empty response from AI.")
        except Exception as e:
            st.error(f"Critical error in Set {label}: {str(e)}")

    progress_bar.progress(1.0)
    status_msg.success(f"Successfully generated {cfg['num_sets']} question paper sets!")
    time.sleep(1)
    st.session_state.v5_page = "papers"
    st.rerun()

def _papers():
    """Display generated papers with Section 9 Download Options."""
    papers = st.session_state.get("v5_papers", [])
    if not papers:
        st.warning("No papers available. Use the configuration panel to generate sets.")
        if st.button("Go to Configuration"):
            st.session_state.v5_page = "configuration"
            st.rerun()
        return

    st.markdown(f'<div style="font-size:16px; font-weight:700; color:{C.t1}; margin-bottom:15px;">Generated Exam Papers repository</div>', unsafe_allow_html=True)
    
    for p in papers:
        # Normalize for Export Handler
        p_norm = _normalize_paper(p)
        
        # Move timestamp to top level for better visibility
        created_at = p.get('created_at', p.get('date', 'Unknown Time'))
        expander_label = f"📄 {p['name']} | 🕒 {created_at} | {p['qCnt']} Qs — {p['mks']} Marks"
        
        # Auto-expand logic if jumping from notification
        is_jump = st.session_state.get("jump_to_paper") == p['id']
        if is_jump:
            expanded_state = True
            # We don't clear it here yet to ensure it persists for the actual render
        else:
            expanded_state = False

        with st.expander(expander_label, expanded=expanded_state):
            if is_jump:
                # Clear it inside so it only happens once
                st.session_state.jump_to_paper = None
            # --- APPROVAL WORKFLOW STATUS ---
            status = p.get("approval_status", "Pending")
            comments = p.get("admin_comments", "")
            
            # ALLOW downloads for Drafts (Pending) and Approved papers
            is_downloadable = (status == "Pending" or status == "Approved")
            
            st_colors = {
                "Pending": ("#F1F5F9", "#475569", "#E2E8F0"), # Neutral color for DRAFT
                "Submitted": ("#FEF3C7", "#92400E", "#FDE68A"),
                "Approved": ("#D1FAE5", "#065F46", "#A7F3D0"),
                "Changes Requested": ("#FFedd5", "#9a3412", "#fed7aa")
            }
            bg, fg, bd = st_colors.get(status, st_colors["Pending"])
            p_status_lbl = "DRAFT" if status == "Pending" else status.upper()
            
            st.markdown(f"""
            <div style="background:{bg}; color:{fg}; border:1px solid {bd}; padding:4px 12px; 
                        border-radius:6px; font-size:11px; font-weight:800; display:inline-block; margin-bottom:12px;">
                STATUS: {p_status_lbl}
            </div>""", unsafe_allow_html=True)
            
            if comments:
                st.info(f"💬 **Admin Feedback:** {comments}")
            
            # Show warning ONLY if it's actually with the admin (Submitted or Changes Requested)
            if status in ["Submitted", "Changes Requested"]:
                st.warning("⚠️ This paper is awaiting admin approval. Downloads are disabled until it is approved.")

            st.markdown(f"""
            <div style="margin-bottom:12px; padding: 4px 2px;">
                <div style="font-size:12.5px; color:{C.t1}; margin-bottom: 2px;"><b>{p.get('inst_name','')}</b></div>
                <div style="font-size:11.5px; color:{C.t3}; opacity: 0.8;">{p.get('course_name','')} ({p.get('course_code','')}) • {p.get('department','')}</div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
            with c1:
                if st.button(f"👁️ Preview Set {p['set']}", key=f"prev_set_{p['id']}", use_container_width=True):
                    st.session_state.preview_paper_id = p['id']
                    st.session_state.v5_page = "preview"
                    st.rerun()
            
            # SECTION 9: DOWNLOAD OPTIONS (Restricted)
            with c2:
                try:
                    pdf_path = ExportHandler.export_to_pdf(p_norm, f"Set_{p['set']}_{p['id']}.pdf")
                    with open(pdf_path, "rb") as f:
                        st.download_button(f"📕 PDF (Set {p['set']})", f, file_name=f"Set_{p['set']}.pdf", 
                                          key=f"pdf_{p['id']}", use_container_width=True, 
                                          on_click=_track_dl, args=("PDF", p['name'], p.get('db_id')),
                                          disabled=not is_downloadable)
                except:
                    st.button("PDF Error", disabled=True, key=f"pe_{p['id']}")
                
            with c3:
                try:
                    docx_path = ExportHandler.export_to_docx(p_norm, f"Set_{p['set']}_{p['id']}.docx")
                    with open(docx_path, "rb") as f:
                        st.download_button(f"📘 DOCX (Set {p['set']})", f, file_name=f"Set_{p['set']}.docx", 
                                          key=f"doc_{p['id']}", use_container_width=True, 
                                          on_click=_track_dl, args=("DOCX", p['name'], p.get('db_id')),
                                          disabled=not is_downloadable)
                except:
                    st.button("DOCX Error", disabled=True, key=f"de_{p['id']}")
 
            with c4:
                txt_data = ExportHandler._to_txt(p_norm)
                st.download_button(f"📄 TXT (Set {p['set']})", txt_data, file_name=f"Set_{p['set']}.txt", 
                                  key=f"txt_{p['id']}", use_container_width=True, 
                                  on_click=_track_dl, args=("TXT", p['name'], p.get('db_id')),
                                  disabled=not is_downloadable)

            # --- SUBMISSION AND DELETE ACTIONS ---
            st.markdown("<hr style='margin:15px 0; opacity:0.3;'>", unsafe_allow_html=True)
            act_col1, act_col2 = st.columns([1, 1])
            
            with act_col1:
                if status in ["Pending", "Changes Requested"]:
                    if st.button(f"📤 Send to Admin (Set {p['set']})", key=f"send_adm_{p['id']}", use_container_width=True):
                        st.session_state[f"show_sub_{p['id']}"] = True
                    
                    if st.session_state.get(f"show_sub_{p['id']}"):
                        with st.form(key=f"form_sub_{p['id']}"):
                            fmt = st.selectbox("Preferred Format for Review", ["PDF", "DOCX", "TXT"], key=f"fmt_sub_{p['id']}")
                            if st.form_submit_button("Confirm Submission", use_container_width=True):
                                if "db_id" in p:
                                    from modules.database import submit_paper, add_notification
                                    submit_paper(p["db_id"], fmt)
                                    # Notify Admin
                                    username = st.session_state.get("user_data", {}).get("name", "A Faculty Member")
                                    admin_msg = f"🔔 **{username}** has sent a paper (**{p['name']}**) for review in **{fmt}** format."
                                    add_notification("admin@gmail.com", admin_msg, p["db_id"])
                                    add_audit_log(st.session_state.get("user_data", {}).get("email", ""), "Paper Submitted", f"Submitted {p['name']} in {fmt}")
                                    st.success("Paper submitted to Admin successfully!")
                                    del st.session_state[f"show_sub_{p['id']}"]
                                    time.sleep(1)
                                    st.rerun()
                else:
                    st.button("✅ Already Submitted", disabled=True, use_container_width=True, key=f"sent_dis_{p['id']}")

            with act_col2:
                if st.button(f"🗑️ Delete (Set {p['set']})", key=f"del_{p['id']}", type="primary", use_container_width=True):
                    if "db_id" in p:
                        user_email = st.session_state.get("user_data", {}).get("email", "")
                        from modules.database import delete_paper
                        delete_paper(p["db_id"], user_email)
                        add_audit_log(user_email, "Paper Deleted", f"Deleted {p['name']}")
                    if p in st.session_state.v5_papers:
                        st.session_state.v5_papers.remove(p)
                    st.rerun()


# ═══════════════════════════════════════════════════════════════
# PAGE: EXAM PREVIEW
# ═══════════════════════════════════════════════════════════════
def _preview():
    st.markdown(f'<div style="font-size:15px;font-weight:800;color:{C.t1};margin-bottom:16px;">Print-Ready Exam Preview</div>', unsafe_allow_html=True)
    if not st.session_state.v5_papers:
        st.info("Generate a paper first.")
        return

    papers_list = st.session_state.get("v5_papers", [])
    pid = st.session_state.get("preview_paper_id")
    if pid:
        p = next((x for x in papers_list if x["id"] == pid),
                 papers_list[-1] if papers_list else {})
    else:
        p = papers_list[-1] if papers_list else {}

    cfg = p.get('cfg', {})
    raw_instr = cfg.get('instructions', '1. Answer all questions.\n2. Figures to the right indicate full marks.')
    formatted_instr = raw_instr.replace('\n', '<br/>')
    
    # ── SORT BY TYPE PRIORITY & RESET NUMBERING ──
    type_priority = {"MCQ": 0, "Fill in the Blanks": 1, "Short Answer": 2, "Long Answer": 3}
    sorted_qs = sorted(p["questions"], key=lambda x: type_priority.get(x.get("type"), 4))
    
    # ── Aggressive Cleaner Instance ──
    from modules.question_generator import QuestionGenerator
    cleaner = QuestionGenerator()

    # ── Professional Header ──
    paper_html = f"""<div style="background:white; padding:60px 80px; border:1px solid #eee; max-width:900px; margin:0 auto; color:black; box-shadow:0 0 40px rgba(0,0,0,0.05); border-radius:3px; font-family: 'Times New Roman', Times, serif; position: relative; line-height: 1.6;">
<center>
    <h1 style="margin:0 0 10px 0; text-transform:uppercase; font-size: 28px; font-weight: 900; letter-spacing: 1.5px; color:#000;">{cfg.get('exam_name', 'Examination')}</h1>
    <div style="margin:5px 0; font-size:18px; font-weight:600;">Course: {cfg.get('course_name', '')} ({cfg.get('course_code', '')})</div>
    <div style="font-size:15px; margin:10px 0 20px 0; color:#444; font-weight:500;">Set: <b>{p.get('set', 'A')}</b> &nbsp; | &nbsp; Time: <b>{cfg.get('duration', '3 Hours')}</b> &nbsp; | &nbsp; Max Marks: <b>{p.get('mks', 100)}</b> &nbsp; | &nbsp; Date: <b>{datetime.now().strftime('%d-%m-%Y')}</b></div>
</center>

<div style="margin-top: 20px; font-size: 14px; font-weight: 700;">
    <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
        <div style="width: 48%;">Name: __________________________</div>
        <div style="width: 48%;">Roll No: _______________________</div>
    </div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 25px;">
        <div style="width: 48%;">Student Signature: ______________</div>
        <div style="width: 48%;">Teacher Signature: ______________</div>
    </div>
</div>

<div style="width:100%; border-top:2px solid #000; margin-bottom:20px;"></div>
<div style="margin-bottom: 25px; border: 1px solid #111; padding: 15px; font-size: 14px; background: #fdfdfd;">
    <div style="font-weight: 900; text-transform: uppercase; margin-bottom: 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px;">General Instructions:</div>
    <div style="line-height: 1.5;">{formatted_instr}</div>
</div>
<div style="width:100%; border-top:1px solid #000; margin-bottom:40px;"></div>"""

    # ── Render Questions with Sections ──
    sections = ["A", "B", "C", "D", "E"]
    current_type = None
    type_idx = 0
    q_count = 0

    for q in sorted_qs:
        # Add Section Header (Left Aligned, Simple)
        if q.get("type") != current_type:
            current_type = q.get("type")
            sec_letter = sections[type_idx] if type_idx < len(sections) else chr(65 + type_idx)
            header_text = f"SECTION {sec_letter}: {current_type.upper()}S"
            if "MCQ" in current_type.upper(): header_text = f"SECTION {sec_letter}: MCQs"
            
            paper_html += f'<div style="text-align:left; font-weight:900; margin: 55px 0 25px; font-size: 18px; text-transform:uppercase; letter-spacing:0.5px; border-bottom: 2px solid #000; padding-bottom: 5px; width: fit-content; display: inline-block;">{header_text}</div>'
            type_idx += 1

        q_count += 1
        q_clean = cleaner.clean_metadata(q['q'])
        
        # Flex container with a reserved right zone for marks to avoid overlap
        paper_html += f"""<div style="display: flex; margin-bottom: 40px; font-size: 16px; align-items: flex-start; justify-content: space-between;">
    <div style="display: flex; flex: 1;">
        <div style="width: 40px; font-weight: 900;">{q_count}.</div>
        <div style="flex: 1; padding-right: 20px; line-height: 1.6;">
            {q_clean}"""

        if q.get("type") == "MCQ" and q.get("options"):
            opts = q["options"]
            if isinstance(opts, list):
                opts = opts[:4]
                opt_str = ""
                prefixes = ["a)", "b)", "c)", "d)"]
                for i, opt in enumerate(opts):
                    opt_str += f"<div style='width: 100%; display: block; margin-top: 12px; padding-left: 20px; color: #333;'>{prefixes[i]} {opt}</div> "
                paper_html += f"<div style='margin-top: 5px; font-size: 15.5px;'>{opt_str}</div>"
            else:
                paper_html += f"<div style='margin-top: 12px; font-size: 15px; font-style: italic;'>{opts}</div>"
        
        paper_html += f"""</div>
    </div>
    <div style="width: 100px; text-align: right; font-weight: 900; color:#000; padding-top: 2px;">[{q["marks"]} Marks]</div>
</div>"""
            
    paper_html += """<div style="margin-top: 80px; border-top: 1px solid #000; padding-top: 25px; text-align: center; font-variant: small-caps; letter-spacing: 4px; font-weight: 900; color:#000; font-size: 14px;">
*** END OF QUESTION PAPER ***
</div>
</div>"""
    st.markdown(paper_html, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# PAGE: FACULTY ALERTS
# ═══════════════════════════════════════════════════════════════
def _faculty_alerts():
    user_email = st.session_state.get("user_data", {}).get("email", "")
    from modules.database import get_notifications, mark_notification_read
    notifs = get_notifications(user_email)
    
    st.markdown(f"""
    <div style="background:white; border-radius:12px; border:1px solid {C.sbBd}; padding:18px; margin-bottom:20px; box-shadow:{C.cardSh};">
        <h3 style="margin:0; color:{C.t1}; font-size:16px; font-weight:700;">🔔 Faculty Alerts & Notifications</h3>
        <p style="font-size:12px; color:{C.t3}; margin-top:4px;">Stay updated on your paper statuses and system announcements.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if not notifs:
        st.info("You have no notifications yet.")
        return

    # Tabs for Unread/All
    unread = [n for n in notifs if not n["is_read"]]
    t1, t2 = st.tabs([f"New Alerts ({len(unread)})", "Read Notifications"])
    
    with t1:
        if not unread:
            st.markdown(f'<div style="text-align:center; padding:40px; color:{C.t4};">No new alerts.</div>', unsafe_allow_html=True)
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
                    if st.button("👁️", key=f"clr_page_{n['id']}", help="View Paper & Mark as Read"):
                        mark_notification_read(n["id"])
                        if n.get("paper_id"):
                            st.session_state.v5_page = "papers"
                            st.session_state.jump_to_paper = n["paper_id"]
                        st.rerun()

    with t2:
        read_notifs = [n for n in notifs if n["is_read"]]
        if not read_notifs:
            st.markdown(f'<div style="text-align:center; padding:40px; color:{C.t4};">No read notifications.</div>', unsafe_allow_html=True)
        else:
            for n in read_notifs:
                st.markdown(f"""
                <div style="padding:12px 16px; background:white; border:1px solid #f0f0f0; border-radius:8px; margin-bottom:10px; opacity:0.75;">
                    <div style="font-size:13px; color:{C.t2};">{n['message']}</div>
                    <div style="font-size:10px; color:{C.t4}; margin-top:4px;">{n['time']}</div>
                </div>
                """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: ANSWER KEYS
# ═══════════════════════════════════════════════════════════════
def _answers():
    st.markdown(f'<div style="font-size:15px;font-weight:800;color:{C.t1};margin-bottom:16px;">Model Answer Keys</div>', unsafe_allow_html=True)
    if not st.session_state.v5_papers:
        st.info("🔑 Generate papers first.")
        return
    for p in st.session_state.v5_papers:
        # Move timestamp and metadata to expander label for consistency
        created_at = p.get('created_at', p.get('date', 'Unknown Time'))
        expander_label = f"🔑 {p['name']} | 🕒 {created_at} | Set {p['set']}"
        
        with st.expander(expander_label):
            cfg = p.get('cfg', {})
            # Professional Header inside Answer Key
            st.markdown(f"""
            <div style="background:white; padding:15px; border:1px solid {C.sbBd}; border-radius:8px; margin-bottom:15px; border-left:5px solid {C.sky};">
                <div style="font-size:10px; font-weight:700; color:{C.t4}; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">Official Answer Key</div>
                <div style="font-size:14px; font-weight:800; color:{C.t1};">{cfg.get('exam_name', 'Examination')}</div>
                <div style="font-size:12px; color:{C.t3}; margin-top:2px;">
                    {cfg.get('course_name', '')} ({cfg.get('course_code', '')}) &nbsp;|&nbsp; 
                    Set: <b>{p.get('set', 'A')}</b> &nbsp;|&nbsp; 
                    Generated: <b>{created_at}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

            for q in p["questions"]:
                st.markdown(f"""
                <div style="background:{C.pageBg};border-radius:10px;padding:12px;
                            border:1px solid {C.sbBd};border-left:4px solid {C.sky};margin-bottom:8px;">
                  <div style="font-size:8.5px;font-weight:800;color:{C.sky};margin-bottom:4px;">Q{q['no']} · REFERENCE SOLUTION</div>
                  <div style="font-size:12px;color:{C.t2};line-height:1.6;">{q['a']}</div>
                </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: MARKS SCHEME
# ═══════════════════════════════════════════════════════════════
def _markscheme():
    st.markdown(f'<div style="font-size:15px;font-weight:800;color:{C.t1};margin-bottom:16px;">Marks Allocation Scheme</div>', unsafe_allow_html=True)
    if not st.session_state.v5_papers:
        st.info("Generate papers first.")
        return
    
    # ── SINGLE PAPER FILTERING logic (same as preview) ──
    papers_list = st.session_state.get("v5_papers", [])
    pid = st.session_state.get("preview_paper_id")
    if pid:
        p = next((x for x in papers_list if x["id"] == pid),
                 papers_list[-1] if papers_list else {})
    else:
        p = papers_list[-1] if papers_list else {}

    if p:
        html = f"""
        <div class="pg-card" style="padding: 20px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:18px; border-bottom: 2px solid {C.sbLine}; padding-bottom: 12px;">
            <div style="font-size:14px; font-weight:800; color:{C.t1};">{p['name']}</div>
            <div style="font-size:12px; font-weight:800; color:{C.violet}; letter-spacing: 0.5px;">TOTAL SCORE: {p['mks']} MARKS</div>
          </div>
          <table style="width:100%; border-collapse:collapse; font-size:12px; table-layout: fixed;">
            <thead>
              <tr style="background: {C.pageBg}; text-align:left;">
                <th style="padding:12px 8px; color:{C.t3}; width: 50px; border-radius: 8px 0 0 8px;">Q</th>
                <th style="padding:12px 8px; color:{C.t3};">Question Prompt</th>
                <th style="padding:12px 8px; color:{C.t3}; width: 120px;">Type [Section]</th>
                <th style="padding:12px 8px; color:{C.t3}; width: 80px; text-align: center; border-radius: 0 8px 8px 0;">Marks</th>
              </tr>
            </thead>
            <tbody>"""
            
        # ── SORT BY MARKS ──
        sorted_qs = sorted(p["questions"], key=lambda x: x.get("marks", 0))

        for q in sorted_qs:
            q_text = q['q'][:80] + "..." if len(q['q']) > 80 else q['q']
            html += f"""
              <tr style="border-bottom:1px solid {C.sbLine};">
                <td style="padding:14px 8px; font-weight:700; color:{C.t1};">{q['no']}</td>
                <td style="padding:14px 8px; color:{C.t2}; line-height: 1.4;">{q_text}</td>
                <td style="padding:14px 8px;">
                  <span style="background:{C.sbBd}; color:{C.violet}; padding:4px 8px; border-radius:6px; font-size:10px; font-weight:600;">{q['type']}</span>
                </td>
                <td style="padding:14px 8px; font-weight:800; color:{C.pink}; text-align: center; font-size: 14px;">{q['marks']}</td>
              </tr>"""
        html += "</tbody></table></div>"
        st.markdown(html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: QUESTION BANK
# ═══════════════════════════════════════════════════════════════
def _qbank():
    st.markdown(f'<div style="font-size:15px;font-weight:800;color:{C.t1};margin-bottom:16px;">Question Bank</div>', unsafe_allow_html=True)
    all_qs = [q for p in st.session_state.v5_papers for q in p["questions"]]
    if not all_qs:
        st.info("🗂️ No questions yet. Generate papers first.")
        return
    st.markdown(f'<div style="font-size:11.5px;color:{C.t3};margin-bottom:12px;">Total: <strong>{len(all_qs)}</strong> questions</div>',
                unsafe_allow_html=True)
    for q in all_qs[:25]:
        st.markdown(f"""
        <div class="pg-card" style="padding:10px;">
          <div style="font-size:11px;font-weight:700;color:{C.t1};margin-bottom:4px;">Q{q['no']}. {q['q']}</div>
          <div style="display:flex;gap:5px;flex-wrap:wrap;">
            <span style="background:{C.pageBg};color:{C.violet};padding:2px 6px;border-radius:7px;font-size:9px;font-weight:600;">{q['type']}</span>
            <span style="background:{C.pageBg};color:{C.t3};padding:2px 6px;border-radius:7px;font-size:9px;">{q['difficulty']}</span>
            <span style="background:{C.pageBg};color:{C.t3};padding:2px 6px;border-radius:7px;font-size:9px;">{q['marks']} marks</span>
          </div>
        </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: TEMPLATES
# ═══════════════════════════════════════════════════════════════
def _templates():
    st.markdown(f'<div style="font-size:15px;font-weight:800;color:{C.t1};margin-bottom:16px;">Saved Exam Templates & Patterns</div>', unsafe_allow_html=True)
    
    templates = st.session_state.get("v5_templates", SEED_TEMPLATES)
    if not templates:
        st.info("No templates saved yet.")
        return

    cols = st.columns(2)
    grads = [C.gPink, C.gSkyBlue, C.gViolet, C.gOrange]
    
    for i, t in enumerate(templates):
        with cols[i % 2]:
            st.markdown(f"""
            <div class="pg-card">
              <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                <div style="width:36px;height:36px;background:{grads[i%4]};border-radius:9px;
                            display:flex;align-items:center;justify-content:center;font-size:16px;">📐</div>
                <span style="background:{C.pageBg};color:{C.t3};padding:2px 7px;border-radius:7px;
                             font-size:8.5px;font-weight:700;border:1px solid {C.sbBd};
                             height:fit-content;">{t.get('uses',0)} uses</span>
              </div>
              <div style="font-size:12px;font-weight:800;color:{C.t1};margin-bottom:2px;">{t['name']}</div>
              <div style="font-size:9.5px;color:{C.t4};margin-bottom:10px;line-height:1.5;">{t['desc']}</div>
              <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-bottom:10px;">
                <div style="text-align:center;">
                  <div style="font-size:12.5px;font-weight:800;">{t['q']}</div>
                  <div style="font-size:7.5px;color:{C.t4};">Questions</div>
                </div>
                <div style="text-align:center;">
                  <div style="font-size:12.5px;font-weight:800;">{t['m']}</div>
                  <div style="font-size:7.5px;color:{C.t4};">Marks</div>
                </div>
                <div style="text-align:center;">
                  <div style="font-size:9px;font-weight:800;color:{C.sky};">{t['diff']}</div>
                  <div style="font-size:7.5px;color:{C.t4};">Mode</div>
                </div>
              </div>""", unsafe_allow_html=True)
            
            if st.button(f"Apply Blueprint {t['id']}", key=f"tpl_apply_{t['id']}", use_container_width=True):
                # If template has a stored cfg, use it
                if "cfg" in t:
                    st.session_state.v5_config = t["cfg"].copy()
                else:
                    st.session_state.v5_config["total_questions"] = t["q"]
                    st.session_state.v5_config["max_marks"] = t["m"]
                    st.session_state.v5_config["difficulty"] = t["diff"]
                
                st.success(f"'{t['name']}' applied successfully!")
                time.sleep(0.5)
                st.session_state.v5_page = "configuration"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: STATISTICS
# ═══════════════════════════════════════════════════════════════
def _statistics():
    st.markdown(f'<div style="font-size:15px;font-weight:800;color:{C.t1};margin-bottom:20px;">Premium Analytics Dashboard</div>', unsafe_allow_html=True)
    
    papers = st.session_state.get("v5_papers", [])
    if not papers:
        st.info("📊 Generate papers to see advanced analytics.")
        return

    # 1. Advanced Data Processing
    total_q = 0
    total_m = 0
    type_counts = {"MCQ": 0, "Short Answer": 0, "Long Answer": 0, "Other": 0}
    diff_counts = {"Easy": 0, "Medium": 0, "Hard": 0}
    bloom_counts = {"Remember": 0, "Understand": 0, "Apply": 0, "Analyze": 0, "Evaluate": 0, "Create": 0}
    
    for p in papers:
        total_q += p.get("qCnt", 0)
        total_m += p.get("mks", 0)
        for q in p.get("questions", []):
            # Aggregating types
            qt = q.get("type", "Other")
            if qt in type_counts: type_counts[qt] += 1
            else: type_counts["Other"] += 1
            
            # Aggregating difficulty
            df = q.get("difficulty", "Medium")
            if df in diff_counts: diff_counts[df] += 1

            # Aggregating Bloom's
            bl = q.get("bloom", "Understand")
            if bl in bloom_counts: bloom_counts[bl] += 1
            elif any(b in bl for b in bloom_counts):
                for b in bloom_counts:
                    if b in bl: 
                        bloom_counts[b] += 1
                        break

    # 2. Premium Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    
    def _metric_card(col, label, val, icon, grad):
        col.markdown(f"""
        <div style="background:{grad}; padding:20px; border-radius:15px; color:white; 
                    box-shadow:0 4px 15px rgba(0,0,0,0.05); height:120px; 
                    display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
            <div style="font-size:24px; margin-bottom:5px;">{icon}</div>
            <div style="font-size:24px; font-weight:800; line-height:1;">{val}</div>
            <div style="font-size:10px; font-weight:700; text-transform:uppercase; margin-top:4px; opacity:0.8; letter-spacing:0.5px;">{label}</div>
        </div>
        """, unsafe_allow_html=True)

    _metric_card(m1, "Total Papers", len(papers), "📄", C.gPink)
    _metric_card(m2, "Total Questions", total_q, "❓", C.gViolet)
    _metric_card(m3, "Total Marks", total_m, "🏆", C.gSkyBlue)
    _metric_card(m4, "Avg Q / Paper", round(total_q/len(papers), 1), "📈", C.gOrange)

    st.markdown('<div style="height:30px;"></div>', unsafe_allow_html=True)

    # 3. Visual Distributions (Custom CSS Bars)
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f'<div style="font-size:12px; font-weight:700; color:{C.t2}; margin-bottom:15px;">Question Types</div>', unsafe_allow_html=True)
        for t, count in type_counts.items():
            if count == 0 and t == "Other": continue
            pct = (count / total_q) * 100 if total_q > 0 else 0
            st.markdown(f"""
            <div style="margin-bottom:10px;">
                <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:600; color:{C.t3}; margin-bottom:3px;">
                    <span>{t}</span>
                    <span>{count}</span>
                </div>
                <div style="background:#F0EBF8; height:6px; border-radius:3px; overflow:hidden;">
                    <div style="background:{C.violet}; width:{pct}%; height:100%; border-radius:3px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with c2:
        st.markdown(f'<div style="font-size:12px; font-weight:700; color:{C.t2}; margin-bottom:15px;">Difficulty</div>', unsafe_allow_html=True)
        colors = {"Easy": "#2DC653", "Medium": "#F8961E", "Hard": "#F72585"}
        for d, count in diff_counts.items():
            pct = (count / total_q) * 100 if total_q > 0 else 0
            st.markdown(f"""
            <div style="margin-bottom:10px;">
                <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:600; color:{C.t3}; margin-bottom:3px;">
                    <span>{d}</span>
                    <span>{count}</span>
                </div>
                <div style="background:#F0EBF8; height:6px; border-radius:3px; overflow:hidden;">
                    <div style="background:{colors.get(d, C.violet)}; width:{pct}%; height:100%; border-radius:3px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with c3:
        st.markdown(f'<div style="font-size:12px; font-weight:700; color:{C.t2}; margin-bottom:15px;">Bloom\'s Taxonomy</div>', unsafe_allow_html=True)
        for b, count in bloom_counts.items():
            if count == 0: continue
            pct = (count / total_q) * 100 if total_q > 0 else 0
            st.markdown(f"""
            <div style="margin-bottom:10px;">
                <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:600; color:{C.t3}; margin-bottom:3px;">
                    <span>{b}</span>
                    <span>{count}</span>
                </div>
                <div style="background:#F0EBF8; height:6px; border-radius:3px; overflow:hidden;">
                    <div style="background:{C.sky}; width:{pct}%; height:100%; border-radius:3px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # 4. Recent Activity Timeline
    st.markdown('<div style="height:30px;"></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:13px; font-weight:700; color:{C.t2}; margin-bottom:15px;">Recent Generation Activity</div>', unsafe_allow_html=True)
    
    for idx, p in enumerate(papers[:5]):
        bg = "#ffffff" if idx % 2 == 0 else "#FBF9FE"
        with st.container():
            st.markdown(f"""
            <div style="background:{bg}; border:1px solid #EDE8F5; border-radius:10px; padding:12px 18px; 
                        margin-bottom:0px; display:flex; justify-content:space-between; align-items:center;">
                <div style="flex:1;">
                    <div style="font-size:12px; font-weight:700; color:{C.t1};">{p['name']}</div>
                    <div style="font-size:10px; color:{C.t4};">{p.get('created_at','')}</div>
                </div>
                <div style="display:flex; gap:15px; font-size:11px; font-weight:600; color:{C.t3}; align-items:center;">
                    <span>{p['qCnt']} Qs</span>
                    <span>{p['mks']} Marks</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            # Functional Button layer
            bc1, bc2 = st.columns([5,1])
            with bc2:
                if st.button("👁️ View", key=f"stat_view_{p['id']}", use_container_width=True):
                    st.session_state.preview_paper_id = p['id']
                    st.session_state.v5_page = "preview"
                    st.rerun()
            st.markdown('<div style="margin-bottom:8px;"></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: DOWNLOADS
# ═══════════════════════════════════════════════════════════════
def _downloads():
    st.markdown(f'<div style="font-size:15px;font-weight:800;color:{C.t1};margin-bottom:16px;">Downloads</div>', unsafe_allow_html=True)
    if not st.session_state.v5_papers:
        st.info("📥 No papers to download yet.")
        return
    for p in st.session_state.v5_papers:
        st.markdown(
            f'<div class="pg-card" style="padding:12px;"><b>{p["title"]} — {p["name"]}</b>'
            f' <span style="color:{C.t4};font-size:9.5px;">({p["date"]})</span></div>',
            unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: ANNOUNCEMENTS
# ═══════════════════════════════════════════════════════════════
def _announcements():
    st.markdown(f'<div style="font-size:15px;font-weight:800;color:{C.t1};margin-bottom:16px;">System Announcements</div>', unsafe_allow_html=True)
    ts = {
        "warning": ("#FFF8EC","#F8D89F","⚠️"),
        "info":    ("#EFF6FF","#BFDBFE","ℹ️"),
        "success": ("#EDFAF4","#B2EAD8","✅"),
    }
    anns = get_announcements()
    if not anns:
        st.info("No active announcements from administration.")
        return
        
    for a in anns:
        bg, bd, ico = ts.get(a["type"], (C.pageBg, C.sbBd, "📢"))
        st.markdown(f"""
        <div style="background:{bg};border:1px solid {bd};border-radius:10px;padding:13px;margin-bottom:9px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
            <div style="font-size:11.5px;font-weight:800;color:{C.t1};">{ico} {a['title']}</div>
            <div style="font-size:8.5px;color:{C.t4};">{a['created_at']}</div>
          </div>
          <div style="font-size:10.5px;color:{C.t2};line-height:1.6;">{a['message']}</div>
        </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ═══════════════════════════════════════════════════════════════
def _settings():
    st.markdown(f'<div style="font-size:16px; font-weight:700; color:{C.t1}; margin-bottom:15px;">Faculty Command Center</div>', unsafe_allow_html=True)
    
    u = st.session_state.get("user_data", {})
    user_initials = "".join([w[0] for w in u.get("name", "F M").split()[:2]]).upper()

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown(f"""
        <div class="pg-card" style="padding:22px;">
            <div style="display:flex; align-items:center; gap:15px; margin-bottom:15px;">
                <div style="width:50px; height:50px; border-radius:12px; background:{C.gViolet}; 
                            display:flex; align-items:center; justify-content:center; font-size:20px; font-weight:800; color:white;">
                    {user_initials}
                </div>
                <div>
                    <div style="font-size:15px; font-weight:800; color:{C.t1};">Profile Settings</div>
                    <div style="font-size:11px; color:{C.t3};">Manage your faculty identity</div>
                </div>
            </div>""", unsafe_allow_html=True)
        st.text_input("Full Name", value=u.get("name", ""), key="set_name")
        st.text_input("Email Address", value=u.get("email", ""), key="set_email")
        st.button("Update Profile", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="pg-card" style="padding:22px;">
            <div style="display:flex; align-items:center; gap:15px; margin-bottom:15px;">
                <div style="width:50px; height:50px; border-radius:12px; background:{C.gSkyBlue}; 
                            display:flex; align-items:center; justify-content:center; font-size:20px;">🎨</div>
                <div>
                    <div style="font-size:15px; font-weight:800; color:{C.t1};">Preferences</div>
                    <div style="font-size:11px; color:{C.t3};">Customize your dashboard</div>
                </div>
            </div>""", unsafe_allow_html=True)
        st.toggle("Push Notifications", value=True, key="set_push")
        st.toggle("Auto-save Config", value=True, key="set_autosave")
        st.toggle("Advanced Model Previews", value=False, key="set_previews")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:15px;"></div>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="pg-card" style="padding:22px;">
        <div style="display:flex; align-items:center; gap:15px; margin-bottom:15px;">
            <div style="width:50px; height:50px; border-radius:12px; background:{C.gOrange}; 
                        display:flex; align-items:center; justify-content:center; font-size:20px;">🔑</div>
            <div>
                <div style="font-size:15px; font-weight:800; color:{C.t1};">API Configuration</div>
                <div style="font-size:11px; color:{C.t3};">Securely manage your Gemini API Key</div>
            </div>
        </div>""", unsafe_allow_html=True)
    
    k = _get_key()
    if st.session_state.get("v5_api_key"):
        mask = f"{k[:10]}...{k[-4:]}"
        st.success(f"**Manual API Key Active**: `{mask}`", icon="✅")
    elif Config.GEMINI_API_KEY:
        st.info("Using default API Key from system configuration.", icon="ℹ️")
    else:
        st.warning("No API Key detected. Please enter one below to enable paper generation.", icon="⚠️")

    new_key = st.text_input("Gemini API Key", type="password", placeholder="AIzaSy...", help="Your key is only stored in your current session.")
    
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Save & Validate Key", type="primary", use_container_width=True):
            if not new_key.startswith("AIza"):
                st.error("Invalid key format. Should start with 'AIza'.")
            else:
                with st.spinner("Validating key..."):
                    ok, err = _validate_key(new_key)
                    if ok:
                        st.session_state.v5_api_key = new_key
                        st.success("API Key validated and active!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Validation failed: {err}")
    with c2:
        if st.button("Clear Manual Key", type="secondary", use_container_width=True):
            if "v5_api_key" in st.session_state:
                del st.session_state.v5_api_key
                st.info("Manual key cleared. Reverting to system defaults.")
                time.sleep(0.5)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: ABOUT
# ═══════════════════════════════════════════════════════════════
def _about():
    st.markdown(f"""
    <div class="pg-hero" style="text-align:center;padding:32px 26px;">
      <div style="font-size:38px;margin-bottom:13px;">🤖</div>
      <h1 style="font-size:24px;font-weight:800;margin-bottom:8px;">PaperGen AI v5.0</h1>
      <p style="font-size:12.5px;opacity:0.84;max-width:500px;margin:0 auto;line-height:1.7;">
        AI-powered academic examination design. Powered by Google Gemini to automate
        fair, comprehensive paper generation.
      </p>
      <div style="margin-top:18px;display:flex;justify-content:center;gap:7px;flex-wrap:wrap;">
        <span style="background:rgba(255,255,255,0.18);padding:4px 12px;border-radius:20px;font-size:9.5px;font-weight:700;">GEMINI 1.5 FLASH</span>
        <span style="background:rgba(255,255,255,0.18);padding:4px 12px;border-radius:20px;font-size:9.5px;font-weight:700;">STREAMLIT</span>
        <span style="background:rgba(255,255,255,0.18);padding:4px 12px;border-radius:20px;font-size:9.5px;font-weight:700;">PYTHON 3.11</span>
      </div>
    </div>""", unsafe_allow_html=True)

import streamlit as st
from config import Config
from modules.paper_builder import PaperBuilder
from modules.export_handler import ExportHandler
from modules.pdf_extractor import extract_topics_from_pdf, summarize_pdf_text_for_prompt
from login.faculty.login import show_faculty_login
from login.admin.login import show_admin_login
from modules.auth.style_utils import C, inject_global_auth_styles
from dashboard.faculty_dashboard import show_v5_faculty_dashboard
from dashboard.admin_dashboard import show_v5_admin_dashboard
from modules.database import init_db, add_audit_log
import re
import html as html_mod

# Initialize Database
init_db()

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AI Question Paper Generator",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===============================================================================
# ULTRA-PREMIUM CSS - Luxury Dark Editorial
# ===============================================================================
def inject_app_styles():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700;800;900&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
    
        /* -- Root Variables -- */
        :root {
            --obsidian: #0a0a0f;
            --obsidian-2: #0f0f18;
            --obsidian-3: #151520;
            --obsidian-4: #1c1c2e;
            --obsidian-5: #242438;
            --gold: #c9a84c;
            --gold-light: #e4c76b;
            --gold-pale: #f0dfa0;
            --gold-dim: rgba(201,168,76,0.15);
            --gold-glow: rgba(201,168,76,0.25);
            --platinum: #e8e8f0;
            --silver: #a0a0b8;
            --muted: #60607a;
            --emerald: #2dd4a0;
            --emerald-dim: rgba(45,212,160,0.12);
            --rose: #f87491;
            --rose-dim: rgba(248,116,145,0.12);
            --sapphire: #6eb4ff;
            --sapphire-dim: rgba(110,180,255,0.12);
            --border: rgba(201,168,76,0.12);
            --border-hover: rgba(201,168,76,0.3);
            --glass: rgba(255,255,255,0.02);
            --glass-hover: rgba(255,255,255,0.04);
            --shadow-gold: 0 0 40px rgba(201,168,76,0.08);
            --shadow-deep: 0 25px 60px rgba(0,0,0,0.6);
            --radius: 16px;
            --radius-sm: 10px;
        }
    
        /* -- Base Reset -- */
        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'DM Sans', system-ui, sans-serif !important;
            background-color: var(--obsidian) !important;
            color: var(--platinum) !important;
        }
    
        .stApp {
            background: var(--obsidian) !important;
            background-image:
                radial-gradient(ellipse 80% 50% at 50% -20%, rgba(201,168,76,0.06) 0%, transparent 60%),
                radial-gradient(ellipse 40% 30% at 80% 80%, rgba(45,212,160,0.03) 0%, transparent 50%);
        }
    
        .block-container {
            padding-top: 1.5rem !important;
            max-width: 1020px !important;
        }
    </style>
    """, unsafe_allow_html=True)

# Apply global styles ONLY if not in special dashboard mode
if not (st.session_state.get('logged_in') and st.session_state.get('user_role') in ["faculty", "admin"]):
    inject_app_styles()

# ===============================================================================
# SCROLLBAR & HERO
# ===============================================================================
# Note: These are applied globally for login/home
if not (st.session_state.get('logged_in') and st.session_state.get('user_role') in ["faculty", "admin"]):
    st.markdown("""
    <style>
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: var(--obsidian-2); }
        ::-webkit-scrollbar-thumb { background: var(--gold); border-radius: 2px; }
        
        .hero {
            position: relative;
            background: var(--obsidian-3);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 3rem 2.5rem;
            text-align: center;
            margin-bottom: 2rem;
            overflow: hidden;
        }
        .hero::before {
            content: '';
            position: absolute;
            inset: 0;
            background: radial-gradient(ellipse 60% 80% at 50% 0%, rgba(201,168,76,0.08) 0%, transparent 70%);
            pointer-events: none;
        }
    </style>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def format_question_html(content, question_type):
    """Safely format question content as HTML with proper escaping."""
    if not content:
        return '<span style="color:var(--muted);font-style:italic;">No content available</span>'

    lines = content.split('\n')
    in_code = False
    code_buf = []
    html_parts = []
    options = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('```'):
            if in_code:
                code_text = html_mod.escape('\n'.join(code_buf))
                html_parts.append(f'<pre><code>{code_text}</code></pre>')
                code_buf = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_buf.append(line)
            continue

        if not stripped:
            continue

        if question_type == 'MCQ' and (
            re.match(r'^[A-Da-d][).]\s', stripped) or
            re.match(r'^\([A-Da-d]\)\s', stripped)
        ):
            options.append(stripped)
        else:
            html_parts.append(html_mod.escape(stripped))

    if in_code and code_buf:
        code_text = html_mod.escape('\n'.join(code_buf))
        html_parts.append(f'<pre><code>{code_text}</code></pre>')

    result = '<br>'.join(html_parts)

    if options:
        result += '<div style="margin-top:14px;">'
        for opt in options:
            m = re.match(r'^([A-Da-d][).])\s*(.*)', opt)
            if m:
                letter = html_mod.escape(m.group(1))
                text = html_mod.escape(m.group(2))
                result += f'<div class="mcq-opt"><span class="opt-letter">{letter}</span> {text}</div>'
            else:
                result += f'<div class="mcq-opt">{html_mod.escape(opt)}</div>'
        result += '</div>'

    result = re.sub(
        r'`([^`]+)`',
        r'<code style="background:var(--obsidian);padding:2px 8px;border-radius:5px;font-family:\'DM Mono\',monospace;font-size:0.82em;color:var(--gold-pale);border:1px solid rgba(201,168,76,0.15);">\1</code>',
        result
    )

    return result


def render_question(q):
    """Render a single question as a luxury card."""
    diff = q['difficulty'].lower()
    tags = (
        f'<span class="pill pill-{diff}">{html_mod.escape(q["difficulty"])}</span>'
        f'<span class="pill pill-type">{html_mod.escape(q["type"])}</span>'
        f'<span class="pill pill-marks">{q["marks"]} pts</span>'
        f'<span class="pill pill-topic">{html_mod.escape(q["topic"])}</span>'
    )
    body = format_question_html(q['content'], q['type'])

    st.markdown(f"""
    <div class="qc">
        <div class="qc-head">
            <span class="qc-num">Q{q['number']}</span>
            <div class="qc-tags">{tags}</div>
        </div>
        <div class="qc-body">{body}</div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ═══════════════════════════════════════════════════════════════════════════════
if 'generated_papers' not in st.session_state:
    st.session_state.generated_papers = []
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'faculty_name' not in st.session_state:
    st.session_state.faculty_name = ''
if 'auth_screen' not in st.session_state:
    st.session_state.auth_screen = 'login'
if 'auth_tab' not in st.session_state:
    st.session_state.auth_tab = 'faculty'

# ── AUTH GATE ──
if not st.session_state.logged_in:
    inject_global_auth_styles()
    
    # The brand header stays outside the main form container
    mode = st.session_state.auth_tab
    logo_bg = C.facIconGrad if mode == 'faculty' else C.admIconGrad
    logo_svg = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>' if mode == 'faculty' else '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><polyline points="9 12 11 14 15 10"></polyline></svg>'
    
    st.markdown(f"""
    <div style="text-align:center; margin-bottom:10px;">
        <div style="width:64px; height:64px; border-radius:18px; background:{logo_bg}; 
             display:inline-flex; align-items:center; justify-content:center; 
             margin-bottom:12px; box-shadow: 0 8px 25px rgba(0,0,0,0.15);">
             {logo_svg}
        </div>
        <h1 style="font-size:26px; font-weight:700; color:{C.tTitle}; margin-bottom:4px;">
            PaperGen AI
        </h1>
        <p style="font-size:12px; color:{C.tSub}; font-weight:500; margin-bottom:0;">
            AI-Powered Examination System
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Creating a dedicated container that our CSS will target to look like a card
    with st.container():
        # Active tabs for Login
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👤 Faculty", use_container_width=True, type="primary" if st.session_state.auth_tab == 'faculty' else "secondary", key="tab_fac"):
                    st.session_state.auth_tab = 'faculty'
                    st.rerun()
            with col2:
                if st.button("🛡️ Admin", use_container_width=True, type="primary" if st.session_state.auth_tab == 'admin' else "secondary", key="tab_adm"):
                    st.session_state.auth_tab = 'admin'
                    st.rerun()
            
            if st.session_state.auth_tab == 'faculty':
                show_faculty_login()
            else:
                show_admin_login()
        
    st.markdown("""
    <p style="text-align:center; font-size:11px; color:#b0aac8; margin-top:18px; font-weight:500;">
      PaperGen AI · AI & NLP Final Year Project
    </p>
    """, unsafe_allow_html=True)
    st.stop()


# ===============================================================================
# DASHBOARD ROUTING
# ===============================================================================
if st.session_state.logged_in and st.session_state.user_role == "faculty":
    show_v5_faculty_dashboard()
    st.stop()

if st.session_state.logged_in and st.session_state.user_role == "admin":
    show_v5_admin_dashboard()
    st.stop()

# ===============================================================================
# HERO BANNER
# ===============================================================================
st.markdown("""
<div class="hero">
    <div class="hero-eyebrow">✦ Powered by Gemini AI</div>
    <h1>AI Question Paper Generator</h1>
    <div class="hero-divider"></div>
    <p>Craft professional examination papers with intelligent AI generation</p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# API KEY CHECK
# ═══════════════════════════════════════════════════════════════════════════════
if not Config.GEMINI_API_KEY:
    st.error("🔑 Google Gemini API Key not found!")
    st.info("""
    **Get your FREE API Key:**
    1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
    2. Click **Create API Key**
    3. Add to `.env` file: `GEMINI_API_KEY=your_key_here`
    4. Restart the app
    """)
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — Configuration
# ═══════════════════════════════════════════════════════════════════════════════

st.sidebar.markdown(f"""
<div style="padding: 1.2rem 0.5rem 0.5rem; text-align:center;">
    <div style="font-family:'Playfair Display',serif; font-size:1.15rem; font-weight:700; color:#c9a84c; letter-spacing:-0.01em;">
        AI Question Paper Generator
    </div>
    <div style="font-size:0.6rem; color:#60607a; text-transform:uppercase; letter-spacing:0.16em; margin-top:2px;">
        Configuration Panel
    </div>
    <div style="margin-top:0.6rem;font-size:0.72rem;color:#a0a0b8;">
        Signed in as <strong style="color:#e4c76b;">{html_mod.escape(st.session_state.faculty_name)}</strong>
    </div>
</div>
<hr style="border:none; border-top: 1px solid rgba(201,168,76,0.12); margin: 0.8rem 0 1rem;">
""", unsafe_allow_html=True)

if st.sidebar.button("↩ Logout", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.faculty_name = ''
    st.session_state.generated_papers = []
    st.rerun()

st.sidebar.markdown("<br>", unsafe_allow_html=True)


# ── Exam Details ──
st.sidebar.markdown('<div class="sb-label">📋 Exam Details</div>', unsafe_allow_html=True)
exam_name = st.sidebar.text_input("Examination Name", value="Mid-Term Examination", placeholder="e.g., Final Examination 2026")
subject_name = st.sidebar.text_input("Subject", placeholder="e.g., Computer Science")
exam_duration = st.sidebar.selectbox("Duration", [
    "30 Minutes", "45 Minutes", "1 Hour", "1.5 Hours",
    "2 Hours", "2.5 Hours", "3 Hours"
], index=4)
max_marks = st.sidebar.number_input("Maximum Marks", min_value=10, max_value=200, value=50, step=5)

# ── Topics ──
st.sidebar.markdown('<div class="sb-label">📚 Syllabus Topics</div>', unsafe_allow_html=True)

# PDF Upload section
st.sidebar.markdown(
    '<div style="font-size:0.75rem;font-weight:600;color:#a0a0b8;margin-bottom:0.3rem;">Upload Syllabus PDF <span style="color:#60607a;font-weight:400;">(optional)</span></div>',
    unsafe_allow_html=True
)
uploaded_pdf = st.sidebar.file_uploader(
    "Upload PDF", type=["pdf"], label_visibility="collapsed"
)

pdf_context = None
pdf_topics = []

if uploaded_pdf is not None:
    try:
        pdf_bytes = uploaded_pdf.read()
        pdf_topics = extract_topics_from_pdf(pdf_bytes)
        pdf_context = summarize_pdf_text_for_prompt(pdf_bytes, max_chars=4000)
        st.sidebar.success(f"✔ PDF loaded: {len(pdf_topics)} topics detected")
        if pdf_topics:
            with st.sidebar.expander("📖 Detected Topics", expanded=False):
                for i, t in enumerate(pdf_topics[:20], 1):
                    st.markdown(f'<div style="font-size:0.78rem;color:#a0a0b8;padding:2px 0;"><span style="color:#c9a84c;font-weight:700;">{i}.</span> {html_mod.escape(str(t))}</div>', unsafe_allow_html=True)
                if len(pdf_topics) > 20:
                    st.markdown(f'<div style="font-size:0.72rem;color:#60607a;">...and {len(pdf_topics)-20} more</div>', unsafe_allow_html=True)
    except ImportError:
        st.sidebar.error("⚠️ PyMuPDF not installed. Run: pip install PyMuPDF")
    except Exception as e:
        st.sidebar.error(f"⚠️ Could not read PDF: {e}")

# Manual topics
st.sidebar.markdown(
    '<div style="font-size:0.75rem;font-weight:600;color:#a0a0b8;margin:0.6rem 0 0.3rem;">Manual Topics <span style="color:#60607a;font-weight:400;">(optional)</span></div>',
    unsafe_allow_html=True
)
num_topics = st.sidebar.number_input("Number of topics", min_value=0, max_value=10, value=3)

manual_topics = []
for i in range(num_topics):
    t = st.sidebar.text_input(f"Topic {i+1}", key=f"topic_{i}", placeholder=f"e.g., Topic {i+1}")
    if t:
        manual_topics.append(t)

# Combine PDF topics + manual topics (deduplicated)
seen_topics = set()
topics = []
for t in (pdf_topics + manual_topics):
    key = t.lower().strip()
    if key not in seen_topics:
        seen_topics.add(key)
        topics.append(t)

# ── Question Settings ──
st.sidebar.markdown('<div class="sb-label">⚙️ Question Settings</div>', unsafe_allow_html=True)
total_questions = st.sidebar.slider("Total Questions", Config.MIN_QUESTIONS, Config.MAX_QUESTIONS, Config.DEFAULT_QUESTIONS)

st.sidebar.markdown(
    '<div style="font-size:0.75rem; font-weight:600; color:#a0a0b8; margin: 0.5rem 0 0.3rem;">Difficulty Distribution (%)</div>',
    unsafe_allow_html=True
)
dc1, dc2, dc3 = st.sidebar.columns(3)
easy_pct = dc1.number_input("Easy", 0, 100, 40, key="easy")
medium_pct = dc2.number_input("Med", 0, 100, 40, key="medium")
hard_pct = dc3.number_input("Hard", 0, 100, 20, key="hard")

if easy_pct + medium_pct + hard_pct != 100:
    st.sidebar.warning("⚠️ Must sum to 100%")

difficulty_dist = {'Easy': easy_pct, 'Medium': medium_pct, 'Hard': hard_pct}

# ── Question Types & Marks ──
st.sidebar.markdown('<div class="sb-label">📝 Question Types & Marks</div>', unsafe_allow_html=True)
selected_types = st.sidebar.multiselect(
    "Select question types",
    Config.QUESTION_TYPES,
    default=['MCQ', 'Short Answer']
)

custom_marks = {}
if selected_types:
    st.sidebar.markdown(
        '<div style="font-size:0.75rem; font-weight:600; color:#a0a0b8; margin: 0.4rem 0 0.2rem;">Marks per question type</div>',
        unsafe_allow_html=True
    )
    for qtype in selected_types:
        default_m = Config.MARKS_CONFIG['Medium'].get(qtype, 2)
        custom_marks[qtype] = st.sidebar.number_input(
            qtype, min_value=1, max_value=20, value=default_m, key=f"marks_{qtype}"
        )

# ── Output Settings ──
st.sidebar.markdown('<div class="sb-label">📄 Output Settings</div>', unsafe_allow_html=True)
num_sets = st.sidebar.number_input("Paper Sets", min_value=1, max_value=5, value=1)

st.sidebar.markdown("<br>", unsafe_allow_html=True)
generate_btn = st.sidebar.button("✦ Generate Question Papers", type="primary", use_container_width=True)
st.sidebar.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ═══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs(["📋 Question Papers", "📊 Analytics", "ℹ️ About"])

# ── Tab 1: Papers ─────────────────────────────────────────────────────────────
with tab1:

    if generate_btn:
        if not topics:
            st.error("Please add at least one topic in the sidebar.")
        elif not selected_types:
            st.error("Please select at least one question type.")
        elif easy_pct + medium_pct + hard_pct != 100:
            st.error("Difficulty percentages must sum to 100%.")
        else:
            try:
                builder = PaperBuilder()
                builder.custom_marks = custom_marks
                builder.exam_metadata = {
                    'exam_name': exam_name,
                    'subject': subject_name,
                    'duration': exam_duration,
                    'max_marks': max_marks,
                }

                progress_bar = st.progress(0)
                status_text = st.empty()

                def update_progress(current, total, topic, difficulty, q_type):
                    progress_bar.progress(current / total)
                    status_text.markdown(
                        f'<div style="text-align:center;font-size:0.78rem;color:#c9a84c;letter-spacing:0.04em;">'
                        f'Generating <strong>Q{current}/{total}</strong> — {q_type} · {topic} · {difficulty}'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                builder.progress_callback = update_progress

                papers = builder.build_multiple_sets(
                    topics=topics,
                    total_questions=total_questions,
                    difficulty_dist=difficulty_dist,
                    question_types=selected_types,
                    num_sets=num_sets,
                    pdf_context=pdf_context
                )

                for p in papers:
                    p['exam_name'] = exam_name
                    p['subject'] = subject_name
                    p['duration'] = exam_duration
                    p['max_marks'] = max_marks

                progress_bar.empty()
                status_text.empty()

                st.session_state.generated_papers = papers

                total_q = sum(p['total_questions'] for p in papers)
                if total_q > 0:
                    st.success(f"✦ Successfully generated {total_q} question(s) across {num_sets} paper set(s).")
                else:
                    st.error("No questions generated. Check your API key and internet connection.")

                for p in papers:
                    if p.get('errors'):
                        with st.expander(f"⚠️ {len(p['errors'])} warning(s) — {p['name']}"):
                            for err in p['errors']:
                                st.warning(err)

            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.info("Make sure your API key is valid and you have internet connection.")

    # ── Display Papers ──
    if st.session_state.generated_papers:
        for paper in st.session_state.generated_papers:

            ex_title = paper.get('exam_name', 'Examination')
            subj = paper.get('subject', '')
            dur = paper.get('duration', '')
            mm = paper.get('max_marks', paper['total_marks'])

            subj_html = f'<span><strong>Subject:</strong> {html_mod.escape(str(subj))}</span><span class="paper-meta-divider">·</span>' if subj else ""

            st.markdown(f"""
            <div class="paper-title">
                <div class="paper-kicker">Official Examination Document</div>
                <h2>{html_mod.escape(str(ex_title))} — {html_mod.escape(paper['name'])}</h2>
                <div class="paper-meta">
                    {subj_html}
                    <span><strong>Duration:</strong> {html_mod.escape(str(dur))}</span>
                    <span class="paper-meta-divider">·</span>
                    <span><strong>Max Marks:</strong> {mm}</span>
                    <span class="paper-meta-divider">·</span>
                    <span><strong>Questions:</strong> {paper['total_questions']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Metric Cards ──
            mc1, mc2, mc3, mc4 = st.columns(4)
            with mc1:
                st.markdown(f'<div class="mc"><div class="mc-label">Questions</div><div class="mc-val">{paper["total_questions"]}</div><div class="mc-sub">total items</div></div>', unsafe_allow_html=True)
            with mc2:
                st.markdown(f'<div class="mc"><div class="mc-label">Total Marks</div><div class="mc-val">{paper["total_marks"]}</div><div class="mc-sub">points available</div></div>', unsafe_allow_html=True)
            with mc3:
                st.markdown(f'<div class="mc"><div class="mc-label">Topics</div><div class="mc-val">{len(paper["topics"])}</div><div class="mc-sub">covered</div></div>', unsafe_allow_html=True)
            with mc4:
                qt_count = len(set(q['type'] for q in paper['questions'])) if paper['questions'] else 0
                st.markdown(f'<div class="mc"><div class="mc-label">Formats</div><div class="mc-val">{qt_count}</div><div class="mc-sub">question types</div></div>', unsafe_allow_html=True)

            st.markdown("")

            # ── Questions ──
            by_type = {}
            for q in paper['questions']:
                by_type.setdefault(q['type'], []).append(q)

            with st.expander("📄 View Question Paper", expanded=True):
                sec = 1
                for qtype, qs in by_type.items():
                    sec_marks = sum(q['marks'] for q in qs)
                    st.markdown(
                        f'<div class="sec-div">Section {sec} &nbsp;·&nbsp; {html_mod.escape(qtype)} &nbsp;({len(qs)} Q · {sec_marks} pts)</div>',
                        unsafe_allow_html=True
                    )
                    for q in qs:
                        render_question(q)
                    sec += 1



            # ── Downloads ──
            st.markdown(
                f'<div class="sec-div">Export {html_mod.escape(paper["name"])}</div>',
                unsafe_allow_html=True
            )
            dl1, dl2, dl3 = st.columns(3)

            with dl1:
                try:
                    fp = ExportHandler.export_to_pdf(paper)
                    with open(fp, 'rb') as f:
                        st.download_button(
                            "📄 Download PDF", f.read(),
                            f"{paper['name'].replace(' ', '_')}.pdf",
                            "application/pdf",
                            key=f"pdf_{paper['name']}",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"PDF error: {e}")

            with dl2:
                try:
                    fp = ExportHandler.export_to_docx(paper)
                    with open(fp, 'rb') as f:
                        st.download_button(
                            "📝 Download DOCX", f.read(),
                            f"{paper['name'].replace(' ', '_')}.docx",
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"docx_{paper['name']}",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"DOCX error: {e}")

            with dl3:
                try:
                    fp = ExportHandler.export_to_txt(paper)
                    with open(fp, 'r', encoding='utf-8') as f:
                        st.download_button(
                            "📃 Download TXT", f.read(),
                            f"{paper['name'].replace(' ', '_')}.txt",
                            "text/plain",
                            key=f"txt_{paper['name']}",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"TXT error: {e}")

            st.markdown('<hr style="border:none; border-top:1px solid rgba(201,168,76,0.1); margin:2rem 0;">', unsafe_allow_html=True)

    else:
        st.markdown("""
        <div class="empty-state">
            <span class="empty-state-icon">✦</span>
            <h3>Ready to Create</h3>
            <p>Configure your examination parameters in the sidebar, then generate your papers.</p>
            <div class="empty-steps">
                <div class="empty-step">
                    <div class="empty-step-num">01</div>
                    <div class="empty-step-label">Exam Details</div>
                    <div class="empty-step-desc">Set name, subject & duration</div>
                </div>
                <div class="empty-step">
                    <div class="empty-step-num">02</div>
                    <div class="empty-step-label">Add Topics</div>
                    <div class="empty-step-desc">Define your syllabus</div>
                </div>
                <div class="empty-step">
                    <div class="empty-step-num">03</div>
                    <div class="empty-step-label">Configure</div>
                    <div class="empty-step-desc">Set difficulty & types</div>
                </div>
                <div class="empty-step">
                    <div class="empty-step-num">04</div>
                    <div class="empty-step-label">Generate</div>
                    <div class="empty-step-desc">Download in PDF, DOCX, TXT</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ── Tab 2: Analytics ──────────────────────────────────────────────────────────
with tab2:
    if st.session_state.generated_papers:
        for paper in st.session_state.generated_papers:
            st.markdown(
                f'<div style="font-family:\'Playfair Display\',serif;font-size:1.2rem;font-weight:700;color:#e4c76b;margin-bottom:1.2rem;">{html_mod.escape(paper["name"])}</div>',
                unsafe_allow_html=True
            )

            if not paper['questions']:
                st.info("No questions in this paper.")
                continue

            diff_colors = {
                'Easy': 'var(--emerald)',
                'Medium': 'var(--gold-light)',
                'Hard': 'var(--rose)'
            }

            sc1, sc2, sc3 = st.columns(3)

            with sc1:
                st.markdown(
                    '<div style="font-size:0.65rem;font-weight:700;color:#c9a84c;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:1rem;">Difficulty</div>',
                    unsafe_allow_html=True
                )
                diff_counts = {}
                for q in paper['questions']:
                    diff_counts[q['difficulty']] = diff_counts.get(q['difficulty'], 0) + 1
                for diff, count in diff_counts.items():
                    pct = count / paper['total_questions'] * 100
                    color = diff_colors.get(diff, 'var(--gold)')
                    st.markdown(f"""
                    <div class="sbar-wrap">
                        <div class="sbar-header">
                            <span>{html_mod.escape(diff)}</span>
                            <span class="sbar-pct">{count} · {pct:.0f}%</span>
                        </div>
                        <div class="sbar-bg">
                            <div class="sbar-fg" style="width:{pct}%;background:{color};"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            with sc2:
                st.markdown(
                    '<div style="font-size:0.65rem;font-weight:700;color:#c9a84c;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:1rem;">Question Types</div>',
                    unsafe_allow_html=True
                )
                type_counts = {}
                for q in paper['questions']:
                    type_counts[q['type']] = type_counts.get(q['type'], 0) + 1
                for qtype, count in type_counts.items():
                    pct = count / paper['total_questions'] * 100
                    st.markdown(f"""
                    <div class="sbar-wrap">
                        <div class="sbar-header">
                            <span>{html_mod.escape(qtype)}</span>
                            <span class="sbar-pct">{count} · {pct:.0f}%</span>
                        </div>
                        <div class="sbar-bg">
                            <div class="sbar-fg" style="width:{pct}%;background:var(--sapphire);"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            with sc3:
                st.markdown(
                    '<div style="font-size:0.65rem;font-weight:700;color:#c9a84c;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:1rem;">Topic Coverage</div>',
                    unsafe_allow_html=True
                )
                topic_counts = {}
                for q in paper['questions']:
                    topic_counts[q['topic']] = topic_counts.get(q['topic'], 0) + 1
                for topic_name, count in topic_counts.items():
                    pct = count / paper['total_questions'] * 100
                    st.markdown(f"""
                    <div class="sbar-wrap">
                        <div class="sbar-header">
                            <span>{html_mod.escape(topic_name)}</span>
                            <span class="sbar-pct">{count} · {pct:.0f}%</span>
                        </div>
                        <div class="sbar-bg">
                            <div class="sbar-fg" style="width:{pct}%;background:#c4b5fd;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown(
                '<div style="font-size:0.65rem;font-weight:700;color:#c9a84c;text-transform:uppercase;letter-spacing:0.14em;margin:1.5rem 0 1rem;">Marks by Section</div>',
                unsafe_allow_html=True
            )
            marks_data = {}
            for q in paper['questions']:
                marks_data[q['type']] = marks_data.get(q['type'], 0) + q['marks']

            if marks_data:
                mcols = st.columns(len(marks_data))
                for i, (qtype, total_m) in enumerate(marks_data.items()):
                    with mcols[i]:
                        st.markdown(
                            f'<div class="mc"><div class="mc-label">{html_mod.escape(qtype)}</div>'
                            f'<div class="mc-val">{total_m}</div><div class="mc-sub">marks</div></div>',
                            unsafe_allow_html=True
                        )

            st.markdown('<hr style="border:none; border-top:1px solid rgba(201,168,76,0.1); margin:2rem 0;">', unsafe_allow_html=True)
    else:
        st.info("Generate papers first to view analytics.")


# ── Tab 3: About ──────────────────────────────────────────────────────────────
with tab3:
    st.markdown("""
    <div style="max-width:640px;">
    <div style="font-family:'Playfair Display',serif; font-size:1.6rem; font-weight:700; color:#e4c76b; margin-bottom:0.5rem;">About AI Question Paper Generator</div>
    <p style="color:#a0a0b8; line-height:1.8; font-size:0.9rem;">
    AI Question Paper Generator is an AI-powered examination paper studio built on Google Gemini AI.
    It generates professional, unique questions with separate answer keys —
    designed for educators who need quality, speed, and control.
    </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr style="border:none; border-top:1px solid rgba(201,168,76,0.1); margin:1.5rem 0;">', unsafe_allow_html=True)

    st.markdown("""
    **Key Features**

    - **AI-Powered Generation** — Unique, contextual questions via Google Gemini 2.5 Flash
    - **Separate Answer Keys** — Questions and answers always kept apart for fairness
    - **Sectioned Papers** — Cleanly organized by type (MCQ, Short Answer, etc.)
    - **Custom Marks** — Set marks per question type with full control
    - **Multiple Paper Sets** — Generate Set A, B, C with distinct questions
    - **Difficulty Control** — Precise Easy / Medium / Hard percentage distribution
    - **Export Options** — Download as PDF, DOCX, or TXT instantly
    """)

    st.markdown('<hr style="border:none; border-top:1px solid rgba(201,168,76,0.1); margin:1.5rem 0;">', unsafe_allow_html=True)

    st.markdown("**Technology Stack**")
    st.markdown("""
    | Component | Technology |
    |-----------|------------|
    | Backend | Python 3.11 |
    | UI Framework | Streamlit |
    | AI Engine | Google Gemini 2.5 Flash |
    | PDF Export | FPDF |
    | DOCX Export | python-docx |
    """)

    st.markdown('<hr style="border:none; border-top:1px solid rgba(201,168,76,0.1); margin:1.5rem 0;">', unsafe_allow_html=True)

    st.markdown("""
    **How to Use**
    1. Fill in exam details — name, subject, duration, and max marks
    2. Add your syllabus topics
    3. Configure question count, difficulty balance, and question types
    4. Set marks per question type
    5. Click **Generate Question Papers**
    6. Review questions, check the answer key, and download your papers
    """)


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="app-footer">
    Examina · AI Question Paper Studio
    <span>·</span>
    Powered by Google Gemini AI
    <span>·</span>
    Always review generated content for accuracy
</div>
""", unsafe_allow_html=True)
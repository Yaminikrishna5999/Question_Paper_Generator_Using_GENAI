import streamlit as st

class C:
    # Colors matching the user's exact prompt
    pageBg = "#edeaf6"
    card = "#ffffff"
    cardSh = "0 4px 32px rgba(100,60,200,0.09)"
    
    # Gradients
    tabActiveGrad = "linear-gradient(90deg, #f02fc2 0%, #7c3aed 100%)"
    facIconGrad = "linear-gradient(135deg, #d63af5, #7b35f0)"
    admIconGrad = "linear-gradient(135deg, #2e3a8c, #1a237e)"
    
    # Inputs
    inputBg = "#f5f3fb"
    inputBd = "#ede9f8"
    inputHoverBg = "#faf8ff"
    inputHoverBd = "#a07ef0"
    placeholder = "#c0bad8"
    
    # Inactive Tab
    tabBg = "#f5f3fb"
    tabBd = "#e8e4f4"
    tabText = "#9490b0"
    tabHoverBg = "#ede9f8"
    tabHoverText = "#7c3aed"
    
    # Text
    tTitle = "#1a1060"
    tSub = "#9490b0"
    
    # Admin Notice
    admNoticeBg = "#eef0ff"
    admNoticeBd = "#cdd3f8"
    admBadgeBg = "#dce2ff"
    admNoticeTitle = "#3648b8"
    admNoticeSub = "#7482c8"

GLOBAL_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    /* Global Typography & Hide Streamlit Junk */
    * {{ font-family: 'Inter', sans-serif !important; }}
    header, [data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none !important; }}
    footer {{ visibility: hidden; }}
    
    /* Background and Layout */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .stApp {{
        background: {C.pageBg} !important;
        overflow-x: hidden;
    }}
    
    .main .block-container {{ 
        padding-top: 3rem !important; 
        padding-bottom: 2rem !important;
        max-width: 500px !important; 
        width: 100% !important;
        margin: 0 auto !important;
        display: block !important;
    }}

    /* Card Styling */
    [data-testid="stVerticalBlock"] > div:has([data-testid="stVerticalBlock"]) {{
        background: {C.card} !important;
        border-radius: 20px !important;
        padding: 22px 26px 28px !important;
        box-shadow: {C.cardSh} !important;
        border: none !important;
        width: 100% !important;
        margin-top: 15px !important;
    }}

    /* Targeted fix: Remove nested white boxes */
    [data-testid="stVerticalBlock"] [data-testid="stVerticalBlock"] > div {{
        background: transparent !important;
        box-shadow: none !important;
        border: none !important;
        padding: 0 !important;
    }}
    
    /* Outer Input Wrapper */
    [data-testid="stTextInput"] div[data-baseweb="input"] {{
        background-color: {C.inputBg} !important;
        border: 1.5px solid {C.inputBd} !important;
        border-radius: 12px !important;
        transition: all 0.2s ease-in-out !important;
        overflow: hidden !important;
    }}
    [data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {{
        background-color: {C.inputHoverBg} !important;
        border-color: {C.inputHoverBd} !important;
    }}
    
    /* Inner Text Input */
    [data-testid="stTextInput"] input {{
        background-color: transparent !important;
        border: none !important;
        font-weight: 500 !important;
        padding: 0 16px !important;
        height: 48px !important;
        color: {C.tTitle} !important;
        box-shadow: none !important;
        outline: none !important;
    }}
    [data-testid="stTextInput"] input::placeholder {{
        color: {C.placeholder} !important;
        opacity: 1 !important;
    }}

    
    /* Input Labels */
    /* Only target the labels right above inputs, not markdown */
    [data-testid="stWidgetLabel"] p {{
        font-size: 10px !important;
        font-weight: 700 !important;
        color: {C.tSub} !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        margin-bottom: 6px !important;
    }}

    /* Buttons row (Tabs inside card) */
    /* Streamlit columns have gap, we'll try to override or just use it */
    [data-testid="column"] [data-testid="stBaseButton-primary"],
    [data-testid="column"] [data-testid="stBaseButton-secondary"] {{
        height: 48px !important;
        border-radius: 12px !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        width: 100% !important;
        border: none !important;
        transition: all 0.2s !important;
    }}
    
    /* Inactive Tab (Secondary) */
    [data-testid="column"] [data-testid="stBaseButton-secondary"] {{
        background: {C.tabBg} !important;
        border: 2px solid {C.tabBd} !important;
        color: {C.tabText} !important;
    }}
    [data-testid="column"] [data-testid="stBaseButton-secondary"]:hover {{
        background: {C.tabHoverBg} !important;
        color: {C.tabHoverText} !important;
        box-shadow: 0 4px 12px rgba(124,58,237,0.1) !important;
        transform: translateY(-1px);
    }}
    
    /* Active Tab (Primary in columns) & Submit Buttons (Primary everywhere) */
    [data-testid="stBaseButton-primary"] {{
        background: {C.tabActiveGrad} !important;
        color: #ffffff !important;
        box-shadow: 0 6px 20px rgba(210,45,185,0.40), 0 2px 8px rgba(124,58,237,0.20) !important;
    }}
    [data-testid="stBaseButton-primary"]:hover {{
        box-shadow: 0 8px 24px rgba(210,45,185,0.50), 0 4px 12px rgba(124,58,237,0.30) !important;
        transform: translateY(-1px);
    }}
    [data-testid="stBaseButton-primary"]:active {{
        transform: translateY(1px);
        box-shadow: 0 2px 10px rgba(210,45,185,0.30) !important;
    }}

    /* Submit Button Specifics (if outside columns) */
    [data-testid="stForm"] [data-testid="stBaseButton-primary"],
    /* or anywhere primary button is used for submit */
    div:not([data-testid="column"]) > [data-testid="stBaseButton-primary"] {{
        height: 50px !important;
        border-radius: 13px !important;
        font-size: 15px !important;
        box-shadow: 0 6px 22px rgba(210,45,185,0.36), 0 2px 8px rgba(124,58,237,0.18) !important;
    }}

</style>
"""

def inject_global_auth_styles():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

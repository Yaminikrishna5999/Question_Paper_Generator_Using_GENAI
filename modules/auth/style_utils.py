import streamlit as st

class C:
    pageBg = "#F8F4FD"
    card = "#FFFFFF"
    cardBd = "#EDE8F5"
    cardSh = "0 2px 10px rgba(114,9,183,0.07),0 1px 3px rgba(114,9,183,0.04)"
    cardShHov = "0 20px 60px rgba(114,9,183,0.13),0 4px 16px rgba(114,9,183,0.07)"
    input = "#F4F0FB"
    inputBd = "#E4DCF5"
    gPinkVio = "linear-gradient(135deg,#F72585,#7209B7)"
    gAdmin = "linear-gradient(135deg,#1E1B4B,#3730A3)"
    pink = "#F72585"
    violet = "#7209B7"
    indigo = "#4361EE"
    red = "#EF4444"
    redLt = "#FEE2E2"
    redBd = "#FCA5A5"
    green = "#2DC653"
    t1 = "#2D1B69"
    t2 = "#4A3880"
    t3 = "#6E6893"
    t4 = "#A89EC4"
    t5 = "#D4CEE8"

GLOBAL_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    /* Global Typography & Hide Streamlit Junk */
    * {{ font-family: 'Plus Jakarta Sans', sans-serif !important; }}
    header, [data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none !important; }}
    footer {{ visibility: hidden; }}
    
    /* Centered Layout with Scrolling Enabled */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .stApp {{
        background: {C.pageBg} !important;
        /* Natural height to allow scrolling */
    }}
    
    .main .block-container {{ 
        padding-top: 4rem !important; 
        padding-bottom: 4rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 440px !important; 
        width: 100% !important;
        margin: 0 auto !important;
        display: block !important;
    }}

    /* Ensure vertical block behaves naturally */
    [data-testid="stVerticalBlock"] {{
        width: 100% !important;
    }}

    /* Decorative blobs */
    .blob {{ position: fixed; border-radius: 50%; pointer-events: none; z-index: -1; }}
    .blob-1 {{ top: -100px; right: -100px; width: 420px; height: 420px; background: rgba(247, 37, 133, 0.08); }}
    .blob-2 {{ bottom: -100px; left: -80px; width: 360px; height: 360px; background: rgba(114, 9, 183, 0.07); }}
    
    /* Broad Card Targeting (Streamlined for Login) */
    [data-testid="stVerticalBlock"] > div:has([data-testid="stVerticalBlock"]) {{
        background: {C.card} !important;
        border-radius: 20px !important;
        padding: 24px 20px !important;
        box-shadow: {C.cardShHov} !important;
        border: 1px solid {C.cardBd} !important;
        animation: fadeUp 0.5s ease-out;
        width: 100% !important;
    }}

    /* Targeted fix: Remove nested white boxes for columns/nested blocks */
    [data-testid="stVerticalBlock"] [data-testid="stVerticalBlock"] > div {{
        background: transparent !important;
        box-shadow: none !important;
        border: none !important;
        padding: 0 !important;
    }}
    
    @keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}

    /* Inputs Skinning - unified look for all inputs */
    [data-testid="stTextInput"] input, 
    [data-testid="stSelectbox"] div[data-baseweb="select"],
    [data-testid="stSelectbox"] [role="combobox"],
    [data-testid="stTextInput"] div[data-baseweb="input"] {{
        background-color: {C.input} !important;
        border: 1.5px solid {C.inputBd} !important;
        border-radius: 12px !important;
        color: {C.t1} !important;
        font-weight: 500 !important;
        padding: 8px 12px !important; /* Adjusted for better alignment */
        height: 48px !important; /* Standard professional height */
        transition: all 0.2s ease-in-out !important;
        display: flex !important;
        align-items: center !important;
    }}

    /* Specific fix for selectbox text alignment */
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
        padding: 0 !important;
        background: transparent !important;
        color: {C.t1} !important;
    }}
    
    /* Labels */
    [data-testid="stWidgetLabel"] p {{
        font-size: 11px !important;
        font-weight: 700 !important;
        color: {C.t3} !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        margin-bottom: 6px !important;
    }}

    /* Buttons */
    [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-secondary"] {{
        border-radius: 14px !important;
        font-weight: 700 !important;
        letter-spacing: -0.2px !important;
        transition: all 0.2s !important;
        border: none !important;
        width: 100% !important;
    }}
    [data-testid="stBaseButton-primary"] {{
        background: {C.gPinkVio} !important;
        color: white !important;
        box-shadow: 0 8px 24px rgba(247, 37, 133, 0.25) !important;
        height: 50px !important;
    }}
</style>
<div class="blob blob-1"></div>
<div class="blob blob-2"></div>
"""

def inject_global_auth_styles():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

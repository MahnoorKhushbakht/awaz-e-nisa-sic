import streamlit as st
import os
import shutil
import pytesseract
import pdfplumber
from PIL import Image
import cv2
import numpy as np
import tempfile
import warnings
import uuid
from datetime import datetime
from fpdf import FPDF
from database import init_db, add_user, verify_user, save_chat_message, get_chat_history, delete_chat_history

# ============================================================
#  CONFIGURATION (MUST BE FIRST)
# ============================================================
st.set_page_config(
    page_title="Awaz-e-Nisa | Legal AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# ============================================================
#  PATH CONFIGURATION
# ============================================================
@st.cache_resource
def configure_paths():
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    if not shutil.which("ffmpeg"):
        winget_base = os.path.join(os.environ.get('LOCALAPPDATA', ''), r'Microsoft\WinGet\Packages')
        if os.path.exists(winget_base):
            os.environ["PATH"] += os.pathsep + winget_base

configure_paths()
init_db()

# ============================================================
#  SESSION STATE DEFAULTS
# ============================================================
defaults = {
    "logged_in": False,
    "show_landing": True,
    "messages": [],
    "current_mode": "GENERAL USER (Woman)",
    "active_feature": "Legal Chat",
    "last_query": "",
    "chat_sessions": {},
    "active_session_id": None,
    "show_analysis": False,
    "analysis_result": None,
    "theme": "dark",
    "font_size": "medium",
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ============================================================
#  DARK THEME CSS
# ============================================================
dark_theme = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&family=Inter:wght@300;400;500;600&display=swap');

:root {
    --fs-xs:   11px;
    --fs-sm:   13px;
    --fs-base: 15px;
    --fs-md:   17px;
    --fs-lg:   19px;
    --fs-xl:   22px;
    --fs-2xl:  28px;
    --fs-3xl:  36px;
    --fs-hero: 60px;

    --c-bg:          #0f0a1a;
    --c-surface:     #1a1028;
    --c-surface2:    #221535;
    --c-border:      rgba(255, 255, 255, 0.10);
    --c-border-pink: rgba(255, 46, 126, 0.30);

    --c-text:        #f0e8ff;
    --c-text-muted:  #b8a8d0;
    --c-text-dim:    #8878a8;
    --c-text-hint:   #604878;

    --c-pink:        #FF2E7E;
    --c-purple:      #8A2BE2;
    --c-red-alert:   #ef4444;
    --c-green:       #4ade80;

    --radius-sm:  8px;
    --radius-md:  12px;
    --radius-lg:  18px;
    --radius-xl:  24px;
    --radius-pill:60px;
}

[data-font="small"]  { --fs-base: 13px; --fs-md: 15px; --fs-lg: 17px; }
[data-font="large"]  { --fs-base: 17px; --fs-md: 19px; --fs-lg: 21px; }

*, *::before, *::after { box-sizing: border-box; }

.stApp {
    background: var(--c-bg) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: var(--fs-base) !important;
}
.stApp > header { display: none !important; }
#MainMenu, footer { display: none !important; }
.stApp > div { background: var(--c-bg) !important; }

p, span, label, div, li, td, th {
    font-family: 'Inter', sans-serif !important;
    color: var(--c-text) !important;
    font-size: var(--fs-base) !important;
    line-height: 1.65 !important;
}
h1, h2, h3, h4, h5, h6 {
    font-family: 'Playfair Display', serif !important;
    color: #f8f2ff !important;
    letter-spacing: -0.02em !important;
}
h1 { font-size: var(--fs-hero)  !important; }
h2 { font-size: var(--fs-3xl)   !important; }
h3 { font-size: var(--fs-2xl)   !important; }
h4 { font-size: var(--fs-xl)    !important; }
h5 { font-size: var(--fs-lg)    !important; }
h6 { font-size: var(--fs-md)    !important; }
small, .small { font-size: var(--fs-sm) !important; color: var(--c-text-muted) !important; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #13091f 0%, var(--c-bg) 100%) !important;
    border-right: 1px solid var(--c-border-pink) !important;
    width: 280px !important;
    backdrop-filter: blur(10px);
}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] div,
section[data-testid="stSidebar"] li {
    color: var(--c-text-muted) !important;
    font-size: var(--fs-sm) !important;
}
section[data-testid="stSidebar"] strong,
section[data-testid="stSidebar"] b { color: var(--c-text) !important; }

.block-container {
    padding: 0 2rem 5rem 2rem !important;
    max-width: 1200px !important;
    margin: 0 auto !important;
    position: relative;
    z-index: 1;
}

.samsung-footer {
    text-align: center; padding: 20px; margin-top: 30px;
    border-top: 1px solid var(--c-border-pink);
    font-size: var(--fs-xs) !important;
    color: var(--c-text-dim) !important;
}
.samsung-logo {
    display: inline-flex; align-items: center; gap: 8px;
    background: rgba(255,255,255,0.05);
    padding: 6px 16px; border-radius: 30px; margin-bottom: 8px;
}
.samsung-icon { font-size: 14px; }
.samsung-text { font-weight: 600; letter-spacing: 1px; color: var(--c-text) !important; }

.about-page { padding: 20px; }
.about-hero {
    text-align: center; padding: 40px 20px;
    background: linear-gradient(135deg, rgba(255,46,126,0.10), rgba(138,43,226,0.10));
    border-radius: var(--radius-xl); margin-bottom: 30px;
    border: 1px solid var(--c-border-pink);
}
.about-hero-icon { font-size: 64px; margin-bottom: 20px; }
.about-hero-title {
    font-size: var(--fs-3xl) !important; font-weight: 700;
    background: linear-gradient(135deg, var(--c-pink), var(--c-purple));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 10px; font-family: 'Playfair Display', serif !important;
}
.about-hero-sub { font-size: var(--fs-md) !important; color: var(--c-text-muted) !important; }
.about-card {
    background: var(--c-surface); border: 1px solid var(--c-border-pink);
    border-radius: var(--radius-lg); padding: 25px; margin-bottom: 20px;
}
.about-card-title {
    font-size: var(--fs-xl) !important; font-weight: 700;
    color: var(--c-pink) !important; margin-bottom: 15px;
    display: flex; align-items: center; gap: 10px;
    font-family: 'Playfair Display', serif !important;
}
.about-card-text {
    font-size: var(--fs-base) !important; line-height: 1.75 !important;
    color: var(--c-text-muted) !important;
}
.about-badge-container { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 15px; }
.about-badge-large {
    background: rgba(255,46,126,0.15); border: 1px solid rgba(255,46,126,0.35);
    padding: 8px 18px; border-radius: 30px;
    font-size: var(--fs-sm) !important; color: #ffa0c0 !important; font-weight: 500;
}
.about-highlight { color: var(--c-pink) !important; font-weight: 600; }

.demo-section {
    background: var(--c-surface); border: 1px solid var(--c-border-pink);
    border-radius: var(--radius-lg); padding: 20px; margin: 20px 0;
}
.demo-title {
    font-size: var(--fs-sm) !important; font-weight: 600;
    color: var(--c-pink) !important; margin-bottom: 15px;
    display: flex; align-items: center; gap: 8px;
}
.demo-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.demo-question {
    background: var(--c-surface2); border: 1px solid rgba(255,46,126,0.25);
    border-radius: var(--radius-md); padding: 14px;
    cursor: pointer; transition: all 0.2s ease;
}
.demo-question:hover {
    background: rgba(255,46,126,0.12); border-color: var(--c-pink); transform: translateX(4px);
}
.demo-category {
    font-size: var(--fs-xs) !important; color: var(--c-pink) !important;
    margin-bottom: 6px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
}
.demo-text { font-size: var(--fs-sm) !important; line-height: 1.55 !important; color: var(--c-text-muted) !important; }

.an-welcome { text-align: center; padding: 20px; animation: fadeInUp 0.6s ease-out; }
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(30px); }
    to   { opacity: 1; transform: translateY(0); }
}
.an-welcome-icon { font-size: 56px; margin-bottom: 15px; animation: bounce 2s infinite; }
@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50%       { transform: translateY(-8px); }
}
.an-welcome-title {
    font-size: var(--fs-2xl) !important; font-weight: 700;
    background: linear-gradient(135deg, var(--c-pink), var(--c-purple));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 10px; font-family: 'Playfair Display', serif !important;
}
.an-welcome-sub { font-size: var(--fs-base) !important; color: var(--c-text-muted) !important; line-height: 1.7 !important; }

[data-testid="stChatInput"] {
    background: var(--c-surface) !important; border: 2px solid var(--c-border-pink) !important;
    border-radius: var(--radius-pill) !important; padding: 4px 8px 4px 24px !important;
    margin: 20px 0 !important; transition: all 0.3s cubic-bezier(0.4,0,0.2,1) !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3) !important;
}
[data-testid="stChatInput"]:hover,
[data-testid="stChatInput"]:focus-within {
    border-color: var(--c-pink) !important;
    box-shadow: 0 6px 30px rgba(255,46,126,0.35) !important;
    transform: translateY(-2px);
}
[data-testid="stChatInput"] textarea {
    background: transparent !important; color: var(--c-text) !important;
    font-size: var(--fs-base) !important; font-weight: 400 !important;
    padding: 14px 8px !important; font-family: 'Inter', sans-serif !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--c-text-dim) !important; font-size: var(--fs-sm) !important; }
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, var(--c-pink), var(--c-purple)) !important;
    border-radius: 50% !important; width: 44px !important; height: 44px !important;
    margin: 4px !important; transition: all 0.3s cubic-bezier(0.4,0,0.2,1) !important;
}
[data-testid="stChatInput"] button:hover { transform: scale(1.1) rotate(15deg) !important; }

.an-section-header {
    background: linear-gradient(135deg, rgba(255,46,126,0.10), rgba(138,43,226,0.10));
    border: 1px solid var(--c-border-pink); border-radius: var(--radius-lg);
    padding: 20px 24px; margin-bottom: 24px;
    display: flex; justify-content: space-between; align-items: center;
}
.an-header-left { display: flex; align-items: center; gap: 16px; }
.an-icon-box {
    width: 48px; height: 48px;
    background: linear-gradient(135deg, rgba(255,46,126,0.15), rgba(138,43,226,0.15));
    border: 1px solid var(--c-border-pink); border-radius: var(--radius-md);
    display: flex; align-items: center; justify-content: center; font-size: 24px;
}
.an-feature-title {
    font-size: var(--fs-xl) !important; font-weight: 700; color: #f8f2ff !important;
    font-family: 'Playfair Display', serif !important;
}
.an-feature-sub { font-size: var(--fs-xs) !important; color: var(--c-text-dim) !important; }
.an-mode-chip {
    display: inline-block; background: rgba(255,46,126,0.20); color: #ffa0c0 !important;
    padding: 2px 10px; border-radius: 12px; font-size: var(--fs-xs) !important; font-weight: 600;
}

.sb-pad { padding: 0 12px; }
.an-user-card {
    background: linear-gradient(135deg, rgba(255,46,126,0.10), rgba(138,43,226,0.10));
    border: 1px solid var(--c-border-pink); border-radius: var(--radius-md);
    padding: 14px; margin: 16px 0; display: flex; align-items: center; gap: 12px;
}
.an-avatar {
    width: 44px; height: 44px;
    background: linear-gradient(135deg, var(--c-pink), var(--c-purple));
    border-radius: 50%; display: flex; align-items: center; justify-content: center;
    font-size: 18px; font-weight: 700; color: white !important; flex-shrink: 0;
}
.an-uname { font-size: var(--fs-base) !important; font-weight: 600; color: var(--c-text) !important; }
.an-ustatus { font-size: var(--fs-xs) !important; color: var(--c-green) !important; }
.an-nav-label {
    font-size: var(--fs-xs) !important; color: var(--c-pink) !important;
    text-transform: uppercase; letter-spacing: 1px; font-weight: 700;
    margin: 20px 0 12px; display: block;
}

.an-hotlines {
    background: rgba(220,38,38,0.10); border: 1px solid rgba(220,38,38,0.30);
    border-radius: var(--radius-md); padding: 14px; margin-top: 20px;
}
.an-hotlines-title {
    font-size: var(--fs-xs) !important; font-weight: 700; color: var(--c-red-alert) !important;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px;
}
.an-hotline-row {
    display: flex; justify-content: space-between; padding: 6px 0;
    border-bottom: 1px solid rgba(220,38,38,0.12);
}
.an-hotline-row:last-child { border-bottom: none; }
.an-hotline-label { font-size: var(--fs-sm) !important; color: var(--c-text-muted) !important; }
.an-hotline-num { font-size: var(--fs-sm) !important; color: var(--c-red-alert) !important; font-weight: 700; }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,0.04); }
::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, var(--c-pink), var(--c-purple)); border-radius: 10px;
}

/* Landing page nav */
.lp-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 18px 40px; position: fixed; top: 0; left: 0; right: 0; z-index: 999;
    background: rgba(15,10,26,0.94); backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(255,46,126,0.18);
}
.lp-logo { display: flex; align-items: center; gap: 10px; }
.lp-logo-text {
    font-family: 'Playfair Display', serif; font-size: var(--fs-lg) !important; font-weight: 700;
    background: linear-gradient(135deg, var(--c-pink), var(--c-purple));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.lp-nav { display: flex; align-items: center; gap: 12px; }
.lp-nav-link {
    color: var(--c-text-muted) !important; font-size: var(--fs-sm) !important;
    font-weight: 500; cursor: pointer; padding: 6px 14px;
    border-radius: var(--radius-sm); transition: all 0.2s;
}
.lp-nav-link:hover { color: var(--c-pink) !important; background: rgba(255,46,126,0.10); }
.lp-theme-btn {
    background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.12);
    color: var(--c-text-muted) !important; padding: 6px 14px;
    border-radius: 20px; font-size: var(--fs-xs) !important; cursor: pointer;
}
.lp-cta-btn {
    background: linear-gradient(135deg, var(--c-pink), var(--c-purple));
    color: white !important; padding: 9px 22px; border-radius: 22px;
    font-size: var(--fs-sm) !important; font-weight: 600; cursor: pointer; border: none;
}

[data-testid="stChatMessage"] {
    animation: slideIn 0.3s ease-out; background: var(--c-surface) !important;
    border: 1px solid var(--c-border) !important; border-radius: var(--radius-lg) !important;
    padding: 18px 22px !important; margin-bottom: 14px !important;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] td {
    color: var(--c-text) !important; font-size: var(--fs-base) !important; line-height: 1.75 !important;
}
[data-testid="stChatMessage"] strong,
[data-testid="stChatMessage"] b { color: #f8f2ff !important; font-weight: 600; }
[data-testid="stChatMessage"] code {
    background: rgba(138,43,226,0.15) !important; color: #c8a8ff !important;
    padding: 2px 6px; border-radius: 4px; font-size: var(--fs-sm) !important;
}
@keyframes slideIn {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}

.stButton > button {
    background: linear-gradient(135deg, var(--c-pink) 0%, var(--c-purple) 100%) !important;
    color: #fff !important; border: none !important; border-radius: var(--radius-md) !important;
    padding: 10px 24px !important; font-family: 'Inter', sans-serif !important;
    font-size: var(--fs-sm) !important; font-weight: 600 !important;
    letter-spacing: 0.3px !important; transition: all 0.3s ease !important;
    cursor: pointer !important; white-space: nowrap !important;
}
.stButton > button:hover { transform: translateY(-2px) !important; }
section[data-testid="stSidebar"] .stButton > button {
    white-space: normal !important; word-break: break-word !important;
    width: 100% !important; text-align: left !important;
    font-size: var(--fs-xs) !important; padding: 8px 12px !important;
    line-height: 1.4 !important; min-height: unset !important; height: auto !important;
}

.stSelectbox > div > div,
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--c-surface) !important; color: var(--c-text) !important;
    border-color: var(--c-border-pink) !important; font-size: var(--fs-base) !important;
}
.stTextArea > div > div > textarea::placeholder,
.stTextInput > div > div > input::placeholder { color: var(--c-text-dim) !important; }

.stTabs [data-baseweb="tab"] { color: var(--c-text-muted) !important; font-size: var(--fs-sm) !important; }
.stTabs [data-baseweb="tab"][aria-selected="true"] { color: var(--c-text) !important; font-weight: 600; }

body.font-small  { --fs-base: 13px; --fs-md: 15px; --fs-lg: 17px; }
body.font-large  { --fs-base: 17px; --fs-md: 19px; --fs-lg: 21px; }
</style>
"""

# ============================================================
#  LIGHT THEME CSS
# ============================================================
light_theme = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&family=Inter:wght@300;400;500;600&display=swap');

:root {
    --fs-xs:   11px; --fs-sm:   13px; --fs-base: 15px; --fs-md:   17px;
    --fs-lg:   19px; --fs-xl:   22px; --fs-2xl:  28px; --fs-3xl:  36px; --fs-hero: 60px;
    --c-bg:          #f5f3fa; --c-surface:     #ffffff; --c-surface2:    #faf7ff;
    --c-border:      rgba(0,0,0,0.08); --c-border-pink: rgba(200, 30, 100, 0.22);
    --c-text:        #1a0e30; --c-text-muted:  #3d2a5a; --c-text-dim:    #7060a0; --c-text-hint:   #a090c8;
    --c-pink:        #d41a68; --c-pink-light:  #FF2E7E; --c-purple:      #6b21c8; --c-purple-light:#8A2BE2;
    --c-red-alert:   #dc2626; --c-green:       #16a34a;
    --radius-sm:  8px; --radius-md:  12px; --radius-lg:  18px; --radius-xl:  24px; --radius-pill:60px;
}

[data-font="small"] { --fs-base: 13px; --fs-md: 15px; --fs-lg: 17px; }
[data-font="large"] { --fs-base: 17px; --fs-md: 19px; --fs-lg: 21px; }
*, *::before, *::after { box-sizing: border-box; }

.stApp { background: var(--c-bg) !important; font-family: 'Inter', sans-serif !important; font-size: var(--fs-base) !important; }
.stApp > header { display: none !important; }
#MainMenu, footer { display: none !important; }
.stApp > div { background: var(--c-bg) !important; }

p, span, label, div, li, td, th {
    font-family: 'Inter', sans-serif !important; color: var(--c-text) !important;
    font-size: var(--fs-base) !important; line-height: 1.65 !important;
}
h1, h2, h3, h4, h5, h6 {
    font-family: 'Playfair Display', serif !important; color: var(--c-text) !important; letter-spacing: -0.02em !important;
}
h1 { font-size: var(--fs-hero) !important; } h2 { font-size: var(--fs-3xl) !important; }
h3 { font-size: var(--fs-2xl) !important; } h4 { font-size: var(--fs-xl) !important; }
h5 { font-size: var(--fs-lg) !important; } h6 { font-size: var(--fs-md) !important; }
small, .small { font-size: var(--fs-sm) !important; color: var(--c-text-dim) !important; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #f5f0ff 100%) !important;
    border-right: 1px solid var(--c-border-pink) !important; width: 280px !important;
    box-shadow: 2px 0 12px rgba(0,0,0,0.06);
}
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] div,
section[data-testid="stSidebar"] li { color: var(--c-text-muted) !important; font-size: var(--fs-sm) !important; }
section[data-testid="stSidebar"] strong, section[data-testid="stSidebar"] b { color: var(--c-text) !important; }

.block-container { padding: 0 2rem 5rem 2rem !important; max-width: 1200px !important; margin: 0 auto !important; position: relative; z-index: 1; }

.samsung-footer { text-align: center; padding: 20px; margin-top: 30px; border-top: 1px solid var(--c-border-pink); font-size: var(--fs-xs) !important; color: var(--c-text-dim) !important; }
.samsung-logo { display: inline-flex; align-items: center; gap: 8px; background: rgba(200,30,100,0.07); padding: 6px 16px; border-radius: 30px; margin-bottom: 8px; }
.samsung-text { font-weight: 600; letter-spacing: 1px; color: var(--c-text) !important; }

.about-page { padding: 20px; }
.about-hero { text-align: center; padding: 40px 20px; background: linear-gradient(135deg, rgba(212,26,104,0.06), rgba(107,33,200,0.06)); border: 1px solid var(--c-border-pink); border-radius: var(--radius-xl); margin-bottom: 30px; }
.about-hero-icon { font-size: 64px; margin-bottom: 20px; }
.about-hero-title { font-size: var(--fs-3xl) !important; font-weight: 700; background: linear-gradient(135deg, var(--c-pink), var(--c-purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; font-family: 'Playfair Display', serif !important; }
.about-hero-sub { font-size: var(--fs-md) !important; color: var(--c-text-muted) !important; }
.about-card { background: var(--c-surface); border: 1px solid var(--c-border-pink); border-radius: var(--radius-lg); padding: 25px; margin-bottom: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.04); }
.about-card-title { font-size: var(--fs-xl) !important; font-weight: 700; color: var(--c-pink) !important; margin-bottom: 15px; display: flex; align-items: center; gap: 10px; font-family: 'Playfair Display', serif !important; }
.about-card-text { font-size: var(--fs-base) !important; line-height: 1.75 !important; color: var(--c-text-muted) !important; }
.about-badge-container { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 15px; }
.about-badge-large { background: rgba(200,30,100,0.08); border: 1px solid rgba(200,30,100,0.22); padding: 8px 18px; border-radius: 30px; font-size: var(--fs-sm) !important; color: var(--c-pink) !important; font-weight: 600; }
.about-highlight { color: var(--c-pink) !important; font-weight: 600; }

.demo-section { background: var(--c-surface2); border: 1px solid var(--c-border-pink); border-radius: var(--radius-lg); padding: 20px; margin: 20px 0; }
.demo-title { font-size: var(--fs-sm) !important; font-weight: 700; color: var(--c-pink) !important; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; }
.demo-grid { display: grid; grid-template-columns: repeat(2,1fr); gap: 12px; }
.demo-question { background: var(--c-surface); border: 1px solid rgba(200,30,100,0.18); border-radius: var(--radius-md); padding: 14px; cursor: pointer; transition: all 0.2s ease; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
.demo-question:hover { background: rgba(200,30,100,0.05); border-color: var(--c-pink); transform: translateX(4px); box-shadow: 0 4px 12px rgba(200,30,100,0.12); }
.demo-category { font-size: var(--fs-xs) !important; color: var(--c-pink) !important; margin-bottom: 6px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
.demo-text { font-size: var(--fs-sm) !important; line-height: 1.55 !important; color: var(--c-text-muted) !important; }

.an-welcome { text-align: center; padding: 20px; animation: fadeInUp 0.6s ease-out; }
@keyframes fadeInUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
.an-welcome-icon { font-size: 56px; margin-bottom: 15px; animation: bounce 2s infinite; }
@keyframes bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
.an-welcome-title { font-size: var(--fs-2xl) !important; font-weight: 700; background: linear-gradient(135deg, var(--c-pink), var(--c-purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; font-family: 'Playfair Display', serif !important; }
.an-welcome-sub { font-size: var(--fs-base) !important; color: var(--c-text-muted) !important; line-height: 1.7 !important; }

[data-testid="stChatInput"] { background: var(--c-surface) !important; border: 2px solid var(--c-border-pink) !important; border-radius: var(--radius-pill) !important; padding: 4px 8px 4px 24px !important; margin: 20px 0 !important; transition: all 0.3s cubic-bezier(0.4,0,0.2,1) !important; box-shadow: 0 4px 16px rgba(0,0,0,0.06) !important; }
[data-testid="stChatInput"]:hover, [data-testid="stChatInput"]:focus-within { border-color: var(--c-pink) !important; box-shadow: 0 6px 24px rgba(200,30,100,0.18) !important; transform: translateY(-2px); }
[data-testid="stChatInput"] textarea { background: transparent !important; color: var(--c-text) !important; font-size: var(--fs-base) !important; font-weight: 400 !important; padding: 14px 8px !important; font-family: 'Inter', sans-serif !important; }
[data-testid="stChatInput"] textarea::placeholder { color: var(--c-text-hint) !important; font-size: var(--fs-sm) !important; }
[data-testid="stChatInput"] button { background: linear-gradient(135deg, var(--c-pink-light), var(--c-purple-light)) !important; border-radius: 50% !important; width: 44px !important; height: 44px !important; margin: 4px !important; transition: all 0.3s cubic-bezier(0.4,0,0.2,1) !important; }
[data-testid="stChatInput"] button:hover { transform: scale(1.1) rotate(15deg) !important; }

.an-section-header { background: linear-gradient(135deg, rgba(212,26,104,0.07), rgba(107,33,200,0.07)); border: 1px solid var(--c-border-pink); border-radius: var(--radius-lg); padding: 20px 24px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }
.an-header-left { display: flex; align-items: center; gap: 16px; }
.an-icon-box { width: 48px; height: 48px; background: linear-gradient(135deg, rgba(212,26,104,0.10), rgba(107,33,200,0.10)); border: 1px solid var(--c-border-pink); border-radius: var(--radius-md); display: flex; align-items: center; justify-content: center; font-size: 24px; }
.an-feature-title { font-size: var(--fs-xl) !important; font-weight: 700; color: var(--c-text) !important; font-family: 'Playfair Display', serif !important; }
.an-feature-sub { font-size: var(--fs-xs) !important; color: var(--c-text-dim) !important; }
.an-mode-chip { display: inline-block; background: rgba(200,30,100,0.10); color: var(--c-pink) !important; padding: 2px 10px; border-radius: 12px; font-size: var(--fs-xs) !important; font-weight: 700; }

.sb-pad { padding: 0 12px; }
.an-user-card { background: linear-gradient(135deg, rgba(212,26,104,0.07), rgba(107,33,200,0.07)); border: 1px solid var(--c-border-pink); border-radius: var(--radius-md); padding: 14px; margin: 16px 0; display: flex; align-items: center; gap: 12px; }
.an-avatar { width: 44px; height: 44px; background: linear-gradient(135deg, var(--c-pink-light), var(--c-purple-light)); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 700; color: white !important; flex-shrink: 0; }
.an-uname { font-size: var(--fs-base) !important; font-weight: 700; color: var(--c-text) !important; }
.an-ustatus { font-size: var(--fs-xs) !important; color: var(--c-green) !important; }
.an-nav-label { font-size: var(--fs-xs) !important; color: var(--c-pink) !important; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin: 20px 0 12px; display: block; }

.an-hotlines { background: rgba(220,38,38,0.07); border: 1px solid rgba(220,38,38,0.22); border-radius: var(--radius-md); padding: 14px; margin-top: 20px; }
.an-hotlines-title { font-size: var(--fs-xs) !important; font-weight: 700; color: var(--c-red-alert) !important; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
.an-hotline-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(220,38,38,0.10); }
.an-hotline-row:last-child { border-bottom: none; }
.an-hotline-label { font-size: var(--fs-sm) !important; color: var(--c-text-muted) !important; }
.an-hotline-num { font-size: var(--fs-sm) !important; color: var(--c-red-alert) !important; font-weight: 700; }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #e8e0f5; }
::-webkit-scrollbar-thumb { background: linear-gradient(135deg, var(--c-pink-light), var(--c-purple-light)); border-radius: 10px; }

.lp-header { display: flex; align-items: center; justify-content: space-between; padding: 18px 40px; position: fixed; top: 0; left: 0; right: 0; z-index: 999; background: rgba(255,255,255,0.96); backdrop-filter: blur(20px); border-bottom: 1px solid var(--c-border-pink); box-shadow: 0 2px 20px rgba(0,0,0,0.06); }
.lp-logo { display: flex; align-items: center; gap: 10px; }
.lp-logo-text { font-family: 'Playfair Display', serif; font-size: var(--fs-lg) !important; font-weight: 700; background: linear-gradient(135deg, var(--c-pink), var(--c-purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.lp-nav { display: flex; align-items: center; gap: 12px; }
.lp-nav-link { color: var(--c-text-dim) !important; font-size: var(--fs-sm) !important; font-weight: 500; cursor: pointer; padding: 6px 14px; border-radius: var(--radius-sm); transition: all 0.2s; }
.lp-nav-link:hover { color: var(--c-pink) !important; background: rgba(200,30,100,0.07); }
.lp-theme-btn { background: #f0e8ff; border: 1px solid #d8c8f8; color: var(--c-text-dim) !important; padding: 6px 14px; border-radius: 20px; font-size: var(--fs-xs) !important; cursor: pointer; }
.lp-cta-btn { background: linear-gradient(135deg, var(--c-pink-light), var(--c-purple-light)); color: white !important; padding: 9px 22px; border-radius: 22px; font-size: var(--fs-sm) !important; font-weight: 600; cursor: pointer; border: none; }

[data-testid="stChatMessage"] { animation: slideIn 0.3s ease-out; background: var(--c-surface) !important; border: 1px solid var(--c-border) !important; border-radius: var(--radius-lg) !important; padding: 18px 22px !important; margin-bottom: 14px !important; box-shadow: 0 2px 10px rgba(0,0,0,0.04); }
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li, [data-testid="stChatMessage"] td { color: var(--c-text) !important; font-size: var(--fs-base) !important; line-height: 1.75 !important; }
[data-testid="stChatMessage"] strong, [data-testid="stChatMessage"] b { color: #0e0820 !important; font-weight: 700; }
[data-testid="stChatMessage"] code { background: rgba(107,33,200,0.08) !important; color: var(--c-purple) !important; padding: 2px 6px; border-radius: 4px; font-size: var(--fs-sm) !important; }
@keyframes slideIn { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }

.stButton > button { background: linear-gradient(135deg, var(--c-pink-light) 0%, var(--c-purple-light) 100%) !important; color: #fff !important; border: none !important; border-radius: var(--radius-md) !important; padding: 10px 24px !important; font-family: 'Inter', sans-serif !important; font-size: var(--fs-sm) !important; font-weight: 600 !important; letter-spacing: 0.3px !important; transition: all 0.3s ease !important; cursor: pointer !important; white-space: nowrap !important; }
.stButton > button:hover { transform: translateY(-2px) !important; }
section[data-testid="stSidebar"] .stButton > button { background: rgba(200,30,100,0.08) !important; color: var(--c-pink) !important; box-shadow: none !important; white-space: normal !important; word-break: break-word !important; width: 100% !important; text-align: left !important; font-size: var(--fs-xs) !important; padding: 8px 12px !important; line-height: 1.4 !important; min-height: unset !important; height: auto !important; }
section[data-testid="stSidebar"] .stButton > button:hover { background: linear-gradient(135deg, var(--c-pink-light), var(--c-purple-light)) !important; color: white !important; }

.stSelectbox > div > div, .stTextInput > div > div > input, .stTextArea > div > div > textarea { background: var(--c-surface) !important; color: var(--c-text) !important; border-color: var(--c-border-pink) !important; font-size: var(--fs-base) !important; }
.stTextArea > div > div > textarea::placeholder, .stTextInput > div > div > input::placeholder { color: var(--c-text-hint) !important; }
.stTabs [data-baseweb="tab"] { color: var(--c-text-muted) !important; font-size: var(--fs-sm) !important; }
.stTabs [data-baseweb="tab"][aria-selected="true"] { color: var(--c-text) !important; font-weight: 700; }
body.font-small { --fs-base: 13px; --fs-md: 15px; --fs-lg: 17px; }
body.font-large { --fs-base: 17px; --fs-md: 19px; --fs-lg: 21px; }
</style>
"""

# Apply theme
if st.session_state.theme == "dark":
    st.markdown(dark_theme, unsafe_allow_html=True)
else:
    st.markdown(light_theme, unsafe_allow_html=True)

# Font size injection
font_size = st.session_state.get("font_size", "medium")
if font_size != "medium":
    st.markdown(f"""
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        document.body.classList.remove('font-small', 'font-large');
        if ("{font_size}" === "small") document.body.classList.add('font-small');
        if ("{font_size}" === "large") document.body.classList.add('font-large');
    }});
    </script>
    """, unsafe_allow_html=True)

# ============================================================
#  HELPER FUNCTIONS
# ============================================================
def show_toast(message, duration=3):
    toast_html = f"""
    <div style="position: fixed; bottom: 20px; right: 20px; background: linear-gradient(135deg, #FF2E7E, #8A2BE2); color: white; padding: 12px 24px; border-radius: 12px; z-index: 1000; animation: fadeInUp 0.3s ease-out;">
        {message}
    </div>
    """
    st.markdown(toast_html, unsafe_allow_html=True)

def create_pdf(text, title="Legal Document"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    clean_text = text.encode('latin-1', 'ignore').decode('latin-1')
    for line in clean_text.split('\n'):
        pdf.multi_cell(0, 10, txt=line)
        pdf.ln(2)
    pdf.set_y(-20)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 10, f"Generated by Awaz-e-Nisa - {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        return tmp.name

def extract_text_from_pdf(file_content):
    try:
        with pdfplumber.open(file_content) as pdf:
            text = ""
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                text += f"--- Page {i+1} ---\n{page_text}\n"
            return text.strip() or "No readable text found."
    except Exception as e:
        return f"Error: {str(e)}"

def extract_text_from_image(uploaded_file):
    try:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.medianBlur(gray, 3)
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(thresh, lang='eng+urd')
        return text.strip() if text else "No text detected."
    except Exception as e:
        return f"OCR failed: {str(e)}"

def new_session_id():
    return str(uuid.uuid4())[:8]

def get_session_title(messages):
    for m in messages:
        if m["role"] == "user":
            txt = m["content"][:40]
            if any(word in txt.lower() for word in ['talaq', 'divorce']):
                return f"💔 {txt[:35]}..."
            elif any(word in txt.lower() for word in ['custody', 'bacha', 'child']):
                return f"👶 {txt[:35]}..."
            elif any(word in txt.lower() for word in ['harassment', 'cyber']):
                return f"🛡️ {txt[:35]}..."
            else:
                return f"💬 {txt[:35]}..."
    return "💬 New conversation"

def create_new_chat():
    sid = new_session_id()
    st.session_state.active_session_id = sid
    st.session_state.messages = []
    st.session_state.last_query = ""
    st.session_state.active_feature = "Legal Chat"
    st.session_state.show_analysis = False
    st.session_state.analysis_result = None
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = {}
    st.session_state.chat_sessions[sid] = {
        "title": "💬 New conversation",
        "messages": [],
        "ts": datetime.now().strftime("%H:%M"),
        "date": datetime.now().strftime("%Y-%m-%d")
    }

def save_current_session():
    sid = st.session_state.active_session_id
    if sid and sid in st.session_state.get("chat_sessions", {}):
        st.session_state.chat_sessions[sid]["messages"] = list(st.session_state.messages)
        if st.session_state.messages:
            st.session_state.chat_sessions[sid]["title"] = get_session_title(st.session_state.messages)
        st.session_state.chat_sessions[sid]["ts"] = datetime.now().strftime("%H:%M")

def load_session(sid):
    sessions = st.session_state.get("chat_sessions", {})
    if sid in sessions:
        save_current_session()
        st.session_state.active_session_id = sid
        st.session_state.messages = list(sessions[sid]["messages"])
        st.session_state.active_feature = "Legal Chat"
        st.session_state.show_analysis = False
        st.session_state.analysis_result = None

def get_recent_sessions(n=5):
    sessions = st.session_state.get("chat_sessions", {})
    active = st.session_state.active_session_id
    items = [(k, v) for k, v in sessions.items() if k != active and v.get("messages")]
    items.sort(key=lambda x: x[1].get("ts", ""), reverse=True)
    return items[:n]

def delete_session(sid):
    if sid in st.session_state.chat_sessions:
        del st.session_state.chat_sessions[sid]
        if st.session_state.active_session_id == sid:
            create_new_chat()
        return True
    return False

def show_about_page():
    st.markdown("""
    <div class="about-page">
        <div class="about-hero">
            <div class="about-hero-icon">🌸</div>
            <div class="about-hero-title">About Awaz-e-Nisa</div>
            <div class="about-hero-sub">آوازِ نسواں - "Voice of Women"</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="about-card">
        <div class="about-card-title"><span>⚖️</span> Our Mission</div>
        <div class="about-card-text">
            <strong class="about-highlight">Awaz-e-Nisa</strong> is a dedicated AI legal assistant designed specifically for
            <strong class="about-highlight">Pakistani women</strong> and <strong class="about-highlight">legal professionals</strong>
            working on family cases. We believe every woman deserves access to clear, accurate, and practical legal guidance.
        </div>
    </div>
    <div class="about-card">
        <div class="about-card-title"><span>🇵🇰</span> For Women</div>
        <div class="about-card-text">
            Get instant, clear answers about your legal rights - from divorce and custody to maintenance and inheritance.
            No complex legal jargon, just practical guidance you can understand and act upon.
        </div>
    </div>
    <div class="about-card">
        <div class="about-card-title"><span>⚖️</span> For Lawyers & Legal Pros</div>
        <div class="about-card-text">
            Quickly analyze case merits, prepare counter arguments, estimate timelines, and generate legal drafts.
            Save hours of research time with AI-powered legal assistance.
        </div>
    </div>
    <div class="about-card">
        <div class="about-card-title"><span>✨</span> What We Cover</div>
        <div class="about-badge-container">
            <span class="about-badge-large">🏛️ Family Law</span>
            <span class="about-badge-large">📝 Khula & Talaq</span>
            <span class="about-badge-large">👶 Child Custody</span>
            <span class="about-badge-large">💰 Haq Mehr</span>
            <span class="about-badge-large">🏠 Maintenance</span>
            <span class="about-badge-large">🛡️ Domestic Violence</span>
            <span class="about-badge-large">💻 Cybercrime</span>
            <span class="about-badge-large">🏢 Workplace Harassment</span>
            <span class="about-badge-large">📜 Inheritance</span>
            <span class="about-badge-large">👨‍👩‍👧 Guardianship</span>
            <span class="about-badge-large">🏘️ Property Rights</span>
            <span class="about-badge-large">⚖️ Constitutional Rights</span>
        </div>
    </div>
    <div class="about-card">
        <div class="about-card-title"><span>💡</span> How It Works</div>
        <div class="about-card-text">
            <strong>1. Ask a Question</strong> - Type your legal question in simple language<br><br>
            <strong>2. Get Instant Analysis</strong> - Receive clear, actionable legal guidance<br><br>
            <strong>3. Deep Dive</strong> - Use our tools to analyze case merits, counter arguments, timelines, and legal drafts<br><br>
            <strong>4. Take Action</strong> - Download legal documents and know your next steps
        </div>
    </div>
    <div class="about-card">
        <div class="about-card-title"><span>🔒</span> Privacy & Security</div>
        <div class="about-card-text">
            Your conversations are private and secure. We do not share your personal information or case details with any third party.
        </div>
    </div>
    """, unsafe_allow_html=True)

HOTLINES_HTML = """
<div class="an-hotlines">
    <div class="an-hotlines-title">🆘 EMERGENCY HELPLINES</div>
    <div class="an-hotline-row"><span class="an-hotline-label">🚨 FIA Cybercrime</span><span class="an-hotline-num">1991</span></div>
    <div class="an-hotline-row"><span class="an-hotline-label">⚖️ Ministry of Human Rights</span><span class="an-hotline-num">1099</span></div>
    <div class="an-hotline-row"><span class="an-hotline-label">👮 Women Safety (Police)</span><span class="an-hotline-num">15</span></div>
    <div class="an-hotline-row"><span class="an-hotline-label">💻 Digital Rights Foundation</span><span class="an-hotline-num">0800-39393</span></div>
    <div class="an-hotline-row"><span class="an-hotline-label">❤️ Rozan Helpline</span><span class="an-hotline-num">0345-2222222</span></div>
</div>
"""

FEATURES = {
    "⚡ Legal Chat": "Legal Chat",
    "📊 Case Merits": "Case Merits",
    "⚔ Counter Arguments": "Counter Arguments",
    "📅 Timeline Estimator": "Timeline Estimator",
    "📄 Legal Draft": "Legal Draft",
    "🌸 About Awaz-e-Nisa": "About",
}

FEATURE_ICONS = {
    "Legal Chat": "⚡",
    "Case Merits": "📊",
    "Counter Arguments": "⚔",
    "Timeline Estimator": "📅",
    "Legal Draft": "📄",
    "About": "🌸",
}

def ensure_session():
    if not st.session_state.active_session_id:
        create_new_chat()

# ============================================================
#  LANDING PAGE  —  IMPROVED
# ============================================================
# ============================================================
#  LANDING PAGE  —  IMPROVED WITH LARGER TEXT & WHITE BUTTONS
# ============================================================
if not st.session_state.logged_in and st.session_state.show_landing:
    is_dark = st.session_state.theme == "dark"

    # ── Sticky nav ──────────────────────────────────────────




    # ── HERO SECTION WITH LARGER TEXT ───────────────────────
    st.markdown("""
    <div style="text-align:center;padding:80px 24px 60px;position:relative;overflow:hidden;">
      <div style="position:absolute;top:-100px;left:50%;transform:translateX(-50%);
                  width:700px;height:700px;border-radius:50%;
                  background:radial-gradient(circle,rgba(138,43,226,0.15) 0%,rgba(255,46,126,0.08) 45%,transparent 70%);
                  pointer-events:none;"></div>

      <div style="display:inline-flex;align-items:center;gap:10px;
                  background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.35);
                  padding:8px 24px;border-radius:40px;font-size:13px;font-weight:700;
                  color:#ff7ab8;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:32px;">
        <span style="width:8px;height:8px;border-radius:50%;background:#FF2E7E;
                     display:inline-block;"></span>
        Samsung Innovation Campus · Pakistan
      </div>

      <div style="font-family:'Playfair Display',serif;font-size:clamp(48px,8vw,80px);
                  font-weight:700;line-height:1.1;margin-bottom:24px;color:#f5eeff;">
        Legal Rights for Every<br>
        <span style="background:linear-gradient(135deg,#FF2E7E,#c44dff);
                     -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
          Pakistani Woman
        </span>
      </div>

      <p style="font-size:20px;line-height:1.8;max-width:580px;margin:0 auto 24px;color:#8878a8;">
        AI-powered legal assistant trained on
        <strong style="color:#c090e8;font-size:20px;">164 Pakistani law documents.</strong><br>
         Empowering citizens with legal literacy and assisting Legal Professionals with rapid case analysis.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Hero CTA buttons with white text (force white color)
    st.markdown("""
    <style>
    /* Force white text on all buttons in both themes */
    .stButton > button {
        color: white !important;
    }
    .stButton > button:hover {
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    _, hc1, hc2, _ = st.columns([1, 1.3, 1.3, 1])
    with hc1:
        if st.button("Start Free Consultation  →", use_container_width=True, key="hero_cta"):
            st.session_state.show_landing = False
            st.rerun()
    with hc2:
        if st.button("Try as Guest", use_container_width=True, key="hero_guest"):
            st.session_state.logged_in = True
            st.session_state.username = "Guest"
            st.session_state.show_landing = False
            create_new_chat()
            st.rerun()

    # ── TRUST BAR ──
    st.markdown("""
    <div style="display:flex;border:1px solid rgba(255,46,126,0.18);border-radius:20px;
                overflow:hidden;background:rgba(255,255,255,0.025);margin:40px 0 64px;">
      <div style="flex:1;text-align:center;padding:28px 16px;border-right:1px solid rgba(255,46,126,0.12);">
        <div style="font-size:36px;font-weight:800;background:linear-gradient(135deg,#FF2E7E,#c44dff);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    font-family:'Playfair Display',serif;">164</div>
        <div style="font-size:12px;color:#806898;text-transform:uppercase;
                    letter-spacing:1px;font-weight:600;margin-top:6px;">Law Documents</div>
      </div>
      <div style="flex:1;text-align:center;padding:28px 16px;border-right:1px solid rgba(255,46,126,0.12);">
        <div style="font-size:36px;font-weight:800;background:linear-gradient(135deg,#FF2E7E,#c44dff);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    font-family:'Playfair Display',serif;">6+</div>
        <div style="font-size:12px;color:#806898;text-transform:uppercase;
                    letter-spacing:1px;font-weight:600;margin-top:6px;">Legal Domains</div>
      </div>
      <div style="flex:1;text-align:center;padding:28px 16px;border-right:1px solid rgba(255,46,126,0.12);">
        <div style="font-size:36px;font-weight:800;background:linear-gradient(135deg,#FF2E7E,#c44dff);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    font-family:'Playfair Display',serif;">2</div>
        <div style="font-size:12px;color:#806898;text-transform:uppercase;
                    letter-spacing:1px;font-weight:600;margin-top:6px;">Languages</div>
      </div>
      <div style="flex:1;text-align:center;padding:28px 16px;border-right:1px solid rgba(255,46,126,0.12);">
        <div style="font-size:36px;font-weight:800;background:linear-gradient(135deg,#FF2E7E,#c44dff);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    font-family:'Playfair Display',serif;">5</div>
        <div style="font-size:12px;color:#806898;text-transform:uppercase;
                    letter-spacing:1px;font-weight:600;margin-top:6px;">AI Tools</div>
      </div>
      <div style="flex:1;text-align:center;padding:28px 16px;">
        <div style="font-size:36px;font-weight:800;background:linear-gradient(135deg,#FF2E7E,#c44dff);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    font-family:'Playfair Display',serif;">87%</div>
        <div style="font-size:12px;color:#806898;text-transform:uppercase;
                    letter-spacing:1px;font-weight:600;margin-top:6px;">Accuracy Rate</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── FEATURES SECTION ──
    st.markdown("""
    <div style="margin-bottom:72px;">
      <div style="display:inline-block;background:rgba(255,46,126,0.12);
                  border:1px solid rgba(255,46,126,0.28);color:#ff7ab8;padding:6px 18px;
                  border-radius:24px;font-size:12px;font-weight:700;letter-spacing:1px;
                  text-transform:uppercase;margin-bottom:18px;">✦ Features</div>
      <div style="font-family:'Playfair Display',serif;font-size:44px;font-weight:700;
                  color:#f5eeff;margin-bottom:14px;">Everything You Need to Know Your Rights</div>
      <p style="font-size:17px;color:#8878a8;line-height:1.75;max-width:560px;margin-bottom:40px;">
        From instant legal Q&amp;A to professional court documents — all powered by AI trained on Pakistani law.
      </p>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px;">
        <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
                    border-radius:20px;padding:28px;transition:all .25s;">
          <div style="width:52px;height:52px;border-radius:14px;background:rgba(255,46,126,0.12);
                      border:1px solid rgba(255,46,126,0.25);display:flex;align-items:center;
                      justify-content:center;font-size:24px;margin-bottom:18px;">⚡</div>
          <div style="font-size:18px;font-weight:700;color:#f0e8ff;margin-bottom:10px;">Instant Legal Chat</div>
          <div style="font-size:14px;color:#7868a0;line-height:1.7;">Ask in Urdu or English. Get cited answers with section numbers from MFLO, PECA, and more.</div>
        </div>
        <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
                    border-radius:20px;padding:28px;">
          <div style="width:52px;height:52px;border-radius:14px;background:rgba(255,46,126,0.12);
                      border:1px solid rgba(255,46,126,0.25);display:flex;align-items:center;
                      justify-content:center;font-size:24px;margin-bottom:18px;">📊</div>
          <div style="font-size:18px;font-weight:700;color:#f0e8ff;margin-bottom:10px;">Case Merits Analysis</div>
          <div style="font-size:14px;color:#7868a0;line-height:1.7;">Understand legal strengths and weaknesses of your case before approaching a lawyer.</div>
        </div>
        <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
                    border-radius:20px;padding:28px;">
          <div style="width:52px;height:52px;border-radius:14px;background:rgba(255,46,126,0.12);
                      border:1px solid rgba(255,46,126,0.25);display:flex;align-items:center;
                      justify-content:center;font-size:24px;margin-bottom:18px;">⚔</div>
          <div style="font-size:18px;font-weight:700;color:#f0e8ff;margin-bottom:10px;">Counter Arguments</div>
          <div style="font-size:14px;color:#7868a0;line-height:1.7;">Know opposing arguments in advance so you're fully prepared before your hearing.</div>
        </div>
        <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
                    border-radius:20px;padding:28px;">
          <div style="width:52px;height:52px;border-radius:14px;background:rgba(255,46,126,0.12);
                      border:1px solid rgba(255,46,126,0.25);display:flex;align-items:center;
                      justify-content:center;font-size:24px;margin-bottom:18px;">📅</div>
          <div style="font-size:18px;font-weight:700;color:#f0e8ff;margin-bottom:10px;">Timeline Estimator</div>
          <div style="font-size:14px;color:#7868a0;line-height:1.7;">Stage-by-stage timeline for your case based on Pakistani court procedures.</div>
        </div>
        <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
                    border-radius:20px;padding:28px;">
          <div style="width:52px;height:52px;border-radius:14px;background:rgba(255,46,126,0.12);
                      border:1px solid rgba(255,46,126,0.25);display:flex;align-items:center;
                      justify-content:center;font-size:24px;margin-bottom:18px;">📄</div>
          <div style="font-size:18px;font-weight:700;color:#f0e8ff;margin-bottom:10px;">Legal Draft Generator</div>
          <div style="font-size:14px;color:#7868a0;line-height:1.7;">Generate Khula petitions, custody applications, and police complaints as PDF.</div>
        </div>
        <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
                    border-radius:20px;padding:28px;">
          <div style="width:52px;height:52px;border-radius:14px;background:rgba(255,46,126,0.12);
                      border:1px solid rgba(255,46,126,0.25);display:flex;align-items:center;
                      justify-content:center;font-size:24px;margin-bottom:18px;">📎</div>
          <div style="font-size:18px;font-weight:700;color:#f0e8ff;margin-bottom:10px;">Document Analysis</div>
          <div style="font-size:14px;color:#7868a0;line-height:1.7;">Upload Nikah Nama or court notices — AI explains what it means for you.</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── TRAINING DATA SECTION ──
    st.markdown("""
    <div style="margin-bottom:72px;background:rgba(138,43,226,0.05);
                border-radius:28px;padding:48px 36px;">
      <div style="display:inline-block;background:rgba(255,46,126,0.12);
                  border:1px solid rgba(255,46,126,0.28);color:#ff7ab8;padding:6px 18px;
                  border-radius:24px;font-size:12px;font-weight:700;letter-spacing:1px;
                  text-transform:uppercase;margin-bottom:18px;"> Training Data</div>
      <div style="font-family:'Playfair Display',serif;font-size:44px;font-weight:700;
                  color:#f5eeff;margin-bottom:14px;">Trained on 164 Pakistani Law Documents</div>
      <p style="font-size:17px;color:#8878a8;line-height:1.75;max-width:560px;margin-bottom:40px;">
        Our RAG system retrieves answers directly from verified legal texts — not hallucination.
      </p>
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:20px;">
        <div style="background:rgba(138,43,226,0.10);border:1px solid rgba(138,43,226,0.20);
                    border-radius:20px;padding:28px;">
          <div style="font-size:48px;font-weight:800;color:#b070f8;margin-bottom:10px;
                      font-family:'Playfair Display',serif;">50+</div>
          <div style="font-size:16px;font-weight:700;color:#c0a8e8;margin-bottom:8px;">Family Law Texts</div>
          <div style="font-size:14px;color:#7868a0;line-height:1.7;">Muslim Family Laws Ordinance 1961, Family Courts Act 1964, Child Marriage Restraint Act, Guardians &amp; Wards Act 1890</div>
          <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:18px;">
            <span style="background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.22);color:#ff8ec0;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">MFLO 1961</span>
            <span style="background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.22);color:#ff8ec0;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">FCA 1964</span>
            <span style="background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.22);color:#ff8ec0;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">CMRA</span>
            <span style="background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.22);color:#ff8ec0;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">GWA 1890</span>
          </div>
        </div>
        <div style="background:rgba(138,43,226,0.10);border:1px solid rgba(138,43,226,0.20);
                    border-radius:20px;padding:28px;">
          <div style="font-size:48px;font-weight:800;color:#b070f8;margin-bottom:10px;
                      font-family:'Playfair Display',serif;">40+</div>
          <div style="font-size:16px;font-weight:700;color:#c0a8e8;margin-bottom:8px;">Cybercrime &amp; Digital Rights</div>
          <div style="font-size:14px;color:#7868a0;line-height:1.7;">Prevention of Electronic Crimes Act 2016, FIA Cybercrime Wing procedures, Digital Rights Foundation guidelines</div>
          <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:18px;">
            <span style="background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.22);color:#ff8ec0;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">PECA 2016</span>
            <span style="background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.22);color:#ff8ec0;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">FIA Rules</span>
            <span style="background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.22);color:#ff8ec0;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">NR3C</span>
          </div>
        </div>
        <div style="background:rgba(138,43,226,0.10);border:1px solid rgba(138,43,226,0.20);
                    border-radius:20px;padding:28px;">
          <div style="font-size:48px;font-weight:800;color:#b070f8;margin-bottom:10px;
                      font-family:'Playfair Display',serif;">35+</div>
          <div style="font-size:16px;font-weight:700;color:#c0a8e8;margin-bottom:8px;">Workplace &amp; Rights Laws</div>
          <div style="font-size:14px;color:#7868a0;line-height:1.7;">Protection Against Harassment Act 2010, Provincial Labour Laws, Women Protection Acts across all 4 provinces</div>
          <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:18px;">
            <span style="background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.22);color:#ff8ec0;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">HAW 2010</span>
            <span style="background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.22);color:#ff8ec0;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">Labour Laws</span>
            <span style="background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.22);color:#ff8ec0;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">WPA Punjab</span>
          </div>
        </div>
        <div style="background:rgba(138,43,226,0.10);border:1px solid rgba(138,43,226,0.20);
                    border-radius:20px;padding:28px;">
          <div style="font-size:48px;font-weight:800;color:#b070f8;margin-bottom:10px;
                      font-family:'Playfair Display',serif;">39+</div>
          <div style="font-size:16px;font-weight:700;color:#c0a8e8;margin-bottom:8px;">Inheritance &amp; Property</div>
          <div style="font-size:14px;color:#7868a0;line-height:1.7;">Muslim Personal Law Application Act, Succession Act — covering Haq Mehr, Wirasat, and property rights</div>
          <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:18px;">
            <span style="background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.22);color:#ff8ec0;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">Shariat Act</span>
            <span style="background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.22);color:#ff8ec0;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">Succession</span>
            <span style="background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.22);color:#ff8ec0;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">Haq Mehr</span>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── HOW IT WORKS SECTION ──
    st.markdown("""
    <div style="margin-bottom:72px;">
      <div style="display:inline-block;background:rgba(255,46,126,0.12);
                  border:1px solid rgba(255,46,126,0.28);color:#ff7ab8;padding:6px 18px;
                  border-radius:24px;font-size:12px;font-weight:700;letter-spacing:1px;
                  text-transform:uppercase;margin-bottom:18px;">💡 How It Works</div>
      <div style="font-family:'Playfair Display',serif;font-size:44px;font-weight:700;
                  color:#f5eeff;margin-bottom:14px;">From Question to Legal Action in Minutes</div>
      <p style="font-size:17px;color:#8878a8;line-height:1.75;max-width:560px;margin-bottom:40px;">
        No lawyer needed for your first consultation. Just type and get answers.
      </p>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:20px;">
        <div style="text-align:center;padding:32px 20px;background:rgba(255,255,255,0.03);
                    border:1px solid rgba(255,255,255,0.08);border-radius:20px;">
          <div style="width:48px;height:48px;border-radius:50%;
                      background:linear-gradient(135deg,#FF2E7E,#8A2BE2);
                      display:flex;align-items:center;justify-content:center;
                      font-size:18px;font-weight:800;color:white;margin:0 auto 16px;">1</div>
          <div style="font-size:16px;font-weight:700;color:#d8c8f0;margin-bottom:10px;">Ask Your Question</div>
          <div style="font-size:14px;color:#7060a0;line-height:1.7;">Type in Roman Urdu, or English. No legal knowledge needed.</div>
        </div>
        <div style="text-align:center;padding:32px 20px;background:rgba(255,255,255,0.03);
                    border:1px solid rgba(255,255,255,0.08);border-radius:20px;">
          <div style="width:48px;height:48px;border-radius:50%;
                      background:linear-gradient(135deg,#FF2E7E,#8A2BE2);
                      display:flex;align-items:center;justify-content:center;
                      font-size:18px;font-weight:800;color:white;margin:0 auto 16px;">2</div>
          <div style="font-size:16px;font-weight:700;color:#d8c8f0;margin-bottom:10px;">AI Searches the Law</div>
          <div style="font-size:14px;color:#7060a0;line-height:1.7;">RAG finds relevant sections from 164 verified Pakistani legal documents.</div>
        </div>
        <div style="text-align:center;padding:32px 20px;background:rgba(255,255,255,0.03);
                    border:1px solid rgba(255,255,255,0.08);border-radius:20px;">
          <div style="width:48px;height:48px;border-radius:50%;
                      background:linear-gradient(135deg,#FF2E7E,#8A2BE2);
                      display:flex;align-items:center;justify-content:center;
                      font-size:18px;font-weight:800;color:white;margin:0 auto 16px;">3</div>
          <div style="font-size:16px;font-weight:700;color:#d8c8f0;margin-bottom:10px;">Get Cited Answers</div>
          <div style="font-size:14px;color:#7060a0;line-height:1.7;">Guidance with exact section numbers like "MFLO Section 6" so you can verify.</div>
        </div>
        <div style="text-align:center;padding:32px 20px;background:rgba(255,255,255,0.03);
                    border:1px solid rgba(255,255,255,0.08);border-radius:20px;">
          <div style="width:48px;height:48px;border-radius:50%;
                      background:linear-gradient(135deg,#FF2E7E,#8A2BE2);
                      display:flex;align-items:center;justify-content:center;
                      font-size:18px;font-weight:800;color:white;margin:0 auto 16px;">4</div>
          <div style="font-size:16px;font-weight:700;color:#d8c8f0;margin-bottom:10px;">Download &amp; Act</div>
          <div style="font-size:14px;color:#7060a0;line-height:1.7;">Generate legal drafts as PDF, know your timeline, walk into court prepared.</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── CTA SECTION ──
    st.markdown("""
    <div style="border-radius:28px;padding:72px 48px;text-align:center;
                background:linear-gradient(135deg,rgba(255,46,126,0.12),rgba(138,43,226,0.16));
                border:1px solid rgba(255,46,126,0.25);position:relative;overflow:hidden;
                margin-bottom:48px;">
      <div style="position:absolute;font-size:200px;opacity:0.04;
                  top:-30px;right:40px;line-height:1;pointer-events:none;color:#FF2E7E;">⚖</div>
      <div style="font-family:'Playfair Display',serif;font-size:48px;font-weight:700;
                  color:#f5eeff;margin-bottom:18px;">Your Voice. Your Rights. Your Law.</div>
      <p style="font-size:17px;color:#8878a8;margin-bottom:48px;max-width:520px;margin-left:auto;margin-right:auto;">
        Join thousands of Pakistani women who've used Awaz-e-Nisa to understand their legal rights.
      </p>
    </div>
    """, unsafe_allow_html=True)

    _, cc1, cc2, _ = st.columns([1, 1.2, 1.2, 1])
    with cc1:
        if st.button("⚖️  Get Started Free", use_container_width=True, key="cta_start"):
            st.session_state.show_landing = False
            st.rerun()
    with cc2:
        if st.button("👀  Try as Guest", use_container_width=True, key="cta_guest"):
            st.session_state.logged_in = True
            st.session_state.username = "Guest"
            st.session_state.show_landing = False
            create_new_chat()
            st.rerun()

    # ── FOOTER ──
    st.markdown("""
    <div style="border-top:1px solid rgba(255,46,126,0.12);padding:40px 0;
                display:flex;justify-content:space-between;align-items:center;
                flex-wrap:wrap;gap:24px;margin-top:40px;">
      <div style="display:flex;align-items:center;gap:12px;">
        <span style="font-size:28px;">⚖️</span>
        <div>
          <div style="font-family:'Playfair Display',serif;font-size:18px;font-weight:700;
                      background:linear-gradient(135deg,#FF2E7E,#8A2BE2);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent;">AWAZ-E-NISA</div>
          <div style="font-size:12px;color:#604878;">آوازِ نسواں · Voice of Women</div>
        </div>
      </div>
      <div style="display:flex;gap:28px;flex-wrap:wrap;">
        <span style="font-size:13px;color:#706080;"> Legal Chat</span>
        <span style="font-size:13px;color:#706080;"> Case Merits</span>
        <span style="font-size:13px;color:#706080;"> Counter Args</span>
        <span style="font-size:13px;color:#706080;"> Timeline</span>
        <span style="font-size:13px;color:#706080;"> Legal Draft</span>
      </div>
      <div style="text-align:right;">
        <div style="display:inline-flex;align-items:center;gap:8px;
                    background:rgba(255,46,126,0.08);border:1px solid rgba(255,46,126,0.18);
                    padding:6px 16px;border-radius:24px;margin-bottom:8px;">
          <span style="font-size:11px;color:#805870;font-weight:700;letter-spacing:0.8px;">
            🚀 SAMSUNG INNOVATION CAMPUS
          </span>
        </div>
        <div style="font-size:11px;color:#503860;">© 2026 Awaz-e-Nisa · Pakistan</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
#  LOGIN PAGE
# ============================================================
elif not st.session_state.logged_in and not st.session_state.show_landing:
    h1, h2, h3 = st.columns([1, 6, 1])
    with h1:
        if st.button("← Back", key="login_back"):
            st.session_state.show_landing = True
            st.rerun()
    with h3:
        cur = st.session_state.theme
        if st.button("☀️" if cur == "dark" else "🌙", key="login_theme"):
            st.session_state.theme = "light" if cur == "dark" else "dark"
            st.rerun()

    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; margin-bottom: 32px;">
            <span style="font-size: 64px; display: block; margin-bottom: 16px;">⚖️</span>
            <span style="font-size: 32px; font-weight: 800; background: linear-gradient(135deg, #FF2E7E, #8A2BE2); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">AWAZ-E-NISA</span>
            <span style="font-size: 12px; color: #888; display: block; margin-top: 8px;">Legal AI for Pakistani Women</span>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2 = st.tabs([" Login", " Create Account"])

        with tab1:
            u = st.text_input("Username", placeholder="Enter your username", key="li_u")
            p = st.text_input("Password", type="password", placeholder="Enter your password", key="li_p")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Login →", use_container_width=True, key="btn_login"):
                    if verify_user(u, p):
                        st.session_state.logged_in = True
                        st.session_state.username = u
                        hist = get_chat_history(u)
                        if hist:
                            sid = new_session_id()
                            st.session_state.chat_sessions[sid] = {
                                "title": get_session_title(hist),
                                "messages": hist,
                                "ts": "Earlier",
                                "date": "Previous"
                            }
                            st.session_state.active_session_id = sid
                            st.session_state.messages = hist
                        else:
                            create_new_chat()
                        st.rerun()
                    else:
                        st.error(" Invalid credentials")
            with c2:
                if st.button(" Guest", use_container_width=True, key="btn_guest"):
                    st.session_state.logged_in = True
                    st.session_state.username = "Guest"
                    create_new_chat()
                    st.rerun()

        with tab2:
            nu = st.text_input("Username", placeholder="Choose username", key="reg_u")
            np_ = st.text_input("Password", type="password", placeholder="Create password", key="reg_p")
            if st.button("Create Account →", use_container_width=True, key="btn_reg"):
                if nu and np_:
                    if len(np_) < 4:
                        st.warning(" Password must be at least 4 characters")
                    elif add_user(nu, np_):
                        st.success(" Account created! Please login.")
                    else:
                        st.error(" Username taken")
                else:
                    st.warning(" Fill all fields")

        st.markdown("""
        <div class="samsung-footer">
            <div class="samsung-logo">
                <span class="samsung-icon">🚀</span>
                <span class="samsung-text">SAMSUNG INNOVATION CAMPUS</span>
            </div>
            <div>Powered by Samsung Innovation Campus | Built for Pakistani Women</div>
            <div style="font-size: 9px; margin-top: 5px;">© 2026 Awaz-e-Nisa · All Rights Reserved</div>
        </div>
        """, unsafe_allow_html=True)

# ============================================================
#  MAIN APP
# ============================================================
else:
    ensure_session()

    if "rag" not in st.session_state:
        with st.spinner("🚀 Loading AI model..."):
            from legal_advisor import (rag_chain, merits_chain,
                                       opposition_chain, timeline_chain, draft_chain)
            st.session_state.rag = rag_chain
            st.session_state.m_chain = merits_chain
            st.session_state.o_chain = opposition_chain
            st.session_state.t_chain = timeline_chain
            st.session_state.d_chain = draft_chain
            show_toast("AI model loaded!")

    # SIDEBAR
    with st.sidebar:
        st.markdown("""
        <div style="padding: 20px 0; text-align: center; border-bottom: 1px solid rgba(255,46,126,0.2); margin-bottom: 16px;">
            <div style="font-size: 48px;">⚖️</div>
            <div style="font-size: 18px; font-weight: 700; background: linear-gradient(135deg, #FF2E7E, #8A2BE2); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">AWAZ-E-NISA</div>
            <div style="font-size: 9px; color: #6b5d80;">Voice of Women</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div class='sb-pad'>", unsafe_allow_html=True)

        init = st.session_state.username[0].upper()
        st.markdown(f"""
        <div class="an-user-card">
            <div class="an-avatar">{init}</div>
            <div>
                <div class="an-uname">{st.session_state.username}</div>
                <div class="an-ustatus">🟢 Active · {datetime.now().strftime('%H:%M')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<span class='an-nav-label'>🎨 Appearance</span>", unsafe_allow_html=True)
        cur_theme = st.session_state.theme
        if st.button(f"{'☀️ Switch to Light' if cur_theme == 'dark' else '🌙 Switch to Dark'}", use_container_width=True, key="sidebar_theme_btn"):
            st.session_state.theme = "light" if cur_theme == "dark" else "dark"
            st.rerun()

        font_options = {"Small (A-)": "small", "Medium (A)": "medium", "Large (A+)": "large"}
        cur_font_label = {v: k for k, v in font_options.items()}.get(st.session_state.font_size, "Medium (A)")
        selected_font_label = st.selectbox("Font Size", list(font_options.keys()),
                                           index=list(font_options.keys()).index(cur_font_label),
                                           key="font_size_sel", label_visibility="collapsed")
        new_font = font_options[selected_font_label]
        if new_font != st.session_state.font_size:
            st.session_state.font_size = new_font
            st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<span class='an-nav-label'>👤 User Mode</span>", unsafe_allow_html=True)
        mode_options = ["👩 GENERAL USER", "⚖️ LEGAL PRO"]
        mode_index = 0 if "GENERAL" in st.session_state.current_mode else 1
        mode = st.selectbox("mode_sel", mode_options, index=mode_index, label_visibility="collapsed")
        st.session_state.current_mode = "GENERAL USER (Woman)" if "GENERAL" in mode else "LEGAL PRO"

        st.markdown("<hr>", unsafe_allow_html=True)

        if st.button("✨ New Chat", use_container_width=True, key="btn_new_chat"):
            save_current_session()
            create_new_chat()
            st.rerun()

        recent = get_recent_sessions(5)
        if recent:
            st.markdown("<span class='an-nav-label'>📋 Recent Chats</span>", unsafe_allow_html=True)
            for sid, sdata in recent:
                title = sdata.get("title", "💬 Chat")
                if st.button(f"💬 {title[:30]}", use_container_width=True, key=f"rc_{sid}"):
                    load_session(sid)
                    st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<span class='an-nav-label'>🎯 Features</span>", unsafe_allow_html=True)

        for label, key in FEATURES.items():
            if st.button(f"{label}", use_container_width=True, key=f"nav_{key}"):
                st.session_state.active_feature = key
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<span class='an-nav-label'>📎 Upload</span>", unsafe_allow_html=True)
        uploaded_docs = st.file_uploader("docs", type=['pdf','png','jpg','jpeg'], accept_multiple_files=True, label_visibility="collapsed")

        if uploaded_docs:
            if st.button("🔍 Analyze Documents", use_container_width=True):
                with st.spinner("Processing..."):
                    full_text = ""
                    for doc in uploaded_docs:
                        if "pdf" in doc.type:
                            full_text += extract_text_from_pdf(doc)
                        else:
                            full_text += extract_text_from_image(doc)
                    res = st.session_state.rag.invoke({
                        "question": f"Analyze these documents: {full_text}",
                        "mode": st.session_state.current_mode
                    })
                    st.session_state.messages.append({"role": "assistant", "content": res})
                    save_current_session()
                    st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        if st.button("🗑️ Clear Chat", use_container_width=True, key="btn_clear"):
            st.session_state.messages = []
            st.session_state.analysis_result = None
            save_current_session()
            st.rerun()

        if st.button("🚪 Logout", use_container_width=True, key="btn_logout"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(HOTLINES_HTML, unsafe_allow_html=True)

        st.markdown("""
        <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid rgba(255,46,126,0.15); text-align: center;">
            <div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(255,255,255,0.03); padding: 5px 12px; border-radius: 20px;">
                <span style="font-size: 10px;">🚀</span>
                <span style="font-size: 9px; color: #888;">SAMSUNG INNOVATION CAMPUS</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.caption(f"📱 v2.0 | {datetime.now().strftime('%Y')}")

    # ========== MAIN CONTENT ==========
    feature = st.session_state.active_feature
    icon = FEATURE_ICONS.get(feature, "⚖️")
    mode_lbl = "General User" if "GENERAL" in st.session_state.current_mode else "Legal Pro"

    cur_t = st.session_state.theme
    th_icon = "☀️" if cur_t == "dark" else "🌙"
    th_label = "Light" if cur_t == "dark" else "Dark"
    hdr_bg   = "rgba(15,10,26,0.95)" if cur_t == "dark" else "rgba(255,255,255,0.97)"
    hdr_bdr  = "rgba(255,46,126,0.18)" if cur_t == "dark" else "rgba(200,30,100,0.18)"
    hdr_sub  = "#9080a8" if cur_t == "dark" else "#7060a0"

    st.markdown(f"""
    <div style="position:sticky;top:0;z-index:990;
                background:{hdr_bg};backdrop-filter:blur(20px);
                border-bottom:1px solid {hdr_bdr};
                padding:10px 4px;margin-bottom:24px;
                display:flex;align-items:center;justify-content:space-between;">
        <div style="display:flex;align-items:center;gap:10px;">
            <span style="font-size:20px;">{icon}</span>
            <div>
                <div style="font-family:'Playfair Display',serif;font-size:16px;font-weight:700;
                            background:linear-gradient(135deg,#FF2E7E,#8A2BE2);
                            -webkit-background-clip:text;-webkit-text-fill-color:transparent;">{feature}</div>
                <div style="font-size:10px;color:{hdr_sub};">
                    Awaz-e-Nisa &nbsp;·&nbsp;
                    <span style="color:#FF2E7E;font-weight:600;">{mode_lbl}</span>
                    &nbsp;·&nbsp; {datetime.now().strftime('%d %b %Y')}
                </div>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:12px;">
            <div style="background:rgba(255,46,126,0.1);border:1px solid rgba(255,46,126,0.25);
                        padding:4px 12px;border-radius:20px;font-size:11px;color:#FF2E7E;font-weight:600;">
                ● LIVE
            </div>
            <div style="font-size:11px;color:{hdr_sub};">{th_icon} {th_label} mode</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    _, _, th_col = st.columns([6, 1, 1])
    with th_col:
        if st.button(f"{th_icon} {th_label}", key="hdr_theme_btn"):
            st.session_state.theme = "light" if cur_t == "dark" else "dark"
            st.rerun()

    # ── ABOUT PAGE ──────────────────────────────────────────
    if feature == "About":
        st.markdown(f"""
        <div class="an-section-header">
            <div class="an-header-left">
                <div class="an-icon-box">🌸</div>
                <div>
                    <div class="an-feature-title">About Awaz-e-Nisa</div>
                    <div class="an-feature-sub">آوازِ نسواں - "Voice of Women"</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        show_about_page()
        st.markdown("""
        <div class="samsung-footer">
            <div class="samsung-logo">
                <span class="samsung-icon">🚀</span>
                <span class="samsung-text">SAMSUNG INNOVATION CAMPUS</span>
            </div>
            <div>Powered by Samsung Innovation Campus | Built for Pakistani Women</div>
            <div style="font-size: 9px; margin-top: 5px;">© 2026 Awaz-e-Nisa · All Rights Reserved</div>
        </div>
        """, unsafe_allow_html=True)

    # ── LEGAL CHAT ──────────────────────────────────────────
    elif feature == "Legal Chat":
        st.markdown(f"""
        <div class="an-section-header">
            <div class="an-header-left">
                <div class="an-icon-box">{icon}</div>
                <div>
                    <div class="an-feature-title">{feature}</div>
                    <div class="an-feature-sub">Awaz-e-Nisa · <span class="an-mode-chip">{mode_lbl}</span></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not st.session_state.messages:
            st.markdown("""
            <div class="an-welcome">
                <div class="an-welcome-icon">⚖️</div>
                <div class="an-welcome-title">Welcome to Awaz-e-Nisa AI</div>
                <div class="an-welcome-sub">Your trusted legal assistant for Pakistani laws.<br>Please ask me anything about your legal concerns.</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div class="demo-section">
                <div class="demo-title"><span>💡</span> Try Asking These Questions</div>
                <div class="demo-grid">
                    <div class="demo-question">
                        <div class="demo-category"> Family Law</div>
                        <div class="demo-text">My husband married a second woman without my permission and left me with 2 children. What should I do?</div>
                    </div>
                    <div class="demo-question">
                        <div class="demo-category"> Financial Rights</div>
                        <div class="demo-text">How much maintenance (kharcha) can I claim for myself and my 2 children?</div>
                    </div>
                    <div class="demo-question">
                        <div class="demo-category"> Child Custody</div>
                        <div class="demo-text">Can my husband take my children away from me after divorce?</div>
                    </div>
                    <div class="demo-question">
                        <div class="demo-category"> Cybercrime</div>
                        <div class="demo-text">Someone is blackmailing me with my private photos. How to file a complaint?</div>
                    </div>
                    <div class="demo-question">
                        <div class="demo-category"> Khula/Talaq</div>
                        <div class="demo-text">What is the procedure for Khula and how long does it take?</div>
                    </div>
                    <div class="demo-question">
                        <div class="demo-category"> Workplace</div>
                        <div class="demo-text">How to file a workplace harassment complaint in Pakistan?</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ask me anything about Pakistani law..."):
            st.session_state.last_query = prompt
            st.session_state.messages.append({"role": "user", "content": prompt})
            save_chat_message(st.session_state.username, "user", prompt, st.session_state.current_mode)

            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    res = st.session_state.rag.invoke({
                        "question": prompt,
                        "mode": st.session_state.current_mode
                    })
                st.markdown(res)
                save_chat_message(st.session_state.username, "assistant", res, st.session_state.current_mode)
                st.session_state.messages.append({"role": "assistant", "content": res})
                save_current_session()

                st.markdown("""
                <div style="margin-top: 20px; margin-bottom: 10px;">
                    <div style="font-size: 11px; color: #FF2E7E; font-weight: 600;">⚡ ANALYZE FURTHER</div>
                </div>
                """, unsafe_allow_html=True)

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("Case Merits", key="qa1"):
                        with st.spinner("Analyzing..."):
                            result = st.session_state.m_chain.invoke(prompt)
                        st.markdown("### Case Merits Analysis")
                        st.markdown(result)
                with col2:
                    if st.button("⚔ Counter", key="qa2"):
                        with st.spinner("Analyzing..."):
                            result = st.session_state.o_chain.invoke(prompt)
                        st.markdown("### ⚔ Counter Arguments")
                        st.markdown(result)
                with col3:
                    if st.button(" Timeline", key="qa3"):
                        with st.spinner("Analyzing..."):
                            result = st.session_state.t_chain.invoke(prompt)
                        st.markdown("###  Timeline Estimate")
                        st.markdown(result)
                with col4:
                    if st.button(" Draft", key="qa4"):
                        with st.spinner("Generating..."):
                            result = st.session_state.d_chain.invoke(prompt)
                        st.markdown("###  Legal Draft")
                        st.markdown(result)
                        pdf_path = create_pdf(result)
                        with open(pdf_path, "rb") as f:
                            st.download_button(" Download PDF", f, file_name="legal_draft.pdf")
                        os.unlink(pdf_path)

        # Feature pills footer
        st.markdown("""
        <div style="margin-top:40px;padding:20px 0 8px;border-top:1px solid rgba(255,46,126,0.15);">
            <div style="text-align:center;font-size:10px;color:#FF2E7E;font-weight:700;
                        letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;">
                🎯 Jump to a Feature
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <style>
        div[data-testid="stHorizontalBlock"] > div > div > div > .stButton > button {
            background: rgba(255,46,126,0.08) !important;
            border: 1px solid rgba(255,46,126,0.25) !important;
            color: #FF2E7E !important; border-radius: 22px !important;
            padding: 6px 14px !important; font-size: 12px !important;
            font-weight: 600 !important; box-shadow: none !important;
            transition: all 0.2s !important; white-space: nowrap !important;
        }
        div[data-testid="stHorizontalBlock"] > div > div > div > .stButton > button:hover {
            background: rgba(255,46,126,0.18) !important; border-color: #FF2E7E !important;
            transform: translateY(-1px) !important; box-shadow: 0 4px 12px rgba(255,46,126,0.2) !important;
        }
        </style>
        """, unsafe_allow_html=True)

        fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)
        with fc1:
            if st.button(" Legal Chat", key="ft_chat", use_container_width=True):
                st.session_state.active_feature = "Legal Chat"; st.rerun()
        with fc2:
            if st.button(" Case Merits", key="ft_merits", use_container_width=True):
                st.session_state.active_feature = "Case Merits"; st.rerun()
        with fc3:
            if st.button(" Counter Args", key="ft_counter", use_container_width=True):
                st.session_state.active_feature = "Counter Arguments"; st.rerun()
        with fc4:
            if st.button(" Timeline", key="ft_timeline", use_container_width=True):
                st.session_state.active_feature = "Timeline Estimator"; st.rerun()
        with fc5:
            if st.button(" Legal Draft", key="ft_draft", use_container_width=True):
                st.session_state.active_feature = "Legal Draft"; st.rerun()
        with fc6:
            if st.button(" About", key="ft_about", use_container_width=True):
                st.session_state.active_feature = "About"; st.rerun()

        st.markdown(f"""
        <div style="text-align:center;padding:16px 0 8px;border-top:1px solid rgba(255,46,126,0.08);margin-top:8px;">
            <div style="display:inline-flex;align-items:center;gap:8px;
                        background:rgba(255,46,126,0.06);padding:6px 18px;border-radius:30px;margin-bottom:8px;">
                <span style="font-size:14px;">🚀</span>
                <span style="font-size:11px;font-weight:700;letter-spacing:1.5px;color:#FF2E7E;">SAMSUNG INNOVATION CAMPUS</span>
            </div>
            <div style="font-size:11px;color:#9080a8;">Powered by Samsung Innovation Campus · Built for Pakistani Women</div>
            <div style="font-size:10px;color:#60508a;margin-top:4px;">
                Trained on 164 Pakistani Law Documents · RAG + Gemini AI · © 2026 Awaz-e-Nisa
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── CASE MERITS ─────────────────────────────────────────
    elif feature == "Case Merits":
        st.markdown(f"""
        <div class="an-section-header">
            <div class="an-header-left">
                <div class="an-icon-box">{icon}</div>
                <div>
                    <div class="an-feature-title">{feature}</div>
                    <div class="an-feature-sub">Awaz-e-Nisa · <span class="an-mode-chip">{mode_lbl}</span></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        query = st.text_area("Case Description", value=st.session_state.get("last_query", ""),
                            placeholder="Describe your case in detail...", height=120)
        if st.button(" Analyze Merits", use_container_width=True):
            if query.strip():
                with st.spinner("Analyzing case strengths..."):
                    result = st.session_state.m_chain.invoke(query)
                st.markdown("### Case Merits Analysis")
                st.markdown(result)
            else:
                st.warning("Please describe your case first.")
        if st.button("← Back to Chat"):
            st.session_state.active_feature = "Legal Chat"
            st.rerun()

    # ── COUNTER ARGUMENTS ───────────────────────────────────
    elif feature == "Counter Arguments":
        st.markdown(f"""
        <div class="an-section-header">
            <div class="an-header-left">
                <div class="an-icon-box">{icon}</div>
                <div>
                    <div class="an-feature-title">{feature}</div>
                    <div class="an-feature-sub">Awaz-e-Nisa · <span class="an-mode-chip">{mode_lbl}</span></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        query = st.text_area("Case Description", value=st.session_state.get("last_query", ""),
                            placeholder="Describe your case...", height=120)
        if st.button("⚔ Get Counter Arguments", use_container_width=True):
            if query.strip():
                with st.spinner("Preparing counter arguments..."):
                    result = st.session_state.o_chain.invoke(query)
                st.markdown("### ⚔ Counter Arguments")
                st.markdown(result)
            else:
                st.warning("Please describe your case first.")
        if st.button("← Back to Chat"):
            st.session_state.active_feature = "Legal Chat"
            st.rerun()

    # ── TIMELINE ESTIMATOR ──────────────────────────────────
    elif feature == "Timeline Estimator":
        st.markdown(f"""
        <div class="an-section-header">
            <div class="an-header-left">
                <div class="an-icon-box">{icon}</div>
                <div>
                    <div class="an-feature-title">{feature}</div>
                    <div class="an-feature-sub">Awaz-e-Nisa · <span class="an-mode-chip">{mode_lbl}</span></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        query = st.text_area("Case Description", value=st.session_state.get("last_query", ""),
                            placeholder="Describe your case...", height=120)
        if st.button(" Estimate Timeline", use_container_width=True):
            if query.strip():
                with st.spinner("Estimating timeline..."):
                    result = st.session_state.t_chain.invoke(query)
                st.markdown("###  Estimated Timeline")
                st.markdown(result)
            else:
                st.warning("Please describe your case first.")
        if st.button("← Back to Chat"):
            st.session_state.active_feature = "Legal Chat"
            st.rerun()

    # ── LEGAL DRAFT ─────────────────────────────────────────
    elif feature == "Legal Draft":
        st.markdown(f"""
        <div class="an-section-header">
            <div class="an-header-left">
                <div class="an-icon-box">{icon}</div>
                <div>
                    <div class="an-feature-title">{feature}</div>
                    <div class="an-feature-sub">Awaz-e-Nisa · <span class="an-mode-chip">{mode_lbl}</span></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        doc_type = st.selectbox("Select Document Type",
                                ["Legal Notice", "Application for Maintenance", "Khula Petition", "Custody Petition", "Police Complaint"])
        query = st.text_area("Case Details", value=st.session_state.get("last_query", ""),
                            placeholder=f"Provide details for {doc_type}...", height=120)
        if st.button(" Generate Draft", use_container_width=True):
            if query.strip():
                with st.spinner(f"Generating {doc_type}..."):
                    full_query = f"Generate a {doc_type} based on these details: {query}"
                    result = st.session_state.d_chain.invoke(full_query)
                st.markdown(f"###  {doc_type}")
                st.markdown(result)
                pdf_path = create_pdf(result, title=doc_type)
                with open(pdf_path, "rb") as f:
                    st.download_button(" Download PDF", data=f,
                                      file_name=f"{doc_type.lower().replace(' ', '_')}.pdf",
                                      mime="application/pdf")
                os.unlink(pdf_path)
            else:
                st.warning("Please provide case details first.")
        if st.button("← Back to Chat"):
            st.session_state.active_feature = "Legal Chat"
            st.rerun()
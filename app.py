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
import whisper
import random
from datetime import datetime
from fpdf import FPDF
from database import init_db, add_user, verify_user, save_chat_message, get_chat_history, delete_chat_history
from streamlit_mic_recorder import mic_recorder

# ============================================================
#  CONFIGURATION (MUST BE FIRST)
# ============================================================
st.set_page_config(
    page_title="Awaz-e-Nisa | Legal AI for Pakistani Women",
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

@st.cache_resource
def load_whisper_model():
    return whisper.load_model("base")

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
    "expanded_panels": {},
    "last_audio_id": None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ============================================================
#  DARK THEME CSS - PREMIUM HOMEPAGE DESIGN
# ============================================================
dark_theme = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700;800;900&family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --fs-xs: 11px; --fs-sm: 13px; --fs-base: 15px; --fs-md: 17px; --fs-lg: 19px;
    --fs-xl: 22px; --fs-2xl: 28px; --fs-3xl: 36px; --fs-4xl: 48px; --fs-hero: 72px;
    --c-bg: #0a0a12; --c-surface: #13111c; --c-surface2: #1c1930; --c-surface3: #221f38;
    --c-border: rgba(255,46,126,0.15); --c-border-pink: rgba(255,46,126,0.25);
    --c-text: #f0e8ff; --c-text-muted: #a8a0c0; --c-text-dim: #6a6080;
    --c-pink: #FF2E7E; --c-pink-light: #ff5c9e; --c-purple: #8A2BE2; --c-purple-light: #a855f7;
    --c-red-alert: #ef4444; --c-green: #4ade80; --c-blue: #3b82f6;
    --radius-sm: 8px; --radius-md: 12px; --radius-lg: 18px; --radius-xl: 24px; --radius-2xl: 32px; --radius-pill: 60px;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

.stApp { background: linear-gradient(135deg, var(--c-bg) 0%, #0d0d18 100%) !important; font-family: 'Inter', sans-serif !important; }
.stApp > header, #MainMenu, footer { display: none !important; }

.block-container { padding: 0 2rem 2rem 2rem !important; max-width: 1400px !important; margin: 0 auto !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--c-surface) 0%, var(--c-bg) 100%) !important;
    border-right: 1px solid var(--c-border) !important;
    width: 300px !important;
}

/* Chat Messages */
[data-testid="stChatMessage"] {
    background: var(--c-surface) !important;
    border-radius: 20px !important;
    border: 1px solid var(--c-border) !important;
    padding: 20px !important;
    margin-bottom: 16px !important;
    animation: slideIn 0.3s ease-out;
}

/* Chat Input */
[data-testid="stChatInput"] {
    background: var(--c-surface) !important;
    border: 2px solid var(--c-border) !important;
    border-radius: var(--radius-pill) !important;
    transition: all 0.3s ease !important;
}
[data-testid="stChatInput"]:focus-within { 
    border-color: var(--c-pink) !important; 
    box-shadow: 0 0 0 3px rgba(255,46,126,0.2); 
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, var(--c-pink), var(--c-purple)) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.stButton > button:hover { 
    transform: translateY(-2px) !important; 
    box-shadow: 0 10px 25px rgba(255,46,126,0.3); 
}

/* Headers */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Playfair Display', serif !important;
    background: linear-gradient(135deg, var(--c-text), #c8b8ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* Hero Section */
.hero-section {
    text-align: center;
    padding: 80px 24px 60px;
    position: relative;
    overflow: hidden;
}
.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: rgba(255,46,126,0.12);
    border: 1px solid rgba(255,46,126,0.35);
    padding: 8px 24px;
    border-radius: 40px;
    font-size: 13px;
    font-weight: 700;
    color: #ff7ab8;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 32px;
}
.hero-title {
    font-family: 'Playfair Display', serif;
    font-size: clamp(48px, 8vw, 80px);
    font-weight: 800;
    line-height: 1.1;
    margin-bottom: 24px;
    color: #f5eeff;
}
.hero-subtitle {
    font-size: 20px;
    line-height: 1.8;
    max-width: 580px;
    margin: 0 auto 24px;
    color: #8878a8;
}
.hero-gradient-text {
    background: linear-gradient(135deg, #FF2E7E, #c44dff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* Stats Bar */
.stats-bar {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 1px;
    background: rgba(255,46,126,0.15);
    border-radius: 24px;
    overflow: hidden;
    margin: 40px 0;
}
.stat-item {
    background: var(--c-surface);
    padding: 32px 20px;
    text-align: center;
    transition: all 0.3s ease;
}
.stat-item:hover { background: var(--c-surface2); }
.stat-number {
    font-size: 42px;
    font-weight: 800;
    background: linear-gradient(135deg, #FF2E7E, #c44dff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-family: 'Playfair Display', serif;
}
.stat-label {
    font-size: 12px;
    color: #806898;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
    margin-top: 8px;
}

/* Feature Cards Grid */
.features-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
    margin: 40px 0;
}
.feature-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 24px;
    padding: 32px;
    transition: all 0.3s ease;
}
.feature-card:hover {
    transform: translateY(-6px);
    border-color: var(--c-pink);
    background: rgba(255,46,126,0.05);
}
.feature-icon {
    width: 56px;
    height: 56px;
    border-radius: 16px;
    background: rgba(255,46,126,0.12);
    border: 1px solid rgba(255,46,126,0.25);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    margin-bottom: 20px;
}
.feature-title {
    font-size: 18px;
    font-weight: 700;
    color: #f0e8ff;
    margin-bottom: 10px;
}
.feature-desc {
    font-size: 14px;
    color: #7868a0;
    line-height: 1.6;
}

/* Training Data Cards */
.training-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 24px;
    margin: 40px 0;
}
.training-card {
    background: rgba(138,43,226,0.08);
    border: 1px solid rgba(138,43,226,0.2);
    border-radius: 24px;
    padding: 32px;
}
.training-number {
    font-size: 52px;
    font-weight: 800;
    color: #b070f8;
    margin-bottom: 10px;
    font-family: 'Playfair Display', serif;
}
.training-title {
    font-size: 18px;
    font-weight: 700;
    color: #c0a8e8;
    margin-bottom: 12px;
}
.training-text {
    font-size: 14px;
    color: #7868a0;
    line-height: 1.6;
}
.training-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 18px;
}
.training-tag {
    background: rgba(255,46,126,0.12);
    border: 1px solid rgba(255,46,126,0.22);
    color: #ff8ec0;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
}

/* How It Works */
.howit-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 24px;
    margin: 40px 0;
}
.howit-card {
    text-align: center;
    padding: 32px 20px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
}
.howit-number {
    width: 52px;
    height: 52px;
    border-radius: 50%;
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    font-weight: 800;
    color: white;
    margin: 0 auto 16px;
}
.howit-title {
    font-size: 16px;
    font-weight: 700;
    color: #d8c8f0;
    margin-bottom: 10px;
}
.howit-text {
    font-size: 13px;
    color: #7060a0;
    line-height: 1.6;
}

/* CTA Section */
.cta-section {
    border-radius: 32px;
    padding: 80px 48px;
    text-align: center;
    background: linear-gradient(135deg, rgba(255,46,126,0.12), rgba(138,43,226,0.16));
    border: 1px solid rgba(255,46,126,0.25);
    position: relative;
    overflow: hidden;
    margin: 48px 0;
}
.cta-title {
    font-size: 48px;
    font-weight: 700;
    font-family: 'Playfair Display', serif;
    color: #f5eeff;
    margin-bottom: 18px;
}
.cta-text {
    font-size: 17px;
    color: #8878a8;
    margin-bottom: 32px;
    max-width: 520px;
    margin-left: auto;
    margin-right: auto;
}

/* Footer */
.premium-footer {
    border-top: 1px solid rgba(255,46,126,0.12);
    padding: 40px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 24px;
    margin-top: 40px;
}
.footer-logo {
    display: flex;
    align-items: center;
    gap: 12px;
}
.footer-logo-text {
    font-family: 'Playfair Display', serif;
    font-size: 18px;
    font-weight: 700;
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.footer-links {
    display: flex;
    gap: 28px;
    flex-wrap: wrap;
}
.footer-link {
    font-size: 13px;
    color: #706080;
}
.footer-brand {
    text-align: right;
}
.footer-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(255,46,126,0.08);
    border: 1px solid rgba(255,46,126,0.18);
    padding: 6px 16px;
    border-radius: 24px;
    margin-bottom: 8px;
}

/* Law Tip Box */
.law-tip-box {
    padding: 15px;
    background: linear-gradient(135deg, #1a1a2e 0%, #0f0f1a 100%);
    border-left: 4px solid var(--c-pink);
    border-radius: 12px;
    margin: 15px 0;
}
.tip-title { color: var(--c-pink); font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; letter-spacing: 1px; }
.tip-text { color: var(--c-text-muted); font-size: 13px; line-height: 1.4; }

/* Emergency Box */
.emergency-box {
    padding: 12px;
    background: rgba(220,38,38,0.1);
    border: 1px solid rgba(220,38,38,0.3);
    border-radius: 12px;
    margin-top: 15px;
}
.emergency-item { color: #ff6b6b; font-size: 12px; font-weight: bold; margin-bottom: 5px; }

/* Mode Tag */
.mode-tag {
    background: linear-gradient(90deg, var(--c-pink), var(--c-purple));
    color: white !important;
    padding: 4px 12px;
    border-radius: 15px;
    font-size: 10px;
    font-weight: 700;
    display: inline-block;
    margin-bottom: 12px;
}

/* Demo Questions */
.demo-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin: 20px 0;
}
.demo-question {
    background: var(--c-surface2);
    border: 1px solid var(--c-border);
    border-radius: 12px;
    padding: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
}
.demo-question:hover {
    border-color: var(--c-pink);
    background: rgba(255,46,126,0.05);
    transform: translateX(4px);
}
.demo-category {
    font-size: 10px;
    color: var(--c-pink);
    font-weight: 700;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.demo-text {
    font-size: 13px;
    color: var(--c-text-muted);
    line-height: 1.5;
}

/* User Card */
.an-user-card {
    background: linear-gradient(135deg, rgba(255,46,126,0.1), rgba(138,43,226,0.1));
    border: 1px solid var(--c-border);
    border-radius: 12px;
    padding: 14px;
    margin: 16px 0;
    display: flex;
    align-items: center;
    gap: 12px;
}
.an-avatar {
    width: 44px; height: 44px;
    background: linear-gradient(135deg, var(--c-pink), var(--c-purple));
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 700;
    color: white !important;
}
.an-nav-label {
    font-size: 11px;
    color: var(--c-pink);
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 700;
    margin: 20px 0 12px;
    display: block;
}

/* Hotlines */
.an-hotlines {
    background: rgba(220,38,38,0.1);
    border: 1px solid rgba(220,38,38,0.3);
    border-radius: 12px;
    padding: 14px;
    margin-top: 20px;
}
.an-hotlines-title {
    font-size: 11px;
    font-weight: 700;
    color: var(--c-red-alert);
    text-transform: uppercase;
    margin-bottom: 10px;
}
.an-hotline-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid rgba(220,38,38,0.12);
}
.an-hotline-label { font-size: 12px; color: var(--c-text-muted); }
.an-hotline-num { font-size: 12px; color: var(--c-red-alert); font-weight: 700; }

/* Section Header */
.an-section-header {
    background: linear-gradient(135deg, rgba(255,46,126,0.08), rgba(138,43,226,0.08));
    border: 1px solid var(--c-border);
    border-radius: var(--radius-lg);
    padding: 20px 24px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.an-feature-title {
    font-size: 20px;
    font-weight: 700;
    font-family: 'Playfair Display', serif;
}
.an-mode-chip {
    background: rgba(255,46,126,0.2);
    color: #ffa0c0 !important;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 10px;
    font-weight: 600;
}

/* Animations */
@keyframes slideIn {
    from { opacity: 0; transform: translateY(16px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-8px); }
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--c-surface); }
::-webkit-scrollbar-thumb { background: linear-gradient(135deg, var(--c-pink), var(--c-purple)); border-radius: 10px; }
</style>
"""

# ============================================================
#  LIGHT THEME CSS
# ============================================================
light_theme = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700;800;900&family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --fs-xs: 11px; --fs-sm: 13px; --fs-base: 15px; --fs-md: 17px; --fs-lg: 19px;
    --fs-xl: 22px; --fs-2xl: 28px; --fs-3xl: 36px; --fs-4xl: 48px; --fs-hero: 72px;
    --c-bg: #f8f6ff; --c-surface: #ffffff; --c-surface2: #faf7ff; --c-surface3: #f5f0ff;
    --c-border: rgba(212,26,104,0.12); --c-border-pink: rgba(212,26,104,0.2);
    --c-text: #1a0e30; --c-text-muted: #4a3a6a; --c-text-dim: #8a7aa8;
    --c-pink: #d41a68; --c-pink-light: #FF2E7E; --c-purple: #6b21c8; --c-purple-light: #8A2BE2;
    --c-red-alert: #dc2626; --c-green: #16a34a; --c-blue: #3b82f6;
    --radius-sm: 8px; --radius-md: 12px; --radius-lg: 18px; --radius-xl: 24px; --radius-2xl: 32px; --radius-pill: 60px;
}

.stApp { background: var(--c-bg) !important; font-family: 'Inter', sans-serif !important; }
.stApp > header, #MainMenu, footer { display: none !important; }

.block-container { padding: 0 2rem 2rem 2rem !important; max-width: 1400px !important; margin: 0 auto !important; }

section[data-testid="stSidebar"] {
    background: var(--c-surface) !important;
    border-right: 1px solid var(--c-border) !important;
    width: 300px !important;
}

[data-testid="stChatMessage"] {
    background: var(--c-surface) !important;
    border-radius: 20px !important;
    border: 1px solid var(--c-border) !important;
    padding: 20px !important;
    margin-bottom: 16px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

[data-testid="stChatInput"] {
    background: var(--c-surface) !important;
    border: 2px solid var(--c-border) !important;
    border-radius: var(--radius-pill) !important;
}
[data-testid="stChatInput"]:focus-within { border-color: var(--c-pink) !important; }

.stButton > button {
    background: linear-gradient(135deg, var(--c-pink), var(--c-purple)) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}
.stButton > button:hover { transform: translateY(-2px) !important; }

h1, h2, h3, h4, h5, h6 {
    font-family: 'Playfair Display', serif !important;
    color: var(--c-text) !important;
}

.hero-section { text-align: center; padding: 80px 24px 60px; }
.hero-badge {
    display: inline-flex; align-items: center; gap: 10px;
    background: rgba(212,26,104,0.1); border: 1px solid rgba(212,26,104,0.25);
    padding: 8px 24px; border-radius: 40px; font-size: 13px; font-weight: 700;
    color: var(--c-pink); margin-bottom: 32px;
}
.stats-bar {
    display: grid; grid-template-columns: repeat(5,1fr); gap: 1px;
    background: var(--c-border); border-radius: 24px; overflow: hidden; margin: 40px 0;
}
.stat-item { background: var(--c-surface); padding: 32px 20px; text-align: center; }
.stat-number {
    font-size: 42px; font-weight: 800;
    background: linear-gradient(135deg, var(--c-pink), var(--c-purple));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.features-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 24px; margin: 40px 0; }
.feature-card {
    background: var(--c-surface); border: 1px solid var(--c-border);
    border-radius: 24px; padding: 32px; transition: all 0.3s ease;
}
.feature-card:hover { transform: translateY(-6px); border-color: var(--c-pink); box-shadow: 0 12px 30px rgba(212,26,104,0.1); }
.training-card {
    background: rgba(107,33,200,0.05); border: 1px solid rgba(107,33,200,0.15);
    border-radius: 24px; padding: 32px;
}
.howit-card {
    text-align: center; padding: 32px 20px;
    background: var(--c-surface); border: 1px solid var(--c-border); border-radius: 20px;
}
.cta-section {
    border-radius: 32px; padding: 80px 48px; text-align: center;
    background: linear-gradient(135deg, rgba(212,26,104,0.06), rgba(107,33,200,0.06));
    border: 1px solid var(--c-border); margin: 48px 0;
}
.law-tip-box {
    padding: 15px; background: linear-gradient(135deg, #f0ecfc 0%, #faf7ff 100%);
    border-left: 4px solid var(--c-pink); border-radius: 12px;
}
.emergency-box {
    padding: 12px; background: rgba(220,38,38,0.06);
    border: 1px solid rgba(220,38,38,0.2); border-radius: 12px;
}
.demo-question {
    background: var(--c-surface2); border: 1px solid var(--c-border); border-radius: 12px; padding: 14px;
}
.demo-question:hover { border-color: var(--c-pink); background: rgba(212,26,104,0.03); }
</style>
"""

# Apply theme
if st.session_state.theme == "dark":
    st.markdown(dark_theme, unsafe_allow_html=True)
else:
    st.markdown(light_theme, unsafe_allow_html=True)

# ============================================================
#  HELPER FUNCTIONS
# ============================================================
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
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        return tmp.name

def extract_text_from_pdf(file_content):
    try:
        with pdfplumber.open(file_content) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
            return text.strip() or "No readable text found."
    except Exception as e:
        return f"Error: {str(e)}"

def extract_text_from_image(uploaded_file):
    try:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(thresh, lang='eng+urd')
        return text.strip() if text else "No text detected."
    except Exception as e:
        return f"OCR failed: {str(e)}"

def new_session_id():
    return str(uuid.uuid4())[:8]

def create_new_chat():
    sid = new_session_id()
    st.session_state.active_session_id = sid
    st.session_state.messages = []
    st.session_state.last_query = ""
    st.session_state.active_feature = "Legal Chat"
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = {}
    st.session_state.chat_sessions[sid] = {
        "title": "💬 New conversation",
        "messages": [],
        "ts": datetime.now().strftime("%H:%M"),
    }

def save_current_session():
    sid = st.session_state.active_session_id
    if sid and sid in st.session_state.get("chat_sessions", {}):
        st.session_state.chat_sessions[sid]["messages"] = list(st.session_state.messages)

def ensure_session():
    if not st.session_state.active_session_id:
        create_new_chat()

# Deep Analysis Panel
@st.fragment
def render_analysis_panel(msg_index, original_query):
    panel_key = f"panel_{msg_index}"
    if panel_key not in st.session_state.expanded_panels:
        st.session_state.expanded_panels[panel_key] = {
            "merits": False, "opposition": False, "timeline": False, "draft": False,
            "merits_res": None, "opp_res": None, "time_res": None, "draft_res": None
        }
    
    panel = st.session_state.expanded_panels[panel_key]
    st.markdown('<div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid var(--c-border);">', unsafe_allow_html=True)
    st.markdown("<p style='color:#888; font-size:11px; font-weight:bold; letter-spacing:1px;'>🔍 DEEP ANALYSIS TOOLS</p>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("✅ Case Merits", key=f"m_{msg_index}", use_container_width=True):
            if not panel["merits_res"]:
                with st.spinner("Analyzing..."):
                    panel["merits_res"] = st.session_state.m_chain.invoke(original_query)
            panel["merits"] = not panel["merits"]
            st.rerun()
    with col2:
        if st.button("⚔ Opposition", key=f"o_{msg_index}", use_container_width=True):
            if not panel["opp_res"]:
                with st.spinner("Analyzing..."):
                    panel["opp_res"] = st.session_state.o_chain.invoke(original_query)
            panel["opposition"] = not panel["opposition"]
            st.rerun()
    with col3:
        if st.button("📅 Timeline", key=f"t_{msg_index}", use_container_width=True):
            if not panel["time_res"]:
                with st.spinner("Analyzing..."):
                    panel["time_res"] = st.session_state.t_chain.invoke(original_query)
            panel["timeline"] = not panel["timeline"]
            st.rerun()
    with col4:
        if st.button("📄 Draft", key=f"d_{msg_index}", use_container_width=True):
            if not panel["draft_res"]:
                with st.spinner("Generating..."):
                    panel["draft_res"] = st.session_state.d_chain.invoke(original_query)
            panel["draft"] = not panel["draft"]
            st.rerun()

    if panel["merits"] and panel["merits_res"]:
        st.success(panel["merits_res"])
    if panel["opposition"] and panel["opp_res"]:
        st.error(panel["opp_res"])
    if panel["timeline"] and panel["time_res"]:
        st.info(panel["time_res"])
    if panel["draft"] and panel["draft_res"]:
        st.warning(panel["draft_res"])
        pdf_path = create_pdf(panel["draft_res"])
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download PDF", f, file_name=f"legal_draft_{msg_index}.pdf", key=f"dl_{msg_index}", use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

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

LEGAL_TIPS = [
    ("Women's Rights", "Article 25 ensures protection for women and children under Pakistani law."),
    ("Workplace", "The Protection Against Harassment Act 2010 protects you from workplace harassment."),
    ("Cyber Law", "Reporting online abuse to FIA under PECA 2016 is your legal right."),
    ("Family Law", "MFLO 1961 governs marriage, divorce, and maintenance for Muslim women."),
    ("Child Custody", "Guardians & Wards Act 1890 prioritizes child's welfare in custody cases."),
]

FEATURES = {
    "⚡ Legal Chat": "Legal Chat",
    "📊 Case Merits": "Case Merits",
    "⚔ Counter Arguments": "Counter Arguments",
    "📅 Timeline Estimator": "Timeline Estimator",
    "📄 Legal Draft": "Legal Draft",
    "🌸 About": "About",
}

FEATURE_ICONS = {
    "Legal Chat": "⚡", "Case Merits": "📊", "Counter Arguments": "⚔",
    "Timeline Estimator": "📅", "Legal Draft": "📄", "About": "🌸",
}

# ============================================================
#  LANDING PAGE - PREMIUM VERSION
# ============================================================
if not st.session_state.logged_in and st.session_state.show_landing:
    # Hero Section
    st.markdown("""
    <div class="hero-section">
        <div class="hero-badge">
            <span style="width:8px;height:8px;border-radius:50%;background:#FF2E7E;display:inline-block;"></span>
            Samsung Innovation Campus · Pakistan
        </div>
        <div class="hero-title">
            Legal Rights for Every<br>
            <span class="hero-gradient-text">Pakistani Woman</span>
        </div>
        <div class="hero-subtitle">
            AI-powered legal assistant trained on <strong style="color:#c090e8;">164 Pakistani law documents.</strong><br>
            Empowering citizens with legal literacy and assisting Legal Professionals with rapid case analysis.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Hero Buttons
    col1, col2, col3, col4 = st.columns([1, 1.2, 1.2, 1])
    with col2:
        if st.button("🚀 Start Free Consultation", use_container_width=True, key="hero_start"):
            st.session_state.show_landing = False
            st.rerun()
    with col3:
        if st.button("👤 Try as Guest", use_container_width=True, key="hero_guest"):
            st.session_state.logged_in = True
            st.session_state.username = "Guest"
            st.session_state.show_landing = False
            create_new_chat()
            st.rerun()
    
    # Stats Bar
    st.markdown("""
    <div class="stats-bar">
        <div class="stat-item"><div class="stat-number">164</div><div class="stat-label">Law Documents</div></div>
        <div class="stat-item"><div class="stat-number">12+</div><div class="stat-label">Legal Domains</div></div>
        <div class="stat-item"><div class="stat-number">2</div><div class="stat-label">Languages</div></div>
        <div class="stat-item"><div class="stat-number">6</div><div class="stat-label">AI Tools</div></div>
        <div class="stat-item"><div class="stat-number">24/7</div><div class="stat-label">Availability</div></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Features Section
    st.markdown("""
    <div style="text-align:center; margin-bottom:20px;">
        <div style="display:inline-block;background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.28);color:#ff7ab8;padding:6px 18px;border-radius:24px;font-size:12px;font-weight:700;text-transform:uppercase;">✦ Features</div>
        <h2 style="margin-top:20px;">Everything You Need to Know Your Rights</h2>
        <p style="color:#8878a8;max-width:560px;margin:0 auto;">From instant legal Q&amp;A to professional court documents — all powered by AI trained on Pakistani law.</p>
    </div>
    """, unsafe_allow_html=True)
    
    features_data = [
        ("⚡", "Instant Legal Chat", "Ask in Urdu or English. Get cited answers with section numbers from MFLO, PECA, and more."),
        ("📊", "Case Merits Analysis", "Understand legal strengths and weaknesses of your case before approaching a lawyer."),
        ("⚔", "Counter Arguments", "Know opposing arguments in advance so you're fully prepared before your hearing."),
        ("📅", "Timeline Estimator", "Stage-by-stage timeline for your case based on Pakistani court procedures."),
        ("📄", "Legal Draft Generator", "Generate Khula petitions, custody applications, and police complaints as PDF."),
        ("📎", "Document Analysis", "Upload Nikah Nama or court notices — AI explains what it means for you."),
    ]
    
    cols = st.columns(3)
    for i, (icon, title, desc) in enumerate(features_data):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="feature-card">
                <div class="feature-icon">{icon}</div>
                <div class="feature-title">{title}</div>
                <div class="feature-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
    
    # Training Data Section
    st.markdown("""
    <div style="margin:60px 0;background:rgba(138,43,226,0.05);border-radius:32px;padding:48px 36px;">
        <div style="text-align:center; margin-bottom:30px;">
            <div style="display:inline-block;background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.28);color:#ff7ab8;padding:6px 18px;border-radius:24px;font-size:12px;font-weight:700;text-transform:uppercase;">📚 Training Data</div>
            <h2 style="margin-top:20px;">Trained on 164 Pakistani Law Documents</h2>
            <p style="color:#8878a8;max-width:560px;margin:0 auto;">Our RAG system retrieves answers directly from verified legal texts — not hallucination.</p>
        </div>
        <div class="training-grid">
            <div class="training-card"><div class="training-number">50+</div><div class="training-title">Family Law Texts</div><div class="training-text">MFLO 1961, FCA 1964, CMRA, GWA 1890</div><div class="training-tags"><span class="training-tag">MFLO 1961</span><span class="training-tag">FCA 1964</span><span class="training-tag">CMRA</span></div></div>
            <div class="training-card"><div class="training-number">40+</div><div class="training-title">Cybercrime & Digital Rights</div><div class="training-text">PECA 2016, FIA Rules, NR3C</div><div class="training-tags"><span class="training-tag">PECA 2016</span><span class="training-tag">FIA Rules</span><span class="training-tag">NR3C</span></div></div>
            <div class="training-card"><div class="training-number">35+</div><div class="training-title">Workplace & Rights Laws</div><div class="training-text">HAW 2010, Labour Laws, WPA Punjab</div><div class="training-tags"><span class="training-tag">HAW 2010</span><span class="training-tag">Labour Laws</span><span class="training-tag">WPA Punjab</span></div></div>
            <div class="training-card"><div class="training-number">39+</div><div class="training-title">Inheritance & Property</div><div class="training-text">Shariat Act, Succession, Haq Mehr</div><div class="training-tags"><span class="training-tag">Shariat Act</span><span class="training-tag">Succession</span><span class="training-tag">Haq Mehr</span></div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # How It Works Section
    st.markdown("""
    <div style="margin:60px 0;">
        <div style="text-align:center; margin-bottom:30px;">
            <div style="display:inline-block;background:rgba(255,46,126,0.12);border:1px solid rgba(255,46,126,0.28);color:#ff7ab8;padding:6px 18px;border-radius:24px;font-size:12px;font-weight:700;text-transform:uppercase;">💡 How It Works</div>
            <h2 style="margin-top:20px;">From Question to Legal Action in Minutes</h2>
            <p style="color:#8878a8;max-width:560px;margin:0 auto;">No lawyer needed for your first consultation. Just type and get answers.</p>
        </div>
        <div class="howit-grid">
            <div class="howit-card"><div class="howit-number">1</div><div class="howit-title">Ask Your Question</div><div class="howit-text">Type in Roman Urdu or English. No legal knowledge needed.</div></div>
            <div class="howit-card"><div class="howit-number">2</div><div class="howit-title">AI Searches the Law</div><div class="howit-text">RAG finds relevant sections from 164 verified Pakistani legal documents.</div></div>
            <div class="howit-card"><div class="howit-number">3</div><div class="howit-title">Get Cited Answers</div><div class="howit-text">Guidance with exact section numbers like "MFLO Section 6" so you can verify.</div></div>
            <div class="howit-card"><div class="howit-number">4</div><div class="howit-title">Download & Act</div><div class="howit-text">Generate legal drafts as PDF, know your timeline, walk into court prepared.</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # CTA Section
    st.markdown("""
    <div class="cta-section">
        <div class="cta-title">Your Voice. Your Rights. Your Law.</div>
        <div class="cta-text">Join thousands of Pakistani women who've used Awaz-e-Nisa to understand their legal rights.</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns([1, 1.2, 1.2, 1])
    with col2:
        if st.button("⚖️ Get Started Free", use_container_width=True, key="cta_start"):
            st.session_state.show_landing = False
            st.rerun()
    with col3:
        if st.button("👀 Try as Guest", use_container_width=True, key="cta_guest"):
            st.session_state.logged_in = True
            st.session_state.username = "Guest"
            st.session_state.show_landing = False
            create_new_chat()
            st.rerun()
    
    # Footer
    st.markdown("""
    <div class="premium-footer">
        <div class="footer-logo">
            <span style="font-size:28px;">⚖️</span>
            <div><div class="footer-logo-text">AWAZ-E-NISA</div><div style="font-size:12px;color:#604878;">آوازِ نسواں · Voice of Women</div></div>
        </div>
        <div class="footer-links">
            <span class="footer-link">Legal Chat</span>
            <span class="footer-link">Case Merits</span>
            <span class="footer-link">Counter Args</span>
            <span class="footer-link">Timeline</span>
            <span class="footer-link">Legal Draft</span>
        </div>
        <div class="footer-brand">
            <div class="footer-badge"><span style="font-size:11px;">🚀 SAMSUNG INNOVATION CAMPUS</span></div>
            <div style="font-size:11px;color:#503860;">© 2026 Awaz-e-Nisa · Pakistan</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
#  LOGIN PAGE
# ============================================================
elif not st.session_state.logged_in and not st.session_state.show_landing:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center;">
            <div style="font-size: 56px; margin-bottom: 16px;">⚖️</div>
            <h2>Welcome Back</h2>
            <p style="color: #8878a8;">Sign in to continue to Awaz-e-Nisa</p>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
        
        with tab1:
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            if st.button("Login", use_container_width=True):
                if verify_user(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    create_new_chat()
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        
        with tab2:
            new_user = st.text_input("Username", placeholder="Choose a username")
            new_pass = st.text_input("Password", type="password", placeholder="Choose a password")
            if st.button("Create Account", use_container_width=True):
                if new_user and new_pass:
                    if len(new_pass) >= 4:
                        if add_user(new_user, new_pass):
                            st.success("Account created! Please login.")
                        else:
                            st.error("Username already exists")
                    else:
                        st.warning("Password must be at least 4 characters")
                else:
                    st.warning("Please fill all fields")
        
        if st.button("← Back to Home", use_container_width=True):
            st.session_state.show_landing = True
            st.rerun()

# ============================================================
#  MAIN APP
# ============================================================
else:
    ensure_session()

    if "rag" not in st.session_state:
        with st.spinner("🚀 Loading AI model..."):
            try:
                from legal_advisor import (rag_chain, merits_chain,
                                           opposition_chain, timeline_chain, draft_chain)
                st.session_state.rag = rag_chain
                st.session_state.m_chain = merits_chain
                st.session_state.o_chain = opposition_chain
                st.session_state.t_chain = timeline_chain
                st.session_state.d_chain = draft_chain
            except:
                # Mock chains for testing
                class MockChain:
                    def invoke(self, q):
                        if isinstance(q, dict):
                            q = q.get("question", "")
                        return f"**Legal Guidance**\n\nBased on Pakistani law: {q[:200]}..."
                st.session_state.rag = MockChain()
                st.session_state.m_chain = MockChain()
                st.session_state.o_chain = MockChain()
                st.session_state.t_chain = MockChain()
                st.session_state.d_chain = MockChain()

    # ========== SIDEBAR ==========
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 20px 0; border-bottom: 1px solid rgba(255,46,126,0.15); margin-bottom: 20px;">
            <div style="font-size: 48px;">⚖️</div>
            <div style="font-size: 18px; font-weight: 700;">AWAZ-E-NISA</div>
            <div style="font-size: 11px; color: #8878a8;">Voice of Women</div>
        </div>
        """, unsafe_allow_html=True)
        
        # User info
        st.markdown(f"""
        <div class="an-user-card">
            <div class="an-avatar">{st.session_state.username[0].upper()}</div>
            <div>
                <div style="font-weight: 600;">{st.session_state.username}</div>
                <div style="font-size: 11px; color: #4ade80;">● Active</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Law Tip
        tip_title, tip_content = random.choice(LEGAL_TIPS)
        st.markdown(f"""
        <div class="law-tip-box">
            <div class="tip-title">⚖️ {tip_title}</div>
            <div class="tip-text">{tip_content}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Voice Input
        st.markdown('<span class="an-nav-label">🎤 VOICE COMMAND</span>', unsafe_allow_html=True)
        audio = mic_recorder(key="mic", start_prompt="🎤 Start Speaking", stop_prompt="⏹️ Stop", just_once=True, use_container_width=True)
        
        st.divider()
        
        # Mode selector
        st.markdown('<span class="an-nav-label">👤 USER MODE</span>', unsafe_allow_html=True)
        mode_options = ["👩 GENERAL USER", "⚖️ LEGAL PRO"]
        mode_idx = 0 if "GENERAL" in st.session_state.current_mode else 1
        mode = st.selectbox("mode_sel", mode_options, index=mode_idx, label_visibility="collapsed")
        st.session_state.current_mode = "GENERAL USER (Woman)" if "GENERAL" in mode else "LEGAL PRO"
        
        st.divider()
        
        # New Chat button
        if st.button("✨ New Chat", use_container_width=True):
            save_current_session()
            create_new_chat()
            st.rerun()
        
        # Feature navigation
        st.markdown('<span class="an-nav-label">🎯 FEATURES</span>', unsafe_allow_html=True)
        for label, key in FEATURES.items():
            if st.button(label, use_container_width=True, key=f"nav_{key}"):
                st.session_state.active_feature = key
                st.rerun()
        
        st.divider()
        
        # Document Upload
        st.markdown('<span class="an-nav-label">📎 DOCUMENT UPLOAD</span>', unsafe_allow_html=True)
        uploaded_docs = st.file_uploader("Upload", type=['pdf','png','jpg','jpeg'], accept_multiple_files=True, label_visibility="collapsed")
        
        if uploaded_docs:
            if st.button("🔍 Analyze Documents", use_container_width=True):
                with st.spinner("Processing..."):
                    full_text = ""
                    for doc in uploaded_docs:
                        if "pdf" in doc.type:
                            full_text += extract_text_from_pdf(doc)
                        else:
                            full_text += extract_text_from_image(doc)
                    res = st.session_state.rag.invoke(f"Analyze these documents: {full_text[:500]}")
                    st.session_state.messages.append({"role": "assistant", "content": res})
                    save_current_session()
                    st.rerun()
        
        st.divider()
        
        # Clear chat
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            save_current_session()
            st.rerun()
        
        # Logout
        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        # Emergency Hotlines
        st.markdown(HOTLINES_HTML, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid rgba(255,46,126,0.15); text-align: center;">
            <div style="font-size: 10px; color: #604878;">🚀 Samsung Innovation Campus</div>
            <div style="font-size: 9px; color: #604878;">© 2026 Awaz-e-Nisa</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ========== MAIN CONTENT ==========
    feature = st.session_state.active_feature
    
    # Voice input handler
    if 'audio' in locals() and audio and audio.get('id') != st.session_state.get('last_audio_id'):
        st.session_state.last_audio_id = audio['id']
        whisper_model = load_whisper_model()
        with st.spinner("Processing voice..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio['bytes'])
                result = whisper_model.transcribe(tmp.name, language="ur", task="translate")
                detected_text = result["text"].strip()
            if detected_text:
                st.session_state.messages.append({"role": "user", "content": f"🎤: {detected_text}"})
                with st.spinner("Analyzing..."):
                    res = st.session_state.rag.invoke({"question": detected_text, "mode": st.session_state.current_mode})
                st.session_state.messages.append({"role": "assistant", "content": res})
                save_current_session()
                st.rerun()
    
    if feature == "Legal Chat":
        st.markdown(f"""
        <div class="an-section-header">
            <div style="display:flex;align-items:center;gap:16px;">
                <div style="width:48px;height:48px;background:rgba(255,46,126,0.15);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px;">⚡</div>
                <div><div class="an-feature-title">Legal Chat</div><div style="font-size:11px;color:#8878a8;">Ask any legal question about Pakistani law</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if not st.session_state.messages:
            st.markdown("""
            <div style="text-align: center; padding: 40px 20px;">
                <div style="font-size: 56px; margin-bottom: 20px;">⚖️</div>
                <h3>Welcome to Awaz-e-Nisa</h3>
                <p style="color: #8878a8;">Your AI legal assistant for Pakistani law. Ask me anything about your legal rights.</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="demo-grid">
                <div class="demo-question"><div class="demo-category">Family Law</div><div class="demo-text">My husband married a second woman. What are my rights?</div></div>
                <div class="demo-question"><div class="demo-category">Child Custody</div><div class="demo-text">Can my ex-husband take our children away from me?</div></div>
                <div class="demo-question"><div class="demo-category">Financial Rights</div><div class="demo-text">How much maintenance can I claim for my children?</div></div>
                <div class="demo-question"><div class="demo-category">Cybercrime</div><div class="demo-text">Someone is blackmailing me online. What should I do?</div></div>
            </div>
            """, unsafe_allow_html=True)
        
        # Display messages
        for i, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"], avatar="👩" if msg["role"] == "user" else "⚖️"):
                if msg["role"] == "assistant":
                    st.markdown(f"<div class='mode-tag'>{st.session_state.current_mode}</div>", unsafe_allow_html=True)
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and i > 0:
                    prev_q = next((st.session_state.messages[j]["content"] for j in range(i-1, -1, -1) if st.session_state.messages[j]["role"] == "user"), "")
                    if prev_q:
                        render_analysis_panel(i, prev_q)
        
        # Chat input
        if prompt := st.chat_input("Type your legal question here..."):
            st.session_state.last_query = prompt
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user", avatar="👩"):
                st.markdown(prompt)
            
            with st.chat_message("assistant", avatar="⚖️"):
                with st.spinner("Analyzing..."):
                    response = st.session_state.rag.invoke({"question": prompt, "mode": st.session_state.current_mode})
                st.markdown(f"<div class='mode-tag'>{st.session_state.current_mode}</div>", unsafe_allow_html=True)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                save_current_session()
                st.rerun()
    
    elif feature == "Case Merits":
        st.markdown(f"""
        <div class="an-section-header">
            <div style="display:flex;align-items:center;gap:16px;">
                <div style="width:48px;height:48px;background:rgba(255,46,126,0.15);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px;">📊</div>
                <div><div class="an-feature-title">Case Merits Analysis</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        query = st.text_area("Case Description", value=st.session_state.get("last_query", ""), height=120)
        if st.button("Analyze Merits", use_container_width=True):
            if query.strip():
                with st.spinner("Analyzing..."):
                    result = st.session_state.m_chain.invoke(query)
                st.markdown("### Results")
                st.markdown(result)
            else:
                st.warning("Please describe your case first.")
        if st.button("← Back to Chat", use_container_width=True):
            st.session_state.active_feature = "Legal Chat"
            st.rerun()
    
    elif feature == "Counter Arguments":
        st.markdown(f"""
        <div class="an-section-header">
            <div style="display:flex;align-items:center;gap:16px;">
                <div style="width:48px;height:48px;background:rgba(255,46,126,0.15);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px;">⚔</div>
                <div><div class="an-feature-title">Counter Arguments</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        query = st.text_area("Case Description", value=st.session_state.get("last_query", ""), height=120)
        if st.button("Get Counter Arguments", use_container_width=True):
            if query.strip():
                with st.spinner("Generating counter arguments..."):
                    result = st.session_state.o_chain.invoke(query)
                st.markdown("### Results")
                st.markdown(result)
            else:
                st.warning("Please describe your case first.")
        if st.button("← Back to Chat", use_container_width=True):
            st.session_state.active_feature = "Legal Chat"
            st.rerun()
    
    elif feature == "Timeline Estimator":
        st.markdown(f"""
        <div class="an-section-header">
            <div style="display:flex;align-items:center;gap:16px;">
                <div style="width:48px;height:48px;background:rgba(255,46,126,0.15);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px;">📅</div>
                <div><div class="an-feature-title">Timeline Estimator</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        query = st.text_area("Case Description", value=st.session_state.get("last_query", ""), height=120)
        if st.button("Estimate Timeline", use_container_width=True):
            if query.strip():
                with st.spinner("Estimating timeline..."):
                    result = st.session_state.t_chain.invoke(query)
                st.markdown("### Results")
                st.markdown(result)
            else:
                st.warning("Please describe your case first.")
        if st.button("← Back to Chat", use_container_width=True):
            st.session_state.active_feature = "Legal Chat"
            st.rerun()
    
    elif feature == "Legal Draft":
        st.markdown(f"""
        <div class="an-section-header">
            <div style="display:flex;align-items:center;gap:16px;">
                <div style="width:48px;height:48px;background:rgba(255,46,126,0.15);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px;">📄</div>
                <div><div class="an-feature-title">Legal Draft Generator</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        doc_type = st.selectbox("Document Type", ["Legal Notice", "Khula Petition", "Custody Petition", "Maintenance Application", "Police Complaint"])
        query = st.text_area("Case Details", value=st.session_state.get("last_query", ""), height=120)
        if st.button("Generate Draft", use_container_width=True):
            if query.strip():
                with st.spinner(f"Generating {doc_type}..."):
                    result = st.session_state.d_chain.invoke(f"Generate a {doc_type}: {query}")
                st.markdown("### Results")
                st.markdown(result)
                pdf_path = create_pdf(result, doc_type)
                with open(pdf_path, "rb") as f:
                    st.download_button("Download PDF", f, file_name=f"{doc_type.lower().replace(' ', '_')}.pdf")
                os.unlink(pdf_path)
            else:
                st.warning("Please provide case details first.")
        if st.button("← Back to Chat", use_container_width=True):
            st.session_state.active_feature = "Legal Chat"
            st.rerun()
    
    elif feature == "About":
        st.markdown("""
        <div style="text-align:center;padding:40px 20px;background:linear-gradient(135deg,rgba(255,46,126,0.08),rgba(138,43,226,0.08));border-radius:24px;margin-bottom:30px;">
            <div style="font-size:64px;margin-bottom:20px;">🌸</div>
            <h2>About Awaz-e-Nisa</h2>
            <p style="color:#8878a8;">آوازِ نسواں — "Voice of Women"</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background:rgba(255,46,126,0.05);border-radius:20px;padding:30px;margin-bottom:20px;">
            <h3>Our Mission</h3>
            <p>Awaz-e-Nisa is a dedicated AI legal assistant designed specifically for Pakistani women and legal professionals working on family cases.</p>
        </div>
        <div style="background:rgba(255,46,126,0.05);border-radius:20px;padding:30px;margin-bottom:20px;">
            <h3>What We Cover</h3>
            <div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:15px;">
                <span style="background:rgba(255,46,126,0.1);padding:6px 14px;border-radius:20px;">🏛️ Family Law</span>
                <span style="background:rgba(255,46,126,0.1);padding:6px 14px;border-radius:20px;">📝 Khula & Talaq</span>
                <span style="background:rgba(255,46,126,0.1);padding:6px 14px;border-radius:20px;">👶 Child Custody</span>
                <span style="background:rgba(255,46,126,0.1);padding:6px 14px;border-radius:20px;">💰 Haq Mehr</span>
                <span style="background:rgba(255,46,126,0.1);padding:6px 14px;border-radius:20px;">🛡️ Domestic Violence</span>
                <span style="background:rgba(255,46,126,0.1);padding:6px 14px;border-radius:20px;">💻 Cybercrime</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("← Back to Chat", use_container_width=True):
            st.session_state.active_feature = "Legal Chat"
            st.rerun()
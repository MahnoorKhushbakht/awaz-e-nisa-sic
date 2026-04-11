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

# --- CONFIG (MUST BE FIRST) ---
st.set_page_config(
    page_title="Awaz-e-Nisa | Legal AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

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

# ── SESSION STATE DEFAULTS ────────────────────────────────
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

*, *::before, *::after { box-sizing: border-box; }

.stApp {
    background: #0f0a1a !important;
    font-family: 'Inter', sans-serif !important;
}
.stApp > header { display: none !important; }
#MainMenu, footer { display: none !important; }
.stApp > div { background: #0f0a1a !important; }

.stApp::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(circle at 20% 50%, rgba(255,46,126,0.03) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(138,43,226,0.03) 0%, transparent 50%);
    pointer-events: none;
    z-index: 0;
}

.samsung-footer {
    text-align: center;
    padding: 20px;
    margin-top: 30px;
    border-top: 1px solid rgba(255,46,126,0.15);
    font-size: 11px;
    color: #888;
}
.samsung-logo {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(255,255,255,0.05);
    padding: 6px 16px;
    border-radius: 30px;
    margin-bottom: 8px;
}
.samsung-icon { font-size: 14px; }
.samsung-text { font-weight: 600; letter-spacing: 1px; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #13091f 0%, #0f0a1a 100%) !important;
    border-right: 1px solid rgba(255,46,126,0.15) !important;
    width: 280px !important;
    backdrop-filter: blur(10px);
}

.block-container {
    padding: 0 2rem 5rem 2rem !important;
    max-width: 1200px !important;
    margin: 0 auto !important;
    position: relative;
    z-index: 1;
}

p, span, label, div, li {
    font-family: 'Inter', sans-serif !important;
    color: #e8e0f0 !important;
}
h1, h2, h3, h4, h5, h6 {
    font-family: 'Playfair Display', serif !important;
    color: #f5f0ff !important;
    letter-spacing: -0.02em;
}

/* About Page Styles */
.about-page {
    padding: 20px;
}
.about-hero {
    text-align: center;
    padding: 40px 20px;
    background: linear-gradient(135deg, rgba(255,46,126,0.08), rgba(138,43,226,0.08));
    border-radius: 30px;
    margin-bottom: 30px;
}
.about-hero-icon {
    font-size: 64px;
    margin-bottom: 20px;
}
.about-hero-title {
    font-size: 36px;
    font-weight: 700;
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 10px;
}
.about-hero-sub {
    font-size: 16px;
    color: #aaa;
}
.about-card {
    background: linear-gradient(135deg, rgba(255,46,126,0.05), rgba(138,43,226,0.05));
    border: 1px solid rgba(255,46,126,0.2);
    border-radius: 20px;
    padding: 25px;
    margin-bottom: 20px;
}
.about-card-title {
    font-size: 22px;
    font-weight: 700;
    color: #FF2E7E;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.about-card-text {
    font-size: 15px;
    line-height: 1.7;
    color: #d0c8e8;
}
.about-badge-container {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 15px;
}
.about-badge-large {
    background: rgba(255,46,126,0.15);
    border: 1px solid rgba(255,46,126,0.3);
    padding: 8px 18px;
    border-radius: 30px;
    font-size: 13px;
    color: #FF2E7E;
    font-weight: 500;
}

.about-section {
    background: linear-gradient(135deg, rgba(255,46,126,0.08), rgba(138,43,226,0.08));
    border: 1px solid rgba(255,46,126,0.2);
    border-radius: 20px;
    padding: 20px;
    margin-bottom: 20px;
}
.about-title {
    font-size: 18px;
    font-weight: 700;
    color: #FF2E7E;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.about-text {
    font-size: 14px;
    line-height: 1.6;
    color: #d0c8e8;
}
.about-highlight { color: #FF2E7E; font-weight: 600; }
.about-badge {
    display: inline-block;
    background: rgba(255,46,126,0.15);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    margin-right: 8px;
    margin-top: 8px;
}

.demo-section {
    background: linear-gradient(135deg, rgba(255,46,126,0.05), rgba(138,43,226,0.05));
    border: 1px solid rgba(255,46,126,0.15);
    border-radius: 20px;
    padding: 20px;
    margin: 20px 0;
}
.demo-title {
    font-size: 14px;
    font-weight: 600;
    color: #FF2E7E;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.demo-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
}
.demo-question {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,46,126,0.2);
    border-radius: 12px;
    padding: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
}
.demo-question:hover {
    background: rgba(255,46,126,0.1);
    border-color: #FF2E7E;
    transform: translateX(5px);
}
.demo-category {
    font-size: 10px;
    color: #FF2E7E;
    margin-bottom: 5px;
    font-weight: 600;
}
.demo-text { font-size: 12px; line-height: 1.4; color: #d0c8e8; }

.an-welcome {
    text-align: center;
    padding: 20px 20px;
    animation: fadeInUp 0.6s ease-out;
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}
.an-welcome-icon {
    font-size: 56px;
    margin-bottom: 15px;
    animation: bounce 2s infinite;
}
@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-8px); }
}
.an-welcome-title {
    font-size: 26px;
    font-weight: 700;
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 10px;
}
.an-welcome-sub { font-size: 14px; color: #aaa; line-height: 1.6; }

[data-testid="stChatInput"] {
    background: linear-gradient(135deg, rgba(30, 18, 48, 0.95), rgba(20, 10, 35, 0.95)) !important;
    backdrop-filter: blur(20px);
    border: 2px solid rgba(255,46,126,0.35) !important;
    border-radius: 60px !important;
    padding: 4px 8px 4px 24px !important;
    margin: 20px 0 20px 0 !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2), 0 0 15px rgba(255,46,126,0.15) !important;
}
[data-testid="stChatInput"]:hover {
    border-color: #FF2E7E !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3), 0 0 25px rgba(255,46,126,0.3) !important;
    transform: translateY(-2px);
}
[data-testid="stChatInput"]:focus-within {
    border-color: #FF2E7E !important;
    box-shadow: 0 8px 40px rgba(0,0,0,0.4), 0 0 35px rgba(255,46,126,0.5) !important;
    transform: translateY(-2px);
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: #f5f0ff !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    padding: 14px 8px !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #888 !important; font-size: 14px !important; }
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2) !important;
    border-radius: 50% !important;
    width: 44px !important;
    height: 44px !important;
    margin: 4px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 15px rgba(255,46,126,0.4) !important;
}
[data-testid="stChatInput"] button:hover {
    transform: scale(1.1) rotate(15deg) !important;
    box-shadow: 0 6px 25px rgba(255,46,126,0.6) !important;
}

.an-section-header {
    background: linear-gradient(135deg, rgba(255,46,126,0.1), rgba(138,43,226,0.1));
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.an-header-left { display: flex; align-items: center; gap: 16px; }
.an-icon-box {
    width: 48px;
    height: 48px;
    background: linear-gradient(135deg, rgba(255,46,126,0.15), rgba(138,43,226,0.15));
    border: 1px solid rgba(255,46,126,0.3);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
}
.an-feature-title { font-size: 24px; font-weight: 700; color: white; }
.an-feature-sub { font-size: 12px; color: #888; }
.an-mode-chip {
    display: inline-block;
    background: rgba(255,46,126,0.2);
    color: #FF2E7E;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 10px;
}

.sb-pad { padding: 0 12px; }
.an-user-card {
    background: linear-gradient(135deg, rgba(255,46,126,0.1), rgba(138,43,226,0.1));
    border: 1px solid rgba(255,46,126,0.2);
    border-radius: 16px;
    padding: 14px;
    margin: 16px 0;
    display: flex;
    align-items: center;
    gap: 12px;
}
.an-avatar {
    width: 44px;
    height: 44px;
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 700;
    color: white;
}
.an-uname { font-size: 15px; font-weight: 600; color: white; }
.an-ustatus { font-size: 10px; color: #4ade80; }
.an-nav-label {
    font-size: 11px;
    color: #FF2E7E;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
    margin: 20px 0 12px 0;
    display: block;
}

.an-hotlines {
    background: linear-gradient(135deg, rgba(220, 38, 38, 0.1), rgba(220, 38, 38, 0.05));
    border: 1px solid rgba(220, 38, 38, 0.3);
    border-radius: 12px;
    padding: 14px;
    margin-top: 20px;
}
.an-hotlines-title {
    font-size: 11px;
    font-weight: 700;
    color: #ef4444;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 10px;
}
.an-hotline-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    font-size: 12px;
}
.an-hotline-label { color: #bbb; }
.an-hotline-num { color: #ef4444; font-weight: 700; }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); }
::-webkit-scrollbar-thumb { background: linear-gradient(135deg, #FF2E7E, #8A2BE2); border-radius: 10px; }

/* ===== LANDING PAGE ===== */
.lp-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 18px 40px; position: fixed; top: 0; left: 0; right: 0; z-index: 999;
    background: rgba(15,10,26,0.92); backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(255,46,126,0.15);
}
.lp-logo { display: flex; align-items: center; gap: 10px; }
.lp-logo-text { font-family: 'Playfair Display', serif; font-size: 20px; font-weight: 700;
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.lp-nav { display: flex; align-items: center; gap: 12px; }
.lp-nav-link { color: #aaa; font-size: 13px; font-weight: 500; cursor: pointer;
    padding: 6px 14px; border-radius: 8px; transition: all 0.2s; }
.lp-nav-link:hover { color: #FF2E7E; background: rgba(255,46,126,0.08); }
.lp-theme-btn { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
    color: #ccc; padding: 6px 14px; border-radius: 20px; font-size: 12px; cursor: pointer; }
.lp-cta-btn { background: linear-gradient(135deg, #FF2E7E, #8A2BE2); color: white;
    padding: 9px 22px; border-radius: 22px; font-size: 13px; font-weight: 600;
    cursor: pointer; box-shadow: 0 4px 15px rgba(255,46,126,0.35); border: none; }

.lp-hero { text-align: center; padding: 160px 20px 80px; position: relative; }
.lp-hero-badge { display: inline-flex; align-items: center; gap: 8px;
    background: rgba(255,46,126,0.1); border: 1px solid rgba(255,46,126,0.3);
    padding: 7px 18px; border-radius: 30px; font-size: 12px; color: #FF2E7E;
    font-weight: 600; margin-bottom: 28px; letter-spacing: 0.5px; }
.lp-hero-title { font-family: 'Playfair Display', serif; font-size: 62px; font-weight: 700;
    line-height: 1.1; margin-bottom: 20px; color: #f5f0ff; }
.lp-hero-title span { background: linear-gradient(135deg, #FF2E7E, #8A2BE2);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.lp-hero-sub { font-size: 18px; color: #9080a8; max-width: 560px; margin: 0 auto 40px; line-height: 1.7; }
.lp-hero-btns { display: flex; gap: 14px; justify-content: center; align-items: center; flex-wrap: wrap; }
.lp-btn-primary { background: linear-gradient(135deg, #FF2E7E, #8A2BE2); color: white;
    padding: 14px 32px; border-radius: 30px; font-size: 15px; font-weight: 600;
    cursor: pointer; box-shadow: 0 6px 25px rgba(255,46,126,0.4); transition: all 0.3s; display: inline-block; }
.lp-btn-secondary { background: rgba(255,255,255,0.06); border: 1.5px solid rgba(255,46,126,0.3);
    color: #e0d0f8; padding: 14px 32px; border-radius: 30px; font-size: 15px; font-weight: 500;
    cursor: pointer; transition: all 0.2s; display: inline-block; }
.lp-btn-secondary:hover { background: rgba(255,46,126,0.1); border-color: #FF2E7E; }

.lp-stats { display: flex; justify-content: center; gap: 50px; margin: 60px 0;
    flex-wrap: wrap; padding: 30px 40px; border-top: 1px solid rgba(255,46,126,0.1);
    border-bottom: 1px solid rgba(255,46,126,0.1); }
.lp-stat { text-align: center; }
.lp-stat-num { font-size: 32px; font-weight: 700;
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.lp-stat-label { font-size: 12px; color: #7060a0; margin-top: 4px; letter-spacing: 0.5px; }

.lp-section { padding: 70px 40px; max-width: 1100px; margin: 0 auto; }
.lp-section-tag { display: inline-block; background: rgba(255,46,126,0.1);
    border: 1px solid rgba(255,46,126,0.25); color: #FF2E7E; padding: 5px 14px;
    border-radius: 20px; font-size: 11px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; margin-bottom: 16px; }
.lp-section-title { font-family: 'Playfair Display', serif; font-size: 38px; font-weight: 700;
    color: #f5f0ff; margin-bottom: 12px; }
.lp-section-sub { font-size: 16px; color: #8070a0; max-width: 560px; line-height: 1.7; }

.lp-features-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 44px; }
.lp-feat-card { background: rgba(255,46,126,0.04); border: 1px solid rgba(255,46,126,0.12);
    border-radius: 20px; padding: 28px; transition: all 0.3s; }
.lp-feat-card:hover { background: rgba(255,46,126,0.09); border-color: rgba(255,46,126,0.3);
    transform: translateY(-4px); box-shadow: 0 12px 30px rgba(255,46,126,0.12); }
.lp-feat-icon { font-size: 32px; margin-bottom: 14px; }
.lp-feat-title { font-size: 17px; font-weight: 700; color: #f0e8ff; margin-bottom: 8px; }
.lp-feat-desc { font-size: 13px; color: #8878a8; line-height: 1.6; }

.lp-data-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-top: 44px; }
.lp-data-card { background: rgba(138,43,226,0.06); border: 1px solid rgba(138,43,226,0.18);
    border-radius: 18px; padding: 24px; }
.lp-data-num { font-size: 36px; font-weight: 800; color: #8A2BE2; margin-bottom: 6px; }
.lp-data-label { font-size: 14px; font-weight: 600; color: #c0a8e8; margin-bottom: 6px; }
.lp-data-desc { font-size: 12px; color: #7868a0; line-height: 1.5; }
.lp-law-badges { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 20px; }
.lp-law-badge { background: rgba(255,46,126,0.1); border: 1px solid rgba(255,46,126,0.2);
    color: #FF9EC0; padding: 5px 12px; border-radius: 20px; font-size: 11px; font-weight: 500; }

.lp-how-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 44px; }
.lp-how-card { text-align: center; padding: 24px 16px; }
.lp-how-num { width: 44px; height: 44px; border-radius: 50%;
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2);
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; font-weight: 700; color: white; margin: 0 auto 14px; }
.lp-how-title { font-size: 14px; font-weight: 700; color: #f0e8ff; margin-bottom: 6px; }
.lp-how-desc { font-size: 12px; color: #8070a0; line-height: 1.5; }
.lp-how-arrow { font-size: 22px; color: rgba(255,46,126,0.4); display: flex;
    align-items: center; justify-content: center; padding-top: 24px; }

.lp-cta-section { text-align: center; padding: 80px 40px;
    background: linear-gradient(135deg, rgba(255,46,126,0.08), rgba(138,43,226,0.1));
    border-top: 1px solid rgba(255,46,126,0.15); border-radius: 30px 30px 0 0; }
.lp-cta-title { font-family: 'Playfair Display', serif; font-size: 40px; font-weight: 700;
    color: #f5f0ff; margin-bottom: 14px; }
.lp-cta-sub { font-size: 16px; color: #9080b0; margin-bottom: 36px; }

.lp-footer { background: rgba(10,6,18,0.95); border-top: 1px solid rgba(255,46,126,0.12);
    padding: 40px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px; }
.lp-footer-left { display: flex; align-items: center; gap: 10px; }
.lp-footer-feat { display: flex; gap: 24px; flex-wrap: wrap; }
.lp-footer-link { font-size: 12px; color: #7060a0; cursor: pointer; }
.lp-footer-link:hover { color: #FF2E7E; }
.lp-footer-right { font-size: 11px; color: #5040708; text-align: right; }

[data-testid="stChatMessage"] {
    animation: slideIn 0.3s ease-out;
    background: rgba(26, 16, 40, 0.8) !important;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 18px !important;
    padding: 16px 20px !important;
    margin-bottom: 12px !important;
}
@keyframes slideIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.stButton > button {
    background: linear-gradient(135deg, #FF2E7E 0%, #8A2BE2 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 10px 24px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    letter-spacing: 0.3px !important;
    transition: all 0.3s ease !important;
    cursor: pointer !important;
    box-shadow: 0 4px 20px rgba(255,46,126,0.35) !important;
    white-space: nowrap !important;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 30px rgba(255,46,126,0.5);
}
section[data-testid="stSidebar"] .stButton > button {
    white-space: normal !important;
    word-break: break-word !important;
    width: 100% !important;
    text-align: left !important;
    font-size: 12px !important;
    padding: 8px 12px !important;
    line-height: 1.3 !important;
    min-height: unset !important;
    height: auto !important;
}
</style>
"""

# ============================================================
#  LIGHT THEME CSS
# ============================================================
light_theme = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&family=Inter:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; }

.stApp {
    background: #f8f9fc !important;
    font-family: 'Inter', sans-serif !important;
}
.stApp > header { display: none !important; }
#MainMenu, footer { display: none !important; }
.stApp > div { background: #f8f9fc !important; }

.samsung-footer {
    text-align: center;
    padding: 20px;
    margin-top: 30px;
    border-top: 1px solid rgba(255,46,126,0.2);
    font-size: 11px;
    color: #888;
}
.samsung-logo {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(255,46,126,0.08);
    padding: 6px 16px;
    border-radius: 30px;
    margin-bottom: 8px;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #f5f0ff 100%) !important;
    border-right: 1px solid rgba(255,46,126,0.15) !important;
    width: 280px !important;
    box-shadow: 2px 0 10px rgba(0,0,0,0.05);
}

.block-container {
    padding: 0 2rem 5rem 2rem !important;
    max-width: 1200px !important;
    margin: 0 auto !important;
    position: relative;
    z-index: 1;
}

p, span, label, div, li {
    font-family: 'Inter', sans-serif !important;
    color: #1a1a2e !important;
}
h1, h2, h3, h4, h5, h6 {
    font-family: 'Playfair Display', serif !important;
    color: #2d1b36 !important;
    letter-spacing: -0.02em;
}

/* About Page Styles - Light */
.about-page {
    padding: 20px;
}
.about-hero {
    text-align: center;
    padding: 40px 20px;
    background: linear-gradient(135deg, rgba(255,46,126,0.05), rgba(138,43,226,0.05));
    border-radius: 30px;
    margin-bottom: 30px;
}
.about-hero-icon {
    font-size: 64px;
    margin-bottom: 20px;
}
.about-hero-title {
    font-size: 36px;
    font-weight: 700;
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 10px;
}
.about-hero-sub {
    font-size: 16px;
    color: #666;
}
.about-card {
    background: white;
    border: 1px solid rgba(255,46,126,0.15);
    border-radius: 20px;
    padding: 25px;
    margin-bottom: 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.03);
}
.about-card-title {
    font-size: 22px;
    font-weight: 700;
    color: #FF2E7E;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.about-card-text {
    font-size: 15px;
    line-height: 1.7;
    color: #4a4a6a;
}
.about-badge-container {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 15px;
}
.about-badge-large {
    background: rgba(255,46,126,0.1);
    border: 1px solid rgba(255,46,126,0.2);
    padding: 8px 18px;
    border-radius: 30px;
    font-size: 13px;
    color: #FF2E7E;
    font-weight: 500;
}

.about-section {
    background: linear-gradient(135deg, rgba(255,46,126,0.05), rgba(138,43,226,0.05));
    border: 1px solid rgba(255,46,126,0.15);
    border-radius: 20px;
    padding: 20px;
    margin-bottom: 20px;
}
.about-title {
    font-size: 18px;
    font-weight: 700;
    color: #FF2E7E;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.about-text {
    font-size: 14px;
    line-height: 1.6;
    color: #4a4a6a;
}
.about-highlight { color: #FF2E7E; font-weight: 600; }
.about-badge {
    display: inline-block;
    background: rgba(255,46,126,0.1);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    margin-right: 8px;
    margin-top: 8px;
}

.demo-section {
    background: linear-gradient(135deg, rgba(255,46,126,0.05), rgba(138,43,226,0.05));
    border: 1px solid rgba(255,46,126,0.15);
    border-radius: 20px;
    padding: 20px;
    margin: 20px 0;
}
.demo-title {
    font-size: 14px;
    font-weight: 600;
    color: #FF2E7E;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.demo-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
}
.demo-question {
    background: #ffffff;
    border: 1px solid rgba(255,46,126,0.2);
    border-radius: 12px;
    padding: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
}
.demo-question:hover {
    background: rgba(255,46,126,0.05);
    border-color: #FF2E7E;
    transform: translateX(5px);
}
.demo-category {
    font-size: 10px;
    color: #FF2E7E;
    margin-bottom: 5px;
    font-weight: 600;
}
.demo-text { font-size: 12px; line-height: 1.4; color: #1a1a2e; }

.an-welcome {
    text-align: center;
    padding: 20px 20px;
    animation: fadeInUp 0.6s ease-out;
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}
.an-welcome-icon {
    font-size: 56px;
    margin-bottom: 15px;
    animation: bounce 2s infinite;
}
@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-8px); }
}
.an-welcome-title {
    font-size: 26px;
    font-weight: 700;
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 10px;
}
.an-welcome-sub { font-size: 14px; color: #666; line-height: 1.6; }

[data-testid="stChatInput"] {
    background: #ffffff !important;
    border: 2px solid rgba(255,46,126,0.3) !important;
    border-radius: 60px !important;
    padding: 4px 8px 4px 24px !important;
    margin: 20px 0 20px 0 !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.05) !important;
}
[data-testid="stChatInput"]:hover {
    border-color: #FF2E7E !important;
    box-shadow: 0 8px 25px rgba(255,46,126,0.15) !important;
    transform: translateY(-2px);
}
[data-testid="stChatInput"]:focus-within {
    border-color: #FF2E7E !important;
    box-shadow: 0 8px 30px rgba(255,46,126,0.25) !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: #1a1a2e !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    padding: 14px 8px !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #aaa !important; font-size: 14px !important; }
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2) !important;
    border-radius: 50% !important;
    width: 44px !important;
    height: 44px !important;
    margin: 4px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 15px rgba(255,46,126,0.3) !important;
}
[data-testid="stChatInput"] button:hover {
    transform: scale(1.1) rotate(15deg) !important;
    box-shadow: 0 6px 25px rgba(255,46,126,0.5) !important;
}

.an-section-header {
    background: linear-gradient(135deg, rgba(255,46,126,0.08), rgba(138,43,226,0.08));
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.an-header-left { display: flex; align-items: center; gap: 16px; }
.an-icon-box {
    width: 48px;
    height: 48px;
    background: linear-gradient(135deg, rgba(255,46,126,0.1), rgba(138,43,226,0.1));
    border: 1px solid rgba(255,46,126,0.2);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
}
.an-feature-title { font-size: 24px; font-weight: 700; color: #2d1b36; }
.an-feature-sub { font-size: 12px; color: #888; }
.an-mode-chip {
    display: inline-block;
    background: rgba(255,46,126,0.12);
    color: #FF2E7E;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 10px;
}

.sb-pad { padding: 0 12px; }
.an-user-card {
    background: linear-gradient(135deg, rgba(255,46,126,0.08), rgba(138,43,226,0.08));
    border: 1px solid rgba(255,46,126,0.15);
    border-radius: 16px;
    padding: 14px;
    margin: 16px 0;
    display: flex;
    align-items: center;
    gap: 12px;
}
.an-avatar {
    width: 44px;
    height: 44px;
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 700;
    color: white;
}
.an-uname { font-size: 15px; font-weight: 600; color: #2d1b36; }
.an-ustatus { font-size: 10px; color: #4caf50; }
.an-nav-label {
    font-size: 11px;
    color: #FF2E7E;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
    margin: 20px 0 12px 0;
    display: block;
}

.an-hotlines {
    background: linear-gradient(135deg, rgba(220, 38, 38, 0.08), rgba(220, 38, 38, 0.03));
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 12px;
    padding: 14px;
    margin-top: 20px;
}
.an-hotlines-title {
    font-size: 11px;
    font-weight: 700;
    color: #ef4444;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 10px;
}
.an-hotline-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    font-size: 12px;
}
.an-hotline-label { color: #555; }
.an-hotline-num { color: #ef4444; font-weight: 700; }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #e0d8f0; }
::-webkit-scrollbar-thumb { background: linear-gradient(135deg, #FF2E7E, #8A2BE2); border-radius: 10px; }

/* ===== LANDING PAGE - Light ===== */
.lp-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 18px 40px; position: fixed; top: 0; left: 0; right: 0; z-index: 999;
    background: rgba(255,255,255,0.95); backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(255,46,126,0.15);
    box-shadow: 0 2px 20px rgba(0,0,0,0.06);
}
.lp-logo { display: flex; align-items: center; gap: 10px; }
.lp-logo-text { font-family: 'Playfair Display', serif; font-size: 20px; font-weight: 700;
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.lp-nav { display: flex; align-items: center; gap: 12px; }
.lp-nav-link { color: #6050a0; font-size: 13px; font-weight: 500; cursor: pointer;
    padding: 6px 14px; border-radius: 8px; transition: all 0.2s; }
.lp-nav-link:hover { color: #FF2E7E; background: rgba(255,46,126,0.06); }
.lp-theme-btn { background: #f0e8ff; border: 1px solid #d8c8f8;
    color: #7050b0; padding: 6px 14px; border-radius: 20px; font-size: 12px; cursor: pointer; }
.lp-cta-btn { background: linear-gradient(135deg, #FF2E7E, #8A2BE2); color: white;
    padding: 9px 22px; border-radius: 22px; font-size: 13px; font-weight: 600;
    cursor: pointer; box-shadow: 0 4px 15px rgba(255,46,126,0.3); border: none; }

.lp-hero { text-align: center; padding: 160px 20px 80px; background: linear-gradient(180deg, #faf8ff 0%, #f5f0ff 100%); }
.lp-hero-badge { display: inline-flex; align-items: center; gap: 8px;
    background: rgba(255,46,126,0.08); border: 1px solid rgba(255,46,126,0.25);
    padding: 7px 18px; border-radius: 30px; font-size: 12px; color: #FF2E7E;
    font-weight: 600; margin-bottom: 28px; letter-spacing: 0.5px; }
.lp-hero-title { font-family: 'Playfair Display', serif; font-size: 62px; font-weight: 700;
    line-height: 1.1; margin-bottom: 20px; color: #1a0e30; }
.lp-hero-title span { background: linear-gradient(135deg, #FF2E7E, #8A2BE2);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.lp-hero-sub { font-size: 18px; color: #7060a0; max-width: 560px; margin: 0 auto 40px; line-height: 1.7; }
.lp-hero-btns { display: flex; gap: 14px; justify-content: center; align-items: center; flex-wrap: wrap; }
.lp-btn-primary { background: linear-gradient(135deg, #FF2E7E, #8A2BE2); color: white;
    padding: 14px 32px; border-radius: 30px; font-size: 15px; font-weight: 600;
    cursor: pointer; box-shadow: 0 6px 25px rgba(255,46,126,0.35); transition: all 0.3s; display: inline-block; }
.lp-btn-secondary { background: white; border: 1.5px solid rgba(255,46,126,0.3);
    color: #5030a0; padding: 14px 32px; border-radius: 30px; font-size: 15px; font-weight: 500;
    cursor: pointer; transition: all 0.2s; display: inline-block; }
.lp-btn-secondary:hover { background: rgba(255,46,126,0.06); border-color: #FF2E7E; }

.lp-stats { display: flex; justify-content: center; gap: 50px; margin: 60px 0;
    flex-wrap: wrap; padding: 30px 40px; border-top: 1px solid rgba(255,46,126,0.1);
    border-bottom: 1px solid rgba(255,46,126,0.1); background: white; }
.lp-stat { text-align: center; }
.lp-stat-num { font-size: 32px; font-weight: 700;
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.lp-stat-label { font-size: 12px; color: #9080b0; margin-top: 4px; letter-spacing: 0.5px; }

.lp-section { padding: 70px 40px; max-width: 1100px; margin: 0 auto; }
.lp-section-tag { display: inline-block; background: rgba(255,46,126,0.08);
    border: 1px solid rgba(255,46,126,0.2); color: #FF2E7E; padding: 5px 14px;
    border-radius: 20px; font-size: 11px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; margin-bottom: 16px; }
.lp-section-title { font-family: 'Playfair Display', serif; font-size: 38px; font-weight: 700;
    color: #1a0e30; margin-bottom: 12px; }
.lp-section-sub { font-size: 16px; color: #7060a0; max-width: 560px; line-height: 1.7; }

.lp-features-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 44px; }
.lp-feat-card { background: white; border: 1px solid rgba(255,46,126,0.12);
    border-radius: 20px; padding: 28px; transition: all 0.3s;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04); }
.lp-feat-card:hover { border-color: rgba(255,46,126,0.3);
    transform: translateY(-4px); box-shadow: 0 12px 30px rgba(255,46,126,0.1); }
.lp-feat-icon { font-size: 32px; margin-bottom: 14px; }
.lp-feat-title { font-size: 17px; font-weight: 700; color: #1a0e30; margin-bottom: 8px; }
.lp-feat-desc { font-size: 13px; color: #8070a8; line-height: 1.6; }

.lp-data-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-top: 44px; }
.lp-data-card { background: rgba(138,43,226,0.04); border: 1px solid rgba(138,43,226,0.15);
    border-radius: 18px; padding: 24px; }
.lp-data-num { font-size: 36px; font-weight: 800; color: #8A2BE2; margin-bottom: 6px; }
.lp-data-label { font-size: 14px; font-weight: 600; color: #5030a0; margin-bottom: 6px; }
.lp-data-desc { font-size: 12px; color: #9080b8; line-height: 1.5; }
.lp-law-badges { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 20px; }
.lp-law-badge { background: rgba(255,46,126,0.07); border: 1px solid rgba(255,46,126,0.18);
    color: #d0306a; padding: 5px 12px; border-radius: 20px; font-size: 11px; font-weight: 500; }

.lp-how-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 44px; }
.lp-how-card { text-align: center; padding: 24px 16px; }
.lp-how-num { width: 44px; height: 44px; border-radius: 50%;
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2);
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; font-weight: 700; color: white; margin: 0 auto 14px; }
.lp-how-title { font-size: 14px; font-weight: 700; color: #1a0e30; margin-bottom: 6px; }
.lp-how-desc { font-size: 12px; color: #9080b8; line-height: 1.5; }

.lp-cta-section { text-align: center; padding: 80px 40px;
    background: linear-gradient(135deg, #fff5fa, #f0e8ff);
    border-top: 1px solid rgba(255,46,126,0.15); border-radius: 30px 30px 0 0; }
.lp-cta-title { font-family: 'Playfair Display', serif; font-size: 40px; font-weight: 700;
    color: #1a0e30; margin-bottom: 14px; }
.lp-cta-sub { font-size: 16px; color: #9080b0; margin-bottom: 36px; }

.lp-footer { background: #f5f0ff; border-top: 1px solid rgba(255,46,126,0.12);
    padding: 40px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px; }
.lp-footer-left { display: flex; align-items: center; gap: 10px; }
.lp-footer-feat { display: flex; gap: 24px; flex-wrap: wrap; }
.lp-footer-link { font-size: 12px; color: #9080b8; cursor: pointer; }
.lp-footer-link:hover { color: #FF2E7E; }

[data-testid="stChatMessage"] {
    animation: slideIn 0.3s ease-out;
    background: #ffffff !important;
    border: 1px solid rgba(255,46,126,0.15) !important;
    border-radius: 18px !important;
    padding: 16px 20px !important;
    margin-bottom: 12px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.03);
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: #faf5ff !important;
}
@keyframes slideIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.stButton > button {
    background: linear-gradient(135deg, #FF2E7E 0%, #8A2BE2 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 10px 24px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    letter-spacing: 0.3px !important;
    transition: all 0.3s ease !important;
    cursor: pointer !important;
    box-shadow: 0 4px 15px rgba(255,46,126,0.25) !important;
    white-space: nowrap !important;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 25px rgba(255,46,126,0.35);
}
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,46,126,0.08) !important;
    color: #d0306a !important;
    box-shadow: none !important;
    white-space: normal !important;
    word-break: break-word !important;
    width: 100% !important;
    text-align: left !important;
    font-size: 12px !important;
    padding: 8px 12px !important;
    line-height: 1.3 !important;
    min-height: unset !important;
    height: auto !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: linear-gradient(135deg, #FF2E7E, #8A2BE2) !important;
    color: white !important;
}
</style>
"""

# Apply theme based on session state
if st.session_state.theme == "dark":
    st.markdown(dark_theme, unsafe_allow_html=True)
else:
    st.markdown(light_theme, unsafe_allow_html=True)


# ============================================================
#  HELPERS
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
    """Display the About Awaz-e-Nisa page"""
    st.markdown("""
    <div class="about-page">
        <div class="about-hero">
            <div class="about-hero-icon">🌸</div>
            <div class="about-hero-title">About Awaz-e-Nisa</div>
            <div class="about-hero-sub">آوازِ نسواں - "Voice of Women"</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Mission Section
    st.markdown("""
    <div class="about-card">
        <div class="about-card-title">
            <span>⚖️</span> Our Mission
        </div>
        <div class="about-card-text">
            <strong class="about-highlight">Awaz-e-Nisa</strong> is a dedicated AI legal assistant designed specifically for 
            <strong class="about-highlight">Pakistani women</strong> and <strong class="about-highlight">legal professionals</strong> 
            working on family cases. We believe every woman deserves access to clear, accurate, and practical legal guidance.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # For Women Section
    st.markdown("""
    <div class="about-card">
        <div class="about-card-title">
            <span>🇵🇰</span> For Women
        </div>
        <div class="about-card-text">
            Get instant, clear answers about your legal rights - from divorce and custody to maintenance and inheritance. 
            No complex legal jargon, just practical guidance you can understand and act upon.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # For Lawyers Section
    st.markdown("""
    <div class="about-card">
        <div class="about-card-title">
            <span>⚖️</span> For Lawyers & Legal Pros
        </div>
        <div class="about-card-text">
            Quickly analyze case merits, prepare counter arguments, estimate timelines, and generate legal drafts. 
            Save hours of research time with AI-powered legal assistance.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # What We Cover Section
    st.markdown("""
    <div class="about-card">
        <div class="about-card-title">
            <span>✨</span> What We Cover
        </div>
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
    """, unsafe_allow_html=True)
    
    # How It Works Section
    st.markdown("""
    <div class="about-card">
        <div class="about-card-title">
            <span>💡</span> How It Works
        </div>
        <div class="about-card-text">
            <strong>1. Ask a Question</strong> - Type your legal question in simple language<br><br>
            <strong>2. Get Instant Analysis</strong> - Receive clear, actionable legal guidance<br><br>
            <strong>3. Deep Dive</strong> - Use our tools to analyze case merits, prepare counter arguments, estimate timelines, and generate legal drafts<br><br>
            <strong>4. Take Action</strong> - Download legal documents and know your next steps
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Privacy Section
    st.markdown("""
    <div class="about-card">
        <div class="about-card-title">
            <span>🔒</span> Privacy & Security
        </div>
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
#  LANDING PAGE
# ============================================================
if not st.session_state.logged_in and st.session_state.show_landing:
    is_dark = st.session_state.theme == "dark"
    
    # Floating header
    st.markdown(f"""
    <div class="lp-header">
        <div class="lp-logo">
            <span style="font-size:28px;">⚖️</span>
            <span class="lp-logo-text">AWAZ-E-NISA</span>
        </div>
        <div class="lp-nav">
            <span class="lp-nav-link" data-scroll="features" onclick="doScroll(this)">Features</span>
            <span class="lp-nav-link" data-scroll="training" onclick="doScroll(this)">Training Data</span>
            <span class="lp-nav-link" data-scroll="how" onclick="doScroll(this)">How It Works</span>
        </div>
        <div style="display:flex;gap:10px;align-items:center;">
            <span class="lp-theme-btn">{'☀️ Light' if is_dark else '🌙 Dark'}</span>
            <button class="lp-cta-btn" data-scroll="cta" onclick="doScroll(this)">Get Started Free</button>
        </div>
    </div>
    <div style="height:72px;"></div>
    <script>
    function doScroll(el) {{
        var target = el.getAttribute('data-scroll');
        var scrollMap = {{
            'features': 900,
            'training': 1600,
            'how': 2300,
            'cta': 3000
        }};
        var px = scrollMap[target] || 0;
        // Try scrolling the top-level Streamlit page
        try {{ window.top.scrollTo({{top: px, behavior: 'smooth'}}); }} catch(e) {{}}
        try {{ window.parent.scrollTo({{top: px, behavior: 'smooth'}}); }} catch(e) {{}}
        try {{ window.scrollTo({{top: px, behavior: 'smooth'}}); }} catch(e) {{}}
        // Also try finding element by id in parent docs
        try {{
            var docs = [document, window.parent.document, window.top.document];
            for (var d of docs) {{
                var el2 = d.getElementById('sec-' + target);
                if (el2) {{ el2.scrollIntoView({{behavior:'smooth'}}); break; }}
            }}
        }} catch(e) {{}}
    }}
    </script>
    """, unsafe_allow_html=True)

    # Theme toggle (actual Streamlit button, hidden style)
    c_tl, _, c_tr = st.columns([1,8,1])
    with c_tl:
        if st.button("🌙" if is_dark else "☀️", key="lp_theme"):
            st.session_state.theme = "light" if is_dark else "dark"
            st.rerun()

    # ── HERO ──
    st.markdown("""
    <div class="lp-hero">
        <div class="lp-hero-badge">🏆 Samsung Innovation Campus · Pakistan</div>
        <div class="lp-hero-title">
            Legal Rights for Every<br><span>Pakistani Woman</span>
        </div>
        <div class="lp-hero-sub">
            AI-powered legal assistant trained on 164 Pakistani law documents. 
            Get instant guidance on family law, cybercrime, and workplace rights in Urdu or English.
        </div>
        <div class="lp-hero-btns">
            <span class="lp-btn-primary" id="start-btn">⚖️ Start Free Consultation</span>
            <span class="lp-btn-secondary" id="learn-btn">▶ Watch Demo</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Actual hero button
    _, hc, _ = st.columns([1,2,1])
    with hc:
        if st.button("⚖️  Start Free Consultation  →", use_container_width=True, key="hero_cta"):
            st.session_state.show_landing = False
            st.rerun()

    # ── STATS ──
    st.markdown("""
    <div class="lp-stats">
        <div class="lp-stat"><div class="lp-stat-num">164</div><div class="lp-stat-label">LAW DOCUMENTS</div></div>
        <div class="lp-stat"><div class="lp-stat-num">6+</div><div class="lp-stat-label">LEGAL DOMAINS</div></div>
        <div class="lp-stat"><div class="lp-stat-num">2</div><div class="lp-stat-label">LANGUAGES</div></div>
        <div class="lp-stat"><div class="lp-stat-num">5</div><div class="lp-stat-label">AI TOOLS</div></div>
        <div class="lp-stat"><div class="lp-stat-num">87%</div><div class="lp-stat-label">ACCURACY RATE</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ── FEATURES ──
    st.markdown("""
    <div id="sec-features" class="lp-section">
        <div class="lp-section-tag">✨ Features</div>
        <div class="lp-section-title">Everything You Need to Know Your Rights</div>
        <div class="lp-section-sub">From instant legal Q&A to professional court documents — all powered by AI trained on Pakistani law.</div>
        <div class="lp-features-grid">
            <div class="lp-feat-card">
                <div class="lp-feat-icon">⚡</div>
                <div class="lp-feat-title">Instant Legal Chat</div>
                <div class="lp-feat-desc">Ask any question in Urdu or English. Get clear, cited answers with section numbers from MFLO, PECA, and more.</div>
            </div>
            <div class="lp-feat-card">
                <div class="lp-feat-icon">📊</div>
                <div class="lp-feat-title">Case Merits Analysis</div>
                <div class="lp-feat-desc">Understand the legal strengths and weaknesses of your case before approaching a lawyer or court.</div>
            </div>
            <div class="lp-feat-card">
                <div class="lp-feat-icon">⚔</div>
                <div class="lp-feat-title">Counter Arguments</div>
                <div class="lp-feat-desc">Know what arguments the opposing party will raise so you're fully prepared before your hearing.</div>
            </div>
            <div class="lp-feat-card">
                <div class="lp-feat-icon">📅</div>
                <div class="lp-feat-title">Timeline Estimator</div>
                <div class="lp-feat-desc">Get a realistic stage-by-stage timeline for your case based on Pakistani court procedures.</div>
            </div>
            <div class="lp-feat-card">
                <div class="lp-feat-icon">📄</div>
                <div class="lp-feat-title">Legal Draft Generator</div>
                <div class="lp-feat-desc">Generate professional legal notices, Khula petitions, custody applications, and police complaints as PDF.</div>
            </div>
            <div class="lp-feat-card">
                <div class="lp-feat-icon">📎</div>
                <div class="lp-feat-title">Document Analysis</div>
                <div class="lp-feat-desc">Upload your Nikah Nama, court notices, or any legal document — AI will explain what it means for you.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── TRAINING DATA ──
    st.markdown("""
    <div id="sec-training" class="lp-section" style="background: rgba(138,43,226,0.03); border-radius:30px; margin-top:0;">
        <div class="lp-section-tag">📚 Training Data</div>
        <div class="lp-section-title">Trained on 164 Pakistani Law Documents</div>
        <div class="lp-section-sub">Our RAG system retrieves answers directly from verified legal texts — not hallucination.</div>
        <div class="lp-data-grid">
            <div class="lp-data-card">
                <div class="lp-data-num">50+</div>
                <div class="lp-data-label">Family Law Texts</div>
                <div class="lp-data-desc">Muslim Family Laws Ordinance 1961, Family Courts Act 1964, Child Marriage Restraint Act, Guardians & Wards Act 1890</div>
                <div class="lp-law-badges">
                    <span class="lp-law-badge">MFLO 1961</span>
                    <span class="lp-law-badge">FCA 1964</span>
                    <span class="lp-law-badge">CMRA</span>
                    <span class="lp-law-badge">GWA 1890</span>
                </div>
            </div>
            <div class="lp-data-card">
                <div class="lp-data-num">40+</div>
                <div class="lp-data-label">Cybercrime & Digital Rights</div>
                <div class="lp-data-desc">Prevention of Electronic Crimes Act 2016, FIA Cybercrime Wing procedures, Digital Rights Foundation guidelines</div>
                <div class="lp-law-badges">
                    <span class="lp-law-badge">PECA 2016</span>
                    <span class="lp-law-badge">FIA Rules</span>
                    <span class="lp-law-badge">NR3C</span>
                </div>
            </div>
            <div class="lp-data-card">
                <div class="lp-data-num">35+</div>
                <div class="lp-data-label">Workplace & Rights Laws</div>
                <div class="lp-data-desc">Protection Against Harassment Act 2010, Provincial Labour Laws, Women Protection Acts across all 4 provinces</div>
                <div class="lp-law-badges">
                    <span class="lp-law-badge">HAW 2010</span>
                    <span class="lp-law-badge">Labour Laws</span>
                    <span class="lp-law-badge">WPA Punjab</span>
                </div>
            </div>
            <div class="lp-data-card">
                <div class="lp-data-num">39+</div>
                <div class="lp-data-label">Inheritance & Property</div>
                <div class="lp-data-desc">Muslim Personal Law (Shariat) Application Act, West Pakistan Muslim Personal Law, Succession Act — covering Haq Mehr, Wirasat, and property rights</div>
                <div class="lp-law-badges">
                    <span class="lp-law-badge">Shariat Act</span>
                    <span class="lp-law-badge">Succession</span>
                    <span class="lp-law-badge">Haq Mehr</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── HOW IT WORKS ──
    st.markdown("""
    <div id="sec-how" class="lp-section">
        <div class="lp-section-tag">💡 How It Works</div>
        <div class="lp-section-title">From Question to Legal Action in Minutes</div>
        <div class="lp-section-sub">No lawyer needed for your first consultation. Just type and get answers.</div>
        <div class="lp-how-grid">
            <div class="lp-how-card">
                <div class="lp-how-num">1</div>
                <div class="lp-how-title">Ask Your Question</div>
                <div class="lp-how-desc">Type in Urdu, Roman Urdu, or English. No legal knowledge required.</div>
            </div>
            <div class="lp-how-card">
                <div class="lp-how-num">2</div>
                <div class="lp-how-title">AI Searches the Law</div>
                <div class="lp-how-desc">RAG system finds relevant sections from 164 verified Pakistani legal documents.</div>
            </div>
            <div class="lp-how-card">
                <div class="lp-how-num">3</div>
                <div class="lp-how-title">Get Cited Answers</div>
                <div class="lp-how-desc">Receive clear guidance with exact section numbers like "MFLO Section 6" so you can verify.</div>
            </div>
            <div class="lp-how-card">
                <div class="lp-how-num">4</div>
                <div class="lp-how-title">Download & Act</div>
                <div class="lp-how-desc">Generate legal drafts as PDF, know your timeline, and walk into court prepared.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── CTA SECTION ──
    st.markdown("""
    <div id="sec-cta" class="lp-cta-section">
        <div class="lp-cta-title">Your Voice. Your Rights. Your Law.</div>
        <div class="lp-cta-sub">Join thousands of Pakistani women who've used Awaz-e-Nisa to understand their legal rights.</div>
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
    <div class="lp-footer">
        <div class="lp-footer-left">
            <span style="font-size:22px;">⚖️</span>
            <div>
                <div style="font-size:14px;font-weight:700;background:linear-gradient(135deg,#FF2E7E,#8A2BE2);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">AWAZ-E-NISA</div>
                <div style="font-size:10px;color:#9080b0;">آوازِ نسواں · Voice of Women</div>
            </div>
        </div>
        <div class="lp-footer-feat">
            <span class="lp-footer-link">⚡ Legal Chat</span>
            <span class="lp-footer-link">📊 Case Merits</span>
            <span class="lp-footer-link">⚔ Counter Arguments</span>
            <span class="lp-footer-link">📅 Timeline</span>
            <span class="lp-footer-link">📄 Legal Draft</span>
            <span class="lp-footer-link">📎 Doc Analysis</span>
        </div>
        <div style="font-size:11px;color:#9080b0;text-align:right;">
            <div>🚀 Samsung Innovation Campus</div>
            <div style="margin-top:4px;">© 2026 Awaz-e-Nisa · Pakistan</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
#  LOGIN PAGE
# ============================================================
elif not st.session_state.logged_in and not st.session_state.show_landing:
    # Mini header
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

        tab1, tab2 = st.tabs(["🔑 Login", "✨ Create Account"])

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
                        st.error("❌ Invalid credentials")
            with c2:
                if st.button("🔑 Guest", use_container_width=True, key="btn_guest"):
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
                        st.warning("⚠️ Password must be at least 4 characters")
                    elif add_user(nu, np_):
                        st.success("✅ Account created! Please login.")
                    else:
                        st.error("❌ Username taken")
                else:
                    st.warning("⚠️ Fill all fields")

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

    # Load AI chains
    if "rag" not in st.session_state:
        with st.spinner("🚀 Loading AI model..."):
            from legal_advisor import (rag_chain, merits_chain,
                                       opposition_chain, timeline_chain, draft_chain)
            st.session_state.rag = rag_chain
            st.session_state.m_chain = merits_chain
            st.session_state.o_chain = opposition_chain
            st.session_state.t_chain = timeline_chain
            st.session_state.d_chain = draft_chain
            show_toast("✅ AI model loaded!")

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

        # Theme Toggle - compact in sidebar
        st.markdown("<span class='an-nav-label'>🎨 Appearance</span>", unsafe_allow_html=True)
        cur_theme = st.session_state.theme
        if st.button(f"{'☀️ Switch to Light' if cur_theme == 'dark' else '🌙 Switch to Dark'}", use_container_width=True, key="sidebar_theme_btn"):
            st.session_state.theme = "light" if cur_theme == "dark" else "dark"
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

    # ── STICKY TOP HEADER BAR ──
    cur_t = st.session_state.theme
    th_icon = "☀️" if cur_t == "dark" else "🌙"
    th_label = "Light" if cur_t == "dark" else "Dark"
    hdr_bg   = "rgba(15,10,26,0.95)" if cur_t == "dark" else "rgba(255,255,255,0.97)"
    hdr_bdr  = "rgba(255,46,126,0.18)" if cur_t == "dark" else "rgba(255,46,126,0.15)"
    hdr_sub  = "#9080a8" if cur_t == "dark" else "#9070b0"

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

    # Theme toggle button in header row (actual Streamlit)
    _, _, th_col = st.columns([6, 1, 1])
    with th_col:
        if st.button(f"{th_icon} {th_label}", key="hdr_theme_btn"):
            st.session_state.theme = "light" if cur_t == "dark" else "dark"
            st.rerun()

    # Show About Page
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
        
        # Add Samsung footer on About page
        st.markdown("""
        <div class="samsung-footer">
            <div class="samsung-logo">
                <span class="samsung-icon">🚀</span>
                <span class="samsung-text">SAMSUNG INNOVATION CAMPUS</span>
            </div>
            <div>Powered by Samsung Innovation Campus | Built for Pakistani Women</div>
            <div style="font-size: 9px; margin-top: 5px;">© 2024 Awaz-e-Nisa · All Rights Reserved</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Show Legal Chat
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
                <div class="demo-title">
                    <span>💡</span> Try Asking These Questions
                </div>
                <div class="demo-grid">
                    <div class="demo-question">
                        <div class="demo-category">🔴 Family Law</div>
                        <div class="demo-text">My husband married a second woman without my permission and left me with 2 children. What should I do?</div>
                    </div>
                    <div class="demo-question">
                        <div class="demo-category">💰 Financial Rights</div>
                        <div class="demo-text">How much maintenance (kharcha) can I claim for myself and my 2 children?</div>
                    </div>
                    <div class="demo-question">
                        <div class="demo-category">👶 Child Custody</div>
                        <div class="demo-text">Can my husband take my children away from me after divorce?</div>
                    </div>
                    <div class="demo-question">
                        <div class="demo-category">💻 Cybercrime</div>
                        <div class="demo-text">Someone is blackmailing me with my private photos. How to file a complaint?</div>
                    </div>
                    <div class="demo-question">
                        <div class="demo-category">📝 Khula/Talaq</div>
                        <div class="demo-text">What is the procedure for Khula and how long does it take?</div>
                    </div>
                    <div class="demo-question">
                        <div class="demo-category">🏢 Workplace</div>
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
                    if st.button("📊 Case Merits", key="qa1"):
                        with st.spinner("Analyzing..."):
                            result = st.session_state.m_chain.invoke(prompt)
                        st.markdown("### 📊 Case Merits Analysis")
                        st.markdown(result)
                with col2:
                    if st.button("⚔ Counter", key="qa2"):
                        with st.spinner("Analyzing..."):
                            result = st.session_state.o_chain.invoke(prompt)
                        st.markdown("### ⚔ Counter Arguments")
                        st.markdown(result)
                with col3:
                    if st.button("📅 Timeline", key="qa3"):
                        with st.spinner("Analyzing..."):
                            result = st.session_state.t_chain.invoke(prompt)
                        st.markdown("### 📅 Timeline Estimate")
                        st.markdown(result)
                with col4:
                    if st.button("📄 Draft", key="qa4"):
                        with st.spinner("Generating..."):
                            result = st.session_state.d_chain.invoke(prompt)
                        st.markdown("### 📄 Legal Draft")
                        st.markdown(result)
                        pdf_path = create_pdf(result)
                        with open(pdf_path, "rb") as f:
                            st.download_button("📥 Download PDF", f, file_name="legal_draft.pdf")
                        os.unlink(pdf_path)
        
        # ── FOOTER with clickable feature pills ──
        st.markdown("""
        <div style="margin-top:40px;padding:20px 0 8px;border-top:1px solid rgba(255,46,126,0.15);">
            <div style="text-align:center;font-size:10px;color:#FF2E7E;font-weight:700;
                        letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;">
                🎯 Jump to a Feature
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Add custom CSS to make these buttons look like pills
        st.markdown("""
        <style>
        div[data-testid="stHorizontalBlock"] > div > div > div > .stButton > button {
            background: rgba(255,46,126,0.08) !important;
            border: 1px solid rgba(255,46,126,0.25) !important;
            color: #FF2E7E !important;
            border-radius: 22px !important;
            padding: 6px 14px !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            box-shadow: none !important;
            transition: all 0.2s !important;
            white-space: nowrap !important;
        }
        div[data-testid="stHorizontalBlock"] > div > div > div > .stButton > button:hover {
            background: rgba(255,46,126,0.18) !important;
            border-color: #FF2E7E !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(255,46,126,0.2) !important;
        }
        </style>
        """, unsafe_allow_html=True)

        fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)
        with fc1:
            if st.button("⚡ Legal Chat", key="ft_chat", use_container_width=True):
                st.session_state.active_feature = "Legal Chat"; st.rerun()
        with fc2:
            if st.button("📊 Case Merits", key="ft_merits", use_container_width=True):
                st.session_state.active_feature = "Case Merits"; st.rerun()
        with fc3:
            if st.button("⚔ Counter Args", key="ft_counter", use_container_width=True):
                st.session_state.active_feature = "Counter Arguments"; st.rerun()
        with fc4:
            if st.button("📅 Timeline", key="ft_timeline", use_container_width=True):
                st.session_state.active_feature = "Timeline Estimator"; st.rerun()
        with fc5:
            if st.button("📄 Legal Draft", key="ft_draft", use_container_width=True):
                st.session_state.active_feature = "Legal Draft"; st.rerun()
        with fc6:
            if st.button("🌸 About", key="ft_about", use_container_width=True):
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

    # ========== OTHER FEATURES ==========
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
        if st.button("📊 Analyze Merits", use_container_width=True):
            if query.strip():
                with st.spinner("Analyzing case strengths..."):
                    result = st.session_state.m_chain.invoke(query)
                st.markdown("### 📊 Case Merits Analysis")
                st.markdown(result)
            else:
                st.warning("Please describe your case first.")
        if st.button("← Back to Chat"):
            st.session_state.active_feature = "Legal Chat"
            st.rerun()

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
        if st.button("📅 Estimate Timeline", use_container_width=True):
            if query.strip():
                with st.spinner("Estimating timeline..."):
                    result = st.session_state.t_chain.invoke(query)
                st.markdown("### 📅 Estimated Timeline")
                st.markdown(result)
            else:
                st.warning("Please describe your case first.")
        if st.button("← Back to Chat"):
            st.session_state.active_feature = "Legal Chat"
            st.rerun()

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
        if st.button("📄 Generate Draft", use_container_width=True):
            if query.strip():
                with st.spinner(f"Generating {doc_type}..."):
                    full_query = f"Generate a {doc_type} based on these details: {query}"
                    result = st.session_state.d_chain.invoke(full_query)
                st.markdown(f"### 📄 {doc_type}")
                st.markdown(result)
                pdf_path = create_pdf(result, title=doc_type)
                with open(pdf_path, "rb") as f:
                    st.download_button("📥 Download PDF", data=f, file_name=f"{doc_type.lower().replace(' ', '_')}.pdf", mime="application/pdf")
                os.unlink(pdf_path)
            else:
                st.warning("Please provide case details first.")
        if st.button("← Back to Chat"):
            st.session_state.active_feature = "Legal Chat"
            st.rerun()
import streamlit as st
import os
import shutil
import pytesseract
import pdfplumber
from PIL import Image
import cv2
import numpy as np
import tempfile
import whisper
import warnings
import uuid
import random
import re
from datetime import datetime
from fpdf import FPDF
from database import init_db, add_user, verify_user, save_chat_message, get_chat_history, delete_chat_history
from streamlit_mic_recorder import mic_recorder
from legal_advisor import is_legal_query

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

# ============================================================
#  WHISPER MODEL (FROM OLD APP)
# ============================================================
@st.cache_resource
def load_whisper_model():
    """Load Whisper model - from old app configuration"""
    return whisper.load_model("small")  # Using "small" model like old app

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
    "theme": "dark",
    "expanded_panels": {},
    "last_audio_id": None,
    "username": "",
    "active_session_id": None,
    "chat_sessions": {},
    "processing_audio": False,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ============================================================
#  DARK THEME CSS
# ============================================================
dark_theme = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300;1,400&family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

:root {
    --c-bg: #06050e;
    --c-bg2: #0b0917;
    --c-surface: #100e1d;
    --c-surface2: #161329;
    --c-surface3: #1e1a35;
    --c-surface-glass: rgba(22, 19, 41, 0.7);
    --c-border: rgba(180, 130, 255, 0.08);
    --c-border-mid: rgba(180, 130, 255, 0.14);
    --c-border-vivid: rgba(220, 80, 130, 0.30);
    --c-text: #ede8f8;
    --c-text-muted: #9d92bc;
    --c-text-dim: #5a5278;
    --c-rose: #e8487a;
    --c-rose-light: #f07fa0;
    --c-rose-glow: rgba(232, 72, 122, 0.18);
    --c-violet: #7c3aed;
    --c-violet-light: #a78bfa;
    --c-violet-glow: rgba(124, 58, 237, 0.15);
    --c-gold: #c9a84c;
    --c-gold-light: #e4c97a;
    --c-red-alert: #f05070;
    --c-green: #50c87a;
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 16px;
    --radius-xl: 22px;
    --radius-2xl: 30px;
    --radius-pill: 999px;
    --shadow-sm: 0 2px 8px rgba(0,0,0,0.35);
    --shadow-md: 0 6px 24px rgba(0,0,0,0.45);
    --shadow-lg: 0 16px 48px rgba(0,0,0,0.55);
    --shadow-rose: 0 8px 32px rgba(232,72,122,0.20);
    --shadow-violet: 0 8px 32px rgba(124,58,237,0.20);
    --font-display: 'Cormorant Garamond', Georgia, serif;
    --font-body: 'DM Sans', system-ui, sans-serif;
    --font-mono: 'DM Mono', monospace;
}

*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

.stApp {
    background: var(--c-bg) !important;
    background-image:
        radial-gradient(ellipse 80% 50% at 20% -10%, rgba(124,58,237,0.08) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 85% 110%, rgba(232,72,122,0.06) 0%, transparent 55%) !important;
    font-family: var(--font-body) !important;
    min-height: 100vh;
}
.stApp > header, #MainMenu, footer { display: none !important; }

.block-container {
    padding: 0 2.5rem 3rem 2.5rem !important;
    max-width: 1380px !important;
    margin: 0 auto !important;
}

/* ── SIDEBAR ── */
section[data-testid="stSidebar"] {
    background: var(--c-bg2) !important;
    border-right: 1px solid var(--c-border-mid) !important;
    width: 288px !important;
}
section[data-testid="stSidebar"] > div { padding: 0 !important; }
section[data-testid="stSidebar"] .block-container { padding: 1.5rem 1.25rem 2rem !important; }

/* ── CHAT MESSAGES ── */
[data-testid="stChatMessage"] {
    background: var(--c-surface) !important;
    border: 1px solid var(--c-border-mid) !important;
    border-radius: var(--radius-xl) !important;
    padding: 22px 26px !important;
    margin-bottom: 14px !important;
    box-shadow: var(--shadow-sm) !important;
    animation: msgFadeUp 0.35s cubic-bezier(0.22,0.68,0,1.2) both;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageContent"]) {
    backdrop-filter: blur(8px);
}

/* ── CHAT INPUT ── */
[data-testid="stChatInput"] textarea {
    background: var(--c-surface2) !important;
    border: 1.5px solid var(--c-border-mid) !important;
    border-radius: 14px !important;
    color: var(--c-text) !important;
    font-family: var(--font-body) !important;
    font-size: 14px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--c-rose) !important;
    box-shadow: 0 0 0 3px var(--c-rose-glow) !important;
}

/* ── BUTTONS ── */
.stButton > button {
    background: linear-gradient(135deg, var(--c-rose) 0%, var(--c-violet) 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: var(--radius-md) !important;
    font-family: var(--font-body) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 0.02em !important;
    padding: 10px 18px !important;
    transition: all 0.25s cubic-bezier(0.4,0,0.2,1) !important;
    box-shadow: 0 2px 10px rgba(232,72,122,0.18) !important;
    position: relative !important;
    overflow: hidden !important;
}
.stButton > button::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.08) 0%, transparent 60%);
    pointer-events: none;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(232,72,122,0.30) !important;
    filter: brightness(1.08) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── TYPOGRAPHY ── */
h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-display) !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
    color: var(--c-text) !important;
    -webkit-text-fill-color: var(--c-text) !important;
    background: none !important;
    -webkit-background-clip: unset !important;
    background-clip: unset !important;
}

/* ── SELECTBOX / INPUTS ── */
[data-baseweb="select"] > div {
    background: var(--c-surface2) !important;
    border: 1.5px solid var(--c-border-mid) !important;
    border-radius: var(--radius-md) !important;
    color: var(--c-text) !important;
}
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--c-surface2) !important;
    border: 1.5px solid var(--c-border-mid) !important;
    border-radius: var(--radius-md) !important;
    color: var(--c-text) !important;
    font-family: var(--font-body) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--c-rose) !important;
    box-shadow: 0 0 0 3px var(--c-rose-glow) !important;
}

/* ── DIVIDER ── */
hr { border-color: var(--c-border-mid) !important; margin: 12px 0 !important; }

/* ════════════════════════════════════════
   LANDING PAGE
════════════════════════════════════════ */
.hero-section {
    text-align: center;
    padding: 96px 32px 72px;
    position: relative;
}
.hero-section::before {
    content: '';
    position: absolute;
    top: 0; left: 50%; transform: translateX(-50%);
    width: 600px; height: 600px;
    background: radial-gradient(ellipse, rgba(124,58,237,0.10) 0%, transparent 70%);
    pointer-events: none;
}

.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: rgba(232,72,122,0.08);
    border: 1px solid rgba(232,72,122,0.22);
    padding: 7px 22px;
    border-radius: var(--radius-pill);
    font-family: var(--font-body);
    font-size: 11px;
    font-weight: 700;
    color: var(--c-rose-light);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 36px;
}

.hero-title {
    font-family: var(--font-display);
    font-size: clamp(52px, 7.5vw, 88px);
    font-weight: 300;
    line-height: 1.08;
    margin-bottom: 28px;
    color: var(--c-text);
    letter-spacing: -0.02em;
}
.hero-title strong {
    font-weight: 600;
}

.hero-subtitle {
    font-family: var(--font-body);
    font-size: 17px;
    line-height: 1.75;
    max-width: 560px;
    margin: 0 auto 28px;
    color: var(--c-text-muted);
    font-weight: 300;
}

.hero-gradient-text {
    background: linear-gradient(135deg, var(--c-rose) 0%, var(--c-violet-light) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 600;
}

/* Stats */
.stats-bar {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    background: var(--c-surface);
    border: 1px solid var(--c-border-mid);
    border-radius: var(--radius-xl);
    overflow: hidden;
    margin: 48px 0;
    box-shadow: var(--shadow-md);
}
.stat-item {
    padding: 36px 20px;
    text-align: center;
    position: relative;
    transition: background 0.25s ease;
}
.stat-item::after {
    content: '';
    position: absolute;
    right: 0; top: 20%; height: 60%;
    width: 1px;
    background: var(--c-border-mid);
}
.stat-item:last-child::after { display: none; }
.stat-item:hover { background: var(--c-surface2); }
.stat-number {
    font-family: var(--font-display);
    font-size: 46px;
    font-weight: 600;
    background: linear-gradient(135deg, var(--c-rose), var(--c-violet-light));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1;
    margin-bottom: 8px;
}
.stat-label {
    font-family: var(--font-body);
    font-size: 11px;
    color: var(--c-text-dim);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 600;
}

/* Feature Cards */
.features-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    margin: 40px 0;
}
.feature-card {
    background: var(--c-surface);
    border: 1px solid var(--c-border-mid);
    border-radius: var(--radius-xl);
    padding: 34px 30px;
    transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
    position: relative;
    overflow: hidden;
}
.feature-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, var(--c-rose), var(--c-violet));
    opacity: 0;
    transition: opacity 0.3s ease;
}
.feature-card:hover {
    transform: translateY(-5px);
    border-color: var(--c-border-vivid);
    box-shadow: var(--shadow-rose);
}
.feature-card:hover::before { opacity: 1; }
.feature-icon {
    width: 52px; height: 52px;
    border-radius: var(--radius-md);
    background: rgba(232,72,122,0.10);
    border: 1px solid rgba(232,72,122,0.20);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    margin-bottom: 22px;
}
.feature-title {
    font-family: var(--font-display);
    font-size: 19px;
    font-weight: 600;
    color: var(--c-text);
    margin-bottom: 10px;
    letter-spacing: -0.01em;
}
.feature-desc {
    font-family: var(--font-body);
    font-size: 13.5px;
    color: var(--c-text-muted);
    line-height: 1.65;
    font-weight: 300;
}

/* Training Grid */
.training-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
    margin: 40px 0;
}
.training-card {
    background: rgba(124,58,237,0.06);
    border: 1px solid rgba(124,58,237,0.14);
    border-radius: var(--radius-xl);
    padding: 34px 30px;
    transition: border-color 0.25s ease;
}
.training-card:hover { border-color: rgba(124,58,237,0.28); }
.training-number {
    font-family: var(--font-display);
    font-size: 56px;
    font-weight: 300;
    color: var(--c-violet-light);
    margin-bottom: 8px;
    line-height: 1;
}
.training-title {
    font-family: var(--font-display);
    font-size: 19px;
    font-weight: 600;
    color: var(--c-text);
    margin-bottom: 10px;
}
.training-text {
    font-family: var(--font-body);
    font-size: 13.5px;
    color: var(--c-text-muted);
    line-height: 1.6;
    font-weight: 300;
}
.training-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    margin-top: 18px;
}
.training-tag {
    background: rgba(232,72,122,0.10);
    border: 1px solid rgba(232,72,122,0.18);
    color: var(--c-rose-light);
    padding: 4px 13px;
    border-radius: var(--radius-pill);
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 500;
}

/* How It Works */
.howit-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    margin: 40px 0;
}
.howit-card {
    text-align: center;
    padding: 36px 22px;
    background: var(--c-surface);
    border: 1px solid var(--c-border-mid);
    border-radius: var(--radius-xl);
    position: relative;
    transition: transform 0.25s ease, border-color 0.25s ease;
}
.howit-card:hover { transform: translateY(-4px); border-color: var(--c-border-vivid); }
.howit-number {
    width: 48px; height: 48px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--c-rose), var(--c-violet));
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-display);
    font-size: 20px;
    font-weight: 600;
    color: white;
    margin: 0 auto 18px;
    box-shadow: 0 4px 16px rgba(232,72,122,0.25);
}
.howit-title {
    font-family: var(--font-display);
    font-size: 17px;
    font-weight: 600;
    color: var(--c-text);
    margin-bottom: 10px;
}
.howit-text {
    font-family: var(--font-body);
    font-size: 13px;
    color: var(--c-text-muted);
    line-height: 1.65;
    font-weight: 300;
}

/* CTA */
.cta-section {
    border-radius: var(--radius-2xl);
    padding: 88px 56px;
    text-align: center;
    background: linear-gradient(135deg, rgba(232,72,122,0.08) 0%, rgba(124,58,237,0.12) 100%);
    border: 1px solid rgba(232,72,122,0.18);
    position: relative;
    overflow: hidden;
    margin: 56px 0;
}
.cta-section::before {
    content: '';
    position: absolute;
    top: -100px; right: -100px;
    width: 400px; height: 400px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(124,58,237,0.08) 0%, transparent 70%);
    pointer-events: none;
}
.cta-title {
    font-family: var(--font-display);
    font-size: 52px;
    font-weight: 300;
    color: var(--c-text);
    margin-bottom: 18px;
    letter-spacing: -0.02em;
}
.cta-text {
    font-family: var(--font-body);
    font-size: 16px;
    color: var(--c-text-muted);
    margin-bottom: 36px;
    max-width: 480px;
    margin-left: auto;
    margin-right: auto;
    line-height: 1.7;
    font-weight: 300;
}

/* Footer */
.premium-footer {
    border-top: 1px solid var(--c-border-mid);
    padding: 44px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 24px;
    margin-top: 48px;
}
.footer-logo { display: flex; align-items: center; gap: 14px; }
.footer-logo-text {
    font-family: var(--font-display);
    font-size: 20px;
    font-weight: 600;
    background: linear-gradient(135deg, var(--c-rose), var(--c-violet));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: 0.05em;
}
.footer-links { display: flex; gap: 32px; flex-wrap: wrap; }
.footer-link { font-family: var(--font-body); font-size: 13px; color: var(--c-text-dim); }
.footer-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(232,72,122,0.07);
    border: 1px solid rgba(232,72,122,0.15);
    padding: 6px 16px;
    border-radius: var(--radius-pill);
    margin-bottom: 8px;
}

/* ════════════════════════════════════════
   MAIN APP UI
════════════════════════════════════════ */
.law-tip-box {
    padding: 14px 16px;
    background: var(--c-surface2);
    border-left: 3px solid var(--c-rose);
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    margin: 12px 0;
}
.tip-title {
    font-family: var(--font-body);
    color: var(--c-rose);
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 5px;
}
.tip-text {
    font-family: var(--font-body);
    color: var(--c-text-muted);
    font-size: 12.5px;
    line-height: 1.5;
    font-weight: 300;
}

.mode-tag {
    display: inline-block;
    background: linear-gradient(90deg, var(--c-rose), var(--c-violet));
    color: white !important;
    padding: 3px 11px;
    border-radius: var(--radius-pill);
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.05em;
    margin-bottom: 10px;
}

.demo-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin: 24px 0;
}
.demo-question {
    background: var(--c-surface2);
    border: 1px solid var(--c-border-mid);
    border-radius: var(--radius-lg);
    padding: 16px 18px;
    cursor: pointer;
    transition: all 0.22s ease;
}
.demo-question:hover {
    border-color: var(--c-rose);
    background: rgba(232,72,122,0.05);
    transform: translateX(3px);
}
.demo-category {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--c-rose);
    font-weight: 500;
    letter-spacing: 0.08em;
    margin-bottom: 7px;
    text-transform: uppercase;
}
.demo-text {
    font-family: var(--font-body);
    font-size: 13px;
    color: var(--c-text-muted);
    line-height: 1.55;
    font-weight: 300;
}

.an-user-card {
    background: linear-gradient(135deg, rgba(232,72,122,0.07), rgba(124,58,237,0.07));
    border: 1px solid var(--c-border-mid);
    border-radius: var(--radius-lg);
    padding: 14px 16px;
    margin: 14px 0;
    display: flex;
    align-items: center;
    gap: 12px;
}
.an-avatar {
    width: 40px; height: 40px;
    background: linear-gradient(135deg, var(--c-rose), var(--c-violet));
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-display);
    font-size: 17px;
    font-weight: 600;
    color: white !important;
    flex-shrink: 0;
    box-shadow: 0 3px 12px rgba(232,72,122,0.25);
}
.an-nav-label {
    font-family: var(--font-body);
    font-size: 10px;
    color: var(--c-rose);
    text-transform: uppercase;
    letter-spacing: 1.8px;
    font-weight: 700;
    margin: 18px 0 10px;
    display: block;
}

.an-hotlines {
    background: rgba(240,80,112,0.07);
    border: 1px solid rgba(240,80,112,0.18);
    border-radius: var(--radius-lg);
    padding: 14px 16px;
    margin-top: 18px;
}
.an-hotlines-title {
    font-family: var(--font-body);
    font-size: 10px;
    font-weight: 700;
    color: var(--c-red-alert);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 10px;
}
.an-hotline-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid rgba(240,80,112,0.10);
}
.an-hotline-row:last-child { border-bottom: none; }
.an-hotline-label { font-family: var(--font-body); font-size: 12px; color: var(--c-text-muted); font-weight: 300; }
.an-hotline-num { font-family: var(--font-mono); font-size: 12px; color: var(--c-red-alert); font-weight: 500; }

.an-section-header {
    background: linear-gradient(135deg, rgba(232,72,122,0.06), rgba(124,58,237,0.06));
    border: 1px solid var(--c-border-mid);
    border-radius: var(--radius-xl);
    padding: 22px 28px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.an-feature-title {
    font-family: var(--font-display);
    font-size: 22px;
    font-weight: 600;
    color: var(--c-text);
    letter-spacing: -0.01em;
}

/* ── ANIMATIONS ── */
@keyframes msgFadeUp {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--c-bg); }
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--c-rose), var(--c-violet));
    border-radius: 10px;
}
</style>
"""

# ============================================================
#  LIGHT THEME CSS
# ============================================================
light_theme = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300;1,400&family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

:root {
    --c-bg: #fdf8f6;
    --c-bg2: #faf4f2;
    --c-surface: #ffffff;
    --c-surface2: #fdf6f4;
    --c-surface3: #f8f0ee;
    --c-border: rgba(180,60,100,0.08);
    --c-border-mid: rgba(180,60,100,0.14);
    --c-border-vivid: rgba(200,50,90,0.28);
    --c-text: #1a0e18;
    --c-text-muted: #5a3a50;
    --c-text-dim: #a888a0;
    --c-rose: #c0335a;
    --c-rose-light: #e05578;
    --c-rose-glow: rgba(192,51,90,0.12);
    --c-violet: #6b21a8;
    --c-violet-light: #9333ea;
    --c-violet-glow: rgba(107,33,168,0.10);
    --c-gold: #b5860a;
    --c-red-alert: #c0284a;
    --c-green: #166534;
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 16px;
    --radius-xl: 22px;
    --radius-2xl: 30px;
    --radius-pill: 999px;
    --shadow-sm: 0 1px 6px rgba(180,60,100,0.07);
    --shadow-md: 0 4px 18px rgba(180,60,100,0.09);
    --shadow-lg: 0 12px 40px rgba(180,60,100,0.12);
    --shadow-rose: 0 8px 28px rgba(192,51,90,0.14);
    --font-display: 'Cormorant Garamond', Georgia, serif;
    --font-body: 'DM Sans', system-ui, sans-serif;
    --font-mono: 'DM Mono', monospace;
}

*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

.stApp {
    background: var(--c-bg) !important;
    background-image: radial-gradient(ellipse 70% 40% at 15% 0%, rgba(192,51,90,0.04) 0%, transparent 60%) !important;
    font-family: var(--font-body) !important;
}
.stApp > header, #MainMenu, footer { display: none !important; }
.block-container { padding: 0 2.5rem 3rem 2.5rem !important; max-width: 1380px !important; margin: 0 auto !important; }

section[data-testid="stSidebar"] {
    background: var(--c-surface) !important;
    border-right: 1px solid var(--c-border-mid) !important;
    width: 288px !important;
    box-shadow: 4px 0 20px rgba(180,60,100,0.06) !important;
}

[data-testid="stChatMessage"] {
    background: var(--c-surface) !important;
    border: 1px solid var(--c-border-mid) !important;
    border-radius: var(--radius-xl) !important;
    padding: 22px 26px !important;
    margin-bottom: 14px !important;
    box-shadow: var(--shadow-sm) !important;
    animation: msgFadeUp 0.35s cubic-bezier(0.22,0.68,0,1.2) both;
}
[data-testid="stChatInput"] textarea {
    background: var(--c-surface) !important;
    border: 1.5px solid var(--c-border-mid) !important;
    border-radius: 14px !important;
    color: var(--c-text) !important;
    font-family: var(--font-body) !important;
    font-size: 14px !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--c-rose) !important;
    box-shadow: 0 0 0 3px var(--c-rose-glow) !important;
}

.stButton > button {
    background: linear-gradient(135deg, var(--c-rose) 0%, var(--c-violet) 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: var(--radius-md) !important;
    font-family: var(--font-body) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 0.02em !important;
    padding: 10px 18px !important;
    transition: all 0.25s cubic-bezier(0.4,0,0.2,1) !important;
    box-shadow: 0 2px 10px rgba(192,51,90,0.16) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(192,51,90,0.24) !important;
    filter: brightness(1.06) !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-display) !important;
    font-weight: 600 !important;
    color: var(--c-text) !important;
    background: none !important;
    -webkit-text-fill-color: var(--c-text) !important;
}

[data-baseweb="select"] > div {
    background: var(--c-surface) !important;
    border: 1.5px solid var(--c-border-mid) !important;
    border-radius: var(--radius-md) !important;
    color: var(--c-text) !important;
}
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--c-surface) !important;
    border: 1.5px solid var(--c-border-mid) !important;
    border-radius: var(--radius-md) !important;
    color: var(--c-text) !important;
    font-family: var(--font-body) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--c-rose) !important;
    box-shadow: 0 0 0 3px var(--c-rose-glow) !important;
}

hr { border-color: var(--c-border-mid) !important; margin: 12px 0 !important; }

.hero-section { text-align: center; padding: 96px 32px 72px; }
.hero-badge {
    display: inline-flex; align-items: center; gap: 10px;
    background: rgba(192,51,90,0.07); border: 1px solid rgba(192,51,90,0.18);
    padding: 7px 22px; border-radius: var(--radius-pill);
    font-family: var(--font-body); font-size: 11px; font-weight: 700;
    color: var(--c-rose); letter-spacing: 2px; text-transform: uppercase; margin-bottom: 36px;
}
.hero-title {
    font-family: var(--font-display); font-size: clamp(52px, 7.5vw, 88px);
    font-weight: 300; line-height: 1.08; margin-bottom: 28px;
    color: var(--c-text); letter-spacing: -0.02em;
}
.hero-title strong { font-weight: 600; }
.hero-gradient-text {
    background: linear-gradient(135deg, var(--c-rose), var(--c-violet-light));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; font-weight: 600;
}
.hero-subtitle {
    font-family: var(--font-body); font-size: 17px; line-height: 1.75;
    max-width: 560px; margin: 0 auto 28px; color: var(--c-text-muted); font-weight: 300;
}
.stats-bar {
    display: grid; grid-template-columns: repeat(5, 1fr);
    background: var(--c-surface); border: 1px solid var(--c-border-mid);
    border-radius: var(--radius-xl); overflow: hidden; margin: 48px 0;
    box-shadow: var(--shadow-md);
}
.stat-item { padding: 36px 20px; text-align: center; position: relative; }
.stat-item::after {
    content: ''; position: absolute; right: 0; top: 20%; height: 60%;
    width: 1px; background: var(--c-border-mid);
}
.stat-item:last-child::after { display: none; }
.stat-number {
    font-family: var(--font-display); font-size: 46px; font-weight: 600;
    background: linear-gradient(135deg, var(--c-rose), var(--c-violet-light));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    line-height: 1; margin-bottom: 8px;
}
.stat-label { font-family: var(--font-body); font-size: 11px; color: var(--c-text-dim); text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600; }
.features-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 40px 0; }
.feature-card {
    background: var(--c-surface); border: 1px solid var(--c-border-mid);
    border-radius: var(--radius-xl); padding: 34px 30px;
    transition: all 0.3s cubic-bezier(0.4,0,0.2,1); position: relative; overflow: hidden;
}
.feature-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, var(--c-rose), var(--c-violet)); opacity: 0; transition: opacity 0.3s;
}
.feature-card:hover { transform: translateY(-5px); border-color: var(--c-border-vivid); box-shadow: var(--shadow-rose); }
.feature-card:hover::before { opacity: 1; }
.feature-icon {
    width: 52px; height: 52px; border-radius: var(--radius-md);
    background: rgba(192,51,90,0.08); border: 1px solid rgba(192,51,90,0.16);
    display: flex; align-items: center; justify-content: center; font-size: 24px; margin-bottom: 22px;
}
.feature-title { font-family: var(--font-display); font-size: 19px; font-weight: 600; color: var(--c-text); margin-bottom: 10px; }
.feature-desc { font-family: var(--font-body); font-size: 13.5px; color: var(--c-text-muted); line-height: 1.65; font-weight: 300; }
.training-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 40px 0; }
.training-card {
    background: rgba(107,33,168,0.04); border: 1px solid rgba(107,33,168,0.12);
    border-radius: var(--radius-xl); padding: 34px 30px;
}
.training-number { font-family: var(--font-display); font-size: 56px; font-weight: 300; color: var(--c-violet); margin-bottom: 8px; line-height: 1; }
.training-title { font-family: var(--font-display); font-size: 19px; font-weight: 600; color: var(--c-text); margin-bottom: 10px; }
.training-text { font-family: var(--font-body); font-size: 13.5px; color: var(--c-text-muted); line-height: 1.6; font-weight: 300; }
.training-tags { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 18px; }
.training-tag {
    background: rgba(192,51,90,0.08); border: 1px solid rgba(192,51,90,0.15);
    color: var(--c-rose); padding: 4px 13px; border-radius: var(--radius-pill);
    font-family: var(--font-mono); font-size: 11px; font-weight: 500;
}
.howit-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 40px 0; }
.howit-card {
    text-align: center; padding: 36px 22px; background: var(--c-surface);
    border: 1px solid var(--c-border-mid); border-radius: var(--radius-xl); transition: all 0.25s ease;
}
.howit-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-md); }
.howit-number {
    width: 48px; height: 48px; border-radius: 50%;
    background: linear-gradient(135deg, var(--c-rose), var(--c-violet));
    display: flex; align-items: center; justify-content: center;
    font-family: var(--font-display); font-size: 20px; font-weight: 600; color: white;
    margin: 0 auto 18px; box-shadow: 0 4px 16px rgba(192,51,90,0.20);
}
.howit-title { font-family: var(--font-display); font-size: 17px; font-weight: 600; color: var(--c-text); margin-bottom: 10px; }
.howit-text { font-family: var(--font-body); font-size: 13px; color: var(--c-text-muted); line-height: 1.65; font-weight: 300; }
.cta-section {
    border-radius: var(--radius-2xl); padding: 88px 56px; text-align: center;
    background: linear-gradient(135deg, rgba(192,51,90,0.05), rgba(107,33,168,0.06));
    border: 1px solid var(--c-border-mid); margin: 56px 0; position: relative; overflow: hidden;
}
.cta-title { font-family: var(--font-display); font-size: 52px; font-weight: 300; color: var(--c-text); margin-bottom: 18px; letter-spacing: -0.02em; }
.cta-text { font-family: var(--font-body); font-size: 16px; color: var(--c-text-muted); margin-bottom: 36px; max-width: 480px; margin-left: auto; margin-right: auto; line-height: 1.7; font-weight: 300; }
.premium-footer { border-top: 1px solid var(--c-border-mid); padding: 44px 0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 24px; margin-top: 48px; }
.footer-logo { display: flex; align-items: center; gap: 14px; }
.footer-logo-text { font-family: var(--font-display); font-size: 20px; font-weight: 600; background: linear-gradient(135deg, var(--c-rose), var(--c-violet)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; letter-spacing: 0.05em; }
.footer-links { display: flex; gap: 32px; flex-wrap: wrap; }
.footer-link { font-family: var(--font-body); font-size: 13px; color: var(--c-text-dim); }
.footer-badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(192,51,90,0.06); border: 1px solid rgba(192,51,90,0.14); padding: 6px 16px; border-radius: var(--radius-pill); margin-bottom: 8px; }

.law-tip-box { padding: 14px 16px; background: var(--c-surface2); border-left: 3px solid var(--c-rose); border-radius: 0 var(--radius-md) var(--radius-md) 0; margin: 12px 0; }
.tip-title { font-family: var(--font-body); color: var(--c-rose); font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px; }
.tip-text { font-family: var(--font-body); color: var(--c-text-muted); font-size: 12.5px; line-height: 1.5; font-weight: 300; }
.mode-tag { display: inline-block; background: linear-gradient(90deg, var(--c-rose), var(--c-violet)); color: white !important; padding: 3px 11px; border-radius: var(--radius-pill); font-family: var(--font-mono); font-size: 10px; font-weight: 500; letter-spacing: 0.05em; margin-bottom: 10px; }
.demo-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin: 24px 0; }
.demo-question { background: var(--c-surface); border: 1px solid var(--c-border-mid); border-radius: var(--radius-lg); padding: 16px 18px; cursor: pointer; transition: all 0.22s ease; }
.demo-question:hover { border-color: var(--c-rose); background: rgba(192,51,90,0.03); transform: translateX(3px); box-shadow: var(--shadow-sm); }
.demo-category { font-family: var(--font-mono); font-size: 10px; color: var(--c-rose); font-weight: 500; letter-spacing: 0.08em; margin-bottom: 7px; text-transform: uppercase; }
.demo-text { font-family: var(--font-body); font-size: 13px; color: var(--c-text-muted); line-height: 1.55; font-weight: 300; }
.an-user-card { background: linear-gradient(135deg, rgba(192,51,90,0.05), rgba(107,33,168,0.05)); border: 1px solid var(--c-border-mid); border-radius: var(--radius-lg); padding: 14px 16px; margin: 14px 0; display: flex; align-items: center; gap: 12px; }
.an-avatar { width: 40px; height: 40px; background: linear-gradient(135deg, var(--c-rose), var(--c-violet)); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-family: var(--font-display); font-size: 17px; font-weight: 600; color: white !important; flex-shrink: 0; box-shadow: 0 3px 12px rgba(192,51,90,0.20); }
.an-nav-label { font-family: var(--font-body); font-size: 10px; color: var(--c-rose); text-transform: uppercase; letter-spacing: 1.8px; font-weight: 700; margin: 18px 0 10px; display: block; }
.an-hotlines { background: rgba(192,51,90,0.05); border: 1px solid rgba(192,51,90,0.15); border-radius: var(--radius-lg); padding: 14px 16px; margin-top: 18px; }
.an-hotlines-title { font-family: var(--font-body); font-size: 10px; font-weight: 700; color: var(--c-red-alert); text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 10px; }
.an-hotline-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(192,51,90,0.08); }
.an-hotline-row:last-child { border-bottom: none; }
.an-hotline-label { font-family: var(--font-body); font-size: 12px; color: var(--c-text-muted); font-weight: 300; }
.an-hotline-num { font-family: var(--font-mono); font-size: 12px; color: var(--c-red-alert); font-weight: 500; }
.an-section-header { background: linear-gradient(135deg, rgba(192,51,90,0.05), rgba(107,33,168,0.05)); border: 1px solid var(--c-border-mid); border-radius: var(--radius-xl); padding: 22px 28px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; box-shadow: var(--shadow-sm); }
.an-feature-title { font-family: var(--font-display); font-size: 22px; font-weight: 600; color: var(--c-text); letter-spacing: -0.01em; }

@keyframes msgFadeUp {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--c-bg); }
::-webkit-scrollbar-thumb { background: linear-gradient(180deg, var(--c-rose), var(--c-violet)); border-radius: 10px; }
</style>
"""

# Apply theme
if st.session_state.theme == "dark":
    st.markdown(dark_theme, unsafe_allow_html=True)
else:
    st.markdown(light_theme, unsafe_allow_html=True)

# ============================================================
#  MOBILE RESPONSIVE CSS
# ============================================================
st.markdown("""
<style>
@media (max-width: 768px) {

    /* ── CORE LAYOUT ── */
    .block-container {
        padding: 0 1rem 2rem 1rem !important;
    }

    /* ── VIEWPORT META (Streamlit doesn't inject this) ── */
    * { -webkit-text-size-adjust: 100%; }

    /* ── SIDEBAR: collapse-friendly ── */
    section[data-testid="stSidebar"] {
        width: 100% !important;
    }

    /* ── HERO ── */
    .hero-section {
        padding: 48px 16px 40px !important;
    }
    .hero-title {
        font-size: clamp(36px, 9vw, 56px) !important;
        line-height: 1.12 !important;
    }
    .hero-subtitle {
        font-size: 15px !important;
    }

    /* ── STATS BAR: 2 cols on mobile ── */
    .stats-bar {
        grid-template-columns: repeat(2, 1fr) !important;
        margin: 24px 0 !important;
    }
    .stat-item { padding: 22px 12px !important; }
    .stat-number { font-size: 32px !important; }
    .stat-item::after { display: none !important; }

    /* ── FEATURES: 1 col ── */
    .features-grid {
        grid-template-columns: 1fr !important;
        gap: 14px !important;
        margin: 20px 0 !important;
    }
    .feature-card { padding: 24px 20px !important; }

    /* ── TRAINING: 1 col ── */
    .training-grid {
        grid-template-columns: 1fr !important;
        gap: 14px !important;
    }
    .training-card { padding: 24px 20px !important; }
    .training-number { font-size: 40px !important; }

    /* ── HOW IT WORKS: 2 col ── */
    .howit-grid {
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 12px !important;
    }
    .howit-card { padding: 22px 14px !important; }

    /* ── CTA ── */
    .cta-section {
        padding: 48px 24px !important;
    }
    .cta-title { font-size: 32px !important; }
    .cta-text  { font-size: 14px !important; }

    /* ── FOOTER ── */
    .premium-footer {
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 16px !important;
        padding: 28px 0 !important;
    }
    .footer-links {
        gap: 16px !important;
        flex-wrap: wrap !important;
    }

    /* ── LOGIN PAGE ── */
    .block-container { padding: 0 0.75rem 2rem !important; }

    /* ── DEMO GRID: 1 col ── */
    .demo-grid {
        grid-template-columns: 1fr !important;
        gap: 10px !important;
    }

    /* ── SECTION HEADER ── */
    .an-section-header {
        padding: 14px 16px !important;
        border-radius: 14px !important;
    }
    .an-feature-title { font-size: 18px !important; }

    /* ── CHAT MESSAGES ── */
    [data-testid="stChatMessage"] {
        padding: 14px 16px !important;
        border-radius: 14px !important;
    }

    /* ── ANALYSIS PANEL: 2 col ── */
    [data-testid="stChatMessage"] [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }

    /* ── BUTTONS ── */
    .stButton > button {
        font-size: 12px !important;
        padding: 9px 14px !important;
    }

    /* ── HEADINGS ── */
    h2 { font-size: 26px !important; }
    h3 { font-size: 22px !important; }
}

@media (max-width: 480px) {
    .hero-title { font-size: 32px !important; }
    .stats-bar  { grid-template-columns: repeat(2, 1fr) !important; }
    .howit-grid { grid-template-columns: 1fr !important; }
    .cta-title  { font-size: 26px !important; }

    /* login center col fills screen */
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child,
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child {
        display: none !important;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) {
        width: 100% !important;
        flex: 1 !important;
    }
}
</style>
""", unsafe_allow_html=True)

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
        "title": " New conversation",
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

def clean_text(text):
    text = text.lower().strip()
    replacements = {
        "kula": "khula",
        "khulaa": "khula",
        "talaq": "divorce",
        "shaadi": "marriage",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

# Deep Analysis Panel
@st.fragment
def render_analysis_panel(msg_index, original_query):
    if not is_legal_query(original_query):
        return

    panel_key = f"panel_{msg_index}"
    if panel_key not in st.session_state.expanded_panels:
        st.session_state.expanded_panels[panel_key] = {
            "merits": False, "opposition": False, "timeline": False, "draft": False,
            "merits_res": None, "opp_res": None, "time_res": None, "draft_res": None
        }

    panel = st.session_state.expanded_panels[panel_key]
    st.markdown('<div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid var(--c-border-mid);">', unsafe_allow_html=True)
    st.markdown("<p style='color:var(--c-text-dim); font-size:10px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; font-family:var(--font-body);'>🔍 Deep Analysis Tools</p>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button(" Case Merits", key=f"m_{msg_index}", use_container_width=True):
            if not panel["merits_res"]:
                with st.spinner("Analyzing..."):
                    panel["merits_res"] = st.session_state.m_chain.invoke(original_query)
            panel["merits"] = not panel["merits"]
            st.rerun()
    with col2:
        if st.button(" Opposition", key=f"o_{msg_index}", use_container_width=True):
            if not panel["opp_res"]:
                with st.spinner("Analyzing..."):
                    panel["opp_res"] = st.session_state.o_chain.invoke(original_query)
            panel["opposition"] = not panel["opposition"]
            st.rerun()
    with col3:
        if st.button(" Timeline", key=f"t_{msg_index}", use_container_width=True):
            if not panel["time_res"]:
                with st.spinner("Analyzing..."):
                    panel["time_res"] = st.session_state.t_chain.invoke(original_query)
            panel["timeline"] = not panel["timeline"]
            st.rerun()
    with col4:
        if st.button(" Draft", key=f"d_{msg_index}", use_container_width=True):
            if not panel["draft_res"]:
                with st.spinner("Generating..."):
                    panel["draft_res"] = st.session_state.d_chain.invoke(original_query)
            panel["draft"] = not panel["draft"]
            st.rerun()

    if panel["merits"] and panel["merits_res"] and panel["merits_res"] != "SKIP_ANALYSIS":
        st.success(panel["merits_res"])
    if panel["opposition"] and panel["opp_res"] and panel["opp_res"] != "SKIP_ANALYSIS":
        st.error(panel["opp_res"])
    if panel["timeline"] and panel["time_res"] and panel["time_res"] != "SKIP_ANALYSIS":
        st.info(panel["time_res"])
    if panel["draft"] and panel["draft_res"] and panel["draft_res"] != "SKIP_ANALYSIS":
        st.warning(panel["draft_res"])
        pdf_path = create_pdf(panel["draft_res"])
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download PDF", f, file_name=f"legal_draft_{msg_index}.pdf", key=f"dl_{msg_index}", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

HOTLINES_HTML = """
<div class="an-hotlines">
    <div class="an-hotlines-title"> EMERGENCY HELPLINES</div>
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
    " Legal Chat": "Legal Chat",
    " Case Merits": "Case Merits",
    " Counter Arguments": "Counter Arguments",
    " Timeline Estimator": "Timeline Estimator",
    " Legal Draft": "Legal Draft",
    " About": "About",
}

# ============================================================
#  LANDING PAGE
# ============================================================
if not st.session_state.logged_in and st.session_state.show_landing:
    st.markdown("""
    <div class="hero-section">
        <div class="hero-badge">
            <span style="width:7px;height:7px;border-radius:50%;background:var(--c-rose);display:inline-block;"></span>
            Samsung Innovation Campus · Pakistan
        </div>
        <div class="hero-title">
            Legal Rights for Every<br>
            <span class="hero-gradient-text">Pakistani Woman</span>
        </div>
        <div class="hero-subtitle">
            AI-powered legal assistant trained on <strong style="color:var(--c-violet-light);">164 Pakistani law documents.</strong><br>
            Empowering citizens with legal literacy and assisting Legal Professionals with rapid case analysis.
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([1, 1.2, 1.2, 1])
    with col2:
        if st.button(" Start Free Consultation", use_container_width=True, key="hero_start"):
            st.session_state.show_landing = False
            st.rerun()
    with col3:
        if st.button(" Try as Guest", use_container_width=True, key="hero_guest"):
            st.session_state.logged_in = True
            st.session_state.username = "Guest"
            st.session_state.show_landing = False
            create_new_chat()
            st.rerun()

    st.markdown("""
    <div class="stats-bar">
        <div class="stat-item"><div class="stat-number">164</div><div class="stat-label">Law Documents</div></div>
        <div class="stat-item"><div class="stat-number">12+</div><div class="stat-label">Legal Domains</div></div>
        <div class="stat-item"><div class="stat-number">2</div><div class="stat-label">Languages</div></div>
        <div class="stat-item"><div class="stat-number">6</div><div class="stat-label">AI Tools</div></div>
        <div class="stat-item"><div class="stat-number">24/7</div><div class="stat-label">Availability</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center; margin-bottom:20px;">
        <div style="display:inline-block;background:rgba(232,72,122,0.08);border:1px solid rgba(232,72,122,0.20);color:var(--c-rose-light);padding:6px 18px;border-radius:999px;font-family:var(--font-body);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;">✦ Features</div>
        <h2 style="margin-top:20px;font-family:var(--font-display);font-size:38px;font-weight:300;">Everything You Need to Know Your Rights</h2>
        <p style="color:var(--c-text-muted);max-width:560px;margin:10px auto 0;font-family:var(--font-body);font-weight:300;font-size:15px;">From instant legal Q&amp;A to professional court documents — all powered by AI trained on Pakistani law.</p>
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

    st.markdown("""
    <div style="margin:60px 0;background:rgba(124,58,237,0.04);border:1px solid rgba(124,58,237,0.10);border-radius:var(--radius-2xl);padding:56px 48px;">
        <div style="text-align:center; margin-bottom:30px;">
            <div style="display:inline-block;background:rgba(232,72,122,0.08);border:1px solid rgba(232,72,122,0.18);color:var(--c-rose-light);padding:6px 18px;border-radius:999px;font-family:var(--font-body);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;">📚 Training Data</div>
            <h2 style="margin-top:20px;font-family:var(--font-display);font-size:38px;font-weight:300;">Trained on 164 Pakistani Law Documents</h2>
            <p style="color:var(--c-text-muted);max-width:560px;margin:10px auto 0;font-family:var(--font-body);font-weight:300;font-size:15px;">Our RAG system retrieves answers directly from verified legal texts — not hallucination.</p>
        </div>
        <div class="training-grid">
            <div class="training-card"><div class="training-number">50+</div><div class="training-title">Family Law Texts</div><div class="training-text">MFLO 1961, FCA 1964, CMRA, GWA 1890</div><div class="training-tags"><span class="training-tag">MFLO 1961</span><span class="training-tag">FCA 1964</span><span class="training-tag">CMRA</span></div></div>
            <div class="training-card"><div class="training-number">40+</div><div class="training-title">Cybercrime & Digital Rights</div><div class="training-text">PECA 2016, FIA Rules, NR3C</div><div class="training-tags"><span class="training-tag">PECA 2016</span><span class="training-tag">FIA Rules</span><span class="training-tag">NR3C</span></div></div>
            <div class="training-card"><div class="training-number">35+</div><div class="training-title">Workplace & Rights Laws</div><div class="training-text">HAW 2010, Labour Laws, WPA Punjab</div><div class="training-tags"><span class="training-tag">HAW 2010</span><span class="training-tag">Labour Laws</span><span class="training-tag">WPA Punjab</span></div></div>
            <div class="training-card"><div class="training-number">39+</div><div class="training-title">Inheritance & Property</div><div class="training-text">Shariat Act, Succession, Haq Mehr</div><div class="training-tags"><span class="training-tag">Shariat Act</span><span class="training-tag">Succession</span><span class="training-tag">Haq Mehr</span></div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin:60px 0;">
        <div style="text-align:center; margin-bottom:30px;">
            <div style="display:inline-block;background:rgba(232,72,122,0.08);border:1px solid rgba(232,72,122,0.18);color:var(--c-rose-light);padding:6px 18px;border-radius:999px;font-family:var(--font-body);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;">💡 How It Works</div>
            <h2 style="margin-top:20px;font-family:var(--font-display);font-size:38px;font-weight:300;">From Question to Legal Action in Minutes</h2>
            <p style="color:var(--c-text-muted);max-width:560px;margin:10px auto 0;font-family:var(--font-body);font-weight:300;font-size:15px;">No lawyer needed for your first consultation. Just type and get answers.</p>
        </div>
        <div class="howit-grid">
            <div class="howit-card"><div class="howit-number">1</div><div class="howit-title">Ask Your Question</div><div class="howit-text">Type in Roman Urdu or English. No legal knowledge needed.</div></div>
            <div class="howit-card"><div class="howit-number">2</div><div class="howit-title">AI Searches the Law</div><div class="howit-text">RAG finds relevant sections from 164 verified Pakistani legal documents.</div></div>
            <div class="howit-card"><div class="howit-number">3</div><div class="howit-title">Get Cited Answers</div><div class="howit-text">Guidance with exact section numbers like "MFLO Section 6" so you can verify.</div></div>
            <div class="howit-card"><div class="howit-number">4</div><div class="howit-title">Download & Act</div><div class="howit-text">Generate legal drafts as PDF, know your timeline, walk into court prepared.</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="cta-section">
        <div class="cta-title">Your Voice. Your Rights. Your Law.</div>
        <div class="cta-text">Join thousands of Pakistani women who've used Awaz-e-Nisa to understand their legal rights.</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([1, 1.2, 1.2, 1])
    with col2:
        if st.button(" Get Started Free", use_container_width=True, key="cta_start"):
            st.session_state.show_landing = False
            st.rerun()
    with col3:
        if st.button(" Try as Guest", use_container_width=True, key="cta_guest"):
            st.session_state.logged_in = True
            st.session_state.username = "Guest"
            st.session_state.show_landing = False
            create_new_chat()
            st.rerun()

    st.markdown("""
    <div class="premium-footer">
        <div class="footer-logo">
            <span style="font-size:28px;">⚖️</span>
            <div><div class="footer-logo-text">AWAZ-E-NISA</div><div style="font-family:var(--font-body);font-size:12px;color:var(--c-text-dim);font-weight:300;">آوازِ نسواں · Voice of Women</div></div>
        </div>
        <div class="footer-links">
            <span class="footer-link">Legal Chat</span>
            <span class="footer-link">Case Merits</span>
            <span class="footer-link">Counter Args</span>
            <span class="footer-link">Timeline</span>
            <span class="footer-link">Legal Draft</span>
        </div>
        <div class="footer-brand" style="text-align:right;">
            <div class="footer-badge"><span style="font-family:var(--font-body);font-size:11px;color:var(--c-text-muted);">🚀 SAMSUNG INNOVATION CAMPUS</span></div>
            <div style="font-family:var(--font-body);font-size:11px;color:var(--c-text-dim);">© 2026 Awaz-e-Nisa · Pakistan</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
#  LOGIN PAGE
# ============================================================
elif not st.session_state.logged_in and not st.session_state.show_landing:

    st.markdown("""
    <style>
    /* ── reset container for login page only ── */
    .block-container { padding: 0 0 0 0 !important; max-width: 100% !important; }
    [data-testid="column"] { padding: 0 !important; gap: 0 !important; }
    [data-testid="stHorizontalBlock"] { gap: 0 !important; }

    /* ════ LEFT PANEL ════ */
    .lp-left {
        min-height: 100vh;
        background: linear-gradient(160deg, #0f0c1e 0%, #160e28 40%, #0c0a18 100%);
        border-right: 1px solid rgba(232,72,122,0.15);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 60px 52px;
        position: relative;
        overflow: hidden;
    }
    .lp-left::before {
        content:''; position:absolute;
        top:-180px; left:-100px;
        width:500px; height:500px;
        background: radial-gradient(ellipse, rgba(124,58,237,0.18) 0%, transparent 65%);
        pointer-events:none;
    }
    .lp-left::after {
        content:''; position:absolute;
        bottom:-140px; right:-80px;
        width:400px; height:400px;
        background: radial-gradient(ellipse, rgba(232,72,122,0.12) 0%, transparent 65%);
        pointer-events:none;
    }

    .lp-icon   { font-size:72px; line-height:1; margin-bottom:22px; filter:drop-shadow(0 8px 28px rgba(232,72,122,0.4)); display:block; }
    .lp-brand  {
        font-family:'Cormorant Garamond',Georgia,serif;
        font-size:38px; font-weight:600; letter-spacing:0.14em;
        background:linear-gradient(135deg,#e8487a,#a78bfa);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
        display:block; margin-bottom:8px; text-align:center;
    }
    .lp-urdu   {
        font-family:'DM Sans',sans-serif; font-size:13px; color:#4a4268;
        font-weight:300; margin-bottom:48px; display:block; text-align:center;
        letter-spacing:0.5px;
    }

    .lp-feats { display:flex; flex-direction:column; gap:12px; width:100%; max-width:320px; }
    .lp-feat {
        display:flex; align-items:center; gap:16px;
        padding:14px 18px;
        background:rgba(255,255,255,0.04);
        border:1px solid rgba(255,255,255,0.08);
        border-radius:14px;
        transition: border-color 0.2s ease;
    }
    .lp-feat:hover { border-color: rgba(232,72,122,0.25); }
    .lp-feat-icon  { font-size:22px; flex-shrink:0; }
    .lp-feat-title { font-family:'DM Sans',sans-serif; font-size:13px; font-weight:600; color:#ede8f8; margin-bottom:3px; }
    .lp-feat-sub   { font-family:'DM Sans',sans-serif; font-size:11px; color:#4a4268; font-weight:300; }

    .lp-badge {
        margin-top:40px;
        display:inline-flex; align-items:center; gap:8px;
        background:rgba(232,72,122,0.08); border:1px solid rgba(232,72,122,0.20);
        padding:7px 18px; border-radius:999px;
        font-family:'DM Mono',monospace; font-size:10px; color:#f07fa0;
        letter-spacing:1.2px; text-transform:uppercase;
    }

    /* ════ RIGHT PANEL ════ */
    .lp-right {
        min-height: 100vh;
        background: #06050e;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 60px 64px;
    }
    .lp-right-inner { width: 100%; max-width: 400px; }
    .lp-title {
        font-family:'Cormorant Garamond',Georgia,serif;
        font-size:36px; font-weight:300; color:#ede8f8;
        margin-bottom:6px; letter-spacing:-0.01em;
    }
    .lp-subtitle {
        font-family:'DM Sans',sans-serif; font-size:13px; color:#4a4268;
        font-weight:300; margin-bottom:32px;
    }
    .lp-divider {
        display:flex; align-items:center; gap:12px; margin:0 0 20px;
    }
    .lp-div-line { flex:1; height:1px; background:rgba(180,130,255,0.14); }
    .lp-div-txt  {
        font-family:'DM Mono',monospace; font-size:10px; color:#3e3660;
        letter-spacing:1.2px; text-transform:uppercase;
    }
    .lp-foot {
        display:flex; justify-content:center; gap:24px;
        margin-top:28px; padding-top:20px;
        border-top:1px solid rgba(180,130,255,0.08);
        font-family:'DM Sans',sans-serif; font-size:11px; color:#3e3660;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── centered single column ──
    _, center_col, _ = st.columns([1, 1.4, 1])

    with center_col:
        st.markdown("""
        <div style="padding: 60px 0 20px; text-align: center;">
            <div style="font-size:60px;filter:drop-shadow(0 6px 20px rgba(232,72,122,0.38));margin-bottom:18px;">⚖️</div>
            <div style="font-family:'Cormorant Garamond',Georgia,serif;font-size:32px;font-weight:600;letter-spacing:0.14em;background:linear-gradient(135deg,#e8487a,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:6px;">AWAZ-E-NISA</div>
            <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:#4a4268;font-weight:300;letter-spacing:0.5px;margin-bottom:36px;">آوازِ نسواں · Voice of Women</div>
        </div>
        """, unsafe_allow_html=True)

        role = st.selectbox("Operational Mode", ["GENERAL USER (Woman)", "LEGAL PRO"])

        st.markdown("""
        <div class="lp-divider" style="margin:14px 0 18px;">
            <div class="lp-div-line"></div>
            <div class="lp-div-txt">Access Portal</div>
            <div class="lp-div-line"></div>
        </div>
        """, unsafe_allow_html=True)

        t1, t2 = st.tabs(["🔑  LOGIN", "✨  SIGN UP"])
        with t1:
            with st.form("login"):
                u = st.text_input("Username", placeholder="Enter your username")
                p = st.text_input("Password", type="password", placeholder="Enter your password")
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("LOGIN  →", use_container_width=True):
                    if verify_user(u, p):
                        st.session_state.logged_in = True
                        st.session_state.username = u
                        st.session_state.current_mode = role
                        st.session_state.messages = get_chat_history(u)
                        st.rerun()
                    else:
                        st.error("Invalid credentials — please try again.")

        with t2:
            with st.form("signup"):
                nu = st.text_input("Username", placeholder="Choose a username")
                np_ = st.text_input("Password", type="password", placeholder="Minimum 4 characters")
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("CREATE ACCOUNT  →", use_container_width=True):
                    if nu and np_:
                        if len(np_) >= 4:
                            if add_user(nu, np_):
                                st.success("Account created! Please switch to Login.")
                            else:
                                st.error("Username already taken — try another.")
                        else:
                            st.warning("Password must be at least 4 characters.")
                    else:
                        st.warning("Please fill in all fields.")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("← Back to Home", use_container_width=True):
            st.session_state.show_landing = True
            st.rerun()

        st.markdown("""
        <div class="lp-foot" style="margin-top:20px;padding-top:16px;border-top:1px solid rgba(180,130,255,0.08);display:flex;justify-content:center;gap:24px;font-family:'DM Sans',sans-serif;font-size:11px;color:#3e3660;">
            <span>🔒 Secure</span><span>🇵🇰 Pakistani Law</span><span>⚡ 24/7</span>
        </div>
        """, unsafe_allow_html=True)

# ============================================================
#  MAIN APP
# ============================================================
else:
    ensure_session()

    if "rag" not in st.session_state:
        with st.spinner(" Loading AI model..."):
            from legal_advisor import (rag_chain, merits_chain,
                                       opposition_chain, timeline_chain, draft_chain)
            st.session_state.rag = rag_chain
            st.session_state.m_chain = merits_chain
            st.session_state.o_chain = opposition_chain
            st.session_state.t_chain = timeline_chain
            st.session_state.d_chain = draft_chain

    # ========== SIDEBAR ==========
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 24px 0 20px; border-bottom: 1px solid var(--c-border-mid); margin-bottom: 18px;">
            <div style="font-size: 44px; margin-bottom: 8px;">⚖️</div>
            <div style="font-family: var(--font-display); font-size: 20px; font-weight: 600; letter-spacing: 0.06em; color: var(--c-text);">AWAZ-E-NISA</div>
            <div style="font-family: var(--font-body); font-size: 11px; color: var(--c-text-dim); font-weight: 300; margin-top: 2px;">Voice of Women · آوازِ نسواں</div>
        </div>
        """, unsafe_allow_html=True)

        is_dark = st.session_state.theme == "dark"
        toggle_label = "☀️ Light Mode" if is_dark else "🌙 Dark Mode"
        if st.button(toggle_label, use_container_width=True, key="theme_toggle"):
            st.session_state.theme = "light" if is_dark else "dark"
            st.rerun()

        st.markdown(f"""
        <div class="an-user-card">
            <div class="an-avatar">{st.session_state.username[0].upper()}</div>
            <div>
                <div style="font-family: var(--font-body); font-weight: 600; color: var(--c-text); font-size: 14px;">{st.session_state.username}</div>
                <div style="font-family: var(--font-mono); font-size: 11px; color: var(--c-green);">● Active</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        tip_title, tip_content = random.choice(LEGAL_TIPS)
        st.markdown(f"""
        <div class="law-tip-box">
            <div class="tip-title">⚖️ {tip_title}</div>
            <div class="tip-text">{tip_content}</div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # ============================================================
        #  VOICE INPUT — USING WHISPER (FROM OLD APP CONFIGURATION)
        # ============================================================
        st.markdown('<span class="an-nav-label"> VOICE COMMAND</span>', unsafe_allow_html=True)
        audio = mic_recorder(start_prompt=" Start Speaking", stop_prompt="⏹️ Stop", key="recorder", just_once=True, use_container_width=True)

        if audio and not st.session_state.processing_audio:
            if audio.get("id") != st.session_state.last_audio_id:
                st.session_state.last_audio_id = audio.get("id")
                st.session_state.processing_audio = True
                with st.spinner("🎤 Transcribing..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                        tmp.write(audio["bytes"])
                        tmp_path = tmp.name

                    res = load_whisper_model().transcribe(
                        tmp_path, language="en",
                        initial_prompt="Harassment, Khula, Divorce, Roman Urdu, Pakistani Law.",
                        fp16=False, no_speech_threshold=0.6
                    )
                    raw_text = res["text"].strip()


                    clean_q = re.sub(r'[^a-zA-Z0-9\s\.,\?!]', '', raw_text)

                    # Filter Hallucinations
                    if len(clean_q) > 5 and not any(x in clean_q.lower() for x in ["have a nice night", "thank you"]):
                        st.session_state.messages.append({"role": "user", "content": clean_q})
                        ans = st.session_state.rag.invoke({"question": clean_q, "mode": st.session_state.current_mode})
                        st.session_state.messages.append({"role": "assistant", "content": ans, "mode": st.session_state.current_mode})
                        save_chat_message(st.session_state.username, "user", clean_q, st.session_state.current_mode)
                        save_chat_message(st.session_state.username, "assistant", ans, st.session_state.current_mode)
                    else:
                        st.warning("Unclear audio, try again.")

                    st.session_state.processing_audio = False
                    os.remove(tmp_path); st.rerun()

        st.divider()

        st.markdown('<span class="an-nav-label">👤 USER MODE</span>', unsafe_allow_html=True)
        mode_options = [" GENERAL USER (Woman)", " LEGAL PRO"]
        mode_idx = 0 if "GENERAL" in st.session_state.current_mode else 1
        mode = st.selectbox("mode_sel", mode_options, index=mode_idx, label_visibility="collapsed")
        if mode != st.session_state.current_mode:
            st.session_state.current_mode = mode
            st.rerun()

        st.divider()

        if st.button("✨ New Chat", use_container_width=True):
            save_current_session()
            create_new_chat()
            st.rerun()

        st.markdown('<span class="an-nav-label">🎯 FEATURES</span>', unsafe_allow_html=True)
        for label, key in FEATURES.items():
            if st.button(label, use_container_width=True, key=f"nav_{key}"):
                st.session_state.active_feature = key
                st.rerun()

        st.divider()

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
                    if full_text.strip():
                        doc_query = f"Analyzed Document Content: {full_text[:500]}..."
                        st.session_state.messages.append({"role": "user", "content": doc_query})
                        save_chat_message(st.session_state.username, "user", doc_query, st.session_state.current_mode)

                        res = st.session_state.rag.invoke({"question": full_text, "mode": st.session_state.current_mode})
                        st.session_state.messages.append({"role": "assistant", "content": res})
                        save_chat_message(st.session_state.username, "assistant", res, st.session_state.current_mode)
                        st.rerun()

        st.divider()

        if st.button(" Clear Chat", use_container_width=True):
            st.session_state.messages = []
            save_current_session()
            st.rerun()

        if st.button(" Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        st.markdown(HOTLINES_HTML, unsafe_allow_html=True)

        st.markdown("""
        <div style="margin-top: 20px; padding-top: 14px; border-top: 1px solid var(--c-border-mid); text-align: center;">
            <div style="font-family: var(--font-body); font-size: 10px; color: var(--c-text-dim); letter-spacing: 0.5px;">🚀 Samsung Innovation Campus</div>
            <div style="font-family: var(--font-body); font-size: 9px; color: var(--c-text-dim); margin-top: 3px;">© 2026 Awaz-e-Nisa</div>
        </div>
        """, unsafe_allow_html=True)

    # ========== MAIN CONTENT ==========
    feature = st.session_state.active_feature

    st.markdown(f"### ⚖️ {st.session_state.current_mode}")

    if feature == "Legal Chat":
        st.markdown(f"""
        <div class="an-section-header">
            <div style="display:flex;align-items:center;gap:16px;">
                <div style="width:48px;height:48px;background:rgba(232,72,122,0.12);border:1px solid rgba(232,72,122,0.20);border-radius:var(--radius-md);display:flex;align-items:center;justify-content:center;font-size:22px;">⚡</div>
                <div>
                    <div class="an-feature-title">Legal Chat</div>
                    <div style="font-family:var(--font-body);font-size:12px;color:var(--c-text-dim);font-weight:300;margin-top:2px;">Ask any legal question about Pakistani law</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not st.session_state.messages:
            st.markdown("""
            <div style="text-align: center; padding: 52px 20px;">
                <div style="font-size: 52px; margin-bottom: 18px;">⚖️</div>
                <h3 style="font-family:var(--font-display);font-size:28px;font-weight:300;color:var(--c-text);">Welcome to Awaz-e-Nisa</h3>
                <p style="font-family:var(--font-body);color:var(--c-text-muted);font-weight:300;font-size:15px;margin-top:10px;">Your AI legal assistant for Pakistani law. Ask me anything about your legal rights.</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div class="demo-grid">
                <div class="demo-question"><div class="demo-category">Family Law</div><div class="demo-text">My husband married a second woman. What are my rights?</div></div>
                <div class="demo-question"><div class="demo-category">Child Custody</div><div class="demo-text">Can my ex-husband take our children away from me?</div></div>
                <div class="demo-question"><div class="demo-category">Financial Rights</div><div class="demo-text">How much maintenance can I claim for my children?</div></div>
                <div class="demo-question"><div class="demo-category">Khula</div><div class="demo-text">Khula lene ka kya tareeqa hai?</div></div>
            </div>
            """, unsafe_allow_html=True)

        for i, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"], avatar="👩" if msg["role"] == "user" else "⚖️"):
                if msg["role"] == "assistant":
                    msg_mode = msg.get("mode", st.session_state.current_mode)
                    st.markdown(f"<div class='mode-tag'>{msg_mode}</div>", unsafe_allow_html=True)
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and i > 0:
                    prev_q = None
                    for j in range(i-1, -1, -1):
                        if st.session_state.messages[j]["role"] == "user":
                            prev_q = st.session_state.messages[j]["content"]
                            break
                    if prev_q and is_legal_query(prev_q):
                        render_analysis_panel(i, prev_q)

        if prompt := st.chat_input("Type your legal question here..."):
            st.session_state.last_query = prompt
            st.session_state.messages.append({"role": "user", "content": prompt})
            save_chat_message(st.session_state.username, "user", prompt, st.session_state.current_mode)

            with st.chat_message("user", avatar="👩"):
                st.markdown(prompt)

            with st.chat_message("assistant", avatar="⚖️"):
                with st.spinner("Analyzing..."):
                    response = st.session_state.rag.invoke({"question": prompt, "mode": st.session_state.current_mode})
                st.markdown(f"<div class='mode-tag'>{st.session_state.current_mode}</div>", unsafe_allow_html=True)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response, "mode": st.session_state.current_mode})
                save_chat_message(st.session_state.username, "assistant", response, st.session_state.current_mode)
                st.rerun()

    elif feature == "Case Merits":
        st.markdown(f"""
        <div class="an-section-header">
            <div style="display:flex;align-items:center;gap:16px;">
                <div style="width:48px;height:48px;background:rgba(232,72,122,0.12);border:1px solid rgba(232,72,122,0.20);border-radius:var(--radius-md);display:flex;align-items:center;justify-content:center;font-size:22px;">📊</div>
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
                <div style="width:48px;height:48px;background:rgba(232,72,122,0.12);border:1px solid rgba(232,72,122,0.20);border-radius:var(--radius-md);display:flex;align-items:center;justify-content:center;font-size:22px;">⚔</div>
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
                <div style="width:48px;height:48px;background:rgba(232,72,122,0.12);border:1px solid rgba(232,72,122,0.20);border-radius:var(--radius-md);display:flex;align-items:center;justify-content:center;font-size:22px;">📅</div>
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
                <div style="width:48px;height:48px;background:rgba(232,72,122,0.12);border:1px solid rgba(232,72,122,0.20);border-radius:var(--radius-md);display:flex;align-items:center;justify-content:center;font-size:22px;">📄</div>
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
        <div style="text-align:center;padding:52px 28px;background:linear-gradient(135deg,rgba(232,72,122,0.06),rgba(124,58,237,0.06));border:1px solid var(--c-border-mid);border-radius:var(--radius-2xl);margin-bottom:28px;">
            <div style="font-size:60px;margin-bottom:18px;">🌸</div>
            <h2 style="font-family:var(--font-display);font-size:36px;font-weight:300;color:var(--c-text);">About Awaz-e-Nisa</h2>
            <p style="font-family:var(--font-body);color:var(--c-text-muted);font-weight:300;margin-top:8px;">آوازِ نسواں — "Voice of Women"</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background:var(--c-surface);border:1px solid var(--c-border-mid);border-radius:var(--radius-xl);padding:32px;margin-bottom:18px;">
            <h3 style="font-family:var(--font-display);font-size:22px;font-weight:600;color:var(--c-text);margin-bottom:12px;">Our Mission</h3>
            <p style="font-family:var(--font-body);color:var(--c-text-muted);line-height:1.75;font-weight:300;font-size:15px;">Awaz-e-Nisa is a dedicated AI legal assistant designed specifically for Pakistani women and legal professionals working on family cases.</p>
        </div>
        <div style="background:var(--c-surface);border:1px solid var(--c-border-mid);border-radius:var(--radius-xl);padding:32px;margin-bottom:18px;">
            <h3 style="font-family:var(--font-display);font-size:22px;font-weight:600;color:var(--c-text);margin-bottom:16px;">What We Cover</h3>
            <div style="display:flex;flex-wrap:wrap;gap:10px;">
                <span style="background:rgba(232,72,122,0.08);border:1px solid rgba(232,72,122,0.16);color:var(--c-rose-light);padding:6px 16px;border-radius:999px;font-family:var(--font-body);font-size:13px;font-weight:500;">🏛️ Family Law</span>
                <span style="background:rgba(232,72,122,0.08);border:1px solid rgba(232,72,122,0.16);color:var(--c-rose-light);padding:6px 16px;border-radius:999px;font-family:var(--font-body);font-size:13px;font-weight:500;">📝 Khula & Talaq</span>
                <span style="background:rgba(232,72,122,0.08);border:1px solid rgba(232,72,122,0.16);color:var(--c-rose-light);padding:6px 16px;border-radius:999px;font-family:var(--font-body);font-size:13px;font-weight:500;">👶 Child Custody</span>
                <span style="background:rgba(232,72,122,0.08);border:1px solid rgba(232,72,122,0.16);color:var(--c-rose-light);padding:6px 16px;border-radius:999px;font-family:var(--font-body);font-size:13px;font-weight:500;">💰 Haq Mehr</span>
                <span style="background:rgba(232,72,122,0.08);border:1px solid rgba(232,72,122,0.16);color:var(--c-rose-light);padding:6px 16px;border-radius:999px;font-family:var(--font-body);font-size:13px;font-weight:500;">🛡️ Domestic Violence</span>
                <span style="background:rgba(232,72,122,0.08);border:1px solid rgba(232,72,122,0.16);color:var(--c-rose-light);padding:6px 16px;border-radius:999px;font-family:var(--font-body);font-size:13px;font-weight:500;">💻 Cybercrime</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("← Back to Chat", use_container_width=True):
            st.session_state.active_feature = "Legal Chat"
            st.rerun()
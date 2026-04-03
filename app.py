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
import string
import re
import random
import warnings # Added to ignore warnings
from fpdf import FPDF
from database import init_db, add_user, verify_user, save_chat_message, get_chat_history
from streamlit_mic_recorder import mic_recorder

# --- 0. SUPPRESS WARNINGS ---
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# --- 0. CONFIGURATION ---
@st.cache_resource
def configure_paths():
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    if not shutil.which("ffmpeg"):
        winget_base = os.path.join(os.environ.get('LOCALAPPDATA', ''), r'Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.WinGet.Source_8wekyb3d8bbwe')
        found_path = None
        if os.path.exists(winget_base):
            for folder in os.listdir(winget_base):
                if folder.startswith("ffmpeg-"):
                    bin_path = os.path.join(winget_base, folder, 'bin')
                    if os.path.exists(bin_path):
                        found_path = bin_path
                        break
        possible_ffmpeg_paths = [found_path, r'C:\ffmpeg\bin', r'C:\Program Files\ffmpeg\bin']
        for path in possible_ffmpeg_paths:
            if path and os.path.exists(path):
                os.environ["PATH"] = path + os.pathsep + os.environ["PATH"]
                break

configure_paths()

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Awaz-e-Nisa", page_icon="⚖️", layout="wide", initial_sidebar_state="expanded")

@st.cache_resource
def load_whisper_model():
    return whisper.load_model("small")

init_db()

# --- 2. SESSION STATE ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "messages" not in st.session_state: st.session_state.messages = []
if "current_mode" not in st.session_state: st.session_state.current_mode = "GENERAL USER (Woman)"
if "last_audio_id" not in st.session_state: st.session_state.last_audio_id = None
if "expanded_panels" not in st.session_state: st.session_state.expanded_panels = {}

# --- 3. CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #000000 !important; color: #FFFFFF !important; }
    [data-testid="stSidebar"] { 
        background-color: #050505 !important; 
        border-right: 1px solid #FF2E7E33; 
    }
    .sidebar-heading {
        font-size: 11px !important;
        color: #888888 !important;
        font-weight: bold !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        margin-bottom: 10px !important;
        margin-top: 5px !important;
    }
    .law-tip-box {
        padding: 15px;
        background: linear-gradient(135deg, #1a1a1a 0%, #000000 100%);
        border-left: 4px solid #FF2E7E;
        border-radius: 8px;
        margin: 10px 0px;
    }
    .tip-title {
        color: #FF2E7E; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; letter-spacing: 1px;
    }
    .tip-text { color: #cccccc; font-size: 13px; line-height: 1.4; }
    .emergency-box {
        padding: 12px; background-color: #1a0005; border: 1px solid #ff2e7e44; border-radius: 8px; margin-top: 5px;
    }
    .emergency-item { color: #ff4d8d; font-size: 12px; font-weight: bold; margin-bottom: 3px; }
    .voice-container { margin-top: -5px; padding: 0px !important; }
    .mode-tag { 
        background: linear-gradient(90deg, #FF2E7E, #8A2BE2); color: white !important; padding: 4px 12px; border-radius: 15px; 
        font-size: 10px; font-weight: 700; display: inline-block; margin-bottom: 12px;
    }
    [data-testid="stChatMessage"] { background-color: #0D0D0D !important; border: 1px solid #1A1A1A; border-radius: 15px; margin-bottom: 15px; }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 4. HELPER FUNCTIONS ---
def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean_text = text.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text, align='L')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        return tmp.name

def extract_text_from_pdf(file_content):
    try:
        with pdfplumber.open(file_content) as pdf:
            return "\n".join([p.extract_text() or "" for p in pdf.pages])
    except: return "Error reading PDF."

def extract_text_from_image(uploaded_file):
    try:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
        return pytesseract.image_to_string(img).strip()
    except: return "OCR failed."

# --- 5. DEEP ANALYSIS PANEL ---
@st.fragment
def render_analysis_panel(msg_index, original_query):
    panel_key = f"panel_{msg_index}"
    if panel_key not in st.session_state.expanded_panels:
        st.session_state.expanded_panels[panel_key] = {
            "merits": False, "opposition": False, "timeline": False, "draft": False,
            "merits_res": None, "opp_res": None, "time_res": None, "draft_res": None
        }
    
    panel = st.session_state.expanded_panels[panel_key]
    st.markdown("---")
    st.markdown("<p style='color:#888; font-size:11px; font-weight:bold; letter-spacing:1px;'>🔍 DEEP ANALYSIS TOOLS</p>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("✅ Case Merits/Demerits", key=f"m_{msg_index}", use_container_width=True):
            if not panel["merits_res"]:
                with st.spinner("Analyzing..."): panel["merits_res"] = st.session_state.merits_chain.invoke(original_query)
            panel["merits"] = not panel["merits"]; st.rerun()
    with col2:
        if st.button("🔴 Opposition", key=f"o_{msg_index}", use_container_width=True):
            if not panel["opp_res"]:
                with st.spinner("Analyzing..."): panel["opp_res"] = st.session_state.opposition_chain.invoke(original_query)
            panel["opposition"] = not panel["opposition"]; st.rerun()
    with col3:
        if st.button("📅 Timeline", key=f"t_{msg_index}", use_container_width=True):
            if not panel["time_res"]:
                with st.spinner("Analyzing..."): panel["time_res"] = st.session_state.timeline_chain.invoke(original_query)
            panel["timeline"] = not panel["timeline"]; st.rerun()
    with col4:
        if st.button("📄 Legal Draft", key=f"d_{msg_index}", use_container_width=True):
            if not panel["draft_res"]:
                with st.spinner("Analyzing..."): panel["draft_res"] = st.session_state.draft_chain.invoke(original_query)
            panel["draft"] = not panel["draft"]; st.rerun()

    if panel["merits"] and panel["merits_res"]: st.success(panel["merits_res"])
    if panel["opposition"] and panel["opp_res"]: st.error(panel["opp_res"])
    if panel["timeline"] and panel["time_res"]: st.info(panel["time_res"])
    if panel["draft"] and panel["draft_res"]:
        st.warning(panel["draft_res"])
        pdf_path = create_pdf(panel["draft_res"])
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download PDF", f, file_name=f"Legal_Draft_{msg_index}.pdf", key=f"dl_{msg_index}", use_container_width=True)

# --- 6. LOGIN GATE ---
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #FF2E7E; font-family: sans-serif; font-weight: 800;'>AWAZ-E-NISA</h1>", unsafe_allow_html=True)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    col_img, col_login = st.columns([1.5, 1], gap="large")
    with col_img: st.image("https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&q=80&w=800", use_container_width=True)
    with col_login:
        role = st.selectbox("Operational Mode:", ["GENERAL USER (Woman)", "LEGAL PRO"])
        t1, t2 = st.tabs(["🔑 LOGIN", "📝 SIGN UP"])
        with t1:
            with st.form("login"):
                u, p = st.text_input("Username"), st.text_input("Password", type="password")
                if st.form_submit_button("LOGIN", use_container_width=True):
                    if verify_user(u, p):
                        st.session_state.update({"logged_in": True, "username": u, "current_mode": role, "messages": get_chat_history(u)})
                        st.rerun()
        with t2:
            with st.form("signup"):
                nu, np_ = st.text_input("New Username"), st.text_input("New Password", type="password")
                if st.form_submit_button("REGISTER", use_container_width=True):
                    if add_user(nu, np_): st.success("Account Created!")

# --- 7. MAIN APP ---
else:
    if "rag" not in st.session_state:
        from legal_advisor import rag_chain, merits_chain, opposition_chain, timeline_chain, draft_chain
        st.session_state.update({"rag": rag_chain, "merits_chain": merits_chain, "opposition_chain": opposition_chain, "timeline_chain": timeline_chain, "draft_chain": draft_chain})

    with st.sidebar:
        st.markdown("<h2 style='color: #FF2E7E; margin-bottom:0;'>AWAZ-E-NISA</h2>", unsafe_allow_html=True)
        st.write(f"Logged in as: **{st.session_state.username}**")
        legal_tips = [
            ("Women's Rights", "Article 25 ensures protection for women and children."),
            ("Workplace", "The 2010 Act protects you from harassment at work."),
            ("Cyber Law", "Reporting online abuse to FIA is your legal right.")
        ]
        title, content = random.choice(legal_tips)
        st.markdown(f'<div class="law-tip-box"><div class="tip-title">⚖️ {title}</div><div class="tip-text">{content}</div></div>', unsafe_allow_html=True)
        
        st.divider()
        st.markdown('<p class="sidebar-heading">VOICE COMMAND</p>', unsafe_allow_html=True)
        st.markdown('<div class="voice-container">', unsafe_allow_html=True)
        audio = mic_recorder(key="mic", start_prompt="🎤 Start Speaking", stop_prompt="⏹️ Stop", just_once=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        st.markdown('<p class="sidebar-heading">VIEW MODE</p>', unsafe_allow_html=True)
        new_mode = st.radio("Select operational mode:", ["GENERAL USER (Woman)", "LEGAL PRO"], label_visibility="collapsed")
        if new_mode != st.session_state.current_mode:
            st.session_state.current_mode = new_mode
            st.rerun()
        
        st.divider()
        st.markdown('<p class="sidebar-heading">DOCUMENT SCANNER</p>', unsafe_allow_html=True)
        uploaded_docs = st.file_uploader("Upload documents", type=['pdf', 'png', 'jpg'], accept_multiple_files=True, label_visibility="collapsed")
        
        if uploaded_docs:
            if st.button("🔍 Process Documents", use_container_width=True):
                full_text = ""
                for doc in uploaded_docs:
                    if doc.type == "application/pdf": full_text += extract_text_from_pdf(doc)
                    else: full_text += extract_text_from_image(doc)
                
                if full_text.strip():
                    doc_query = f"Analyzed Document Content: {full_text[:500]}..."
                    st.session_state.messages.append({"role": "user", "content": doc_query, "mode": st.session_state.current_mode})
                    save_chat_message(st.session_state.username, "user", doc_query, st.session_state.current_mode)
                    
                    with st.spinner("Analyzing Document..."):
                        res = st.session_state.rag.invoke({"question": full_text, "mode": st.session_state.current_mode})
                        st.session_state.messages.append({"role": "assistant", "content": res, "mode": st.session_state.current_mode})
                        save_chat_message(st.session_state.username, "assistant", res, st.session_state.current_mode)
                    st.rerun()

        st.divider()
        st.markdown('<p class="sidebar-heading">🚨 HELP LINES</p>', unsafe_allow_html=True)
        st.markdown('<div class="emergency-box"><div class="emergency-item">📞 Women Help: 1094</div><div class="emergency-item">🛡️ Police: 15</div></div>', unsafe_allow_html=True)
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    st.markdown(f"### ⚖️ {st.session_state.current_mode}")
    if not st.session_state.messages:
        st.info("👋 Welcome! State your legal issue or use the microphone.")
    else:
        for i, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"], avatar="👩" if msg["role"] == "user" else "⚖️"):
                st.markdown(f"<div class='mode-tag'>{msg.get('mode', 'GENERAL')}</div>", unsafe_allow_html=True)
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and i > 0:
                    prev_q = next((st.session_state.messages[j]["content"] for j in range(i-1, -1, -1) if st.session_state.messages[j]["role"] == "user"), "")
                    if prev_q: render_analysis_panel(i, prev_q)

    if prompt := st.chat_input("Enter query..."):
        st.session_state.messages.append({"role": "user", "content": prompt, "mode": st.session_state.current_mode})
        save_chat_message(st.session_state.username, "user", prompt, st.session_state.current_mode)
        with st.chat_message("user", avatar="👩"): st.markdown(prompt)
        with st.spinner("Searching database..."):
            res = st.session_state.rag.invoke({"question": prompt, "mode": st.session_state.current_mode})
            st.session_state.messages.append({"role": "assistant", "content": res, "mode": st.session_state.current_mode})
            save_chat_message(st.session_state.username, "assistant", res, st.session_state.current_mode)
        st.rerun()

    if audio and audio.get('id') != st.session_state.last_audio_id:
        st.session_state.last_audio_id = audio['id']
        whisper_model = load_whisper_model()
        with st.spinner("Processing Voice..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio['bytes'])
                result = whisper_model.transcribe(tmp.name, language="ur", task="translate")
                detected_text = result["text"].strip()
            if detected_text:
                voice_content = f"🎤: {detected_text}"
                st.session_state.messages.append({"role": "user", "content": voice_content, "mode": st.session_state.current_mode})
                save_chat_message(st.session_state.username, "user", voice_content, st.session_state.current_mode)
                res = st.session_state.rag.invoke({"question": detected_text, "mode": st.session_state.current_mode})
                st.session_state.messages.append({"role": "assistant", "content": res, "mode": st.session_state.current_mode})
                save_chat_message(st.session_state.username, "assistant", res, st.session_state.current_mode)
                st.rerun()
import streamlit as st
import google.generativeai as genai
from groq import Groq
import requests
import json
from PIL import Image
import io
import sys
import os
import hashlib
import datetime
import pandas as pd
import matplotlib.pyplot as plt

# ==========================================
# 1. PAGE CONFIG & ADVANCED 3D CSS
# ==========================================
st.set_page_config(page_title="NEXUS AI OS", page_icon="🌌", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* Dark Space Gradient Background */
    .stApp {
        background: radial-gradient(circle at 50% 0%, #0b0f19, #000000);
        color: #e2e8f0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* 3D Glassmorphism Chat Bubbles */[data-testid="stChatMessage"] {
        background: rgba(16, 24, 39, 0.6) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(56, 189, 248, 0.15) !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255,255,255,0.1) !important;
        padding: 20px !important;
        margin-bottom: 24px !important;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }[data-testid="stChatMessage"]:hover {
        transform: translateY(-5px) scale(1.01);
        border: 1px solid rgba(56, 189, 248, 0.4) !important;
        box-shadow: 0 20px 40px -10px rgba(56, 189, 248, 0.2) !important;
    }

    /* Glow Text */
    .nexus-title {
        font-size: 3rem; font-weight: 900; text-align: center; letter-spacing: 2px;
        background: linear-gradient(to right, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-transform: uppercase; margin-bottom: 0px;
        text-shadow: 0px 0px 20px rgba(129, 140, 248, 0.3);
    }
    .nexus-subtitle { text-align: center; color: #94a3b8; font-size: 1rem; margin-bottom: 30px; }

    /* Custom Scrollbar */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #0f172a; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: #475569; }
    
    /* Hide Deploy Button & Footer */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE & ENCRYPTION SYSTEM
# ==========================================
DB_FILE = "nexus_os_db.json"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {"users": {}, "chats": {}}

def save_db(db):
    with open(DB_FILE, "w") as f: json.dump(db, f)

db = load_db()

# ==========================================
# 3. SESSION STATE INITIALIZATION
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = "Guest"
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = "Default"
if "api_keys" not in st.session_state:
    st.session_state.api_keys = {"GROQ": "", "GEMINI": "", "OPENROUTER": ""}
if "messages" not in st.session_state:
    st.session_state.messages =[]

# ==========================================
# 4. SIDEBAR - OS CONTROL PANEL
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #38bdf8;'>🌌 Control Panel</h2>", unsafe_allow_html=True)
    
    # --- Authentication Module ---
    if not st.session_state.logged_in:
        with st.expander("🔐 User Login / Register", expanded=True):
            tab1, tab2 = st.tabs(["Login", "Register"])
            with tab1:
                l_user = st.text_input("Username", key="l_user")
                l_pass = st.text_input("Password", type="password", key="l_pass")
                if st.button("Access System", use_container_width=True):
                    if l_user in db["users"] and db["users"][l_user] == hash_password(l_pass):
                        st.session_state.logged_in = True
                        st.session_state.username = l_user
                        st.rerun()
                    else:
                        st.error("Access Denied.")
            with tab2:
                r_user = st.text_input("New Username", key="r_user")
                r_pass = st.text_input("New Password", type="password", key="r_pass")
                if st.button("Create Account", use_container_width=True):
                    if r_user in db["users"]: st.error("User exists.")
                    elif r_user and r_pass:
                        db["users"][r_user] = hash_password(r_pass)
                        db["chats"][r_user] = {"Default":[]}
                        save_db(db)
                        st.success("Registered! Please Login.")
    else:
        st.success(f"🟢 User: {st.session_state.username.upper()}")
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = "Guest"
            st.rerun()

    st.divider()

    # --- Chat Session Management ---
    st.markdown("### 🗂️ Workspaces")
    if st.session_state.logged_in:
        user_chats = list(db["chats"].get(st.session_state.username, {"Default":[]}).keys())
        selected_chat = st.selectbox("Switch Workspace", user_chats, index=user_chats.index(st.session_state.current_chat_id) if st.session_state.current_chat_id in user_chats else 0)
        
        if selected_chat != st.session_state.current_chat_id:
            st.session_state.current_chat_id = selected_chat
            st.session_state.messages = db["chats"][st.session_state.username][selected_chat]
            st.rerun()

        new_chat_name = st.text_input("New Workspace Name")
        if st.button("➕ Create Workspace"):
            if new_chat_name and new_chat_name not in user_chats:
                db["chats"][st.session_state.username][new_chat_name] =[]
                save_db(db)
                st.session_state.current_chat_id = new_chat_name
                st.session_state.messages =[]
                st.rerun()
    else:
        st.info("Login to save multiple workspaces.")
        if st.button("🗑️ Clear Guest Chat"):
            st.session_state.messages =[]
            st.rerun()

    st.divider()

    # --- AI Settings & Models ---
    st.markdown("### ⚙️ AI Engine Configuration")
    provider = st.selectbox("AI Provider",["Groq (Fast Processing)", "Gemini (Vision & Logic)", "OpenRouter (Multi-Model)"])
    
    if provider == "Groq (Fast Processing)": model_name = st.selectbox("Model",["llama-3.3-70b-versatile", "qwen-2.5-coder-32b", "mixtral-8x7b-32768"])
    elif provider == "Gemini (Vision & Logic)": model_name = st.selectbox("Model",["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-exp"])
    else: model_name = st.selectbox("Model",["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "deepseek/deepseek-r1"])

    persona = st.selectbox("AI Persona",["Super Intelligence", "Expert Programmer", "Data Analyst", "Creative Author"])
    temperature = st.slider("Creativity (Temperature)", 0.0, 1.0, 0.7)

    # --- Secure API Key Inputs (BYOK) ---
    with st.expander("🔑 Secure API Key Configuration"):
        st.caption("Leave blank if you hardcoded them in the script.")
        st.session_state.api_keys["GROQ"] = st.text_input("Groq Key", type="password", value=st.session_state.api_keys["GROQ"])
        st.session_state.api_keys["GEMINI"] = st.text_input("Gemini Key", type="password", value=st.session_state.api_keys["GEMINI"])
        st.session_state.api_keys["OPENROUTER"] = st.text_input("OpenRouter Key", type="password", value=st.session_state.api_keys["OPENROUTER"])

# ==========================================
# 5. CORE FUNCTIONS (Code Interpreter & Data)
# ==========================================
def run_python_environment(code):
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        exec(code, globals())
        output = sys.stdout.getvalue()
    except Exception as e:
        output = str(e)
    finally:
        sys.stdout = old_stdout
    return output

# Hardcoded keys as fallback
FALLBACK_GROQ = "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"
FALLBACK_GEMINI = "আপনার_GEMINI_API_KEY"
FALLBACK_OPENROUTER = "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"

def get_key(provider):
    key = st.session_state.api_keys.get(provider, "")
    if not key:
        if provider == "GROQ": return FALLBACK_GROQ
        if provider == "GEMINI": return FALLBACK_GEMINI
        if provider == "OPENROUTER": return FALLBACK_OPENROUTER
    return key

# ==========================================
# 6. MAIN UI & CHAT INTERFACE
# ==========================================
st.markdown("<p class='nexus-title'>NEXUS AI OS</p>", unsafe_allow_html=True)
st.markdown("<p class='nexus-subtitle'>Enterprise-Grade Multi-Modal Artificial Intelligence</p>", unsafe_allow_html=True)

# Display Chat Messages
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Code Execution Block
        if message["role"] == "assistant" and "```python" in message["content"]:
            code_snippet = message["content"].split("```python")[1].split("```")[0]
            if st.button(f"⚡ Execute Script {i}", key=f"btn_{i}"):
                with st.spinner("Compiling & Executing..."):
                    result = run_python_environment(code_snippet)
                    st.success("Execution Complete")
                    st.code(result, language="bash")

# ==========================================
# 7. MULTIMODAL INPUT & LOGIC
# ==========================================
st.write("---")
input_col, file_col = st.columns([0.85, 0.15])

with file_col:
    uploaded_file = st.file_uploader("Upload", type=["jpg", "png", "pdf", "csv"], label_visibility="collapsed")
with input_col:
    prompt = st.chat_input("Command Nexus OS...")

if prompt or uploaded_file:
    # Process Uploads first
    user_message = prompt if prompt else "Analyze the uploaded file."
    
    if uploaded_file and uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        st.dataframe(df.head())
        user_message = f"Here is a dataset with columns {list(df.columns)}. User question: {user_message}"

    # Append & Save User Message
    st.session_state.messages.append({"role": "user", "content": user_message})
    if st.session_state.logged_in:
        db["chats"][st.session_state.username][st.session_state.current_chat_id] = st.session_state.messages
        save_db(db)
    st.rerun()

# ==========================================
# 8. AI RESPONSE GENERATION
# ==========================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        response_box = st.empty()
        full_response = ""
        system_prompt = f"You are NEXUS, a {persona}. Provide highly accurate and professional responses."

        try:
            # --- GEMINI VISION LOGIC ---
            if uploaded_file and uploaded_file.name.lower().endswith(('jpg', 'png', 'jpeg')):
                img = Image.open(uploaded_file)
                st.image(img, caption="Visual Input", width=300)
                genai.configure(api_key=get_key("GEMINI"))
                model = genai.GenerativeModel("gemini-1.5-pro")
                response = model.generate_content([system_prompt, st.session_state.messages[-1]["content"], img])
                full_response = response.text
                response_box.markdown(full_response)

            # --- GROQ TEXT LOGIC ---
            elif provider == "Groq (Fast Processing)":
                client = Groq(api_key=get_key("GROQ"))
                msgs =[{"role": "system", "content": system_prompt}] + [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                stream = client.chat.completions.create(model=model_name, messages=msgs, temperature=temperature, stream=True)
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        response_box.markdown(full_response + "▌")

            # --- GEMINI TEXT LOGIC ---
            elif provider == "Gemini (Vision & Logic)":
                genai.configure(api_key=get_key("GEMINI"))
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(st.session_state.messages[-1]["content"], stream=True)
                for chunk in response:
                    full_response += chunk.text
                    response_box.markdown(full_response + "▌")

            # --- OPENROUTER LOGIC ---
            elif provider == "OpenRouter (Multi-Model)":
                headers = {"Authorization": f"Bearer {get_key('OPENROUTER')}", "Content-Type": "application/json"}
                payload = {
                    "model": model_name,
                    "temperature": temperature,
                    "messages":[{"role": "system", "content": system_prompt}] + [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                }
                res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                full_response = res.json()['choices'][0]['message']['content']
                response_box.markdown(full_response)

            response_box.markdown(full_response)
            
            # Append & Save AI Message
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            if st.session_state.logged_in:
                db["chats"][st.session_state.username][st.session_state.current_chat_id] = st.session_state.messages
                save_db(db)

        except Exception as e:
            st.error(f"SYSTEM OVERLOAD ERROR: Please check API Keys or connection. Details: {e}")

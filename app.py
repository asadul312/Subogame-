import streamlit as st
import google.generativeai as genai
from groq import Groq
from anthropic import Anthropic
import requests
import json
from PIL import Image
import io
import sys
import os
import hashlib
import base64

# ১. পেজ ডিজাইন
st.set_page_config(page_title="NEXUS VISION AI PRO", page_icon="👁️", layout="wide")
st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at center, #0b0f19, #000000); color: #e2e8f0; }
    [data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.04) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
        border-radius: 15px !important;
        padding: 12px 18px !important; margin-bottom: 12px !important;
    }
    .nexus-title {
        font-size: 2.8rem; font-weight: 800; text-align: center;
        background: linear-gradient(to right, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    </style>
""", unsafe_allow_html=True)

# ২. মডেল ক্যাটালগ (FIXED IDs)
MODEL_CATALOG = {
    "Gemini: 1.5 Pro 👁️": {"id": "gemini-1.5-pro", "provider": "gemini"},
    "Anthropic: Claude 3.5 Sonnet 👁️": {"id": "claude-3-5-sonnet-20240620", "provider": "anthropic"},
    "Groq: Llama 3.2 Vision (11B) 👁️": {"id": "llama-3.2-11b-vision", "provider": "groq"},
    "Groq: Llama 3.2 Vision (90B) 👁️": {"id": "llama-3.2-90b-vision", "provider": "groq"},
}

# সেশন ও সিকিউরিটি
DB_FILE = "nexus_final_db.json"
def hash_pass(password): return hashlib.sha256(password.encode()).hexdigest()
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {"users": {}, "chats": {}}
def save_db(db):
    with open(DB_FILE, "w") as f: json.dump(db, f)
db = load_db()

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = "Guest"
if "api_keys" not in st.session_state: st.session_state.api_keys = {"GROQ": "", "GEMINI": "", "ANTHROPIC": ""}
if "messages" not in st.session_state: st.session_state.messages =[]

# সাইডবার
with st.sidebar:
    st.markdown("<h2 style='color: #38bdf8;'>⚙️ Settings</h2>", unsafe_allow_html=True)
    if not st.session_state.logged_in:
        auth = st.radio("Access", ["Login", "Register"], horizontal=True)
        u, p = st.text_input("User"), st.text_input("Pass", type="password")
        if st.button(auth, use_container_width=True):
            if auth == "Register" and u and p:
                db["users"][u] = hash_pass(p); db["chats"][u] = []; save_db(db); st.success("Registered!")
            elif auth == "Login" and db["users"].get(u) == hash_pass(p):
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.messages = db["chats"].get(u, []); st.rerun()
    else:
        st.success(f"🟢 User: {st.session_state.username}")
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False; st.rerun()

    st.divider()
    selected_model_name = st.selectbox("Select Model", list(MODEL_CATALOG.keys()))
    with st.expander("🔑 Secure API Keys"):
        st.session_state.api_keys["GROQ"] = st.text_input("Groq Key", type="password", value=st.session_state.api_keys["GROQ"])
        st.session_state.api_keys["GEMINI"] = st.text_input("Gemini Key", type="password", value=st.session_state.api_keys["GEMINI"])
        st.session_state.api_keys["ANTHROPIC"] = st.text_input("Anthropic Key", type="password", value=st.session_state.api_keys["ANTHROPIC"])

# ইউটিলিটি
def get_key(prov):
    k = st.session_state.api_keys.get(prov.upper())
    if k: return k
    return {"GROQ": "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", "GEMINI": "", "ANTHROPIC": ""}.get(prov.upper())

def img_to_b64(img):
    buf = io.BytesIO(); img.save(buf, format="JPEG"); return base64.b64encode(buf.getvalue()).decode()

# মেইন টাইটেল
st.markdown("<div class='nexus-title'>NEXUS VISION AI</div>", unsafe_allow_html=True)

# চ্যাট হিস্ট্রি প্রদর্শন
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "imgs_b64" in msg:
            for b in msg["imgs_b64"]: st.image(io.BytesIO(base64.b64decode(b)), width=250)

# ইনপুট
inp = st.chat_input("Ask or attach image...")
if inp:
    txt = getattr(inp, "text", "")
    files = getattr(inp, "files", [])
    if not txt and files: txt = "Analyze this."
    m = {"role": "user", "content": txt, "imgs_b64": []}
    if files:
        for f in files:
            if f.name.lower().endswith(('png','jpg','jpeg')): m["imgs_b64"].append(img_to_b64(Image.open(f)))
    st.session_state.messages.append(m)
    if st.session_state.logged_in:
        db["chats"][st.session_state.username] = st.session_state.messages; save_db(db)
    st.rerun()

# এআই লজিক
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last = st.session_state.messages[-1]
    info = MODEL_CATALOG[selected_model_name]
    key = get_key(info["provider"])
    
    if not key or "আপনার_" in key:
        with st.chat_message("assistant"): st.error(f"Key missing for {info['provider']}")
    else:
        with st.chat_message("assistant"):
            box = st.empty(); full = ""
            try:
                if info["provider"] == "gemini":
                    genai.configure(api_key=key)
                    model = genai.GenerativeModel(info["id"])
                    payload = [last["content"]] + [Image.open(io.BytesIO(base64.b64decode(b))) for b in last["imgs_b64"]]
                    res = model.generate_content(payload, stream=True)
                    for chunk in res: full += chunk.text; box.markdown(full + "▌")
                elif info["provider"] == "anthropic":
                    client = Anthropic(api_key=key)
                    cnt = [{"type": "text", "text": last["content"]}]
                    for b in last["imgs_b64"]: cnt.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b}})
                    with client.messages.stream(model=info["id"], max_tokens=2048, messages=[{"role": "user", "content": cnt}]) as s:
                        for c in s.text_stream: full += c; box.markdown(full + "▌")
                elif info["provider"] == "groq":
                    client = Groq(api_key=key)
                    cnt = [{"type": "text", "text": last["content"]}]
                    for b in last["imgs_b64"]: cnt.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b}"}})
                    stream = client.chat.completions.create(model=info["id"], messages=[{"role": "user", "content": cnt}], stream=True)
                    for c in stream: 
                        if c.choices[0].delta.content: full += c.choices[0].delta.content; box.markdown(full + "▌")
                box.markdown(full); st.session_state.messages.append({"role": "assistant", "content": full})
                if st.session_state.logged_in: db["chats"][st.session_state.username] = st.session_state.messages; save_db(db)
            except Exception as e: st.error(f"Error: {e}")

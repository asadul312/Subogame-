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
import pandas as pd
from bs4 import BeautifulSoup

# ==========================================
# ১. পেজ ডিজাইন 
# ==========================================
st.set_page_config(page_title="NEXUS AI OS", page_icon="🌌", layout="wide")

st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at top right, #0b0f19, #000000); color: #e2e8f0; }
    
    [data-testid="stChatMessage"] {
        background: rgba(16, 24, 39, 0.8) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
        border-radius: 12px !important;
        padding: 15px 20px !important;
        margin-bottom: 12px !important;
        font-size: 15px;
    }
    
    .nexus-title {
        font-size: 2.5rem; font-weight: bold; text-align: center;
        background: linear-gradient(to right, #38bdf8, #c084fc);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ২. ডাটাবেস এবং সেশন 
# ==========================================
DB_FILE = "nexus_db.json"

def hash_pass(password): return hashlib.sha256(password.encode()).hexdigest()

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {"users": {}, "chats": {}}

def save_db(db):
    with open(DB_FILE, "w") as f: json.dump(db, f)

db = load_db()

# সেশন ভ্যারিয়েবলস
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = "Guest"
if "api_keys" not in st.session_state: st.session_state.api_keys = {"GROQ": "", "GEMINI": "", "OPENROUTER": ""}
if "messages" not in st.session_state: st.session_state.messages =[]
if "code_outputs" not in st.session_state: st.session_state.code_outputs = {}

# ==========================================
# ৩. সেফ ওয়েব সার্চ (Crash-proof)
# ==========================================
def safe_web_search(query):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(f"https://html.duckduckgo.com/html/?q={query}", headers=headers, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        results =[a.text for a in soup.find_all('a', class_='result__snippet')]
        if results: return " ".join(results[:3])
        return "No direct snippet found."
    except:
        return "Web search is currently unavailable."

# ==========================================
# ৪. সাইডবার সেটিংস
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: #38bdf8;'>⚙️ Settings</h2>", unsafe_allow_html=True)
    
    # লগইন প্যানেল
    if not st.session_state.logged_in:
        auth_mode = st.radio("Access",["Login", "Register"], horizontal=True)
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.button(auth_mode):
            if auth_mode == "Register" and user and pwd:
                if user not in db["users"]:
                    db["users"][user] = hash_pass(pwd)
                    db["chats"][user] =[]
                    save_db(db)
                    st.success("Registered! You can login now.")
            elif auth_mode == "Login" and user in db["users"] and db["users"][user] == hash_pass(pwd):
                st.session_state.logged_in = True
                st.session_state.username = user
                st.session_state.messages = db["chats"].get(user,[])
                st.rerun()
    else:
        st.success(f"🟢 User: {st.session_state.username}")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = "Guest"
            st.session_state.messages =[]
            st.session_state.code_outputs = {}
            st.rerun()

    st.divider()
    
    provider = st.selectbox("AI Engine",["Groq", "Gemini", "OpenRouter"])
    if provider == "Groq": model_name = st.selectbox("Model",["llama-3.3-70b-versatile", "qwen-2.5-coder-32b"])
    elif provider == "Gemini": model_name = st.selectbox("Model",["gemini-1.5-pro", "gemini-1.5-flash"])
    else: model_name = st.selectbox("Model",["openai/gpt-4o", "deepseek/deepseek-r1"])

    use_web_search = st.checkbox("🌐 Enable Web Search")
with st.expander("🔑 Secure API Keys"):
        st.session_state.api_keys["GROQ"] = st.text_input("Groq Key", type="password", value=st.session_state.api_keys["GROQ"])
        st.session_state.api_keys["GEMINI"] = st.text_input("Gemini Key", type="password", value=st.session_state.api_keys["GEMINI"])
        st.session_state.api_keys["OPENROUTER"] = st.text_input("OpenRouter Key", type="password", value=st.session_state.api_keys["OPENROUTER"])

def get_key(prov):
    # ব্যবহারকারী যদি ওয়েবসাইটে কী দেয়, তবে সেটি ব্যবহার হবে
    if st.session_state.api_keys.get(prov):
        return st.session_state.api_keys.get(prov)
    
    # ==========================================
    # 💡 বিকল্প: আপনার আসল এপিআই কীগুলো এখানে বসান 💡
    # ==========================================
    hardcoded_keys = {
        "GROQ": "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",
        "GEMINI": "আপনার_GEMINI_কী_এখানে_দিন",
        "OPENROUTER": "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"
    }
    return hardcoded_keys.get(prov)
# ==========================================
# ৫. চ্যাট হিস্ট্রি এবং কোড রানার
# ==========================================
st.markdown("<div class='nexus-title'>NEXUS AI OS</div>", unsafe_allow_html=True)

def run_code(code):
    old_out = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    try: 
        exec(code, globals())
        output = redirected_output.getvalue()
        return output if output.strip() else "✅ Code ran successfully (No printed output)."
    except Exception as e: 
        return f"❌ Error:\n{str(e)}"
    finally: 
        sys.stdout = old_out

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        if msg.get("images"):
            for img in msg["images"]: st.image(img, width=200)
        if msg.get("dataframes"):
            for df in msg["dataframes"]: st.dataframe(df.head())
        
        if msg["role"] == "assistant" and "```python" in msg["content"]:
            code_blocks = msg["content"].split("```python")[1:]
            for idx, block in enumerate(code_blocks):
                code_str = block.split("```")[0].strip()
                btn_key = f"run_btn_{i}_{idx}"
                
                col1, col2, col3 = st.columns([0.15, 0.25, 0.6])
                with col1:
                    if st.button("▶️ Run Code", key=btn_key):
                        st.session_state.code_outputs[btn_key] = run_code(code_str)
                with col2:
                    st.download_button("📥 Download .py", data=code_str, file_name=f"script_{i}_{idx}.py", mime="text/plain", key=f"dl_{i}_{idx}")
                
                if btn_key in st.session_state.code_outputs:
                    st.code(st.session_state.code_outputs[btn_key], language="bash")

# ==========================================
# ৬. ইনপুট প্রসেসিং (100% Bug-Free)
# ==========================================
prompt_data = st.chat_input("Ask anything or attach a file...", accept_file="multiple")

if prompt_data:
    user_txt = ""
    uploaded_files =[]
    
    # স্ট্রিং এবং ডিকশনারি উভয়ের জন্যই নিরাপদ চেকিং
    if isinstance(prompt_data, dict):
        user_txt = prompt_data.get("text", "")
        uploaded_files = prompt_data.get("files",[])
    elif hasattr(prompt_data, "text") and hasattr(prompt_data, "files"):
        user_txt = prompt_data.text
        uploaded_files = prompt_data.files
    else:
        user_txt = str(prompt_data)

    if not user_txt and uploaded_files: 
        user_txt = "Please analyze the attached files."
    
    new_msg = {"role": "user", "content": user_txt, "images":[], "dataframes":[]}
    
    # ফাইল এক্সট্রাকশন
    if uploaded_files:
        for f in uploaded_files:
            try:
                if f.name.lower().endswith(('png', 'jpg', 'jpeg')): new_msg["images"].append(Image.open(f))
                elif f.name.lower().endswith('csv'): new_msg["dataframes"].append(pd.read_csv(f))
            except Exception as e: 
                st.error(f"Error loading file: {e}")

    # ওয়েব সার্চ অ্যাড করা
    if use_web_search and user_txt:
        with st.spinner("🌐 Searching the Web..."):
            web_info = safe_web_search(user_txt)
            new_msg["content"] = f"User Query: {user_txt}\n\n[Live Web Data for context]: {web_info}"

    st.session_state.messages.append(new_msg)
    
    if st.session_state.logged_in:
        safe_msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        db["chats"][st.session_state.username] = safe_msgs
        save_db(db)
        
    st.rerun()

# ==========================================
# ৭. এআই রেসপন্স এবং এপিআই চেকিং
# ==========================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_msg = st.session_state.messages[-1]
    
    # এপিআই কী চেক করা
    current_key = get_key(provider.split(" ")[0].upper())
    if not current_key:
        with st.chat_message("assistant"):
            st.error(f"⚠️ You haven't added an API Key for {provider}. Please open 'Settings -> Secure API Keys' in the sidebar to enter your key.")
    else:
        with st.chat_message("assistant"):
            res_box = st.empty()
            full_res = ""
            
            try:
                # ছবি থাকলে Gemini
                if last_msg.get("images"):
                    gemini_key = get_key("GEMINI")
                    if not gemini_key:
                        st.error("⚠️ Image processing requires a Gemini API Key!")
                    else:
                        genai.configure(api_key=gemini_key)
                        model = genai.GenerativeModel("gemini-1.5-flash")
                        payload =[last_msg["content"]] + last_msg["images"]
                        response = model.generate_content(payload, stream=True)
                        for chunk in response:
                            full_res += chunk.text
                            res_box.markdown(full_res + "▌")
                        
                else:
                    if provider == "Groq":
                        client = Groq(api_key=current_key)
                        msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                        stream = client.chat.completions.create(model=model_name, messages=msgs, stream=True)
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                full_res += chunk.choices[0].delta.content
                                res_box.markdown(full_res + "▌")
                                
                    elif provider == "Gemini":
                        genai.configure(api_key=current_key)
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(last_msg["content"], stream=True)
                        for chunk in response:
                            full_res += chunk.text
                            res_box.markdown(full_res + "▌")
                            
                    elif provider == "OpenRouter":
                        headers = {"Authorization": f"Bearer {current_key}", "Content-Type": "application/json"}
                        payload = {"model": model_name, "messages":[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]}
                        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                        full_res = res.json()['choices'][0]['message']['content']
                        res_box.markdown(full_res + "▌")
                        
                res_box.markdown(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
                
                if st.session_state.logged_in:
                    safe_msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                    db["chats"][st.session_state.username] = safe_msgs
                    save_db(db)
                    
            except Exception as e:
                st.error(f"⚠️ API Error: Make sure your '{provider}' API key is correct. Details: {e}")

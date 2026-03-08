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
# ১. পেজ ডিজাইন (NEXUS OS 3D UI)
# ==========================================
st.set_page_config(page_title="NEXUS AI OS", page_icon="🌌", layout="wide")

st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at top right, #0b0f19, #000000); color: #e2e8f0; }
    
    [data-testid="stChatMessage"] {
        background: rgba(16, 24, 39, 0.7) !important;
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
    
    /* ডাউনলোড ও রান বাটন স্টাইল */
    .stDownloadButton button { background-color: #10b981 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ২. ডাটাবেস এবং সেশন সিস্টেম
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

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = "Guest"
if "api_keys" not in st.session_state: st.session_state.api_keys = {"GROQ": "", "GEMINI": "", "OPENROUTER": ""}
if "messages" not in st.session_state: st.session_state.messages =[]
if "code_outputs" not in st.session_state: st.session_state.code_outputs = {}

# ==========================================
# ৩. ওয়েব সার্চ ইঞ্জিন ফাংশন (DuckDuckGo Lite)
# ==========================================
def web_search(query):
    try:
        url = f"https://html.duckduckgo.com/html/?q={query}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        results =[a.text for a in soup.find_all('a', class_='result__snippet')]
        return " ".join(results[:3]) if results else "No direct results found."
    except:
        return "Web search failed."

# ==========================================
# ৪. সাইডবার সেটিংস ও নতুন ফিচার
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
                st.session_state.messages = db["chats"][user]
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
    
    # মডেল ও ইন্টারনেট অপশন
    provider = st.selectbox("AI Engine",["Groq", "Gemini", "OpenRouter"])
    if provider == "Groq": model_name = st.selectbox("Model",["llama-3.3-70b-versatile", "qwen-2.5-coder-32b"])
    elif provider == "Gemini": model_name = st.selectbox("Model",["gemini-1.5-pro", "gemini-1.5-flash"])
    else: model_name = st.selectbox("Model",["openai/gpt-4o", "deepseek/deepseek-r1"])

    use_web_search = st.checkbox("🌐 Enable Web Search (Real-time data)")

    # প্রম্পট লাইব্রেরি
    with st.expander("📚 Prompt Library"):
        quick_prompt = st.selectbox("Quick Tasks", ["Select...", "Write a Snake Game in Python", "Analyze this data", "Explain Quantum Physics simply"])

    # এপিআই কী সেটআপ
    with st.expander("🔑 Secure API Keys"):
        st.session_state.api_keys["GROQ"] = st.text_input("Groq Key", type="password", value=st.session_state.api_keys["GROQ"])
        st.session_state.api_keys["GEMINI"] = st.text_input("Gemini Key", type="password", value=st.session_state.api_keys["GEMINI"])
        st.session_state.api_keys["OPENROUTER"] = st.text_input("OpenRouter Key", type="password", value=st.session_state.api_keys["OPENROUTER"])

def get_key(prov):
    k = st.session_state.api_keys.get(prov, "")
    # ==========================================
    # ⚠️ আপনার আসল এপিআই কীগুলো এখানে বসান ⚠️
    # ==========================================
    fallbacks = {
        "GROQ": "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", # এখানে আপনার Groq কী দিন
        "GEMINI": "", # এখানে আপনার Gemini কী দিন
        "OPENROUTER": "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" # এখানে আপনার OpenRouter কী দিন
    }
    return k if k else fallbacks.get(prov)

# ==========================================
# ৫. চ্যাট হিস্ট্রি, কোড রানার ও ডাউনলোডার
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
        
        # কোড রানার এবং ডাউনলোড বাটন
        if msg["role"] == "assistant" and "```python" in msg["content"]:
            code_blocks = msg["content"].split("```python")[1:]
            for idx, block in enumerate(code_blocks):
                code_str = block.split("```")[0].strip()
                btn_key = f"run_btn_{i}_{idx}"
                
                # পাশাপাশি বাটন রাখার জন্য কলাম
                col1, col2, col3 = st.columns([0.15, 0.25, 0.6])
                with col1:
                    if st.button("▶️ Run Code", key=btn_key):
                        st.session_state.code_outputs[btn_key] = run_code(code_str)
                with col2:
                    st.download_button("📥 Download .py", data=code_str, file_name=f"script_{i}.py", mime="text/plain", key=f"dl_{i}_{idx}")
                
                if btn_key in st.session_state.code_outputs:
                    st.code(st.session_state.code_outputs[btn_key], language="bash")

# ==========================================
# ৬. ফাইল আপলোড ও ইনপুট লজিক
# ==========================================
prompt_data = st.chat_input("Ask anything or attach a file...", accept_file="multiple")

# যদি প্রম্পট লাইব্রেরি থেকে কিছু সিলেক্ট করা হয়
if quick_prompt and quick_prompt != "Select...":
    prompt_text_final = quick_prompt
else:
    prompt_text_final = None

if prompt_data:
    if isinstance(prompt_data, dict):
        user_txt = prompt_data.get("text", "")
        uploaded_files = prompt_data.get("files",[])
    else:
        user_txt = getattr(prompt_data, "text", str(prompt_data))
        uploaded_files = getattr(prompt_data, "files",[])

    if not user_txt: user_txt = "Please analyze the attached files."
    prompt_text_final = user_txt

if prompt_text_final:
    new_msg = {"role": "user", "content": prompt_text_final, "images":[], "dataframes":[]}
    
    # ফাইল পড়া
    if prompt_data:
        for f in getattr(prompt_data, "files", []) if not isinstance(prompt_data, dict) else prompt_data.get("files",[]):
            try:
                if f.name.lower().endswith(('png', 'jpg', 'jpeg')): new_msg["images"].append(Image.open(f))
                elif f.name.lower().endswith('csv'): new_msg["dataframes"].append(pd.read_csv(f))
            except Exception as e: st.error(f"Error loading file: {e}")
            
    # ওয়েব সার্চ লজিক
    if use_web_search:
        with st.spinner("🌐 Searching the Web..."):
            web_info = web_search(prompt_text_final)
            new_msg["content"] = f"User Query: {prompt_text_final}\n\n[Live Web Data for context]: {web_info}"

    st.session_state.messages.append(new_msg)
    
    if st.session_state.logged_in:
        safe_msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        db["chats"][st.session_state.username] = safe_msgs
        save_db(db)
        
    st.rerun()

# ==========================================
# ৭. এআই প্রসেসিং এবং এপিআই ভ্যালিডেটর
# ==========================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_msg = st.session_state.messages[-1]
    
    # এপিআই ভ্যালিডেটর (ভুল কী দিলে ক্র্যাশ করবে না)
    current_key = get_key(provider.split(" ")[0].upper())
    if not current_key or "আপনার_" in current_key:
        st.warning(f"⚠️ {provider} API Key is missing! Please enter a valid API Key in the Settings -> 'Secure API Keys' section.")
        st.stop()

    with st.chat_message("assistant"):
        res_box = st.empty()
        full_res = ""
        
        try:
            if last_msg.get("images"):
                gemini_key = get_key("GEMINI")
                if not gemini_key or "আপনার_" in gemini_key:
                    st.warning("⚠️ Image processing requires a valid Gemini API Key!")
                    st.stop()
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
                    msgs =[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
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
                    payload = {"model": model_name, "messages": [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]}
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
            st.error(f"⚠️ Error with {provider} Engine: {e}")

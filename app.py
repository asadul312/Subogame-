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

# ==========================================
# ১. পেজ ডিজাইন (বিনা এররের লেআউট)
# ==========================================
st.set_page_config(page_title="NEXUS AI OS", page_icon="🌌", layout="wide")

st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at top right, #0b0f19, #000000); color: #e2e8f0; }
    
    /* ৩ডি চ্যাট বাবল */
    [data-testid="stChatMessage"] {
        background: rgba(16, 24, 39, 0.6) !important;
        backdrop-filter: blur(15px) !important;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
        border-radius: 16px !important;
        padding: 20px !important;
    }
    
    /* টাইটেল ডিজাইন */
    .nexus-title {
        font-size: 3rem; font-weight: bold; text-align: center;
        background: linear-gradient(to right, #38bdf8, #c084fc);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ২. ডাটাবেস এবং লগইন সিস্টেম
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

# সেশন সেটআপ
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = "Guest"
if "api_keys" not in st.session_state: st.session_state.api_keys = {"GROQ": "", "GEMINI": "", "OPENROUTER": ""}
if "messages" not in st.session_state: st.session_state.messages =[]

# ==========================================
# ৩. সাইডবার সেটিংস
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
            st.rerun()

    st.divider()
    # মডেল অপশন
    provider = st.selectbox("AI Engine", ["Groq", "Gemini", "OpenRouter"])
    if provider == "Groq": model_name = st.selectbox("Model",["llama-3.3-70b-versatile", "qwen-2.5-coder-32b"])
    elif provider == "Gemini": model_name = st.selectbox("Model",["gemini-1.5-pro", "gemini-1.5-flash"])
    else: model_name = st.selectbox("Model",["openai/gpt-4o", "deepseek/deepseek-r1"])

    # এপিআই কী বসানোর জায়গা
    with st.expander("🔑 Your API Keys"):
        st.session_state.api_keys["GROQ"] = st.text_input("Groq Key", type="password", value=st.session_state.api_keys["GROQ"])
        st.session_state.api_keys["GEMINI"] = st.text_input("Gemini Key", type="password", value=st.session_state.api_keys["GEMINI"])
        st.session_state.api_keys["OPENROUTER"] = st.text_input("OpenRouter Key", type="password", value=st.session_state.api_keys["OPENROUTER"])

# এপিআই ফাংশন
def get_key(prov):
    k = st.session_state.api_keys.get(prov, "")
    # আপনি চাইলে এখানে আপনার আসল কীগুলো হার্ডকোড করে দিতে পারেন
    fallbacks = {"GROQ": "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", "GEMINI": "আপনার_GEMINI_API_KEY", "OPENROUTER": "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"}
    return k if k else fallbacks.get(prov)

# ==========================================
# ৪. চ্যাট হিস্ট্রি এবং কোড রানার
# ==========================================
st.markdown("<div class='nexus-title'>NEXUS AI OS</div>", unsafe_allow_html=True)
st.write("---")

def run_code(code):
    old_out = sys.stdout
    sys.stdout = io.StringIO()
    try: exec(code, globals()); return sys.stdout.getvalue()
    except Exception as e: return str(e)
    finally: sys.stdout = old_out

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("images"):
            for img in msg["images"]: st.image(img, width=250)
        if msg.get("dataframes"):
            for df in msg["dataframes"]: st.dataframe(df.head())
        
        # পাইথন কোড রান করার বাটন
        if msg["role"] == "assistant" and "```python" in msg["content"]:
            code_str = msg["content"].split("```python")[1].split("```")[0]
            if st.button("▶️ Run Code", key=f"run_{i}"):
                st.code(run_code(code_str), language="bash")

# ==========================================
# ৫. ন্যাটিভ ইনপুট বার (ChatGPT স্টাইল)
# ==========================================
# এই নতুন ফিচারের কারণে ফাইল আপলোড আইকন চ্যাটবক্সের ভেতরেই থাকবে!
prompt_data = st.chat_input("Ask anything or attach a file...", accept_file="multiple")

if prompt_data:
    user_txt = prompt_data.text if prompt_data.text else "Please analyze the attached files."
    new_msg = {"role": "user", "content": user_txt, "images":[], "dataframes":[]}
    
    if hasattr(prompt_data, "files") and prompt_data.files:
        for f in prompt_data.files:
            if f.name.lower().endswith(('png', 'jpg', 'jpeg')):
                new_msg["images"].append(Image.open(f))
            elif f.name.lower().endswith('csv'):
                new_msg["dataframes"].append(pd.read_csv(f))
                
    st.session_state.messages.append(new_msg)
    
    # চ্যাট সেভ করা (শুধু টেক্সট)
    if st.session_state.logged_in:
        safe_msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        db["chats"][st.session_state.username] = safe_msgs
        save_db(db)
        
    st.rerun()

# ==========================================
# ৬. এআই লজিক ও প্রসেসিং
# ==========================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_msg = st.session_state.messages[-1]
    with st.chat_message("assistant"):
        res_box = st.empty()
        full_res = ""
        
        try:
            # যদি ছবি থাকে (Gemini Vision)
            if last_msg.get("images"):
                genai.configure(api_key=get_key("GEMINI"))
                model = genai.GenerativeModel("gemini-1.5-pro")
                response = model.generate_content([last_msg["content"]] + last_msg["images"])
                full_res = response.text
                res_box.markdown(full_res)
                
            # Groq
            elif provider == "Groq":
                client = Groq(api_key=get_key("GROQ"))
                msgs =[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                stream = client.chat.completions.create(model=model_name, messages=msgs, stream=True)
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        full_res += chunk.choices[0].delta.content
                        res_box.markdown(full_res + "▌")
                        
            # Gemini (Text)
            elif provider == "Gemini":
                genai.configure(api_key=get_key("GEMINI"))
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(last_msg["content"], stream=True)
                for chunk in response:
                    full_res += chunk.text
                    res_box.markdown(full_res + "▌")
                    
            # OpenRouter
            elif provider == "OpenRouter":
                headers = {"Authorization": f"Bearer {get_key('OPENROUTER')}", "Content-Type": "application/json"}
                payload = {"model": model_name, "messages": [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]}
                res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                full_res = res.json()['choices'][0]['message']['content']
                res_box.markdown(full_res)
                
            res_box.markdown(full_res)
            st.session_state.messages.append({"role": "assistant", "content": full_res})
            
            # এআই এর উত্তর সেভ করা
            if st.session_state.logged_in:
                safe_msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                db["chats"][st.session_state.username] = safe_msgs
                save_db(db)
                
        except Exception as e:
            st.error(f"Error! Make sure your API keys are correct. Details: {e}")

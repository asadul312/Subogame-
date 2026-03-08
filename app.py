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
import base64

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
# ২. মডেল ক্যাটালগ (এখানেই সব মডেলের তথ্য থাকবে)
# ==========================================
MODEL_CATALOG = {
    "Groq: Llama 3.3 70B": {"id": "llama-3.3-70b-versatile", "provider": "groq", "vision": False},
    "Groq: Qwen 2.5 Coder": {"id": "qwen-2.5-coder-32b", "provider": "groq", "vision": False},
    "Gemini: 1.5 Pro 👁️": {"id": "gemini-1.5-pro", "provider": "gemini", "vision": True},
    "Gemini: 1.5 Flash 👁️": {"id": "gemini-1.5-flash", "provider": "gemini", "vision": True},
    "OpenRouter: GPT-4o 👁️": {"id": "openai/gpt-4o", "provider": "openrouter", "vision": True},
    "OpenRouter: Claude 3.5 Sonnet 👁️": {"id": "anthropic/claude-3.5-sonnet", "provider": "openrouter", "vision": True},
    "OpenRouter: DeepSeek R1": {"id": "deepseek/deepseek-r1", "provider": "openrouter", "vision": False}
}

# ==========================================
# ৩. ডাটাবেস এবং সেশন 
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
# ৪. সাইডবার সেটিংস
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: #38bdf8;'>⚙️ Settings</h2>", unsafe_allow_html=True)
    
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
    
    selected_model_name = st.selectbox("Select AI Model", list(MODEL_CATALOG.keys()))
    
    with st.expander("🔑 Secure API Keys"):
        st.session_state.api_keys["GROQ"] = st.text_input("Groq Key", type="password", value=st.session_state.api_keys["GROQ"])
        st.session_state.api_keys["GEMINI"] = st.text_input("Gemini Key", type="password", value=st.session_state.api_keys["GEMINI"])
        st.session_state.api_keys["OPENROUTER"] = st.text_input("OpenRouter Key", type="password", value=st.session_state.api_keys["OPENROUTER"])

def get_key(prov):
    user_key = st.session_state.api_keys.get(prov.upper())
    if user_key: return user_key
    
    hardcoded_keys = {
        "GROQ": "", # আপনার Groq কী এখানে দিন
        "GEMINI": "", # আপনার Gemini কী এখানে দিন
        "OPENROUTER": "" # আপনার OpenRouter কী এখানে দিন
    }
    return hardcoded_keys.get(prov.upper())

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
        if "images" in msg and msg["images"]:
            # বেস৬৪ স্ট্রিং থেকে ছবি দেখানো
            try:
                img_data = base64.b64decode(msg["images"][0].split(",")[1])
                st.image(Image.open(io.BytesIO(img_data)), width=200)
            except: pass # পুরানো ফরম্যাটের জন্য
        
        if msg["role"] == "assistant" and "```python" in msg["content"]:
            # ... (Code runner remains the same)
            code_blocks = msg["content"].split("```python")[1:]
            for idx, block in enumerate(code_blocks):
                code_str = block.split("```").strip()
                btn_key = f"run_btn_{i}_{idx}"
                col1, col2, _ = st.columns([0.15, 0.25, 0.6])
                if col1.button("▶️ Run Code", key=btn_key):
                    st.session_state.code_outputs[btn_key] = run_code(code_str)
                if col2.download_button("📥 Download .py", data=code_str, file_name=f"script_{i}_{idx}.py", mime="text/plain", key=f"dl_{i}_{idx}"):
                    pass
                if btn_key in st.session_state.code_outputs:
                    st.code(st.session_state.code_outputs[btn_key], language="bash")

# ==========================================
# ৬. মাল্টি-মোডাল ইনপুট প্রসেসিং
# ==========================================
def image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode()}"

prompt_data = st.chat_input("Ask anything or attach a file...", accept_file="multiple")

if prompt_data:
    user_txt = getattr(prompt_data, "text", str(prompt_data))
    uploaded_files = getattr(prompt_data, "files",[])

    if not user_txt and uploaded_files: 
        user_txt = "Please analyze the attached files."
    
    new_msg = {"role": "user", "content": user_txt, "images":[]} # বেস৬৪ স্ট্রিং সেভ হবে
    
    if uploaded_files:
        for f in uploaded_files:
            if f.name.lower().endswith(('png', 'jpg', 'jpeg')):
                img = Image.open(f)
                new_msg["images"].append(image_to_base64(img))

    st.session_state.messages.append(new_msg)
    
    if st.session_state.logged_in:
        db["chats"][st.session_state.username] = st.session_state.messages
        save_db(db)
        
    st.rerun()

# ==========================================
# ৭. আল্টিমেট এআই রেসপন্স লজিক
# ==========================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_msg = st.session_state.messages[-1]
    
    model_info = MODEL_CATALOG[selected_model_name]
    
    # অটো-সুইচ লজিক
    if last_msg["images"] and not model_info["vision"]:
        st.info(f"'{selected_model_name}' can't process images. Auto-switching to Gemini 1.5 Flash for this request.")
        model_info = MODEL_CATALOG["Gemini: 1.5 Flash 👁️"]
        
    current_key = get_key(model_info["provider"])

    if not current_key:
        with st.chat_message("assistant"):
            st.error(f"⚠️ API Key for {model_info['provider'].upper()} is missing!")
    else:
        with st.chat_message("assistant"):
            res_box = st.empty()
            full_res = ""
            
            try:
                # --- মাল্টি-মোডাল Gemini লজিক ---
                if model_info["provider"] == "gemini" and last_msg["images"]:
                    genai.configure(api_key=current_key)
                    model = genai.GenerativeModel(model_info["id"])
                    img_parts = [Image.open(io.BytesIO(base64.b64decode(img.split(",")))) for img in last_msg["images"]]
                    payload = [last_msg["content"]] + img_parts
                    response = model.generate_content(payload, stream=True)
                    for chunk in response:
                        full_res += chunk.text
                        res_box.markdown(full_res + "▌")

                # --- মাল্টি-মোডাল OpenRouter লজিক ---
                elif model_info["provider"] == "openrouter" and last_msg["images"]:
                    headers = {"Authorization": f"Bearer {current_key}"}
                    content_parts = [{"type": "text", "text": last_msg["content"]}]
                    for img_b64 in last_msg["images"]:
                        content_parts.append({"type": "image_url", "image_url": {"url": img_b64}})
                    
                    payload = {
                        "model": model_info["id"], 
                        "messages": [{"role": "user", "content": content_parts}]
                    }
                    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                    res.raise_for_status()
                    full_res = res.json()['choices']['message']['content']
                    res_box.markdown(full_res)

                # --- টেক্সট-অনলি মডেল লজিক ---
                else:
                    if model_info["provider"] == "groq":
                        client = Groq(api_key=current_key)
                        msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                        stream = client.chat.completions.create(model=model_info["id"], messages=msgs, stream=True)
                        for chunk in stream:
                            if chunk.choices.delta.content:
                                full_res += chunk.choices.delta.content
                                res_box.markdown(full_res + "▌")

                    elif model_info["provider"] == "gemini":
                        genai.configure(api_key=current_key)
                        model = genai.GenerativeModel(model_info["id"])
                        response = model.generate_content(last_msg["content"], stream=True)
                        for chunk in response:
                            full_res += chunk.text
                            res_box.markdown(full_res + "▌")
                            
                    elif model_info["provider"] == "openrouter":
                        headers = {"Authorization": f"Bearer {current_key}"}
                        payload = {"model": model_info["id"], "messages": [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]}
                        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                        res.raise_for_status()
                        full_res = res.json()['choices']['message']['content']
                        res_box.markdown(full_res)
                        
                res_box.markdown(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
                
                if st.session_state.logged_in:
                    db["chats"][st.session_state.username] = st.session_state.messages
                    save_db(db)
                    
            except Exception as e:
                st.error(f"⚠️ API Error for {model_info['id']}: {e}")

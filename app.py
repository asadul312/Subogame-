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

# ==========================================
# ১. পেজ ডিজাইন (Premium 3D Look)
# ==========================================
st.set_page_config(page_title="NEXUS VISION AI PRO", page_icon="👁️", layout="wide")

st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at center, #0b0f19, #000000); color: #e2e8f0; }
    
    /* কম্প্যাক্ট ৩ডি চ্যাট বাবল */
    [data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.04) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
        border-radius: 15px !important;
        padding: 12px 18px !important;
        margin-bottom: 12px !important;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.3);
    }
    
    /* টাইটেল ডিজাইন */
    .nexus-title {
        font-size: 2.8rem; font-weight: 800; text-align: center;
        background: linear-gradient(to right, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 10px; filter: drop-shadow(0 0 10px rgba(56, 189, 248, 0.3));
    }
    
    /* ইনপুট বার নিচের দিকে ফিক্সড */
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ২. অলরাউন্ডার মডেল ক্যাটালগ (Working IDs)
# ==========================================
MODEL_CATALOG = {
    "Gemini: 1.5 Pro 👁️": {"id": "gemini-1.5-pro", "provider": "gemini"},
    "Anthropic: Claude 3.5 Sonnet 👁️": {"id": "claude-3-5-sonnet-20240620", "provider": "anthropic"},
    "Groq: Llama 3.2 Vision (Fast) 👁️": {"id": "llama-3.2-11b-vision-preview", "provider": "groq"},
}

# ==========================================
# ৩. ডাটাবেস ও সিকিউরিটি
# ==========================================
DB_FILE = "nexus_v4_db.json"
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
if "code_outputs" not in st.session_state: st.session_state.code_outputs = {}

# ==========================================
# ৪. সাইডবার কন্ট্রোল প্যানেল
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: #38bdf8;'>⚙️ System Settings</h2>", unsafe_allow_html=True)
    
    if not st.session_state.logged_in:
        auth_mode = st.radio("Access",["Login", "Register"], horizontal=True)
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.button(auth_mode, use_container_width=True):
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
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = "Guest"
            st.session_state.messages =[]
            st.rerun()

    st.divider()
    selected_model_name = st.selectbox("Select Vision Model", list(MODEL_CATALOG.keys()))
    
    with st.expander("🔑 Secure API Keys"):
        st.session_state.api_keys["GROQ"] = st.text_input("Groq Key", type="password", value=st.session_state.api_keys["GROQ"])
        st.session_state.api_keys["GEMINI"] = st.text_input("Gemini Key", type="password", value=st.session_state.api_keys["GEMINI"])
        st.session_state.api_keys["ANTHROPIC"] = st.text_input("Anthropic Key", type="password", value=st.session_state.api_keys["ANTHROPIC"])

# এপিআই কী রিট্রিভাল
def get_key(prov):
    user_key = st.session_state.api_keys.get(prov.upper())
    if user_key: return user_key
    
    # 💡 আপনার এপিআই কীগুলো এখানে পেস্ট করুন 💡
    hardcoded_keys = {
        "GROQ": "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",
        "GEMINI": "আপনার_GEMINI_কী",
        "ANTHROPIC": "আপনার_ANTHROPIC_কী"
    }
    return hardcoded_keys.get(prov.upper())

# ==========================================
# ৫. ইউটিলিটি ফাংশন (Code Runner & Image)
# ==========================================
def run_code(code):
    old_out = sys.stdout
    sys.stdout = io.StringIO()
    try: 
        exec(code, globals())
        output = sys.stdout.getvalue()
        return output if output.strip() else "✅ Code executed (No print output)."
    except Exception as e: return f"❌ Error: {str(e)}"
    finally: sys.stdout = old_out

def img_to_b64(img):
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()

# ==========================================
# ৬. চ্যাট হিস্ট্রি প্রদর্শন
# ==========================================
st.markdown("<div class='nexus-title'>NEXUS VISION AI</div>", unsafe_allow_html=True)

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "images_b64" in msg:
            for b64 in msg["images_b64"]:
                st.image(Image.open(io.BytesIO(base64.b64decode(b64))), width=250)
        
        # কোড রানার বাটন
        if msg["role"] == "assistant" and "```python" in msg["content"]:
            code_str = msg["content"].split("```python")[1].split("```")[0].strip()
            if st.button(f"▶️ Run Snippet {i}", key=f"run_{i}"):
                st.code(run_code(code_str), language="bash")

# ==========================================
# ৭. ইনপুট প্রসেসিং (Bug-Free Input)
# ==========================================
input_data = st.chat_input("Ask or attach image/file...", accept_file="multiple")

if input_data:
    # স্ক্রিনশটের এরর ফিক্স করার জন্য এই অংশটি:
    user_txt = getattr(input_data, "text", "")
    files = getattr(input_data, "files", [])
    
    if not user_txt and files: user_txt = "Analyze the attached file."
    
    new_msg = {"role": "user", "content": user_txt, "images_b64": []}
    
    if files:
        for f in files:
            if f.name.lower().endswith(('png', 'jpg', 'jpeg')):
                img = Image.open(f)
                new_msg["images_b64"].append(img_to_b64(img))
    
    st.session_state.messages.append(new_msg)
    if st.session_state.logged_in:
        db["chats"][st.session_state.username] = st.session_state.messages
        save_db(db)
    st.rerun()

# ==========================================
# ৮. আল্টিমেট এআই লজিক (Vision Optimized)
# ==========================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_msg = st.session_state.messages[-1]
    model_info = MODEL_CATALOG[selected_model_name]
    current_key = get_key(model_info["provider"])

    if not current_key or "আপনার_" in current_key:
        with st.chat_message("assistant"): st.error(f"⚠️ {model_info['provider'].upper()} Key is missing!")
    else:
        with st.chat_message("assistant"):
            res_box = st.empty()
            full_res = ""
            
            try:
                # --- GEMINI লজিক ---
                if model_info["provider"] == "gemini":
                    genai.configure(api_key=current_key)
                    model = genai.GenerativeModel(model_info["id"])
                    payload = [last_msg["content"]]
                    if last_msg["images_b64"]:
                        payload += [Image.open(io.BytesIO(base64.b64decode(b))) for b in last_msg["images_b64"]]
                    response = model.generate_content(payload, stream=True)
                    for chunk in response:
                        full_res += chunk.text
                        res_box.markdown(full_res + "▌")

                # --- ANTHROPIC লজিক ---
                elif model_info["provider"] == "anthropic":
                    client = Anthropic(api_key=current_key)
                    content = [{"type": "text", "text": last_msg["content"]}]
                    for b64 in last_msg["images_b64"]:
                        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}})
                    
                    with client.messages.stream(model=model_info["id"], max_tokens=2048, messages=[{"role": "user", "content": content}]) as stream:
                        for chunk in stream.text_stream:
                            full_res += chunk
                            res_box.markdown(full_res + "▌")

                # --- GROQ VISION (LLAMA 3.2) লজিক ---
                elif model_info["provider"] == "groq":
                    client = Groq(api_key=current_key)
                    content = [{"type": "text", "text": last_msg["content"]}]
                    for b64 in last_msg["images_b64"]:
                        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
                    
                    stream = client.chat.completions.create(
                        model=model_info["id"],
                        messages=[{"role": "user", "content": content}],
                        stream=True
                    )
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            full_res += chunk.choices[0].delta.content
                            res_box.markdown(full_res + "▌")
                
                res_box.markdown(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
                if st.session_state.logged_in:
                    db["chats"][st.session_state.username] = st.session_state.messages
                    save_db(db)

            except Exception as e:
                st.error(f"❌ System Error: {str(e)}")

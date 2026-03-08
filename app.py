import streamlit as st
import google.generativeai as genai
from groq import Groq
from anthropic import Anthropic
from PIL import Image
import base64
import io
import json
import os
import hashlib

st.set_page_config(page_title="NEXUS VISION AI", page_icon="👁️", layout="wide")

# ---------- STYLE ----------
st.markdown("""
<style>

.stApp{
background: radial-gradient(circle,#0b0f19,#000);
color:white;
}

[data-testid="stChatMessage"]{
background: rgba(255,255,255,0.05);
border-radius:15px;
padding:10px;
border:1px solid rgba(56,189,248,0.3);
}

.title{
font-size:40px;
font-weight:800;
text-align:center;
background:linear-gradient(90deg,#38bdf8,#818cf8,#c084fc);
-webkit-background-clip:text;
-webkit-text-fill-color:transparent;
}

</style>
""",unsafe_allow_html=True)

st.markdown('<div class="title">NEXUS VISION AI</div>',unsafe_allow_html=True)

# ---------- FIXED API KEYS ----------
DEFAULT_KEYS = {
"GEMINI":"PASTE_GEMINI_KEY",
"GROQ":"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",
"ANTHROPIC":"PASTE_CLAUDE_KEY"
}

# ---------- DATABASE ----------
DB="nexus_db.json"

def load_db():
    if os.path.exists(DB):
        with open(DB) as f:
            return json.load(f)
    return {"users":{},"chats":{}}

def save_db(data):
    with open(DB,"w") as f:
        json.dump(data,f)

def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

db=load_db()

# ---------- SESSION ----------
if "login" not in st.session_state:
    st.session_state.login=False

if "messages" not in st.session_state:
    st.session_state.messages=[]

if "api" not in st.session_state:
    st.session_state.api={
    "GEMINI":"",
    "GROQ":"",
    "ANTHROPIC":""
    }

# ---------- API GETTER ----------
def get_api(provider):

    sidebar_key = st.session_state.api.get(provider)

    if sidebar_key:
        return sidebar_key

    return DEFAULT_KEYS.get(provider)

# ---------- SIDEBAR ----------
with st.sidebar:

    st.title("⚙️ Settings")

    auth=st.radio("Access",["Login","Register"])

    u=st.text_input("Username")
    p=st.text_input("Password",type="password")

    if st.button(auth):

        if auth=="Register":

            db["users"][u]=hash_pass(p)
            db["chats"][u]=[]
            save_db(db)

            st.success("Account created")

        else:

            if db["users"].get(u)==hash_pass(p):

                st.session_state.login=True
                st.session_state.user=u
                st.session_state.messages=db["chats"].get(u,[])

                st.rerun()

    st.divider()

    MODEL=st.selectbox("Model",[
    "Gemini 1.5 Pro",
    "Claude 3.5 Sonnet",
    "Groq Vision"
    ])

    st.session_state.api["GEMINI"]=st.text_input("Gemini API",type="password")
    st.session_state.api["ANTHROPIC"]=st.text_input("Claude API",type="password")
    st.session_state.api["GROQ"]=st.text_input("Groq API",type="password")

# ---------- SHOW CHAT ----------
for m in st.session_state.messages:

    with st.chat_message(m["role"]):

        st.markdown(m["content"])

        if "imgs" in m:

            for img in m["imgs"]:
                st.image(img,width=250)

# ---------- INPUT ----------
text=st.chat_input("Ask anything...")

files=st.file_uploader("Upload Image",type=["png","jpg","jpeg"],accept_multiple_files=True)

if text or files:

    imgs=[]

    if files:

        for f in files:
            imgs.append(Image.open(f))

    user_msg={
    "role":"user",
    "content":text,
    "imgs":imgs
    }

    st.session_state.messages.append(user_msg)

    with st.chat_message("user"):

        st.markdown(text)

        for i in imgs:
            st.image(i,width=250)

    response=""

    with st.chat_message("assistant"):

        box=st.empty()

        try:

            # GEMINI
            if MODEL=="Gemini 1.5 Pro":

                genai.configure(api_key=get_api("GEMINI"))

                model=genai.GenerativeModel("gemini-1.5-pro")

                res=model.generate_content([text]+imgs)

                response=res.text

            # CLAUDE
            elif MODEL=="Claude 3.5 Sonnet":

                client=Anthropic(api_key=get_api("ANTHROPIC"))

                content=[{"type":"text","text":text}]

                for img in imgs:

                    buf=io.BytesIO()
                    img.save(buf,format="JPEG")

                    content.append({
                    "type":"image",
                    "source":{
                    "type":"base64",
                    "media_type":"image/jpeg",
                    "data":base64.b64encode(buf.getvalue()).decode()
                    }})

                res=client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1024,
                messages=[{"role":"user","content":content}]
                )

                response=res.content[0].text

            # GROQ
            elif MODEL=="Groq Vision":

                client=Groq(api_key=get_api("GROQ"))

                res=client.chat.completions.create(
                model="llava-v1.5-7b-4096-preview",
                messages=[{"role":"user","content":text}]
                )

                response=res.choices[0].message.content

            box.markdown(response)

        except Exception as e:

            st.error(e)

    st.session_state.messages.append({
    "role":"assistant",
    "content":response
    })

    if st.session_state.login:

        db["chats"][st.session_state.user]=st.session_state.messages
        save_db(db)

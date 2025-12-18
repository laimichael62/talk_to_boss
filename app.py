import streamlit as st
from openai import OpenAI
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

# --- 頁面設定 ---
st.set_page_config(page_title="Small Talk Pro", layout="wide")
st.title("🌐 Small Talk Master: 對話訓練 (Pro)")

# --- 連接資料庫 (Google Sheets) ---
# 這是建立連接的關鍵指令
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 登入系統 (User Identification) ---
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# 如果還沒登入，顯示登入畫面
if not st.session_state.user_id:
    with st.form("login_form"):
        st.header("🔐 用戶登入")
        username = st.text_input("請輸入你的代號 (Username):", placeholder="例如: Neo_01")
        submitted = st.form_submit_button("進入系統")
        
        if submitted and username:
            st.session_state.user_id = username
            st.rerun()
    st.stop() # 停止執行下面的代碼，直到登入

# --- 登入後顯示用戶資訊 ---
st.sidebar.write(f"👤 當前用戶: **{st.session_state.user_id}**")
if st.sidebar.button("登出"):
    st.session_state.user_id = None
    st.session_state.messages = []
    st.rerun()

# --- 角色矩陣 ---
personas = {
    "商業 - Gordon (華爾街巨鱷)": {
        "role": "Gordon",
        "desc": "掌控百億基金的風險投資人。性格冷酷，只看回報率。",
        "style": "Direct, impatient, money-focused. Hates small talk. Speaks in short, punchy sentences.",
        "win_condition": "用戶能在一分鐘內講清楚商業模式，並提供令人震驚的增長數據。"
    },
    "科技 - Elon (矽谷鋼鐵人)": {
        "role": "Elon",
        "desc": "火星殖民計畫發起人，物理學信徒。",
        "style": "Erratic, visionary, physics-first thinking, loves memes and engineering.",
        "win_condition": "用戶提出一個基於'第一性原理'的工程解決方案，解決人類級別的難題。"
    },
    "科學 - Marie (諾貝爾獎得主)": {
        "role": "Marie",
        "desc": "頂尖生物化學家，對偽科學深惡痛絕。",
        "style": "Rigorous, skeptical, data-driven. Constantly asks 'What is your source?'.",
        "win_condition": "用戶展現對科學方法的深刻理解，或提供獨特的實驗數據。"
    },
    "體育 - Kobe (黑曼巴)": {
        "role": "Kobe",
        "desc": "退役傳奇球星，擁有極致的勝負欲。",
        "style": "Intense, philosophical, obsessed with discipline and hard work.",
        "win_condition": "用戶展現出極致的專注力、紀律性，或對勝利的偏執渴望。"
    },
    "AI - Sam (AGI 開發者)": {
        "role": "Sam",
        "desc": "通用人工智慧架構師，思考維度超越常人。",
        "style": "Calm, futuristic, talks about alignment and scaling laws. Slightly detached.",
        "win_condition": "用戶對 AI 的倫理或未來發展有獨特且深刻的見解，而非人云亦云。"
    },
    "藝術 - Pablo (瘋狂畫家)": {
        "role": "Pablo",
        "desc": "顛覆傳統的抽象派大師，討厭平庸。",
        "style": "Emotional, abstract, provocative. Hates 'logic' and 'structure'.",
        "win_condition": "用戶能用非邏輯的方式表達一種強烈的情感或美學觀點。"
    },
    "電影 - Nolan (時間魔術師)": {
        "role": "Nolan",
        "desc": "執著於非線性敘事的金牌導演。",
        "style": "Intellectual, focused on structure, time, and visual storytelling.",
        "win_condition": "用戶提出一個結構精妙、燒腦且具備情感深度的故事核心。"
    },
    "音樂 - Taylor (流行天后)": {
        "role": "Taylor",
        "desc": "透過歌詞掌控全球情感的創作歌手。",
        "style": "Expressive, storytelling-focused, values authenticity and heartbreak.",
        "win_condition": "用戶分享一個真實、脆弱且具備共鳴的個人故事。"
    },
    "遊戲 - Hideo (金牌製作人)": {
        "role": "Hideo",
        "desc": "將遊戲視為電影藝術的傳奇製作人。",
        "style": "Visionary, mysterious, obsessed with 'connection' (strands).",
        "win_condition": "用戶理解遊戲不僅是娛樂，而是一種連接人與人的媒介。"
    }
}


# --- 側邊欄：設定 ---
with st.sidebar:
    st.header("🎯 選擇目標")
    selected_key = st.selectbox("選擇行業領袖：", list(personas.keys()))
    current_persona = personas[selected_key]
    
    # API Key 邏輯
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("✅ 系統連線正常")
    else:
        api_key = st.text_input("輸入 DeepSeek Key", type="password")

# --- 資料庫邏輯：讀取歷史訊息 ---
# 我們定義一個函數來從 Google Sheets 撈資料
def load_history(username, persona_role):
    try:
        # 讀取整個表格
        df = conn.read(worksheet="Sheet1", ttl=0) # ttl=0 代表不快取，每次都拿最新的
        # 篩選出當前用戶和當前角色的對話
        if not df.empty:
            user_history = df[
                (df["username"] == username) & 
                (df["target_persona"] == persona_role)
            ]
            return user_history
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# --- 資料庫邏輯：寫入訊息 ---
def save_message(username, persona_role, role, content):
    try:
        # 讀取現有資料
        df = conn.read(worksheet="Sheet1", ttl=0)
        
        # 建立新的一行
        new_row = pd.DataFrame([{
            "username": username,
            "target_persona": persona_role,
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        
        # 合併並寫回
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Sheet1", data=updated_df)
        
    except Exception as e:
        st.error(f"存檔失敗: {e}")

# --- 初始化 Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    
    # 剛登入時，嘗試從資料庫載入舊記錄
    history_df = load_history(st.session_state.user_id, current_persona["role"])
    if not history_df.empty:
        for index, row in history_df.iterrows():
            st.session_state.messages.append({"role": row["role"], "content": row["content"]})

# 如果切換了角色，我們要重新載入該角色的歷史記錄
if "last_persona" not in st.session_state:
    st.session_state.last_persona = current_persona["role"]

if st.session_state.last_persona != current_persona["role"]:
    st.session_state.messages = [] # 清空畫面
    # 載入新角色的歷史
    history_df = load_history(st.session_state.user_id, current_persona["role"])
    if not history_df.empty:
        for index, row in history_df.iterrows():
            st.session_state.messages.append({"role": row["role"], "content": row["content"]})
    st.session_state.last_persona = current_persona["role"]


# --- System Prompt ---
system_prompt = f"""
You are '{current_persona['role']}'. {current_persona['style']}
Mission: Test the user. Win Condition: {current_persona['win_condition']}
Protocol:
1. Stay in character.
2. Keep responses < 60 words.
3. Output "|||" then critique in Traditional Chinese.
"""

# --- 對話介面 ---
if api_key:
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    # 顯示訊息
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 輸入
    if prompt := st.chat_input(f"回應 {current_persona['role']}..."):
        # 1. 顯示並保存用戶訊息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # 寫入資料庫 (User)
        save_message(st.session_state.user_id, current_persona["role"], "user", prompt)

        # 2. 呼叫 AI
        api_msgs = [{"role": "system", "content": system_prompt}] + st.session_state.messages
        
        try:
            response = client.chat.completions.create(
                model="deepseek-chat", messages=api_msgs, stream=False, temperature=1.3
            )
            full_res = response.choices[0].message.content
            
            if "|||" in full_res:
                reply, feedback = full_res.split("|||", 1)
            else:
                reply, feedback = full_res, ""

            # 3. 顯示並保存 AI 訊息
            st.session_state.messages.append({"role": "assistant", "content": reply.strip()})
            with st.chat_message("assistant"):
                st.markdown(reply.strip())
            
            # 寫入資料庫 (AI)
            save_message(st.session_state.user_id, current_persona["role"], "assistant", reply.strip())

            if feedback:
                with st.expander("教練分析"):
                    st.info(feedback.strip())

        except Exception as e:
            st.error(f"錯誤: {e}")
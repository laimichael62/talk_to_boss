import streamlit as st
from openai import OpenAI
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import edge_tts
import asyncio
import tempfile
import os

# --- 頁面設定 ---
st.set_page_config(page_title="Network Master Pro (Voice)", layout="wide")
st.title("🎙️ Network Master: 沉浸式商業模擬")

# --- 連接資料庫 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("資料庫連線失敗，請檢查 secrets.toml")
    conn = None

# --- 角色矩陣 (含語音設定) ---
# voice_id 參考: en-US-BrianNeural (男), en-US-AriaNeural (女)
# --- 角色矩陣 (含語音設定) ---
personas = {
    "商業 - Gordon (VC)": {
        "role": "Gordon",
        "desc": "華爾街巨鱷，冷酷直接。",
        "style": "Direct, impatient.",
        "win_condition": "清晰的商業模式。",
        "voice_id": "en-US-ChristopherNeural"  # <--- 必須有這行
    },
    "科技 - Elon (Tech CEO)": {
        "role": "Elon",
        "desc": "火星殖民者，思維跳躍。",
        "style": "Visionary, erratic.",
        "win_condition": "第一性原理。",
        "voice_id": "en-US-EricNeural"       # <--- 必須有這行
    },
    "科學 - Marie (科學家)": {
        "role": "Marie",
        "desc": "諾貝爾獎得主，嚴謹。",
        "style": "Skeptical, precise.",
        "win_condition": "科學數據。",
        "voice_id": "en-US-EmmaNeural"       # <--- 必須有這行
    },
    "體育 - Kobe (黑曼巴)": {
        "role": "Kobe",
        "desc": "傳奇球星，勝負欲極強。",
        "style": "Intense, philosophical.",
        "win_condition": "極致的專注力。",
        "voice_id": "en-US-BrianNeural"      # <--- 必須有這行
    },
    "AI - Sam (AGI 開發者)": {
        "role": "Sam",
        "desc": "AI 架構師，冷靜理性。",
        "style": "Calm, futuristic.",
        "win_condition": "獨特 AI 見解。",
        "voice_id": "en-US-RogerNeural"      # <--- 必須有這行
    },
    "藝術 - Pablo (畫家)": {
        "role": "Pablo",
        "desc": "抽象派大師，感性。",
        "style": "Abstract, emotional.",
        "win_condition": "獨特美學。",
        "voice_id": "en-US-GuyNeural"        # <--- 必須有這行
    },
    "電影 - Nolan (導演)": {
        "role": "Nolan",
        "desc": "時間魔術師，結構控。",
        "style": "Intellectual, complex.",
        "win_condition": "精妙的故事結構。",
        "voice_id": "en-US-ChristopherNeural" # <--- 必須有這行
    },
    "音樂 - Taylor (歌手)": {
        "role": "Taylor",
        "desc": "流行天后，情感豐富。",
        "style": "Expressive, storytelling.",
        "win_condition": "真實故事。",
        "voice_id": "en-US-JennyNeural"      # <--- 必須有這行
    },
    "遊戲 - Hideo (製作人)": {
        "role": "Hideo",
        "desc": "傳奇製作人，連結。",
        "style": "Visionary, mysterious.",
        "win_condition": "連結與共鳴。",
        "voice_id": "en-US-EricNeural"       # <--- 必須有這行
    }
}


# --- 側邊欄 ---
with st.sidebar:
    st.header("🎯 設定中心")
    selected_key = st.selectbox("選擇對話目標：", list(personas.keys()))
    current_persona = personas[selected_key]
    
    st.divider()
    
    # 這裡我們需要兩個 Key
    # 1. DeepSeek (負責大腦)
    if "DEEPSEEK_API_KEY" in st.secrets:
        deepseek_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("🧠 DeepSeek: 已連接")
    else:
        deepseek_key = st.text_input("DeepSeek Key", type="password")

    # 2. OpenAI (負責耳朵 - Whisper)
    # 如果你想用免費的 Edge-TTS (嘴巴) 不需要 Key
    # 但如果要語音轉文字，目前最穩的是 OpenAI Whisper
    if "OPENAI_API_KEY" in st.secrets:
        openai_key = st.secrets["OPENAI_API_KEY"]
        st.success("👂 Whisper: 已連接")
    else:
        openai_key = st.text_input("OpenAI Key (用於語音輸入)", type="password", help="如果你沒有 OpenAI Key，請使用文字輸入。")

    st.divider()
    if st.button("🗑️ 清除對話"):
        st.session_state.messages = []
        st.rerun()

# --- 功能函數：TTS (文字轉語音 - 免費版) ---
async def generate_audio(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def play_voice(text, voice_id):
    try:
        # 建立暫存檔
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_filename = fp.name
        
        # 執行異步生成
        asyncio.run(generate_audio(text, voice_id, temp_filename))
        
        # 播放
        st.audio(temp_filename, format="audio/mp3", autoplay=True)
        
        # 清理 (非必要，Streamlit 會自動清理部分)
    except Exception as e:
        st.error(f"語音生成失敗: {e}")

# --- 功能函數：STT (語音轉文字 - 需 OpenAI Key) ---
def transcribe_audio(audio_file, api_key):
    try:
        client = OpenAI(api_key=api_key) # 使用 OpenAI 官方服務
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file
        )
        return transcription.text
    except Exception as e:
        st.error(f"聽寫失敗 (請確認有 OpenAI Key): {e}")
        return None

# --- 資料庫函數 (簡化版) ---
def save_to_db(role, content):
    if conn:
        try:
            # 這裡簡單處理，實際商業專案需更嚴謹的結構
            data = pd.DataFrame([{"timestamp": datetime.datetime.now(), "role": role, "content": content}])
            # 由於 streamlit-gsheets 寫入較慢，這裡僅做示範，建議實際使用時用 append 模式
            # conn.update(worksheet="Sheet1", data=data) 
            pass 
        except:
            pass

# --- 初始化 (多角色記憶體管理) ---
# 我們用一個字典來存所有角色的對話，key是角色名，value是對話列表
if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}

# 確保當前角色的記憶體存在
if current_persona['role'] not in st.session_state.chat_history:
    st.session_state.chat_history[current_persona['role']] = []

# 將當前畫面的 messages 指向對應角色的記憶體
# 這樣我們操作 messages 時，其實就是在操作 st.session_state.chat_history[角色名]
st.session_state.messages = st.session_state.chat_history[current_persona['role']]

# --- System Prompt ---
system_prompt = f"""
You are '{current_persona['role']}'. {current_persona['style']}
Win Condition: {current_persona['win_condition']}
Protocol:
1. Stay in character 100%.
2. Keep responses < 50 words (Spoken style).
3. Output "|||" then critique in Traditional Chinese.
"""

# --- 核心邏輯 ---
if deepseek_key:
    # 1. 顯示歷史對話
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 2. 獲取用戶輸入 (文字 或 語音)
    user_input = None
    
    # A. 語音輸入區
    audio_value = st.audio_input("🎤 按下錄音 (需 OpenAI Key)")
    
    # B. 文字輸入區
    text_value = st.chat_input(f"回應 {current_persona['role']}...")

    # 處理輸入優先級
    if audio_value and openai_key:
        with st.spinner("正在聽寫..."):
            transcribed_text = transcribe_audio(audio_value, openai_key)
            if transcribed_text:
                user_input = transcribed_text
    elif text_value:
        user_input = text_value

    # 3. 處理對話
    if user_input:
        # 顯示用戶訊息
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # 呼叫 DeepSeek
        client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")
        api_msgs = [{"role": "system", "content": system_prompt}] + st.session_state.messages
        
        try:
            with st.spinner(f"{current_persona['role']} 正在思考..."):
                response = client.chat.completions.create(
                    model="deepseek-chat", messages=api_msgs, stream=False, temperature=1.3
                )
            
            full_res = response.choices[0].message.content
            if "|||" in full_res:
                reply, feedback = full_res.split("|||", 1)
            else:
                reply, feedback = full_res, ""

            # 顯示 AI 回覆
            st.session_state.messages.append({"role": "assistant", "content": reply.strip()})
            with st.chat_message("assistant"):
                st.markdown(reply.strip())
                # --- 關鍵：觸發語音播放 ---
                play_voice(reply.strip(), current_persona['voice_id'])

            # 顯示教練分析
            if feedback:
                with st.sidebar:
                    st.info(f"**教練分析：**\n{feedback.strip()}")

        except Exception as e:
            st.error(f"連線錯誤: {e}")

else:
    st.warning("請先輸入 DeepSeek Key")
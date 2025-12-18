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
talk to boss

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

# --- 初始化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

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
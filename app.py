import streamlit as st
from openai import OpenAI

# --- 頁面設定 ---
st.set_page_config(page_title="Small Talk Coach", layout="wide")

st.title("🐲 Small Talk Dojo")
st.caption("商業談判 | 閒聊技巧 | 即時反饋教練")

# --- 側邊欄：設定 ---
with st.sidebar:
    st.header("⚙️ 設定")
    
    # 邏輯：優先使用 Streamlit Secrets (雲端保險箱) 的 Key
    # 如果雲端沒有 Key (比如你在本地跑)，才讓用戶輸入
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("✅ 已啟用自動授權 (Demo Mode)")
    else:
        api_key = st.text_input("輸入 DeepSeek API Key", type="password")

    st.divider()
    st.header("🧐 教練反饋")
    feedback_placeholder = st.empty()
    feedback_placeholder.info("等待對話開始...")

# --- 初始化記憶體 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 系統提示詞 ---
system_prompt = """
You are 'Gordon', a seasoned Venture Capitalist.
Your style: Direct, professional, slightly impatient but helpful.
Task: Engage in small talk for networking.
Constraints:
1. Keep responses under 50 words.
2. CRITICAL: After your response, output exactly "|||" followed by a critique in Traditional Chinese.
3. Critique Format: [Score 0-10] - [One sentence critique] - [One sentence improvement]
"""

# --- 核心邏輯 ---
if api_key:
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("向 Gordon 介紹你自己..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            history_for_api = [{"role": "system", "content": system_prompt}]
            for msg in st.session_state.messages:
                history_for_api.append(msg)

            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=history_for_api,
                    stream=False,
                    temperature=1.3
                )
                
                full_response = response.choices[0].message.content

                if "|||" in full_response:
                    reply_part, feedback_part = full_response.split("|||", 1)
                else:
                    reply_part = full_response
                    feedback_part = "無法生成反饋。"

                st.session_state.messages.append({"role": "assistant", "content": reply_part.strip()})
                with st.chat_message("assistant"):
                    st.markdown(reply_part.strip())

                with st.sidebar:
                    feedback_placeholder.success(f"**教練分析：**\n\n{feedback_part.strip()}")

            except Exception as e:
                st.error(f"連線錯誤: {e}")

    except Exception as e:
        st.error("API Key 格式錯誤。")
else:
    st.warning("請輸入 API Key 以啟動系統。")
import google.generativeai as genai

# 把你的 API Key 貼在下面的引號裡
MY_API_KEY = "AIzaSyBf-pNfRPSYRnqDgoL8ZQtzVSae5npPaXA " 

genai.configure(api_key=MY_API_KEY)

print("正在查詢可用模型...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
    print("\n查詢完成！")
except Exception as e:
    print(f"錯誤發生: {e}")
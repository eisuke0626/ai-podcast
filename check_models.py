import os
from dotenv import load_dotenv
from google import genai

# .envファイルからAPIキーを読み込む
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=gemini_key)

print("🔍 利用可能なモデル一覧を取得中...\n")

try:
    for model in client.models.list():
        # 名前の中に 'flash' が含まれるモデルだけを絞り込んで表示
        # if 'flash' in model.name:
        if 'pro' in model.name:
            print(f"・ {model.name}")
    print("\n✅ 取得完了！")
except Exception as e:
    print(f"エラーが発生しました: {e}")
import os
import feedparser
from dotenv import load_dotenv
from google import genai  # 追加: Gemini APIのライブラリ

# --- 準備 ---
# .envファイルから環境変数を読み込む
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")
google_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# --- タスク2-1: ニュース取得モジュール ---
def get_latest_news(limit=5):
    """
    指定したRSSフィードから最新のニュースを取得し、テキストとして返す関数
    """
    print("📰 ニュースを取得中...")
    rss_url = "https://news.yahoo.co.jp/rss/topics/top-picks.xml"
    feed = feedparser.parse(rss_url)

    news_text = "【本日のニュース素材】\n"
    for i, entry in enumerate(feed.entries[:limit]):
        title = entry.title
        news_text += f"・{title}\n"

    return news_text

# --- タスク2-2: Gemini AI要約モジュール ---
def generate_podcast_script(news_text):
    """
    ニュース素材をGeminiに渡し、ポッドキャスト風の台本を生成する関数
    """
    print("🤖 Geminiがラジオ台本を執筆中...")
    
    # Geminiクライアントの初期化
    client = genai.Client(api_key=gemini_key)
    
    # AIへの細かい指示書き（プロンプト）
    system_instruction = """
    あなたはプロのラジオパーソナリティです。
    提供されたニュース素材をもとに、リスナーが朝の通勤中や作業の準備中に心地よく聴けるポッドキャストの台本を作成してください。
    
    【条件】
    ・冒頭は「おはようございます！」のような自然な挨拶から始めること。
    ・ニュースはただ読み上げるのではなく、ニュースキャスターのように分かりやすく自然な話し言葉で要約すること。
    ・読むと約1〜2分程度になる長さ（400〜600文字程度）にまとめること。
    ・最後は、今日一日を応援するような前向きなメッセージで締めくくること。
    ・※音声合成エンジンに読み上げさせるため、感情を表す記号（！や？）は使っても良いですが、読み上げられない特殊な記号は避けること。
    """
    
    # 指示書きとニュース素材を結合
    prompt = f"{system_instruction}\n\n{news_text}"
    
    # Gemini APIを呼び出してテキストを生成（高速・軽量なflashモデルを使用）
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    
    return response.text

# --- メイン処理（テスト実行用） ---
if __name__ == "__main__":
    # 1. ニュースの取得
    raw_news = get_latest_news(limit=5)
    
    # 2. ラジオ台本の作成
    script_text = generate_podcast_script(raw_news)
    
    print("\n=== 完成したラジオ台本 ===")
    print(script_text)
    print("============================\n")
    print("✅ 台本の作成が完了しました！")
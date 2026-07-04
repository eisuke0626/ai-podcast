import os
import datetime
from email.utils import formatdate
from dotenv import load_dotenv
from google import genai
from google.genai import types  # 追加: Google検索グラウンディング（ツール）の設定に必要
from google.cloud import texttospeech

# --- 準備 ---
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")

# --- タスク2-1: Gemini Proによるニュース検索・生成モジュール ---
def get_latest_news_via_gemini(query="SAP", limit=5):
    """
    Gemini ProモデルのGoogle検索グラウンディング機能を使用し、
    指定されたキーワードに関する最新ニュースをウェブから検索・抽出する
    """
    print(f"🤖 Gemini Proが「{query}」に関する最新ニュースをWeb検索中...")
    client = genai.Client(api_key=gemini_key)
    
    prompt = f"""
    最新の「{query}」に関するニュース、技術アップデート、プレスリリース、または重要な動向を検索してください。
    検索結果から、特に重要と思われるトピックを最大{limit}個選び、客観的な事実のみを箇流書きで簡潔にまとめてください。
    ※出力はニュースの事実（箇条書き）のみとし、挨拶や「検索した結果〜」のような前置き、まとめの言葉は一切含めないでください。
    """
    
    # 検索グラウンディングを有効にして、賢いProモデル(gemini-1.5-pro)で実行
    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}]  # ★ここでGoogle検索を連動させています
        )
    )
    
    return response.text

# --- タスク2-2: Gemini AI要約・台本作成モジュール ---
def generate_podcast_script(news_text, topic="SAP関連"):
    print("🤖 Gemini Flashがラジオ台本を執筆中...")
    client = genai.Client(api_key=gemini_key)
    
    today = datetime.datetime.now()
    date_str = f"{today.month}月{today.day}日"
    
    system_instruction = f"""
    あなたはプロのラジオパーソナリティです。
    提供されたニュース素材をもとに、リスナーが朝の通勤中や作業の準備中に心地よく聴けるポッドキャストの台本を作成してください。
    
    【条件】
    ・冒頭は必ず「{date_str}のニュース（{topic}）をお伝えします。」という一文のみで始めること。他の挨拶や自己紹介は絶対に含めないこと。
    ・ニュースはただ読み上げるのではなく、ニュースキャスターのように分かりやすく自然な話し言葉で要約すること。
    ・読むと約1〜2分程度になる長さ（400〜600文字程度）にまとめること。
    ・【重要】音声合成エンジンが記号を誤読してしまうため、**や#などのマークダウン記法、および特殊記号は一切使用しないこと。すべてプレーンな日本語テキストで記述すること。
    ・最後は長々としたポエムのような文章は避け、「それでは、今日も一日頑張りましょう。いってらっしゃい！」のような、短くシンプルな一言のみで締めくくること。
    """
    
    prompt = f"{system_instruction}\n\n{news_text}"
    
    # 台本の作成は高速でコストパフォーマンスの良いFlashモデル(gemini-2.5-flash)で実行
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    return response.text

# --- タスク2-3: 音声化(Google TTS)モジュール ---
def synthesize_audio(script_text, output_filename="podcast.mp3"):
    print("🎙️ ラジオパーソナリティが音声を収録中（Google TTS）...")
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=script_text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="ja-JP",
        name="ja-JP-Neural2-B" 
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    with open(output_filename, "wb") as out:
        out.write(response.audio_content)
    print(f"🎵 音声ファイル【{output_filename}】の生成が完了しました！")

# --- タスク2-4: RSSフィード生成モジュール ---
def generate_rss(topic="SAP関連", mp3_filename="podcast.mp3"):
    print("📻 RSSフィード(feed.xml)を生成中...")
    
    # ★ここをご自身の情報に書き換えてください★
    github_username = "eisuke0626" 
    repo_name = "ai-podcast"
    
    base_url = f"https://{github_username}.github.io/{repo_name}"
    today_str = datetime.datetime.now().strftime("%Y年%m月%d日")
    pub_date = formatdate(localtime=False) 
    
    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>あなた専用 AIニュース</title>
    <link>{base_url}</link>
    <description>Geminiが毎朝お届けする最新ニュースの要約ポッドキャストです。</description>
    <language>ja</language>
    <item>
      <title>{today_str}のニュース（{topic}）</title>
      <enclosure url="{base_url}/{mp3_filename}" type="audio/mpeg" length="1000000"/>
      <pubDate>{pub_date}</pubDate>
      <guid>{base_url}/{mp3_filename}?t={datetime.datetime.now().timestamp()}</guid>
    </item>
  </channel>
</rss>"""

    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(rss_content)
    print("✅ RSSフィードの生成が完了しました！")

# --- メイン処理 ---
if __name__ == "__main__":
    # ==========================================
    # ⚙️ 設定エリア：今後テーマや検索対象を変える時はここを変更するだけ
    # ==========================================
    TARGET_TOPIC_KEYWORD = "SAP"   # Gemini ProにWeb検索させるキーワード
    DISPLAY_TOPIC_NAME   = "SAP関連" # 番組タイトルや台本で読み上げるテーマ名
    # ==========================================

    # 1. Gemini Pro (Google Search連動) で最新ニュース素材を生成
    raw_news = get_latest_news_via_gemini(query=TARGET_TOPIC_KEYWORD, limit=5)
    
    # 2. Gemini Flashでラジオ台本に整形
    script_text = generate_podcast_script(raw_news, topic=DISPLAY_TOPIC_NAME)
    
    # 3. 音声化および配信設定
    synthesize_audio(script_text, output_filename="podcast.mp3")
    generate_rss(topic=DISPLAY_TOPIC_NAME, mp3_filename="podcast.mp3")
    
    print("🎉 すべての処理が完了しました！")
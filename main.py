import os
import datetime
from email.utils import formatdate
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.cloud import texttospeech

# --- 準備 ---
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")

# --- タスク2-1: Gemini Proによるニュース検索・生成モジュール ---
def get_latest_news_via_gemini(query="SAP", limit=5):
    print(f"🤖 Gemini Proが「{query}」に関する最新ニュースをWeb検索中...")
    client = genai.Client(api_key=gemini_key)
    
    prompt = f"""
    最新の「{query}」に関するニュース、技術アップデート、プレスリリース、または重要な動向を検索してください。
    検索結果から、特に重要と思われるトピックを最大{limit}個選び、客観的な事実のみを箇条書きで簡潔にまとめてください。
    ※出力はニュースの事実（箇条書き）のみとし、挨拶や「検索した結果〜」のような前置き、まとめの言葉は一切含めないでください。
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}]
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
    ・最後は長々としたポエムのような文章は避け、「それでは、今日も一日頑張りましょう。いってらっしゃい！」のような, 短くシンプルな一言のみで締めくくること。
    """
    
    prompt = f"{system_instruction}\n\n{news_text}"
    
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

# --- タスク2-4: RSSフィード生成モジュール（完全自動化版） ---
def generate_rss(script_text, topic="SAP関連", mp3_filename="podcast.mp3", image_filename="podcast-art.png"):
    """ RSSに番組画像と、各エピソードの説明欄（台本テキスト）を追加する """
    print("📻 RSSフィード(feed.xml)を生成中...")
    
    # GitHub Actionsまたは.envから「ユーザー名/リポジトリ名」の形（例: owner/repo）で自動取得
    repo_env = os.getenv("GITHUB_REPOSITORY")
    
    if repo_env and "/" in repo_env:
        # スラッシュで分割して自動的に変数に代入
        github_username, repo_name = repo_env.split("/")
    else:
        # 万が一取得できなかった場合のセーフティ
        print("⚠️ GITHUB_REPOSITORY環境変数が見つかりません。")
        github_username = "default_user"
        repo_name = "default_repo"
        
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
    <itunes:image href="{base_url}/{image_filename}"/>
    <item>
      <title>{today_str}のニュース（{topic}）</title>
      <enclosure url="{base_url}/{mp3_filename}" type="audio/mpeg" length="1000000"/>
      <pubDate>{pub_date}</pubDate>
      <guid>{base_url}/{mp3_filename}?t={datetime.datetime.now().timestamp()}</guid>
      <description><![CDATA[{script_text}]]></description>
      <itunes:summary><![CDATA[{script_text}]]></itunes:summary>
    </item>
  </channel>
</rss>"""

    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(rss_content)
    print(f"✅ RSSフィードの生成が完了しました！ (配信元: {base_url})")

# --- メイン処理 ---
if __name__ == "__main__":
    # ==========================================
    # ⚙️ 設定エリア
    # ==========================================
    TARGET_TOPIC_KEYWORD = "SAP"   
    DISPLAY_TOPIC_NAME   = "SAP関連" 
    IMAGE_FILE_NAME      = "podcast-art.png" # チャンネル画像用のファイル名（固定）
    # ==========================================

    raw_news = get_latest_news_via_gemini(query=TARGET_TOPIC_KEYWORD, limit=5)
    script_text = generate_podcast_script(raw_news, topic=DISPLAY_TOPIC_NAME)
    synthesize_audio(script_text, output_filename="podcast.mp3")
    
    # 引数に script_text と IMAGE_FILE_NAME を渡すように変更
    generate_rss(script_text=script_text, topic=DISPLAY_TOPIC_NAME, mp3_filename="podcast.mp3", image_filename=IMAGE_FILE_NAME)
    
    print("🎉 すべての処理が完了しました！")
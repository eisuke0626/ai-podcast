import os
import datetime
import json  # 追加: 履歴データを管理するため
import glob  # 追加: フォルダ内の古いMP3ファイルを探すため
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
    
    # 修正点: 冒頭の指定から（{topic}）を削除しました
    system_instruction = f"""
    あなたはプロのラジオパーソナリティです。
    提供されたニュース素材をもとに、リスナーが朝の通勤中や作業の準備中に心地よく聴けるポッドキャストの台本を作成してください。
    
    【条件】
    ・冒頭は必ず「{date_str}のニュースをお伝えします。」という一文のみで始めること。テーマ名（{topic}など）や他の挨拶、自己紹介は絶対に含めないこと。
    ・ニュースはただ読み上げるのではなく、ニュースキャスターのように分かりやすく自然な話し言葉で要約すること。
    ・読むと約1〜2分程度になる長さ（400〜600文字程度）にまとめること。
    ・【重要】音声合成エンジンが記号を誤読してしまうため、**や#などのマークダウン記法、および特殊記号は一切使用しないこと。すべてプレーンな日本語テキストで記述すること。
    ・最後は長々としたポエムのような文章は避け、「それでは、今日も一日頑張りましょう。いってらっしゃい！」のような、短くシンプルな一言のみで締めくくること。
    """
    
    prompt = f"{system_instruction}\n\n{news_text}"
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    return response.text

# --- タスク2-3: 音声化(Google TTS)モジュール ---
def synthesize_audio(script_text, output_filepath):
    print(f"🎙️ ラジオパーソナリティが音声を収録中（Google TTS）: {output_filepath}")
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
    with open(output_filepath, "wb") as out:
        out.write(response.audio_content)
    print("🎵 音声ファイルの生成が完了しました！")

# --- タスク2-4: アーカイブ管理＆RSSフィード生成モジュール ---
def manage_episodes_and_rss(script_text, topic, new_mp3_filename, image_filename="podcast-art.png"):
    print("📻 エピソード履歴の更新とRSSフィード(feed.xml)を生成中...")
    
    repo_env = os.getenv("GITHUB_REPOSITORY")
    if repo_env and "/" in repo_env:
        github_username, repo_name = repo_env.split("/")
    else:
        github_username = "default_user"
        repo_name = "default_repo"
        
    base_url = f"https://{github_username}.github.io/{repo_name}"
    
    now = datetime.datetime.now()
    today_str = now.strftime("%Y年%m月%d日")
    pub_date = formatdate(localtime=False) 
    
    # 1. 過去のエピソード履歴（JSON）を読み込む
    history_file = "public/episodes.json"
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            episodes = json.load(f)
            # ★追加: 過去の蓄積データからも「（SAP関連）」や「(SAP)」を一括で消去してクレンジングします
            for ep in episodes:
                ep["title"] = ep["title"].replace(f"（{topic}）", "").replace(f"({topic})", "").replace("（SAP関連）", "").replace("(SAP)", "").strip()
    else:
        episodes = []
        
    # 2. 新しいエピソードをリストの先頭に追加
    # 修正点: タイトル文字列から（{topic}）を除外しました
    new_episode = {
        "title": f"{today_str}のニュース",
        "mp3_filename": new_mp3_filename,
        "pub_date": pub_date,
        "guid": f"{base_url}/{new_mp3_filename}?t={int(now.timestamp())}",
        "script_text": script_text
    }
    episodes.insert(0, new_episode)
    
    # 3. リストを最新30件に絞り込む（ここで古いデータが弾かれる）
    episodes = episodes[:30]
    
    # 4. 更新した履歴をJSONに保存する
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, indent=2)
        
    # 5. publicフォルダ内をチェックし、履歴に残っていない古いMP3ファイルを物理削除する
    allowed_mp3s = [ep["mp3_filename"] for ep in episodes]
    for mp3_path in glob.glob("public/podcast_*.mp3"):
        filename = os.path.basename(mp3_path)
        if filename not in allowed_mp3s:
            os.remove(mp3_path)
            print(f"🗑️ 容量節約のため、古いファイル {filename} を削除しました。")
            
    # 6. 最新の履歴データをもとに、RSSフィード（XML）を組み立てる
    items_xml = ""
    for ep in episodes:
        items_xml += f"""
    <item>
      <title>{ep['title']}</title>
      <enclosure url="{base_url}/{ep['mp3_filename']}" type="audio/mpeg" length="1000000"/>
      <pubDate>{ep['pub_date']}</pubDate>
      <guid>{ep['guid']}</guid>
      <description><![CDATA[{ep['script_text']}]]></description>
      <itunes:summary><![CDATA[{ep['script_text']}]]></itunes:summary>
    </item>"""

    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>あなた専用 AIニュース</title>
    <link>{base_url}</link>
    <description>Geminiが毎朝お届けする最新ニュースの要約ポッドキャストです。</description>
    <language>ja</language>
    <itunes:image href="{base_url}/{image_filename}"/>{items_xml}
  </channel>
</rss>"""

    with open("public/feed.xml", "w", encoding="utf-8") as f:
        f.write(rss_content)
    print(f"✅ RSSフィードの生成が完了しました！ (現在 {len(episodes)} 件のエピソードを配信中)")


# --- メイン処理 ---
if __name__ == "__main__":
    # ==========================================
    # ⚙️ 設定エリア
    # ==========================================
    TARGET_TOPIC_KEYWORD = "SAP"   
    DISPLAY_TOPIC_NAME   = "SAP関連" 
    IMAGE_FILE_NAME      = "podcast-art.png" 
    # ==========================================

    # 出力先となる「public」フォルダを作成
    os.makedirs("public", exist_ok=True)
    
    # 毎回上書きされないように、日付と時刻を入れた固有のファイル名を生成 (例: podcast_20260705_083000.mp3)
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    new_mp3_filename = f"podcast_{now_str}.mp3"
    output_filepath = f"public/{new_mp3_filename}"

    raw_news = get_latest_news_via_gemini(query=TARGET_TOPIC_KEYWORD, limit=5)
    script_text = generate_podcast_script(raw_news, topic=DISPLAY_TOPIC_NAME)
    
    # 音声の保存先を output_filepath に変更
    synthesize_audio(script_text, output_filepath=output_filepath)
    
    # アーカイブ管理とRSSの生成を実行
    manage_episodes_and_rss(script_text=script_text, topic=DISPLAY_TOPIC_NAME, new_mp3_filename=new_mp3_filename, image_filename=IMAGE_FILE_NAME)
    
    print("🎉 すべての処理が完了しました！")
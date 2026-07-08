import os
import datetime
import json
import glob
from email.utils import formatdate
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.cloud import texttospeech

# --- 準備 ---
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")

# ★追加: サーバーの場所に関わらず、常に日本時間(JST)を基準にするための設定
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')

# --- 【統合】Gemini Proによるニュース検索＆台本生成モジュール ---
def generate_podcast_script_via_pro(query="SAP", limit=5):
    print(f"🤖 Gemini Proが「{query}」の最新ニュースを検索し、ラジオ台本を執筆中...")
    client = genai.Client(api_key=gemini_key)
    
    prompt = f"""
    最新の「{query}」に関するニュース、技術アップデート、プレスリリース、または重要な動向を検索してください。
    検索結果から、特に重要と思われるトピックを最大{limit}個選んでください。
    特に、過去1週間の間に起こった出来事、ニュースを優先して選んでください。
    
    選んだニュースをもとに、プロのラジオパーソナリティがキャスターのように分かりやすく自然な話し言葉で解説する、ポッドキャストの「本編原稿」を作成してください。
    
    【原稿作成の条件】
    ・各トピックの【背景】【具体的な内容】【今後の影響や展望】を深く掘り下げ、聴き応えのある内容にすること。
    ・全体の長さは、読むと約3〜4分程度になるボリューム（1000〜1200文字程度）にしっかりと肉付けすること。
    ・【最重要】音声合成エンジンが記号を誤読するのを防ぐため、**や#などのマークダウン記法、および「・」や「-」などの箇条書き記号、特殊記号は一切使用しないこと。段落を分け、すべて滑らかな日本語の文章（プレーンテキスト）で記述すること。
    ・冒頭の挨拶（〇月〇日のニュースなど）や、終わりの挨拶（いってらっしゃいなど）は、システム側で自動挿入するため、原稿内には絶対に含めないこと。ニュースの本編のみを出力してください。
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}]
        )
    )
    return response.text

# --- タスク2-3: 音声化(Google TTS)モジュール ---
def synthesize_audio(script_text, output_filepath):
    print(f"🎙️ ラジオパーソナリティが音声を収録中（Google TTS）: {output_filepath}")
    client = texttospeech.TextToSpeechClient()
    
    max_chars = 1000
    sentences = script_text.split("。")
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if not sentence.strip():
            continue
        test_sentence = sentence + "。"
        if len(current_chunk) + len(test_sentence) > max_chars:
            chunks.append(current_chunk)
            current_chunk = test_sentence
        else:
            current_chunk += test_sentence
            
    if current_chunk:
        chunks.append(current_chunk)
        
    combined_audio_content = b""
    
    for idx, chunk in enumerate(chunks):
        print(f"  🔊 音声化処理中... パート {idx+1}/{len(chunks)} ({len(chunk)}文字)")
        synthesis_input = texttospeech.SynthesisInput(text=chunk)
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
        combined_audio_content += response.audio_content
        
    with open(output_filepath, "wb") as out:
        out.write(combined_audio_content)
    print("🎵 すべてのパートの統合および音声ファイルの生成が完了しました！")

# --- タスク2-4: アーカイブ管理＆RSSフィード生成モジュール ---
def manage_episodes_and_rss(script_text, new_mp3_filename, image_filename="podcast-art.png"):
    print("📻 エピソード履歴の更新とRSSフィード(feed.xml)を生成中...")
    
    repo_env = os.getenv("GITHUB_REPOSITORY")
    if repo_env and "/" in repo_env:
        github_username, repo_name = repo_env.split("/")
    else:
        github_username = "default_user"
        repo_name = "default_repo"
        
    base_url = f"https://{github_username}.github.io/{repo_name}"
    
    now = datetime.datetime.now(JST) # 日本時間を取得
    today_str = now.strftime("%Y年%m月%d日")
    pub_date = formatdate(localtime=False) 
    
    history_file = "public/episodes.json"
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            episodes = json.load(f)
    else:
        episodes = []
        
    new_episode = {
        "title": f"{today_str}のニュース",
        "mp3_filename": new_mp3_filename,
        "pub_date": pub_date,
        "guid": f"{base_url}/{new_mp3_filename}?t={int(now.timestamp())}",
        "script_text": script_text
    }
    episodes.insert(0, new_episode)
    
    episodes = episodes[:30]
    
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, indent=2)
        
    allowed_mp3s = [ep["mp3_filename"] for ep in episodes]
    for mp3_path in glob.glob("public/podcast_*.mp3"):
        filename = os.path.basename(mp3_path)
        if filename not in allowed_mp3s:
            os.remove(mp3_path)
            print(f"🗑️ 容量節約のため、古いファイル {filename} を削除しました。")
            
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
    IMAGE_FILE_NAME = "podcast-art.png" 

# 1. まずGitHub Actionsの手動入力（環境変数）があるかチェックする
    # ※ワークフロー側から「INPUT_MANUAL_TOPIC」という名前で値が渡ってきます
    manual_topic = os.getenv("INPUT_MANUAL_TOPIC", "auto")
    
    if manual_topic and manual_topic != "auto":
        # 手動でテーマが選ばれている場合は、曜日を無視してそれを使う
        TARGET_TOPIC_KEYWORD = manual_topic
        print(f"🎛️ GitHubからの手動指定による配信テーマ: {TARGET_TOPIC_KEYWORD}ニュース")
    else:
        # 通常の自動実行（または手動でautoが選ばれた）場合は、日本時間の曜日から決定する
        now_jst = datetime.datetime.now(JST)
        weekday = now_jst.weekday() # 0:月, 1:火, ...
        
        daily_topics = {
            0: "SAP関連",
            1: "コンサル業界関連",
            2: "AI関連",
            3: "海外IT業界関連",
            4: "日本国内IT業界関連",
            5: "ビジネスパーソンが知っておくべき最新の海外",
            6: "ビジネスパーソンが知っておくべき最新の日本国内"
        }
        TARGET_TOPIC_KEYWORD = daily_topics[weekday]
        print(f"📅 定期自動配信によるテーマ（{now_jst.strftime('%A')}）: {TARGET_TOPIC_KEYWORD}ニュース")

    os.makedirs("public", exist_ok=True)
    
    # ファイル名にも日本時間を適用
    now_str = now_jst.strftime("%Y%m%d_%H%M%S")
    new_mp3_filename = f"podcast_{now_str}.mp3"
    output_filepath = f"public/{new_mp3_filename}"

    # 1. 決定したテーマを渡してGemini Proで原稿作成
    body_text = generate_podcast_script_via_pro(query=TARGET_TOPIC_KEYWORD, limit=5)
    
    # 2. 定型文（挨拶など）を生成
    date_str = f"{now_jst.month}月{now_jst.day}日"
    
    # 音声の冒頭文（テーマ名はあえて入れず、日付のみでスッキリさせる仕様を維持）
    opening = f"{date_str}のニュースをお伝えします。\n\n"
    closing = "\n\nそれでは、今日も一日頑張りましょう。いってらっしゃい！"
    
    final_script_text = opening + body_text + closing

    # 音声合成とアーカイブ管理を実行
    synthesize_audio(final_script_text, output_filepath=output_filepath)
    manage_episodes_and_rss(script_text=final_script_text, new_mp3_filename=new_mp3_filename, image_filename=IMAGE_FILE_NAME)
    
    print("🎉 スマート化されたすべての処理が完了しました！")
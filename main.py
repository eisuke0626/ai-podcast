import os
import feedparser
import datetime  # 追加: 実行時の日付を自動取得するためのライブラリ
from dotenv import load_dotenv
from google import genai
from google.cloud import texttospeech  # 追加: Google Cloud TTSライブラリ

# --- 準備 ---
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")
# GOOGLE_APPLICATION_CREDENTIALSは、texttospeechライブラリが自動で読み込みます

# --- タスク2-1: ニュース取得モジュール ---
def get_latest_news(limit=5):
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
    
    client = genai.Client(api_key=gemini_key)
    
    # プログラムを実行した「今日の日付」を取得して文字列にする（例：7月5日）
    today = datetime.datetime.now()
    date_str = f"{today.month}月{today.day}日"
    
    # 冒頭の挨拶を、取得した日付を使った一文に完全に固定する
    system_instruction = f"""
    あなたはプロのラジオパーソナリティです。
    提供されたニュース素材をもとに、リスナーが朝の通勤中や作業の準備中に心地よく聴けるポッドキャストの台本を作成してください。
    
    【条件】
    ・冒頭は必ず「{date_str}のニュースをお伝えします。」という一文のみで始めること。他の挨拶や自己紹介（〇〇など）は絶対に含めないこと。
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
def synthesize_audio(script_text, output_filename="podcast.mp3"):
    """
    テキストをGoogle Cloud TTSで音声化し、MP3として保存する関数
    """
    print("🎙️ ラジオパーソナリティが音声を収録中（Google TTS）...")
    
    # TTSクライアントの初期化
    client = texttospeech.TextToSpeechClient()

    # 読み上げるテキストをセット
    synthesis_input = texttospeech.SynthesisInput(text=script_text)

    # 音声の言語と声質の設定（日本語、自然で聴きやすいNeural2モデルの男性声）
    voice = texttospeech.VoiceSelectionParams(
        language_code="ja-JP",
        name="ja-JP-Neural2-B" 
    )

    # 出力する音声の形式（MP3）
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    # APIを呼び出して音声を生成
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # 生成された音声データをMP3ファイルとして書き込み
    with open(output_filename, "wb") as out:
        out.write(response.audio_content)
        
    print(f"🎵 音声ファイル【{output_filename}】の生成が完了しました！")

# --- メイン処理 ---
if __name__ == "__main__":
    # 1. ニュースの取得
    raw_news = get_latest_news(limit=5)
    
    # 2. ラジオ台本の作成
    script_text = generate_podcast_script(raw_news)
    print("\n=== 完成したラジオ台本 ===")
    print(script_text)
    print("============================\n")
    
    # 3. 台本の音声化
    synthesize_audio(script_text, output_filename="podcast.mp3")
    
    print("✅ すべての処理が完了しました！")
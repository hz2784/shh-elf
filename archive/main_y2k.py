from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv
import hashlib
from pathlib import Path

# 加载环境变量
load_dotenv()

app = FastAPI(title="Shh-elf", description="A Book Talk Tool to Spark Reading Through Curiosity and Connection")

# 创建必要目录
Path("audio").mkdir(exist_ok=True)
Path("static").mkdir(exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/audio", StaticFiles(directory="audio"), name="audio")

# API密钥
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# 数据模型
class BookRecommendation(BaseModel):
    book_title: str
    recipient_name: str
    relationship: str = "朋友"
    recipient_interests: str = ""
    tone: str = "友好热情"
    language: str = "中文"

# GPT生成推荐文本 (保持不变)
def generate_recommendation_text(book_title: str, recipient_name: str, relationship: str, interests: str, tone: str, language: str) -> str:
    if language == "English":
        prompt = f"""
Create a 1-minute personalized book recommendation for {recipient_name} (my {relationship}).

Book: {book_title}
Recipient's interests: {interests}
Tone: {tone}

Requirements:
1. Speak directly to {recipient_name}, use "you"
2. Mention why this book is perfect for them
3. Include 1-2 specific highlights or plot points
4. Natural, conversational language like friends talking
5. Keep it 30-50 words
6. End with a call to action encouraging them to read it

Generate the recommendation:
"""
        system_msg = "You are an enthusiastic book lover who excels at personalized book recommendations."
    else:  # 中文
        prompt = f"""
为{recipient_name}（我的{relationship}）创建一个1分钟的个性化书籍推荐。

书籍：{book_title}
接收人兴趣：{interests}
语调：{tone}

要求：
1. 直接对{recipient_name}说话，使用"你"
2. 提及为什么这本书特别适合他/她
3. 包含1-2个具体的吸引点或情节亮点
4. 语言自然、口语化，像朋友间的推荐
5. 长度控制在50-80字
6. 结尾要有行动召唤，鼓励去读这本书

请生成推荐文本：
"""
        system_msg = "你是一个热情的书友，擅长个性化推荐书籍。"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300,
        "temperature": 0.7
    }
    
    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", 
                               headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GPT API错误: {str(e)}")

# ElevenLabs文本转语音 (保持不变)
def text_to_speech(text: str, filename: str, language: str) -> str:
    voice_id = "9BWtsMINqrJLrRacOk9x"  # Aria
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    print(f"=== 语音生成调试信息 ===")
    print(f"Text: {text}")
    print(f"Filename: {filename}")
        
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"Response status: {response.status_code}")
        response.raise_for_status()
        
        audio_path = f"audio/{filename}.mp3"
        with open(audio_path, "wb") as f:
            f.write(response.content)
        
        return audio_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音生成错误: {str(e)}")

# 主页 - 品牌风格设计
@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Shh-elf: A Story's About to Begin</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="Shh-elf helps students rediscover the joy of reading through bite-sized, relatable book talks and personalized recommendations.">
        <link href="https://fonts.googleapis.com/css2?family=Cooper+BT:wght@400;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            :root {
                --cream: #f5f1e8;
                --sunshine: #ffd700;
                --purple: #8b3a5c;
                --soft-pink: #e89cc5;
                --warm-blue: #7bb3f0;
                --mint: #98d8c8;
                --orange: #ff9b5a;
                --text-dark: #2c2c2c;
                --text-light: #6b6b6b;
            }
            
            body {
                font-family: 'Inter', sans-serif;
                background: var(--cream);
                color: var(--text-dark);
                line-height: 1.6;
                overflow-x: hidden;
            }
            
            /* Header */
            .header {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 1rem 2rem;
                position: fixed;
                top: 0;
                width: 100%;
                z-index: 100;
                border-bottom: 1px solid rgba(139, 58, 92, 0.1);
            }
            
            .nav {
                max-width: 1200px;
                margin: 0 auto;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .logo {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-family: 'Cooper BT', serif;
                font-size: 1.5rem;
                font-weight: 700;
                color: var(--purple);
                text-decoration: none;
            }
            
            .logo-visual {
                width: 50px;
                height: 50px;
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .brand-illustration {
                width: 100%;
                height: auto;
                background: linear-gradient(135deg, var(--cream) 0%, rgba(255, 215, 0, 0.1) 100%);
                border-radius: 50%;
                padding: 8px;
                position: relative;
            }
            
            /* SVG-style brand elements */
            .sun-character {
                width: 32px;
                height: 32px;
                background: var(--sunshine);
                border-radius: 50%;
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .sun-character::before {
                content: '';
                position: absolute;
                width: 40px;
                height: 40px;
                background: radial-gradient(circle, transparent 50%, var(--sunshine) 50%, var(--sunshine) 55%, transparent 55%);
                border-radius: 50%;
            }
            
            .sun-character::after {
                content: ':)';
                font-size: 12px;
                color: var(--purple);
                font-weight: bold;
            }
            
            /* Hero Section */
            .hero {
                min-height: 100vh;
                display: flex;
                align-items: center;
                background: var(--cream);
                position: relative;
                overflow: hidden;
                padding-top: 80px;
            }
            
            .hero::before {
                content: '';
                position: absolute;
                top: 15%;
                right: -5%;
                width: 200px;
                height: 200px;
                background: var(--sunshine);
                border-radius: 50%;
                opacity: 0.2;
                animation: float 6s ease-in-out infinite;
            }
            
            .hero::after {
                content: '';
                position: absolute;
                bottom: 15%;
                left: -5%;
                width: 150px;
                height: 150px;
                background: var(--soft-pink);
                border-radius: 50%;
                opacity: 0.3;
                animation: float 8s ease-in-out infinite reverse;
            }
            
            @keyframes float {
                0%, 100% { transform: translateY(0px) scale(1); }
                50% { transform: translateY(-20px) scale(1.1); }
            }
            
            .hero-content {
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 4rem;
                align-items: center;
                position: relative;
                z-index: 2;
            }
            
            .hero-text h1 {
                font-family: 'Cooper BT', serif;
                font-size: clamp(2.5rem, 5vw, 4rem);
                color: var(--purple);
                margin-bottom: 1rem;
                line-height: 1.2;
            }
            
            .tagline {
                font-size: 1.5rem;
                color: var(--text-light);
                margin-bottom: 2rem;
                font-style: italic;
            }
            
            .hero-description {
                font-size: 1.2rem;
                margin-bottom: 2.5rem;
                color: var(--text-dark);
            }
            
            .cta-button {
                background: linear-gradient(135deg, var(--sunshine), var(--soft-pink));
                color: var(--text-dark);
                padding: 1rem 2.5rem;
                border: none;
                border-radius: 50px;
                font-size: 1.1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3);
                text-decoration: none;
                display: inline-block;
            }
            
            .cta-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(255, 215, 0, 0.4);
            }
            
            .hero-visual {
                position: relative;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            
            .main-illustration {
                width: 100%;
                max-width: 450px;
                height: 450px;
                position: relative;
                background: var(--cream);
                border-radius: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
            }
            
            /* Recreate your brand illustration */
            .brand-scene {
                position: relative;
                width: 350px;
                height: 350px;
            }
            
            .character {
                position: absolute;
                bottom: 80px;
                left: 50%;
                transform: translateX(-50%);
                width: 120px;
                height: 140px;
                background: var(--purple);
                border-radius: 60px 60px 20px 20px;
            }
            
            .character-arms {
                position: absolute;
                top: 40px;
                left: -20px;
                right: -20px;
                height: 80px;
            }
            
            .arm-left, .arm-right {
                position: absolute;
                width: 40px;
                height: 80px;
                background: var(--purple);
                border-radius: 20px;
                animation: gentle-wave 3s ease-in-out infinite;
            }
            
            .arm-left {
                left: 0;
                transform: rotate(-30deg);
                transform-origin: top center;
            }
            
            .arm-right {
                right: 0;
                transform: rotate(30deg);
                transform-origin: top center;
            }
            
            @keyframes gentle-wave {
                0%, 100% { transform: rotate(-30deg); }
                50% { transform: rotate(-45deg); }
            }
            
            .sun-element {
                position: absolute;
                top: 50px;
                left: 50%;
                transform: translateX(-50%);
                width: 80px;
                height: 80px;
                background: var(--sunshine);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .sun-face {
                font-size: 24px;
                color: var(--purple);
            }
            
            .sun-rays {
                position: absolute;
                top: -10px;
                left: -10px;
                right: -10px;
                bottom: -10px;
            }
            
            .ray {
                position: absolute;
                width: 3px;
                height: 20px;
                background: var(--orange);
                border-radius: 2px;
            }
            
            .ray:nth-child(1) { top: 0; left: 50%; transform: translateX(-50%); }
            .ray:nth-child(2) { top: 7px; right: 7px; transform: rotate(45deg); }
            .ray:nth-child(3) { top: 50%; right: 0; transform: translateY(-50%) rotate(90deg); }
            .ray:nth-child(4) { bottom: 7px; right: 7px; transform: rotate(135deg); }
            .ray:nth-child(5) { bottom: 0; left: 50%; transform: translateX(-50%) rotate(180deg); }
            .ray:nth-child(6) { bottom: 7px; left: 7px; transform: rotate(225deg); }
            .ray:nth-child(7) { top: 50%; left: 0; transform: translateY(-50%) rotate(270deg); }
            .ray:nth-child(8) { top: 7px; left: 7px; transform: rotate(315deg); }
            
            .rainbow {
                position: absolute;
                top: 70px;
                right: 40px;
                width: 100px;
                height: 50px;
                border-radius: 100px 100px 0 0;
                border: 8px solid transparent;
                border-top: 3px solid var(--soft-pink);
                border-right: 3px solid var(--sunshine);
                border-left: 3px solid var(--warm-blue);
            }
            
            .rainbow::after {
                content: '';
                position: absolute;
                top: -6px;
                left: -6px;
                right: -6px;
                height: 30px;
                border-radius: 100px 100px 0 0;
                border-top: 2px solid var(--mint);
            }
            
            .sparkles {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
            }
            
            .sparkle {
                position: absolute;
                color: var(--purple);
                font-size: 16px;
                animation: twinkle 2s ease-in-out infinite;
            }
            
            .sparkle:nth-child(1) { top: 20%; left: 15%; animation-delay: 0s; }
            .sparkle:nth-child(2) { top: 30%; right: 20%; animation-delay: 0.5s; }
            .sparkle:nth-child(3) { bottom: 25%; left: 25%; animation-delay: 1s; }
            .sparkle:nth-child(4) { bottom: 35%; right: 15%; animation-delay: 1.5s; }
            .sparkle:nth-child(5) { top: 15%; left: 70%; animation-delay: 0.3s; }
            .sparkle:nth-child(6) { bottom: 40%; left: 60%; animation-delay: 0.8s; }
            
            @keyframes twinkle {
                0%, 100% { opacity: 0.3; transform: scale(1); }
                50% { opacity: 1; transform: scale(1.2); }
            }
            
            /* Features Section */
            .features {
                padding: 6rem 2rem;
                background: white;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            
            .section-title {
                font-family: 'Cooper BT', serif;
                font-size: 2.5rem;
                text-align: center;
                color: var(--purple);
                margin-bottom: 3rem;
            }
            
            .features-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 3rem;
                margin-top: 4rem;
            }
            
            .feature-card {
                background: var(--cream);
                padding: 2.5rem;
                border-radius: 20px;
                text-align: center;
                border: 3px solid transparent;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            
            .feature-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, var(--sunshine), var(--soft-pink), var(--warm-blue));
            }
            
            .feature-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 30px rgba(139, 58, 92, 0.15);
            }
            
            .feature-icon {
                width: 80px;
                height: 80px;
                margin: 0 auto 1.5rem;
                background: linear-gradient(135deg, var(--sunshine), var(--soft-pink));
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 2rem;
                position: relative;
            }
            
            .feature-icon::after {
                content: '';
                position: absolute;
                width: 60%;
                height: 60%;
                background: white;
                border-radius: 50%;
            }
            
            .feature-title {
                font-family: 'Cooper BT', serif;
                font-size: 1.3rem;
                color: var(--purple);
                margin-bottom: 1rem;
            }
            
            /* Book Talk Playground Section */
            .playground {
                padding: 6rem 2rem;
                background: linear-gradient(135deg, var(--soft-pink) 0%, var(--warm-blue) 100%);
                color: white;
                text-align: center;
            }
            
            .playground h2 {
                font-family: 'Cooper BT', serif;
                font-size: 2.5rem;
                margin-bottom: 2rem;
            }
            
            .playground p {
                font-size: 1.2rem;
                max-width: 600px;
                margin: 0 auto 3rem;
                opacity: 0.9;
            }
            
            /* Form Styling */
            .form-container {
                max-width: 600px;
                margin: 4rem auto;
                background: white;
                padding: 3rem;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            }
            
            .form-group {
                margin-bottom: 2rem;
                text-align: left;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 0.5rem;
                font-weight: 600;
                color: var(--purple);
                font-size: 1rem;
            }
            
            .form-group input,
            .form-group textarea,
            .form-group select {
                width: 100%;
                padding: 1rem;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 1rem;
                transition: border-color 0.3s ease;
                font-family: 'Inter', sans-serif;
            }
            
            .form-group input:focus,
            .form-group textarea:focus,
            .form-group select:focus {
                outline: none;
                border-color: var(--soft-pink);
                box-shadow: 0 0 0 3px rgba(232, 156, 197, 0.1);
            }
            
            .form-group input::placeholder,
            .form-group textarea::placeholder {
                color: #999;
            }
            
            .submit-button {
                width: 100%;
                background: linear-gradient(135deg, var(--sunshine), var(--soft-pink));
                color: var(--text-dark);
                padding: 1.2rem;
                border: none;
                border-radius: 50px;
                font-size: 1.1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 1rem;
            }
            
            .submit-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(255, 215, 0, 0.4);
            }
            
            .submit-button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            
            /* Loading & Result Styles */
            .loading {
                display: none;
                text-align: center;
                padding: 2rem;
                background: var(--cream);
                border-radius: 15px;
                margin: 2rem 0;
            }
            
            .loading-spinner {
                width: 40px;
                height: 40px;
                margin: 0 auto 1rem;
                border: 4px solid var(--soft-pink);
                border-top: 4px solid var(--sunshine);
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .result {
                display: none;
                margin-top: 2rem;
                padding: 2rem;
                background: var(--cream);
                border-radius: 15px;
                border-left: 4px solid var(--sunshine);
            }
            
            .result h3 {
                color: var(--purple);
                margin-bottom: 1rem;
                font-family: 'Cooper BT', serif;
            }
            
            .audio-player {
                margin: 1.5rem 0;
            }
            
            .audio-player audio {
                width: 100%;
                border-radius: 10px;
            }
            
            .share-section {
                margin-top: 1.5rem;
                padding: 1.5rem;
                background: white;
                border-radius: 10px;
            }
            
            .share-section input {
                margin-bottom: 1rem;
            }
            
            /* Language Switcher */
            .language-switcher {
                position: fixed;
                bottom: 2rem;
                right: 2rem;
                background: var(--purple);
                color: white;
                padding: 0.8rem 1.5rem;
                border-radius: 50px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s ease;
                z-index: 100;
                box-shadow: 0 4px 15px rgba(139, 58, 92, 0.3);
            }
            
            .language-switcher:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(139, 58, 92, 0.4);
            }
            
            /* Responsive Design */
            @media (max-width: 768px) {
                .hero-content {
                    grid-template-columns: 1fr;
                    text-align: center;
                    gap: 2rem;
                }
                
                .hero-text h1 {
                    font-size: 2.5rem;
                }
                
                .features-grid {
                    grid-template-columns: 1fr;
                }
                
                .form-container {
                    margin: 2rem 1rem;
                    padding: 2rem;
                }
                
                .language-switcher {
                    bottom: 1rem;
                    right: 1rem;
                    padding: 0.6rem 1.2rem;
                    font-size: 0.9rem;
                }
                
                .brand-scene {
                    width: 280px;
                    height: 280px;
                }
                
                .character {
                    width: 100px;
                    height: 120px;
                }
            }
            
            /* Quote styles */
            .quote {
                font-style: italic;
                font-size: 1.2rem;
                color: var(--text-light);
                text-align: center;
                margin: 3rem auto;
                max-width: 500px;
                padding: 2rem;
                background: white;
                border-radius: 15px;
                border-left: 4px solid var(--soft-pink);
            }
        </style>
                text-align: center;
            }
            
            .playground h2 {
                font-family: 'Cooper BT', serif;
                font-size: 2.5rem;
                margin-bottom: 2rem;
            }
            
            .playground p {
                font-size: 1.2rem;
                max-width: 600px;
                margin: 0 auto 3rem;
                opacity: 0.9;
            }
            
            /* Form Styling */
            .form-container {
                max-width: 600px;
                margin: 4rem auto;
                background: white;
                padding: 3rem;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            }
            
            .form-group {
                margin-bottom: 2rem;
                text-align: left;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 0.5rem;
                font-weight: 600;
                color: var(--purple);
                font-size: 1rem;
            }
            
            .form-group input,
            .form-group textarea,
            .form-group select {
                width: 100%;
                padding: 1rem;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 1rem;
                transition: border-color 0.3s ease;
                font-family: 'Inter', sans-serif;
            }
            
            .form-group input:focus,
            .form-group textarea:focus,
            .form-group select:focus {
                outline: none;
                border-color: var(--soft-pink);
                box-shadow: 0 0 0 3px rgba(232, 156, 197, 0.1);
            }
            
            .form-group input::placeholder,
            .form-group textarea::placeholder {
                color: #999;
            }
            
            .submit-button {
                width: 100%;
                background: linear-gradient(135deg, var(--sunshine), var(--soft-pink));
                color: var(--text-dark);
                padding: 1.2rem;
                border: none;
                border-radius: 50px;
                font-size: 1.1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 1rem;
            }
            
            .submit-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(255, 215, 0, 0.4);
            }
            
            .submit-button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            
            /* Loading & Result Styles */
            .loading {
                display: none;
                text-align: center;
                padding: 2rem;
                background: var(--cream);
                border-radius: 15px;
                margin: 2rem 0;
            }
            
            .loading-spinner {
                width: 40px;
                height: 40px;
                margin: 0 auto 1rem;
                border: 4px solid var(--soft-pink);
                border-top: 4px solid var(--sunshine);
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .result {
                display: none;
                margin-top: 2rem;
                padding: 2rem;
                background: var(--cream);
                border-radius: 15px;
                border-left: 4px solid var(--sunshine);
            }
            
            .result h3 {
                color: var(--purple);
                margin-bottom: 1rem;
                font-family: 'Cooper BT', serif;
            }
            
            .audio-player {
                margin: 1.5rem 0;
            }
            
            .audio-player audio {
                width: 100%;
                border-radius: 10px;
            }
            
            .share-section {
                margin-top: 1.5rem;
                padding: 1.5rem;
                background: white;
                border-radius: 10px;
            }
            
            .share-section input {
                margin-bottom: 1rem;
            }
            
            /* Language Switcher */
            .language-switcher {
                position: fixed;
                bottom: 2rem;
                right: 2rem;
                background: var(--purple);
                color: white;
                padding: 0.8rem 1.5rem;
                border-radius: 50px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s ease;
                z-index: 100;
                box-shadow: 0 4px 15px rgba(139, 58, 92, 0.3);
            }
            
            .language-switcher:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(139, 58, 92, 0.4);
            }
            
            /* Responsive Design */
            @media (max-width: 768px) {
                .hero-content {
                    grid-template-columns: 1fr;
                    text-align: center;
                    gap: 2rem;
                }
                
                .hero-text h1 {
                    font-size: 2.5rem;
                }
                
                .features-grid {
                    grid-template-columns: 1fr;
                }
                
                .form-container {
                    margin: 2rem 1rem;
                    padding: 2rem;
                }
                
                .language-switcher {
                    bottom: 1rem;
                    right: 1rem;
                    padding: 0.6rem 1.2rem;
                    font-size: 0.9rem;
                }
            }
            
            /* Quote styles */
            .quote {
                font-style: italic;
                font-size: 1.2rem;
                color: var(--text-light);
                text-align: center;
                margin: 3rem auto;
                max-width: 500px;
                padding: 2rem;
                background: white;
                border-radius: 15px;
                border-left: 4px solid var(--soft-pink);
            }
        </style>
    </head>
    <body>
        <!-- Header -->
        <header class="header">
            <nav class="nav">
                <a href="#" class="logo">
                    <div class="logo-icon">☀️</div>
                    Shh-elf
                </a>
            </nav>
        </header>

        <!-- Hero Section -->
        <section class="hero">
            <div class="hero-content">
                <div class="hero-text">
                    <h1>Shh-elf</h1>
                    <p class="tagline">Shh... a story's about to begin.</p>
                    <p class="hero-description">
                        Turn reading into a curious, social, and emotionally engaging experience through 
                        bite-sized book talks and personalized recommendations.
                    </p>
                    <a href="#playground" class="cta-button">Start Your Reading Journey</a>
                </div>
                <div class="hero-visual">
                    <div class="illustration">
                        <div class="character">🙌</div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Quote Section -->
        <div class="quote">
            "Finding books is hard... It takes me a long time to finish the first chapter and 
            I'm not even sure if I like it."
            <br><strong>— Teen interviewee</strong>
        </div>

        <!-- Features Section -->
        <section class="features">
            <div class="container">
                <h2 class="section-title">How Shh-elf Works</h2>
                
                <div class="features-grid">
                    <div class="feature-card">
                        <div class="feature-icon">🎧</div>
                        <h3 class="feature-title">Book Talk Gallery</h3>
                        <p>Short audio clips to spark interest. Designed for curious or reluctant readers. Emotion-first! Not summary-first.</p>
                    </div>
                    
                    <div class="feature-card">
                        <div class="feature-icon">🎪</div>
                        <h3 class="feature-title">Book Talk Playground</h3>
                        <p>Students upload a few lines about someone they want to recommend a book to. AI turns it into a podcast-style voice memo—natural, emotional, shareable.</p>
                    </div>
                    
                    <div class="feature-card">
                        <div class="feature-icon">🌈</div>
                        <h3 class="feature-title">Social Discovery</h3>
                        <p>People read more when they're curious. Reading sticks when it leads to conversation. Peer recommendations matter more than generic lists.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Book Talk Playground -->
        <section id="playground" class="playground">
            <div class="container">
                <h2>Book Talk Playground</h2>
                <p>Create a personalized book recommendation for someone special. Our AI will turn your thoughts into a natural, emotional voice memo that's perfect for sharing.</p>
                
                <div class="form-container">
                    <form id="recommendationForm">
                        <div class="form-group">
                            <label for="book_title" id="label-book">Book Title</label>
                            <input type="text" id="book_title" name="book_title" required 
                                   placeholder="e.g., The Seven Husbands of Evelyn Hugo">
                        </div>
                        
                        <div class="form-group">
                            <label for="recipient_name" id="label-recipient">Recommend to</label>
                            <input type="text" id="recipient_name" name="recipient_name" required 
                                   placeholder="e.g., Sarah, my book-loving friend">
                        </div>
                        
                        <div class="form-group">
                            <label for="relationship" id="label-relationship">Your relationship</label>
                            <select id="relationship" name="relationship">
                                <option value="friend">Friend</option>
                                <option value="classmate">Classmate</option>
                                <option value="colleague">Colleague</option>
                                <option value="family">Family</option>
                                <option value="student">Student</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="recipient_interests" id="label-interests">Their interests (optional)</label>
                            <textarea id="recipient_interests" name="recipient_interests" rows="3" 
                                      placeholder="e.g., loves romance novels, enjoys character-driven stories, big fan of historical fiction..."></textarea>
                        </div>
                        
                        <div class="form-group">
                            <label for="language" id="label-language">Language</label>
                            <select id="language" name="language">
                                <option value="English">🇺🇸 English</option>
                                <option value="中文">🇨🇳 中文</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="tone" id="label-tone">Recommendation tone</label>
                            <select id="tone" name="tone">
                                <option value="friendly and enthusiastic">Friendly & Enthusiastic</option>
                                <option value="professional and objective">Professional & Objective</option>
                                <option value="casual and humorous">Casual & Humorous</option>
                                <option value="warm and caring">Warm & Caring</option>
                            </select>
                        </div>
                        
                        <button type="submit" class="submit-button" id="submit-btn">
                            🎙️ Create Audio Recommendation
                        </button>
                    </form>
                    
                    <div class="loading" id="loading">
                        <div class="loading-spinner"></div>
                        <p id="loading-text1">Creating your personalized book talk...</p>
                        <p id="loading-text2">This usually takes 10-15 seconds</p>
                    </div>
                    
                    <div class="result" id="result">
                        <h3 id="success-title">🎉 Your Book Talk is Ready!</h3>
                        <div class="audio-player">
                            <audio controls id="audioPlayer">
                                Your browser does not support audio playback.
                            </audio>
                        </div>
                        <div class="share-section">
                            <h4 id="share-title">📱 Share Your Recommendation</h4>
                            <input type="text" id="shareUrl" readonly placeholder="Share link will appear here">
                            <button onclick="copyToClipboard()" class="cta-button" id="copy-btn">📋 Copy Link</button>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Language Switcher -->
        <div class="language-switcher" onclick="toggleLanguage()">
            <span id="lang-switch">中文</span>
        </div>

        <script>
            // Language translations
            const translations = {
                en: {
                    'label-book': "Book Title",
                    'label-recipient': "Recommend to",
                    'label-relationship': "Your relationship",
                    'label-interests': "Their interests (optional)",
                    'label-language': "Language",
                    'label-tone': "Recommendation tone",
                    'submit-btn': "🎙️ Create Audio Recommendation",
                    'loading-text1': "Creating your personalized book talk...",
                    'loading-text2': "This usually takes 10-15 seconds",
                    'success-title': "🎉 Your Book Talk is Ready!",
                    'share-title': "📱 Share Your Recommendation",
                    'copy-btn': "📋 Copy Link",
                    'lang-switch': "中文",
                    placeholders: {
                        book: "e.g., The Seven Husbands of Evelyn Hugo",
                        recipient: "e.g., Sarah, my book-loving friend",
                        interests: "e.g., loves romance novels, enjoys character-driven stories..."
                    },
                    relationships: ["Friend", "Classmate", "Colleague", "Family", "Student"],
                    relationshipValues: ["friend", "classmate", "colleague", "family", "student"],
                    tones: ["Friendly & Enthusiastic", "Professional & Objective", "Casual & Humorous", "Warm & Caring"],
                    toneValues: ["friendly and enthusiastic", "professional and objective", "casual and humorous", "warm and caring"]
                },
                zh: {
                    'label-book': "书籍名称",
                    'label-recipient': "推荐给谁",
                    'label-relationship': "你们的关系",
                    'label-interests': "TA的兴趣爱好（可选）",
                    'label-language': "语言",
                    'label-tone': "推荐语调",
                    'submit-btn': "🎙️ 生成语音推荐",
                    'loading-text1': "正在创建个性化书籍推荐...",
                    'loading-text2': "通常需要10-15秒",
                    'success-title': "🎉 你的书籍推荐已准备好！",
                    'share-title': "📱 分享你的推荐",
                    'copy-btn': "📋 复制链接",
                    'lang-switch': "English",
                    placeholders: {
                        book: "例如：《活着》",
                        recipient: "例如：我的朋友小明",
                        interests: "例如：喜欢文学小说，爱看历史故事..."
                    },
                    relationships: ["朋友", "同学", "同事", "家人", "学生"],
                    relationshipValues: ["朋友", "同学", "同事", "家人", "学生"],
                    tones: ["友好热情", "专业客观", "轻松幽默", "温暖亲切"],
                    toneValues: ["友好热情", "专业客观", "轻松幽默", "温暖亲切"]
                }
            };

            let currentLang = 'en';

            function toggleLanguage() {
                currentLang = currentLang === 'en' ? 'zh' : 'en';
                updateLanguage();
            }

            function updateLanguage() {
                const t = translations[currentLang];
                
                // Update labels and text
                Object.keys(t).forEach(key => {
                    const element = document.getElementById(key);
                    if (element && typeof t[key] === 'string') {
                        element.textContent = t[key];
                    }
                });
                
                // Update placeholders
                if (t.placeholders) {
                    document.getElementById('book_title').placeholder = t.placeholders.book;
                    document.getElementById('recipient_name').placeholder = t.placeholders.recipient;
                    document.getElementById('recipient_interests').placeholder = t.placeholders.interests;
                }
                
                // Update dropdown options
                if (t.relationships) {
                    const relationshipSelect = document.getElementById('relationship');
                    relationshipSelect.innerHTML = '';
                    t.relationships.forEach((rel, i) => {
                        const option = document.createElement('option');
                        option.value = t.relationshipValues[i];
                        option.textContent = rel;
                        relationshipSelect.appendChild(option);
                    });
                }
                
                if (t.tones) {
                    const toneSelect = document.getElementById('tone');
                    toneSelect.innerHTML = '';
                    t.tones.forEach((tone, i) => {
                        const option = document.createElement('option');
                        option.value = t.toneValues[i];
                        option.textContent = tone;
                        toneSelect.appendChild(option);
                    });
                }
            }

            // Form submission
            document.getElementById('recommendationForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const submitBtn = document.getElementById('submit-btn');
                const loadingDiv = document.getElementById('loading');
                const resultDiv = document.getElementById('result');
                
                // Show loading state
                loadingDiv.style.display = 'block';
                resultDiv.style.display = 'none';
                submitBtn.disabled = true;
                
                // Collect form data
                const formData = {
                    book_title: document.getElementById('book_title').value,
                    recipient_name: document.getElementById('recipient_name').value,
                    relationship: document.getElementById('relationship').value,
                    recipient_interests: document.getElementById('recipient_interests').value,
                    tone: document.getElementById('tone').value,
                    language: document.getElementById('language').value
                };
                
                try {
                    const response = await fetch('/generate-recommendation', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(formData)
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        // Show result
                        loadingDiv.style.display = 'none';
                        resultDiv.style.display = 'block';
                        
                        // Set audio player
                        const audioPlayer = document.getElementById('audioPlayer');
                        audioPlayer.src = '/' + result.audio_path;
                        
                        // Set share URL
                        const shareUrl = window.location.origin + '/share/' + result.share_id;
                        document.getElementById('shareUrl').value = shareUrl;
                        
                        // Scroll to result
                        resultDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    } else {
                        throw new Error(result.detail || 'Generation failed');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    alert('Sorry, something went wrong. Please try again.');
                    loadingDiv.style.display = 'none';
                } finally {
                    submitBtn.disabled = false;
                }
            });
            
            function copyToClipboard() {
                const shareUrl = document.getElementById('shareUrl');
                shareUrl.select();
                document.execCommand('copy');
                
                const copyBtn = document.getElementById('copy-btn');
                const originalText = copyBtn.textContent;
                copyBtn.textContent = currentLang === 'en' ? '✓ Copied!' : '✓ 已复制!';
                
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                }, 2000);
            }

            // Smooth scrolling for anchor links
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', function (e) {
                    e.preventDefault();
                    const target = document.querySelector(this.getAttribute('href'));
                    if (target) {
                        target.scrollIntoView({ behavior: 'smooth' });
                    }
                });
            });

            // Initialize
            window.onload = function() {
                updateLanguage();
            };
        </script>
    </body>
    </html>
    """

# API路由 - 生成推荐 (保持不变)
@app.post("/generate-recommendation")
async def generate_recommendation(req: BookRecommendation):
    try:
        print(f"=== 处理推荐请求 ===")
        print(f"书籍: {req.book_title}")
        print(f"接收人: {req.recipient_name}")
        
        recommendation_text = generate_recommendation_text(
            req.book_title, 
            req.recipient_name, 
            req.relationship,
            req.recipient_interests,
            req.tone,
            req.language
        )
        
        content_hash = hashlib.md5(
            f"{req.book_title}{req.recipient_name}{recommendation_text}".encode()
        ).hexdigest()[:8]
        filename = f"rec_{content_hash}"
        
        audio_path = text_to_speech(recommendation_text, filename, req.language)
        
        return {
            "success": True,
            "recommendation_text": recommendation_text,
            "audio_path": audio_path,
            "share_id": content_hash
        }
        
    except Exception as e:
        print(f"=== 推荐生成失败: {str(e)} ===")
        raise HTTPException(status_code=500, detail=str(e))

# 分享页面 - 品牌风格
@app.get("/share/{share_id}")
async def share_recommendation(share_id: str):
    audio_file = f"audio/rec_{share_id}.mp3"
    if not os.path.exists(audio_file):
        raise HTTPException(status_code=404, detail="推荐不存在")
    
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>A Book Recommendation for You | Shh-elf</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="Someone has shared a personalized book recommendation with you through Shh-elf!">
        <link href="https://fonts.googleapis.com/css2?family=Cooper+BT:wght@400;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            
            :root {{
                --cream: #f5f1e8;
                --sunshine: #ffd700;
                --purple: #8b3a5c;
                --soft-pink: #e89cc5;
                --warm-blue: #7bb3f0;
                --text-dark: #2c2c2c;
                --text-light: #6b6b6b;
            }}
            
            body {{
                font-family: 'Inter', sans-serif;
                background: var(--cream);
                color: var(--text-dark);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                line-height: 1.6;
                padding: 2rem;
            }}
            
            .container {{
                max-width: 600px;
                background: white;
                padding: 3rem;
                border-radius: 20px;
                text-align: center;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
                border-top: 4px solid var(--sunshine);
                position: relative;
                overflow: hidden;
            }}
            
            .container::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(135deg, transparent 0%, rgba(255, 215, 0, 0.05) 100%);
                pointer-events: none;
            }}
            
            .logo {{
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
                margin-bottom: 2rem;
                position: relative;
                z-index: 2;
            }}
            
            .logo-icon {{
                width: 50px;
                height: 50px;
                background: linear-gradient(135deg, var(--sunshine), var(--soft-pink));
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.5rem;
                animation: gentle-pulse 3s ease-in-out infinite;
            }}
            
            @keyframes gentle-pulse {{
                0%, 100% {{ transform: scale(1); }}
                50% {{ transform: scale(1.1); }}
            }}
            
            .logo-text {{
                font-family: 'Cooper BT', serif;
                font-size: 1.5rem;
                font-weight: 700;
                color: var(--purple);
            }}
            
            h1 {{
                font-family: 'Cooper BT', serif;
                font-size: 2.2rem;
                color: var(--purple);
                margin-bottom: 1rem;
                position: relative;
                z-index: 2;
            }}
            
            .subtitle {{
                font-size: 1.2rem;
                color: var(--text-light);
                margin-bottom: 2.5rem;
                position: relative;
                z-index: 2;
            }}
            
            .audio-player {{
                margin: 2.5rem 0;
                position: relative;
                z-index: 2;
            }}
            
            audio {{
                width: 100%;
                height: 60px;
                border-radius: 15px;
                background: var(--cream);
                border: 2px solid var(--soft-pink);
            }}
            
            .cta {{
                margin-top: 2.5rem;
                position: relative;
                z-index: 2;
            }}
            
            .cta-button {{
                background: linear-gradient(135deg, var(--sunshine), var(--soft-pink));
                color: var(--text-dark);
                padding: 1rem 2.5rem;
                border: none;
                border-radius: 50px;
                font-size: 1.1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3);
                text-decoration: none;
                display: inline-block;
                font-family: 'Inter', sans-serif;
            }}
            
            .cta-button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(255, 215, 0, 0.4);
            }}
            
            .tagline {{
                margin-top: 2rem;
                font-style: italic;
                color: var(--text-light);
                font-size: 1rem;
                position: relative;
                z-index: 2;
            }}
            
            @media (max-width: 768px) {{
                .container {{
                    margin: 1rem;
                    padding: 2rem;
                }}
                
                h1 {{
                    font-size: 1.8rem;
                }}
                
                .subtitle {{
                    font-size: 1.1rem;
                }}
                
                .cta-button {{
                    padding: 0.8rem 2rem;
                    font-size: 1rem;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">
                <div class="logo-icon">☀️</div>
                <div class="logo-text">Shh-elf</div>
            </div>
            
            <h1>🎁 A Book Recommendation for You!</h1>
            <p class="subtitle">Someone special thought you'd love this book and created a personalized recommendation just for you.</p>
            
            <div class="audio-player">
                <audio controls>
                    <source src="/audio/rec_{share_id}.mp3" type="audio/mpeg">
                    Your browser does not support audio playback.
                </audio>
            </div>
            
            <div class="cta">
                <a href="/" class="cta-button">✨ Create Your Own Book Talk</a>
            </div>
            
            <p class="tagline">Shh... a story's about to begin.</p>
        </div>
    </body>
    </html>
    """)

# 健康检查
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "message": "Shh-elf is ready to spark reading through curiosity and connection!",
        "services": {
            "openai": "configured" if OPENAI_API_KEY else "missing",
            "elevenlabs": "configured" if ELEVENLABS_API_KEY else "missing"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

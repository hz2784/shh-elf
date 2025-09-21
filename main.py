from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional, List
import requests
import os
from dotenv import load_dotenv
import hashlib
from pathlib import Path
from datetime import timedelta

from database import (
    create_tables, get_db, get_user_by_email, get_user_by_username,
    create_user, create_user_recommendation, get_user_recommendations,
    get_recommendation_by_share_id, User, UserRecommendation
)
from auth import (
    create_access_token, get_current_user, get_current_user_optional,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# 加载环境变量
load_dotenv()

app = FastAPI(
    title="Shh-elf API", 
    description="AI-powered personalized book recommendations API",
    version="2.0.0"
)

# CORS配置 - 允许前端访问API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建必要目录
Path("audio").mkdir(exist_ok=True)

# 创建数据库表
create_tables()

# 简单的内存存储来记录每个分享的语言信息
share_language_store = {}

# 挂载音频文件服务
app.mount("/audio", StaticFiles(directory="audio"), name="audio")

# API密钥
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

# 数据模型
class BookRecommendation(BaseModel):
    book_title: str
    recipient_name: str
    relationship: str = "朋友"
    recipient_interests: str = ""
    tone: str = "友好热情"
    language: str = "中文"
    dialect: str = "zh-CN-XiaoxiaoNeural"

class RecommendationResponse(BaseModel):
    success: bool
    recommendation_text: str
    audio_path: str
    share_id: str

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class RecommendationHistoryResponse(BaseModel):
    id: int
    book_title: str
    recipient_name: str
    relationship: str
    language: str
    recommendation_text: str
    audio_path: str
    share_id: str
    created_at: str

# GPT生成推荐文本
def generate_recommendation_text(book_title: str, recipient_name: str, relationship: str, interests: str, tone: str, language: str) -> str:
    """使用GPT生成个性化书籍推荐文本"""
    
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
        print(f"GPT API错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GPT API错误: {str(e)}")

# 智能文本转语音 - 根据语言选择最佳API
def text_to_speech(text: str, filename: str, language: str, dialect: str = "zh-CN-XiaoxiaoNeural") -> str:
    """根据语言选择最佳TTS服务：中文使用Azure方言语音，英文使用ElevenLabs"""

    print(f"=== 语音生成调试信息 ===")
    print(f"文本: {text}")
    print(f"文件名: {filename}")
    print(f"语言: {language}")
    print(f"方言: {dialect}")

    if language == "中文":
        # 使用Azure Speech Services和用户选择的方言
        return azure_text_to_speech(text, filename, dialect)
    else:
        return elevenlabs_text_to_speech(text, filename)

def enhance_text_with_ssml(text: str) -> str:
    """智能增强中文文本的SSML标记，改善断句和语调"""
    import re

    # 替换标点符号为带停顿的SSML标记
    enhanced = text

    # 在句号、叹号、问号后添加长停顿
    enhanced = re.sub(r'([。！？])', r'\1<break time="800ms"/>', enhanced)

    # 在逗号、顿号后添加中等停顿
    enhanced = re.sub(r'([，、])', r'\1<break time="400ms"/>', enhanced)

    # 在分号、冒号后添加短停顿
    enhanced = re.sub(r'([；：])', r'\1<break time="600ms"/>', enhanced)

    # 强调重要词汇（书名、人名等）- 移除书名号避免SSML冲突
    enhanced = re.sub(r'《([^》]+)》', r'<emphasis level="moderate">\1</emphasis>', enhanced)

    # 为语气词添加适当的语调变化
    enhanced = re.sub(r'(哇|哦|呀|啊|嗯|哈哈)', r'<prosody pitch="+10%" rate="0.8">\1</prosody>', enhanced)

    # 为感叹词添加情感表达
    enhanced = re.sub(r'(太棒了|真的|绝对|非常|特别)', r'<emphasis level="strong">\1</emphasis>', enhanced)

    # 为数字添加清晰发音
    enhanced = re.sub(r'(\d+)', r'<say-as interpret-as="cardinal">\1</say-as>', enhanced)

    return enhanced

def azure_text_to_speech(text: str, filename: str, voice_name: str = "zh-CN-XiaoxiaoNeural") -> str:
    """使用Azure Speech Services生成中文语音 - 专业中文声优"""

    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        print("Azure Speech Services未配置，回退到OpenAI TTS")
        return openai_text_to_speech(text, filename)

    # Azure Speech Services endpoint
    url = f"https://{AZURE_SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_SPEECH_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-160kbitrate-mono-mp3"
    }

    # 简化SSML格式 - 避免复杂标签冲突
    # enhanced_text = enhance_text_with_ssml(text)  # 暂时禁用
    ssml = f"""<?xml version="1.0" encoding="UTF-8"?>
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
    <voice name="{voice_name}">
        {text}
    </voice>
</speak>"""

    try:
        print(f"使用Azure Speech Services生成中文语音...")
        print(f"声音: {voice_name}")
        print(f"SSML内容: {ssml}")
        response = requests.post(url, headers=headers, data=ssml.encode('utf-8'))
        print(f"Azure Speech响应状态: {response.status_code}")
        response.raise_for_status()

        audio_path = f"audio/{filename}.mp3"
        with open(audio_path, "wb") as f:
            f.write(response.content)

        print(f"Azure中文音频文件已保存: {audio_path}")
        return audio_path
    except Exception as e:
        print(f"Azure Speech错误: {str(e)}")
        print("回退到OpenAI TTS")
        return openai_text_to_speech(text, filename)

def openai_text_to_speech(text: str, filename: str) -> str:
    """使用OpenAI TTS生成中文语音 - 更自然的中文发音"""

    url = "https://api.openai.com/v1/audio/speech"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "tts-1",  # 或 tts-1-hd 用于更高质量
        "input": text,
        "voice": "alloy",  # 支持中文的声音: alloy, echo, fable, onyx, nova, shimmer
        "response_format": "mp3",
        "speed": 1.0
    }

    try:
        print(f"使用OpenAI TTS生成中文语音...")
        response = requests.post(url, json=data, headers=headers)
        print(f"OpenAI TTS响应状态: {response.status_code}")
        response.raise_for_status()

        audio_path = f"audio/{filename}.mp3"
        with open(audio_path, "wb") as f:
            f.write(response.content)

        print(f"中文音频文件已保存: {audio_path}")
        return audio_path
    except Exception as e:
        print(f"OpenAI TTS错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"中文语音生成错误: {str(e)}")

def elevenlabs_text_to_speech(text: str, filename: str) -> str:
    """使用ElevenLabs生成英文语音"""

    voice_id = "9BWtsMINqrJLrRacOk9x"  # Aria voice
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

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
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }

    try:
        print(f"使用ElevenLabs生成英文语音...")
        response = requests.post(url, json=data, headers=headers)
        print(f"ElevenLabs响应状态: {response.status_code}")
        response.raise_for_status()

        audio_path = f"audio/{filename}.mp3"
        with open(audio_path, "wb") as f:
            f.write(response.content)

        print(f"英文音频文件已保存: {audio_path}")
        return audio_path
    except Exception as e:
        print(f"ElevenLabs错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"英文语音生成错误: {str(e)}")

# API路由

@app.get("/")
async def root():
    """API根路由"""
    return {
        "message": "Shh-elf API Server", 
        "version": "2.0.0",
        "status": "online",
        "docs": "/docs",
        "frontend": "Please serve frontend separately"
    }

@app.post("/api/register", response_model=Token)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    # 检查邮箱是否已存在
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已存在"
        )

    # 创建新用户
    user = create_user(db, user_data.username, user_data.email, user_data.password)

    # 生成访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at.isoformat()
        }
    }

@app.post("/api/login", response_model=Token)
async def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    user = get_user_by_username(db, login_data.username)
    if not user or not user.verify_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at.isoformat()
        }
    }

@app.get("/api/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "created_at": current_user.created_at.isoformat()
    }

@app.get("/api/my-recommendations", response_model=List[RecommendationHistoryResponse])
async def get_my_recommendations(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户的推荐历史"""
    recommendations = get_user_recommendations(db, current_user.id, skip, limit)

    return [
        {
            "id": rec.id,
            "book_title": rec.book_title,
            "recipient_name": rec.recipient_name,
            "relationship": rec.relationship,
            "language": rec.language,
            "recommendation_text": rec.recommendation_text,
            "audio_path": rec.audio_path,
            "share_id": rec.share_id,
            "created_at": rec.created_at.isoformat()
        }
        for rec in recommendations
    ]

@app.post("/api/generate-recommendation", response_model=RecommendationResponse)
async def generate_recommendation(
    req: BookRecommendation,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """生成书籍推荐API"""
    try:
        print(f"=== 处理推荐请求 ===")
        print(f"书籍: {req.book_title}")
        print(f"接收人: {req.recipient_name}")
        print(f"关系: {req.relationship}")
        print(f"兴趣: {req.recipient_interests}")
        print(f"语调: {req.tone}")
        print(f"语言: {req.language}")
        
        # 生成推荐文本
        recommendation_text = generate_recommendation_text(
            req.book_title, 
            req.recipient_name, 
            req.relationship,
            req.recipient_interests,
            req.tone,
            req.language
        )
        
        print(f"生成的推荐文本: {recommendation_text}")
        print(f"接收到的方言参数: {req.dialect}")

        # 生成唯一文件名
        content_hash = hashlib.md5(
            f"{req.book_title}{req.recipient_name}{recommendation_text}".encode()
        ).hexdigest()[:8]
        filename = f"rec_{content_hash}"
        
        # 生成语音文件
        audio_path = text_to_speech(recommendation_text, filename, req.language, req.dialect)

        # 存储分享的语言信息
        share_language_store[content_hash] = req.language

        # 如果用户已登录，保存到数据库
        if current_user:
            create_user_recommendation(
                db=db,
                user_id=current_user.id,
                book_title=req.book_title,
                recipient_name=req.recipient_name,
                relationship=req.relationship,
                recipient_interests=req.recipient_interests,
                tone=req.tone,
                language=req.language,
                dialect=req.dialect,
                recommendation_text=recommendation_text,
                audio_path=audio_path,
                share_id=content_hash
            )

        response = RecommendationResponse(
            success=True,
            recommendation_text=recommendation_text,
            audio_path=audio_path,
            share_id=content_hash
        )
        
        print(f"=== 推荐生成成功 ===")
        print(f"分享ID: {content_hash}")
        
        return response
        
    except Exception as e:
        print(f"=== 推荐生成失败 ===")
        print(f"错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/share/{share_id}")
async def share_recommendation_page(share_id: str):
    """分享推荐页面 - 支持多语言"""
    audio_file = f"audio/rec_{share_id}.mp3"
    if not os.path.exists(audio_file):
        raise HTTPException(status_code=404, detail="推荐不存在")

    # 获取推荐的语言，默认为英文
    language = share_language_store.get(share_id, "English")

    if language == "中文":
        return chinese_share_page(share_id)
    else:
        return english_share_page(share_id)

def chinese_share_page(share_id: str) -> HTMLResponse:
    """中文分享页面"""
    html_content = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SHH-ELF :: 个性化书籍推荐分享</title>
    <meta name="description" content="有人通过 SHH-ELF 与你分享了一个个性化书籍推荐！">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{
            --primary-green: #00ff00; --dark-green: #008000; --bg-black: #000000;
            --bg-dark: #111111; --white: #ffffff; --gray: #333333; --light-gray: #666666;
        }}
        body {{ font-family: 'VT323', 'Courier New', monospace; background: var(--bg-black);
            color: var(--primary-green); line-height: 1.4; font-size: 18px; cursor: crosshair; min-height: 100vh; }}
        body::before {{ content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(transparent 50%, rgba(0, 255, 0, 0.03) 50%);
            background-size: 100% 4px; pointer-events: none; z-index: 9999; }}
        @keyframes flicker {{ 0%, 100% {{ opacity: 1; }} 98% {{ opacity: 0.98; }} 99% {{ opacity: 1; }} }}
        body {{ animation: flicker 3s infinite; }}
        .main-content {{ margin-top: 60px; padding: 40px 20px; display: flex; justify-content: center;
            align-items: center; min-height: calc(100vh - 60px); }}
        .share-container {{ max-width: 600px; width: 100%; border: 3px solid var(--primary-green);
            background: var(--bg-dark); padding: 40px; text-align: center; }}
        .share-header {{ font-size: 2rem; text-transform: uppercase; letter-spacing: 2px;
            margin-bottom: 30px; color: var(--primary-green); text-shadow: 2px 2px 0px var(--dark-green); }}
        .share-message {{ font-size: 1.2rem; margin-bottom: 30px; color: var(--white); line-height: 1.6; }}
        .audio-container {{ margin: 30px 0; padding: 20px; border: 2px solid var(--light-gray);
            background: var(--bg-black); }}
        .audio-player {{ width: 100%; background: var(--bg-black); border: 2px solid var(--primary-green);
            margin-top: 10px; }}
        .pixel-btn {{ background: var(--bg-black); color: var(--primary-green);
            border: 3px solid var(--primary-green); padding: 12px 24px; font-family: 'VT323', monospace;
            font-size: 1.2rem; text-transform: uppercase; cursor: pointer; transition: all 0.2s;
            text-decoration: none; display: inline-block; margin-top: 20px;
            box-shadow: 4px 4px 0px var(--dark-green); }}
        .pixel-btn:hover {{ background: var(--primary-green); color: var(--bg-black);
            transform: translate(2px, 2px); box-shadow: 2px 2px 0px var(--dark-green); }}
    </style>
</head>
<body>
    <div class="main-content">
        <div class="share-container">
            <div class="share-header">📚 书籍推荐</div>
            <div class="share-message">
                有人通过 SHH-ELF 与你分享了一个个性化书籍推荐！
            </div>
            <div class="audio-container">
                <div style="color: var(--primary-green); margin-bottom: 10px; text-transform: uppercase;">
                    🎧 语音推荐：
                </div>
                <audio controls class="audio-player">
                    <source src="/audio/rec_{share_id}.mp3" type="audio/mpeg">
                    你的浏览器不支持音频播放。
                </audio>
            </div>
            <div style="margin-top: 30px;">
                <a href="https://hz2784.github.io/shh-elf/" class="pixel-btn">创建你的推荐</a>
            </div>
        </div>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html_content)

def english_share_page(share_id: str) -> HTMLResponse:
    """英文分享页面"""
    # Inline HTML for share page
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SHH-ELF :: Shared Book Recommendation</title>
    <meta name="description" content="Someone has shared a personalized book recommendation with you through Shh-elf!">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{
            --primary-green: #00ff00; --dark-green: #008000; --bg-black: #000000;
            --bg-dark: #111111; --white: #ffffff; --gray: #333333; --light-gray: #666666;
        }}
        body {{ font-family: 'VT323', 'Courier New', monospace; background: var(--bg-black);
            color: var(--primary-green); line-height: 1.4; font-size: 18px; cursor: crosshair; min-height: 100vh; }}
        body::before {{ content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(transparent 50%, rgba(0, 255, 0, 0.03) 50%);
            background-size: 100% 4px; pointer-events: none; z-index: 9999; }}
        @keyframes flicker {{ 0%, 100% {{ opacity: 1; }} 98% {{ opacity: 0.98; }} 99% {{ opacity: 1; }} }}
        body {{ animation: flicker 3s infinite; }}
        .main-content {{ margin-top: 60px; padding: 40px 20px; display: flex; justify-content: center;
            align-items: center; min-height: calc(100vh - 60px); }}
        .share-container {{ max-width: 600px; width: 100%; border: 3px solid var(--primary-green);
            background: var(--bg-dark); padding: 40px; text-align: center; }}
        .share-header {{ font-size: 2rem; text-transform: uppercase; letter-spacing: 2px;
            margin-bottom: 30px; color: var(--primary-green); text-shadow: 2px 2px 0px var(--dark-green); }}
        .share-message {{ font-size: 1.2rem; margin-bottom: 30px; color: var(--white); line-height: 1.6; }}
        .audio-container {{ margin: 30px 0; padding: 20px; border: 2px solid var(--light-gray);
            background: var(--bg-black); }}
        .audio-player {{ width: 100%; background: var(--bg-black); border: 2px solid var(--primary-green);
            margin-top: 10px; }}
        .pixel-btn {{ background: var(--bg-black); color: var(--primary-green);
            border: 3px solid var(--primary-green); padding: 12px 24px; font-family: 'VT323', monospace;
            font-size: 1.2rem; text-transform: uppercase; cursor: pointer; transition: all 0.2s;
            text-decoration: none; display: inline-block; margin-top: 20px;
            box-shadow: 4px 4px 0px var(--dark-green); }}
        .pixel-btn:hover {{ background: var(--primary-green); color: var(--bg-black);
            transform: translate(2px, 2px); box-shadow: 2px 2px 0px var(--dark-green); }}
    </style>
</head>
<body>
    <div class="main-content">
        <div class="share-container">
            <div class="share-header">📚 Book Recommendation</div>
            <div class="share-message">
                Someone has shared a personalized book recommendation with you through SHH-ELF!
            </div>
            <div class="audio-container">
                <div style="color: var(--primary-green); margin-bottom: 10px; text-transform: uppercase;">
                    🎧 Audio Recommendation:
                </div>
                <audio controls class="audio-player">
                    <source src="/audio/rec_{share_id}.mp3" type="audio/mpeg">
                    Your browser does not support audio playback.
                </audio>
            </div>
            <div style="margin-top: 30px;">
                <a href="https://hz2784.github.io/shh-elf/" class="pixel-btn">Create Your Own Recommendation</a>
            </divki>
        </div>
    </div>
</body>
</html>"""

    return HTMLResponse(content=html_content)

@app.get("/api/share/{share_id}")
async def get_shared_recommendation(share_id: str):
    """获取分享的推荐信息"""
    audio_file = f"audio/rec_{share_id}.mp3"
    if not os.path.exists(audio_file):
        raise HTTPException(status_code=404, detail="推荐不存在")
    
    return {
        "success": True,
        "share_id": share_id,
        "audio_url": f"/audio/rec_{share_id}.mp3",
        "message": "推荐存在"
    }

@app.get("/api/health")
async def health_check():
    """健康检查API"""
    return {
        "status": "healthy", 
        "message": "Shh-elf API is operational!",
        "services": {
            "openai": "configured" if OPENAI_API_KEY else "missing",
            "elevenlabs": "configured" if ELEVENLABS_API_KEY else "missing"
        }
    }

# Render部署配置
if __name__ == "__main__":
    import uvicorn
    print("🚀 启动 Shh-elf API 服务器...")
    print("📋 API文档: http://localhost:8000/docs")
    print("🔗 前端: 请单独部署前端文件")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
        log_level="info"
    )

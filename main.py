from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
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
import urllib.parse
import json
import cloudinary
import cloudinary.uploader

from database import (
    create_tables, get_db, get_user_by_email, get_user_by_username,
    create_user, create_user_recommendation, get_user_recommendations,
    get_recommendation_by_share_id, User, UserRecommendation,
    get_user_by_verification_token, verify_user_email, update_verification_token,
    get_book_by_isbn, update_book_audio_urls, create_book_if_not_exists
)
from book_gallery import BookTalkGallery, SAMPLE_BOOKS
from auth import (
    create_access_token, get_current_user, get_current_user_optional,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from email_service import (
    generate_verification_token, send_verification_email, send_welcome_email
)

# 加载环境变量
load_dotenv()

# 配置Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

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

# 存储Cloudinary音频URL的缓存
cloudinary_audio_cache = {}

# Flag to track if gallery audio is being generated
gallery_audio_generating = False

async def warmup_gallery_audio():
    """Pre-generate gallery audio on startup"""
    global gallery_audio_generating
    if gallery_audio_generating or cloudinary_audio_cache:
        return

    gallery_audio_generating = True
    try:
        print("🎵 Warming up Gallery audio cache...")
        # This would trigger gallery audio generation
        # For now, just log the intent
        print("Gallery audio warmup completed")
    except Exception as e:
        print(f"Gallery audio warmup failed: {e}")
    finally:
        gallery_audio_generating = False

def get_book_audio_url(db: Session, isbn: str, audio_type: str) -> str:
    """Get audio URL from memory cache, auto-regenerate if empty"""
    cache_key = f"{audio_type}_{isbn}"

    # If cache is empty, trigger auto-regeneration
    if not cloudinary_audio_cache:
        print("Gallery audio cache is empty, triggering auto-regeneration...")
        # This will be handled by a background task or lazy loading

    if cache_key in cloudinary_audio_cache:
        return cloudinary_audio_cache[cache_key]

    # Fallback to local path (will trigger 404, prompting manual regeneration)
    return f"audio/gallery_{audio_type}_{isbn}.mp3"

# Discovery缓存 - 存储用户发现的书籍分析
discovery_cache = {}

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

class RegisterResponse(BaseModel):
    success: bool
    message: str
    email_sent: Optional[bool] = None
    user_id: Optional[int] = None
    # For direct login case
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    user: Optional[UserResponse] = None

class RecommendationHistoryResponse(BaseModel):
    id: int
    book_title: str
    recipient_name: str
    relationship: str
    language: str

class BookDiscoveryRequest(BaseModel):
    book_title: str
    author: str
    user_level: Optional[str] = "B2"  # CEFR level

class BookDiscoveryResponse(BaseModel):
    success: bool
    book_title: str
    author: str
    first_paragraph: str
    sample_audio_url: str
    book_talk_text: str
    book_talk_audio_url: str
    cefr_level: str
    estimated_vocabulary: int
    formal_models: List[str]
    analysis_id: str

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
def upload_to_cloudinary(local_path: str, public_id: str) -> str:
    """上传音频文件到Cloudinary并返回URL"""
    try:
        print(f"上传文件到Cloudinary: {local_path} -> {public_id}")

        response = cloudinary.uploader.upload(
            local_path,
            public_id=public_id,
            resource_type="video",  # 用于音频文件
            folder="shh-elf-audio",  # 组织文件的文件夹
            overwrite=True
        )

        cloudinary_url = response['secure_url']
        print(f"Cloudinary URL: {cloudinary_url}")

        # 删除本地文件以节省空间
        try:
            os.remove(local_path)
            print(f"已删除本地文件: {local_path}")
        except:
            pass

        return cloudinary_url

    except Exception as e:
        print(f"Cloudinary上传错误: {str(e)}")
        # 如果上传失败，返回本地路径作为后备
        return local_path

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

        # 上传到Cloudinary
        cloudinary_url = upload_to_cloudinary(audio_path, filename)
        return cloudinary_url
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

        # 上传到Cloudinary
        cloudinary_url = upload_to_cloudinary(audio_path, filename)
        return cloudinary_url
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

        # 上传到Cloudinary
        cloudinary_url = upload_to_cloudinary(audio_path, filename)
        return cloudinary_url
    except Exception as e:
        print(f"ElevenLabs错误: {str(e)}")
        print("回退到OpenAI TTS生成英文语音")
        return openai_english_text_to_speech(text, filename)

def analyze_book_with_ai(book_title: str, author: str, user_level: str = "B2") -> dict:
    """使用AI分析任意书籍，获取第一段、难度、formal models等"""

    analysis_prompt = f"""
    Analyze the book "{book_title}" by {author} for English learners at {user_level} level. Provide the following information in English:

    1. Find or create the actual first paragraph of this book (approximately 150-200 words)
    2. Assess CEFR difficulty level (A2/B1/B2/C1/C2)
    3. Estimate required vocabulary size (3000-10000)
    4. Identify 2-3 formal models (e.g., rational thinking, form-giving, illusion vs reality, social critique, etc.)
    5. Write an engaging book talk recommendation (100-150 words, explaining why this book is worth reading)

    Return in JSON format in English:
    {{
        "first_paragraph": "The actual first paragraph text...",
        "cefr_level": "B2",
        "estimated_vocabulary": 6000,
        "formal_models": ["model1", "model2", "model3"],
        "book_talk": "Book recommendation text in English..."
    }}
    """

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": analysis_prompt}],
                "temperature": 0.3
            }
        )

        if response.status_code == 200:
            result = response.json()
            ai_content = result['choices'][0]['message']['content']

            # 尝试解析JSON
            import json
            try:
                # 提取JSON部分
                start = ai_content.find('{')
                end = ai_content.rfind('}') + 1
                json_str = ai_content[start:end]
                analysis = json.loads(json_str)
                return analysis
            except:
                # 如果JSON解析失败，返回默认值
                return {
                    "first_paragraph": f"Sorry, could not retrieve the first paragraph of {book_title} by {author}. This is a placeholder text for analysis purposes.",
                    "cefr_level": user_level,
                    "estimated_vocabulary": 6000,
                    "formal_models": ["literary analysis", "narrative structure", "character development"],
                    "book_talk": f"{book_title} by {author} is a compelling work that offers rich opportunities for language learning and literary appreciation."
                }
        else:
            raise Exception(f"OpenAI API error: {response.status_code}")

    except Exception as e:
        print(f"AI analysis error: {str(e)}")
        # 返回默认分析
        return {
            "first_paragraph": f"Unable to analyze {book_title} by {author} at this time. Please try again later.",
            "cefr_level": user_level,
            "estimated_vocabulary": 6000,
            "formal_models": ["literary analysis", "narrative structure"],
            "book_talk": f"We're currently unable to provide a detailed analysis of {book_title}, but it remains an interesting choice for language learners."
        }

def openai_english_text_to_speech(text: str, filename: str) -> str:
    """使用OpenAI TTS生成英文语音（ElevenLabs备用方案）"""

    url = "https://api.openai.com/v1/audio/speech"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "tts-1",
        "input": text,
        "voice": "alloy",  # 适合英文的声音
        "response_format": "mp3",
        "speed": 1.0
    }

    try:
        print(f"使用OpenAI TTS生成英文语音（ElevenLabs备用）...")
        response = requests.post(url, json=data, headers=headers)
        print(f"OpenAI TTS响应状态: {response.status_code}")
        response.raise_for_status()

        audio_path = f"audio/{filename}.mp3"
        with open(audio_path, "wb") as f:
            f.write(response.content)

        print(f"英文音频文件已保存: {audio_path}")

        # 上传到Cloudinary
        cloudinary_url = upload_to_cloudinary(audio_path, filename)
        return cloudinary_url
    except Exception as e:
        print(f"OpenAI TTS错误: {str(e)}")
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

@app.post("/api/register", response_model=RegisterResponse)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 验证用户名长度和格式
    if len(user_data.username) < 3 or len(user_data.username) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be between 3-20 characters"
        )

    # 验证密码强度
    if len(user_data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )

    # 检查用户名是否已存在
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # 检查邮箱是否已存在
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        # 提供更详细的错误信息
        if existing_user.is_email_verified == 'true':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email address is already registered and verified. Please use a different email or try logging in."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email address is already registered but not verified. Please check your email for the verification link or contact support."
            )

    # 创建新用户
    user = create_user(db, user_data.username, user_data.email, user_data.password)

    # 生成邮箱验证token
    verification_token = generate_verification_token()
    update_verification_token(db, user, verification_token)

    # 发送验证邮件
    try:
        email_sent = send_verification_email(user.email, user.username, verification_token)

        if email_sent:
            return {
                "success": True,
                "message": "Registration successful! Please check your email and click the verification link to complete registration.",
                "email_sent": True,
                "user_id": user.id
            }
        else:
            # 邮件发送失败，直接验证用户
            verify_user_email(db, user)

            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user.username}, expires_delta=access_token_expires
            )

            return {
                "success": True,
                "message": "Registration successful! (Email service unavailable, account auto-verified)",
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "created_at": user.created_at.isoformat()
                }
            }

    except Exception as e:
        print(f"Email sending error: {str(e)}")
        # 如果邮件发送失败，直接验证用户
        verify_user_email(db, user)

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )

        return {
            "success": True,
            "message": "Registration successful! (Email service unavailable, account auto-verified)",
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
            detail="Incorrect username or password"
        )

    # 检查邮箱是否已验证
    if user.is_email_verified != 'true':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先验证你的邮箱地址。检查你的邮箱中的验证链接。"
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

@app.get("/api/check-email")
async def check_email_availability(email: str, db: Session = Depends(get_db)):
    """检查邮箱是否可用"""
    existing_user = get_user_by_email(db, email)
    if existing_user:
        return {
            "available": False,
            "verified": existing_user.is_email_verified == 'true',
            "message": "This email address is already registered" + (
                " and verified" if existing_user.is_email_verified == 'true' else " but not verified"
            )
        }
    return {
        "available": True,
        "message": "Email address is available"
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

@app.get("/api/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """邮箱验证端点"""
    user = get_user_by_verification_token(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的验证链接或链接已过期"
        )

    if user.is_email_verified == 'true':
        # 已经验证过，生成访问令牌并自动登录
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Email Already Verified - SHH-ELF</title>
            <style>
                body { font-family: 'Courier New', monospace; background: #000; color: #00ff00; text-align: center; padding: 50px; }
                .container { max-width: 600px; margin: 0 auto; border: 2px solid #00ff00; padding: 40px; background: #111; }
                .header { font-size: 24px; margin-bottom: 30px; text-transform: uppercase; }
                .message { margin-bottom: 30px; line-height: 1.6; }
                .button { display: inline-block; background: #00ff00; color: #000; padding: 15px 30px; text-decoration: none; text-transform: uppercase; font-weight: bold; margin: 10px; cursor: pointer; border: none; font-family: 'Courier New', monospace; }
                .button:hover { background: #008000; }
                .lang-toggle { position: absolute; top: 20px; right: 20px; background: transparent; border: 2px solid #00ff00; color: #00ff00; padding: 8px 16px; cursor: pointer; font-family: 'Courier New', monospace; }
                .lang-toggle:hover { background: #00ff00; color: #000; }
            </style>
            <script>
                let currentLang = 'en';

                const translations = {
                    en: {
                        title: 'Email Already Verified - SHH-ELF',
                        header: '✅ Email Already Verified',
                        message1: 'Your email has already been verified!',
                        message2: 'Redirecting to SHH-ELF in 3 seconds...',
                        button: 'Go to SHH-ELF Now',
                        langToggle: '中文'
                    },
                    zh: {
                        title: '邮箱已验证 - SHH-ELF',
                        header: '✅ 邮箱已验证',
                        message1: '你的邮箱已经验证过了！',
                        message2: '3秒后自动跳转到 SHH-ELF...',
                        button: '立即前往 SHH-ELF',
                        langToggle: 'English'
                    }
                };

                function updateLanguage() {
                    const t = translations[currentLang];
                    document.title = t.title;
                    document.getElementById('header').textContent = t.header;
                    document.getElementById('message1').textContent = t.message1;
                    document.getElementById('message2').textContent = t.message2;
                    document.getElementById('button').textContent = t.button;
                    document.getElementById('langToggle').textContent = t.langToggle;
                }

                function toggleLanguage() {
                    currentLang = currentLang === 'en' ? 'zh' : 'en';
                    updateLanguage();
                }

                window.onload = function() {
                    updateLanguage();

                    // Auto-login user with token
                    const urlParams = new URLSearchParams(window.location.search);
                    const token = urlParams.get('token');
                    const userData = urlParams.get('user');

                    if (token && userData) {
                        try {
                            const user = JSON.parse(decodeURIComponent(userData));
                            localStorage.setItem('authToken', token);
                            localStorage.setItem('currentUser', JSON.stringify(user));
                            console.log('Auto-login successful:', user.username);
                        } catch (e) {
                            console.error('Auto-login failed:', e);
                        }
                    }

                    setTimeout(function() {
                        window.location.href = 'https://hz2784.github.io/shh-elf/';
                    }, 3000);
                };
            </script>
        </head>
        <body>
            <button class="lang-toggle" id="langToggle" onclick="toggleLanguage()">中文</button>
            <div class="container">
                <div class="header" id="header">✅ Email Already Verified</div>
                <div class="message">
                    <p id="message1">Your email has already been verified!</p>
                    <p id="message2">Redirecting to SHH-ELF in 3 seconds...</p>
                </div>
                <a href="https://hz2784.github.io/shh-elf/" class="button" id="button">Go to SHH-ELF Now</a>
            </div>
        </body>
        </html>
        """

        # 准备用户数据
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at.isoformat()
        }

        # 在HTML中添加token和用户数据参数
        html_content = html_content.replace(
            'https://hz2784.github.io/shh-elf/',
            f'https://hz2784.github.io/shh-elf/?token={access_token}&user={urllib.parse.quote(json.dumps(user_data))}'
        )

        return HTMLResponse(content=html_content)

    # 验证邮箱
    verify_user_email(db, user)

    # 为新验证的用户生成访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # 发送欢迎邮件
    send_welcome_email(user.email, user.username)

    # 返回成功页面 - 默认英文，可切换中文
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Email Verification Success - SHH-ELF</title>
        <style>
            body { font-family: 'Courier New', monospace; background: #000; color: #00ff00; text-align: center; padding: 50px; }
            .container { max-width: 600px; margin: 0 auto; border: 2px solid #00ff00; padding: 40px; background: #111; }
            .header { font-size: 24px; margin-bottom: 30px; text-transform: uppercase; }
            .message { margin-bottom: 30px; line-height: 1.6; }
            .button { display: inline-block; background: #00ff00; color: #000; padding: 15px 30px; text-decoration: none; text-transform: uppercase; font-weight: bold; margin: 10px; cursor: pointer; border: none; font-family: 'Courier New', monospace; }
            .button:hover { background: #008000; }
            .success { color: #00ff00; font-size: 48px; margin-bottom: 20px; }
            .lang-toggle { position: absolute; top: 20px; right: 20px; background: transparent; border: 2px solid #00ff00; color: #00ff00; padding: 8px 16px; cursor: pointer; font-family: 'Courier New', monospace; }
            .lang-toggle:hover { background: #00ff00; color: #000; }
        </style>
        <script>
            let currentLang = 'en';
            let redirectTimer;

            const translations = {
                en: {
                    title: 'Email Verification Success - SHH-ELF',
                    header: 'Email Verification Successful!',
                    welcome: 'Welcome to SHH-ELF!',
                    feature1: 'Save recommendation history',
                    feature2: 'View all recommendations',
                    feature3: 'Share personalized content',
                    redirect: 'Redirecting in 5 seconds...',
                    button: 'Start Using SHH-ELF',
                    langToggle: '中文'
                },
                zh: {
                    title: '邮箱验证成功 - SHH-ELF',
                    header: '邮箱验证成功！',
                    welcome: '欢迎来到 SHH-ELF！',
                    feature1: '保存推荐历史',
                    feature2: '查看所有推荐',
                    feature3: '分享个性化内容',
                    redirect: '5秒后自动跳转...',
                    button: '开始使用 SHH-ELF',
                    langToggle: 'English'
                }
            };

            function updateLanguage() {
                const t = translations[currentLang];
                document.title = t.title;
                document.getElementById('header').textContent = t.header;
                document.getElementById('welcome').textContent = t.welcome;
                document.getElementById('intro').textContent = currentLang === 'en' ? 'You can now enjoy full features:' : '现在你可以享受完整功能：';
                document.getElementById('feature1').textContent = t.feature1;
                document.getElementById('feature2').textContent = t.feature2;
                document.getElementById('feature3').textContent = t.feature3;
                document.getElementById('redirect').textContent = t.redirect;
                document.getElementById('button').textContent = t.button;
                document.getElementById('langToggle').textContent = t.langToggle;
            }

            function toggleLanguage() {
                currentLang = currentLang === 'en' ? 'zh' : 'en';
                updateLanguage();
            }

            function startRedirect() {
                redirectTimer = setTimeout(function() {
                    window.location.href = 'https://hz2784.github.io/shh-elf/';
                }, 5000);
            }

            window.onload = function() {
                updateLanguage();

                // Auto-login user with token
                const urlParams = new URLSearchParams(window.location.search);
                const token = urlParams.get('token');
                const userData = urlParams.get('user');

                if (token && userData) {
                    try {
                        const user = JSON.parse(decodeURIComponent(userData));
                        localStorage.setItem('authToken', token);
                        localStorage.setItem('currentUser', JSON.stringify(user));
                        console.log('Auto-login successful:', user.username);
                    } catch (e) {
                        console.error('Auto-login failed:', e);
                    }
                }

                startRedirect();
            };
        </script>
    </head>
    <body>
        <button class="lang-toggle" id="langToggle" onclick="toggleLanguage()">中文</button>
        <div class="container">
            <div class="success">🎉</div>
            <div class="header" id="header">Email Verification Successful!</div>
            <div class="message">
                <p id="welcome">Welcome to SHH-ELF!</p>
                <p id="intro">You can now enjoy full features:</p>
                <ul style="text-align: left; max-width: 350px; margin: 20px auto;">
                    <li id="feature1">Save recommendation history</li>
                    <li id="feature2">View all recommendations</li>
                    <li id="feature3">Share personalized content</li>
                </ul>
                <p id="redirect" style="margin-top: 30px;">Redirecting in 5 seconds...</p>
            </div>
            <a href="https://hz2784.github.io/shh-elf/" class="button" id="button">Start Using SHH-ELF</a>
        </div>
    </body>
    </html>
    """

    # 准备用户数据
    user_data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat()
    }

    # 在HTML中添加token和用户数据参数
    html_content = html_content.replace(
        'https://hz2784.github.io/shh-elf/',
        f'https://hz2784.github.io/shh-elf/?token={access_token}&user={urllib.parse.quote(json.dumps(user_data))}'
    )

    return HTMLResponse(content=html_content)

@app.post("/api/resend-verification")
async def resend_verification(username: str, db: Session = Depends(get_db)):
    """重新发送验证邮件"""
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    if user.is_email_verified == 'true':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已经验证过了"
        )

    # 生成新的验证token
    verification_token = generate_verification_token()
    update_verification_token(db, user, verification_token)

    # 发送验证邮件
    email_sent = send_verification_email(user.email, user.username, verification_token)

    if email_sent:
        return {"success": True, "message": "验证邮件已重新发送"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送验证邮件失败"
        )

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
    # Check if share_id exists in memory store (audio files are on Cloudinary now)
    if share_id not in share_language_store:
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
                    <source src="https://res.cloudinary.com/dpao9jg0k/video/upload/shh-elf-audio/rec_{share_id}.mp3" type="audio/mpeg">
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
                    <source src="https://res.cloudinary.com/dpao9jg0k/video/upload/shh-elf-audio/rec_{share_id}.mp3" type="audio/mpeg">
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
    # Check if share_id exists in memory store
    if share_id not in share_language_store:
        raise HTTPException(status_code=404, detail="推荐不存在")

    # Audio is now on Cloudinary, construct URL
    audio_url = f"https://res.cloudinary.com/dpao9jg0k/video/upload/shh-elf-audio/rec_{share_id}.mp3"

    return {
        "success": True,
        "share_id": share_id,
        "audio_url": audio_url,
        "message": "推荐存在"
    }

@app.get("/api/book-gallery")
async def get_book_gallery(db: Session = Depends(get_db)):
    """获取书籍画廊列表"""
    try:
        # For MVP, return sample data
        books = []
        for book_data in SAMPLE_BOOKS:
            book = {
                "id": len(books) + 1,
                "title": book_data["title"],
                "author": book_data["author"],
                "isbn": book_data["isbn"],
                "cover_url": f"https://covers.openlibrary.org/b/isbn/{book_data['isbn']}-L.jpg",
                "cefr_level": book_data["cefr_level"],
                "estimated_vocabulary": book_data["estimated_vocabulary"],
                "formal_models": book_data["formal_models"],
                "sample_paragraph": book_data["sample_paragraph"],
                "sample_audio_path": get_book_audio_url(db, book_data['isbn'], 'sample'),
                "book_talk_text": book_data["book_talk_text"],
                "book_talk_audio_path": get_book_audio_url(db, book_data['isbn'], 'talk'),
                "genre": book_data["genre"],
                "publication_year": book_data["publication_year"],
                "page_count": book_data["page_count"],
                "goodreads_rating": book_data["goodreads_rating"]
            }
            books.append(book)

        # Check if audio cache needs regeneration
        audio_cache_empty = not cloudinary_audio_cache

        response = {
            "success": True,
            "books": books,
            "total": len(books)
        }

        # Add cache status for frontend auto-detection
        if audio_cache_empty:
            response["audio_cache_empty"] = True
            response["regeneration_url"] = "/api/generate-gallery-audio"

        return response
    except Exception as e:
        print(f"Book gallery error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/book-gallery/{book_id}")
async def get_book_detail(book_id: int, db: Session = Depends(get_db)):
    """获取单本书详细信息"""
    try:
        if book_id < 1 or book_id > len(SAMPLE_BOOKS):
            raise HTTPException(status_code=404, detail="Book not found")

        book_data = SAMPLE_BOOKS[book_id - 1]
        book = {
            "id": book_id,
            "title": book_data["title"],
            "author": book_data["author"],
            "isbn": book_data["isbn"],
            "cover_url": f"https://covers.openlibrary.org/b/isbn/{book_data['isbn']}-L.jpg",
            "cefr_level": book_data["cefr_level"],
            "estimated_vocabulary": book_data["estimated_vocabulary"],
            "formal_models": book_data["formal_models"],
            "sample_paragraph": book_data["sample_paragraph"],
            "sample_audio_path": get_book_audio_url(db, book_data['isbn'], 'sample'),
            "book_talk_text": book_data["book_talk_text"],
            "book_talk_audio_path": get_book_audio_url(db, book_data['isbn'], 'talk'),
            "genre": book_data["genre"],
            "publication_year": book_data["publication_year"],
            "page_count": book_data["page_count"],
            "goodreads_rating": book_data["goodreads_rating"]
        }

        return {
            "success": True,
            "book": book
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Book detail error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-gallery-audio")
@app.get("/api/generate-gallery-audio")
async def generate_gallery_audio(db: Session = Depends(get_db)):
    """为书籍画廊生成示例音频（管理员功能）"""
    try:
        generated_files = []

        for book_data in SAMPLE_BOOKS:
            # Generate sample paragraph audio
            sample_filename = f"gallery_sample_{book_data['isbn']}"
            sample_audio = text_to_speech(
                book_data["sample_paragraph"],
                sample_filename,
                "English"
            )
            generated_files.append(sample_audio)
            # Cache URL in memory
            cloudinary_audio_cache[f"sample_{book_data['isbn']}"] = sample_audio

            # Generate book talk audio
            talk_filename = f"gallery_talk_{book_data['isbn']}"
            talk_audio = text_to_speech(
                book_data["book_talk_text"],
                talk_filename,
                "English"
            )
            generated_files.append(talk_audio)
            # Cache URL in memory
            cloudinary_audio_cache[f"talk_{book_data['isbn']}"] = talk_audio

        return {
            "success": True,
            "message": f"Generated {len(generated_files)} audio files for book gallery",
            "files": generated_files
        }
    except Exception as e:
        print(f"Gallery audio generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audio/{filename}")
async def get_audio_file(filename: str):
    """获取音频文件，带有 CORS 支持"""
    audio_path = Path(f"audio/{filename}")

    if not audio_path.exists() or not filename.endswith('.mp3'):
        raise HTTPException(status_code=404, detail="Audio file not found")

    # 返回文件响应，带有 CORS 头
    response = FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=filename
    )

    # 添加 CORS 头
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET"
    response.headers["Access-Control-Allow-Headers"] = "*"

    return response

@app.post("/api/discover-book")
async def discover_book(request: BookDiscoveryRequest, current_user: User = Depends(get_current_user_optional)):
    """Discovery功能：分析用户输入的任意书籍"""
    try:
        # 生成分析ID
        import hashlib
        analysis_id = hashlib.md5(f"{request.book_title}_{request.author}_{request.user_level}".encode()).hexdigest()[:12]

        # 检查缓存
        if analysis_id in discovery_cache:
            print(f"返回缓存的分析结果: {analysis_id}")
            return discovery_cache[analysis_id]

        print(f"开始分析新书: {request.book_title} by {request.author}")

        # 使用AI分析书籍
        analysis = analyze_book_with_ai(request.book_title, request.author, request.user_level)

        # 生成音频文件
        sample_filename = f"discovery_sample_{analysis_id}"
        sample_audio_url = text_to_speech(analysis["first_paragraph"], sample_filename, "English")

        talk_filename = f"discovery_talk_{analysis_id}"
        talk_audio_url = text_to_speech(analysis["book_talk"], talk_filename, "English")

        # 构建响应
        response = BookDiscoveryResponse(
            success=True,
            book_title=request.book_title,
            author=request.author,
            first_paragraph=analysis["first_paragraph"],
            sample_audio_url=sample_audio_url,
            book_talk_text=analysis["book_talk"],
            book_talk_audio_url=talk_audio_url,
            cefr_level=analysis["cefr_level"],
            estimated_vocabulary=analysis["estimated_vocabulary"],
            formal_models=analysis["formal_models"],
            analysis_id=analysis_id
        )

        # 缓存结果
        discovery_cache[analysis_id] = response

        print(f"书籍分析完成: {request.book_title}")
        return response

    except Exception as e:
        print(f"Discovery error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Book discovery failed: {str(e)}")

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

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv
import hashlib
from pathlib import Path

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

# 挂载音频文件服务
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

class RecommendationResponse(BaseModel):
    success: bool
    recommendation_text: str
    audio_path: str
    share_id: str

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

# ElevenLabs文本转语音
def text_to_speech(text: str, filename: str, language: str) -> str:
    """使用ElevenLabs将文本转换为语音"""
    
    voice_id = "9BWtsMINqrJLrRacOk9x"  # Aria voice
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    print(f"=== 语音生成调试信息 ===")
    print(f"文本: {text}")
    print(f"文件名: {filename}")
    print(f"语言: {language}")
        
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
        response = requests.post(url, json=data, headers=headers)
        print(f"ElevenLabs响应状态: {response.status_code}")
        response.raise_for_status()
        
        audio_path = f"audio/{filename}.mp3"
        with open(audio_path, "wb") as f:
            f.write(response.content)
        
        print(f"音频文件已保存: {audio_path}")
        return audio_path
    except Exception as e:
        print(f"语音生成错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"语音生成错误: {str(e)}")

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

@app.post("/api/generate-recommendation", response_model=RecommendationResponse)
async def generate_recommendation(req: BookRecommendation):
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
        
        # 生成唯一文件名
        content_hash = hashlib.md5(
            f"{req.book_title}{req.recipient_name}{recommendation_text}".encode()
        ).hexdigest()[:8]
        filename = f"rec_{content_hash}"
        
        # 生成语音文件
        audio_path = text_to_speech(recommendation_text, filename, req.language)
        
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
    """分享推荐页面"""
    audio_file = f"audio/rec_{share_id}.mp3"
    if not os.path.exists(audio_file):
        raise HTTPException(status_code=404, detail="推荐不存在")

    # Read the share.html content and inject the share_id
    try:
        with open("share.html", "r", encoding="utf-8") as f:
            html_content = f.read()

        # Replace the API_BASE_URL and ensure it points to current domain
        html_content = html_content.replace(
            "const API_BASE_URL = 'https://shh-elf.onrender.com';",
            f"const API_BASE_URL = window.location.origin;"
        )

        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Share page not found")

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

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv
import json
import hashlib
from pathlib import Path

# 加载环境变量
load_dotenv()

app = FastAPI(title="Shh-elf", description="AI-powered personalized book recommendations in audio format")

# 创建静态文件目录
Path("static").mkdir(exist_ok=True)
Path("audio").mkdir(exist_ok=True)

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

# GPT生成推荐文本
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

# ElevenLabs文本转语音
def text_to_speech(text: str, filename: str, language: str) -> str:
    voice_id = "9BWtsMINqrJLrRacOk9x"  # Aria
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    # 调试信息
    print(f"=== 调试信息 ===")
    print(f"API Key: {ELEVENLABS_API_KEY}")
    print(f"Voice ID: {voice_id}")
    print(f"Text: {text}")
    
    # 截断文本到前30个字符
    # text = text[:30] # 只保留前10个字符，不加...

    print(f"截断后Text: {text}")
    
    print(f"URL: {url}")
        
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
    
    print(f"Headers: {headers}")
    print(f"Data: {data}")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")
        response.raise_for_status()
        
        audio_path = f"audio/{filename}.mp3"
        with open(audio_path, "wb") as f:
            f.write(response.content)
        
        return audio_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音生成错误: {str(e)}")


# 主页
@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Shh-elf - AI Book Recommendations</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
            .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; color: #34495e; }
            input, textarea, select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; }
            button { background: #3498db; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #2980b9; }
            .loading { display: none; text-align: center; margin: 20px 0; }
            .result { margin-top: 30px; display: none; }
            .audio-player { margin: 20px 0; }
            .share-section { margin-top: 20px; padding: 15px; background: #ecf0f1; border-radius: 5px; }
            .language-switcher { position: fixed; bottom: 20px; right: 20px; background: #34495e; color: white; padding: 10px 15px; border-radius: 25px; cursor: pointer; font-size: 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.3); }
            .language-switcher:hover { background: #2c3e50; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 id="title">🎧 Shh-elf</h1>
            <p id="subtitle" style="text-align: center; color: #7f8c8d; margin-bottom: 30px;">
                Transform book recommendations into personalized audio messages
            </p>
            
            <form id="recommendationForm">
                <div class="form-group">
                    <label for="book_title" id="label-book">Book Title:</label>
                    <input type="text" id="book_title" name="book_title" required 
                           placeholder="e.g., Harry Potter and the Philosopher's Stone">
                </div>
                
                <div class="form-group">
                    <label for="recipient_name" id="label-recipient">Recommend to:</label>
                    <input type="text" id="recipient_name" name="recipient_name" required 
                           placeholder="e.g., Sarah">
                </div>
                
                <div class="form-group">
                    <label for="relationship" id="label-relationship">Your relationship:</label>
                    <select id="relationship" name="relationship">
                        <option value="friend">Friend</option>
                        <option value="classmate">Classmate</option>
                        <option value="colleague">Colleague</option>
                        <option value="family">Family</option>
                        <option value="student">Student</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="recipient_interests" id="label-interests">Their interests (optional):</label>
                    <textarea id="recipient_interests" name="recipient_interests" rows="3" 
                              placeholder="e.g., loves sci-fi, mystery novels, enjoys movies..."></textarea>
                </div>
                
                <div class="form-group">
                    <label for="language" id="label-language">Language:</label>
                    <select id="language" name="language">
                        <option value="English">🇺🇸 English</option>
                        <option value="中文">🇨🇳 中文</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="tone" id="label-tone">Recommendation tone:</label>
                    <select id="tone" name="tone">
                        <option value="friendly and enthusiastic">Friendly & Enthusiastic</option>
                        <option value="professional and objective">Professional & Objective</option>
                        <option value="casual and humorous">Casual & Humorous</option>
                        <option value="warm and caring">Warm & Caring</option>
                    </select>
                </div>
                
                <button type="submit" id="submit-btn">🎙️ Generate Audio Recommendation</button>
            </form>
            
            <div class="loading" id="loading">
                <p id="loading-text1">🤖 AI is generating personalized recommendation...</p>
                <p id="loading-text2">⏳ Estimated time: 10-15 seconds</p>
            </div>
            
            <div class="result" id="result">
                <h3 id="success-title">🎉 Recommendation Generated Successfully!</h3>
                <div class="audio-player">
                    <audio controls style="width: 100%;" id="audioPlayer">
                        Your browser does not support audio playback.
                    </audio>
                </div>
                <div class="share-section">
                    <h4 id="share-title">📱 Share Link:</h4>
                    <input type="text" id="shareUrl" readonly style="background: #f8f9fa;">
                    <button onclick="copyToClipboard()" id="copy-btn" style="margin-top: 10px;">📋 Copy Link</button>
                </div>
            </div>
        </div>

        <!-- Language Switcher -->
        <div class="language-switcher" onclick="toggleLanguage()">
            <span id="lang-switch">🇨🇳 中文</span>
        </div>

        <script>
            // Language data
            const translations = {
                en: {
                    title: "🎧 Shh-elf",
                    subtitle: "Transform book recommendations into personalized audio messages",
                    'label-book': "Book Title:",
                    'label-recipient': "Recommend to:",
                    'label-relationship': "Your relationship:",
                    'label-interests': "Their interests (optional):",
                    'label-language': "Language:",
                    'label-tone': "Recommendation tone:",
                    'submit-btn': "🎙️ Generate Audio Recommendation",
                    'loading-text1': "🤖 AI is generating personalized recommendation...",
                    'loading-text2': "⏳ Estimated time: 10-15 seconds",
                    'success-title': "🎉 Recommendation Generated Successfully!",
                    'share-title': "📱 Share Link:",
                    'copy-btn': "📋 Copy Link",
                    'lang-switch': "🇨🇳 中文",
                    placeholders: {
                        book: "e.g., Harry Potter and the Philosopher's Stone",
                        recipient: "e.g., Sarah",
                        interests: "e.g., loves sci-fi, mystery novels, enjoys movies..."
                    },
                    relationships: ["Friend", "Classmate", "Colleague", "Family", "Student"],
                    relationshipValues: ["friend", "classmate", "colleague", "family", "student"],
                    tones: ["Friendly & Enthusiastic", "Professional & Objective", "Casual & Humorous", "Warm & Caring"],
                    toneValues: ["friendly and enthusiastic", "professional and objective", "casual and humorous", "warm and caring"]
                },
                zh: {
                    title: "🎧 Shh-elf",
                    subtitle: "将书籍推荐转换为个性化语音消息",
                    'label-book': "书籍名称：",
                    'label-recipient': "推荐给谁：",
                    'label-relationship': "你们的关系：",
                    'label-interests': "TA的兴趣爱好（可选）：",
                    'label-language': "语言：",
                    'label-tone': "推荐语调：",
                    'submit-btn': "🎙️ 生成语音推荐",
                    'loading-text1': "🤖 AI正在生成个性化推荐...",
                    'loading-text2': "⏳ 预计需要10-15秒",
                    'success-title': "🎉 推荐生成成功！",
                    'share-title': "📱 分享链接：",
                    'copy-btn': "📋 复制链接",
                    'lang-switch': "🇺🇸 English",
                    placeholders: {
                        book: "例如：哈利波特与魔法石",
                        recipient: "例如：小明",
                        interests: "例如：喜欢科幻、悬疑，平时爱看电影..."
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
                
                // Update text content
                document.getElementById('title').textContent = t.title;
                document.getElementById('subtitle').textContent = t.subtitle;
                document.getElementById('label-book').textContent = t['label-book'];
                document.getElementById('label-recipient').textContent = t['label-recipient'];
                document.getElementById('label-relationship').textContent = t['label-relationship'];
                document.getElementById('label-interests').textContent = t['label-interests'];
                document.getElementById('label-language').textContent = t['label-language'];
                document.getElementById('label-tone').textContent = t['label-tone'];
                document.getElementById('submit-btn').textContent = t['submit-btn'];
                document.getElementById('loading-text1').textContent = t['loading-text1'];
                document.getElementById('loading-text2').textContent = t['loading-text2'];
                document.getElementById('success-title').textContent = t['success-title'];
                document.getElementById('share-title').textContent = t['share-title'];
                document.getElementById('copy-btn').textContent = t['copy-btn'];
                document.getElementById('lang-switch').textContent = t['lang-switch'];
                
                // Update placeholders
                document.getElementById('book_title').placeholder = t.placeholders.book;
                document.getElementById('recipient_name').placeholder = t.placeholders.recipient;
                document.getElementById('recipient_interests').placeholder = t.placeholders.interests;
                
                // Update dropdown options
                const relationshipSelect = document.getElementById('relationship');
                relationshipSelect.innerHTML = '';
                t.relationships.forEach((rel, i) => {
                    const option = document.createElement('option');
                    option.value = t.relationshipValues[i];
                    option.textContent = rel;
                    relationshipSelect.appendChild(option);
                });
                
                const toneSelect = document.getElementById('tone');
                toneSelect.innerHTML = '';
                t.tones.forEach((tone, i) => {
                    const option = document.createElement('option');
                    option.value = t.toneValues[i];
                    option.textContent = tone;
                    toneSelect.appendChild(option);
                });
            }

            document.getElementById('recommendationForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                // 显示加载状态
                document.getElementById('loading').style.display = 'block';
                document.getElementById('result').style.display = 'none';
                
                // 收集表单数据
                const formData = {
                    book_title: document.getElementById('book_title').value,
                    recipient_name: document.getElementById('recipient_name').value,
                    relationship: document.getElementById('relationship').value,
                    recipient_interests: document.getElementById('recipient_interests').value,
                    tone: document.getElementById('tone').value,
                    language: document.getElementById('language').value
                };
                
                try {
                    // 调用API
                    const response = await fetch('/generate-recommendation', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(formData)
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        // 显示结果
                        document.getElementById('loading').style.display = 'none';
                        document.getElementById('result').style.display = 'block';
                        
                        // 设置音频
                        const audioPlayer = document.getElementById('audioPlayer');
                        audioPlayer.src = '/' + result.audio_path;
                        
                        // 设置分享链接
                        const shareUrl = window.location.origin + '/share/' + result.share_id;
                        document.getElementById('shareUrl').value = shareUrl;
                        
                    } else {
                        alert('Generation failed: ' + result.detail);
                        document.getElementById('loading').style.display = 'none';
                    }
                } catch (error) {
                    alert('Network error: ' + error.message);
                    document.getElementById('loading').style.display = 'none';
                }
            });
            
            function copyToClipboard() {
                const shareUrl = document.getElementById('shareUrl');
                shareUrl.select();
                document.execCommand('copy');
                const t = translations[currentLang];
                alert(currentLang === 'en' ? 'Link copied to clipboard!' : '链接已复制到剪贴板！');
            }

            // Initialize with English
            updateLanguage();
        </script>
    </body>
    </html>
    """

# 生成推荐API
@app.post("/generate-recommendation")
async def generate_recommendation(req: BookRecommendation):
    try:
        # 生成推荐文本
        recommendation_text = generate_recommendation_text(
            req.book_title, 
            req.recipient_name, 
            req.relationship,
            req.recipient_interests,
            req.tone,
            req.language
        )
        
        # 生成文件名（使用hash避免重复）
        content_hash = hashlib.md5(
            f"{req.book_title}{req.recipient_name}{recommendation_text}".encode()
        ).hexdigest()[:8]
        filename = f"rec_{content_hash}"
        
        # 生成语音
        audio_path = text_to_speech(recommendation_text, filename, req.language)
        
        return {
            "success": True,
            "recommendation_text": recommendation_text,
            "audio_path": audio_path,
            "share_id": content_hash
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 分享页面
@app.get("/share/{share_id}")
async def share_recommendation(share_id: str):
    audio_file = f"audio/rec_{share_id}.mp3"
    if not os.path.exists(audio_file):
        raise HTTPException(status_code=404, detail="推荐不存在")
    
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>书籍推荐分享 - Shh-elf</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
            .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
            h1 {{ color: #2c3e50; }}
            .audio-player {{ margin: 30px 0; }}
            .cta {{ margin-top: 30px; }}
            .cta a {{ background: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎧 有人给你推荐了一本书</h1>
            <p>点击播放，听听这个个性化的推荐：</p>
            <div class="audio-player">
                <audio controls style="width: 100%;">
                    <source src="/audio/rec_{share_id}.mp3" type="audio/mpeg">
                    您的浏览器不支持音频播放。
                </audio>
            </div>
            <div class="cta">
                <a href="/">🎙️ 我也要创建推荐</a>
            </div>
        </div>
    </body>
    </html>
    """)

# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Shh-elf is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

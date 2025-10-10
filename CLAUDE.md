# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SHH-ELF is an AI-powered book recommendation platform that generates personalized audio book recommendations. The system consists of a FastAPI backend and a retro-themed frontend with Y2K/terminal aesthetics.

## Architecture

- **Backend**: FastAPI application (`main.py`) that provides REST API endpoints
- **Frontend**: Single-page HTML application (`index.html`) with terminal/Y2K styling
- **Deployment**: Configured for Render.com hosting with Heroku-style deployment files

### Core Components

1. **API Service** (`main.py`):
   - Uses OpenAI GPT-4o-mini for text generation
   - Uses ElevenLabs API for text-to-speech conversion
   - Stores generated audio files locally in `/audio` directory
   - Provides endpoints for recommendation generation and sharing

2. **Frontend** (`index.html`):
   - Retro terminal interface with Matrix-style animations
   - Bilingual support (English/Chinese)
   - Form-based recommendation input with audio playback
   - Direct API integration with backend

## Common Development Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python main.py
# Or with uvicorn directly
uvicorn main:app --host=0.0.0.0 --port=8000 --reload

# Health check
curl http://localhost:8000/api/health
```

### Environment Variables Required
- `OPENAI_API_KEY`: OpenAI API key for GPT text generation
- `ELEVENLABS_API_KEY`: ElevenLabs API key for text-to-speech

### Testing Endpoints
- `GET /`: Root endpoint with API info
- `POST /api/generate-recommendation`: Main recommendation generation
- `GET /api/share/{share_id}`: Retrieve shared recommendations
- `GET /api/health`: Service health check

## Key Technical Details

### Audio Processing
- Audio files are saved as MP3 format in `/audio` directory
- Filenames use MD5 hash of content for deduplication: `rec_{hash}.mp3`
- ElevenLabs uses "Aria" voice (ID: 9BWtsMINqrJLrRacOk9x) with multilingual model

### Frontend Integration
- Backend URL configured in frontend JavaScript (currently `https://shh-elf.onrender.com`)
- CORS enabled for all origins (production should restrict this)
- Audio playback uses HTML5 audio element

### Data Models
- `BookRecommendation`: Input model for recommendation requests
- `RecommendationResponse`: Output model with text, audio path, and share ID

## Deployment Configuration

- **Procfile**: Heroku/Render deployment with uvicorn
- **runtime.txt**: Python 3.11.0 specified
- **GitHub Pages**: Static frontend deployment from root directory

When modifying this codebase, ensure API keys are properly configured and test both text generation and audio synthesis workflows.
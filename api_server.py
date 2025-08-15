from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from main import tools, chat_with_memory
from langsmith import traceable
import uuid
import whisper
import tempfile
import os
from fastapi.responses import JSONResponse

app = FastAPI(title="CallCenter Agent API", description="API for CallCenter AI Agent", version="1.0.0")

# # CORS middleware - frontenden gelen isteklere izin ver
app.add_middleware(
     CORSMiddleware,
     allow_origins=["*"],  # Üretimde sadece frontend URL'ini yazın
     allow_credentials=True,
     allow_methods=["*"],
     allow_headers=["*"],
 )

model = whisper.load_model("small")

# Request/Response modelleri
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    success: bool
    error: str = None

# Session management için basit bir cache
sessions = {}

@app.get("/")
async def root():
    """API durumu kontrolü"""
    return {"message": "CallCenter Agent API çalışıyor!", "status": "active"}

@app.post("/api/v1/chat", response_model=ChatResponse)
@traceable(name="api_chat_endpoint")
async def chat_with_agent(request: ChatRequest):
    """
    Ana chat endpoint - kullanıcı mesajını alır, AI agent'e gönderir ve yanıt döner
    Memory destekli - her session_id için konuşma geçmişi saklanır
    LangSmith ile izlenir
    """
    # Her API çağrısı için unique trace ID oluştur
    trace_id = str(uuid.uuid4())
    
    try:
        # Memory ile agent'e mesajı gönder
        response = await chat_with_memory(
            message=request.message,
            session_id=request.session_id
        )
        
        # Agent yanıtını çıkar
        agent_response = response.get("output", "Üzgünüm, bir hata oluştu.")
        
        return ChatResponse(
            response=agent_response,
            success=True
        )
        
    except Exception as e:
        print(f"API Hatası: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Agent işlenirken hata oluştu: {str(e)}"
        )

@app.get("/api/v1/health")
async def health_check():
    """Sistem sağlık kontrolü"""
    try:
        # Sadece temel kontroller yap, agent'i tetikleme
        return {
            "status": "healthy",
            "agent_status": "ready",
            "available_tools": len(tools),
            "server_status": "running"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/transcribe")
async def transcribe_audio(audio_data: UploadFile = File(...)):
    # Güvenli geçici dosya oluştur
    temp_dir = tempfile.gettempdir()
    temp_filename = os.path.join(temp_dir, f"temp_audio_{uuid.uuid4()}.webm")
    
    try:
        # Dosya içeriğini oku
        audio_content = await audio_data.read()
        
        # Geçici dosyaya yaz
        with open(temp_filename, "wb") as f:
            f.write(audio_content)
        
        # Dosyanın oluşturulduğunu kontrol et
        if not os.path.exists(temp_filename):
            raise FileNotFoundError(f"Geçici dosya oluşturulamadı: {temp_filename}")
        
        # Whisper ile transkript et
        result = model.transcribe(temp_filename, fp16=False, language="tr")
        transcribed_text = result['text']
        
        return {"text": transcribed_text.strip()}
        
    except FileNotFoundError as e:
        print(f"Dosya bulunamadı hatası: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Dosya hatası: {str(e)}"})
    except Exception as e:
        print(f"Transkripsiyon hatası: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Transkripsiyon hatası: {str(e)}"})
    finally:
        # Temizlik
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception as cleanup_error:
                print(f"Geçici dosya silinirken hata: {cleanup_error}")

@app.get("/api/v1/tools")
async def get_available_tools():
    """Kullanılabilir araçları listele"""
    tool_info = []
    for tool in tools:
        tool_info.append({
            "name": tool.name,
            "description": tool.description
        })
    
    return {
        "tools": tool_info,
        "count": len(tools)
    }

@app.delete("/api/v1/sessions/{session_id}")
async def clear_session_memory(session_id: str):
    """Belirli bir session'ın konuşmasını temizle"""
    from main import clear_session_memory
    if clear_session_memory(session_id):
        return {"message": f"Session {session_id} konuşma geçmişi temizlendi"}
    else:
        raise HTTPException(status_code=404, detail="Session bulunamadı")

if __name__ == "__main__":
    import uvicorn
    print("🚀 CallCenter Agent API başlatılıyor...")
    print("📋 API Dokümantasyonu: http://localhost:8081/docs")
    print("💬 Chat Endpoint: http://localhost:8081/api/v1/chat")
    print("🎤 Transcribe Endpoint: http://localhost:8081/transcribe")
    print("🧠 Memory: Sadece sohbet sırasındaki konuşmaları hatırlar")
    print("🗑️  Memory Temizleme: DELETE /api/v1/sessions/{id}")
    uvicorn.run(app, host="0.0.0.0", port=8080)

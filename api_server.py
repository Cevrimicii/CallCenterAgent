from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from main import agent_executor, tools, chat_with_memory
from langsmith import traceable
import uuid

app = FastAPI(title="CallCenter Agent API", description="API for CallCenter AI Agent", version="1.0.0")

# CORS middleware - frontenden gelen isteklere izin ver
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Üretimde sadece frontend URL'ini yazın
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        
        # LangSmith için metadata ekle
        metadata = {
            "session_id": request.session_id,
            "message_length": len(request.message),
            "response_length": len(agent_response),
            "trace_id": trace_id,
            "success": True
        }
        
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
    print("📋 API Dokümantasyonu: http://localhost:8080/docs")
    print("💬 Chat Endpoint: http://localhost:8080/api/v1/chat")
    print("🧠 Memory: Sadece sohbet sırasındaki konuşmaları hatırlar")
    print("🗑️  Memory Temizleme: DELETE /api/v1/sessions/{id}")
    uvicorn.run(app, host="0.0.0.0", port=8080)

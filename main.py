from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain.memory import ConversationBufferMemory
# from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langsmith import traceable
import httpx
import asyncio
from langchain.tools import Tool
# LangSmith konfigürasyonunu import et
# try:
#     from langsmith_config import setup_langsmith, create_langsmith_client
#     setup_langsmith()
#     langsmith_client = create_langsmith_client()
# except ImportError:
#     print("⚠️  langsmith_config.py bulunamadı - tracing olmadan devam ediliyor")
#     langsmith_client = None

final_answer = Tool(
    name="final_answer",
    description="Kullanıcıya doğrudan yanıt vermek için kullanılır.",
    func=lambda message: message,
    return_direct=True
)

@tool
@traceable(name="control_by_phonenumber")
async def control_by_phonenumber(phoneNumber: str) -> str:
    """
    Telefon numarası ile müşteri kaydını sorgular ve müşteri bilgilerini getirir.
    
    Args:
        phoneNumber (str): Sorgulanacak telefon numarası (örn: 05551234567)
        
    Returns:
        str: Müşteri bilgileri (JSON formatında) veya hata mesajı
        
    Kullanım: Müşterinin sistemde kayıtlı olup olmadığını kontrol etmek ve 
    mevcut müşteri bilgilerini almak için kullanılır.
    """
    try:
         async with httpx.AsyncClient() as client:
             url = f"http://localhost:8000/api/v1/users/phone/{phoneNumber}"
             response = await client.get(url)
             response.raise_for_status()
             return response.text
    except httpx.HTTPStatusError as e:
         if e.response.status_code == 404:
             return "Bu telefon numarasında kayıtlı müşteri bulunamadı."
         return f"Müşteri sorgulanamadı. HTTP {e.response.status_code} hatası."
    except Exception as e:
         return f"Sistem hatası: Müşteri bilgileri alınamadı - {type(e).__name__}"
    

@tool
@traceable(name="control_location_have_problem")
async def control_location_have_problem(location: str) -> str:
    """
    Belirtilen lokasyonda yaşanan teknik sorunları sorgular.
    
    Args:
        location (str): Sorgulanacak konum/bölge adı (örn: İstanbul, Ankara, Kadıköy)
        
    Returns:
        str: Bölgedeki aktif sorunlar listesi (JSON formatında) veya hata mesajı
        
    Kullanım: Müşterinin bulunduğu bölgede internet, hat veya sinyal sorunları olup
    olmadığını kontrol etmek için kullanılır. Müşteri bağlantı sorunu bildirdiğinde
    önce bölgesel arızaları kontrol etmek için kullanın.
    """
    try:
         async with httpx.AsyncClient() as client:
             url = f"http://localhost:8000/api/v1/problems/location/{location}"
             response = await client.get(url)
             response.raise_for_status()
             return response.text
    except httpx.HTTPStatusError as e:
         if e.response.status_code == 404:
             return f"{location} bölgesinde şu anda bilinen bir sorun bulunmuyor."
         return f"Bölgesel sorunlar sorgulanamadı. HTTP {e.response.status_code} hatası."
    except Exception as e:
         return f"Sistem hatası: Bölgesel sorun bilgileri alınamadı - {type(e).__name__}"

@tool
async def get_packages_by_type(package_type: str) ->str:
    """
    Paket türüne göre mevcut paketleri listeler.
    
    Args:
        package_type (str): Paket türü - 'mobil' (mobil internet/hat paketleri) veya 
                           'ev' (ev interneti paketleri)
        
    Returns:
        str: Belirtilen türdeki paketlerin listesi (JSON formatında) veya hata mesajı
        
    Kullanım: Müşteri belirli bir paket türü hakkında bilgi istediğinde kullanın.
    Sadece 'mobil' ve 'ev' değerlerini kabul eder.
    """
    # Geçerli paket türlerini kontrol et
    valid_types = ['mobil', 'ev']
    if package_type.lower() not in valid_types:
        return f"Geçersiz paket türü. Lütfen 'mobil' veya 'ev' türlerinden birini belirtin."
    
    try:
         async with httpx.AsyncClient() as client:
             url = f"http://localhost:8000/api/v1/packages/{package_type.lower()}"
             response = await client.get(url)
             response.raise_for_status()
             return response.text
    except httpx.HTTPStatusError as e:
         if e.response.status_code == 404:
             return f"{package_type} türünde paket bulunamadı."
         return f"Paketler sorgulanamadı. HTTP {e.response.status_code} hatası."
    except Exception as e:
         return f"Sistem hatası: Paket bilgileri alınamadı - {type(e).__name__}"


@tool
def request_user_info() -> str:
    """
    Yeni kullanıcı hesabı oluşturmak için gerekli bilgileri müşteriden talep eder.
    
    Returns:
        str: Müşteriye yönlendirilen bilgi talep mesajı
        
    Kullanım: Müşteri yeni hat açmak veya hesap oluşturmak istediğinde, 
    gerekli kişisel bilgileri toplamak için kullanın. Bu fonksiyondan sonra
    alınan bilgilerle post_new_user fonksiyonunu çağırın.
    """
    return """Yeni kullanıcı hesabı oluşturmak için aşağıdaki bilgilere ihtiyacım var:

📝 Gerekli Bilgiler:
1. **Ad ve Soyad**: Tam adınız
2. **Telefon Numarası**: 11 haneli telefon numaranız (örn: 05551234567)
3. **E-mail Adresi**: İletişim için e-mail adresiniz (isteğe bağlı)

Lütfen bu bilgileri paylaştığınızda hesabınızı hemen oluşturabilirim."""

@tool
async def post_new_user(name: str, phone: str, email: str = "") -> str:
    """
    Yeni kullanıcı hesabı oluşturur ve sisteme kaydeder.
    
    Args:
        name (str): Kullanıcının tam adı ve soyadı
        phone (str): 11 haneli telefon numarası (örn: 05551234567)
        email (str, optional): E-mail adresi (isteğe bağlı)
        
    Returns:
        str: Hesap oluşturma başarı mesajı veya hata açıklaması
        
    Kullanım: request_user_info ile müşteriden alınan bilgilerle yeni hesap oluşturmak için.
    Telefon numarası formatını kontrol edin ve gerekli validasyonları yapın.
    """
    # Basit telefon numarası validasyonu
    if not phone or len(phone.replace(" ", "").replace("-", "")) < 10:
        return "Geçersiz telefon numarası. Lütfen 11 haneli telefon numaranızı doğru formatta girin."
    
    if not name or len(name.strip()) < 2:
        return "Geçersiz ad bilgisi. Lütfen adınızı ve soyadınızı tam olarak girin."
    
    try:
        async with httpx.AsyncClient() as client:
            user_data = {
                "name": name.strip(),
                "phone": phone.replace(" ", "").replace("-", ""),
                "email": email.strip() if email else ""
            }
            response = await client.post("http://localhost:8000/api/v1/users", json=user_data)
            response.raise_for_status()
            return f"✅ Kullanıcı hesabınız başarıyla oluşturuldu!\n\n📋 Hesap Bilgileri:\n• Ad: {name}\n• Telefon: {phone}\n• E-mail: {email if email else 'Belirtilmedi'}\n\nArtık hizmetlerimizden faydalanabilirsiniz."
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            return "Bu telefon numarası zaten sistemimizde kayıtlı. Mevcut hesabınızla işlem yapmak için telefon numaranızı doğrulayabilirsiniz."
        elif e.response.status_code == 400:
            return "Girilen bilgilerde hata var. Lütfen telefon numarası ve ad bilgilerinizi kontrol edin."
        return f"Hesap oluşturulamadı. Sistem hatası (HTTP {e.response.status_code})"
    except Exception as e:
        return f"Sistem hatası: Hesap oluşturulamadı - {type(e).__name__}. Lütfen tekrar deneyin veya müşteri hizmetleri ile iletişime geçin."


@tool
async def get_all_package() -> str:
    """
    Şirketin tüm aktif paket ve tarife seçeneklerini listeler.
    
    Returns:
        str: Tüm paketlerin detaylı listesi (JSON formatında) veya hata mesajı
        
    Kullanım: Müşteri genel olarak "hangi paketler var?" veya "tüm seçenekleri göster" 
    dediğinde kullanın. Hem mobil hem ev interneti paketlerini kapsar.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/v1/packages")
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return "Şu anda aktif paket bulunamadı. Lütfen daha sonra tekrar deneyin."
        return f"Paket bilgileri alınamadı. HTTP {e.response.status_code} hatası."
    except Exception as e:
        return f"Sistem hatası: Paket listesi alınamadı - {type(e).__name__}"


@tool
def request_phone_number() -> str:
    """
    Müşteriden telefon numarasını talep eder.
    
    Returns:
        str: Telefon numarası talep mesajı
        
    Kullanım: Müşteriye özel işlemler (fatura sorgulama, paket bilgisi vb.) için
    telefon numarası gerektiğinde kullanın. Bu fonksiyondan sonra alınan numara ile
    diğer fonksiyonları çağırın.
    """
    return """📞 Telefon Numarası Gerekli

Size daha iyi hizmet verebilmem için telefon numaranıza ihtiyacım var.

Lütfen 11 haneli telefon numaranızı paylaşın:
• Örnek format: 05551234567
• Boşluk ve tire kullanabilirsiniz: 0555 123 45 67

Bu bilgi ile hesabınıza erişebilir ve güncel bilgilerinizi size sunabilirim."""

@tool
async def get_package_by_usernumber(phonenumber: str) -> str:
    """
    Müşterinin telefon numarasına göre aktif paket bilgilerini sorgular.
    
    Args:
        phonenumber (str): Müşterinin telefon numarası (örn: 05551234567)
        
    Returns:
        str: Müşterinin aktif paket detayları (JSON formatında) veya hata mesajı
        
    Kullanım: Müşteri mevcut paketini öğrenmek istediğinde veya paket değişikliği
    yapmadan önce mevcut durumu kontrol etmek için kullanın.
    """
    # Telefon numarası format kontrolü
    if not phonenumber or len(phonenumber.replace(" ", "").replace("-", "")) < 10:
        return "Geçersiz telefon numarası formatı. Lütfen 11 haneli telefon numaranızı doğru girin."
    
    try:
        async with httpx.AsyncClient() as client:
            clean_phone = phonenumber.replace(" ", "").replace("-", "")
            url = f"http://localhost:8000/api/v1/users/phone/{clean_phone}/package"
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Bu telefon numarasında ({phonenumber}) aktif paket bulunamadı veya kullanıcı sistemde kayıtlı değil."
        return f"Paket bilgileri sorgulanamadı. HTTP {e.response.status_code} hatası."
    except Exception as e:
        return f"Sistem hatası: Paket bilgileriniz alınamadı - {type(e).__name__}"

@tool
async def get_user_remainining_uses(phonenumber: str) -> str:
    """
    Müşterinin telefon numarasına göre kalan kullanım haklarını sorgular.
    
    Args:
        phonenumber (str): Müşterinin telefon numarası (örn: 05551234567)
        
    Returns:
        str: Müşterinin kalan kullanım hakları (JSON formatında) veya hata mesajı
        
    Kullanım: Müşteri kalan dakika, SMS, internet kotasını öğrenmek istediğinde kullanın.
    """
    try:
        async with httpx.AsyncClient() as client:
            clean_phone = phonenumber.replace(" ", "").replace("-", "")
            url = f"http://localhost:8000/api/v1/remaining-uses/phone/{clean_phone}/"
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Bu telefon numarasında ({phonenumber}) aktif paket bulunamadı veya kullanıcı sistemde kayıtlı değil."
        return f"Paket bilgileri sorgulanamadı. HTTP {e.response.status_code} hatası."
    except Exception as e:
        return f"Sistem hatası: Paket bilgileriniz alınamadı - {type(e).__name__}"


@tool
async def get_service_purchase(phonenumber: str) -> str:
    """
    Müşterinin telefon numarasına göre satın aldığı hizmetleri sorgular.
    
    Args:
        phonenumber (str): Müşterinin telefon numarası (örn: 05551234567)
        
    Returns:
        str: Müşterinin satın aldığı hizmetler listesi (JSON formatında) veya hata mesajı
        
    Kullanım: Müşteri geçmişte satın aldığı ek hizmetleri, paketleri öğrenmek istediğinde kullanın.
    """
    try:
        async with httpx.AsyncClient() as client:
            clean_phone = phonenumber.replace(" ", "").replace("-", "")
            url = f"http://localhost:8000/api/v1/service-purchases/phone/{clean_phone}/"
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Bu telefon numarasında ({phonenumber}) aktif paket bulunamadı veya kullanıcı sistemde kayıtlı değil."
        return f"Paket bilgileri sorgulanamadı. HTTP {e.response.status_code} hatası."
    except Exception as e:
        return f"Sistem hatası: Paket bilgileriniz alınamadı - {type(e).__name__}"

# @tool
# async def get_invoice_content() -> str:


tools = [final_answer,get_all_package, get_package_by_usernumber, request_user_info, post_new_user, get_packages_by_type, control_by_phonenumber, control_location_have_problem, get_user_remainining_uses, get_service_purchase]  

model = model = ChatOpenAI(
    base_url="http://localhost:1234/v1",  
    api_key="lm-studio",                 
    model="google/gemma-3-12b",
    temperature=0.0,
    streaming=True
)

# Basit sohbet memory - sadece o anki konuşmayı hatırlar
session_memories = {}

def get_or_create_memory(session_id: str = "default") -> ConversationBufferMemory:
    """Session ID'ye göre memory objesi döndürür veya yenisini oluşturur"""
    if session_id not in session_memories:
        session_memories[session_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="output",
            max_token_limit=2000  # Çok uzun konuşmaları sınırla
        )
    return session_memories[session_id]

def clear_session_memory(session_id: str):
    """Belirli bir session'ın konuşmasını temizle"""
    if session_id in session_memories:
        session_memories[session_id].clear()
        return True
    return False

prompt = PromptTemplate.from_template("""
Sen, bir telekomünikasyon şirketinde uzman ve dost canlısı bir müşteri temsilcisisin. 🎧
Görevin, araçları kullanarak müşterilere hızlı ve doğru çözümler sunmaktır.

<kurallar>
1.  **Önce Anla, Sonra Hareket Et:** Müşterinin isteğini anla. Gerekli tüm bilgiye sahip misin? (Örn: Telefon numarası)
2.  **Geçmişi Kontrol Et:** Bir aracı kullanmadan önce, ihtiyacın olan bilginin (isim, telefon numarası vb.) `<konusma_gecmisi>` içinde olup olmadığını KONTROL ET. Eğer bilgi oradaysa, tekrar isteme.
3.  **Doğru Aracı Seç:** Müşterinin isteğine en uygun aracı `<araclar>` listesinden seç.
4.  **Adım Adım Düşün:** Yanıtını `Thought:` ile başlatarak düşünce sürecini açıkla.
5.  **Eğer Yanıt Biliniyorsa, Aracı Kullanma:** Eğer müşterinin sorusuna araç kullanmadan cevap verebiliyorsan, doğrudan `Final Answer:` ile cevap ver. (Örn: "Merhaba" veya "Teşekkürler" gibi basit diyaloglar için)
6.  **Kapsam Dışı:** Telekomünikasyon dışı sorulara (hava durumu, tarih vb.) nazikçe hizmet kapsamın dışında olduğunu belirterek cevap ver.
7.  **Eğer sadece selamlaşma gibi bir durum varsa araç kullanma, doğrudan yanıt ver.**                                      
</kurallar>

<araclar>
{tool_names}                                    
{tools}
</araclar>

<konusma_gecmisi>
{chat_history}
</konusma_gecmisi>

<musteri_sorusu>
{input}
</musteri_sorusu>

<yanit_formati>
Thought: <Buraya müşterinin isteğini nasıl karşılayacağını adım adım düşün. Geçmişte bilgi var mı? Hangi aracı kullanmalıyım? Gerekli parametreler neler?>
Action: <kullanilacak_aracin_adi>
Action Input: <arac_icin_gerekli_parametre_json_formatinda_veya_string>
</yanit_formati>

{agent_scratchpad}
"""
)

# Agent'i modüler olarak oluştur
agent = create_react_agent(llm=model, tools=tools, prompt=prompt)

# Memory ile birlikte chat yapabilen fonksiyon
@traceable(name="chat_with_memory")
async def chat_with_memory(message: str, session_id: str = "default"):
    """Memory kullanan chat fonksiyonu"""
    memory = get_or_create_memory(session_id)
    
    # Executor ile çalıştır - memory parametresi dahil
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,
        memory=memory
    )
    
    response = await agent_executor.ainvoke({
        "input": message
    })
    
    return response


async def main():
    print("=== Basit Sohbet Memory Testi ===")
    print("Bu test sadece aynı konuşmadaki mesajları hatırlayacak\n")
    
    # İlk mesaj
    print("👤 Kullanıcı: Merhaba, ben Ahmet. Telefonum 05551234567")
    response1 = await chat_with_memory("Merhaba, ben Ahmet. Telefonum 05551234567")
    print(response1)
    print("🤖 Agent:", response1.get("output", response1))
    print("-" * 50)
    
    # İkinci mesaj - ismimi ve telefonu hatırlamalı
    print("👤 Kullanıcı: Paketimi öğrenebilir miyim?")
    response2 = await chat_with_memory("Paketimi öğrenebilir miyim?")  
    print(response2)
    print("🤖 Agent:", response2.get("output", response2))
    print("-" * 50)
    
    # Üçüncü mesaj - önceki bilgileri referans almalı
    print("👤 Kullanıcı: Az önce verdiğim telefon numarası neydi?")
    response3 = await chat_with_memory("Az önce verdiğim telefon numarası neydi?")
    print("🤖 Agent:", response3.get("output", response3))

# Test çalıştır
if __name__ == "__main__":
    asyncio.run(main())
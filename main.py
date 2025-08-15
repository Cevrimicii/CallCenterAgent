import typing
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain.memory import ConversationBufferMemory
from langchain_community.embeddings import HuggingFaceEmbeddings
# from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langsmith import traceable
from langchain_core.documents import Document
from langchain.chains import RetrievalQA
import httpx
import asyncio
from langchain.tools import Tool
from langchain_community.vectorstores import FAISS
import pandas as pd
import pickle
import typing
import re

final_answer = Tool(
    name="final_answer",
    description="Kullanıcıya doğrudan yanıt vermek için kullanılır.",
    func=lambda message: message,
    return_direct=True
)

def is_valid_number(phonenumber: str) -> bool:
    if not phonenumber or len(phonenumber.replace(" ", "").replace("-", "")) < 10:
        return False
    return True

@tool
@traceable(name="control_by_phonenumber")
async def control_by_phonenumber(phoneNumber: str) -> str:
    """
    Telefon numarası ile müşteri kaydını sorgular ve müşteri bilgilerini getirir.
    
    Args:
        Müşterinin telefon numarası
        
    Returns:
        str: Müşteri bilgileri (JSON formatında) veya hata mesajı
        
    Kullanım: Müşterinin sistemde kayıtlı olup olmadığını kontrol etmek ve 
    mevcut müşteri bilgilerini almak için kullanılır.
    """
    if not is_valid_number(phoneNumber):
        return "Geçersiz telefon numarası. Lütfen 11 haneli telefon numaranızı doğru formatta girin."
    try:
         async with httpx.AsyncClient() as client:
             phoneNumber = phoneNumber.strip()
             url = f"http://localhost:8000/api/v1/users/phone/{phoneNumber}"
             print("////////////////////////////////////")
             print(url)
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
        package_type (str): Paket türü - 'mobil' (mobil internet/hat paketleri), 
                           'ev interneti' (ev interneti paketleri) veya 'ekstra' (ekstra internet,sms,dakika paketleri)
        
    Returns:
        str: Belirtilen türdeki paketlerin listesi (JSON formatında) veya hata mesajı
        
    Kullanım: Müşteri belirli bir paket türü hakkında bilgi istediğinde kullanın.
    'mobil', 'ev interneti' ve 'ekstra' değerlerini kabul eder.
    """
    # Geçerli paket türlerini kontrol et
    valid_types = ['mobil', 'ev interneti', 'ekstra']
    if package_type.lower() not in valid_types:
        return f"Geçersiz paket türü: '{package_type}'. Lütfen 'mobil', 'ev' veya 'ekstra' türlerinden birini belirtin."
    
    try:
         async with httpx.AsyncClient() as client:
             url = f"http://localhost:8000/api/v1/packages/{package_type.lower()}"
             print("///////////////////////////////////")
             print(url)
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
async def request_user_info(phoneNumber: str = None, **kwargs) -> str:
    """
    Verilen telefon numarasına göre kullanıcı bilgilerini getirir.
    
    Args:
        Müşterinin telefon numarası
        
    Returns:
        str: Müşteri bilgileri (JSON formatında) veya hata mesajı
        
    Kullanım: Müşterinin sistemde kayıtlı olup olmadığını kontrol etmek ve mevcut müşteri bilgilerini almak için kullanılır.
    """
    if not is_valid_number(phoneNumber):
        return "Geçersiz telefon numarası. Lütfen 11 haneli telefon numaranızı doğru formatta girin."
    try:
        async with httpx.AsyncClient() as client:
            phoneNumber = phoneNumber.strip()
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
async def post_new_user(input: typing.Union[dict, str]) -> str:
    """
    Yeni kullanıcı hesabı oluşturur ve sisteme kaydeder.

    Args:
        input (dict | str): 
            - dict formatı: {"name": "Ad Soyad", "phone": "05551234567"}
            - string formatı: "name=Ad Soyad, phone=05551234567"

    Returns:
        str: Hesap oluşturma başarı mesajı veya hata açıklaması
    """

    # 1️⃣ Input formatını ayrıştır
    if isinstance(input, dict):
        name = input.get("name", "").strip()
        phone = input.get("phone", "").strip()
    elif isinstance(input, str):
        match_name = re.search(r'name\s*=\s*([^,\n]+)', input)
        name = match_name.group(1).strip() if match_name else ""
        match_phone = re.search(r'phone\s*=\s*([0-9]+)', input)
        phone = match_phone.group(1).strip() if match_phone else ""
    else:
        return "Geçersiz giriş formatı. Lütfen dict veya 'name=..., phone=...' formatında veri girin."

    # 2️⃣ Telefon numarası validasyonu
    phone_clean = phone.replace(" ", "").replace("-", "")
    if not phone_clean.isdigit() or len(phone_clean) != 11:
        return "Geçersiz telefon numarası. Lütfen 11 haneli telefon numaranızı doğru formatta girin."

    # 3️⃣ Ad-soyad validasyonu
    if not name or len(name.split()) < 2:
        return "Geçersiz ad bilgisi. Lütfen adınızı ve soyadınızı tam olarak girin."

    # 4️⃣ API'ye kayıt denemesi
    try:
        async with httpx.AsyncClient() as client:
            user_data = {"name": name, "phone": phone_clean}
            response = await client.post("http://localhost:8000/api/v1/users/", json=user_data)
            response.raise_for_status()
            return (
                f"✅ Kullanıcı hesabınız başarıyla oluşturuldu!\n\n"
                f"📋 Hesap Bilgileri:\n• Ad: {name}\n• Telefon: {phone_clean}\n\n"
                f"Artık hizmetlerimizden faydalanabilirsiniz."
            )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            return "Bu telefon numarası zaten sistemimizde kayıtlı. Mevcut hesabınızla giriş yapabilirsiniz."
        elif e.response.status_code == 400:
            return "Girilen bilgilerde hata var. Lütfen telefon numarası ve ad bilgilerinizi kontrol edin."
        return f"Hesap oluşturulamadı. Sistem hatası (HTTP {e.response.status_code})"

    except Exception as e:
        return f"Sistem hatası: Hesap oluşturulamadı - {type(e).__name__}. Lütfen tekrar deneyin."

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
            response = await client.get("http://localhost:8000/api/v1/packages/")
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return "Şu anda aktif paket bulunamadı. Lütfen daha sonra tekrar deneyin."
        return f"Paket bilgileri alınamadı. HTTP {e.response.status_code} hatası."
    except Exception as e:
        return f"Sistem hatası: Paket listesi alınamadı - {type(e).__name__}"


request_phone_number_tool = Tool(
    name="request_phone_number",
    description="Müşteriden telefon numarasını talep eder. Müşteriye özel işlemler için telefon numarası gerektiğinde kullanın.",
    func=lambda x: """📞 Telefon Numarası Gerekli

Size daha iyi hizmet verebilmem için telefon numaranıza ihtiyacım var.

Lütfen 11 haneli telefon numaranızı paylaşın:
• Örnek format: 05551234567
• Boşluk ve tire kullanabilirsiniz: 0555 123 45 67

Bu bilgi ile hesabınıza erişebilir ve güncel bilgilerinizi size sunabilirim.""",
    return_direct=True
)

request_new_user_info_tool = Tool(
    name="request_user_info",
    description="Müşteriden adını, numarasını talep eder. Yeni müşteri kaydı yapılacağı zaman kullanın",
    func=lambda x: """� Yeni Müşteri Kaydı İçin Bilgiler Gerekli

Size yeni bir müşteri hesabı oluşturabilmem için adınızı ve telefon numaranızı paylaşmanızı rica ediyorum.

Lütfen aşağıdaki bilgileri girin:
• Adınız ve Soyadınız: (örn. Ahmet Yılmaz)
• Telefon Numaranız: (örn. 0555 123 45 67)

Bilgileriniz güvenli bir şekilde saklanacaktır ve size en iyi hizmeti sunabilmemiz için gereklidir.""",
    return_direct=True
)

@tool
async def get_package_by_usernumber(phonenumber: str) -> str:
    """
    Müşterinin telefon numarasına göre aktif paket bilgilerini sorgular.
    
    Args:
        Müşterinin telefon numarası
        
    Returns:
        str: Müşterinin aktif paket detayları (JSON formatında) veya hata mesajı
        
    Kullanım: Müşteri mevcut paketini öğrenmek istediğinde veya paket değişikliği
    yapmadan önce mevcut durumu kontrol etmek için kullanın.
    """
    # Telefon numarası format kontrolü
    if not is_valid_number(phonenumber):
        return "Geçersiz telefon numarası. Lütfen 11 haneli telefon numaranızı doğru formatta girin."
    try:
        async with httpx.AsyncClient() as client:
            phonenumber = phonenumber.strip()
            url = f"http://localhost:8000/api/v1/users/phone/{phonenumber}/package"
            print("/////////////////////////////////////")
            print(phonenumber)
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Bu telefon numarasında ({phonenumber}) aktif paket bulunamadı veya kullanıcı sistemde kayıtlı değil."
        return f"Paket bilgileri sorgulanamadı. HTTP {e.response.status_code} hatası."
    except Exception as e:
        return f"Sistem hatası: Paket bilgileriniz alınamadı - {type(e).__name__}"

#////////////////////////////////////////    
@tool
async def get_current_subscription_by_usernumber(phonenumber: str) -> str:
    """
    Müşterinin telefon numarasına göre aktif abonelik bilgilerini sorgular.
    
    Args:
        Müşterinin telefon numarası
        
    Returns:
        str: Müşterinin aktif abonelik detayları (JSON formatında) veya hata mesajı
        
    Kullanım: Müşteri mevcut aboneliğini öğrenmek istediğinde veya abonelik değişikliği
    yapmadan önce mevcut durumu kontrol etmek için kullanın.
    """
    # Telefon numarası format kontrolü
    if not is_valid_number(phonenumber):
        return "Geçersiz telefon numarası. Lütfen 11 haneli telefon numaranızı doğru formatta girin."
    try:
        async with httpx.AsyncClient() as client:
            phonenumber = phonenumber.strip()
            url = f"http://localhost:8000/api/v1/subs/{phonenumber}/activesub"
            print("/////////////////////////////////////")
            print(phonenumber)
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Bu telefon numarasında ({phonenumber}) aktif abonelik bulunamadı veya kullanıcı sistemde kayıtlı değil."
        return f"Abonelik bilgileri sorgulanamadı. HTTP {e.response.status_code} hatası."
    except Exception as e:
        return f"Sistem hatası: Abonelik bilgileriniz alınamadı - {type(e).__name__}"

@tool
async def get_active_invoice_by_usernumber(phonenumber: str) -> str:
    """
    Müşterinin telefon numarasına göre aktif faturasını getirir.
    
    Args:
        Müşterinin telefon numarası
        
    Returns:
        str: Müşterinin aktif fatura bilgiler (JSON formatında) veya hata mesajı
        
    Kullanım: Müşteri mevcut faturasını öğrenmek istediğinde kullanın.
    """
    # Telefon numarası format kontrolü
    if not is_valid_number(phonenumber):
        return "Geçersiz telefon numarası. Lütfen 11 haneli telefon numaranızı doğru formatta girin."
    try:
        async with httpx.AsyncClient() as client:
            phonenumber = phonenumber.strip()
            url = f"http://localhost:8000/api/v1/invoices/phone/{phonenumber}/activeinvoice"
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Bu telefon numarasında ({phonenumber}) aktif fatura bulunamadı veya kullanıcı sistemde kayıtlı değil."
        return f"Fatura bilgileri sorgulanamadı. HTTP {e.response.status_code} hatası."
    except Exception as e:
        return f"Sistem hatası: Fatura bilgileriniz alınamadı - {type(e).__name__}"
    
@tool
async def get_user_invoices_by_usernumber(phonenumber: str) -> str:
    """
    Müşterinin telefon numarasına göre tüm faturalarını (geçmiş ve aktif) getirir.
    
    Args:
        Müşterinin telefon numarası
        
    Returns:
        str: Müşterinin tüm fatura geçmişi (JSON formatında) veya hata mesajı
        
    Kullanım: Müşteri fatura geçmişini görmek istediğinde veya geçmişte ödediği faturaları sorgulamak istediğinde kullanın.
    """
    # Telefon numarası format kontrolü
    if not is_valid_number(phonenumber):
        return "Geçersiz telefon numarası. Lütfen 11 haneli telefon numaranızı doğru formatta girin."
    try:
        async with httpx.AsyncClient() as client:
            phonenumber = phonenumber.strip()
            url = f"http://localhost:8000/api/v1/invoices/phone/{phonenumber}/invoices"
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Bu telefon numarasında ({phonenumber}) fatura geçmişi bulunamadı veya kullanıcı sistemde kayıtlı değil."
        return f"Fatura geçmişi sorgulanamadı. HTTP {e.response.status_code} hatası."
    except Exception as e:
        return f"Sistem hatası: Fatura geçmişiniz alınamadı - {type(e).__name__}"
    
@tool
async def get_active_invoice_items(phonenumber: str) -> str:
    """
    Müşterinin telefon numarasına göre aktif faturasının detaylı kalemlerini getirir.
    
    Args:
        Müşterinin telefon numarası
        
    Returns:
        str: Müşterinin aktif fatura kalemlerinin detayları (JSON formatında) veya hata mesajı
        
    Kullanım: Müşteri faturasının detaylarını, hangi hizmetler için ne kadar ücret ödediğini öğrenmek istediğinde kullanın.
    """
    # Telefon numarası format kontrolü
    if not is_valid_number(phonenumber):
        return "Geçersiz telefon numarası. Lütfen 11 haneli telefon numaranızı doğru formatta girin."
    try:
        async with httpx.AsyncClient() as client:
            phonenumber = phonenumber.strip()
            url = f"http://localhost:8000/api/v1/invoices/phone/{phonenumber}/activeinvoice/items"
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Bu telefon numarasında ({phonenumber}) aktif fatura kalemleri bulunamadı veya kullanıcı sistemde kayıtlı değil."
        return f"Fatura kalemleri sorgulanamadı. HTTP {e.response.status_code} hatası."
    except Exception as e:
        return f"Sistem hatası: Fatura kalemi bilgileriniz alınamadı - {type(e).__name__}"


@tool
async def get_user_remainining_uses(phonenumber: str) -> str:
    """
    Müşterinin telefon numarasına göre kalan kullanım haklarını sorgular.
    
    Args:
        Müşterinin telefon numarası
        
    Returns:
        str: Müşterinin kalan kullanım hakları (JSON formatında) veya hata mesajı
        
    Kullanım: Müşteri kalan dakika, SMS, internet kotasını öğrenmek istediğinde kullanın.
    """
    if not is_valid_number(phonenumber):
        return "Geçersiz telefon numarası. Lütfen 11 haneli telefon numaranızı doğru formatta girin."
    try:
        async with httpx.AsyncClient() as client:
            phonenumber = phonenumber.strip()
            url = f"http://localhost:8000/api/v1/remaining-uses/phone/{phonenumber}"
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Bu telefon numarasında ({phonenumber}) kalan kullanım hakkı bulunamadı veya kullanıcı sistemde kayıtlı değil."
        return f"Kullanım hakları sorgulanamadı. HTTP {e.response.status_code} hatası."
    except Exception as e:
        return f"Sistem hatası: Kullanım hakkı bilgileriniz alınamadı - {type(e).__name__}"


@tool
async def get_service_purchase(phonenumber: str) -> str:
    """
    Müşterinin telefon numarasına göre satın aldığı hizmetleri sorgular.
    
    Args:
        Müşterinin telefon numarası
        
    Returns:
        str: Müşterinin satın aldığı hizmetler listesi (JSON formatında) veya hata mesajı
        
    Kullanım: Müşteri geçmişte satın aldığı ek hizmetleri, paketleri öğrenmek istediğinde kullanın.
    """
    if not is_valid_number(phonenumber):
        return "Geçersiz telefon numarası. Lütfen 11 haneli telefon numaranızı doğru formatta girin."
    try:
        async with httpx.AsyncClient() as client:
            phonenumber = phonenumber.strip()
            url = f"http://localhost:8000/api/v1/service-purchases/phone/{phonenumber}"
            print("///////////////////////////////////////////////////////////")
            print(url)
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Bu telefon numarasında ({phonenumber}) satın alınmış hizmet bulunamadı veya kullanıcı sistemde kayıtlı değil."
        return f"Hizmet satın alma bilgileri sorgulanamadı. HTTP {e.response.status_code} hatası."
    except Exception as e:
        return f"Sistem hatası: Hizmet satın alma bilgileriniz alınamadı - {type(e).__name__}"

@tool
async def get_package_by_name(name: str) -> str:
    """
    Paket ismini kullanarak belirli bir paket hakkında detaylı bilgi getirir.
    
    Args:
        name (str): Sorgulanacak paketin tam adı (örn: "Sınırsız Konuşma Paketi", "25GB İnternet Paketi")
        
    Returns:
        str: Belirtilen paketin detayları (fiyat, özellikler, süre vb.) (JSON formatında) veya hata mesajı
        
    Kullanım: Müşteri belirli bir paket hakkında detaylı bilgi almak istediğinde kullanın.
    """
    try:
        async with httpx.AsyncClient() as client:
            name = name.strip()
            url = f"http://localhost:8000/api/v1/packages/{name}"
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"'{name}' isimli paket bulunamadı. Lütfen paket adını kontrol edin."
        return f"Paket bilgileri sorgulanamadı. HTTP {e.response.status_code} hatası."
    except Exception as e:
        return f"Sistem hatası: Paket bilgileri alınamadı - {type(e).__name__}"

@tool
def rag_search(query: str) -> str:
    """
    Müşteri sorgusuna benzer geçmiş sohbet örneklerini bularak agent'a rehberlik sağlar.
    
    Args:
        Müşterinin sorusu veya isteği
        
    Returns:
        str: Benzer sohbet örnekleri ve önerilen yanıt şekli
        
    Kullanım: Karmaşık sorularda veya standart dışı durumlarda geçmiş sohbet örneklerinden
    yararlanarak daha doğal ve uygun yanıtlar oluşturmak için kullanın.
    """
    try:
        import faiss
        import pandas as pd
        from sentence_transformers import SentenceTransformer
        
        # ---- 1. Embed modeli ----
        model = SentenceTransformer('intfloat/multilingual-e5-large')

        # ---- 2. FAISS index yükleme ----
        index = faiss.read_index("e5.index")

        # ---- 3. Veri ve conversation ID'leri ----
        data = pd.read_csv("translated_dialogs.csv", encoding="utf-8")
        conv_ids = pd.read_csv("conversation_ids.csv", encoding="utf-8")

        # ---- 4. Retriever fonksiyonu ----
        def retrieve(search_query, top_k=2):
            # Sorguyu embedle
            query_vec = model.encode([search_query])
            query_vec = query_vec.astype("float32")

            # FAISS ile arama yap
            distances, indices = index.search(query_vec, top_k)

            results = []
            for idx in indices[0]:
                if idx < len(conv_ids):
                    text_id = conv_ids.iloc[idx]['conversation_id']
                    filtered = data[data['conversation_id'] == text_id]
                    if not filtered.empty:
                        text_row = filtered['translated_tr'].values[0]
                        results.append(text_row)
            return results

        # ---- 5. Benzer sohbetleri bul ----
        similar_conversations = retrieve(query)
        
        if not similar_conversations:
            return "Bu sorgu için benzer sohbet örneği bulunamadı."
        
        # ---- 6. Sonuçları formatla ----
        response = f"📚 **Benzer Sohbet Örnekleri** ('{query}' için):\n\n"
        
        for i, conversation in enumerate(similar_conversations, 1):
            response += f"**Örnek {i}:**\n{conversation}\n\n"
        
        response += "💡 **Öneriler:**\n"
        response += "- Bu örnekleri baz alarak müşteriye samimi ve yardımcı bir ton kullan\n"
        response += "- Benzer durumlardan öğrenilen çözüm yöntemlerini uygula\n"
        response += "- Müşterinin ihtiyacına göre bu örneklerdeki yaklaşımı adapte et\n"
        
        return response
        
    except FileNotFoundError as e:
        return f"RAG dosyaları bulunamadı: {str(e)}. Lütfen 'e5.index', 'translated_dialogs.csv' ve 'conversation_ids.csv' dosyalarının mevcut olduğundan emin olun."
    except Exception as e:
        return f"RAG arama hatası: {type(e).__name__} - {str(e)}"


tools = [final_answer,get_all_package, get_package_by_name,get_package_by_usernumber, request_user_info,request_new_user_info_tool, post_new_user, get_packages_by_type, control_by_phonenumber, control_location_have_problem, get_user_remainining_uses, get_service_purchase, get_active_invoice_items,get_active_invoice_by_usernumber,get_current_subscription_by_usernumber, get_user_invoices_by_usernumber,request_phone_number_tool, rag_search]  
# tools = [rag_search,final_answer]

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
            max_token_limit=800  # 4096 token limit için çok düşük tut
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
3.  **Doğru Aracı Seç:** Müşterinin isteğine en uygun aracı `<araclar>` listesinden seç. Eğer uygun bir araç bulamazsan, son çare olarak rag_search aracını kullan.
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
Intent: <Buraya kullanıcının niyeti>                                      
Thought: <Buraya müşterinin isteğini nasıl karşılayacağını adım adım düşün. Geçmişte bilgi var mı? Hangi aracı kullanmalıyım? Gerekli parametreler neler?>
Action: <kullanilacak_aracin_adi>
Action Input: parametre
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
        max_iterations=3,  # 5'ten 3'e düşür
        memory=memory
    )
    
    response = await agent_executor.ainvoke({
        "input": message
    })
    
    return response



async def main():
    print("🎧 CallCenter Agent başlatılıyor...")
    print("Çıkmak için 'exit' yazın\n")
    
    while True:
        try:
            message = input("Siz: ")
            
            if message.lower() in ['exit', 'çık', 'quit']:
                print("👋 Görüşmek üzere!")
                break
            
            # Chat fonksiyonunu çalıştır
            response = await chat_with_memory(message)
            
            print("\nAgent: ")
            print(response.get('output', 'Yanıt alınamadı'))
            print("-" * 50)
            
        except KeyboardInterrupt:
            print("\n👋 Güle güle!")
            break
        except Exception as e:
            print(f"❌ Hata: {e}")

if __name__ == "__main__":
    asyncio.run(main())
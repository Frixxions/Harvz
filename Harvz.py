import requests
from bs4 import BeautifulSoup
import time
import time
import sys

# ================= RENKLER =================
MOR = "\033[35m"
MAVI = "\033[34m"
KIRMIZI = "\033[31m"
RESET = "\033[0m"
LimonataMalzeme = ["4 Adet Büyük Limon","1 Subar Dağı şeker","1 Su Bardağı Sıcak su (Eritmek için)","Birkaç dal Nane","Buz Küpleri"]
LimonataTarif = """ 1 Limonların kabuğunu rendeleyin (sadece sarı kısmını, beyaz kısmı acı yapar).
   2 Rendelediğiniz kabuğu bir kaseye alın ve 1 subar dağı toz şekerle iyice ovun. Bu işlem limon aromasının şekere geçmesini sağlar.
   3 Ardından üzerine 1 su bardağı sıcak su dökün ve şeker eriyene kadar karıştırın.
   4 Limonları sıkın, çıkan suyu şekerli karışıma ekleyin.
   5 Karışımı süzgeçten geçirerek sürahiye alın.
  6  Üzerine 5 su bardağı soğuk suyu ekleyin ve karıştırın.
   6 Buz küpleri ve isteğe göre taze nane yaprakları ekleyerek servis edin. Afiyet olsun."""
İlkSayıGir = "İlk Sayıyı Giriniz: "
İkinciSayıGir = "İkinci Sayıyı Giriniz: "
BuyukseGir = "Bu arada 2. Sayınız ilk sayınızdan daha\n büyük olduğu için ondalıklı çıktı alabilirsiniz."
HarvzAscii = """
                                                   
                                                   
____    ____                                       
`MM'    `MM'                                       
 MM      MM                                        
 MM      MM    ___   ___  __ ____    ___ _________ 
 MM      MM  6MMMMb  `MM 6MM `MM(    )M' MMMMMMMMP 
 MMMMMMMMMM 8M'  `Mb  MM69 "  `Mb    d'  /    dMP  
 MM      MM     ,oMM  MM'      YM.  ,P       dMP   
 MM      MM ,6MM9'MM  MM        MM  M       dMP    
 MM      MM MM'   MM  MM        `Mbd'      dMP     
 MM      MM MM.  ,MM  MM         YMP      dMP    / 
_MM_    _MM_`YMMM9'Yb_MM_         M      dMMMMMMMM 
                                                   
                                                   
                                                   """
# --- Wikipedia helper (uzman sürüm) ---
import requests
import time
import sys
import textwrap
import webbrowser
from functools import lru_cache

# Renkler
MOR = "\033[35m"
MAVI = "\033[34m"
KIRMIZI = "\033[31m"
SARI = "\033[33m"
RESET = "\033[0m"

# Güvenli session ve headers (User-Agent koymak önemli)
_session = requests.Session()
_session.headers.update({
    "User-Agent": "HarvzBrowser/1.0 (https://github.com/Harvz) Python-wiki-client"
})

# Basit retry decorator (küçük retry, exponential backoff)
def _safe_get(url, params=None, tries=3, backoff=0.5, timeout=6):
    for attempt in range(1, tries + 1):
        try:
            r = _session.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:
            if attempt == tries:
                raise
            time.sleep(backoff * attempt)

# LRU cache: aynı arama tekrarlanırsa API çağrısını önler
@lru_cache(maxsize=128)
def wiki_lookup_raw(query: str, lang: str = "tr", limit_sentences: int = 3):
    """
    1) arama yapar (search)
    2) en iyi başlığı alır
    3) extracts API ile intro'u düz metin (explaintext) alır
    Döndürür: dict {found, title, extract, url, suggestions}
    """
    query = query.strip()
    if not query:
        return {"found": False, "reason": "empty query"}

    api_base = f"https://{lang}.wikipedia.org/w/api.php"

    # 1) search (en iyi başlığı bul)
    params_search = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": 1,
        "format": "json"
    }
    resp = _safe_get(api_base, params=params_search)
    data = resp.json()

    search_hits = data.get("query", {}).get("search", [])
    if not search_hits:
        # hiç sonuç yok, öneriler getirmek için opensearch (kısa)
        params_opensearch = {
            "action": "opensearch",
            "search": query,
            "limit": 5,
            "format": "json"
        }
        try:
            r2 = _safe_get(api_base, params=params_opensearch)
            suggestions = r2.json()[1]
        except Exception:
            suggestions = []
        return {"found": False, "reason": "no results", "suggestions": suggestions}

    best = search_hits[0]
    title = best.get("title")

    # 2) page extract (intro, plaintext)
    params_extract = {
        "action": "query",
        "prop": "extracts|pageprops",
        "exintro": True,
        "explaintext": True,
        "titles": title,
        "redirects": True,
        "format": "json",
        "exsentences": limit_sentences
    }
    resp2 = _safe_get(api_base, params=params_extract)
    data2 = resp2.json()

    pages = data2.get("query", {}).get("pages", {})
    page = next(iter(pages.values()))
    extract = page.get("extract", "").strip()
    pageprops = page.get("pageprops", {})
    is_disambig = "disambiguation" in pageprops

    page_title = page.get("title", title)
    page_url = f"https://{lang}.wikipedia.org/wiki/{page_title.replace(' ', '_')}"

    # If disambiguation page: try searching suggestions
    suggestions = []
    if is_disambig:
        # get 'search' results list for alternatives (up to 5)
        params_search_all = {
            "action": "query",
            "list": "search",
            "srsearch": title,
            "srlimit": 6,
            "format": "json"
        }
        resp3 = _safe_get(api_base, params=params_search_all)
        data3 = resp3.json()
        suggestions = [s.get("title") for s in data3.get("query", {}).get("search", []) if s.get("title") != page_title]

    return {
        "found": True,
        "title": page_title,
        "extract": extract,
        "url": page_url,
        "disambiguation": is_disambig,
        "suggestions": suggestions
    }

# Pretty print helper
def pretty_print_wiki(result, width=80):
    if not result or not result.get("found"):
        print(f"{KIRMIZI}Sayfa bulunamadı. Öneriler:{RESET}")
        for s in result.get("suggestions", [])[:5]:
            print(f" - {s}")
        return

    title = result["title"]
    url = result["url"]
    extract = result.get("extract", "")

    print(f"{MOR}┏━ {MAVI}{title}{RESET}{MOR} ━┓{RESET}")
    print(f"{MAVI}{url}{RESET}\n")
    if not extract:
        print(f"{SARI}Sayfa bulundu ama özet yok veya çok kısa.{RESET}\n")
    else:
        # metni temiz şekilde satırlara kır
        wrapped = textwrap.fill(extract, width=width)
        print(wrapped + "\n")
    if result.get("disambiguation"):
        print(f"{SARI}Bu bir ayrım sayfası. Olası başlıklar:{RESET}")
        for s in result.get("suggestions", [])[:8]:
            print(" -", s)
    print(f"{MOR}┗{'━'* (min(len(title), 40))}{RESET}\n")

# Kullanıcıya gösteren üst seviyeli fonksiyon
def wiki_ara_interaktif(lang="tr", sentences=3, save_history=False):
    q = input("Wikipedia'da ara (kelime/başlık): ").strip()
    if not q:
        print("Boş arama iptal edildi.")
        return
    try:
        print(f"{MOR}Arama yapılıyor...{RESET}")
        res = wiki_lookup_raw(q, lang, sentences)
        pretty_print_wiki(res, width=80)
        # isteğe bağlı: kaydetme
        if save_history and res.get("found"):
            try:
                with open("wiki_history.txt", "a", encoding="utf-8") as fh:
                    fh.write(f"{time.ctime()} | {res['title']} | {res['url']}\n")
            except Exception:
                pass
        # isteğe bağlı: tarayıcıda aç
        want = input("Tarayıcıda açmak ister misin? (E/h): ").strip().lower()
        if want == "e":
            webbrowser.open(res["url"])
    except Exception as e:
        print(f"{KIRMIZI}Hata: {e}{RESET}")
# ================= YAVAŞ YAZDIRMA =================
def yavas_yaz(metin, delay=0.01):
    for ch in metin:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)

# ================= YÜKLEME BAR =================
def yukleme_bar():
    bar_uzunluk = 20
    print()
    for i in range(bar_uzunluk + 1):
        dolu = "█" * i
        bos = "░" * (bar_uzunluk - i)
        yuzde = int((i / bar_uzunluk) * 100)
        sys.stdout.write(
            f"\r{MOR}[{dolu}{bos}] %{yuzde}{RESET}"
        )
        sys.stdout.flush()
        time.sleep(0.15)
    print("\n")

# ================= GİRİŞ EKRANI =================
print(MOR)
yavas_yaz(HarvzAscii, 0.002)
print(RESET)

yavas_yaz(MOR + "Harvz Browser Başlatılıyor...\n" + RESET, 0.05)
time.sleep(0.5)

yavas_yaz(MAVI + "Modüller Yükleniyor...\n" + RESET, 0.05)
yukleme_bar()

# ================= MENÜ =================
MenuSecimText = f"""
{MOR}Aramak istediğinizi girin (Sayı){RESET}
[1] Tarifler
[2] Hesap Makinesi XR Range
[3] Harvz Browser Wiki (Geliştiriliyor)
[4] Yapımcılar <Cyber Turks>

Seçiminiz: """
menu = int(input(HarvzAscii + MenuSecimText))
if menu == 1:
  tarif_sec = int(input("""
  Ne Tarifi istersin?
  [1] Yemek Tarifleri
  [2] Oto Bakım
  Daha Fazlası Eklenecek.
  Seçim: """))
  if tarif_sec == 1:
    tarifler = input("""
    Yemek Tariflerine Girdiniz!
    (Yazı olarak girin) 
    _______________________
   | Limonata    
   | Pasta        
   | Muhallebi     
    _______________________
    Seçim: """).title()
    if tarifler == "Limonata":
      print("Limonata Malzemeleri:")
      for i in range(len(LimonataMalzeme)):
        print(i+1 , "-", LimonataMalzeme[i])
      print("""
      YAPILIŞI !!! 
      """ ,LimonataTarif)
elif menu == 2:
  hesap_makinesi = int(input("""
  ⠀⠀⠀⠀⠠⠤⠤⠤⠤⠤⣤⣤⣤⣄⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠛⠛⠿⢶⣤⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⢀⣀⣀⣠⣤⣤⣴⠶⠶⠶⠶⠶⠶⠶⠶⠶⠿⠿⢿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠚⠛⠉⠉⠉⠀⠀⠀⠀⠀⠀⢀⣀⣀⣤⡴⠶⠶⠿⠿⠿⣧⡀⠀⠀⠀⠤⢄⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⢀⣠⡴⠞⠛⠉⠁⠀⠀⠀⠀⠀⠀⠀⢸⣿⣷⣶⣦⣤⣄⣈⡑⢦⣀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⣠⠔⠚⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⡿⠟⠉⠉⠉⠉⠙⠛⠿⣿⣮⣷⣤⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⡿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⢻⣯⣧⡀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠻⢷⡤⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢿⣿⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣿⣦⣤⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠙⠛⠛⠻⠿⠿⣿⣶⣶⣦⣄⣀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠻⣿⣯⡛⠻⢦⡀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⢿⣆⠀⠙⢆⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢻⣆⠀⠈⢣
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠻⡆⠀⠈
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⡀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠃⠀
    __  __                    
   / / / /___ _______   ______
  / /_/ / __ `/ ___/ | / /_  /
 / __  / /_/ / /   | |/ / / /_
/_/_/_/\__,_/_/    |___/ /___/
  | |/ /_____                 
  |   // ___/                 
 /   |/ /                     
/_/|_/_/                      
                              
      <<    Xr Hesap Makinesi     >>
  Yapacağınız işlemi seçin:
  [1] Toplama
  [2] Çıkarma
  [3] Çarpma
  [4] Bölme
  Seçiminiz: """
  ))
  if hesap_makinesi == 1:
    topla_gir1 = int(input(İlkSayıGir))
    topla_gir2 = int(input(İkinciSayıGir))
    print("Toplama Sonucu" ,topla_gir1 + topla_gir2)
  elif hesap_makinesi == 2:
      cikar_gir1 = int(input(İlkSayıGir))
      cikar_gir2 = int(input(İkinciSayıGir))
      print("Çıkarma Sonucu" , cikar_gir1 - cikar_gir2)
      if cikar_gir2 > cikar_gir1:
        print(BuyukseGir)
  elif hesap_makinesi == 3:
    carp_gir1 = int(input(İlkSayıGir))
    carp_gir2 = int(input(İkinciSayıGir))
    print("Çarpma Sonucu," ,carp_gir1 * carp_gir2)
  elif hesap_makinesi == 4:
    bolme_gir1 = int(input(İlkSayıGir))
    bolme_gir2 = int(input(İkinciSayıGir))
    print("Bölme Sonucu," ,bolme_gir1 / bolme_gir2)
    if bolme_gir2 > bolme_gir1:
      print(BuyukseGir)
elif menu == 3:
    # dil isteğe bağlı: 'tr' veya 'en'
    wiki_ara_interaktif(lang="tr", sentences=3, save_history=True)
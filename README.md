# 🧠 ReceiptMind AI

<div align="center">

**Fişlerinizi Akıllı Bir Asistana Dönüştürün**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![LLM](https://img.shields.io/badge/LLM-Qwen2.5--7B-purple.svg)](https://huggingface.co/Qwen)

</div>

---

## 📖 İçindekiler

- [Genel Bakış](#-genel-bakış)
- [Özellikler](#-özellikler)
- [Mimari](#-mimari)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
- [Proje Yapısı](#-proje-yapısı)
- [Teknolojiler](#-teknolojiler)
- [Gelişmiş Özellikler](#-gelişmiş-özellikler)
- [Katkıda Bulunma](#-katkıda-bulunma)
- [Lisans](#-lisans)

---

## 🎯 Genel Bakış

**ReceiptMind AI**, kişisel harcama yönetimini yapay zeka ile birleştiren yeni nesil bir finansal asistan platformudur. Fişlerinizi otomatik olarak okur, kategorize eder, analiz eder ve doğal dil ile sorularınıza yanıt verir.

### 🌟 Neden ReceiptMind AI?

- **🤖 Akıllı OCR**: Vision Language Model (VLM) ile fiş/fatura okuma
- **💬 Doğal Dil Sorgulama**: "Kasım ayında kahveye ne kadar harcadım?" gibi sorular sorun
- **📊 Akıllı Analizler**: Abonelik tespiti, anomali algılama, bütçe uyarıları
- **🔍 RAG Teknolojisi**: FAISS vektör veritabanı ile hızlı ve doğru arama
- **🌐 Modern Web Arayüzü**: Streamlit tabanlı interaktif dashboard
- **🔗 Entegrasyonlar**: Gmail, Telegram, QR kod desteği
- **🌍 Çoklu Dil**: Türkçe ve İngilizce destek

---

## ✨ Özellikler

### 🔥 Temel Özellikler

#### 1. **Akıllı Fiş İşleme**
- PDF fişlerinden otomatik veri çıkarma
- LLM tabanlı ürün adı normalizasyonu
- Otomatik kategorizasyon (gıda, ulaşım, eğlence, vb.)
- Düşük güvenilirlik skorlu kayıtlar için insan onayı

#### 2. **RAG Tabanlı Sorgulama**
- Doğal dil ile soru sorma
- FAISS vektör indeksi ile semantik arama
- Çok dilli embedding desteği (paraphrase-multilingual-MiniLM-L12-v2)
- Kaynak gösterimi ile şeffaf yanıtlar

#### 3. **Akıllı Analizler**

**📅 Abonelik Tespiti**
```python
# Tekrarlayan ödemeleri otomatik tespit eder
- Netflix: 99.99 TL/ay (son 6 ay)
- Spotify: 34.99 TL/ay (son 12 ay)
```

**⚠️ Anomali Algılama**
```python
# Alışılmadık harcamaları bildirir
- Gıda kategorisinde %150 artış tespit edildi
- Normalden 3 standart sapma yüksek harcama
```

**💰 Bütçe Yönetimi**
```python
# Aylık bütçe takibi ve uyarılar
- Gıda: 2,500 / 3,000 TL (%83)
- Eğlence: 1,200 / 1,000 TL (%120) ⚠️ Bütçe aşıldı!
```

**📈 Tahminleme**
```python
# Gelecek ay harcama tahmini
- ARIMA modeli ile zaman serisi analizi
- Mevsimsel trendleri dikkate alır
```

#### 4. **Modern Web Arayüzü**

**💬 Sohbet Sekmesi**
- LLM ile doğal dil etkileşimi
- Geçmiş sohbet kayıtları
- Bağlam farkındalığı

**📊 Dashboard Sekmesi**
- Aylık harcama grafikleri (Plotly)
- Kategori bazlı dağılım
- Top 10 ürünler
- Abonelik ve anomali uyarıları

**📥 İnceleme Sekmesi**
- Yeni eklenen kayıtları görüntüleme
- Düzenleme ve onaylama
- Toplu işlemler

**📤 Yükleme Sekmesi**
- Sürükle-bırak PDF yükleme
- Otomatik işleme
- İlerleme takibi

---

## 🏗️ Mimari

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web UI                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   Chat   │  │Dashboard │  │  Review  │  │  Upload  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Assistant  │    │   Analytics  │    │   Ingestion  │
│   (RAG)      │    │   Engine     │    │   Pipeline   │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ SQLite   │  │  FAISS   │  │  Reports │  │   PDFs   │   │
│  │   DB     │  │  Index   │  │   CSV    │  │  Inbox   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Qwen2.5-7B  │    │ Sentence     │    │   Vision     │
│     LLM      │    │ Transformers │    │     LLM      │
└──────────────┘    └──────────────┘    └──────────────┘
```

### 🔄 Veri Akışı

1. **Ingestion**: PDF → OCR/VLM → Structured Data → SQLite
2. **Indexing**: SQLite → Embeddings → FAISS Index
3. **Query**: User Question → Query Parser → RAG/Reports → LLM → Answer
4. **Analytics**: SQLite → Analysis Engine → Insights → Dashboard

---

## 🚀 Kurulum

### Gereksinimler

- Python 3.10 veya üzeri
- 8GB+ RAM (LLM için)
- 10GB+ disk alanı (model için)

### 1. Depoyu Klonlayın

```bash
git clone https://github.com/yourusername/receiptmind-ai.git
cd receiptmind-ai
```

### 2. Sanal Ortam Oluşturun

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
```

### 3. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

**requirements.txt** içeriği:
```txt
llama-cpp-python==0.2.20
sentence-transformers==2.2.2
faiss-cpu==1.7.4
streamlit==1.28.0
plotly==5.17.0
pandas==2.1.0
numpy==1.24.3
pillow==10.0.0
watchdog==3.0.0
scikit-learn==1.3.0
statsmodels==0.14.0
```

### 4. LLM Modelini İndirin

```bash
# Qwen2.5-7B-Instruct GGUF modelini indirin
# Hugging Face: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF

# models/ klasörüne yerleştirin:
models/
  └── qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf
```

### 5. Proje Yapısını Oluşturun

```bash
python -c "from pathlib import Path; [Path(p).mkdir(parents=True, exist_ok=True) for p in ['data/inbox', 'data/processed', 'data/index', 'data/reports', 'models', 'prompts']]"
```

---

## 💻 Kullanım

### Web Arayüzünü Başlatma

```bash
# Windows
start_app.bat

# Manuel başlatma
streamlit run src/ui/app.py
```

Tarayıcınızda `http://localhost:8501` adresine gidin.

### Komut Satırı Kullanımı

#### 1. Örnek Veri Oluşturma

```bash
python src/make_sample_receipts.py
```

#### 2. PDF İşleme

```bash
python src/ingest_pdf.py data/inbox/ornek_fis_a101_2025-11-25.pdf
```

#### 3. Veritabanı İndeksleme

```bash
python src/index_faiss.py
```

#### 4. Rapor Oluşturma

```bash
python src/report_monthly.py
```

#### 5. Soru Sorma

```bash
python src/assistant.py
# Soru: Kasım ayında kahveye ne kadar harcadım?
```

### 🔄 Tam Pipeline

```bash
python src/pipeline_all.py
```

Bu komut şunları yapar:
1. Tüm PDF'leri işler
2. FAISS indeksini oluşturur
3. Aylık raporları üretir
4. Analizleri çalıştırır

---

## 📁 Proje Yapısı

```
receiptmind-ai/
├── 📂 data/
│   ├── inbox/              # Yeni PDF'ler
│   ├── processed/          # İşlenmiş PDF'ler
│   ├── index/              # FAISS vektör indeksi
│   ├── reports/            # CSV raporları
│   └── receipts.db         # SQLite veritabanı
├── 📂 models/
│   └── qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf
├── 📂 prompts/
│   ├── answer_with_citations_tr.txt
│   └── extract_receipt_items.txt
├── 📂 src/
│   ├── 📂 ai/
│   │   └── model_manager.py      # LLM yönetimi
│   ├── 📂 analytics/
│   │   ├── anomaly.py            # Anomali tespiti
│   │   ├── budget.py             # Bütçe takibi
│   │   ├── prediction.py         # Harcama tahmini
│   │   └── subscription.py       # Abonelik tespiti
│   ├── 📂 ui/
│   │   └── app.py                # Streamlit arayüzü
│   ├── assistant.py              # Ana RAG motoru
│   ├── ingest_pdf.py             # PDF işleme
│   ├── index_faiss.py            # Vektör indeksleme
│   ├── vlm.py                    # Vision LLM
│   ├── db.py                     # Veritabanı
│   ├── categorize.py             # Kategorizasyon
│   └── ...
├── README.md
├── requirements.txt
├── start_app.bat
└── task.md
```

---

## 🛠️ Teknolojiler

### 🤖 AI/ML

| Teknoloji | Kullanım Alanı | Versiyon |
|-----------|----------------|----------|
| **Qwen2.5-7B** | Doğal dil anlama ve üretme | 7B parametreli |
| **llama-cpp-python** | LLM inference | 0.2.20+ |
| **Sentence Transformers** | Metin embedding | 2.2.2+ |
| **FAISS** | Vektör arama | 1.7.4+ |
| **scikit-learn** | Anomali tespiti | 1.3.0+ |
| **statsmodels** | Zaman serisi analizi (ARIMA) | 0.14.0+ |

### 🌐 Web & UI

| Teknoloji | Kullanım Alanı |
|-----------|----------------|
| **Streamlit** | Web arayüzü |
| **Plotly** | İnteraktif grafikler |
| **Watchdog** | Dosya izleme |

### 💾 Veri

| Teknoloji | Kullanım Alanı |
|-----------|----------------|
| **SQLite** | İlişkisel veritabanı |
| **Pandas** | Veri manipülasyonu |
| **NumPy** | Sayısal hesaplamalar |

---

## 🎨 Gelişmiş Özellikler

### 1. Vision Language Model (VLM) Desteği

```python
from src.vlm import extract_with_vlm

# Görsel fiş okuma
items = extract_with_vlm("receipt.jpg")
```

### 2. Otomatik İnbox İzleme

```python
# src/ui/app.py içinde Watchdog ile otomatik izleme
# data/inbox/ klasörüne yeni PDF eklendiğinde otomatik işlenir
```

### 3. Çoklu Dil Desteği

```python
# Türkçe ve İngilizce prompt desteği
# Çok dilli embedding modeli
```

### 4. Akıllı Sorgu Ayrıştırma

```python
from src.query_parse import parse_query

# "Kasım 2025'te gıda kategorisinde ne kadar harcadım?"
spec = parse_query(question)
# QuerySpec(
#   product_term=None,
#   category="gıda",
#   date_from="2025-11-01",
#   date_to="2025-11-30"
# )
```

### 5. Performans Optimizasyonları

- **Model Caching**: LLM ve embedding modelleri tek seferlik yüklenir
- **Batch Processing**: Toplu PDF işleme
- **Lazy Loading**: İhtiyaç duyulduğunda model yükleme
- **FAISS Indexing**: Hızlı vektör arama (milisaniyeler)

---

## 📊 Örnek Kullanım Senaryoları

### Senaryo 1: Aylık Harcama Analizi

```
Kullanıcı: "2025-11 ayında toplam ne kadar harcadım?"

ReceiptMind AI:
📊 Kasım 2025 Harcama Özeti:
- Toplam: 12,450.75 TL
- İşlem Sayısı: 87
- Ortalama: 143.11 TL/işlem

Kategori Dağılımı:
🍔 Gıda: 4,200 TL (33.7%)
🚗 Ulaşım: 2,800 TL (22.5%)
🎬 Eğlence: 1,500 TL (12.0%)
...
```

### Senaryo 2: Ürün Bazlı Sorgulama

```
Kullanıcı: "Kahveye kaç kez para harcadım?"

ReceiptMind AI:
☕ Kahve Harcama Raporu:
- Toplam: 23 kez
- Tutar: 1,150 TL
- Ortalama: 50 TL/kahve

En Sık Gittiğiniz Yerler:
1. Starbucks: 890 TL (12 kez)
2. Kahve Dünyası: 180 TL (8 kez)
3. Espresso Lab: 80 TL (3 kez)
```

### Senaryo 3: Abonelik Tespiti

```
Dashboard → Abonelikler:

🔄 Tespit Edilen Abonelikler:
1. Netflix (99.99 TL/ay)
   - Son ödeme: 2025-12-01
   - Toplam: 599.94 TL (6 ay)

2. Spotify (34.99 TL/ay)
   - Son ödeme: 2025-12-05
   - Toplam: 419.88 TL (12 ay)

💡 İpucu: Aylık 134.98 TL abonelik harcamanız var.
```

### Senaryo 4: Anomali Uyarısı

```
⚠️ Anomali Tespit Edildi!

Gıda kategorisinde alışılmadık harcama:
- Bu ay: 6,200 TL
- Ortalama: 4,000 TL
- Artış: %55 (%150 normalin üstünde)

Olası nedenler:
- Özel etkinlik/davet
- Toplu alışveriş
- Fiyat artışları
```

---

## 🔧 Yapılandırma

### LLM Ayarları

`src/assistant.py` içinde:

```python
LLM_MODEL_PATH = r"models\qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"

def get_llm():
    return Llama(
        model_path=LLM_MODEL_PATH,
        n_ctx=2048,        # Bağlam penceresi
        n_threads=8,       # CPU thread sayısı
        n_gpu_layers=-1,   # GPU kullanımı (varsa)
        verbose=False
    )
```

### Embedding Modeli

```python
EMB_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
```

### Kategori Eşlemeleri

`src/categorize.py` içinde:

```python
CATEGORY_MAP = {
    "gıda": ["market", "bakkal", "manav", "kasap", ...],
    "ulaşım": ["benzin", "akaryakıt", "otobus", ...],
    "eğlence": ["sinema", "konser", "cafe", ...],
    ...
}
```

---

## 🧪 Test

### Örnek Veri ile Test

```bash
# 1. Örnek fişler oluştur
python src/make_sample_receipts.py

# 2. Pipeline'ı çalıştır
python src/pipeline_all.py

# 3. Web arayüzünü başlat
streamlit run src/ui/app.py
```

### Manuel Test

```bash
# Tek bir PDF'i test et
python src/ingest_pdf.py data/inbox/test_receipt.pdf

# Sorgu test et
python src/assistant.py
```

---

## 🤝 Katkıda Bulunma

Katkılarınızı bekliyoruz! Lütfen şu adımları izleyin:

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

### Geliştirme Yol Haritası

- [ ] Multi-user desteği
- [ ] Cloud deployment (AWS/Azure)
- [ ] Mobile app (React Native)
- [ ] Daha fazla entegrasyon (WhatsApp, Slack)
- [ ] Gelişmiş ML modelleri (GPT-4V, Claude)
- [ ] Blockchain tabanlı fiş doğrulama
- [ ] Sesli asistan entegrasyonu

---

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

---

## 👨‍💻 Geliştirici

**ReceiptMind AI** - Kişisel finans yönetimini yapay zeka ile birleştiren yeni nesil platform.

---

## 🙏 Teşekkürler

- [Qwen Team](https://github.com/QwenLM) - Harika LLM için
- [Sentence Transformers](https://www.sbert.net/) - Embedding modelleri için
- [FAISS](https://github.com/facebookresearch/faiss) - Vektör arama için
- [Streamlit](https://streamlit.io/) - Web framework için

---

## 📞 İletişim

Sorularınız veya önerileriniz için:
- 📧 Email: [your-email@example.com](mailto:your-email@example.com)
- 🐙 GitHub Issues: [Issues](https://github.com/yourusername/receiptmind-ai/issues)
- 💬 Discussions: [Discussions](https://github.com/yourusername/receiptmind-ai/discussions)

---

<div align="center">

**⭐ Projeyi beğendiyseniz yıldız vermeyi unutmayın! ⭐**

Made with ❤️ and 🤖 AI

</div>

# 💰 AI Financial Tracker Bot

Bot Telegram pintar untuk mencatat keuangan (Pengeluaran, Pemasukan, Tabungan) yang terintegrasi langsung dengan **Google Sheets**. Dilengkapi dengan **AI Categorization** (Machine Learning) dan **Visualisasi Data** (Grafik).

![Bot Demo](https://img.shields.io/badge/Status-Active-success) ![Python](https://img.shields.io/badge/Python-3.11-blue)

## ✨ Fitur Utama

1.  **Pencatatan Mudah**: Cukup ketik `/pengeluaran 50000 makan siang`, bot otomatis mencatat.
2.  **🧠 AI Categorization**: Bot menggunakan Machine Learning (TF-IDF + SGD) untuk menebak kategori transaksi otomatis.
    *   *Contoh:* Ketik "beli bensin", bot otomatis masukin ke kategori "Transport".
    *   Semakin sering dipakai, AI semakin pintar!
3.  **📊 Analytics & Charts**:
    *   Perintah `/bulanan` menampilkan laporan lengkap dengan **Pie Chart** dan **Grafik Tren Harian**.
    *   Perintah `/stats` untuk melihat dashboard statistik.
4.  **☁️ Google Sheets Integration**: Semua data tersimpan aman di Google Sheets milikmu sendiri. Bisa diedit manual kapan saja.
5.  **Budget Alert**: Peringatan jika pengeluaran melebihi budget per kategori.

---

## 🚀 Cara Penggunaan

### 1. Perintah Dasar
| Perintah | Format | Contoh |
|----------|--------|--------|
| **Pengeluaran** | `/pengeluaran [jumlah] [ket]` | `/pengeluaran 25000 nasi padang` |
| **Pemasukan** | `/pemasukan [jumlah] [ket]` | `/pemasukan 5000000 gaji agustus` |
| **Tabungan** | `/nabung [jumlah] [ket]` | `/nabung 500000 dana darurat` |
| **Set Budget** | `/setbudget [kategori] [jumlah]` | `/setbudget Makanan 1500000` |

### 2. Laporan & Analisis
| Perintah | Deskripsi |
|----------|-----------|
| `/ringkasan` | Ringkasan transaksi hari ini. |
| `/bulanan` | Laporan bulan berjalan + **Grafik**. |
| `/stats` | Dashboard statistik (Rata-rata pengeluaran, Top kategori, dll). |

### 3. Tips AI
*   Bot memprioritaskan **Kata Kunci** yang ada di Google Sheet (Tab `Categories`, Kolom `Keywords`).
*   Jika tidak ada kata kunci yang cocok, AI akan mencoba menebak berdasarkan history transaksimu.
*   Jika AI salah tebak, Anda bisa koreksi manual di Google Sheet, dan AI akan belajar dari situ untuk next time.

---

## 🛠️ Instalasi & Setup (Lokal)

### Prerequisites
*   Python 3.10+
*   Akun Google Cloud Platform (untuk Google Sheets API)
*   Bot Token dari @BotFather

### Langkah-langkah
1.  **Clone Repository**
    ```bash
    git clone https://github.com/username/financial-tracker-bot.git
    cd financial-tracker-bot
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup Google Sheets**
    *   Buat Google Sheet baru.
    *   Buat 4 Tab: `Transactions`, `Categories`, `Monthly_Summary`, `Analytics`.
    *   Isi header kolom sesuai standar (Lihat `inspect_sheet.py` untuk detail struktur).

4.  **Setup Credentials**
    *   Dapatkan `credentials.json` (Service Account Key) dari Google Cloud Console.
    *   Simpan file `credentials.json` di root folder project.
    *   **PENTING**: Share Google Sheet kamu (tombol Share di pojok kanan atas) ke email service account (e.g., `bot-email@project-id.iam.gserviceaccount.com`).

5.  **Konfigurasi Environment (.env)**
    Buat file `.env` dan isi:
    ```ini
    TELEGRAM_BOT_TOKEN=your_bot_token_here
    GOOGLE_SHEET_ID=your_spreadsheet_id_here
    GOOGLE_APPLICATION_CREDENTIALS=credentials.json
    ```

6.  **Jalankan Bot**
    ```bash
    python telegram_bot.py
    ```

---

## 🌐 Deployment (Railway / Fly.io)

Untuk deploy ke server cloud, kita tidak bisa upload file `credentials.json` langsung karena alasan keamanan (dan biasanya di-ignore git). Kita pakai trik **Base64**.

1.  **Encode Credentials**
    Di komputer lokal, jalankan python:
    ```python
    import base64
    print(base64.b64encode(open("credentials.json", "rb").read()).decode())
    ```
    Copy output string panjang tersebut.

2.  **Set Environment Variables di Server**
    Di dashboard Railway/Fly.io, tambahkan variable:
    *   `TELEGRAM_BOT_TOKEN`: (Token Bot Anda)
    *   `GOOGLE_SHEET_ID`: (ID Spreadsheet)
    *   `GOOGLE_CREDENTIALS_BASE64`: (Paste string Base64 tadi di sini)

3.  **Deploy**
    Connect repo GitHub Anda dan deploy. Bot akan otomatis mendeteksi variable Base64 dan menggunakannya untuk login.

---

## 📂 Struktur Project

*   `telegram_bot.py`: Main script bot & command handlers.
*   `google_sheets_handler.py`: Logic koneksi ke Google Sheets.
*   `model_categorization.py`: Modul AI (Scikit-Learn) untuk klasifikasi otomatis.
*   `analytics_engine.py`: Modul visualisasi data (Matplotlib/Seaborn).
*   `requirements.txt`: Daftar library python yang dibutuhkan.
*   `runtime.txt`: Versi python untuk deployment.
*   `Procfile`: Command untuk start bot di server (Heroku/Railway).

---

## 🐛 Troubleshooting

*   **Error "ModuleNotFoundError: No module named 'seaborn'"**: Pastikan `seaborn` ada di `requirements.txt`.
*   **Tanggal Tidak Valid di Sheet**: Bot sekarang menggunakan format `YYYY-MM-DD HH:MM:SS` yang kompatibel dengan Google Sheet. Pastikan kolom format di Sheet diset ke "Date Time".
*   **AI Salah Kategori**: Cek tab `Categories` di Sheet. Pastikan kolom `Keywords` sudah diisi untuk kategori yang sering dipakai (pisahkan koma, misal: `nasgor,soto,makan`).

---

**Enjoy your Financial Freedom! 💸**

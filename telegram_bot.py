from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.request import HTTPXRequest
from telegram.error import BadRequest
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from google_sheets_handler import SheetsManager
from model_categorization import TransactionClassifier
from analytics_engine import AnalyticsVisualizer
import pandas as pd
import io

load_dotenv()

# Config
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
SHEET_ID = os.getenv('GOOGLE_SHEET_ID')

# Initialize
# Initialize
sheets = SheetsManager(SHEET_ID)
ai_classifier = TransactionClassifier()
visualizer = AnalyticsVisualizer()

# Train AI on startup
print("🧠 Training AI model...")
training_data = sheets.get_training_data()
if training_data:
    ai_classifier.train(training_data)
else:
    print("⚠️ No training data found.")

# ==================== COMMAND HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = """
🤖 *Selamat datang di Financial Tracker Bot!*

📝 *Cara Pakai:*
- `/pengeluaran [jumlah] [keterangan]` - Catat pengeluaran
- `/pemasukan [jumlah] [keterangan]` - Catat pemasukan  
- `/nabung [jumlah] [keterangan]` - Catat tabungan

📊 *Laporan:*
- `/ringkasan` - Ringkasan hari ini
- `/bulanan` - Laporan bulan ini
- `/stats` - Analytics dashboard

⚙️ *Pengaturan:*
- `/setbudget [kategori] [jumlah]` - Update budget limit

💡 *Contoh:*
`/pengeluaran 50000 makan siang warteg`
`/pemasukan 5000000 gaji bulanan`
`/nabung 500000 tabungan rutin`

Bot ini otomatis mendeteksi kategori dengan AI! 🧠
    """
    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = ' '.join(context.args)
        parts = args.split(' ', 1)
        
        if len(parts) < 2:
            await update.message.reply_text(
                "❌ Format salah!\n\nContoh yang benar:\n`/pengeluaran 50000 makan siang`",
                parse_mode='Markdown'
            )
            return
        
        try:
            amount = int(parts[0].replace('.', '').replace(',', ''))
        except ValueError:
            await update.message.reply_text(
                "❌ Jumlah harus berupa angka!\n\nContoh: `/pengeluaran 50000 makan siang`",
                parse_mode='Markdown'
            )
            return

        description = parts[1]
        user_id = update.effective_user.id
        
        # AI Categorization (simple keyword matching)
        # 1. Coba AI Prediction
        ai_category, ai_conf = ai_classifier.predict(description)
        
        # 2. Coba Keyword Matching (Rules-based) -> lebih prioritas jika pasti
        kw_category, kw_conf = sheets.simple_categorize(description)
        
        # Logika Keputusan:
        # - Jika Keyword match sangat kuat (>0.8), pakai Keyword (misal: "gaji", "makan")
        # - Jika AI sangat yakin (>0.6) DAN Keyword lemah, pakai AI
        # - Default: Lainnya
        
        if kw_conf >= 0.8:
            category = kw_category
            confidence = kw_conf
            print(f"✅ Rules Applied: {category} ({confidence:.2f})")
        elif ai_category and ai_conf > 0.5:
            category = ai_category
            confidence = ai_conf
            print(f"🤖 AI Selected: {category} ({confidence:.2f})")
        else:
            category = kw_category # Default 'Lainnya' 0.5
            confidence = kw_conf
            print(f"⚠️ Low Confidence, Fallback: {category}")
        
        # Simpan sementara di context
        # Use simple numeric string for ID to avoid timezone complexity in ID, or just keep it simple
        transaction_id = f"TRX-{datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%Y%m%d%H%M%S')}"
        transaction = {
            'id': transaction_id,
            'timestamp': datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': user_id,
            'type': 'expense',
            'amount': amount,
            'category': category,
            'description': description,
            'ai_confidence': confidence,
            'payment_method': '-'
        }
        
        context.user_data['pending_trx'] = transaction
        
        # Kirim Konfirmasi Button
        keyboard = [
            [InlineKeyboardButton("✅ Simpan", callback_data='confirm_trx')],
            [InlineKeyboardButton("✏️ Ganti Kategori", callback_data='edit_category')],
            [InlineKeyboardButton("❌ Batal", callback_data='cancel_trx')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        confidence_emoji = "🧠" if confidence > 0.5 else "" # Added for the new message format
        
        await update.message.reply_text(
            f"Konfirmasi✅ *Pengeluaran tercatat!*

💰 Rp {amount:,}
� Kategori: {category} {confidence_emoji} ({int(confidence*100)}%)
📝 {description}
📅 {datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%d %b %Y, %H:%M')}
",
            reply_markup=reply_markup # Keep reply_markup for consistency, though the message implies it's already saved.
                                      # Assuming this is a pre-confirmation message that was updated.
            , parse_mode='Markdown' # Added parse_mode for markdown formatting
        )
        
        # sheets.add_transaction(transaction) -> Moved to button_handler
        # sheets.update_monthly_summary... -> Moved to button_handler
        # sheets.update_analytics... -> Moved to button_handler
        
        # OLD CODE REMOVED
        # Response logic moved to button_handler
        
        
    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan sistem.\nError: {str(e)}")
        print(f"Error in add_expense: {e}")

async def add_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = ' '.join(context.args)
        parts = args.split(' ', 1)
        
        if len(parts) < 2:
            await update.message.reply_text(
                "❌ Format salah!\n\nContoh yang benar:\n`/pemasukan 5000000 gaji bulanan`",
                parse_mode='Markdown'
            )
            return
        
        try:
            amount = int(parts[0].replace('.', '').replace(',', ''))
        except ValueError:
            await update.message.reply_text(
                "❌ Jumlah harus berupa angka!\n\nContoh: `/pemasukan 5000000 gaji`",
                parse_mode='Markdown'
            )
            return

        description = parts[1]
        user_id = update.effective_user.id
        
        # Kategorisasi income
        category, confidence = sheets.simple_categorize(description)
        if category not in ['Gaji', 'Bonus']:
            category = 'Gaji'  # Default untuk income
        
        transaction_id = f"TRX-{datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%Y%m%d%H%M%S')}"
        
        transaction = {
            'id': transaction_id,
            'timestamp': datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': user_id,
            'type': 'income',
            'amount': amount,
            'category': category,
            'description': description,
            'ai_confidence': confidence,
            'payment_method': '-'
        }
        
        context.user_data['pending_trx'] = transaction
        
        keyboard = [
            [InlineKeyboardButton("✅ Simpan", callback_data='confirm_trx')],
            [InlineKeyboardButton("❌ Batal", callback_data='cancel_trx')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Konfirmasi Pemasukan?\n\n💰 Rp {amount:,}\n📝 {description}\n📂 {category}",
            reply_markup=reply_markup
        )
        
        # OLD CODE REMOVED
        
    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan sistem.\nError: {str(e)}")
        print(f"Error in add_income: {e}")

async def add_saving(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = ' '.join(context.args)
        parts = args.split(' ', 1)
        
        if len(parts) < 2:
            await update.message.reply_text(
                "❌ Format salah!\n\nContoh yang benar:\n`/nabung 500000 tabungan bulanan`",
                parse_mode='Markdown'
            )
            return
        
        try:
            amount = int(parts[0].replace('.', '').replace(',', ''))
        except ValueError:
            await update.message.reply_text(
                "❌ Jumlah harus berupa angka!\n\nContoh: `/nabung 500000 tabungan`",
                parse_mode='Markdown'
            )
            return

        description = parts[1]
        user_id = update.effective_user.id
        
        transaction_id = f"TRX-{datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%Y%m%d%H%M%S')}"
        
        transaction = {
            'id': transaction_id,
            'timestamp': datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': user_id,
            'type': 'saving',
            'amount': amount,
            'category': 'Tabungan Rutin',
            'description': description,
            'ai_confidence': 1.0,
            'payment_method': '-'
        }
        
        context.user_data['pending_trx'] = transaction
        
        keyboard = [
            [InlineKeyboardButton("✅ Simpan", callback_data='confirm_trx')],
            [InlineKeyboardButton("❌ Batal", callback_data='cancel_trx')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Konfirmasi Tabungan?\n\n💰 Rp {amount:,}\n📝 {description}",
            reply_markup=reply_markup
        )
        
        # OLD CODE REMOVED
        
    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan sistem.\nError: {str(e)}")
        print(f"Error in add_saving: {e}")

async def daily_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        today = datetime.now(ZoneInfo('Asia/Jakarta')).date()
        
        transactions = sheets.get_transactions_by_date(user_id, today)
        
        if not transactions:
            await update.message.reply_text("📊 Belum ada transaksi hari ini.")
            return
        
        df = pd.DataFrame(transactions)
        
        income = df[df['type'] == 'income']['amount'].sum()
        expense = df[df['type'] == 'expense']['amount'].sum()
        saving = df[df['type'] == 'saving']['amount'].sum()
        
        expense_by_cat = df[df['type'] == 'expense'].groupby('category')['amount'].agg(['sum', 'count'])
        
        cat_breakdown = "\n".join([
            f"   • {cat}: Rp {row['sum']:,} ({int(row['count'])} transaksi)"
            for cat, row in expense_by_cat.iterrows()
        ]) if not expense_by_cat.empty else "   -"
        
        net = income - expense - saving
        net_emoji = "🟢" if net >= 0 else "🔴"
        
        response = f"""
📊 *RINGKASAN HARI INI*
📅 {today.strftime('%d %b %Y')}

✅ Pemasukan: Rp {income:,}
❌ Pengeluaran: Rp {expense:,}
{cat_breakdown}
💰 Tabungan: Rp {saving:,}

📈 Net: {net_emoji} Rp {net:,}
        """
        
        await update.message.reply_text(response.strip(), parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in daily_summary: {e}")

async def monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        current_month = datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%Y-%m')
        
        transactions = sheets.get_transactions_by_month(user_id, current_month)
        
        if not transactions:
            await update.message.reply_text("📊 Belum ada transaksi bulan ini.")
            return
        
        df = pd.DataFrame(transactions)
        
        income = df[df['type'] == 'income']['amount'].sum()
        expense = df[df['type'] == 'expense']['amount'].sum()
        saving = df[df['type'] == 'saving']['amount'].sum()
        
        # Top 3 categories
        expense_by_cat = df[df['type'] == 'expense'].groupby('category')['amount'].sum().sort_values(ascending=False)
        top_3 = expense_by_cat.head(3)
        
        top_3_text = "\n".join([
            f"{i+1}. {cat}: Rp {amt:,}"
            for i, (cat, amt) in enumerate(top_3.items())
        ]) if not top_3.empty else "-"
        
        net = income - expense - saving
        net_emoji = "🟢" if net >= 0 else "🔴"
        
        response = f"""
📊 *LAPORAN BULANAN*
📅 {datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%B %Y')}

💰 Total Pemasukan: Rp {income:,}
💸 Total Pengeluaran: Rp {expense:,}
🏦 Total Tabungan: Rp {saving:,}
📈 Saldo Bersih: {net_emoji} Rp {net:,}

🔥 *Top 3 Pengeluaran:*
{top_3_text}

📌 Total Transaksi: {len(transactions)}

Ketik /stats untuk analytics lebih detail 📊
        """
        
        await update.message.reply_text(response.strip(), parse_mode='Markdown')
        
        # Kirim Visualisasi Grafik
        try:
            chart_buffer = visualizer.generate_monthly_report(transactions, datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%B %Y'))
            if chart_buffer:
                await update.message.reply_photo(
                    photo=chart_buffer,
                    caption=f"📈 Visualisasi Pengeluaran - {datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%B %Y')}"
                )
        except Exception as e:
            print(f"❌ Error generating chart: {e}")
            # Jangan crash hanya karena grafik gagal, cukup log saja
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in monthly_report: {e}")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan analytics metrics"""
    try:
        user_id = update.effective_user.id
        
        result = sheets.sheet.values().get(
            spreadsheetId=sheets.spreadsheet_id,
            range='Analytics!A2:D'
        ).execute()
        
        rows = result.get('values', [])
        
        metrics = {}
        for row in rows:
            if len(row) >= 3 and str(row[0]) == str(user_id):
                metrics[row[1]] = row[2]
        
        if not metrics:
            await update.message.reply_text("📊 Belum ada data analytics. Tambahkan transaksi terlebih dahulu!")
            return
        
        response = f"""
📊 *ANALYTICS DASHBOARD*

💸 *Pengeluaran:*
- Rata-rata harian: Rp {float(metrics.get('Avg_Daily_Expense', 0)):,.0f}
- Trend bulan ini: {metrics.get('Spending_Trend', 'N/A')}
- Top kategori: {metrics.get('Top_Expense_Category', '-')}

💰 *Pemasukan:*
- Rata-rata harian: Rp {float(metrics.get('Avg_Daily_Income', 0)):,.0f}

🏦 *Tabungan:*
- Savings rate: {metrics.get('Savings_Rate', '0%')}

⚠️ *Budget Alerts:*
- Kategori over budget: {metrics.get('Budget_Alert_Count', '0')}

📈 *Activity:*
- Total transaksi: {metrics.get('Total_Transactions', '0')}
- Transaksi terakhir: {metrics.get('Last_Transaction_Date', '-')}
        """
        
        await update.message.reply_text(response.strip(), parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in show_stats: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 *PANDUAN LENGKAP*

*Input Transaksi:*
- `/pengeluaran [jumlah] [keterangan]`
  Contoh: `/pengeluaran 50000 makan siang`

- `/pemasukan [jumlah] [keterangan]`
  Contoh: `/pemasukan 5000000 gaji bulanan`

- `/nabung [jumlah] [keterangan]`
  Contoh: `/nabung 500000 tabungan rutin`

*Laporan:*
- `/ringkasan` - Ringkasan hari ini
- `/bulanan` - Laporan bulan ini
- `/bulanan` - Laporan bulan ini
- `/stats` - Analytics dashboard

*Pengaturan Budget:*
- `/setbudget [kategori] [jumlah]`
  Contoh: `/setbudget Makanan 1500000`

*Tips:*
- Bot otomatis mendeteksi kategori
- "Simpan" hanya jika kategori sudah benar. Gunakan tombol "Ganti Kategori" jika salah.
- Gunakan kata kunci seperti "makan", "bensin", "gaji"
- Batas budget dapat di-set di Google Sheets

Butuh bantuan? Hubungi developer! 🚀
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def set_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set budget untuk kategori tertentu"""
    try:
        args = ' '.join(context.args)
        parts = args.split(' ', 1)
        
        if len(parts) < 2:
            await update.message.reply_text(
                "❌ Format salah!\n\nContoh: `/setbudget Makanan 1500000`",
                parse_mode='Markdown'
            )
            return
            
        category = parts[0]
        try:
            amount = int(parts[1].replace('.', '').replace(',', ''))
        except ValueError:
            await update.message.reply_text("❌ Jumlah budget harus angka!")
            return
            
        success, msg = sheets.update_budget(category, amount)
        if success:
             await update.message.reply_text(f"✅ {msg}")
        else:
             await update.message.reply_text(f"❌ {msg}")
             
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interactive buttons"""
    query = update.callback_query
    await query.answer() # Close loading state
    
    data = query.data
    
    # 1. CONFIRM
    if data == 'confirm_trx':
        trx = context.user_data.get('pending_trx')
        if not trx:
            try:
                await query.edit_message_text("❌ Data transaksi kadaluarsa.")
            except BadRequest as e:
                if "Message is not modified" not in str(e):
                    raise
            return

        # Simpan ke Sheets
        sheets.add_transaction(trx)
        
        # Update Analytics (Async optimization: do it after replying?)
        # For responsiveness, reply first then update stats in background if possible, 
        # Update Monthly Summary & Analytics
        current_month = datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%Y-%m')
        sheets.update_monthly_summary(trx['user_id'], current_month)
        sheets.update_analytics(trx['user_id'])
        
        # Get budget status if expense
        budget_msg = ""
        if trx['type'] == 'expense':
             budget_info = sheets.get_category_budget_status(trx['category'], trx['user_id'])
             if budget_info:
                 remaining = budget_info['remaining']
                 if remaining < 0:
                     budget_msg = f"\n⚠️ *Budget Over*: Rp {abs(remaining):,}"
                 elif budget_info['percentage'] > 80:
                     budget_msg = f"\n💡 Sisa Budget: Rp {remaining:,}"

        try:
            await query.edit_message_text(
                f"✅ *Tersimpan!*\n\n{trx['description']}\nRp {trx['amount']:,}\n📂 {trx['category']}{budget_msg}", 
                parse_mode='Markdown'
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise
        context.user_data.pop('pending_trx', None)

    # 2. CANCEL
    elif data == 'cancel_trx':
        try:
            await query.edit_message_text("❌ Transaksi dibatalkan.")
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise
        context.user_data.pop('pending_trx', None)

    # 3. EDIT CATEGORY (Request List)
    elif data == 'edit_category':
        # Show predefined categories
        categories = ['Makanan & Minuman', 'Transport', 'Belanja', 'Tagihan', 'Hiburan', 'Kesehatan', 'Pendidikan', 'Lainnya']
        
        keyboard = []
        row = []
        for cat in categories:
            row.append(InlineKeyboardButton(cat, callback_data=f"set_cat|{cat}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row: keyboard.append(row)
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await query.edit_message_text("📂 Pilih Kategori Baru:", reply_markup=reply_markup)
        except BadRequest as e:
                if "Message is not modified" not in str(e):
                    raise

    # 4. SET NEW CATEGORY
    elif data.startswith('set_cat|'):
        try:
            new_cat = data.split('|')[1]
            trx = context.user_data.get('pending_trx')
            
            if trx:
                trx['category'] = new_cat
                # Re-confirm
                keyboard = [
                    [InlineKeyboardButton("✅ Simpan", callback_data='confirm_trx')],
                    [InlineKeyboardButton("✏️ Ganti Kategori", callback_data='edit_category')],
                     [InlineKeyboardButton("❌ Batal", callback_data='cancel_trx')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Escape markdown special characters for category name
                safe_cat = new_cat.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`')
                
                try:
                    await query.edit_message_text(
                        f"🔄 Kategori diubah jadi: *{safe_cat}*\n\nSimpan sekarang?",
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
                except BadRequest as e:
                    if "Message is not modified" not in str(e):
                        raise
            else:
                try:
                    await query.edit_message_text("❌ Sesi transaksi telah berakhir. Silakan input ulang.")
                except BadRequest as e:
                    if "Message is not modified" not in str(e):
                        raise
        except Exception as e:
            print(f"Error setting category: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}")
    

# ==================== MAIN ====================

def main():
    print("🤖 Initializing bot...")
    
    # Test connection
    if not sheets.test_connection():
        print("❌ Failed to connect to Google Sheets. Check credentials!")
        return
    
    print("✅ Google Sheets connected")
    print(f"📱 Bot token: {TELEGRAM_TOKEN[:10]}...")
    
    t_request = HTTPXRequest(connection_pool_size=8, connect_timeout=60, read_timeout=60)
    app = Application.builder().token(TELEGRAM_TOKEN).request(t_request).build()
    
    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("pengeluaran", add_expense))
    app.add_handler(CommandHandler("pemasukan", add_income))
    app.add_handler(CommandHandler("nabung", add_saving))
    app.add_handler(CommandHandler("ringkasan", daily_summary))
    app.add_handler(CommandHandler("bulanan", monthly_report))
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(CommandHandler("setbudget", set_budget))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🚀 Bot is running...")
    print("Press Ctrl+C to stop")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
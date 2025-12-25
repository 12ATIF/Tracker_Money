from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
from datetime import datetime
from dotenv import load_dotenv
from google_sheets_handler import SheetsManager
import pandas as pd

load_dotenv()

# Config
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
SHEET_ID = os.getenv('GOOGLE_SHEET_ID')

# Initialize
sheets = SheetsManager(SHEET_ID)

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
        category, confidence = sheets.simple_categorize(description)
        
        # Simpan transaksi
        transaction_id = f"TRX-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        transaction = {
            'id': transaction_id,
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'type': 'expense',
            'amount': amount,
            'category': category,
            'description': description,
            'ai_confidence': confidence,
            'payment_method': '-'
        }
        
        sheets.add_transaction(transaction)
        
        # Update Monthly Summary & Analytics
        current_month = datetime.now().strftime('%Y-%m')
        sheets.update_monthly_summary(user_id, current_month)
        sheets.update_analytics(user_id)
        
        # Get budget status
        budget_info = sheets.get_category_budget_status(category, user_id)
        
        confidence_emoji = "🔥" if confidence > 0.85 else "✅" if confidence > 0.7 else "⚠️"
        
        response = f"""
✅ *Pengeluaran tercatat!*

💰 Rp {amount:,}
📂 Kategori: {category} {confidence_emoji} ({int(confidence*100)}%)
📝 {description}
📅 {datetime.now().strftime('%d %b %Y, %H:%M')}
"""
        
        if budget_info:
            remaining = budget_info['remaining']
            percentage = budget_info['percentage']
            
            if remaining < 0:
                response += f"\n⚠️ *Budget {category} terlampaui!*\nOver budget: Rp {abs(remaining):,}"
            elif percentage > 80:
                response += f"\n💡 Sisa budget {category}: Rp {remaining:,} ({100-percentage:.0f}% tersisa)"
            else:
                response += f"\n💡 Sisa budget {category}: Rp {remaining:,}"
        
        await update.message.reply_text(response.strip(), parse_mode='Markdown')
        
        
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
        
        transaction_id = f"TRX-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        transaction = {
            'id': transaction_id,
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'type': 'income',
            'amount': amount,
            'category': category,
            'description': description,
            'ai_confidence': confidence,
            'payment_method': '-'
        }
        
        sheets.add_transaction(transaction)
        
        # Update summary & analytics
        current_month = datetime.now().strftime('%Y-%m')
        sheets.update_monthly_summary(user_id, current_month)
        sheets.update_analytics(user_id)
        
        response = f"""
✅ *Pemasukan tercatat!*

💰 Rp {amount:,}
📂 Kategori: {category}
📝 {description}
📅 {datetime.now().strftime('%d %b %Y, %H:%M')}
        """
        
        await update.message.reply_text(response.strip(), parse_mode='Markdown')
        
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
        
        transaction_id = f"TRX-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        transaction = {
            'id': transaction_id,
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'type': 'saving',
            'amount': amount,
            'category': 'Tabungan Rutin',
            'description': description,
            'ai_confidence': 1.0,
            'payment_method': '-'
        }
        
        sheets.add_transaction(transaction)
        
        # Update summary & analytics
        current_month = datetime.now().strftime('%Y-%m')
        sheets.update_monthly_summary(user_id, current_month)
        sheets.update_analytics(user_id)
        
        response = f"""
✅ *Tabungan tercatat!*

💰 Rp {amount:,}
📝 {description}
📅 {datetime.now().strftime('%d %b %Y, %H:%M')}

Hebat! Terus konsisten menabung! 💪
        """
        
        await update.message.reply_text(response.strip(), parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan sistem.\nError: {str(e)}")
        print(f"Error in add_saving: {e}")

async def daily_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        today = datetime.now().date()
        
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
        current_month = datetime.now().strftime('%Y-%m')
        
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
📅 {datetime.now().strftime('%B %Y')}

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
- `/stats` - Analytics dashboard

*Tips:*
- Bot otomatis mendeteksi kategori
- Gunakan kata kunci seperti "makan", "bensin", "gaji"
- Batas budget dapat di-set di Google Sheets

Butuh bantuan? Hubungi developer! 🚀
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ==================== MAIN ====================

def main():
    print("🤖 Initializing bot...")
    
    # Test connection
    if not sheets.test_connection():
        print("❌ Failed to connect to Google Sheets. Check credentials!")
        return
    
    print("✅ Google Sheets connected")
    print(f"📱 Bot token: {TELEGRAM_TOKEN[:10]}...")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("pengeluaran", add_expense))
    app.add_handler(CommandHandler("pemasukan", add_income))
    app.add_handler(CommandHandler("nabung", add_saving))
    app.add_handler(CommandHandler("ringkasan", daily_summary))
    app.add_handler(CommandHandler("bulanan", monthly_report))
    app.add_handler(CommandHandler("stats", show_stats))
    
    print("🚀 Bot is running...")
    print("Press Ctrl+C to stop")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
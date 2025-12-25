from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os
import json
import base64

class SheetsManager:
    def __init__(self, spreadsheet_id):
        self.spreadsheet_id = spreadsheet_id
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
        
        # Load credentials dari environment variable (untuk Fly.io)
        if os.getenv('GOOGLE_CREDENTIALS_BASE64'):
            creds_json = base64.b64decode(os.getenv('GOOGLE_CREDENTIALS_BASE64'))
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_dict, scopes=self.scopes)
        else:
            # Load dari file (untuk development lokal)
            creds = Credentials.from_service_account_file('credentials.json', scopes=self.scopes)
        
        self.service = build('sheets', 'v4', credentials=creds)
        self.sheet = self.service.spreadsheets()
    
    @staticmethod
    def _safe_float(value):
        """Konversi aman ke float"""
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _parse_date(date_str):
        """Parse multiple date formats safely"""
        if not date_str:
            return datetime.now()
            
        formats = [
            '%Y-%m-%d %H:%M:%S',      # Standard SQL/Sheets
            '%Y-%m-%dT%H:%M:%S',      # ISO
            '%Y-%m-%d',               # ISO Date only
            '%d/%m/%Y %H:%M:%S',      # Sheet format (DD/MM/YYYY HH:MM:SS)
            '%d/%m/%Y'                # Short date
        ]
        
        for fmt in formats:
            try:
                # Handle potential microseconds for ISO by splitting
                clean_date = date_str.split('.')[0] if 'T' in date_str else date_str
                return datetime.strptime(clean_date, fmt)
            except ValueError:
                continue
                
        # If all fail, try naive approach or return now to allow flow to continue
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            return datetime.now()

    def test_connection(self):
        """Test koneksi ke spreadsheet"""
        try:
            result = self.sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range='Transactions!A1:I1'
            ).execute()
            print("✅ Koneksi ke Google Sheets berhasil!")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def add_transaction(self, transaction):
        """Tambah transaksi ke sheet"""
        values = [[
            transaction['id'],
            transaction['timestamp'],
            transaction['user_id'],
            transaction['type'],
            transaction['amount'],
            transaction['category'],
            transaction['description'],
            transaction.get('ai_confidence', 0),
            transaction.get('payment_method', '-')
        ]]
        
        body = {'values': values}
        
        result = self.sheet.values().append(
            spreadsheetId=self.spreadsheet_id,
            range='Transactions!A:I',
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        return result
    
    def get_all_categories(self):
        """Ambil semua data kategori dari sheet Categories"""
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range='Categories!A2:F'
        ).execute()
        
        rows = result.get('values', [])
        
        categories = []
        for row in rows:
            if len(row) >= 6:
                categories.append({
                    'id': row[0],
                    'name': row[1],
                    'type': row[2],
                    'icon': row[3],
                    'budget_limit': self._safe_float(row[4]),
                    'keywords': [k.strip().lower() for k in row[5].split(',')]
                })
        
        return categories
    
    def get_keywords_mapping(self):
        """Buat mapping keywords → category_name untuk AI"""
        categories = self.get_all_categories()
        
        keywords_map = {}
        for cat in categories:
            for keyword in cat['keywords']:
                if keyword not in keywords_map:
                    keywords_map[keyword] = []
                keywords_map[keyword].append(cat['name'])
        
        return keywords_map
    
    def simple_categorize(self, description):
        """Kategorisasi sederhana berdasarkan keyword matching"""
        description_lower = description.lower()
        keywords_map = self.get_keywords_mapping()
        
        # Cek setiap keyword
        for keyword, categories in keywords_map.items():
            if keyword in description_lower:
                return categories[0], 0.9  # Return kategori pertama + confidence
        
        return 'Lainnya', 0.5  # Default
    
    def get_category_budget_status(self, category_name, user_id):
        """Cek budget status kategori untuk user tertentu"""
        # 1. Ambil budget limit dari Categories
        categories = self.get_all_categories()
        budget_limit = 0
        
        for cat in categories:
            if cat['name'] == category_name:
                budget_limit = cat['budget_limit']
                break
        
        if budget_limit == 0:
            return None
        
        # 2. Hitung total spending bulan ini
        current_month = datetime.now().strftime('%Y-%m')
        
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range='Transactions!A2:I'
        ).execute()
        
        rows = result.get('values', [])
        total_spent = 0
        
        for row in rows:
            if len(row) >= 7:
                tx_month = self._parse_date(row[1]).strftime('%Y-%m')
                
                if (str(row[2]) == str(user_id) and 
                    row[3] == 'expense' and 
                    row[5] == category_name and 
                    tx_month == current_month):
                    
                    total_spent += self._safe_float(row[4])
        
        return {
            'category': category_name,
            'limit': budget_limit,
            'spent': total_spent,
            'remaining': budget_limit - total_spent,
            'percentage': (total_spent / budget_limit * 100) if budget_limit > 0 else 0
        }
    
    def get_transactions_by_date(self, user_id, date):
        """Ambil transaksi berdasarkan tanggal"""
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range='Transactions!A2:I'
        ).execute()
        
        rows = result.get('values', [])
        transactions = []
        
        for row in rows:
            if len(row) >= 7:
                tx_date = self._parse_date(row[1]).date()
                if str(row[2]) == str(user_id) and tx_date == date:
                    transactions.append({
                        'id': row[0],
                        'timestamp': row[1],
                        'user_id': row[2],
                        'type': row[3],
                        'amount': self._safe_float(row[4]),
                        'category': row[5],
                        'description': row[6]
                    })
        
        return transactions
    
    def get_transactions_by_month(self, user_id, year_month):
        """Ambil transaksi berdasarkan bulan (format: 2025-01)"""
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range='Transactions!A2:I'
        ).execute()
        
        rows = result.get('values', [])
        transactions = []
        
        for row in rows:
            if len(row) >= 7:
                tx_month = self._parse_date(row[1]).strftime('%Y-%m')
                if str(row[2]) == str(user_id) and tx_month == year_month:
                    transactions.append({
                        'id': row[0],
                        'timestamp': row[1],
                        'user_id': row[2],
                        'type': row[3],
                        'amount': self._safe_float(row[4]),
                        'category': row[5],
                        'description': row[6]
                    })
        
        return transactions
    
    def update_monthly_summary(self, user_id, year_month):
        """Update ringkasan bulanan"""
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range='Transactions!A2:I'
        ).execute()
        
        rows = result.get('values', [])
        
        total_income = 0
        total_expense = 0
        total_saving = 0
        transaction_count = 0
        category_expenses = {}
        
        for row in rows:
            if len(row) >= 7:
                tx_month = self._parse_date(row[1]).strftime('%Y-%m')
                
                if str(row[2]) == str(user_id) and tx_month == year_month:
                    tx_type = row[3]
                    amount = self._safe_float(row[4])
                    category = row[5]
                    
                    transaction_count += 1
                    
                    if tx_type == 'income':
                        total_income += amount
                    elif tx_type == 'expense':
                        total_expense += amount
                        category_expenses[category] = category_expenses.get(category, 0) + amount
                    elif tx_type == 'saving':
                        total_saving += amount
        
        top_category = max(category_expenses, key=category_expenses.get) if category_expenses else '-'
        
        # Cek apakah sudah ada di Monthly_Summary
        summary_result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range='Monthly_Summary!A2:H'
        ).execute()
        
        summary_rows = summary_result.get('values', [])
        row_index = None
        
        for i, row in enumerate(summary_rows):
            if len(row) >= 2 and row[0] == year_month and str(row[1]) == str(user_id):
                row_index = i + 2
                break
        
        net_balance = total_income - total_expense - total_saving
        summary_data = [
            year_month,
            user_id,
            total_income,
            total_expense,
            total_saving,
            net_balance,
            top_category,
            transaction_count
        ]
        
        if row_index:
            range_name = f'Monthly_Summary!A{row_index}:H{row_index}'
            body = {'values': [summary_data]}
            
            self.sheet.values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
        else:
            body = {'values': [summary_data]}
            
            self.sheet.values().append(
                spreadsheetId=self.spreadsheet_id,
                range='Monthly_Summary!A:H',
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
        
        return summary_data
    
    def update_analytics(self, user_id):
        """Update analytics metrics"""
        current_month = datetime.now().strftime('%Y-%m')
        
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range='Transactions!A2:I'
        ).execute()
        
        rows = result.get('values', [])
        
        current_month_txs = []
        all_user_txs = []
        
        for row in rows:
            if len(row) >= 7 and str(row[2]) == str(user_id):
                all_user_txs.append(row)
                
                tx_month = self._parse_date(row[1]).strftime('%Y-%m')
                if tx_month == current_month:
                    current_month_txs.append(row)
        
        if not current_month_txs:
            return
        
        days_passed = datetime.now().day
        
        total_expense = sum([self._safe_float(row[4]) for row in current_month_txs if row[3] == 'expense'])
        total_income = sum([self._safe_float(row[4]) for row in current_month_txs if row[3] == 'income'])
        total_saving = sum([self._safe_float(row[4]) for row in current_month_txs if row[3] == 'saving'])
        
        avg_daily_expense = total_expense / days_passed if days_passed > 0 else 0
        avg_daily_income = total_income / days_passed if days_passed > 0 else 0
        total_transactions = len(current_month_txs)
        savings_rate = (total_saving / total_income * 100) if total_income > 0 else 0
        
        category_expenses = {}
        for row in current_month_txs:
            if row[3] == 'expense':
                cat = row[5]
                category_expenses[cat] = category_expenses.get(cat, 0) + self._safe_float(row[4])
        
        top_category = max(category_expenses, key=category_expenses.get) if category_expenses else '-'
        
        last_tx_date = max([self._parse_date(row[1]) for row in current_month_txs])
        
        last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        last_month_expense = sum([
            self._safe_float(row[4]) 
            for row in all_user_txs 
            if row[3] == 'expense' and self._parse_date(row[1]).strftime('%Y-%m') == last_month
        ])
        
        if last_month_expense > 0:
            trend_pct = ((total_expense - last_month_expense) / last_month_expense * 100)
            spending_trend = f"{'+' if trend_pct > 0 else ''}{trend_pct:.1f}%"
        else:
            spending_trend = "N/A"
        
        categories = self.get_all_categories()
        budget_alert_count = 0
        
        for cat in categories:
            if cat['budget_limit'] > 0:
                spent = category_expenses.get(cat['name'], 0)
                if spent > cat['budget_limit']:
                    budget_alert_count += 1
        
        metrics = {
            'Avg_Daily_Expense': f"{avg_daily_expense:.0f}",
            'Avg_Daily_Income': f"{avg_daily_income:.0f}",
            'Total_Transactions': str(total_transactions),
            'Savings_Rate': f"{savings_rate:.1f}%",
            'Budget_Alert_Count': str(budget_alert_count),
            'Spending_Trend': spending_trend,
            'Top_Expense_Category': top_category,
            'Last_Transaction_Date': last_tx_date.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        analytics_result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range='Analytics!A2:D'
        ).execute()
        
        analytics_rows = analytics_result.get('values', [])
        timestamp = datetime.now().isoformat()
        
        for metric_name, value in metrics.items():
            row_index = None
            
            for i, row in enumerate(analytics_rows):
                if len(row) >= 2 and str(row[0]) == str(user_id) and row[1] == metric_name:
                    row_index = i + 2
                    break
            
            metric_data = [user_id, metric_name, value, timestamp]
            
            if row_index:
                range_name = f'Analytics!A{row_index}:D{row_index}'
                body = {'values': [metric_data]}
                
                self.sheet.values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
            else:
                body = {'values': [metric_data]}
                
                self.sheet.values().append(
                    spreadsheetId=self.spreadsheet_id,
                    range='Analytics!A:D',
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
        
        return metrics

    def get_training_data(self):
        """Ambil data deskripsi & kategori untuk training AI"""
        try:
            # Load Categories map first to resolve IDs (CAT-xxx) to Names
            categories = self.get_all_categories()
            id_to_name = {cat['id']: cat['name'] for cat in categories}

            result = self.sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range='Transactions!F2:G'  # F=Category, G=Description
            ).execute()
            
            rows = result.get('values', [])
            training_data = []
            
            for row in rows:
                if len(row) >= 2:
                    category = row[0].strip()
                    description = row[1].strip()
                    
                    if category and description:
                        # Translate ID to Name if exists
                        if category in id_to_name:
                            category = id_to_name[category]

                        training_data.append({
                            'description': description,
                            'category': category
                        })
            
            return training_data
        except Exception as e:
            print(f"❌ Error fetching training data: {e}")
            return []

# Test script
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    
    SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
    sheets = SheetsManager(SHEET_ID)
    sheets.test_connection()
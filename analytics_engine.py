import matplotlib
matplotlib.use('Agg')  # Valid for server usage

import matplotlib.pyplot as plt
import pandas as pd
import io
import seaborn as sns

class AnalyticsVisualizer:
    def __init__(self):
        # Set style
        sns.set_style("whitegrid")
        
    def generate_monthly_report(self, transactions, month_name):
        """
        Generate infographic for monthly report.
        transactions: list of dicts
        Returns: BytesIO object of the image
        """
        if not transactions:
            return None
            
        df = pd.DataFrame(transactions)
        
        # Pastikan kolom numeric
        df['amount'] = pd.to_numeric(df['amount'])
        
        # Filter Expense
        df_expense = df[df['type'] == 'expense']
        
        if df_expense.empty:
            return None
            
        # Create figure with 2 subplots (Pie & Bar)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
        fig.suptitle(f'Laporan Keuangan: {month_name}', fontsize=16, fontweight='bold')
        
        # 1. PIE CHART - Spending by Category
        category_sum = df_expense.groupby('category')['amount'].sum().sort_values(ascending=False)
        
        # Ambil top 5, sisanya 'Lainnya'
        if len(category_sum) > 5:
            top_5 = category_sum.head(5)
            others = pd.Series([category_sum[5:].sum()], index=['Lainnya'])
            category_sum = pd.concat([top_5, others])
            
        wedges, texts, autotexts = ax1.pie(
            category_sum, 
            labels=category_sum.index, 
            autopct='%1.1f%%',
            startangle=90,
            colors=sns.color_palette('pastel'),
            textprops={'fontsize': 10}
        )
        ax1.set_title('Persentase Pengeluaran per Kategori')
        
        # 2. BAR CHART - Daily Spending
        # Convert timestamp to date
        # Asumsi kolom timestamp ada
        # Kita parse aman dulu
        try:
            df_expense['date'] = pd.to_datetime(df_expense['timestamp']).dt.date
            daily_sum = df_expense.groupby('date')['amount'].sum()
            
            # Plot
            sns.barplot(x=daily_sum.index, y=daily_sum.values, ax=ax2, hue=daily_sum.index, palette='viridis', legend=False)
            ax2.set_title('Tren Pengeluaran Harian')
            ax2.set_xlabel('Tanggal')
            ax2.set_ylabel('Total (Rp)')
            ax2.tick_params(axis='x', rotation=45)
            
            # Format Y axis to normal numbers
            ax2.get_yaxis().set_major_formatter(
                matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ','))
            )
        except Exception as e:
            print(f"Error plotting daily trend: {e}")
            ax2.text(0.5, 0.5, "Data Tanggal Tidak Valid", ha='center')

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close(fig)
        
        return buf

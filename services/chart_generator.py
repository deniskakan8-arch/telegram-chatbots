import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def generate_pie_chart(category_data: list, title: str = "Структура расходов") -> io.BytesIO:
    """
    category_data: list of tuples (category_name, total_amount, count)
    """
    labels = []
    values = []
    
    for cat, amt, _ in category_data:
        # Убираем эмодзи для стабильной отрисовки шрифтов на сервере
        clean_cat = cat.split(" ", 1)[-1] if " " in cat else cat
        labels.append(clean_cat)
        values.append(amt)
        
    plt.figure(figsize=(8, 6))
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    
    # Цветовая палитра
    colors = plt.cm.tab20.colors[:len(values)]
    
    wedges, texts, autotexts = plt.pie(
        values,
        labels=labels,
        autopct='%1.1f%%',
        startangle=140,
        colors=colors,
        textprops=dict(color="black", fontsize=10)
    )
    
    plt.title(title, fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', dpi=150)
    img_buf.seek(0)
    plt.close()
    return img_buf

def generate_bar_chart(dynamics: dict) -> io.BytesIO:
    """
    dynamics: dict of { "2026-06": {"total": 350000}, "2026-07": {"total": 420000} }
    """
    months = list(dynamics.keys())[-6:] # Последние 6 месяцев
    totals = [dynamics[m]["total"] for m in months]
    
    plt.figure(figsize=(9, 5))
    bars = plt.bar(months, totals, color='#4A90E2', width=0.5)
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 5000, f"{int(yval):,} ₸", ha='center', va='bottom', fontsize=9)
        
    plt.title("Динамика расходов по месяцам", fontsize=14, fontweight='bold', pad=15)
    plt.ylabel("Траты (KZT)", fontsize=11)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', dpi=150)
    img_buf.seek(0)
    plt.close()
    return img_buf

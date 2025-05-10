# web_dashboard.py
from flask import Flask, render_template, jsonify
import pandas as pd
import json
from datetime import datetime
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    """API endpoint dla statystyk"""
    try:
        # Wczytaj dane z CSV
        if os.path.exists('trading_history.csv'):
            df = pd.read_csv('trading_history.csv')
            
            if not df.empty:
                closed_trades = df[df['action'] == 'close']
                
                stats = {
                    'total_trades': len(closed_trades),
                    'total_pnl': closed_trades['pnl'].sum() if not closed_trades.empty else 0,
                    'win_rate': calculate_win_rate(closed_trades),
                    'current_balance': df['balance_after'].iloc[-1] if 'balance_after' in df.columns else 1000,
                    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                return jsonify(stats)
        
        return jsonify({
            'total_trades': 0,
            'total_pnl': 0,
            'win_rate': 0,
            'current_balance': 1000,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/trades')
def get_trades():
    """API endpoint dla historii transakcji"""
    try:
        if os.path.exists('trading_history.csv'):
            df = pd.read_csv('trading_history.csv')
            return jsonify(df.to_dict(orient='records'))
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/chart_data')
def get_chart_data():
    """API endpoint dla danych do wykresów"""
    try:
        if os.path.exists('trading_history.csv'):
            df = pd.read_csv('trading_history.csv')
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # PnL data
                closed_trades = df[df['action'] == 'close']
                if not closed_trades.empty:
                    closed_trades['cumulative_pnl'] = closed_trades['pnl'].cumsum()
                    
                    pnl_data = {
                        'timestamps': closed_trades['timestamp'].astype(str).tolist(),
                        'values': closed_trades['cumulative_pnl'].tolist()
                    }
                else:
                    pnl_data = {'timestamps': [], 'values': []}
                
                # Balance data
                balance_data = {
                    'timestamps': df['timestamp'].astype(str).tolist(),
                    'values': df['balance_after'].tolist() if 'balance_after' in df.columns else []
                }
                
                return jsonify({
                    'pnl': pnl_data,
                    'balance': balance_data
                })
        
        return jsonify({
            'pnl': {'timestamps': [], 'values': []},
            'balance': {'timestamps': [], 'values': []}
        })
    except Exception as e:
        return jsonify({'error': str(e)})

def calculate_win_rate(closed_trades):
    if closed_trades.empty:
        return 0
    winning_trades = closed_trades[closed_trades['pnl'] > 0]
    return (len(winning_trades) / len(closed_trades)) * 100

if __name__ == '__main__':
    # Stwórz folder templates jeśli nie istnieje
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Stwórz podstawowy template
    with open('templates/index.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Trading Bot Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial; margin: 20px; background: #1a1a1a; color: white; }
        .stats { display: flex; gap: 20px; margin-bottom: 30px; }
        .stat-card { background: #2a2a2a; padding: 20px; border-radius: 10px; flex: 1; }
        .chart-container { width: 100%; height: 400px; margin-bottom: 30px; }
        .positive { color: #00ff00; }
        .negative { color: #ff0000; }
    </style>
</head>
<body>
    <h1>Trading Bot Dashboard</h1>
    
    <div class="stats">
        <div class="stat-card">
            <h3>Total Trades</h3>
            <h2 id="total-trades">0</h2>
        </div>
        <div class="stat-card">
            <h3>Total PnL</h3>
            <h2 id="total-pnl">$0.00</h2>
        </div>
        <div class="stat-card">
            <h3>Win Rate</h3>
            <h2 id="win-rate">0%</h2>
        </div>
        <div class="stat-card">
            <h3>Current Balance</h3>
            <h2 id="current-balance">$1000.00</h2>
        </div>
    </div>
    
    <div class="chart-container">
        <canvas id="pnl-chart"></canvas>
    </div>
    
    <div class="chart-container">
        <canvas id="balance-chart"></canvas>
    </div>
    
    <script>
        // Inicjalizacja wykresów
        const pnlChart = new Chart(document.getElementById('pnl-chart'), {
            type: 'line',
            data: { labels: [], datasets: [{ 
                label: 'Cumulative PnL',
                data: [],
                borderColor: '#00ff00',
                fill: false
            }]},
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: 'white' } },
                    y: { ticks: { color: 'white' } }
                }
            }
        });
        
        const balanceChart = new Chart(document.getElementById('balance-chart'), {
            type: 'line',
            data: { labels: [], datasets: [{ 
                label: 'Account Balance',
                data: [],
                borderColor: '#00ffff',
                fill: false
            }]},
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: 'white' } },
                    y: { ticks: { color: 'white' } }
                }
            }
        });
        
        // Aktualizacja danych
        async function updateDashboard() {
            try {
                // Statystyki
                const statsResponse = await fetch('/api/stats');
                const stats = await statsResponse.json();
                
                document.getElementById('total-trades').textContent = stats.total_trades;
                document.getElementById('total-pnl').textContent = `$${stats.total_pnl.toFixed(2)}`;
                document.getElementById('total-pnl').className = stats.total_pnl >= 0 ? 'positive' : 'negative';
                document.getElementById('win-rate').textContent = `${stats.win_rate.toFixed(1)}%`;
                document.getElementById('current-balance').textContent = `$${stats.current_balance.toFixed(2)}`;
                
                // Wykresy
                const chartResponse = await fetch('/api/chart_data');
                const chartData = await chartResponse.json();
                
                // Aktualizuj PnL chart
                pnlChart.data.labels = chartData.pnl.timestamps;
                pnlChart.data.datasets[0].data = chartData.pnl.values;
                pnlChart.update();
                
                // Aktualizuj Balance chart
                balanceChart.data.labels = chartData.balance.timestamps;
                balanceChart.data.datasets[0].data = chartData.balance.values;
                balanceChart.update();
                
            } catch (error) {
                console.error('Error updating dashboard:', error);
            }
        }
        
        // Aktualizuj co 5 sekund
        updateDashboard();
        setInterval(updateDashboard, 5000);
    </script>
</body>
</html>
        ''')
    
    print("Starting web dashboard on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
"""Module 4: Dashboard Plotly tổng hợp."""

import sqlite3

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import DB_PATH


def load_data(db_path: str = None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    df_inventory = pd.read_sql('SELECT * FROM inventory', conn, parse_dates=['date'])
    df_production = pd.read_sql('SELECT * FROM production', conn, parse_dates=['date'])
    df_materials = pd.read_sql('SELECT * FROM materials', conn)
    conn.close()
    return df_inventory, df_production, df_materials


def create_dashboard(
    df_inventory: pd.DataFrame,
    df_production: pd.DataFrame,
    forecast_fn=None,
) -> go.Figure:
    """
    Vẽ dashboard 4 biểu đồ.

    Parameters
    ----------
    forecast_fn : callable, optional
        Hàm nhận (material_id, n_days) và trả về DataFrame dự báo.
        Truyền None để bỏ qua biểu đồ dự báo.
    """
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            '📦 Tồn kho hiện tại vs Reorder Point',
            '📉 Lịch sử tiêu thụ VL001 (90 ngày)',
            '🏭 Hiệu suất chuyền sản xuất',
            '🎯 Dự báo tồn kho 30 ngày — VL001',
        ],
        specs=[[{'type': 'bar'}, {'type': 'scatter'}],
               [{'type': 'bar'}, {'type': 'scatter'}]],
    )

    # Chart 1: Tồn kho hiện tại vs Reorder Point
    latest = (
        df_inventory.sort_values('date')
        .groupby(['material_id', 'material_name'])
        .last()
        .reset_index()
    )
    bar_colors = [
        '#e74c3c' if s < r else '#2ecc71'
        for s, r in zip(latest['stock_level'], latest['reorder_point'])
    ]
    fig.add_trace(go.Bar(
        x=latest['material_name'], y=latest['stock_level'],
        name='Tồn kho', marker_color=bar_colors, showlegend=False,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=latest['material_name'], y=latest['reorder_point'],
        mode='markers', marker=dict(color='red', size=8, symbol='line-ew-open'),
        name='Reorder Point', showlegend=False,
    ), row=1, col=1)

    # Chart 2: Lịch sử tiêu thụ VL001 (MA7)
    vl001 = df_inventory[df_inventory['material_id'] == 'VL001'].tail(90)
    fig.add_trace(go.Scatter(
        x=vl001['date'], y=vl001['daily_consumption'].rolling(7).mean(),
        mode='lines', line=dict(color='#3498db', width=2),
        name='MA7 tiêu thụ', showlegend=False,
    ), row=1, col=2)

    # Chart 3: Hiệu suất chuyền
    eff_by_line = df_production.groupby('line')['efficiency'].mean().reset_index()
    line_colors = [
        '#e74c3c' if e < 85 else ('#f39c12' if e < 92 else '#2ecc71')
        for e in eff_by_line['efficiency']
    ]
    fig.add_trace(go.Bar(
        x=eff_by_line['line'], y=eff_by_line['efficiency'],
        marker_color=line_colors, showlegend=False,
        text=[f'{v:.1f}%' for v in eff_by_line['efficiency']],
        textposition='auto',
    ), row=2, col=1)

    # Chart 4: Dự báo tồn kho VL001
    if forecast_fn is not None:
        fc30 = forecast_fn('VL001', 30)
        fc_colors = ['#e74c3c' if s < 500 else '#2ecc71' for s in fc30['projected_stock']]
        fig.add_trace(go.Bar(
            x=fc30['date'], y=fc30['projected_stock'],
            marker_color=fc_colors, name='Tồn kho dự báo', showlegend=False,
        ), row=2, col=2)
        fig.add_hline(y=500, line_dash='dash', line_color='red', row=2, col=2)
    else:
        fig.add_annotation(
            text='Chạy Module 2 trước để có dự báo',
            row=2, col=2, showarrow=False,
        )

    fig.update_layout(
        title=dict(text='🏭 LUCKY STAR — ERP AI DASHBOARD', font=dict(size=20)),
        height=750,
        paper_bgcolor='#f8f9fa',
        plot_bgcolor='white',
    )
    fig.update_xaxes(tickangle=45)
    fig.show()
    print('✅ Dashboard đã render!')
    return fig


def run(forecast_fn=None):
    print('\n📈 MODULE 4: Dashboard Tổng Hợp')
    df_inventory, df_production, df_materials = load_data()
    print(f'✅ Đã load dữ liệu từ {DB_PATH}')
    create_dashboard(df_inventory, df_production, forecast_fn)


if __name__ == '__main__':
    run()

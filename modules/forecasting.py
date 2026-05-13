"""Module 2: Dự báo tồn kho bằng Machine Learning."""

import os
import sqlite3

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from config import DB_PATH, FEATURE_COLS, MATERIALS


def load_data(db_path: str = None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    df_inventory = pd.read_sql('SELECT * FROM inventory', conn, parse_dates=['date'])
    df_production = pd.read_sql('SELECT * FROM production', conn, parse_dates=['date'])
    df_materials = pd.read_sql('SELECT * FROM materials', conn)
    conn.close()
    return df_inventory, df_production, df_materials


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().sort_values(['material_id', 'date'])
    df['day_of_week'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    df['day_of_year'] = df['date'].dt.dayofyear
    df['is_high_season'] = df['month'].isin([3, 4, 5, 9, 10, 11]).astype(int)

    for lag in [1, 3, 7, 14]:
        df[f'consumption_lag{lag}'] = (
            df.groupby('material_id')['daily_consumption'].shift(lag)
        )

    for window in [7, 14, 30]:
        df[f'consumption_ma{window}'] = df.groupby('material_id')['daily_consumption'].transform(
            lambda x: x.rolling(window).mean()
        )
        df[f'consumption_std{window}'] = df.groupby('material_id')['daily_consumption'].transform(
            lambda x: x.rolling(window).std()
        )

    df['stock_ma7'] = df.groupby('material_id')['stock_level'].transform(
        lambda x: x.rolling(7).mean()
    )
    df['days_until_reorder'] = df['stock_level'] - df['reorder_point']
    df['material_code'] = df['material_id'].str.replace('VL', '').astype(int)
    return df.dropna()


def train_models(df_feat: pd.DataFrame):
    X = df_feat[FEATURE_COLS]
    y = df_feat['daily_consumption']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    models = {
        'Linear Regression': LinearRegression(),
        'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
        'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, random_state=42),
    }

    results = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        results[name] = {
            'MAE': round(mean_absolute_error(y_test, preds), 3),
            'RMSE': round(np.sqrt(mean_squared_error(y_test, preds)), 3),
            'R²': round(r2_score(y_test, preds), 4),
            'model': model,
        }
        print(
            f'{name:25s} | MAE={results[name]["MAE"]:6.3f} '
            f'| RMSE={results[name]["RMSE"]:6.3f} | R²={results[name]["R²"]:.4f}'
        )

    best_name = max(results, key=lambda k: results[k]['R²'])
    best_model = results[best_name]['model']
    print(f'\n🏆 Best model: {best_name} (R²={results[best_name]["R²"]})')
    return best_model, results


def forecast_next_n_days(
    material_id: str,
    df_feat: pd.DataFrame,
    best_model,
    n_days: int = 30,
) -> pd.DataFrame:
    mat_df = df_feat[df_feat['material_id'] == material_id].sort_values('date')
    if mat_df.empty:
        return None

    last_row = mat_df.iloc[-1]
    last_date = last_row['date']
    last_stock = last_row['stock_level']
    reorder_pt = last_row['reorder_point']

    forecasts = []
    for i in range(1, n_days + 1):
        future_date = last_date + timedelta(days=i)
        month = future_date.month
        row = pd.DataFrame([{
            'stock_level': last_stock,
            'reorder_point': reorder_pt,
            'days_until_reorder': last_stock - reorder_pt,
            'day_of_week': future_date.dayofweek,
            'month': month,
            'day_of_year': future_date.timetuple().tm_yday,
            'is_high_season': int(month in [3, 4, 5, 9, 10, 11]),
            'consumption_lag1': last_row['daily_consumption'],
            'consumption_lag3': last_row.get('consumption_lag3', last_row['daily_consumption']),
            'consumption_lag7': last_row.get('consumption_lag7', last_row['daily_consumption']),
            'consumption_lag14': last_row.get('consumption_lag14', last_row['daily_consumption']),
            'consumption_ma7': last_row['consumption_ma7'],
            'consumption_ma14': last_row['consumption_ma14'],
            'consumption_ma30': last_row['consumption_ma30'],
            'consumption_std7': last_row['consumption_std7'],
            'consumption_std14': last_row['consumption_std14'],
            'stock_ma7': last_row['stock_ma7'],
            'material_code': last_row['material_code'],
        }])
        pred_consumption = max(0, best_model.predict(row)[0])
        last_stock = max(0, last_stock - pred_consumption)
        if last_stock < reorder_pt:
            alert = '🔴 DƯỚI MỨC CẢNH BÁO'
        elif last_stock < reorder_pt * 1.3:
            alert = '🟡 Sắp tới ngưỡng'
        else:
            alert = '🟢 Bình thường'
        forecasts.append({
            'date': future_date.strftime('%Y-%m-%d'),
            'predicted_consumption': round(pred_consumption, 1),
            'projected_stock': round(last_stock, 1),
            'reorder_point': reorder_pt,
            'status': alert,
        })
    return pd.DataFrame(forecasts)


def plot_forecast(fc: pd.DataFrame, material_name: str = 'VL001', save_dir: str = 'data') -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f'Dự báo tồn kho — {material_name}', fontsize=14, fontweight='bold')

    colors = [
        '#e74c3c' if s.startswith('🔴') else ('#f39c12' if s.startswith('🟡') else '#2ecc71')
        for s in fc['status']
    ]
    axes[0].bar(range(len(fc)), fc['projected_stock'], color=colors, alpha=0.8)
    axes[0].axhline(
        y=fc['reorder_point'].iloc[0], color='red', linestyle='--', linewidth=2,
        label=f'Reorder Point ({fc["reorder_point"].iloc[0]})',
    )
    axes[0].set_title('Tồn kho dự báo 30 ngày tới')
    axes[0].set_xlabel('Ngày')
    axes[0].set_ylabel('Số lượng')
    axes[0].legend()
    axes[0].set_xticks(range(0, len(fc), 5))
    axes[0].set_xticklabels([fc['date'].iloc[i][:10] for i in range(0, len(fc), 5)], rotation=30)

    axes[1].plot(range(len(fc)), fc['predicted_consumption'], color='#3498db', linewidth=2, marker='o', markersize=4)
    axes[1].fill_between(range(len(fc)), fc['predicted_consumption'], alpha=0.2, color='#3498db')
    axes[1].set_title('Tiêu thụ dự báo theo ngày')
    axes[1].set_xlabel('Ngày')
    axes[1].set_ylabel('Tiêu thụ/ngày')
    axes[1].set_xticks(range(0, len(fc), 5))
    axes[1].set_xticklabels([fc['date'].iloc[i][:10] for i in range(0, len(fc), 5)], rotation=30)

    plt.tight_layout()
    os.makedirs(save_dir, exist_ok=True)
    out_path = os.path.join(save_dir, f'forecast_{material_name}.png')
    plt.savefig(out_path, dpi=120, bbox_inches='tight')
    plt.show()
    print(f'✅ Đã lưu biểu đồ: {out_path}')


def run():
    print('\n📊 MODULE 2: Dự báo tồn kho bằng Machine Learning')

    df_inventory, df_production, df_materials = load_data()
    print(f'✅ Load dữ liệu từ SQLite3 ({DB_PATH}): {len(df_inventory):,} records')

    df_feat = build_features(df_inventory)
    best_model, _ = train_models(df_feat)

    # Demo forecast VL001
    fc = forecast_next_n_days('VL001', df_feat, best_model, 30)
    plot_forecast(fc, material_name='VL001')

    warning_days = fc[fc['status'].str.startswith('🔴')]
    if not warning_days.empty:
        print(f'⚠️  Tồn kho VL001 xuống dưới ngưỡng từ ngày: {warning_days["date"].iloc[0]}')
    else:
        print('✅ Tồn kho VL001 ổn định trong 30 ngày tới.')

    # Tổng hợp tất cả nguyên liệu
    summary_rows = []
    for mat in MATERIALS:
        mid = mat['material_id']
        fc_all = forecast_next_n_days(mid, df_feat, best_model, 30)
        if fc_all is None:
            continue
        current_stock = df_feat[df_feat['material_id'] == mid]['stock_level'].iloc[-1]
        days_to_reorder = None
        for _, row in fc_all.iterrows():
            if row['projected_stock'] < mat['reorder_point']:
                days_to_reorder = (pd.to_datetime(row['date']) - df_feat['date'].max()).days
                break
        avg_daily = fc_all['predicted_consumption'].mean()
        summary_rows.append({
            'ID': mid,
            'Nguyên liệu': mat['name'],
            'Tồn kho hiện tại': round(current_stock, 0),
            'Reorder Point': mat['reorder_point'],
            'TB tiêu thụ/ngày': round(avg_daily, 1),
            'Ngày đến ngưỡng': days_to_reorder if days_to_reorder else '>30 ngày',
            'Trạng thái': (
                '🔴 Cần nhập gấp' if (days_to_reorder and days_to_reorder <= 7)
                else ('🟡 Theo dõi' if (days_to_reorder and days_to_reorder <= 14) else '🟢 Ổn định')
            ),
        })

    df_summary = pd.DataFrame(summary_rows)
    print('\n📊 BẢNG TỔNG HỢP DỰ BÁO TỒN KHO — 30 NGÀY TỚI')
    print('=' * 80)
    print(df_summary.to_string(index=False))

    os.makedirs('data', exist_ok=True)
    df_summary.to_csv('data/forecast_summary.csv', index=False, encoding='utf-8-sig')
    print('\n✅ Đã lưu data/forecast_summary.csv')

    return best_model, df_feat


if __name__ == '__main__':
    run()

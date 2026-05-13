"""Module 1: Sinh dữ liệu giả lập ERP và lưu vào SQLite3."""

import os
import sqlite3

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from config import DB_PATH, MATERIALS, PRODUCTS


def generate_materials() -> pd.DataFrame:
    return pd.DataFrame(MATERIALS)


def generate_inventory(start_date: datetime = None, days: int = 180) -> pd.DataFrame:
    if start_date is None:
        start_date = datetime(2024, 1, 1)

    records = []
    for mat in MATERIALS:
        stock = np.random.randint(600, 1200)
        for day in range(days):
            date = start_date + timedelta(days=day)
            month = date.month
            season_factor = 1.4 if month in [3, 4, 5, 9, 10, 11] else 0.8
            consumption = max(0, np.random.normal(40 * season_factor, 12))
            stock -= consumption
            if stock < mat['reorder_point']:
                stock += np.random.randint(400, 800)
                restocked = True
            else:
                restocked = False
            records.append({
                'date': date.strftime('%Y-%m-%d'),
                'material_id': mat['material_id'],
                'material_name': mat['name'],
                'stock_level': round(max(0, stock), 1),
                'daily_consumption': round(consumption, 1),
                'restocked': restocked,
                'reorder_point': mat['reorder_point'],
            })

    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'])
    return df


def generate_production(start_date: datetime = None, days: int = 180, n_orders: int = 200) -> pd.DataFrame:
    if start_date is None:
        start_date = datetime(2024, 1, 1)

    records = []
    for i in range(n_orders):
        date = start_date + timedelta(days=int(np.random.randint(0, days)))
        product = np.random.choice(PRODUCTS)
        planned = np.random.randint(200, 1000)
        actual = int(planned * np.random.uniform(0.75, 1.05))
        records.append({
            'order_id': f'PO{1000 + i}',
            'date': date.strftime('%Y-%m-%d'),
            'product': product,
            'line': f'Chuyền {np.random.randint(1, 6)}',
            'planned_qty': planned,
            'actual_qty': actual,
            'efficiency': round(actual / planned * 100, 1),
            'defect_rate': round(np.random.uniform(0.5, 4.5), 2),
        })

    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'])
    return df


def save_to_db(
    df_materials: pd.DataFrame,
    df_inventory: pd.DataFrame,
    df_production: pd.DataFrame,
    db_path: str = None,
) -> None:
    if db_path is None:
        db_path = DB_PATH
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    df_materials.to_sql('materials', conn, if_exists='replace', index=False)
    df_inventory.to_sql('inventory', conn, if_exists='replace', index=False)
    df_production.to_sql('production', conn, if_exists='replace', index=False)
    conn.commit()
    conn.close()


def verify_db(db_path: str = None) -> None:
    """In schema và demo SQL queries sau khi tạo DB."""
    if db_path is None:
        db_path = DB_PATH

    conn = sqlite3.connect(db_path)

    print('=' * 65)
    print(f'📋 DATABASE SCHEMA — {db_path}')
    print('=' * 65)
    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", conn)
    for table in tables['name']:
        cols = pd.read_sql(f'PRAGMA table_info({table})', conn)
        count = pd.read_sql(f'SELECT COUNT(*) AS cnt FROM {table}', conn).iloc[0, 0]
        print(f'\n  🗂️  Table: {table}  ({count:,} records)')
        print(f'     Columns: {", ".join(cols["name"].tolist())}')

    print('\n' + '=' * 65)
    print('🔍 QUERY: Tồn kho gần nhất vs Reorder Point')
    print('=' * 65)
    q = """
        SELECT  i.material_id,
                i.material_name,
                ROUND(i.stock_level, 0)                       AS stock_level,
                i.reorder_point,
                ROUND(i.stock_level - i.reorder_point, 0)     AS margin,
                CASE
                    WHEN i.stock_level < i.reorder_point       THEN '🔴 Cần nhập gấp'
                    WHEN i.stock_level < i.reorder_point * 1.3 THEN '🟡 Sắp tới ngưỡng'
                    ELSE '🟢 Bình thường'
                END AS status
        FROM inventory i
        WHERE i.date = (SELECT MAX(date) FROM inventory WHERE material_id = i.material_id)
        ORDER BY margin ASC
    """
    print(pd.read_sql(q, conn).to_string(index=False))
    conn.close()


def run():
    np.random.seed(42)
    print('📦 MODULE 1: Sinh dữ liệu giả lập ERP')

    df_materials = generate_materials()
    df_inventory = generate_inventory()
    df_production = generate_production()

    save_to_db(df_materials, df_inventory, df_production)

    print(f'✅ Đã tạo và lưu dữ liệu ERP vào SQLite3: {DB_PATH}')
    print(f'   - Bảng materials : {len(df_materials):,} records')
    print(f'   - Bảng inventory : {len(df_inventory):,} records')
    print(f'   - Bảng production: {len(df_production):,} records')

    verify_db()
    return df_materials, df_inventory, df_production


if __name__ == '__main__':
    run()

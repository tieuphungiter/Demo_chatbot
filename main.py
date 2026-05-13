"""
Lucky Star AI System — Entry Point
===================================
Chạy toàn bộ pipeline:
  Module 1 → Sinh & lưu dữ liệu ERP vào SQLite3
  Module 2 → Dự báo tồn kho (ML)
  Module 3 → RAG Chatbot nội bộ
  Module 4 → Dashboard Plotly

Cách dùng:
  python main.py
  ANTHROPIC_API_KEY=sk-... python main.py   # kích hoạt LLM thật
"""

import os
import sys
from functools import partial

# Cho phép import các module con dù chạy từ bất kỳ thư mục nào
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import data_generator, forecasting, rag_chatbot, dashboard
from modules.forecasting import forecast_next_n_days


def main() -> None:
    print('=' * 65)
    print('🏭 LUCKY STAR AI SYSTEM — ERP Mini Project')
    print('=' * 65)

    # ── Module 1: Sinh dữ liệu ERP & lưu SQLite3 ─────────────────────────
    data_generator.run()

    # ── Module 2: Dự báo tồn kho ML ──────────────────────────────────────
    best_model, df_feat = forecasting.run()

    # Đóng gói hàm forecast để truyền sang dashboard
    def _forecast_fn(material_id: str, n_days: int = 30):
        return forecast_next_n_days(material_id, df_feat, best_model, n_days)

    # ── Module 3: RAG Chatbot ─────────────────────────────────────────────
    api_key = os.environ.get('ANTHROPIC_API_KEY', '').strip() or None
    rag_chatbot.run(api_key=api_key)

    # ── Module 4: Dashboard ───────────────────────────────────────────────
    dashboard.run(forecast_fn=_forecast_fn)

    print('\n' + '=' * 65)
    print('✅ Lucky Star AI System hoàn tất!')
    print('=' * 65)


if __name__ == '__main__':
    main()

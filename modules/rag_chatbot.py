"""Module 3: RAG Chatbot nội bộ với FAISS + SentenceTransformers + LLM."""

import sqlite3

import pandas as pd

from config import DB_PATH, KNOWLEDGE_BASE


# ─── Vector Store ─────────────────────────────────────────────────────────────

def build_vector_store(knowledge_base: list = None):
    """Tạo FAISS vector store từ Knowledge Base."""
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np

    if knowledge_base is None:
        knowledge_base = KNOWLEDGE_BASE

    print('⏳ Đang load embedding model (multilingual)...')
    embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    docs_text = [f"{doc['title']}\n{doc['content']}" for doc in knowledge_base]
    print('⏳ Đang tạo vector embeddings...')
    embeddings = embedder.encode(docs_text, show_progress_bar=True)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    print(f'✅ Vector store: {index.ntotal} documents, dim={dim}')
    return embedder, index


def retrieve_relevant_docs(
    query: str,
    embedder,
    index,
    knowledge_base: list = None,
    top_k: int = 2,
) -> list:
    """Tìm tài liệu liên quan nhất cho câu hỏi bằng cosine similarity."""
    import faiss
    import numpy as np

    if knowledge_base is None:
        knowledge_base = KNOWLEDGE_BASE

    query_vec = embedder.encode([query])
    faiss.normalize_L2(query_vec)
    scores, indices = index.search(query_vec, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx >= 0:
            results.append({'doc': knowledge_base[idx], 'score': float(score)})
    return results


# ─── ERP Context ──────────────────────────────────────────────────────────────

def get_erp_context(db_path: str = None) -> str:
    """Truy vấn SQLite3 lấy snapshot ERP hiện tại để bổ sung vào context chatbot."""
    if db_path is None:
        db_path = DB_PATH

    conn = sqlite3.connect(db_path)

    latest_inventory = pd.read_sql("""
        SELECT i.material_name, i.material_id, i.stock_level, i.reorder_point, m.unit
        FROM inventory i
        JOIN materials m ON i.material_id = m.material_id
        WHERE i.date = (SELECT MAX(date) FROM inventory WHERE material_id = i.material_id)
        ORDER BY i.material_id
    """, conn)

    recent_prod = pd.read_sql("""
        SELECT AVG(efficiency)   AS avg_efficiency,
               AVG(defect_rate) AS avg_defect_rate
        FROM (
            SELECT efficiency, defect_rate
            FROM production
            ORDER BY date DESC
            LIMIT 10
        )
    """, conn)

    conn.close()

    snapshot = 'DỮ LIỆU ERP HIỆN TẠI (từ SQLite3):\n'
    for _, row in latest_inventory.iterrows():
        status = '⚠️ DƯỚI NGƯỠNG' if row['stock_level'] < row['reorder_point'] else 'OK'
        snapshot += (
            f"- {row['material_name']} ({row['material_id']}): "
            f"tồn {row['stock_level']:.0f} {row['unit']} [{status}]\n"
        )

    avg_eff = recent_prod['avg_efficiency'].iloc[0]
    avg_defect = recent_prod['avg_defect_rate'].iloc[0]
    snapshot += f'\nSẢN XUẤT GẦN ĐÂY (10 lệnh cuối):\n'
    snapshot += f'- Hiệu suất trung bình: {avg_eff:.1f}%\n'
    snapshot += f'- Tỷ lệ lỗi trung bình: {avg_defect:.2f}%\n'
    return snapshot


# ─── RAG Chat ─────────────────────────────────────────────────────────────────

def rag_chat(
    user_question: str,
    embedder,
    index,
    client=None,
    chat_history: list = None,
    knowledge_base: list = None,
) -> dict:
    """Retrieve → Augment → Generate."""
    if chat_history is None:
        chat_history = []
    if knowledge_base is None:
        knowledge_base = KNOWLEDGE_BASE

    # STEP 1: RETRIEVE
    relevant_docs = retrieve_relevant_docs(user_question, embedder, index, knowledge_base, top_k=2)
    retrieved_context = '\n\n'.join([
        f"[{r['doc']['doc_id']}] {r['doc']['title']}:\n{r['doc']['content']}"
        for r in relevant_docs
    ])

    # STEP 2: AUGMENT
    system_prompt = (
        'Bạn là AI Assistant nội bộ của nhà máy may mặc Lucky Star Việt Nam.\n'
        'Nhiệm vụ: Trả lời câu hỏi của nhân viên dựa trên tài liệu nội bộ và dữ liệu ERP.\n'
        'Nguyên tắc: Chỉ trả lời dựa trên thông tin được cung cấp. Nếu không có thông tin, nói rõ.\n'
        'Trả lời bằng tiếng Việt, súc tích, chuyên nghiệp.\n\n'
        f'=== TÀI LIỆU NỘI BỘ LIÊN QUAN ===\n{retrieved_context}\n\n'
        f'=== {get_erp_context()} ==='
    )

    # MOCK MODE — không cần API key
    if client is None:
        return {
            'answer': (
                '[MOCK MODE — Cần API key để có câu trả lời thực]\n\n'
                'Tài liệu tìm thấy:\n'
                + '\n'.join([f"• [{r['doc']['doc_id']}] {r['doc']['title']}" for r in relevant_docs])
                + f"\n\nNội dung liên quan:\n{relevant_docs[0]['doc']['content'][:400]}..."
            ),
            'sources': [r['doc']['doc_id'] for r in relevant_docs],
            'retrieved_docs': relevant_docs,
        }

    # STEP 3: GENERATE
    messages = chat_history + [{'role': 'user', 'content': user_question}]
    response = client.messages.create(
        model='claude-opus-4-5',
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )
    return {
        'answer': response.content[0].text,
        'sources': [r['doc']['doc_id'] for r in relevant_docs],
        'retrieved_docs': relevant_docs,
    }


# ─── Interactive Chat ──────────────────────────────────────────────────────────

def interactive_chat(embedder, index, client=None):
    """Chat tương tác qua terminal."""
    chat_history = []
    user_id = input('Đăng nhập (tên): ').strip() or 'Nhân viên'
    print(f'\n👋 Xin chào {user_id}! Gõ "quit" để thoát.\n')
    while True:
        user_input = input(f'👤 {user_id}: ').strip()
        if user_input.lower() in ['quit', 'exit', 'thoát']:
            print('👋 Tạm biệt!')
            break
        if not user_input:
            continue
        result = rag_chat(user_input, embedder, index, client, chat_history)
        print(f'🤖 AI: {result["answer"]}')
        print(f'📎 [{", ".join(result["sources"])}]\n')
        if client is not None:
            chat_history.extend([
                {'role': 'user', 'content': user_input},
                {'role': 'assistant', 'content': result['answer']},
            ])


# ─── Module Entry Point ───────────────────────────────────────────────────────

def run(api_key: str = None):
    import os
    print('\n🤖 MODULE 3: RAG Chatbot nội bộ')
    print(f'📚 Knowledge Base: {len(KNOWLEDGE_BASE)} tài liệu')
    for doc in KNOWLEDGE_BASE:
        print(f'   [{doc["doc_id"]}] {doc["title"]}')

    embedder, index = build_vector_store()

    client = None
    use_mock = True
    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            use_mock = False
            print('✅ Đã kết nối Anthropic API')
        except ImportError:
            print('⚠️  anthropic chưa cài. Chạy: pip install anthropic')

    if use_mock:
        print('⚡ Chạy ở MOCK MODE (không cần API key)')

    sample_questions = [
        'Reorder point của vải cotton là bao nhiêu?',
        'Tỷ lệ lỗi cho phép là bao nhiêu phần trăm?',
        'Khi nào cần dừng chuyền sản xuất?',
    ]

    chat_history = []
    print('\n' + '=' * 60)
    print('🤖 LUCKY STAR AI ASSISTANT — Demo câu hỏi mẫu')
    print('=' * 60)
    for question in sample_questions:
        print(f'\n👤 {question}')
        result = rag_chat(question, embedder, index, client, chat_history)
        print(f'🤖 {result["answer"]}')
        print(f'📎 Nguồn: {result["sources"]}')
        print('-' * 50)
        if not use_mock:
            chat_history.extend([
                {'role': 'user', 'content': question},
                {'role': 'assistant', 'content': result['answer']},
            ])

    return embedder, index, client


if __name__ == '__main__':
    import os
    run(api_key=os.environ.get('ANTHROPIC_API_KEY'))

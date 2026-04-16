import pytest
from langchain_core.messages import HumanMessage, AIMessage
from chatbot.graph import get_bot_response, get_messages_list, memory, build_graph

# モック用のテストデータ
USER_MESSAGE_1 = "1たす2は？"
USER_MESSAGE_2 = "東京駅のイベントの検索結果を教えて"

@pytest.fixture
def setup_memory():
    """
    テスト用のメモリを初期化。
    """
    memory.storage.clear()
    return memory

@pytest.fixture
def setup_graph():
    """
    テスト用に新しいグラフを構築。
    """
    return build_graph("gpt-4o-mini", memory)

def test_get_bot_response_single_message(setup_memory):
    """
    ボットがシンプルなメッセージに応答できるかをテスト。
    """
    response = get_bot_response(USER_MESSAGE_1, setup_memory)
    assert isinstance(response, str), "応答は文字列である必要があります。"
    assert "3" in response, "1たす2の計算結果が正しく応答されるべきです。"

def test_get_bot_response_multiple_messages(setup_memory):
    """
    複数のメッセージを処理してメモリに保存されるかをテスト。
    """
    get_bot_response(USER_MESSAGE_1, setup_memory)
    get_bot_response(USER_MESSAGE_2, setup_memory)
    messages = get_messages_list(setup_memory)
    assert len(messages) >= 2, "メッセージ履歴に少なくとも2つのエントリが含まれている必要があります。"
    assert any("1たす2" in msg['text'] for msg in messages if msg['class'] == 'user-message'), "ユーザーの入力が履歴に含まれる必要があります。"
    assert any("東京駅" in msg['text'] for msg in messages if msg['class'] == 'user-message'), "複数のメッセージが正しく保存される必要があります。"

def test_memory_clear_on_new_session(setup_memory):
    """
    新しいセッションでメモリがクリアされるかをテスト。
    """
    # 初期応答を生成してメモリにメッセージを保存
    get_bot_response(USER_MESSAGE_1, setup_memory)

    # メモリの状態を確認
    initial_messages = get_messages_list(setup_memory)
    assert len(initial_messages) > 0, "最初のメッセージがメモリに保存されていない可能性があります。"

    # メモリをクリア
    setup_memory.storage.clear()

    # 再度メッセージリストを取得し、メモリが空になっていることを確認
    cleared_messages = setup_memory.get({"configurable": {"thread_id": "1"}})

    # メモリが空であることを確認
    assert cleared_messages is None or 'channel_values' not in cleared_messages, "メモリがクリアされていません。"

def test_build_graph(setup_memory):
    """
    グラフが正しく構築され、応答を生成できるかをテスト。
    """
    graph = build_graph("gpt-4o-mini", setup_memory)
    response = graph.invoke(
        {"messages": [("user", USER_MESSAGE_1)]},
        {"configurable": {"thread_id": "1"}},
        stream_mode="values"
    )
    assert response["messages"][-1].content, "グラフが有効な応答を生成する必要があります。"

def test_get_messages_list(setup_memory):
    """
    メモリ内のメッセージリストが正しく取得されるかをテスト。
    """
    get_bot_response(USER_MESSAGE_1, setup_memory)
    messages = get_messages_list(setup_memory)
    assert len(messages) > 0, "応答後、メッセージリストは空であってはなりません。"
    assert any(isinstance(msg, dict) for msg in messages), "メッセージリストは辞書のリストである必要があります。"
    assert any(msg['class'] == 'user-message' for msg in messages), "メッセージリストにユーザーのメッセージが含まれている必要があります。"
    assert any(msg['class'] == 'bot-message' for msg in messages), "メッセージリストにボットの応答が含まれている必要があります。"

# 実行用
if __name__ == "__main__":
    pytest.main()
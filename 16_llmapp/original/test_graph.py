import pytest
from langchain_core.messages import HumanMessage, AIMessage
from original.graph import (
    get_bot_response,
    get_messages_list,
    memory,
    build_graph,
    define_tools,
)

# モック用のテストデータ
USER_MESSAGE_1 = "1たす2は？"
USER_MESSAGE_2 = "東京駅のイベントの検索結果を教えて"
USER_MESSAGE_3 = "有給休暇の日数は？"
THREAD_ID = "test_thread"
 
@pytest.fixture
def setup_memory():
    """
    テスト用のメモリを初期化。
    """
    memory.storage.clear()
    return memory

def test_define_tools(monkeypatch):
    """
    RAG未設定方針として、Retrieverツールが含まれないことをテスト。
    """
    from original import graph as graph_module

    class DummyDB:
        def as_retriever(self):
            return object()

    class DummyTool:
        def __init__(self, name):
            self.name = name

    monkeypatch.setattr(graph_module, "OpenAIEmbeddings", lambda model: object())
    monkeypatch.setattr(graph_module.os.path, "exists", lambda _: True)
    monkeypatch.setattr(graph_module, "Chroma", lambda **kwargs: DummyDB())
    monkeypatch.setattr(
        graph_module,
        "create_retriever_tool",
        lambda retriever, name, description: DummyTool(name),
    )
    monkeypatch.setattr(
        graph_module,
        "TavilySearchResults",
        lambda max_results=2: DummyTool("tavily_search_results_json"),
    )

    tools = graph_module.define_tools()
    assert len(tools) > 0, "ツールが正しく定義される必要があります。"
    assert not any(tool.name == "retrieve_company_rules" for tool in tools), (
        "RAG未設定方針のため、retrieve_company_rulesツールが定義されていたら失敗です。"
    )

def test_get_bot_response_single_message(setup_memory):
    """
    ボットがシンプルなメッセージに応答できるかをテスト。
    """
    response = get_bot_response(USER_MESSAGE_1, setup_memory, THREAD_ID)
    assert isinstance(response, str), "応答は文字列である必要があります。"
    assert "3" in response, "1たす2の計算結果が正しく応答されるべきです。"

def test_get_bot_response_without_rag(setup_memory):
    """
    RAG未設定でもボットが応答できることをテスト。
    """
    response = get_bot_response(USER_MESSAGE_3, setup_memory, THREAD_ID)
    assert isinstance(response, str), "応答は文字列である必要があります。"
    assert response != "", "RAG未設定でも空でない応答が返るべきです。"

def test_get_bot_response_multiple_messages(setup_memory):
    """
    複数のメッセージを処理してメモリに保存されるかをテスト。
    """
    get_bot_response(USER_MESSAGE_1, setup_memory, THREAD_ID)
    get_bot_response(USER_MESSAGE_2, setup_memory, THREAD_ID)
    messages = get_messages_list(setup_memory, THREAD_ID)
    assert len(messages) >= 2, "メモリに2つ以上のメッセージが保存されるべきです。"
    assert any("1たす2" in msg['text'] for msg in messages if msg['class'] == 'user-message'), "メモリに最初のユーザーメッセージが保存されるべきです。"
    assert any("東京駅" in msg['text'] for msg in messages if msg['class'] == 'user-message'), "メモリに2番目のユーザーメッセージが保存されるべきです。"

def test_memory_clear_on_new_session(setup_memory):
    """
    新しいセッションでメモリがクリアされるかをテスト。
    """
    get_bot_response(USER_MESSAGE_1, setup_memory, THREAD_ID)
    initial_messages = get_messages_list(setup_memory, THREAD_ID)
    assert len(initial_messages) > 0, "最初のメッセージがメモリに保存されていない可能性があります。"

    setup_memory.storage.clear()
    cleared_messages = setup_memory.get({"configurable": {"thread_id": THREAD_ID}})
    assert cleared_messages is None or 'channel_values' not in cleared_messages, "メモリがクリアされていません。"

def test_build_graph(setup_memory):
    """
    グラフが正しく構築され、応答を生成できるかをテスト。
    """
    graph = build_graph("gpt-4o-mini", setup_memory)
    response = graph.invoke(
        {"messages": [("user", USER_MESSAGE_1)]},
        {"configurable": {"thread_id": THREAD_ID}},
        stream_mode="values"
    )
    assert response["messages"][-1].content, "グラフが有効な応答を生成する必要があります。"

def test_get_messages_list(setup_memory):
    """
    メモリ内のメッセージリストが正しく取得されるかをテスト。
    """
    get_bot_response(USER_MESSAGE_1, setup_memory, THREAD_ID)
    messages = get_messages_list(setup_memory, THREAD_ID)
    assert len(messages) > 0, "応答後、メッセージリストは空であってはなりません。"
    assert any(isinstance(msg, dict) for msg in messages), "メッセージリストは辞書のリストである必要があります。"
    assert any(msg['class'] == 'user-message' for msg in messages), "メッセージリストにユーザーのメッセージが含まれている必要があります。"
    assert any(msg['class'] == 'bot-message' for msg in messages), "メッセージリストにボットの応答が含まれている必要があります。"


def test_get_messages_list_returns_empty_when_memory_payload_is_none(monkeypatch):
    """
    memory.getがNoneを返した場合でも、空配列を返すことを期待する。
    """
    from original import graph as graph_module

    class BrokenMemory:
        def get(self, *_args, **_kwargs):
            return None

    messages = graph_module.get_messages_list(BrokenMemory(), THREAD_ID)
    assert messages == []


def test_get_messages_list_returns_empty_when_memory_payload_has_no_channel_values(monkeypatch):
    """
    memory.getが不正構造を返した場合でも、空配列を返すことを期待する。
    """
    from original import graph as graph_module

    class BrokenMemory:
        def get(self, *_args, **_kwargs):
            return {"unexpected": "shape"}

    messages = graph_module.get_messages_list(BrokenMemory(), THREAD_ID)
    assert messages == []


def test_get_bot_response_returns_fallback_message_when_invoke_raises(monkeypatch):
    """
    graph.invokeで例外が発生した場合、固定文言を返すことを期待する。
    """
    from original import graph as graph_module

    class RaisingGraph:
        def invoke(self, *_args, **_kwargs):
            raise RuntimeError("invoke failed")

    monkeypatch.setattr(graph_module, "graph", RaisingGraph())

    response = graph_module.get_bot_response(USER_MESSAGE_1, memory, THREAD_ID)
    assert response == "現在応答できません。時間をおいて再試行してください。"


def test_get_bot_response_returns_fallback_message_when_build_graph_raises(monkeypatch):
    """
    graph未初期化かつbuild_graphで例外が起きた場合も、固定文言を返すことを期待する。
    """
    from original import graph as graph_module

    monkeypatch.setattr(graph_module, "graph", None)

    def raise_build_graph(*_args, **_kwargs):
        raise RuntimeError("build failed")

    monkeypatch.setattr(graph_module, "build_graph", raise_build_graph)

    response = graph_module.get_bot_response(USER_MESSAGE_1, memory, THREAD_ID)
    assert response == "現在応答できません。時間をおいて再試行してください。"


def test_get_messages_list_handles_non_string_human_message_content():
    """
    HumanMessage.contentが文字列以外でも、例外を出さずメッセージ変換できることを期待する。
    """
    from original import graph as graph_module

    class DummyMemory:
        def get(self, *_args, **_kwargs):
            return {
                "channel_values": {
                    "messages": [
                        HumanMessage(content=[{"type": "text", "text": "hello"}]),
                    ]
                }
            }

    messages = graph_module.get_messages_list(DummyMemory(), THREAD_ID)
    assert len(messages) == 1
    assert messages[0]["class"] == "user-message"


def test_get_messages_list_skips_ai_message_when_content_is_whitespace_only():
    """
    AIMessage.contentが空白のみの場合は表示対象から除外することを期待する。
    """
    from original import graph as graph_module

    class DummyMemory:
        def get(self, *_args, **_kwargs):
            return {
                "channel_values": {
                    "messages": [
                        AIMessage(content="   \n\t  "),
                    ]
                }
            }

    messages = graph_module.get_messages_list(DummyMemory(), THREAD_ID)
    assert messages == []

# 実行用
if __name__ == "__main__":
    pytest.main()
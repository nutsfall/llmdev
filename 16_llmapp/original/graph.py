import os
from dotenv import load_dotenv
import tiktoken
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.tools.retriever import create_retriever_tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_community.tools.tavily_search import TavilySearchResults
from typing import Annotated
from typing_extensions import TypedDict

# 環境変数を読み込む
load_dotenv(".env")
os.environ['OPENAI_API_KEY'] = os.environ['API_KEY']

# 使用するモデル名
MODEL_NAME = "gpt-4o-mini" 
FALLBACK_RESPONSE = "現在応答できません。時間をおいて再試行してください。"

# MemorySaverインスタンスの作成
memory = MemorySaver()

# グラフを保持する変数の初期化
graph = None

# ===== Stateクラスの定義 =====
# Stateクラス: メッセージのリストを保持する辞書型
class State(TypedDict):
    messages: Annotated[list, add_messages]

# ===== インデックスの構築 =====
def create_index(persist_directory, embedding_model):
    # 実行中のスクリプトのパスを取得
    current_script_path = os.path.abspath(__file__)
    # 実行中のスクリプトが存在するディレクトリを取得
    current_directory = os.path.dirname(current_script_path)

    # テキストファイルを読込
    loader = DirectoryLoader(f'{current_directory}/data/pdf', glob="./*.pdf",   loader_cls=PyPDFLoader)
    documents = loader.load()

    # チャンクに分割
    encoding_name = tiktoken.encoding_for_model(MODEL_NAME).name
    text_splitter = CharacterTextSplitter.from_tiktoken_encoder(encoding_name)
    texts = text_splitter.split_documents(documents)

    # 新規にIndexを構築
    db = Chroma.from_documents(texts, embedding_model, persist_directory=persist_directory)
    return db

def define_tools():
    return [TavilySearchResults(max_results=2)]

# ===== グラフの構築 =====
def build_graph(model_name, memory):
    """
    グラフのインスタンスを作成し、ツールノードやチャットボットノードを追加します。
    モデル名とメモリを使用して、実行可能なグラフを作成します。
    """
    # グラフのインスタンスを作成
    graph_builder = StateGraph(State)

    # ツールノードの作成
    tools = define_tools()
    tool_node = ToolNode(tools)
    graph_builder.add_node("tools", tool_node)

    # チャットボットノードの作成
    llm = ChatOpenAI(model_name=model_name)
    llm_with_tools = llm.bind_tools(tools)
    
    # チャットボットの実行方法を定義
    def chatbot(state: State):
        return {"messages": [llm_with_tools.invoke(state["messages"])]}
    
    graph_builder.add_node("chatbot", chatbot)

    # 実行可能なグラフの作成
    graph_builder.add_conditional_edges(
        "chatbot",
        tools_condition,
    )
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.set_entry_point("chatbot")
    
    return graph_builder.compile(checkpointer=memory)

# ===== グラフを実行する関数 =====
def stream_graph_updates(graph: StateGraph, user_message: str, thread_id):
    """
    ユーザーからのメッセージを元に、グラフを実行し、チャットボットの応答をストリーミングします。
    """
    response = graph.invoke(
        {"messages": [("user", user_message)]},
        {"configurable": {"thread_id": thread_id}},
        stream_mode="values"
    )
    return response["messages"][-1].content


def _normalize_message_content(content):
    if isinstance(content, str):
        return content
    return str(content)


def _append_formatted_message(messages, css_class, content):
    normalized = _normalize_message_content(content)
    messages.append({'class': css_class, 'text': normalized.replace('\n', '<br>')})

# ===== 応答を返す関数 =====
def get_bot_response(user_message, memory, thread_id):
    """
    ユーザーのメッセージに基づき、ボットの応答を取得します。
    初回の場合、新しいグラフを作成します。
    """
    global graph
    try:
        # グラフがまだ作成されていない場合、新しいグラフを作成
        if graph is None:
            graph = build_graph(MODEL_NAME, memory)

        # グラフを実行してボットの応答を取得
        return stream_graph_updates(graph, user_message, thread_id)
    except Exception:
        return FALLBACK_RESPONSE

# ===== メッセージの一覧を取得する関数 =====
def get_messages_list(memory, thread_id):
    """
    メモリからメッセージ一覧を取得し、ユーザーとボットのメッセージを分類します。
    """
    messages = []
    # メモリからメッセージを取得
    try:
        payload = memory.get({"configurable": {"thread_id": thread_id}})
        if not payload:
            return messages
        channel_values = payload.get('channel_values')
        if not isinstance(channel_values, dict):
            return messages
        memories = channel_values.get('messages', [])
    except Exception:
        return messages

    for message in memories:
        if isinstance(message, HumanMessage):
            # ユーザーからのメッセージ
            _append_formatted_message(messages, 'user-message', message.content)
        elif isinstance(message, AIMessage):
            # ボットからのメッセージ（最終回答）
            content = _normalize_message_content(message.content)
            if content.strip() == "":
                continue
            _append_formatted_message(messages, 'bot-message', message.content)
    return messages
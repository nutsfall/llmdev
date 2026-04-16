import pytest
from flask import template_rendered
from chatbot.app import app
from chatbot.graph import memory, get_messages_list

@pytest.fixture
def client():
    """
    Flaskテストクライアントを作成。
    """
    app.config['TESTING'] = True
    client = app.test_client()
    yield client

def test_index_get_request(client):
    """
    GETリクエストで初期画面が正しく表示されるかをテスト。
    """
    with client as c:
        response = c.get('/')
        assert response.status_code == 200, "GETリクエストに対してステータスコード200を返すべきです。"
        assert b"<form" in response.data, "HTMLにフォーム要素が含まれている必要があります。"
        assert memory.storage == {}, "GETリクエストでメモリが初期化されるべきです。"

def test_index_post_request(client):
    """
    POSTリクエストでボットの応答が正しく返されるかをテスト。
    """
    user_message = "1たす2は？"

    with client as c:
        response = c.post('/', data={'user_message': user_message})
        decoded_data = response.data.decode('utf-8')  # バイト文字列をデコード
        assert response.status_code == 200, "POSTリクエストに対してステータスコード200を返すべきです。"
        assert "1たす2" in decoded_data, "ユーザーの入力がHTML内に表示されるべきです。"
        assert "3" in decoded_data, "ボットの応答が正しくHTML内に表示されるべきです。"

def test_memory_persistence(client):
    """
    複数のPOSTリクエストでメッセージが正しくメモリに保持されるかをテスト。
    """
    user_message_1 = "1たす2は？"
    user_message_2 = "こんにちは！"

    with client as c:
        c.post('/', data={'user_message': user_message_1})
        c.post('/', data={'user_message': user_message_2})
        
        # メモリの状態を取得
        messages = get_messages_list(memory)
        assert len(messages) >= 2, "メモリに2つ以上のメッセージが保存されるべきです。"
        assert any("1たす2" in msg['text'] for msg in messages if msg['class'] == 'user-message'), "メモリに最初のユーザーメッセージが保存されるべきです。"
        assert any("こんにちは" in msg['text'] for msg in messages if msg['class'] == 'user-message'), "メモリに2番目のユーザーメッセージが保存されるべきです。"

def test_template_rendering(client):
    """
    テンプレートが正しくレンダリングされているかをテスト。
    """
    user_message = "1たす2は？"

    with client as c:
        response = c.post('/', data={'user_message': user_message})
        decoded_data = response.data.decode('utf-8')  # バイト文字列をデコード

        assert response.status_code == 200, "POSTリクエストでステータスコード200を返すべきです。"
        assert "1たす2" in decoded_data, "テンプレートでユーザーの入力がレンダリングされるべきです。"
        assert "3" in decoded_data, "テンプレートでボットの応答がレンダリングされるべきです。"
# VS Codeのデバッグ実行で `from chatbot.graph` でエラーを出さない対策
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from flask import Flask, render_template, request, make_response, session 
from original.graph import get_bot_response, get_messages_list, memory

MAX_USER_MESSAGE_LENGTH = 1000

# Flaskアプリケーションのセットアップ
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # セッション用の秘密鍵


def _render_index(messages=None, error_message=None):
    if messages is None:
        messages = []
    return make_response(
        render_template('index.html', messages=messages, error_message=error_message)
    )

@app.route('/', methods=['GET', 'POST'])
def index():
    # セッションからthread_idを取得、なければ新しく生成してセッションに保存
    if 'thread_id' not in session:
        session['thread_id'] = str(uuid.uuid4())  # ユーザー毎にユニークなIDを生成

    # GETリクエスト時は初期メッセージ表示
    if request.method == 'GET':
        # メモリをクリア
        memory.storage.clear()
        # 対話履歴を初期化
        return _render_index()

    # ユーザーからのメッセージを取得
    user_message = request.form.get('user_message')

    # 欠落・空文字・長文入力のバリデーション
    if user_message is None or user_message.strip() == '':
        return _render_index(error_message='メッセージを入力してください。')
    if len(user_message) > MAX_USER_MESSAGE_LENGTH:
        return _render_index(error_message='メッセージは1000文字以内で入力してください。')
    
    # ボットのレスポンスを取得（メモリに保持）
    get_bot_response(user_message, memory, session['thread_id'])

    # メモリからメッセージの取得
    messages = get_messages_list(memory, session['thread_id'])

    # レスポンスを返す
    return _render_index(messages=messages)

@app.route('/clear', methods=['POST'])
def clear():
    # セッションからthread_idを削除
    session.pop('thread_id', None)

    # メモリをクリア
    memory.storage.clear()
    # 対話履歴を初期化
    return _render_index()

if __name__ == '__main__':
    app.run(debug=True)
# # テストコードの仕様
#
# `06_test` フォルダの中に `test_authenticator.py` という Python ファイルを作成し、
# `Authenticator` クラスをテストするためのコードを記述してください。
# 行うテストは以下の 4 つとします。
#
# 1. `register()` メソッドで、ユーザーが正しく登録されるか
# - ユーザーを登録し、正しく登録されているかを `assert` で評価します。
#
# 2. `register()` メソッドで、すでに存在するユーザー名で登録を試みた場合に、エラーメッセージが出力されるか
# - 同じユーザーを登録し、例外が発生することを `pytest.raises()` で確認します。
#
# 3. `login()` メソッドで、正しいユーザー名とパスワードでログインできるか
# - ユーザーを登録し、ログインメッセージを `assert` で評価します。
#
# 4. `login()` メソッドで、誤ったパスワードでエラーが出るか
# - ユーザーを登録し、誤ったパスワードでログインして例外が発生することを `pytest.raises()` で確認します。

import pytest
from authenticator import Authenticator

@pytest.fixture
def auth():
    return Authenticator()

@pytest.mark.parametrize("username, password", [
    ("user1", "password1"),
    ("user2", "password2"),
])
def test_register(auth,username, password):
    auth.register(username, password)
    assert auth.users[username] == password

@pytest.mark.parametrize("username, password", [
    ("user1", "password1"),
    ("user2", "password2"),
]) 
def test_register_existing_user(auth, username, password):
    auth.register(username, password)
    with pytest.raises(ValueError):
        auth.register(username, password)

@pytest.mark.parametrize("username, password", [
    ("user1", "password1"),
    ("user2", "password2"),
])
def test_login_success(auth, username, password):
    auth.register(username, password)
    assert auth.login(username, password) == "ログイン成功"

@pytest.mark.parametrize("username, password", [
    ("user1", "password1"),
    ("user2", "password2"),
])
def test_login_wrong_password(auth, username, password):
    auth.register(username, password)
    with pytest.raises(ValueError):
        auth.login(username, "wrongpassword")
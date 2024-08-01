from unittest.mock import patch, AsyncMock, MagicMock

from .utils import *
from ..routers.auth import *
from jose import jwt
from datetime import timedelta, datetime, timezone
import pytest


app.dependency_overrides[get_db] = override_get_db


def test_verify_password():
    plain_password = "testpassword"
    hashed_password = bcrypt_context.hash(plain_password)

    assert verify_password(plain_password, hashed_password) == True

    wrong_password = "wrongpassword"
    assert verify_password(wrong_password, hashed_password) == False


def test_authenticate_user(test_user):
    db = TestingSessionLocal()

    authenticated_user = authenticate_user(test_user.username, 'testpassword', db)
    assert authenticated_user is not None
    assert authenticated_user.username == test_user.username

    non_existent_user = authenticate_user('wrong_username', 'testpassword', db)
    assert non_existent_user is False

    wrong_password_user = authenticate_user(test_user.username, 'wrongpassword', db)
    assert wrong_password_user is False


def test_create_access_token():
    username = "testuser"
    user_id = 1
    role = "user"
    expires_delta = timedelta(minutes=15)

    token = create_access_token(username, user_id, role, expires_delta)
    decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert decoded_token["sub"] == username
    assert decoded_token["id"] == user_id
    assert decoded_token["role"] == role
    assert decoded_token["exp"] is not None

    exp_time = datetime.fromtimestamp(decoded_token["exp"], timezone.utc)
    expected_exp_time = datetime.now(timezone.utc) + expires_delta

    assert abs((exp_time - expected_exp_time).total_seconds()) < 5


@pytest.mark.asyncio
async def test_get_current_user():
    request_with_token = Request(scope={
        "type": "http",
        "headers": [(b"cookie", b"access_token=testtoken")]
    })

    request_without_token = Request(scope={
        "type": "http",
        "headers": []
    })

    valid_payload = {"sub": "testuser", "id": "1"}
    invalid_payload = {"sub": None, "id": None}

    with patch("jose.jwt.decode") as mock_decode, \
            patch("blog_app.routers.auth.logout", new_callable=AsyncMock) as mock_logout:
        result = await get_current_user(request_without_token)
        assert result is None

        mock_decode.return_value = valid_payload
        result = await get_current_user(request_with_token)
        assert result == {"username": "testuser", "id": "1"}

        mock_decode.return_value = invalid_payload
        result = await get_current_user(request_with_token)
        assert result is None
        mock_logout.assert_awaited_once()

        mock_decode.side_effect = jwt.JWTError
        result = await get_current_user(request_with_token)
        assert result is None
        assert mock_logout.call_count == 2


def test_login_for_access_token(test_user):
    login_data = {
        "username": test_user.username,
        "password": "testpassword"
    }
    response = client.post("/auth/token", data=login_data)
    assert response.status_code == 200
    assert response.json() is True
    cookies = response.cookies
    assert "access_token" in cookies


def test_auth_page():
    response = client.get("/auth")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "Register?" in response.text


def test_login_success(override_db, mock_login_for_access_token):
    mock_login_for_access_token.return_value = True
    response = client.post("/", data={"username": "testuser", "password": "testpass"})

    assert response.status_code == 302
    assert response.headers["location"] == "/tweets"

def test_register_page():
    response = client.get("auth/register")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "Already have an account?" in response.text


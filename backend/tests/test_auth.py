"""Phase 1 auth tests: registration, login, JWT lifecycle, refresh rotation,
reuse detection, logout blacklist and RBAC."""

API = "/api/v1"


async def register_user(
    client: object,
    email: str = "owner@test.dev",
    password: str = "Secret123!",
    team_name: str = "Test Co",
    name: str = "Owner One",
) -> dict:
    resp = await client.post(
        f"{API}/auth/register",
        json={"name": name, "team_name": team_name, "email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


async def login(client: object, email: str, password: str) -> dict:
    resp = await client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def bearer(data: dict) -> dict:
    return {"Authorization": f"Bearer {data['access_token']}"}


class TestRegisterAndLogin:
    async def test_register_creates_team_and_owner_with_tokens(self, client):
        data = await register_user(client)
        assert data["user"]["role"] == "owner"
        assert data["user"]["email"] == "owner@test.dev"
        assert data["access_token"] and data["refresh_token"]
        assert data["expires_in"] == 15 * 60

    async def test_register_duplicate_email_conflicts(self, client):
        await register_user(client)
        resp = await client.post(
            f"{API}/auth/register",
            json={
                "name": "Other",
                "team_name": "Other Co",
                "email": "owner@test.dev",
                "password": "Secret123!",
            },
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "EMAIL_TAKEN"

    async def test_register_short_password_rejected(self, client):
        resp = await client.post(
            f"{API}/auth/register",
            json={"name": "A", "team_name": "Co", "email": "a@test.dev", "password": "short"},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    async def test_login_ok_returns_tokens_and_user(self, client):
        await register_user(client)
        data = await login(client, "owner@test.dev", "Secret123!")
        assert data["user"]["email"] == "owner@test.dev"
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password_401(self, client):
        await register_user(client)
        resp = await client.post(
            f"{API}/auth/login", json={"email": "owner@test.dev", "password": "WrongPass1!"}
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    async def test_login_unknown_email_same_error_as_wrong_password(self, client):
        resp = await client.post(
            f"{API}/auth/login", json={"email": "ghost@test.dev", "password": "Whatever1!"}
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


class TestMe:
    async def test_me_without_token_401(self, client):
        resp = await client.get(f"{API}/auth/me")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "NOT_AUTHENTICATED"

    async def test_me_returns_profile_and_team(self, client):
        data = await register_user(client, team_name="Profile Co")
        resp = await client.get(f"{API}/auth/me", headers=bearer(data))
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["user"]["role"] == "owner"
        assert body["team"]["name"] == "Profile Co"
        assert body["team"]["plan"] == "free"
        assert body["team"]["slug"]


class TestRefreshRotation:
    async def test_refresh_rotates_and_reuse_kills_whole_family(self, client):
        data = await register_user(client)

        # 1. rotate: old refresh -> new pair
        resp = await client.post(
            f"{API}/auth/refresh", json={"refresh_token": data["refresh_token"]}
        )
        assert resp.status_code == 200
        second_pair = resp.json()["data"]
        assert second_pair["refresh_token"] != data["refresh_token"]

        # 2. replay the OLD refresh -> theft detected, 401
        replay = await client.post(
            f"{API}/auth/refresh", json={"refresh_token": data["refresh_token"]}
        )
        assert replay.status_code == 401
        assert replay.json()["error"]["code"] == "REFRESH_REUSE_DETECTED"

        # 3. the legitimately-rotated token is dead too: whole family revoked
        third = await client.post(
            f"{API}/auth/refresh", json={"refresh_token": second_pair["refresh_token"]}
        )
        assert third.status_code == 401

    async def test_access_token_cannot_be_used_as_refresh(self, client):
        data = await register_user(client)
        resp = await client.post(
            f"{API}/auth/refresh", json={"refresh_token": data["access_token"]}
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "TOKEN_INVALID"


class TestLogout:
    async def test_logout_blacklists_access_token(self, client):
        data = await register_user(client)
        headers = bearer(data)

        resp = await client.get(f"{API}/auth/me", headers=headers)
        assert resp.status_code == 200

        resp = await client.post(f"{API}/auth/logout", headers=headers)
        assert resp.status_code == 200

        resp = await client.get(f"{API}/auth/me", headers=headers)
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "TOKEN_REVOKED"


class TestRbac:
    async def test_viewer_cannot_invite_members(self, client):
        owner = await register_user(client, email="owner2@test.dev", team_name="Invite Co")
        resp = await client.post(
            f"{API}/teams/invite",
            json={"email": "viewer@test.dev", "role": "viewer"},
            headers=bearer(owner),
        )
        assert resp.status_code == 201, resp.text
        temp_password = resp.json()["data"]["temp_password"]

        viewer = await login(client, "viewer@test.dev", temp_password)
        resp = await client.post(
            f"{API}/teams/invite",
            json={"email": "someone@test.dev", "role": "viewer"},
            headers=bearer(viewer),
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"

from tests.test_auth import API, bearer, login, register_user


class TestTeams:
    async def test_my_team_returns_detail_with_member_count(self, client):
        data = await register_user(client, team_name="Detail Co")
        resp = await client.get(f"{API}/teams/me", headers=bearer(data))
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["name"] == "Detail Co"
        assert body["members_count"] == 1
        assert body["plan"] == "free"

    async def test_owner_can_rename_team(self, client):
        data = await register_user(client, team_name="Old Name")
        resp = await client.put(
            f"{API}/teams/me", json={"name": "New Name"}, headers=bearer(data)
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "New Name"

    async def test_slug_conflict_rejected(self, client):
        await register_user(client, email="a@team.dev", team_name="Slug Co")
        data_b = await register_user(client, email="b@team.dev", team_name="Other Co")
        # team A got slug "slug-co" — team B cannot steal it
        resp = await client.put(
            f"{API}/teams/me", json={"slug": "slug-co"}, headers=bearer(data_b)
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "SLUG_TAKEN"

    async def test_members_list_contains_owner_and_invitee(self, client):
        owner = await register_user(client, email="own@m.dev", team_name="Members Co")
        resp = await client.post(
            f"{API}/teams/invite",
            json={"email": "mem@m.dev", "role": "member"},
            headers=bearer(owner),
        )
        assert resp.status_code == 201

        resp = await client.get(f"{API}/teams/members", headers=bearer(owner))
        assert resp.status_code == 200
        emails = [member["email"] for member in resp.json()["data"]]
        assert sorted(emails) == ["mem@m.dev", "own@m.dev"]

        # invited member can log in with the temp password and read members
        invite_resp = await client.post(
            f"{API}/teams/invite",
            json={"email": "mem2@m.dev", "role": "member"},
            headers=bearer(owner),
        )
        temp_password = invite_resp.json()["data"]["temp_password"]
        member_login = await login(client, "mem2@m.dev", temp_password)
        resp = await client.get(f"{API}/teams/members", headers=bearer(member_login))
        assert resp.status_code == 200

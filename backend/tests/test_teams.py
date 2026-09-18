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


class TestRemoveMember:
    async def test_owner_removes_member_login_dies(self, client):
        owner = await register_user(client, email="own@rm.dev", team_name="Remove Co")
        invite = await client.post(
            f"{API}/teams/invite",
            json={"email": "gone@rm.dev", "role": "member"},
            headers=bearer(owner),
        )
        member_id = invite.json()["data"]["user"]["id"]
        temp_password = invite.json()["data"]["temp_password"]
        member_login = await login(client, "gone@rm.dev", temp_password)

        resp = await client.delete(f"{API}/teams/members/{member_id}", headers=bearer(owner))
        assert resp.status_code == 200

        # removed member vanishes from list and their token is dead
        resp = await client.get(f"{API}/teams/members", headers=bearer(owner))
        assert [m["email"] for m in resp.json()["data"]] == ["own@rm.dev"]
        resp = await client.get(f"{API}/auth/me", headers=bearer(member_login))
        assert resp.status_code == 401

    async def test_cannot_remove_self(self, client):
        owner = await register_user(client, email="own@self.dev", team_name="Self Co")
        me = await client.get(f"{API}/auth/me", headers=bearer(owner))
        resp = await client.delete(
            f"{API}/teams/members/{me.json()['data']['user']['id']}", headers=bearer(owner)
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "CANNOT_REMOVE_SELF"

    async def test_remove_unknown_or_other_team_is_404(self, client):
        owner = await register_user(client, email="own@nf.dev", team_name="Nf Co")
        resp = await client.delete(
            f"{API}/teams/members/00000000-0000-0000-0000-000000000000",
            headers=bearer(owner),
        )
        assert resp.status_code == 404

    async def test_member_cannot_remove(self, client):
        owner = await register_user(client, email="own@mr.dev", team_name="Mr Co")
        invite = await client.post(
            f"{API}/teams/invite",
            json={"email": "mem@mr.dev", "role": "member"},
            headers=bearer(owner),
        )
        member_login = await login(client, "mem@mr.dev", invite.json()["data"]["temp_password"])
        resp = await client.delete(
            f"{API}/teams/members/{invite.json()['data']['user']['id']}",
            headers=bearer(member_login),
        )
        assert resp.status_code == 403

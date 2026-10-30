"""market 域集成测试：C 端成员档案（market_member）。

锁定四条规则：
1. **存在档案 = 是 C 端**——身份不再靠角色推断；
2. C 端接口**首次访问自动建档**（lazy ensure），微信/手机号/直连接口全覆盖；
3. 建档幂等：重复调用不新增记录、编号不复用；
4. 停用后的成员被 C 端接口拒绝。
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import engine


def _login(client: TestClient, username: str, password: str) -> dict[str, str]:
    resp = client.post("/system/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}


def _member_rows(user_id: int) -> list[dict[str, object]]:
    """直连库读该用户的档案行（绕过接口，验证落库事实）。"""
    with engine.connect() as conn:
        rows = conn.execute(
            text("select id, member_no, status from market_member where user_id = :u and is_deleted = false"),
            {"u": user_id},
        ).mappings()
        return [dict(row) for row in rows]


def _delete_member(user_id: int) -> None:
    """清掉该用户的档案，让每个用例从「未建档」开始（测试库 session 级共享）。"""
    with engine.begin() as conn:
        conn.execute(text("delete from market_member where user_id = :u"), {"u": user_id})


def _user_id_by_username(username: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text("select id from sys_user where username = :n"), {"n": username}).scalar_one()


class TestMemberAutoCreate:
    """C 端接口首访自动建档。"""

    def test_first_mini_call_creates_member(self, test_client: TestClient) -> None:
        """普通用户第一次调 C 端接口即建档，编号形如 U-NNNN。"""
        user = _login(test_client, "user", "123456")
        user_id = _user_id_by_username("user")
        _delete_member(user_id)
        assert _member_rows(user_id) == []

        resp = test_client.get("/market/mini/tasks", headers=user)
        assert resp.json()["success"] is True, resp.text

        rows = _member_rows(user_id)
        assert len(rows) == 1
        assert rows[0]["member_no"].startswith("U-")
        assert rows[0]["status"] == "ACTIVE"

    def test_repeat_calls_keep_single_member(self, test_client: TestClient) -> None:
        """建档幂等：多次访问只有一条档案，编号不变。"""
        user = _login(test_client, "user", "123456")
        user_id = _user_id_by_username("user")
        _delete_member(user_id)

        for _ in range(3):
            assert test_client.get("/market/mini/tasks", headers=user).json()["success"] is True

        rows = _member_rows(user_id)
        assert len(rows) == 1

    def test_disabled_member_is_rejected(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """停用后 C 端接口直接拒绝，且不会因为访问而「自愈」回启用。"""
        user = _login(test_client, "user", "123456")
        user_id = _user_id_by_username("user")
        _delete_member(user_id)
        assert test_client.get("/market/mini/tasks", headers=user).json()["success"] is True

        member = _member_rows(user_id)[0]
        updated = test_client.put(
            f"/market/members/update/{member['id']}", headers=auth_headers, json={"status": "DISABLED"}
        )
        assert updated.json()["success"] is True, updated.text

        denied = test_client.get("/market/mini/tasks", headers=user)
        assert denied.json()["success"] is False
        assert "停用" in denied.json()["msg"]
        assert _member_rows(user_id)[0]["status"] == "DISABLED"


class TestMemberAdmin:
    """运营端成员管理。"""

    def test_create_is_idempotent_and_lists_user_brief(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """纳入已建档用户不报错、不重复建档；列表带昵称/账号/手机号摘要。"""
        user_id = _user_id_by_username("user")
        _delete_member(user_id)

        first = test_client.post("/market/members/create", headers=auth_headers, json={"user_id": user_id})
        assert first.json()["success"] is True, first.text
        again = test_client.post("/market/members/create", headers=auth_headers, json={"user_id": user_id})
        assert again.json()["success"] is True, again.text
        assert first.json()["data"]["member_no"] == again.json()["data"]["member_no"]
        assert len(_member_rows(user_id)) == 1

        listed = test_client.get(
            "/market/members/list", headers=auth_headers, params={"page_no": 1, "page_size": 10, "user_id": user_id}
        ).json()["data"]
        assert listed["total"] == 1
        brief = listed["items"][0]["user"]
        assert brief["username"] == "user"
        assert brief["name"]
        assert brief["mobile"], "手机号是运营识别 C 端用户的主要手段"

    def test_member_no_is_globally_unique(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """不同用户的成员编号不重复（并发安全的流水号）。"""
        user_id = _user_id_by_username("user")
        _delete_member(user_id)
        created = test_client.post("/market/members/create", headers=auth_headers, json={"user_id": user_id})
        assert created.json()["success"] is True, created.text

        suffix = uuid.uuid4().hex[:6]
        with engine.begin() as conn:
            new_user_id = conn.execute(
                text(
                    "insert into sys_user (uuid, username, password, name, is_superuser, status, is_deleted, "
                    "created_time, updated_time) values (:uuid, :u, 'x', '成员测试', false, 0, false, now(), now()) "
                    "returning id"
                ),
                {"uuid": uuid.uuid4().hex, "u": f"member_test_{suffix}"},
            ).scalar_one()

        other = test_client.post("/market/members/create", headers=auth_headers, json={"user_id": new_user_id})
        assert other.json()["success"] is True, other.text
        assert other.json()["data"]["member_no"] != created.json()["data"]["member_no"]

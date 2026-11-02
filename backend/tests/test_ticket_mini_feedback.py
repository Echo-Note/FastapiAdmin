"""C 端意见反馈（/system/ticket/mini/feedback）集成测试。

C 端不走 RBAC 权限码，但数据必须收敛到本人：列表只返回自己提交的反馈，
提交时标题由内容首行自动生成，运营侧仍在 `/system/ticket/*` 处理同一批记录。
"""

from fastapi.testclient import TestClient


def _create_and_login_user(client: TestClient, admin_headers: dict, username: str) -> dict:
    resp = client.post(
        "/system/user/create",
        json={"username": username, "name": username, "password": "abc123456", "status": 0},
        headers=admin_headers,
    )
    assert resp.json()["success"] is True, resp.text
    login = client.post("/system/auth/login", data={"username": username, "password": "abc123456"})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


class TestMiniFeedback:
    def test_create_feedback_derives_title_from_content(self, test_client: TestClient, auth_headers: dict) -> None:
        user_h = _create_and_login_user(test_client, auth_headers, "fb_user1")

        resp = test_client.post(
            "/system/ticket/mini/feedback",
            json={"content": "任务大厅加载很慢\n下午基本刷不出来", "ticket_type": "bug"},
            headers=user_h,
        )
        assert resp.json()["success"] is True, resp.text
        data = resp.json()["data"]
        assert data["title"] == "任务大厅加载很慢"
        assert data["ticket_type"] == "bug"
        assert data["status"] == 0
        assert "下午基本刷不出来" in data["ticket_content"]

    def test_my_feedback_list_only_returns_own(self, test_client: TestClient, auth_headers: dict) -> None:
        owner_h = _create_and_login_user(test_client, auth_headers, "fb_owner")
        other_h = _create_and_login_user(test_client, auth_headers, "fb_other")

        resp = test_client.post(
            "/system/ticket/mini/feedback",
            json={"content": "希望能按金额排序任务", "ticket_type": "suggestion"},
            headers=owner_h,
        )
        assert resp.json()["success"] is True
        feedback_id = resp.json()["data"]["id"]

        owner_list = test_client.get("/system/ticket/mini/feedback", params={"page_no": 1, "page_size": 20}, headers=owner_h)
        assert owner_list.json()["success"] is True
        owner_ids = [item["id"] for item in owner_list.json()["data"]["items"]]
        assert owner_ids == [feedback_id]

        # 另一个 C 端用户看不到别人的反馈
        other_list = test_client.get("/system/ticket/mini/feedback", params={"page_no": 1, "page_size": 20}, headers=other_h)
        assert other_list.json()["success"] is True
        assert other_list.json()["data"]["items"] == []

    def test_feedback_requires_login(self, test_client: TestClient) -> None:
        assert test_client.get("/system/ticket/mini/feedback").status_code == 401
        assert test_client.post("/system/ticket/mini/feedback", json={"content": "未登录"}).status_code == 401

    def test_operator_ticket_api_still_requires_rbac(self, test_client: TestClient, auth_headers: dict) -> None:
        """C 端不经过 RBAC 接口：运营端工单列表对普通用户仍应拒绝（mini 接口存在的理由）。"""
        user_h = _create_and_login_user(test_client, auth_headers, "fb_user2")
        resp = test_client.get("/system/ticket/list", params={"page_no": 1, "page_size": 10}, headers=user_h)
        assert resp.json()["success"] is False

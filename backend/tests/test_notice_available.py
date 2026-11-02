"""C 端公告可见性（/system/notice/available）集成测试。

口径以模型注释为准：`0:草稿 1:已发布 2:已归档`。C 端只读列表只应看到**已发布**公告，
草稿不得外泄；列表按最新在前排序，并支持 limit 让 C 端一次多取一些。
"""

from fastapi.testclient import TestClient


def _create_notice(client: TestClient, headers: dict, title: str, status: int) -> None:
    resp = client.post(
        "/system/notice/create",
        json={"notice_title": title, "notice_type": "1", "notice_content": f"{title} 正文", "status": status},
        headers=headers,
    )
    assert resp.json()["success"] is True, resp.text


def _login_c_end_user(client: TestClient) -> dict:
    resp = client.post("/system/auth/login", data={"username": "user", "password": "123456"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}


class TestNoticeAvailable:
    def test_only_published_notices_visible(self, test_client: TestClient, auth_headers: dict) -> None:
        _create_notice(test_client, auth_headers, "公告-草稿", 0)
        _create_notice(test_client, auth_headers, "公告-已发布旧", 1)
        _create_notice(test_client, auth_headers, "公告-已发布新", 1)
        _create_notice(test_client, auth_headers, "公告-已归档", 2)

        user_h = _login_c_end_user(test_client)
        resp = test_client.get("/system/notice/available", params={"limit": 50}, headers=user_h)
        assert resp.json()["success"] is True, resp.text
        titles = [item["notice_title"] for item in resp.json()["data"]]
        assert "公告-已发布旧" in titles
        assert "公告-已发布新" in titles
        assert "公告-草稿" not in titles
        assert "公告-已归档" not in titles
        # 新的在前
        assert titles.index("公告-已发布新") < titles.index("公告-已发布旧")

    def test_limit_is_applied(self, test_client: TestClient, auth_headers: dict) -> None:
        _create_notice(test_client, auth_headers, "限流公告-A", 1)
        _create_notice(test_client, auth_headers, "限流公告-B", 1)

        user_h = _login_c_end_user(test_client)
        resp = test_client.get("/system/notice/available", params={"limit": 1}, headers=user_h)
        assert resp.json()["success"] is True
        assert len(resp.json()["data"]) == 1

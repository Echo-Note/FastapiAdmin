"""C 端公告可见性（/system/notice/available）集成测试。

口径以**管理端实际用法**为准：公告状态是「0 启用 / 1 停用」（2 归档预留）。
运营在管理端「发送」的公告落库就是 status=0，若按历史注释的「1 已发布」过滤，
C 端会一条都收不到。另外公告是公开内容，查询必须绕过 CRUD 的数据权限。
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
    def test_only_enabled_notices_visible(self, test_client: TestClient, auth_headers: dict) -> None:
        _create_notice(test_client, auth_headers, "公告-启用旧", 0)
        _create_notice(test_client, auth_headers, "公告-启用新", 0)
        _create_notice(test_client, auth_headers, "公告-停用", 1)

        user_h = _login_c_end_user(test_client)
        resp = test_client.get("/system/notice/available", params={"limit": 50}, headers=user_h)
        assert resp.json()["success"] is True, resp.text
        titles = [item["notice_title"] for item in resp.json()["data"]]
        assert "公告-启用旧" in titles
        assert "公告-启用新" in titles
        assert "公告-停用" not in titles
        # 新的在前
        assert titles.index("公告-启用新") < titles.index("公告-启用旧")

    def test_limit_is_applied(self, test_client: TestClient, auth_headers: dict) -> None:
        _create_notice(test_client, auth_headers, "限流公告-A", 0)
        _create_notice(test_client, auth_headers, "限流公告-B", 0)

        user_h = _login_c_end_user(test_client)
        resp = test_client.get("/system/notice/available", params={"limit": 1}, headers=user_h)
        assert resp.json()["success"] is True
        assert len(resp.json()["data"]) == 1

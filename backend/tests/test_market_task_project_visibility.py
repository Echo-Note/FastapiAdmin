"""market 域集成测试：项目结束后（已关闭 / 已删除）其任务不再出现在运营端任务列表、目录统计与 C 端大厅。

项目的生命周期结束后，任务数据保留在库里以便追溯，但不应再被分派/接单/统计。
"""

import uuid
from typing import Any

from fastapi.testclient import TestClient


class TestInactiveProjectVisibility:
    """已关闭 / 已软删除项目的任务对外不可见。"""

    def _token(self, client: TestClient, username: str, password: str) -> dict[str, str]:
        resp = client.post("/system/auth/login", data={"username": username, "password": password})
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}

    def _setup_project_with_task(self, client: TestClient, headers: dict[str, str], *, publish_task: bool) -> tuple[int, int]:
        """建公司 + 项目（关联一个三级任务）并发布项目，返回 (project_id, task_id)。"""
        suffix = uuid.uuid4().hex[:8]
        company_id = client.post(
            "/market/companies/create", headers=headers, json={"name": f"关闭项目测试公司{suffix}"}
        ).json()["data"]["id"]

        resp = client.get("/market/items/list", headers=headers, params={"page_no": 1, "page_size": 100})
        item = next(i for i in resp.json()["data"]["items"] if i["code"] == "ITEM-0011")
        project = client.post(
            "/market/projects/create",
            headers=headers,
            json={
                "name": f"关闭项目测试{suffix}",
                "company_id": company_id,
                "period": "2026-12-31",
                "item_ids": [item["id"]],
            },
        ).json()["data"]
        project_id = project["id"]
        assert client.post(f"/market/projects/publish/{project_id}", headers=headers).json()["success"]

        tasks = client.get(
            "/market/tasks/list", headers=headers, params={"page_no": 1, "page_size": 10, "project_id": project_id}
        ).json()["data"]["items"]
        assert tasks, "发布项目后应生成任务"
        task_id = tasks[0]["id"]
        if publish_task:
            assert client.post(f"/market/tasks/publish/{task_id}", headers=headers).json()["success"]
        return project_id, task_id

    def _task_ids(self, client: TestClient, headers: dict[str, str], project_id: int) -> list[int]:
        params: dict[str, Any] = {"page_no": 1, "page_size": 20, "project_id": project_id}
        items = client.get("/market/tasks/list", headers=headers, params=params).json()["data"]["items"]
        return [t["id"] for t in items]

    def test_closed_project_tasks_hidden_from_list_and_facets(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """项目关闭后：其任务从任务列表与目录统计中消失，显式要求时才返回。"""
        project_id, task_id = self._setup_project_with_task(test_client, auth_headers, publish_task=False)
        facets_before = test_client.get("/market/tasks/facets", headers=auth_headers).json()["data"]

        # 关闭项目
        closed = test_client.post(f"/market/projects/status/{project_id}", headers=auth_headers, json={"status": "CLOSED"})
        assert closed.json()["success"] is True, closed.text

        # 默认列表：不含该任务
        assert task_id not in self._task_ids(test_client, auth_headers, project_id)

        # 显式 include_closed_project：仍可追溯
        items = test_client.get(
            "/market/tasks/list",
            headers=auth_headers,
            params={"page_no": 1, "page_size": 20, "project_id": project_id, "include_closed_project": True},
        ).json()["data"]["items"]
        assert task_id in [t["id"] for t in items]

        # 目录统计不再计入
        facets_after = test_client.get("/market/tasks/facets", headers=auth_headers).json()["data"]
        assert sum(f["task_count"] for f in facets_after) <= sum(f["task_count"] for f in facets_before)

    def test_deleted_project_tasks_hidden_from_list(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """项目被软删除后，其任务同样不再出现在任务列表。"""
        project_id, task_id = self._setup_project_with_task(test_client, auth_headers, publish_task=False)
        assert task_id in self._task_ids(test_client, auth_headers, project_id)

        deleted = test_client.request("DELETE", "/market/projects/delete", headers=auth_headers, json=[project_id])
        assert deleted.json()["success"] is True, deleted.text

        assert task_id not in self._task_ids(test_client, auth_headers, project_id)

    def test_closed_project_task_not_in_hall(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """已发布任务所属项目关闭后，C 端大厅不应再出现该任务。"""
        project_id, task_id = self._setup_project_with_task(test_client, auth_headers, publish_task=True)
        user_headers = self._token(test_client, "user", "123456")

        def hall_ids() -> list[int]:
            items = test_client.get(
                "/market/mini/tasks", headers=user_headers, params={"page_no": 1, "page_size": 50}
            ).json()["data"]["items"]
            return [t["id"] for t in items]

        assert task_id in hall_ids()

        closed = test_client.post(f"/market/projects/status/{project_id}", headers=auth_headers, json={"status": "CLOSED"})
        assert closed.json()["success"] is True, closed.text
        assert task_id not in hall_ids()

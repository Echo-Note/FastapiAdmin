"""market 域集成测试：任务发布（定向分派须指定分派人员 + 发布即批量创建分派）。

任务实例细化到三级任务粒度：创建任务/项目关联均传 ``item_id``（三级任务），
``template_id`` 由后端按三级任务派生。
"""

from typing import Any

from fastapi.testclient import TestClient


class TestTaskPublish:
    """任务发布流程：定向分派必须指定分派人员，公开大厅无需分派人员。"""

    def _create_company(self, client: TestClient, headers: dict[str, str], name: str) -> int:
        """创建医药公司，返回公司 id。"""
        resp = client.post("/market/companies/create", headers=headers, json={"name": name})
        assert resp.status_code == 200, resp.text
        return resp.json()["data"]["id"]

    def _get_item_id(self, client: TestClient, headers: dict[str, str]) -> int:
        """取一个任务 id。"""
        resp = client.get("/market/items/list", headers=headers, params={"page_no": 1, "page_size": 1})
        assert resp.status_code == 200, resp.text
        items = resp.json()["data"]["items"]
        assert items, "无三级任务种子数据"
        return items[0]["id"]

    def _create_project(self, client: TestClient, headers: dict[str, str], company_id: int, item_id: int) -> int:
        """创建项目（关联三级任务），返回项目 id。"""
        resp = client.post(
            "/market/projects/create",
            headers=headers,
            json={"name": "测试药品", "company_id": company_id, "period": "2026-12-31", "item_ids": [item_id]},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["data"]["id"]

    def _publish_project_get_task(self, client: TestClient, headers: dict[str, str], project_id: int) -> dict[str, Any]:
        """发布项目（批量生成 open 任务），返回第一个任务。"""
        resp = client.post(f"/market/projects/publish/{project_id}", headers=headers)
        assert resp.status_code == 200, resp.text
        resp = client.get("/market/tasks/list", headers=headers, params={"page_no": 1, "page_size": 10, "project_id": project_id})
        items = resp.json()["data"]["items"]
        assert items, "发布项目后应生成任务实例"
        return items[0]

    def _get_user_id(self, client: TestClient, headers: dict[str, str]) -> int:
        """取 C 端普通用户 user 的 id，作为分派对象。"""
        resp = client.get("/system/user/list", headers=headers, params={"page_no": 1, "page_size": 100})
        assert resp.status_code == 200, resp.text
        items = resp.json()["data"]["items"]
        user = next(u for u in items if u.get("username") == "user")
        return user["id"]

    def _create_task(self, client: TestClient, headers: dict[str, str], project_id: int, item_id: int, assign_mode: str) -> int:
        """显式创建任务（指定分配方式），返回任务 id。"""
        resp = client.post(
            "/market/tasks/create",
            headers=headers,
            json={
                "project_id": project_id,
                "item_id": item_id,
                "period": "2026-12-31",
                "assign_mode": assign_mode,
            },
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["data"]["id"]

    def test_publish_direct_task_ok(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """定向分派任务可直接发布（发布与分派解耦，不再强制指定分派人员）。"""
        company_id = self._create_company(test_client, auth_headers, "测试医药公司甲")
        item_id = self._get_item_id(test_client, auth_headers)
        project_id = self._create_project(test_client, auth_headers, company_id, item_id)
        task_id = self._create_task(test_client, auth_headers, project_id, item_id, "direct")

        resp = test_client.post(f"/market/tasks/publish/{task_id}", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["status"] == "PUBLISHED"

    def test_publish_open_without_assignee_ok(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """公开大厅任务无需分派人员即可发布。"""
        company_id = self._create_company(test_client, auth_headers, "测试医药公司丙")
        item_id = self._get_item_id(test_client, auth_headers)
        project_id = self._create_project(test_client, auth_headers, company_id, item_id)

        resp = test_client.post(
            "/market/tasks/create",
            headers=auth_headers,
            json={
                "project_id": project_id,
                "item_id": item_id,
                "period": "2026-12-31",
                "assign_mode": "open",
            },
        )
        assert resp.status_code == 200, resp.text
        task_id = resp.json()["data"]["id"]

        resp = test_client.post(f"/market/tasks/publish/{task_id}", headers=auth_headers, json={})
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["status"] == "PUBLISHED"

    def test_publish_project_creates_open_task(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """发布项目生成的任务默认分配方式为公开大厅，且任务细化到三级任务。"""
        company_id = self._create_company(test_client, auth_headers, "测试医药公司丁")
        item_id = self._get_item_id(test_client, auth_headers)
        project_id = self._create_project(test_client, auth_headers, company_id, item_id)
        task = self._publish_project_get_task(test_client, auth_headers, project_id)
        assert task["assign_mode"] == "open"
        assert task["item_id"] == item_id

    def test_assign_open_task_switches_to_direct(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """对公开大厅任务定向分派用户后，任务分配方式应自动变为定向分派，并创建分派记录。"""
        company_id = self._create_company(test_client, auth_headers, "测试医药公司戊")
        item_id = self._get_item_id(test_client, auth_headers)
        project_id = self._create_project(test_client, auth_headers, company_id, item_id)
        task_id = self._create_task(test_client, auth_headers, project_id, item_id, "open")
        user_id = self._get_user_id(test_client, auth_headers)

        # 对 open 任务定向分派用户
        resp = test_client.post(
            "/market/assignments/create",
            headers=auth_headers,
            json={"task_id": task_id, "user_ids": [user_id]},
        )
        assert resp.status_code == 200, resp.text

        # 任务分配方式应变为 direct
        resp = test_client.get(f"/market/tasks/detail/{task_id}", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["assign_mode"] == "direct"

        # 应创建一条运营分派记录
        resp = test_client.get("/market/assignments/list", headers=auth_headers, params={"page_no": 1, "page_size": 10, "task_id": task_id})
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["user_id"] == user_id
        assert items[0]["source"] == "assigned"

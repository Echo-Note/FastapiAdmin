"""market 域集成测试：任务发布（定向分派须指定分派人员 + 发布即批量创建分派）。"""

from fastapi.testclient import TestClient


class TestTaskPublish:
    """任务发布流程：定向分派必须指定分派人员，公开大厅无需分派人员。"""

    def _create_company(self, client: TestClient, headers: dict, name: str) -> int:
        """创建医药公司，返回公司 id。"""
        resp = client.post("/market/companies/create", headers=headers, json={"name": name})
        assert resp.status_code == 200, resp.text
        return resp.json()["data"]["id"]

    def _get_template_id(self, client: TestClient, headers: dict) -> int:
        """取一个二级模板 id。"""
        resp = client.get("/market/templates/list", headers=headers, params={"page_no": 1, "page_size": 1})
        assert resp.status_code == 200, resp.text
        items = resp.json()["data"]["items"]
        assert items, "无二级模板种子数据"
        return items[0]["id"]

    def _create_project(self, client: TestClient, headers: dict, company_id: int, template_id: int) -> int:
        """创建项目（关联模板），返回项目 id。"""
        resp = client.post(
            "/market/projects/create",
            headers=headers,
            json={"name": "测试药品", "company_id": company_id, "period": "2026-12-31", "template_ids": [template_id]},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["data"]["id"]

    def _publish_project_get_task(self, client: TestClient, headers: dict, project_id: int) -> dict:
        """发布项目（批量生成 direct 任务），返回第一个任务。"""
        resp = client.post(f"/market/projects/publish/{project_id}", headers=headers)
        assert resp.status_code == 200, resp.text
        resp = client.get("/market/tasks/list", headers=headers, params={"page_no": 1, "page_size": 10, "project_id": project_id})
        items = resp.json()["data"]["items"]
        assert items, "发布项目后应生成任务实例"
        return items[0]

    def _get_user_id(self, client: TestClient, headers: dict) -> int:
        """取 C 端普通用户 user 的 id，作为分派对象。"""
        resp = client.get("/system/user/list", headers=headers, params={"page_no": 1, "page_size": 100})
        assert resp.status_code == 200, resp.text
        items = resp.json()["data"]["items"]
        user = next(u for u in items if u.get("username") == "user")
        return user["id"]

    def test_publish_direct_without_assignee_rejected(self, test_client: TestClient, auth_headers: dict) -> None:
        """定向分派任务不带分派人员发布应被拒绝。"""
        company_id = self._create_company(test_client, auth_headers, "测试医药公司甲")
        template_id = self._get_template_id(test_client, auth_headers)
        project_id = self._create_project(test_client, auth_headers, company_id, template_id)
        task = self._publish_project_get_task(test_client, auth_headers, project_id)
        assert task["assign_mode"] == "direct"

        resp = test_client.post(f"/market/tasks/publish/{task['id']}", headers=auth_headers, json={})
        assert resp.status_code == 400, resp.text
        body = resp.json()
        assert body["success"] is False
        assert "必须指定分派人员" in body["msg"]

    def test_publish_direct_with_assignee_creates_assignment(self, test_client: TestClient, auth_headers: dict) -> None:
        """定向分派任务带分派人员发布成功，并创建对应分派记录。"""
        company_id = self._create_company(test_client, auth_headers, "测试医药公司乙")
        template_id = self._get_template_id(test_client, auth_headers)
        project_id = self._create_project(test_client, auth_headers, company_id, template_id)
        task = self._publish_project_get_task(test_client, auth_headers, project_id)
        user_id = self._get_user_id(test_client, auth_headers)

        resp = test_client.post(f"/market/tasks/publish/{task['id']}", headers=auth_headers, json={"assignee_ids": [user_id]})
        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True
        assert resp.json()["data"]["status"] == "PUBLISHED"

        resp = test_client.get("/market/assignments/list", headers=auth_headers, params={"page_no": 1, "page_size": 10, "task_id": task["id"]})
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["user_id"] == user_id
        assert items[0]["source"] == "assigned"
        assert items[0]["status"] == "PENDING"

    def test_publish_open_without_assignee_ok(self, test_client: TestClient, auth_headers: dict) -> None:
        """公开大厅任务无需分派人员即可发布。"""
        company_id = self._create_company(test_client, auth_headers, "测试医药公司丙")
        template_id = self._get_template_id(test_client, auth_headers)
        project_id = self._create_project(test_client, auth_headers, company_id, template_id)

        resp = test_client.post(
            "/market/tasks/create",
            headers=auth_headers,
            json={
                "project_id": project_id,
                "template_id": template_id,
                "name": "测试药品-公开大厅",
                "period": "2026-12-31",
                "assign_mode": "open",
            },
        )
        assert resp.status_code == 200, resp.text
        task_id = resp.json()["data"]["id"]

        resp = test_client.post(f"/market/tasks/publish/{task_id}", headers=auth_headers, json={})
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["status"] == "PUBLISHED"

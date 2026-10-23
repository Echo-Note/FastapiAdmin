"""market 域集成测试：任务类型模板与任务。"""

from fastapi.testclient import TestClient


def _create_company(client: TestClient, headers: dict, name: str, code: str) -> int:
    client.post("/market/companies/create", json={"name": name, "code": code}, headers=headers)
    resp = client.get("/market/companies/list", params={"name": name}, headers=headers)
    return resp.json()["data"]["items"][0]["id"]


def _create_project(client: TestClient, headers: dict, code: str, company_id: int, period: str = "2026-10") -> int:
    """创建项目（对外），返回项目 ID。"""
    client.post(
        "/market/projects/create",
        json={"code": code, "name": f"项目{code}", "company_id": company_id, "period": period},
        headers=headers,
    )
    resp = client.get("/market/projects/list", params={"code": code}, headers=headers)
    return resp.json()["data"]["items"][0]["id"]


_TASK_NO_COUNTER = 100  # 避开种子任务号 1-44


def _create_template(client: TestClient, headers: dict, code: str) -> int:
    """创建采集模板（含 form_schema），返回模板 ID。"""
    client.post(
        "/market/templates/create",
        json={
            "code": code,
            "name": f"模板{code}",
            "scope": "1-4",
            "form_schema": [{"name": "hospital_name", "label": "医院名称", "type": "text", "required": True}],
        },
        headers=headers,
    )
    resp = client.get("/market/templates/list", params={"code": code}, headers=headers)
    return resp.json()["data"]["items"][0]["id"]


def _create_task_type(client: TestClient, headers: dict, code: str) -> int:
    global _TASK_NO_COUNTER
    template_id = _create_template(client, headers, f"tpl_{code}")
    _TASK_NO_COUNTER += 1
    client.post(
        "/market/task-types/create",
        json={
            "code": code,
            "name": f"类型{code}",
            "task_no": _TASK_NO_COUNTER,
            "template_id": template_id,
            "service_type": "医院管理",
            "service_item": "等级医院",
            "service_task": "等级医院管理",
            "unit": "家/月",
            "default_price": 3000,
        },
        headers=headers,
    )
    resp = client.get("/market/task-types/list", params={"code": code}, headers=headers)
    return resp.json()["data"]["items"][0]["id"]


class TestTaskType:
    def test_create(self, test_client: TestClient, auth_headers: dict) -> None:
        template_id = _create_template(test_client, auth_headers, "tpl_tt_create")
        resp = test_client.post(
            "/market/task-types/create",
            json={"code": "tt_create", "name": "创建类型", "task_no": 200, "template_id": template_id, "service_type": "医院管理", "service_item": "等级医院", "service_task": "采集", "unit": "家/月", "default_price": 100},
            headers=auth_headers,
        )
        assert resp.json()["success"] is True
        assert resp.json()["data"]["name"] == "创建类型"

    def test_create_duplicate_code_fails(self, test_client: TestClient, auth_headers: dict) -> None:
        template_id = _create_template(test_client, auth_headers, "tpl_tt_dup")
        resp = test_client.post(
            "/market/task-types/create",
            json={"code": "tt_create", "name": "重复编码", "task_no": 201, "template_id": template_id, "service_type": "医院管理", "service_item": "等级医院", "service_task": "采集", "unit": "家/月", "default_price": 100},
            headers=auth_headers,
        )
        assert resp.json()["success"] is False

    def test_list_and_update(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.get("/market/task-types/list", params={"code": "tt_create"}, headers=auth_headers)
        tt_id = resp.json()["data"]["items"][0]["id"]
        resp = test_client.put(f"/market/task-types/update/{tt_id}", json={"name": "改名类型"}, headers=auth_headers)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["name"] == "改名类型"

    def test_delete(self, test_client: TestClient, auth_headers: dict) -> None:
        client = test_client
        template_id = _create_template(test_client, auth_headers, "tpl_tt_del")
        client.post(
            "/market/task-types/create",
            json={"code": "tt_del", "name": "待删类型", "task_no": 202, "template_id": template_id, "service_type": "医院管理", "service_item": "等级医院", "service_task": "采集", "unit": "家/月", "default_price": 100},
            headers=auth_headers,
        )
        resp = client.get("/market/task-types/list", params={"code": "tt_del"}, headers=auth_headers)
        tt_id = resp.json()["data"]["items"][0]["id"]
        resp = client.request("DELETE", "/market/task-types/delete", json=[tt_id], headers=auth_headers)
        assert resp.json()["success"] is True


class TestTask:
    def test_create_default_price_from_type(self, test_client: TestClient, auth_headers: dict) -> None:
        tt_id = _create_task_type(test_client, auth_headers, "tt_task_a")
        resp = test_client.post(
            "/market/tasks/create",
            json={"task_no": "TASK-A-1", "task_type_id": tt_id, "period": "2026-10", "exec_qty": 2},
            headers=auth_headers,
        )
        assert resp.json()["success"] is True
        # 单价缺省取模板默认 3000；任务分类缺省取模板默认 periodic
        assert resp.json()["data"]["unit_price"] == 3000
        assert resp.json()["data"]["task_kind"] == "periodic"
        assert resp.json()["data"]["status"] == "DRAFT"

    def test_create_duplicate_task_no_fails(self, test_client: TestClient, auth_headers: dict) -> None:
        tt_id = _create_task_type(test_client, auth_headers, "tt_task_b")
        payload = {"task_no": "TASK-B-1", "task_type_id": tt_id, "period": "2026-10", "exec_qty": 1}
        assert test_client.post("/market/tasks/create", json=payload, headers=auth_headers).json()["success"] is True
        resp = test_client.post("/market/tasks/create", json=payload, headers=auth_headers)
        assert resp.json()["success"] is False

    def test_create_invalid_project_fails(self, test_client: TestClient, auth_headers: dict) -> None:
        tt_id = _create_task_type(test_client, auth_headers, "tt_task_c")
        resp = test_client.post(
            "/market/tasks/create",
            json={"task_no": "TASK-C-1", "task_type_id": tt_id, "period": "2026-10", "exec_qty": 1, "project_ids": [999999]},
            headers=auth_headers,
        )
        assert resp.json()["success"] is False

    def test_create_with_project_links(self, test_client: TestClient, auth_headers: dict) -> None:
        """任务创建时归集到项目，项目详情应能看到该任务（多对多）。"""
        company_id = _create_company(test_client, auth_headers, "任务公司G", "TSK-G")
        project_id = _create_project(test_client, auth_headers, "PRJ-G", company_id)
        tt_id = _create_task_type(test_client, auth_headers, "tt_task_g")
        resp = test_client.post(
            "/market/tasks/create",
            json={"task_no": "TASK-G-1", "task_type_id": tt_id, "period": "2026-10", "exec_qty": 1, "project_ids": [project_id]},
            headers=auth_headers,
        )
        assert resp.json()["success"] is True
        task_id = resp.json()["data"]["id"]

        resp = test_client.get(f"/market/projects/detail/{project_id}", headers=auth_headers)
        assert resp.json()["success"] is True
        assert task_id in resp.json()["data"]["task_ids"]

    def test_publish_and_update_guard(self, test_client: TestClient, auth_headers: dict) -> None:
        tt_id = _create_task_type(test_client, auth_headers, "tt_task_d")
        resp = test_client.post(
            "/market/tasks/create",
            json={"task_no": "TASK-D-1", "task_type_id": tt_id, "period": "2026-10", "exec_qty": 1},
            headers=auth_headers,
        )
        task_id = resp.json()["data"]["id"]

        # 发布
        resp = test_client.post(f"/market/tasks/publish/{task_id}", json={}, headers=auth_headers)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["status"] == "PUBLISHED"

        # 发布后不可修改
        resp = test_client.put(f"/market/tasks/update/{task_id}", json={"exec_qty": 5}, headers=auth_headers)
        assert resp.json()["success"] is False

        # 发布后不可删除
        resp = test_client.request("DELETE", "/market/tasks/delete", json=[task_id], headers=auth_headers)
        assert resp.json()["success"] is False

    def test_update_draft(self, test_client: TestClient, auth_headers: dict) -> None:
        tt_id = _create_task_type(test_client, auth_headers, "tt_task_e")
        resp = test_client.post(
            "/market/tasks/create",
            json={"task_no": "TASK-E-1", "task_type_id": tt_id, "period": "2026-10", "exec_qty": 1},
            headers=auth_headers,
        )
        task_id = resp.json()["data"]["id"]
        resp = test_client.put(f"/market/tasks/update/{task_id}", json={"exec_qty": 3, "unit_price": 2500}, headers=auth_headers)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["exec_qty"] == 3
        assert resp.json()["data"]["unit_price"] == 2500

    def test_delete_draft(self, test_client: TestClient, auth_headers: dict) -> None:
        tt_id = _create_task_type(test_client, auth_headers, "tt_task_f")
        resp = test_client.post(
            "/market/tasks/create",
            json={"task_no": "TASK-F-1", "task_type_id": tt_id, "period": "2026-10", "exec_qty": 1},
            headers=auth_headers,
        )
        task_id = resp.json()["data"]["id"]
        resp = test_client.request("DELETE", "/market/tasks/delete", json=[task_id], headers=auth_headers)
        assert resp.json()["success"] is True

    def test_list_and_detail(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.get("/market/tasks/list", params={"task_no": "TASK-A-1"}, headers=auth_headers)
        assert resp.json()["success"] is True
        task_id = resp.json()["data"]["items"][0]["id"]
        resp = test_client.get(f"/market/tasks/detail/{task_id}", headers=auth_headers)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["task_type"] is not None
        assert resp.json()["data"]["task_kind"] == "periodic"


class TestProject:
    def test_update_project(self, test_client: TestClient, auth_headers: dict) -> None:
        """更新项目（含编码唯一性校验），验证 ProjectUpdateSchema 支持 code 字段。"""
        company_id = _create_company(test_client, auth_headers, "项目公司1", "PRJ-COMP-1")
        project_id = _create_project(test_client, auth_headers, "PRJ-U-1", company_id)

        # 更新项目名与编码
        resp = test_client.put(
            f"/market/projects/update/{project_id}",
            json={"name": "改名项目", "code": "PRJ-U-1-NEW"},
            headers=auth_headers,
        )
        assert resp.json()["success"] is True
        assert resp.json()["data"]["code"] == "PRJ-U-1-NEW"
        assert resp.json()["data"]["name"] == "改名项目"

        # 编码唯一性：改为已存在编码失败
        _create_project(test_client, auth_headers, "PRJ-U-2", company_id)
        resp = test_client.put(
            f"/market/projects/update/{project_id}",
            json={"code": "PRJ-U-2"},
            headers=auth_headers,
        )
        assert resp.json()["success"] is False

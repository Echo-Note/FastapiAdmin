"""market 域集成测试：产品库（三要素判重 / 审核可见性 / 成果自动入库 / C 端检索）。

可见性是本模块的核心不变量：``approved`` 对所有人可见、``pending`` 仅提交人可见、
``rejected`` 谁都搜不到。
"""

import uuid
from typing import Any

from fastapi.testclient import TestClient


def _login(client: TestClient, username: str, password: str) -> dict[str, str]:
    """登录并返回认证头（运营端用 admin，C 端用 user）。"""
    resp = client.post("/system/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, f"{username} 登录失败: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}


class TestProductLibrary:
    """产品库 CRUD、判重与 C 端检索。"""

    def _create_product(self, client: TestClient, headers: dict[str, str], name: str, spec: str, manufacturer: str):
        return client.post(
            "/market/products/create",
            headers=headers,
            json={"name": name, "spec": spec, "manufacturer": manufacturer},
        )

    def test_ops_created_product_is_searchable(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """运营录入的产品直接生效（approved），C 端按名称可检索到。"""
        resp = self._create_product(test_client, auth_headers, "一心坦", "100mg*28片", "上海现代制药")
        assert resp.json()["success"] is True, resp.text
        created = resp.json()["data"]
        assert created["audit_status"] == "approved"
        assert created["source"] == "admin"

        search = test_client.get("/market/mini/products/search", headers=auth_headers, params={"keyword": "一心坦"})
        assert search.status_code == 200, search.text
        names = [item["display_name"] for item in search.json()["data"]]
        assert "一心坦 / 100mg*28片 / 上海现代制药" in names

    def test_duplicate_triple_rejected(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """名称+规格+生产企业全等即同一产品，重复录入被拒绝且给出可读文案。"""
        first = self._create_product(test_client, auth_headers, "重复测试药", "10mg", "重复测试厂")
        assert first.json()["success"] is True
        second = self._create_product(test_client, auth_headers, "重复测试药", "10mg", "重复测试厂")
        assert second.json()["success"] is False
        assert "产品已存在" in second.json()["msg"]

    def test_same_name_different_manufacturer_is_distinct(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """同名不同厂商是两条记录（C 端此时应弹窗选择）。"""
        a = self._create_product(test_client, auth_headers, "同名不同厂", "5mg", "甲厂")
        b = self._create_product(test_client, auth_headers, "同名不同厂", "5mg", "乙厂")
        assert a.json()["success"] is True and b.json()["success"] is True

        search = test_client.get("/market/mini/products/search", headers=auth_headers, params={"keyword": "同名不同厂"})
        items = search.json()["data"]
        assert len(items) == 2
        assert {item["manufacturer"] for item in items} == {"甲厂", "乙厂"}

    def test_update_and_delete_product(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """运营可改规格、可删除（软删除后不再出现在列表）。"""
        created = self._create_product(test_client, auth_headers, "待修改药", "旧规格", "旧厂").json()["data"]
        updated = test_client.put(
            f"/market/products/update/{created['id']}",
            headers=auth_headers,
            json={"spec": "新规格"},
        )
        assert updated.json()["data"]["spec"] == "新规格"

        deleted = test_client.request("DELETE", "/market/products/delete", headers=auth_headers, json=[created["id"]])
        assert deleted.json()["success"] is True
        listed = test_client.get(
            "/market/products/list", headers=auth_headers, params={"page_no": 1, "page_size": 50, "name": "待修改药"}
        )
        assert listed.json()["data"]["items"] == []

    def test_requires_permission(self, test_client: TestClient) -> None:
        """未认证访问产品库列表被拒绝。"""
        assert test_client.get("/market/products/list").status_code == 401

    def test_reject_requires_comment(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """驳回必须填写审核意见（避免运营与提交人对不上原因）。"""
        created = self._create_product(test_client, auth_headers, "驳回校验药", "", "").json()["data"]
        resp = test_client.put(
            "/market/products/audit", headers=auth_headers, json={"ids": [created["id"]], "approved": False}
        )
        assert resp.status_code == 422, resp.text


class TestProductAutoIngest:
    """C 端提交成果时把库里没有的产品自动入库为待审，并按审核状态控制可见性。"""

    def _find_item_id(self, client: TestClient, headers: dict[str, str], code: str) -> int:
        resp = client.get("/market/items/list", headers=headers, params={"page_no": 1, "page_size": 100})
        items = resp.json()["data"]["items"]
        return next(item["id"] for item in items if item["code"] == code)

    def _claim_assignment(self, client: TestClient, ops_headers: dict[str, str], user_headers: dict[str, str]) -> int:
        """发布一个公开大厅任务并由 C 端用户接单，返回分派 id。"""
        suffix = uuid.uuid4().hex[:8]
        company_id = client.post(
            "/market/companies/create", headers=ops_headers, json={"name": f"产品库测试公司{suffix}"}
        ).json()["data"]["id"]
        item_id = self._find_item_id(client, ops_headers, "ITEM-0011")  # 民营医疗管理-配送协调
        project_id = client.post(
            "/market/projects/create",
            headers=ops_headers,
            json={
                "name": f"产品库测试药品{suffix}",
                "company_id": company_id,
                "period": "2026-12-31",
                "item_ids": [item_id],
            },
        ).json()["data"]["id"]
        assert client.post(f"/market/projects/publish/{project_id}", headers=ops_headers).json()["success"] is True

        # 直接从运营端按项目取刚生成的任务，避免依赖大厅分页里能翻到它；项目发布只建 DRAFT 任务，
        # 还需单独发布任务（接单要求任务状态为 PUBLISHED）
        tasks = client.get(
            "/market/tasks/list", headers=ops_headers, params={"page_no": 1, "page_size": 10, "project_id": project_id}
        ).json()["data"]["items"]
        task = tasks[0]
        published = client.post(f"/market/tasks/publish/{task['id']}", headers=ops_headers)
        assert published.json()["success"] is True, published.text
        claim = client.post(f"/market/mini/tasks/{task['id']}/claim", headers=user_headers)
        assert claim.json()["success"] is True, claim.text
        return claim.json()["data"]["id"]

    def _submit(self, client: TestClient, headers: dict[str, str], assignment_id: int, product: tuple[str, str, str]):
        name, spec, manufacturer = product
        form_data: dict[str, Any] = {
            "execution_info": {
                "region": "重庆市渝中区",
                "hospital_name": "产品库测试医院",
                "executor": "测试执行人",
                "exec_date": "2026-11-01",
            },
            "delivery_coordination": {
                "delivery_coordination": [
                    {"product_name": name, "product_spec": spec, "manufacturer": manufacturer, "qty": 10},
                ],
                "exception_note": "无",
            },
            "management_verification": {"door_photo": "/static/upload/test.png"},
        }
        return client.post(
            "/market/mini/submissions",
            headers=headers,
            json={"assignment_id": assignment_id, "period": "2026-11", "form_data": form_data},
        )

    def test_pending_product_visible_only_to_submitter(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """提交的新产品自动入库为待审：提交人自己搜得到，其他用户搜不到；审核通过后所有人可见。"""
        user_headers = _login(test_client, "user", "123456")
        assignment_id = self._claim_assignment(test_client, auth_headers, user_headers)

        product_name = "自动入库测试药"
        submitted = self._submit(test_client, user_headers, assignment_id, (product_name, "50mg", "自动入库测试厂"))
        assert submitted.json()["success"] is True, submitted.text

        # 提交人自己可见（pending + submitter 匹配）
        own = test_client.get("/market/mini/products/search", headers=user_headers, params={"keyword": product_name})
        assert [item["name"] for item in own.json()["data"]] == [product_name]

        # 其他用户（运营 admin）在审核前搜不到
        others = test_client.get("/market/mini/products/search", headers=auth_headers, params={"keyword": product_name})
        assert others.json()["data"] == []

        # 运营端能看到这条待审记录
        pending = test_client.get(
            "/market/products/list",
            headers=auth_headers,
            params={"page_no": 1, "page_size": 50, "name": product_name, "audit_status": "pending"},
        )
        rows = pending.json()["data"]["items"]
        assert len(rows) == 1
        product_id = rows[0]["id"]

        # 审核通过 → 所有人可见
        approved = test_client.put(
            "/market/products/audit", headers=auth_headers, json={"ids": [product_id], "approved": True}
        )
        assert approved.json()["data"] == 1
        after = test_client.get("/market/mini/products/search", headers=auth_headers, params={"keyword": product_name})
        assert [item["name"] for item in after.json()["data"]] == [product_name]

    def test_rejected_product_disappears_from_search(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """被驳回的产品不再出现在提交人的检索结果里。"""
        user_headers = _login(test_client, "user", "123456")
        assignment_id = self._claim_assignment(test_client, auth_headers, user_headers)

        product_name = "驳回测试药"
        assert self._submit(test_client, user_headers, assignment_id, (product_name, "1g", "驳回测试厂")).json()["success"]

        rows = test_client.get(
            "/market/products/list",
            headers=auth_headers,
            params={"page_no": 1, "page_size": 50, "name": product_name},
        ).json()["data"]["items"]
        assert len(rows) == 1

        rejected = test_client.put(
            "/market/products/audit",
            headers=auth_headers,
            json={"ids": [rows[0]["id"]], "approved": False, "review_comment": "名称不规范"},
        )
        assert rejected.json()["data"] == 1

        after = test_client.get("/market/mini/products/search", headers=user_headers, params={"keyword": product_name})
        assert after.json()["data"] == []

    def test_resubmit_does_not_duplicate_pending(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """同一产品重复提交只入库一次（判重键已存在则跳过）。"""
        user_headers = _login(test_client, "user", "123456")
        assignment_id = self._claim_assignment(test_client, auth_headers, user_headers)

        product = ("重复提交测试药", "2g", "重复提交测试厂")
        assert self._submit(test_client, user_headers, assignment_id, product).json()["success"]
        assert self._submit(test_client, user_headers, assignment_id, product).json()["success"]

        rows = test_client.get(
            "/market/products/list",
            headers=auth_headers,
            params={"page_no": 1, "page_size": 50, "name": product[0]},
        ).json()["data"]["items"]
        assert len(rows) == 1

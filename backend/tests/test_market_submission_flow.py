"""market 域集成测试：成果提交 → 审核 → 归集结算的分派/成果状态机。

锁定三条 2026-11 定下的规则：
1. C 端提交成果落库即 ``PENDING``（待审核），不再有 DRAFT 中间态；
2. 周期任务（``submit_rule.cadence=monthly``）同一分派同一月只允许一份成果，并发由分派行锁兜底；
3. 分派状态机 PENDING→ACCEPTED→SUBMITTED→REVIEWED→SETTLED 每一步都有写入路径
   （``SUBMITTING`` 已删除，从未被写入过）。
"""

import uuid
from typing import Any

from fastapi.testclient import TestClient


def _login(client: TestClient, username: str, password: str) -> dict[str, str]:
    resp = client.post("/system/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}


def _form_data(org_name: str) -> dict[str, Any]:
    return {
        "execution_info": {
            "region": "重庆市渝中区",
            "hospital_name": org_name,
            "executor": "测试执行人",
            "exec_date": "2026-11-02",
        },
        "delivery_coordination": {
            "delivery_coordination": [
                {"product_name": "状态机测试药", "product_spec": "10mg", "manufacturer": "状态机测试厂", "qty": 5},
            ],
            "exception_note": "无",
        },
        "management_verification": {"door_photo": "/static/upload/test.png"},
    }


class TestSubmissionStateMachine:
    """成果提交、审核与结算对分派状态的回写。"""

    def _prepare_claimed_task(self, client: TestClient, ops: dict[str, str], user: dict[str, str]) -> tuple[int, int]:
        """建公司/项目、发布项目与任务，C 端用户接单，返回 (task_id, assignment_id)。"""
        suffix = uuid.uuid4().hex[:8]
        company_id = client.post(
            "/market/companies/create", headers=ops, json={"name": f"状态机测试公司{suffix}"}
        ).json()["data"]["id"]
        items = client.get("/market/items/list", headers=ops, params={"page_no": 1, "page_size": 100}).json()["data"]["items"]
        item = next(i for i in items if i["code"] == "ITEM-0011")
        project_id = client.post(
            "/market/projects/create",
            headers=ops,
            json={
                "name": f"状态机测试项目{suffix}",
                "company_id": company_id,
                "period": "2026-12-31",
                "item_ids": [item["id"]],
            },
        ).json()["data"]["id"]
        assert client.post(f"/market/projects/publish/{project_id}", headers=ops).json()["success"]

        task = client.get(
            "/market/tasks/list", headers=ops, params={"page_no": 1, "page_size": 10, "project_id": project_id}
        ).json()["data"]["items"][0]
        assert client.post(f"/market/tasks/publish/{task['id']}", headers=ops).json()["success"]

        claim = client.post(f"/market/mini/tasks/{task['id']}/claim", headers=user)
        assert claim.json()["success"] is True, claim.text
        return task["id"], claim.json()["data"]["id"]

    def _assignment_status(self, client: TestClient, ops: dict[str, str], assignment_id: int) -> str:
        return client.get(f"/market/assignments/detail/{assignment_id}", headers=ops).json()["data"]["status"]

    def _submit(self, client: TestClient, user: dict[str, str], assignment_id: int, period: str = "2026-11"):
        return client.post(
            "/market/mini/submissions",
            headers=user,
            json={"assignment_id": assignment_id, "period": period, "form_data": _form_data("状态机测试医院")},
        )

    def test_submit_writes_pending_and_assignment_submitted(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """提交成果：成果落库即 PENDING，分派推进到 SUBMITTED（不再是 DRAFT）。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = self._prepare_claimed_task(test_client, auth_headers, user)
        assert self._assignment_status(test_client, auth_headers, assignment_id) == "ACCEPTED"

        submitted = self._submit(test_client, user, assignment_id)
        assert submitted.json()["success"] is True, submitted.text
        assert submitted.json()["data"]["status"] == "PENDING"
        assert self._assignment_status(test_client, auth_headers, assignment_id) == "SUBMITTED"

    def test_duplicate_submission_same_period_rejected(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """周期任务同月重复提交被拒（行锁 + 同月查重）。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = self._prepare_claimed_task(test_client, auth_headers, user)

        assert self._submit(test_client, user, assignment_id).json()["success"] is True
        again = self._submit(test_client, user, assignment_id)
        assert again.json()["success"] is False
        assert "本月已提交" in again.json()["msg"]

        # 换个月份可以正常提交
        assert self._submit(test_client, user, assignment_id, period="2026-12").json()["success"] is True

    def test_review_approve_writes_reviewed_and_settle_writes_settled(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """审核通过 → 分派 REVIEWED；归集结算 → 分派 SETTLED。"""
        user = _login(test_client, "user", "123456")
        task_id, assignment_id = self._prepare_claimed_task(test_client, auth_headers, user)
        submitted = self._submit(test_client, user, assignment_id).json()["data"]

        reviewed = test_client.post(
            f"/market/submissions/review/{submitted['id']}",
            headers=auth_headers,
            json={"approved": True, "review_comment": "通过"},
        )
        assert reviewed.json()["success"] is True, reviewed.text
        assert reviewed.json()["data"]["status"] == "APPROVED"
        assert self._assignment_status(test_client, auth_headers, assignment_id) == "REVIEWED"

        # 运营判定任务完成 → 才能归集结算
        done = test_client.post(
            f"/market/tasks/status/{task_id}", headers=auth_headers, json={"status": "COMPLETED"}
        )
        assert done.json()["success"] is True, done.text

        settled = test_client.post(
            "/market/settlements/settle", headers=auth_headers, json={"task_id": task_id, "period": "2026-11"}
        )
        assert settled.json()["success"] is True, settled.text
        assert self._assignment_status(test_client, auth_headers, assignment_id) == "SETTLED"

    def test_dashboard_pending_counts_submitted(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """dashboard「待审核成果」不再是恒 0：提交后计数增加。"""
        before = test_client.get("/market/dashboard/overview", headers=auth_headers).json()["data"]["submission"]["pending"]

        user = _login(test_client, "user", "123456")
        _, assignment_id = self._prepare_claimed_task(test_client, auth_headers, user)
        assert self._submit(test_client, user, assignment_id).json()["success"] is True

        after = test_client.get("/market/dashboard/overview", headers=auth_headers).json()["data"]["submission"]["pending"]
        assert after == before + 1

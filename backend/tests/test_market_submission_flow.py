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
from sqlalchemy import text

from app.core.database import engine


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


def _prepare_claimed_task(
    client: TestClient, ops: dict[str, str], user: dict[str, str], item_code: str = "ITEM-0011"
) -> tuple[int, int]:
    """建公司/项目、发布项目与任务，C 端用户接单，返回 (task_id, assignment_id)。

    ``item_code`` 决定三级任务（默认 ITEM-0011 等级医院管理·配送协调，采集对象=机构）。
    """
    suffix = uuid.uuid4().hex[:8]
    company_id = client.post(
        "/market/companies/create", headers=ops, json={"name": f"状态机测试公司{suffix}"}
    ).json()["data"]["id"]
    items = client.get("/market/items/list", headers=ops, params={"page_no": 1, "page_size": 100}).json()["data"]["items"]
    item = next(i for i in items if i["code"] == item_code)
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


def _assignment_status(client: TestClient, ops: dict[str, str], assignment_id: int) -> str:
    return client.get(f"/market/assignments/detail/{assignment_id}", headers=ops).json()["data"]["status"]


def _submit(
    client: TestClient,
    user: dict[str, str],
    assignment_id: int,
    period: str = "2026-11",
    form_data: dict[str, Any] | None = None,
):
    return client.post(
        "/market/mini/submissions",
        headers=user,
        json={"assignment_id": assignment_id, "period": period, "form_data": form_data or _form_data("状态机测试医院")},
    )


class TestSubmissionStateMachine:
    """成果提交、审核与结算对分派状态的回写。"""

    def test_submit_writes_pending_and_assignment_submitted(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """提交成果：成果落库即 PENDING，分派推进到 SUBMITTED（不再是 DRAFT）。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        assert _assignment_status(test_client, auth_headers, assignment_id) == "ACCEPTED"

        submitted = _submit(test_client, user, assignment_id)
        assert submitted.json()["success"] is True, submitted.text
        assert submitted.json()["data"]["status"] == "PENDING"
        assert _assignment_status(test_client, auth_headers, assignment_id) == "SUBMITTED"

    def test_duplicate_submission_same_period_rejected(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """周期任务同月重复提交被拒（行锁 + 同月查重）。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)

        assert _submit(test_client, user, assignment_id).json()["success"] is True
        again = _submit(test_client, user, assignment_id)
        assert again.json()["success"] is False
        assert "本月已提交" in again.json()["msg"]

        # 换个月份可以正常提交
        assert _submit(test_client, user, assignment_id, period="2026-12").json()["success"] is True

    def test_review_approve_writes_reviewed_and_settle_writes_settled(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """审核通过 → 分派 REVIEWED；归集结算 → 分派 SETTLED。"""
        user = _login(test_client, "user", "123456")
        task_id, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        submitted = _submit(test_client, user, assignment_id).json()["data"]

        reviewed = test_client.post(
            f"/market/submissions/review/{submitted['id']}",
            headers=auth_headers,
            json={"approved": True, "review_comment": "通过"},
        )
        assert reviewed.json()["success"] is True, reviewed.text
        assert reviewed.json()["data"]["status"] == "APPROVED"
        assert _assignment_status(test_client, auth_headers, assignment_id) == "REVIEWED"

        # 运营判定任务完成 → 才能归集结算
        done = test_client.post(
            f"/market/tasks/status/{task_id}", headers=auth_headers, json={"status": "COMPLETED"}
        )
        assert done.json()["success"] is True, done.text

        settled = test_client.post(
            "/market/settlements/settle", headers=auth_headers, json={"task_id": task_id, "period": "2026-11"}
        )
        assert settled.json()["success"] is True, settled.text
        assert _assignment_status(test_client, auth_headers, assignment_id) == "SETTLED"

    def test_dashboard_pending_counts_submitted(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """dashboard「待审核成果」不再是恒 0：提交后计数增加。"""
        before = test_client.get("/market/dashboard/overview", headers=auth_headers).json()["data"]["submission"]["pending"]

        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        assert _submit(test_client, user, assignment_id).json()["success"] is True

        after = test_client.get("/market/dashboard/overview", headers=auth_headers).json()["data"]["submission"]["pending"]
        assert after == before + 1


class TestSubmissionReviewPayload:
    """审核页要看到的东西：摘要字段（区域/对象名称/档案号）与中文字段名映射源。"""

    def test_submit_fills_summary_fields(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """C 端只传 form_data，成果表的区域/对象名称/档案号由后端推导并落库。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)

        submitted = _submit(test_client, user, assignment_id).json()["data"]
        assert submitted["region"] == "重庆市渝中区"
        assert submitted["subject_name"] == "状态机测试医院"
        assert submitted["archive_no"].startswith("ARC-")

        # 同一成果每次提交档案号递增、互不重复
        other = _prepare_claimed_task(test_client, auth_headers, user)[1]
        other_submitted = _submit(test_client, user, other, period="2026-12").json()["data"]
        assert other_submitted["archive_no"] != submitted["archive_no"]

    def test_detail_carries_institution_and_form_schema(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """详情接口回填机构摘要与 form_schema——审核页靠它把英文字段名渲染成中文标签。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        submitted = _submit(test_client, user, assignment_id).json()["data"]

        detail = test_client.get(f"/market/submissions/detail/{submitted['id']}", headers=auth_headers).json()["data"]
        assert detail["institution"]["name"] == "状态机测试医院"

        sections = {section["code"]: section for section in detail["form_schema"]}
        assert "execution_info" in sections
        execution = sections["execution_info"]
        assert execution["name"] == "执行信息"
        # form_data 的每个键都要能在 schema 里找到中文标签，否则审核员看到的就是英文
        for field_name in detail["form_data"]["execution_info"]:
            assert execution["fields"][field_name]["label"], f"{field_name} 缺中文标签"
        assert execution["fields"]["hospital_name"]["label"] == "医院名称"

    def test_detail_backfills_legacy_row(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """历史成果（三列从未写入）打开详情时自愈回填，并保证列表也能看到。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        submitted = _submit(test_client, user, assignment_id).json()["data"]

        # 模拟存量数据：绕过接口把摘要三列清空（历史提交只落 form_data）
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE market_submission SET region = NULL, subject_name = NULL, archive_no = NULL WHERE id = :id"),
                {"id": submitted["id"]},
            )

        detail = test_client.get(f"/market/submissions/detail/{submitted['id']}", headers=auth_headers).json()["data"]
        assert detail["region"] == "重庆市渝中区"
        assert detail["subject_name"] == "状态机测试医院"
        assert detail["archive_no"].startswith("ARC-")

        listed = test_client.get(
            "/market/submissions/list",
            headers=auth_headers,
            params={"page_no": 1, "page_size": 10, "assignment_id": assignment_id},
        ).json()["data"]["items"]
        row = next(item for item in listed if item["id"] == submitted["id"])
        assert row["archive_no"] == detail["archive_no"]
        assert row["institution"]["name"] == "状态机测试医院"

    def test_list_carries_task_context_and_filters_by_hierarchy(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """列表每一行都带项目/分类/模板/任务上下文，并支持按这三层筛选。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        submitted = _submit(test_client, user, assignment_id).json()["data"]

        context = submitted["task"]
        for field in ("project_name", "category_name", "template_name", "item_name", "task_no"):
            assert context[field], f"任务上下文缺 {field}"

        def _list_ids(**params: Any) -> list[int]:
            rows = test_client.get(
                "/market/submissions/list", headers=auth_headers, params={"page_no": 1, "page_size": 50, **params}
            ).json()["data"]["items"]
            return [row["id"] for row in rows]

        # 项目 / 模板 / 任务 三层各自都能命中本行
        for key in ("project_id", "template_id", "item_id"):
            assert submitted["id"] in _list_ids(**{key: context[key]}), f"{key} 过滤没命中"

        # 互斥组合恒为空（AND 生效，不是 OR）
        assert _list_ids(project_id=context["project_id"], item_id=context["item_id"] + 100000) == []
        # 档案号改模糊匹配
        assert submitted["id"] in _list_ids(archive_no=submitted["archive_no"][:6])

    def test_staff_submission_takes_respondent_as_object_name(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """医务人员/患者调研类采集表用 respondent 存受访对象，对象名称要取到它。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user, item_code="ITEM-0030")
        form_data = {
            "basic_profile": {"store_name": "状态机测试门店", "respondent": "受访同学", "executor": "普通用户", "exec_date": "2026-11-02"},
            "patient": {"willingness": "愿意", "reason": "", "remark": ""},
        }

        submitted = _submit(test_client, user, assignment_id, form_data=form_data).json()["data"]
        assert submitted["subject_type"] == "staff"
        assert submitted["subject_name"] == "受访同学"
        assert submitted["institution_id"] is None

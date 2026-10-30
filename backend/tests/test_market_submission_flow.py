"""market 域集成测试：成果提交 → 审核 → 归集结算的分派/成果状态机。

锁定三条 2026-11 定下的规则：
1. C 端提交成果落库即 ``PENDING``（待审核），不再有 DRAFT 中间态；
2. 周期任务（``submit_rule.cadence=monthly``）同一分派同一月只允许一份成果，并发由分派行锁兜底；
3. 分派状态机 PENDING→ACCEPTED→SUBMITTED→REVIEWED→SETTLED 每一步都有写入路径
   （``SUBMITTING`` 已删除，从未被写入过）。
"""

import uuid
from decimal import Decimal
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


def _assignment_user_id(client: TestClient, ops: dict[str, str], assignment_id: int) -> int:
    return client.get(f"/market/assignments/detail/{assignment_id}", headers=ops).json()["data"]["user_id"]


def _review(client: TestClient, ops: dict[str, str], submission_id: int, approved: bool = True) -> dict[str, Any]:
    resp = client.post(
        f"/market/submissions/review/{submission_id}",
        headers=ops,
        json={"approved": approved, "review_comment": "通过" if approved else "驳回"},
    )
    assert resp.json()["success"] is True, resp.text
    return resp.json()["data"]


def _set_payout_limit(client: TestClient, ops: dict[str, str], user_id: int, period: str, limit: str) -> None:
    resp = client.post(
        "/market/payout/create",
        headers=ops,
        json={"user_id": user_id, "period": period, "payout_limit": limit},
    )
    assert resp.json()["success"] is True, resp.text


def _payout_result(client: TestClient, ops: dict[str, str], user_id: int, period: str) -> dict[str, Any]:
    resp = client.get("/market/payout/results", headers=ops, params={"page_no": 1, "page_size": 10, "user_id": user_id, "period": period})
    assert resp.json()["success"] is True, resp.text
    items = resp.json()["data"]["items"]
    assert len(items) == 1, items
    return items[0]


def _reset_payout_state(user_id: int) -> None:
    """清空该用户的结算 / 津贴 / 额度数据。

    测试库是 session 级共享（conftest 只建一次），早先的测试会留下同用户同月份的结算单与
    津贴账本；发放口径又依赖「该用户该期的全部结算单 + 上期账本」，不清就会互相污染。
    """
    with engine.begin() as conn:
        conn.execute(
            text(
                "DELETE FROM market_settlement_item WHERE settlement_id IN "
                "(SELECT id FROM market_settlement WHERE user_id = :u)"
            ),
            {"u": user_id},
        )
        conn.execute(text("DELETE FROM market_settlement WHERE user_id = :u"), {"u": user_id})
        conn.execute(text("DELETE FROM market_allowance_detail WHERE user_id = :u"), {"u": user_id})
        conn.execute(text("DELETE FROM market_allowance WHERE user_id = :u"), {"u": user_id})
        conn.execute(text("DELETE FROM market_payout_config WHERE user_id = :u"), {"u": user_id})


def _settlements(client: TestClient, ops: dict[str, str], user_id: int, period: str) -> list[dict[str, Any]]:
    resp = client.get(
        "/market/settlements/list",
        headers=ops,
        params={"page_no": 1, "page_size": 50, "user_id": user_id, "period": period},
    )
    assert resp.json()["success"] is True, resp.text
    return resp.json()["data"]["items"]


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

    def test_review_approve_auto_settles_and_writes_settled(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """审核通过即刻自动归集：分派直接 SETTLED，出参带回本次发放结果。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        _reset_payout_state(_assignment_user_id(test_client, auth_headers, assignment_id))
        submitted = _submit(test_client, user, assignment_id).json()["data"]

        data = _review(test_client, auth_headers, submitted["id"])
        assert data["submission"]["status"] == "APPROVED"
        assert data["warning"] is None

        notice = data["settlement"]
        assert notice is not None
        assert notice["period"] == "2026-11"
        assert Decimal(notice["payable"]) > 0
        assert Decimal(notice["paid"]) == Decimal(notice["payable"])
        assert Decimal(notice["rollover"]) == 0
        # 审核即归集，分派状态机直接走到最后一环，不需要运营再点「归集结算」
        assert _assignment_status(test_client, auth_headers, assignment_id) == "SETTLED"

    def test_manual_settle_still_requires_completed_task(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """自动归集不看任务状态，但运营手动「归集结算」仍要求任务已完成。"""
        user = _login(test_client, "user", "123456")
        task_id, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        user_id = _assignment_user_id(test_client, auth_headers, assignment_id)
        _reset_payout_state(user_id)
        submitted = _submit(test_client, user, assignment_id).json()["data"]
        _review(test_client, auth_headers, submitted["id"])

        denied = test_client.post(
            "/market/settlements/settle", headers=auth_headers, json={"task_id": task_id, "period": "2026-11"}
        )
        assert denied.json()["success"] is False
        assert "已完成" in denied.json()["msg"]

        done = test_client.post(f"/market/tasks/status/{task_id}", headers=auth_headers, json={"status": "COMPLETED"})
        assert done.json()["success"] is True, done.text
        # 任务完成后再手动重跑一次：幂等，不新增结算单、金额不变
        before = _settlements(test_client, auth_headers, user_id, "2026-11")
        rerun = test_client.post(
            "/market/settlements/settle", headers=auth_headers, json={"task_id": task_id, "period": "2026-11"}
        )
        assert rerun.json()["success"] is True, rerun.text
        after = _settlements(test_client, auth_headers, user_id, "2026-11")
        assert len(after) == len(before) == 1
        assert after[0]["payable_amount"] == before[0]["payable_amount"]

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


class TestPayoutAlgorithm:
    """发放封顶 + 津贴滚存（按「用户 × 周期」算，不是按结算单）。

    口径：待发 = 当月应发合计 + 期初津贴；实发 = min(待发, 额度)；期末津贴 = 待发 - 实发。
    """

    def test_payable_under_limit_pays_in_full(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """应发不超额度：实发 = 应发，无滚存。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        user_id = _assignment_user_id(test_client, auth_headers, assignment_id)
        _reset_payout_state(user_id)
        _set_payout_limit(test_client, auth_headers, user_id, "2026-11", "20000")

        submitted = _submit(test_client, user, assignment_id).json()["data"]
        notice = _review(test_client, auth_headers, submitted["id"])["settlement"]

        assert Decimal(notice["payable"]) == Decimal(notice["paid"])
        assert Decimal(notice["rollover"]) == 0
        assert Decimal(notice["limit"]) == Decimal("20000")

        result = _payout_result(test_client, auth_headers, user_id, "2026-11")
        assert Decimal(result["payable"]) == Decimal(notice["payable"])
        assert Decimal(result["paid"]) == Decimal(notice["paid"])

    def test_limit_caps_paid_and_rolls_rest_into_allowance(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """应发超额度：实发被截到额度，差额进个人津贴，结算单实发合计等于实发。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        user_id = _assignment_user_id(test_client, auth_headers, assignment_id)
        _reset_payout_state(user_id)
        _set_payout_limit(test_client, auth_headers, user_id, "2026-11", "100")

        submitted = _submit(test_client, user, assignment_id).json()["data"]
        notice = _review(test_client, auth_headers, submitted["id"])["settlement"]

        payable = Decimal(notice["payable"])
        assert payable > Decimal("100")
        assert Decimal(notice["paid"]) == Decimal("100")
        assert Decimal(notice["rollover"]) == payable - Decimal("100")

        rows = _settlements(test_client, auth_headers, user_id, "2026-11")
        assert len(rows) == 1
        assert Decimal(rows[0]["paid_amount"]) == Decimal("100")
        assert rows[0]["pay_status"] == "SCHEDULED"

        allowance = test_client.get(
            "/market/payout/allowance", headers=auth_headers, params={"page_no": 1, "page_size": 50}
        ).json()["data"]["items"]
        balance = next(Decimal(row["balance"]) for row in allowance if row["user_id"] == user_id)
        assert balance == payable - Decimal("100")

    def test_two_tasks_same_month_share_one_limit(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """封顶按「用户 × 月」而不是按任务：两张结算单合计应发超额度时按 id 顺序贪心分摊。"""
        user = _login(test_client, "user", "123456")
        _, first_assignment = _prepare_claimed_task(test_client, auth_headers, user)
        user_id = _assignment_user_id(test_client, auth_headers, first_assignment)
        _reset_payout_state(user_id)
        _, second_assignment = _prepare_claimed_task(test_client, auth_headers, user)

        first = _submit(test_client, user, first_assignment).json()["data"]
        second = _submit(test_client, user, second_assignment).json()["data"]
        _review(test_client, auth_headers, first["id"])

        cap = Decimal("2000")
        _set_payout_limit(test_client, auth_headers, user_id, "2026-11", "2000")
        notice = _review(test_client, auth_headers, second["id"])["settlement"]

        payable = Decimal(notice["payable"]) * 2  # 两个任务同价同月
        assert payable > cap
        assert Decimal(notice["paid"]) == cap
        assert Decimal(notice["rollover"]) == payable - cap

        rows = sorted(_settlements(test_client, auth_headers, user_id, "2026-11"), key=lambda row: row["id"])
        assert len(rows) == 2
        # 贪心分摊：Σ paid_amount == 实发，且额度耗尽后创建的单显示 0 而不是乱填
        assert sum(Decimal(row["paid_amount"]) for row in rows) == cap
        assert Decimal(rows[0]["paid_amount"]) == min(Decimal(rows[0]["payable_amount"]), cap)

        result = _payout_result(test_client, auth_headers, user_id, "2026-11")
        assert Decimal(result["payable"]) == payable
        assert Decimal(result["paid"]) == cap
        assert Decimal(result["rollover"]) == payable - cap

    def test_rollover_counts_into_next_period_pending(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """上期滚存参与下期待发：下期实发 = min(下期应发 + 上期津贴, 额度)。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        user_id = _assignment_user_id(test_client, auth_headers, assignment_id)
        _reset_payout_state(user_id)

        _set_payout_limit(test_client, auth_headers, user_id, "2026-11", "1")
        november = _submit(test_client, user, assignment_id, period="2026-11").json()["data"]
        prev_rollover = Decimal(_review(test_client, auth_headers, november["id"])["settlement"]["rollover"])
        assert prev_rollover > 0

        _set_payout_limit(test_client, auth_headers, user_id, "2026-12", "20000")
        december = _submit(test_client, user, assignment_id, period="2026-12").json()["data"]
        notice = _review(test_client, auth_headers, december["id"])["settlement"]

        payable = Decimal(notice["payable"])
        assert Decimal(notice["paid"]) == payable + prev_rollover, "下期实发必须把上期滚存算进待发"
        assert Decimal(notice["rollover"]) == 0

    def test_repeated_settle_is_idempotent(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """重复归集不新增结算单、不叠加金额（重算而非累加）。"""
        user = _login(test_client, "user", "123456")
        task_id, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        user_id = _assignment_user_id(test_client, auth_headers, assignment_id)
        _reset_payout_state(user_id)
        _set_payout_limit(test_client, auth_headers, user_id, "2026-11", "100")

        submitted = _submit(test_client, user, assignment_id).json()["data"]
        first = _review(test_client, auth_headers, submitted["id"])["settlement"]

        assert test_client.post(f"/market/tasks/status/{task_id}", headers=auth_headers, json={"status": "COMPLETED"}).json()["success"]
        for _ in range(2):
            assert test_client.post(
                "/market/settlements/settle", headers=auth_headers, json={"task_id": task_id, "period": "2026-11"}
            ).json()["success"]

        rows = _settlements(test_client, auth_headers, user_id, "2026-11")
        assert len(rows) == 1
        assert Decimal(rows[0]["payable_amount"]) == Decimal(first["payable"])
        assert Decimal(rows[0]["paid_amount"]) == Decimal("100")

    def test_settle_failure_does_not_rollback_review(
        self, test_client: TestClient, auth_headers: dict[str, str], monkeypatch: Any
    ) -> None:
        """归集失败不影响已生效的审核：成果仍 APPROVED，原因通过 warning 回传。"""
        from app.modules.market.payout.service import SettlementService

        async def _boom(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("模板单价缺失")

        monkeypatch.setattr(SettlementService, "settle", _boom)

        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        submitted = _submit(test_client, user, assignment_id).json()["data"]

        data = _review(test_client, auth_headers, submitted["id"])
        assert data["submission"]["status"] == "APPROVED"
        assert data["settlement"] is None
        assert "归集失败" in data["warning"]
        assert _assignment_status(test_client, auth_headers, assignment_id) == "REVIEWED"

    def test_reject_produces_no_settlement(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """驳回不触发归集，也不生成结算单。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        user_id = _assignment_user_id(test_client, auth_headers, assignment_id)
        _reset_payout_state(user_id)
        submitted = _submit(test_client, user, assignment_id).json()["data"]

        data = _review(test_client, auth_headers, submitted["id"], approved=False)
        assert data["submission"]["status"] == "REJECTED"
        assert data["settlement"] is None
        assert _settlements(test_client, auth_headers, user_id, "2026-11") == []
        assert _assignment_status(test_client, auth_headers, assignment_id) == "SUBMITTED"


class TestPayoutUserBrief:
    """结算单与发放结果必须自带 C 端用户摘要：只靠 user_id 前端认不出人。"""

    def test_settlement_and_result_carry_user_brief(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        user_id = _assignment_user_id(test_client, auth_headers, assignment_id)
        _reset_payout_state(user_id)

        submitted = _submit(test_client, user, assignment_id).json()["data"]
        _review(test_client, auth_headers, submitted["id"])

        rows = _settlements(test_client, auth_headers, user_id, "2026-11")
        assert rows, "归集后应有结算单"
        brief = rows[0]["user"]
        assert brief["id"] == user_id
        assert brief["name"] == "普通用户"
        assert brief["username"] == "user"
        assert brief["mobile"], "手机号是运营真正的识别手段，不能为空"

        result = _payout_result(test_client, auth_headers, user_id, "2026-11")
        assert result["user"]["id"] == user_id
        assert result["user"]["mobile"] == brief["mobile"]

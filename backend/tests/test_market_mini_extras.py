"""C 端 mini 增量接口测试：待办角标、成果详情（本人）、收益卡应发。

复用 ``test_market_submission_flow`` 的建项目/接单/提交流程，保证与真实业务路径一致。
计数是「该用户全库」口径，同一 session 内多个用例共享数据库，所以断言用增量而不是绝对值。
"""

from typing import Any

from fastapi.testclient import TestClient

from tests.test_market_submission_flow import (
    _form_data,
    _login,
    _prepare_claimed_task,
    _review,
    _settlements,
    _submit,
)

PERIOD = "2026-11"


def _stats(client: TestClient, user: dict[str, str]) -> dict[str, Any]:
    resp = client.get("/market/mini/task-stats", headers=user)
    assert resp.json()["success"] is True, resp.text
    return resp.json()["data"]


def _user_id(client: TestClient, ops: dict[str, str], username: str = "user") -> int:
    resp = client.get("/system/user/list", headers=ops, params={"username": username})
    return resp.json()["data"]["items"][0]["id"]


class TestTaskStats:
    def test_counts_follow_assignment_and_rejection(
        self, test_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """接单 → 提交 → 驳回 三个阶段，角标计数跟着走。"""
        user = _login(test_client, "user", "123456")
        before = _stats(test_client, user)

        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        after_claim = _stats(test_client, user)
        assert after_claim["accepted"] == before["accepted"] + 1

        submitted = _submit(test_client, user, assignment_id)
        assert submitted.json()["success"] is True, submitted.text
        after_submit = _stats(test_client, user)
        assert after_submit["accepted"] == after_claim["accepted"] - 1
        assert after_submit["submitted"] == before["submitted"] + 1

        _review(test_client, auth_headers, submitted.json()["data"]["id"], approved=False)
        after_reject = _stats(test_client, user)
        assert after_reject["rejected_submissions"] == before["rejected_submissions"] + 1


class TestMySubmissionDetail:
    def test_owner_can_read_own_submission(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """驳回重提要回填原表单，所以 C 端必须能读到自己那份成果详情（含 form_data）。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        submitted = _submit(test_client, user, assignment_id, form_data=_form_data("详情读取医院"))
        sid = submitted.json()["data"]["id"]

        resp = test_client.get(f"/market/mini/submissions/{sid}", headers=user)
        assert resp.json()["success"] is True, resp.text
        data = resp.json()["data"]
        assert data["id"] == sid
        assert data["form_data"]["execution_info"]["hospital_name"] == "详情读取医院"

    def test_other_user_cannot_read(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """越权按「不存在」处理，不泄露他人成果是否存在。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        sid = _submit(test_client, user, assignment_id).json()["data"]["id"]

        # 运营账号（非成果提交人）读同一个 id 应失败
        resp = test_client.get(f"/market/mini/submissions/{sid}", headers=auth_headers)
        assert resp.json()["success"] is False


class TestPayoutPayable:
    def test_payout_exposes_period_payable(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """收益卡主数字 `payable` = 该周期结算单应发合计（无结算单时为 0，不能凭空造数）。"""
        user = _login(test_client, "user", "123456")
        uid = _user_id(test_client, auth_headers)
        settlements = _settlements(test_client, auth_headers, uid, PERIOD)
        expected = sum(float(item["payable_amount"]) for item in settlements)

        resp = test_client.get("/market/mini/payout", params={"period": PERIOD}, headers=user)
        assert resp.json()["success"] is True, resp.text
        assert resp.json()["data"]["payable"] == expected


class TestWeekProgress:
    def test_week_progress_shape_and_scope(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """本周进度：结构正确；截止日不在本周的任务不进「本周应完成」。"""
        user = _login(test_client, "user", "123456")
        before = test_client.get("/market/mini/week-progress", headers=user).json()["data"]
        assert set(before) == {"week_start", "week_end", "due", "done", "approved"}
        assert before["due"] >= before["done"] >= before["approved"]

        # 新建任务截止日是 2026-12-31（不在本周），不应改变本周口径
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        after = test_client.get("/market/mini/week-progress", headers=user).json()["data"]
        assert after["due"] == before["due"]
        assert after["done"] == before["done"]

        # 提交成果：只有当该任务确实落本周，done 才会变
        assert _submit(test_client, user, assignment_id).json()["success"] is True
        final = test_client.get("/market/mini/week-progress", headers=user).json()["data"]
        assert final["due"] == after["due"]
        assert final["done"] == after["done"]


class TestTaskStatsSubmissionBreakdown:
    def test_submission_counts_by_status(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """角标里同时给出成果维度计数：待审核 / 已通过 / 被驳回。"""
        user = _login(test_client, "user", "123456")
        before = _stats(test_client, user)
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        sid = _submit(test_client, user, assignment_id).json()["data"]["id"]

        after_submit = _stats(test_client, user)
        assert after_submit["submissions_pending"] == before["submissions_pending"] + 1

        _review(test_client, auth_headers, sid, approved=True)
        after_review = _stats(test_client, user)
        assert after_review["submissions_pending"] == before["submissions_pending"]
        assert after_review["submissions_approved"] == before["submissions_approved"] + 1


class TestAssignmentSubmissionStats:
    def test_assignment_carries_submission_progress(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        """「我的任务」列表每张卡都带成果进度：已提交 / 待审 / 通过 / 驳回。"""
        user = _login(test_client, "user", "123456")
        _, assignment_id = _prepare_claimed_task(test_client, auth_headers, user)
        sid = _submit(test_client, user, assignment_id).json()["data"]["id"]

        items = test_client.get(
            "/market/mini/assignments", params={"page_no": 1, "page_size": 50}, headers=user
        ).json()["data"]["items"]
        target = next(item for item in items if item["id"] == assignment_id)
        stats = target["submission_stats"]
        assert stats["total"] >= 1
        assert stats["pending"] >= 1
        assert stats["rejected"] == 0

        _review(test_client, auth_headers, sid, approved=False)
        items = test_client.get(
            "/market/mini/assignments", params={"page_no": 1, "page_size": 50}, headers=user
        ).json()["data"]["items"]
        target = next(item for item in items if item["id"] == assignment_id)
        assert target["submission_stats"]["rejected"] == 1
        assert target["submission_stats"]["pending"] == 0

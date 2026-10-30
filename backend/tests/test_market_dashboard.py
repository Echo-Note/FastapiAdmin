"""market 域集成测试：运营工作台（市场数据概览）统计。"""

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from app.modules.market.dashboard.schema import SubmissionTrendPointSchema
from app.modules.market.dashboard.service import build_trend
from app.modules.market.enums import SubmissionStatus


class TestDashboard:
    def test_overview_structure(self, test_client: TestClient, auth_headers: dict) -> None:
        """概览接口返回完整统计结构，且各指标为非负整数。"""
        resp = test_client.get("/market/dashboard/overview", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True

        data = body["data"]
        # 三大统计块
        assert set(data["task"].keys()) == {"total", "in_progress", "completed", "settled"}
        assert set(data["submission"].keys()) == {"total", "pending", "approved", "rejected"}
        assert set(data["settlement"].keys()) == {"total", "payable_amount"}
        # 基础数据计数
        for key in ("project_count", "company_count", "institution_count", "category_count", "template_count"):
            assert isinstance(data[key], int) and data[key] >= 0, f"{key} 应为非负整数"

    def test_overview_counts_seed(self, test_client: TestClient, auth_headers: dict) -> None:
        """空库播种后，一级分类 / 二级模板计数与种子数据一致。"""
        resp = test_client.get("/market/dashboard/overview", headers=auth_headers)
        data = resp.json()["data"]
        # 种子：一级分类 6 条、二级模板 18 条（任务目录三级化后，见 DEVELOPMENT-LOG「任务目录三级化」）
        assert data["category_count"] == 6
        assert data["template_count"] == 18
        # 未产生任何任务/成果/结算
        assert data["task"]["total"] == 0
        assert data["submission"]["total"] == 0
        assert data["settlement"]["total"] == 0

    def test_overview_requires_auth(self, test_client: TestClient) -> None:
        """未认证访问概览接口应被拒绝（401）。"""
        resp = test_client.get("/market/dashboard/overview")
        assert resp.status_code == 401

    def test_insights_structure(self, test_client: TestClient, auth_headers: dict) -> None:
        """明细接口固定返回 14 个趋势点（由旧到新）+ 队列列表。"""
        resp = test_client.get("/market/dashboard/insights", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True

        data = body["data"]
        trend = data["submission_trend"]
        assert len(trend) == 14
        assert set(trend[0].keys()) == {"date", "pending", "approved", "rejected"}
        # 日期升序且连续（ISO 字符串可直接比较）
        assert [point["date"] for point in trend] == sorted(point["date"] for point in trend)
        assert isinstance(data["pending_submissions"], list)

    def test_insights_counts_seed(self, test_client: TestClient, auth_headers: dict) -> None:
        """空库播种后没有任何成果：趋势全为 0、队列为空。"""
        resp = test_client.get("/market/dashboard/insights", headers=auth_headers)
        data = resp.json()["data"]
        assert all(
            point["pending"] == point["approved"] == point["rejected"] == 0
            for point in data["submission_trend"]
        )
        assert data["pending_submissions"] == []

    def test_insights_requires_auth(self, test_client: TestClient) -> None:
        """未认证访问明细接口应被拒绝（401）。"""
        resp = test_client.get("/market/dashboard/insights")
        assert resp.status_code == 401


class TestDashboardTrendBuckets:
    """趋势分桶：一天以北京时间 00:00 切分，草稿不计入。"""

    def test_buckets_by_local_day(self) -> None:
        d1, d2 = date(2026, 10, 17), date(2026, 10, 18)
        rows = [
            # 本地 10-16 23:59 → 窗口外，丢弃
            (datetime(2026, 10, 16, 15, 59, tzinfo=UTC), SubmissionStatus.PENDING.value),
            # 本地 10-17 00:00 与 23:59 → 都归到 d1
            (datetime(2026, 10, 16, 16, 0, tzinfo=UTC), SubmissionStatus.PENDING.value),
            (datetime(2026, 10, 17, 15, 59, tzinfo=UTC), SubmissionStatus.APPROVED.value),
            # 本地 10-18 00:00（naive 按 UTC 解释）→ d2
            (datetime(2026, 10, 17, 16, 0), SubmissionStatus.REJECTED.value),
            # 草稿不进入趋势三分类
            (datetime(2026, 10, 17, 16, 30, tzinfo=UTC), SubmissionStatus.DRAFT.value),
        ]

        trend = build_trend(rows, [d1, d2])

        assert trend == [
            SubmissionTrendPointSchema(date="2026-10-17", pending=1, approved=1, rejected=0),
            SubmissionTrendPointSchema(date="2026-10-18", pending=0, approved=0, rejected=1),
        ]

    def test_missing_days_are_zero_filled(self) -> None:
        days = [date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3)]
        trend = build_trend([], days)
        assert [point.date for point in trend] == ["2026-10-01", "2026-10-02", "2026-10-03"]
        assert all(point.pending == 0 and point.approved == 0 and point.rejected == 0 for point in trend)


class TestDashboardQueue:
    """待审核队列：跨 submission → assignment → task → institution 的 join 必须取得到展示字段。

    用同步 `Session(engine)` 落库准备数据（异步全局 session 绑定在 TestClient 的
    事件循环上，`asyncio.run` 会遇到 Event loop is closed）；测完按 FK 反序硬删除，
    不给共享会话库留下残留（其它用例会断言成果计数为 0）。
    """

    @staticmethod
    def _seed_pending_submission(suffix: str) -> dict[str, int]:
        from sqlalchemy.orm import Session

        from app.core.database import engine
        from app.modules.market.models import (
            AssignmentModel,
            CompanyModel,
            InstitutionModel,
            ProjectModel,
            SubmissionModel,
            TaskModel,
            TaskTemplateModel,
        )
        from app.modules.system.user.model import UserModel

        with Session(engine) as db:
            template_id = db.query(TaskTemplateModel.id).order_by(TaskTemplateModel.id).limit(1).scalar()
            user_id = db.query(UserModel.id).order_by(UserModel.id).limit(1).scalar()
            assert template_id is not None and user_id is not None

            company = CompanyModel(name=f"队列测试公司-{suffix}", code=f"COQ-{suffix}")
            db.add(company)
            db.flush()
            project = ProjectModel(
                code=f"PRJQ-{suffix}",
                name=f"队列测试项目-{suffix}",
                company_id=company.id,
                period=date(2026, 12, 31),
            )
            db.add(project)
            db.flush()
            institution = InstitutionModel(name=f"队列测试机构-{suffix}", type="grade_hospital")
            db.add(institution)
            db.flush()
            task = TaskModel(
                task_no=f"TKQ-{suffix}",
                project_id=project.id,
                template_id=template_id,
                name=f"队列测试任务-{suffix}",
                period=date(2026, 12, 31),
            )
            db.add(task)
            db.flush()
            assignment = AssignmentModel(task_id=task.id, user_id=user_id)
            db.add(assignment)
            db.flush()
            submission = SubmissionModel(
                assignment_id=assignment.id,
                user_id=user_id,
                subject_type="institution",
                institution_id=institution.id,
                period="2026-03",
                form_data={},
                status=SubmissionStatus.PENDING.value,
            )
            db.add(submission)
            db.commit()
            return {
                "submission": submission.id,
                "assignment": assignment.id,
                "task": task.id,
                "project": project.id,
                "company": company.id,
                "institution": institution.id,
            }

    @staticmethod
    def _purge(ids: dict[str, int]) -> None:
        from sqlalchemy.orm import Session

        from app.core.database import engine
        from app.modules.market.models import (
            AssignmentModel,
            CompanyModel,
            InstitutionModel,
            ProjectModel,
            SubmissionModel,
            TaskModel,
        )

        with Session(engine) as db:
            for model, key in (
                (SubmissionModel, "submission"),
                (AssignmentModel, "assignment"),
                (TaskModel, "task"),
                (ProjectModel, "project"),
                (CompanyModel, "company"),
                (InstitutionModel, "institution"),
            ):
                obj = db.get(model, ids[key])
                if obj is not None:
                    db.delete(obj)
            db.commit()

    def test_queue_row_fields_and_trend(self, test_client: TestClient, auth_headers: dict) -> None:
        """一条待审核成果应同时进入队列（带机构名/任务名）与今日趋势桶。"""
        ids = self._seed_pending_submission("A")
        try:
            data = test_client.get("/market/dashboard/insights", headers=auth_headers).json()["data"]
            rows = data["pending_submissions"]
            assert len(rows) == 1
            assert rows[0]["subject"] == "队列测试机构-A"
            assert rows[0]["task_name"] == "队列测试任务-A"
            assert rows[0]["period"] == "2026-03"
            assert rows[0]["created_at"].endswith("+08:00")
            # 今日（北京时间）桶里多一条待审核
            assert data["submission_trend"][-1]["pending"] == 1
        finally:
            self._purge(ids)

    def test_queue_excludes_non_pending(self, test_client: TestClient, auth_headers: dict) -> None:
        """已通过的成果不进队列，但仍计入趋势的 approved 桶。"""
        from sqlalchemy.orm import Session

        from app.core.database import engine
        from app.modules.market.models import SubmissionModel

        ids = self._seed_pending_submission("B")
        try:
            with Session(engine) as db:
                row = db.get(SubmissionModel, ids["submission"])
                assert row is not None
                row.status = SubmissionStatus.APPROVED.value
                db.commit()

            data = test_client.get("/market/dashboard/insights", headers=auth_headers).json()["data"]
            assert data["pending_submissions"] == []
            assert data["submission_trend"][-1]["approved"] == 1
        finally:
            self._purge(ids)

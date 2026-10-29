"""market 域集成测试：运营工作台（市场数据概览）统计。"""

from fastapi.testclient import TestClient


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

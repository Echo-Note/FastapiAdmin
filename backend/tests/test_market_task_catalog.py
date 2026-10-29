"""market 域集成测试：任务目录树（一级分类 + 二级模板）。"""

from fastapi.testclient import TestClient


class TestTaskCatalogTree:
    def test_tree_structure(self, test_client: TestClient, auth_headers: dict) -> None:
        """目录树接口返回分类父节点 + 模板子节点，且子节点归属正确。"""
        resp = test_client.get("/market/categories/tree", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True

        categories = body["data"]
        # 种子：一级分类 6 条、二级模板 18 条（任务目录三级化后，见 DEVELOPMENT-LOG「任务目录三级化」）
        assert len(categories) == 6
        assert sum(len(c["children"]) for c in categories) == 18

        for category in categories:
            # 分类节点不含 category_id（只有模板子节点携带）
            assert "category_id" not in category
            assert set(category.keys()) >= {"id", "code", "name", "children"}
            for child in category["children"]:
                assert child["category_id"] == category["id"]
                assert set(child.keys()) >= {"id", "code", "name", "category_id", "config", "enabled"}

    def test_tree_sorted_by_sort(self, test_client: TestClient, auth_headers: dict) -> None:
        """分类按 sort 升序返回。"""
        resp = test_client.get("/market/categories/tree", headers=auth_headers)
        categories = resp.json()["data"]
        sorts = [c["sort"] for c in categories]
        assert sorts == sorted(sorts)

    def test_tree_requires_auth(self, test_client: TestClient) -> None:
        """未认证访问目录树应被拒绝（401）。"""
        resp = test_client.get("/market/categories/tree")
        assert resp.status_code == 401

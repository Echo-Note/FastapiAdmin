"""market 域集成测试：医药公司与机构主数据 CRUD。"""

from fastapi.testclient import TestClient


class TestCompany:
    def test_create(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.post(
            "/market/companies/create",
            json={"name": "测试医药公司A", "credit_code": "91110000A"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["name"] == "测试医药公司A"

    def test_create_duplicate_name_fails(self, test_client: TestClient, auth_headers: dict) -> None:
        test_client.post("/market/companies/create", json={"name": "重复公司"}, headers=auth_headers)
        resp = test_client.post("/market/companies/create", json={"name": "重复公司"}, headers=auth_headers)
        assert resp.json()["success"] is False

    def test_list_and_detail(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.get("/market/companies/list", params={"page_no": 1, "page_size": 10}, headers=auth_headers)
        assert resp.json()["success"] is True
        items = resp.json()["data"]["items"]
        assert isinstance(items, list)

        resp = test_client.get("/market/companies/list", params={"name": "测试医药公司A"}, headers=auth_headers)
        assert resp.json()["success"] is True
        company_id = resp.json()["data"]["items"][0]["id"]

        resp = test_client.get(f"/market/companies/detail/{company_id}", headers=auth_headers)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["name"] == "测试医药公司A"

    def test_detail_not_found(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.get("/market/companies/detail/999999", headers=auth_headers)
        assert resp.json()["success"] is False

    def test_update(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.get("/market/companies/list", params={"name": "测试医药公司A"}, headers=auth_headers)
        company_id = resp.json()["data"]["items"][0]["id"]
        resp = test_client.put(f"/market/companies/update/{company_id}", json={"contact": "张三", "status": 1}, headers=auth_headers)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["contact"] == "张三"
        assert resp.json()["data"]["status"] == 1

    def test_update_duplicate_name_fails(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.get("/market/companies/list", params={"name": "测试医药公司A"}, headers=auth_headers)
        company_id = resp.json()["data"]["items"][0]["id"]
        resp = test_client.put(f"/market/companies/update/{company_id}", json={"name": "重复公司"}, headers=auth_headers)
        assert resp.json()["success"] is False

    def test_delete(self, test_client: TestClient, auth_headers: dict) -> None:
        test_client.post("/market/companies/create", json={"name": "待删除公司"}, headers=auth_headers)
        resp = test_client.get("/market/companies/list", params={"name": "待删除公司"}, headers=auth_headers)
        company_id = resp.json()["data"]["items"][0]["id"]
        resp = test_client.request("DELETE", "/market/companies/delete", json=[company_id], headers=auth_headers)
        assert resp.json()["success"] is True
        # 删除后查不到
        resp = test_client.get(f"/market/companies/detail/{company_id}", headers=auth_headers)
        assert resp.json()["success"] is False

    def test_delete_empty_ids_fails(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.request("DELETE", "/market/companies/delete", json=[], headers=auth_headers)
        assert resp.json()["success"] is False


class TestInstitution:
    def test_create(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.post(
            "/market/institutions/create",
            json={"name": "测试医院", "type": "grade_hospital", "level": "三甲", "region": "北京"},
            headers=auth_headers,
        )
        assert resp.json()["success"] is True
        assert resp.json()["data"]["name"] == "测试医院"

    def test_list_and_detail(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.get("/market/institutions/list", params={"name": "测试医院"}, headers=auth_headers)
        assert resp.json()["success"] is True
        institution_id = resp.json()["data"]["items"][0]["id"]

        resp = test_client.get(f"/market/institutions/detail/{institution_id}", headers=auth_headers)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["type"] == "grade_hospital"

    def test_update(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.get("/market/institutions/list", params={"name": "测试医院"}, headers=auth_headers)
        institution_id = resp.json()["data"]["items"][0]["id"]
        resp = test_client.put(f"/market/institutions/update/{institution_id}", json={"region": "上海"}, headers=auth_headers)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["region"] == "上海"

    def test_delete(self, test_client: TestClient, auth_headers: dict) -> None:
        test_client.post("/market/institutions/create", json={"name": "待删除机构", "type": "retail_pharmacy"}, headers=auth_headers)
        resp = test_client.get("/market/institutions/list", params={"name": "待删除机构"}, headers=auth_headers)
        institution_id = resp.json()["data"]["items"][0]["id"]
        resp = test_client.request("DELETE", "/market/institutions/delete", json=[institution_id], headers=auth_headers)
        assert resp.json()["success"] is True

"""market 域导入中心模块测试：结算单导入 / 报告附件关联 / 同音去重 / 幂等。

走 HTTP 全链路（controller → service → parser → CRUD 落库），断言落库结果与幂等性。
"""

import io

from fastapi.testclient import TestClient
from openpyxl import Workbook

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_INNER_HEADER = ["任务\n序号", "服务项目", None, None, "费用标准", None, "执行要求", None, "实际执行", None]
_INNER_SUBHEADER = [None, "类型", "项目", "任务", "单位", "单价", "执行数量", "执行标准", "数量", "费用金额"]
_OUTER_HEADER = ["序号", "服务项目", None, "计费单位", "单价", "数量", "小计"]


def _xlsx_bytes(rows: list[list]) -> bytes:
    """把二维列表渲染为 xlsx 字节流。"""
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _inner_xlsx(task_no: int, qty: int, amount: float) -> bytes:
    """构造一张含单条「实际执行」行的对内结算单。"""
    return _xlsx_bytes(
        [
            ["市场管理服务结算清单"],
            _INNER_HEADER,
            _INNER_SUBHEADER,
            [task_no, "终端服务", "空白市场开发", "空白等级医院开发", "元/家", 25000, "非必选", "/", qty, amount],
        ]
    )


def _outer_xlsx(service_no: int, qty: int, amount: float) -> bytes:
    """构造一张含单条「实际执行」行的对外服务项目结算单。"""
    return _xlsx_bytes(
        [
            ["服务项目结算单"],
            _OUTER_HEADER,
            [service_no, "合作开发服务", "空白等级医院开发", "元/家", 25000, qty, amount],
        ]
    )


def _upload_settlement(client: TestClient, headers: dict, filename: str, content: bytes, period: str) -> dict:
    """上传一张结算单，返回解析后的 JSON 响应体。"""
    resp = client.post(
        "/market/import/settlement",
        params={"period": period},
        files=[("files", (filename, content, _XLSX_MIME))],
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestImportInnerSettlement:
    """对内结算单导入：task + 执行人用户 + 分派 + 结算落库。"""

    def test_import_inner(self, test_client: TestClient, auth_headers: dict) -> None:
        content = _inner_xlsx(task_no=1, qty=4, amount=4000)
        body = _upload_settlement(test_client, auth_headers, "0.重庆-省平台项目结算单-重庆熊丽.xlsx", content, "2099-01")
        assert body["success"] is True
        data = body["data"]
        assert data["task_created"] == 1
        assert data["user_created"] == 1
        assert data["assignment_created"] == 1
        assert data["settlement_created"] == 1
        assert data["company_created"] == 0
        assert data["report_created"] == 0
        assert data["errors"] == []

    def test_import_inner_reuses_user_and_is_idempotent(self, test_client: TestClient, auth_headers: dict) -> None:
        """同一文件重复导入：第二次全 0（任务/用户/分派/结算均幂等复用）。"""
        content = _inner_xlsx(task_no=1, qty=4, amount=4000)
        filename = "0.重庆-省平台项目结算单-重庆熊志鹏.xlsx"
        first = _upload_settlement(test_client, auth_headers, filename, content, "2099-03")
        second = _upload_settlement(test_client, auth_headers, filename, content, "2099-03")
        assert first["data"]["user_created"] == 1
        assert second["data"]["task_created"] == 0
        assert second["data"]["user_created"] == 0
        assert second["data"]["assignment_created"] == 0
        assert second["data"]["settlement_created"] == 0


class TestImportOuterSettlement:
    """对外结算单导入：委托公司 + 报告落库。"""

    def test_import_outer(self, test_client: TestClient, auth_headers: dict) -> None:
        content = _outer_xlsx(service_no=1, qty=2, amount=50000)
        body = _upload_settlement(
            test_client, auth_headers, "复星万邦-聚苯乙烯磺酸钙散-服务项目结算单.xlsx", content, "2099-02"
        )
        assert body["success"] is True
        data = body["data"]
        assert data["company_created"] == 1
        assert data["report_created"] == 1
        assert data["task_created"] == 0
        assert data["user_created"] == 0


class TestUserDedup:
    """同音不同字执行人去重：黄莉 / 黄丽不应合并为同一账号。"""

    def test_same_pinyin_users_not_merged(self, test_client: TestClient, auth_headers: dict) -> None:
        li = _inner_xlsx(task_no=1, qty=4, amount=4000)
        li2 = _inner_xlsx(task_no=1, qty=2, amount=2000)
        body_li = _upload_settlement(test_client, auth_headers, "0.重庆-省平台项目结算单-重庆黄莉.xlsx", li, "2099-04")
        body_li2 = _upload_settlement(test_client, auth_headers, "0.重庆-省平台项目结算单-重庆黄丽.xlsx", li2, "2099-04")
        assert body_li["data"]["user_created"] == 1
        assert body_li2["data"]["user_created"] == 1

        # 两个执行人应落为两个账号：huangli（黄莉）+ huangli2（黄丽）
        resp = test_client.get("/system/user/list", params={"username": "huangli"}, headers=auth_headers)
        assert resp.json()["success"] is True
        usernames = {u["username"] for u in resp.json()["data"]["items"]}
        assert "huangli" in usernames
        assert "huangli2" in usernames

    def test_same_name_user_reused_across_files(self, test_client: TestClient, auth_headers: dict) -> None:
        """同名执行人出现在两个文件：复用同一账号，不重复创建。"""
        file_a = _inner_xlsx(task_no=1, qty=3, amount=3000)
        file_b = _inner_xlsx(task_no=2, qty=2, amount=2000)
        _upload_settlement(test_client, auth_headers, "0.重庆-省平台项目结算单-重庆王芳.xlsx", file_a, "2099-06")
        second = _upload_settlement(test_client, auth_headers, "0.重庆-省平台项目结算单-重庆王芳.xlsx", file_b, "2099-06")
        assert second["data"]["user_created"] == 0  # 同名复用，不新建用户
        resp = test_client.get("/system/user/list", params={"name": "王芳"}, headers=auth_headers)
        assert resp.json()["data"]["total"] == 1


class TestReportAttachment:
    """报告附件（pptx）关联。"""

    def test_link_attachment(self, test_client: TestClient, auth_headers: dict) -> None:
        # 先导入对外结算单生成报告
        content = _outer_xlsx(service_no=1, qty=2, amount=50000)
        _upload_settlement(
            test_client, auth_headers, "复星万邦-聚苯乙烯磺酸钙散-服务项目结算单.xlsx", content, "2099-05"
        )
        resp = test_client.post(
            "/market/import/report",
            params={"service_no": 1, "period": "2099-05"},
            files=[("file", ("12.等级医院用药数据收集.pptx", b"PK\x03\x04fake-pptx", "application/octet-stream"))],
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True

    def test_link_attachment_report_not_found(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.post(
            "/market/import/report",
            params={"service_no": 999, "period": "2099-99"},
            files=[("file", ("报告.pptx", b"PK\x03\x04fake-pptx", "application/octet-stream"))],
            headers=auth_headers,
        )
        assert resp.json()["success"] is False

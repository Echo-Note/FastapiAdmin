"""market 域集成测试：分派/接收/提交/审核/结算/报告/发放/大厅接单完整业务闭环。"""

from fastapi.testclient import TestClient


def _login_user(client: TestClient) -> dict:
    resp = client.post("/system/auth/login", data={"username": "user", "password": "123456"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}


def _create_and_login_user(client: TestClient, admin_headers: dict, username: str) -> tuple[dict, int]:
    """创建并登录一个 C 端用户，返回 (认证头, 用户ID)。"""
    resp = client.post("/system/user/create", json={"username": username, "name": username, "password": "abc123456", "status": 0}, headers=admin_headers)
    assert resp.json()["success"] is True, resp.text
    uid = resp.json()["data"]["id"]
    login = client.post("/system/auth/login", data={"username": username, "password": "abc123456"})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}, uid


def _get_user_id(client: TestClient, headers: dict) -> int:
    resp = client.get("/system/user/list", params={"username": "user"}, headers=headers)
    return resp.json()["data"]["items"][0]["id"]


def _create_company(client: TestClient, headers: dict, name: str, code: str) -> int:
    client.post("/market/companies/create", json={"name": name, "code": code}, headers=headers)
    return client.get("/market/companies/list", params={"name": name}, headers=headers).json()["data"]["items"][0]["id"]


def _create_project(client: TestClient, headers: dict, code: str, company_id: int, period: str) -> int:
    """创建项目（对外），返回项目 ID。"""
    client.post(
        "/market/projects/create",
        json={"code": code, "name": f"项目{code}", "company_id": company_id, "period": period},
        headers=headers,
    )
    return client.get("/market/projects/list", params={"code": code}, headers=headers).json()["data"]["items"][0]["id"]


_FLOW_TASK_NO_COUNTER = 1000  # 避开种子任务号 1-44


def _create_task_type(client: TestClient, headers: dict, code: str) -> int:
    """创建模板 + 任务类型（计价项），返回任务类型 ID。"""
    client.post(
        "/market/templates/create",
        json={"code": f"tpl_{code}", "name": f"模板{code}", "scope": "1-4", "form_schema": [{"name": "hospital_name", "label": "医院名称", "type": "text", "required": True}]},
        headers=headers,
    )
    template_id = client.get("/market/templates/list", params={"code": f"tpl_{code}"}, headers=headers).json()["data"]["items"][0]["id"]
    global _FLOW_TASK_NO_COUNTER
    _FLOW_TASK_NO_COUNTER += 1
    client.post(
        "/market/task-types/create",
        json={"code": code, "name": code, "task_no": _FLOW_TASK_NO_COUNTER, "template_id": template_id, "service_type": "医院管理", "service_item": "等级医院", "service_task": "采集", "unit": "家/月", "default_price": 3000},
        headers=headers,
    )
    return client.get("/market/task-types/list", params={"code": code}, headers=headers).json()["data"]["items"][0]["id"]


def _create_published_task(
    client: TestClient,
    headers: dict,
    task_no: str,
    tt_id: int,
    period: str = "2026-10",
    exec_qty: int = 1,
    assign_mode: str = "direct",
    task_kind: str | None = None,
    unit_price: int | None = None,
    project_ids: list[int] | None = None,
) -> int:
    """创建并发布任务，返回任务 ID。定额任务自动附带限定时间范围。"""
    payload: dict = {"task_no": task_no, "task_type_id": tt_id, "period": period, "exec_qty": exec_qty, "assign_mode": assign_mode}
    if task_kind is not None:
        payload["task_kind"] = task_kind
    if task_kind == "quota":
        payload["exec_time_start"] = "2026-01-01 00:00:00"
        payload["exec_time_end"] = "2099-12-31 23:59:59"
    if unit_price is not None:
        payload["unit_price"] = unit_price
    if project_ids is not None:
        payload["project_ids"] = project_ids
    client.post("/market/tasks/create", json=payload, headers=headers)
    task_id = client.get("/market/tasks/list", params={"task_no": task_no}, headers=headers).json()["data"]["items"][0]["id"]
    client.post(f"/market/tasks/publish/{task_id}", json={}, headers=headers)
    return task_id


def _create_institution(client: TestClient, headers: dict, name: str) -> int:
    client.post("/market/institutions/create", json={"name": name, "type": "grade_hospital"}, headers=headers)
    return client.get("/market/institutions/list", params={"name": name}, headers=headers).json()["data"]["items"][0]["id"]


def _assign_and_accept(client: TestClient, headers: dict, user_h: dict, task_id: int, uid: int) -> int:
    """定向分派任务给用户并接收，返回分派 ID。"""
    aid = client.post("/market/assignments/create", json={"task_id": task_id, "user_ids": [uid]}, headers=headers).json()["data"][0]["id"]
    client.post(f"/market/mini/assignments/{aid}/accept", headers=user_h)
    return aid


def _submit_and_approve(client: TestClient, headers: dict, user_h: dict, assignment_id: int, institution_name: str) -> None:
    """提交一份成果并审核通过。"""
    iid = _create_institution(client, headers, institution_name)
    resp = client.post(
        "/market/mini/submissions",
        json={"assignment_id": assignment_id, "institution_id": iid, "form_data": {"hospital_name": institution_name}, "status": "PENDING"},
        headers=user_h,
    )
    sid = resp.json()["data"]["id"]
    client.post(f"/market/submissions/review/{sid}", json={"action": "approve"}, headers=headers)


class TestAssignmentFlow:
    def test_assign_accept(self, test_client: TestClient, auth_headers: dict) -> None:
        ttid = _create_task_type(test_client, auth_headers, "flow_tt_1")
        tid = _create_published_task(test_client, auth_headers, "FLOW-TASK-1", ttid)
        uid = _get_user_id(test_client, auth_headers)
        user_h = _login_user(test_client)

        resp = test_client.post("/market/assignments/create", json={"task_id": tid, "user_ids": [uid]}, headers=auth_headers)
        assert resp.json()["success"] is True
        assignment_id = resp.json()["data"][0]["id"]
        assert resp.json()["data"][0]["status"] == "PENDING"

        resp = test_client.post(f"/market/mini/assignments/{assignment_id}/accept", headers=user_h)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["status"] == "ACCEPTED"

    def test_assign_duplicate_idempotent(self, test_client: TestClient, auth_headers: dict) -> None:
        ttid = _create_task_type(test_client, auth_headers, "flow_tt_2")
        tid = _create_published_task(test_client, auth_headers, "FLOW-TASK-2", ttid)
        uid = _get_user_id(test_client, auth_headers)
        # 同一任务同一用户重复分派，第二次返回空列表（幂等）
        test_client.post("/market/assignments/create", json={"task_id": tid, "user_ids": [uid]}, headers=auth_headers)
        resp = test_client.post("/market/assignments/create", json={"task_id": tid, "user_ids": [uid]}, headers=auth_headers)
        assert resp.json()["success"] is True
        assert resp.json()["data"] == []

    def test_assign_invalid_user_fails(self, test_client: TestClient, auth_headers: dict) -> None:
        ttid = _create_task_type(test_client, auth_headers, "flow_tt_3")
        tid = _create_published_task(test_client, auth_headers, "FLOW-TASK-3", ttid)
        resp = test_client.post("/market/assignments/create", json={"task_id": tid, "user_ids": [999999]}, headers=auth_headers)
        assert resp.json()["success"] is False

    def test_accept_twice_fails(self, test_client: TestClient, auth_headers: dict) -> None:
        ttid = _create_task_type(test_client, auth_headers, "flow_tt_4")
        tid = _create_published_task(test_client, auth_headers, "FLOW-TASK-4", ttid)
        uid = _get_user_id(test_client, auth_headers)
        user_h = _login_user(test_client)
        aid = test_client.post("/market/assignments/create", json={"task_id": tid, "user_ids": [uid]}, headers=auth_headers).json()["data"][0]["id"]
        assert test_client.post(f"/market/mini/assignments/{aid}/accept", headers=user_h).json()["success"] is True
        resp = test_client.post(f"/market/mini/assignments/{aid}/accept", headers=user_h)
        assert resp.json()["success"] is False


class TestSubmissionFlow:
    def test_submit_review_approve(self, test_client: TestClient, auth_headers: dict) -> None:
        ttid = _create_task_type(test_client, auth_headers, "flow_tt_5")
        tid = _create_published_task(test_client, auth_headers, "FLOW-TASK-5", ttid)
        uid = _get_user_id(test_client, auth_headers)
        user_h = _login_user(test_client)
        aid = _assign_and_accept(test_client, auth_headers, user_h, tid, uid)
        iid = _create_institution(test_client, auth_headers, "流程机构5")

        resp = test_client.post(
            "/market/mini/submissions",
            json={"assignment_id": aid, "institution_id": iid, "form_data": {"hospital_name": "XX医院"}, "status": "PENDING"},
            headers=user_h,
        )
        assert resp.json()["success"] is True
        submission_id = resp.json()["data"]["id"]
        assert resp.json()["data"]["status"] == "PENDING"

        # 审核通过
        resp = test_client.post(f"/market/submissions/review/{submission_id}", json={"action": "approve"}, headers=auth_headers)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["status"] == "APPROVED"

    def test_submit_missing_required_fails(self, test_client: TestClient, auth_headers: dict) -> None:
        ttid = _create_task_type(test_client, auth_headers, "flow_tt_6")
        tid = _create_published_task(test_client, auth_headers, "FLOW-TASK-6", ttid)
        uid = _get_user_id(test_client, auth_headers)
        user_h = _login_user(test_client)
        aid = _assign_and_accept(test_client, auth_headers, user_h, tid, uid)
        iid = _create_institution(test_client, auth_headers, "流程机构6")

        # 必填字段缺失，正式提交失败
        resp = test_client.post(
            "/market/mini/submissions",
            json={"assignment_id": aid, "institution_id": iid, "form_data": {}, "status": "PENDING"},
            headers=user_h,
        )
        assert resp.json()["success"] is False

    def test_draft_reject_resubmit(self, test_client: TestClient, auth_headers: dict) -> None:
        """草稿暂存 → 正式提交 → 驳回 → 重提（版本 +1）。"""
        ttid = _create_task_type(test_client, auth_headers, "flow_tt_7")
        tid = _create_published_task(test_client, auth_headers, "FLOW-TASK-7", ttid)
        uid = _get_user_id(test_client, auth_headers)
        user_h = _login_user(test_client)
        aid = _assign_and_accept(test_client, auth_headers, user_h, tid, uid)
        iid = _create_institution(test_client, auth_headers, "流程机构7")

        # 存草稿
        resp = test_client.post(
            "/market/mini/submissions",
            json={"assignment_id": aid, "institution_id": iid, "form_data": {"hospital_name": "草稿医院"}, "status": "DRAFT"},
            headers=user_h,
        )
        assert resp.json()["success"] is True
        draft_id = resp.json()["data"]["id"]
        assert resp.json()["data"]["status"] == "DRAFT"

        # 草稿不可审核
        resp = test_client.post(f"/market/submissions/review/{draft_id}", json={"action": "approve"}, headers=auth_headers)
        assert resp.json()["success"] is False

        # 正式提交（周期任务单月一次，草稿不计入）
        resp = test_client.post(
            "/market/mini/submissions",
            json={"assignment_id": aid, "institution_id": iid, "form_data": {"hospital_name": "YY医院"}, "status": "PENDING"},
            headers=user_h,
        )
        assert resp.json()["success"] is True
        sub_id = resp.json()["data"]["id"]
        assert resp.json()["data"]["status"] == "PENDING"

        # 驳回（无意见失败）
        resp = test_client.post(f"/market/submissions/review/{sub_id}", json={"action": "reject"}, headers=auth_headers)
        assert resp.json()["success"] is False

        # 驳回（带意见）
        resp = test_client.post(f"/market/submissions/review/{sub_id}", json={"action": "reject", "comment": "信息不全"}, headers=auth_headers)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["status"] == "REJECTED"

        # 驳回重提：版本 +1，回到待审核
        resp = test_client.put(f"/market/mini/submissions/{sub_id}", json={"form_data": {"hospital_name": "ZZ医院"}}, headers=user_h)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["version"] == 2
        assert resp.json()["data"]["status"] == "PENDING"


class TestSettlementReportFlow:
    def test_settle_and_report(self, test_client: TestClient, auth_headers: dict) -> None:
        cid = _create_company(test_client, auth_headers, "流程公司8", "FLOW-8")
        pid = _create_project(test_client, auth_headers, "PRJ-8", cid, "2026-10")
        ttid = _create_task_type(test_client, auth_headers, "flow_tt_8")
        tid = _create_published_task(test_client, auth_headers, "FLOW-TASK-8", ttid, project_ids=[pid])
        uid = _get_user_id(test_client, auth_headers)
        user_h = _login_user(test_client)
        aid = _assign_and_accept(test_client, auth_headers, user_h, tid, uid)
        _submit_and_approve(test_client, auth_headers, user_h, aid, "流程机构8")

        # 判定完成 + 结算
        test_client.post(f"/market/tasks/complete/{tid}", headers=auth_headers)
        resp = test_client.post(f"/market/tasks/settle/{tid}", headers=auth_headers)
        assert resp.json()["success"] is True
        settlements = resp.json()["data"]
        assert len(settlements) == 1
        assert settlements[0]["payable_amount"] == 3000
        assert len(settlements[0]["items"]) == 1

        # 结算单详情
        settlement_id = settlements[0]["id"]
        resp = test_client.get(f"/market/settlements/detail/{settlement_id}", headers=auth_headers)
        assert resp.json()["success"] is True

        # 报告生成（按医药公司 × 周期，需项目归集任务）
        resp = test_client.post("/market/reports/generate", json={"company_id": cid, "period": "2026-10"}, headers=auth_headers)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["status"] == "GENERATED"

        report_id = resp.json()["data"]["id"]
        resp = test_client.get("/market/reports/list", params={"company_id": cid}, headers=auth_headers)
        assert resp.json()["success"] is True
        resp = test_client.get(f"/market/reports/detail/{report_id}", headers=auth_headers)
        assert resp.json()["success"] is True

    def test_settle_requires_complete(self, test_client: TestClient, auth_headers: dict) -> None:
        ttid = _create_task_type(test_client, auth_headers, "flow_tt_9")
        tid = _create_published_task(test_client, auth_headers, "FLOW-TASK-9", ttid)
        # 未判定完成不可结算
        resp = test_client.post(f"/market/tasks/settle/{tid}", headers=auth_headers)
        assert resp.json()["success"] is False

    def test_settle_no_approved_returns_empty(self, test_client: TestClient, auth_headers: dict) -> None:
        ttid = _create_task_type(test_client, auth_headers, "flow_tt_10")
        tid = _create_published_task(test_client, auth_headers, "FLOW-TASK-10", ttid)
        uid = _get_user_id(test_client, auth_headers)
        # 分派但未接收，无通过成果
        test_client.post("/market/assignments/create", json={"task_id": tid, "user_ids": [uid]}, headers=auth_headers)
        test_client.post(f"/market/tasks/complete/{tid}", headers=auth_headers)
        resp = test_client.post(f"/market/tasks/settle/{tid}", headers=auth_headers)
        assert resp.json()["success"] is True
        assert resp.json()["data"] == []

    def test_report_no_project_fails(self, test_client: TestClient, auth_headers: dict) -> None:
        cid = _create_company(test_client, auth_headers, "流程公司11", "FLOW-11")
        resp = test_client.post("/market/reports/generate", json={"company_id": cid, "period": "2099-01"}, headers=auth_headers)
        assert resp.json()["success"] is False


class TestPayoutFlow:
    PERIOD = "2026-09"  # 独立周期，避免与其它用例的累计金额相互污染

    def test_payout_config_and_usage(self, test_client: TestClient, auth_headers: dict) -> None:
        uid = _get_user_id(test_client, auth_headers)
        resp = test_client.post("/market/payout/save", json={"user_id": uid, "period": self.PERIOD, "payout_limit": 5000}, headers=auth_headers)
        assert resp.json()["success"] is True

        # 重复保存（upsert）
        resp = test_client.post("/market/payout/save", json={"user_id": uid, "period": self.PERIOD, "payout_limit": 8000}, headers=auth_headers)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["payout_limit"] == 8000

        # 配置列表
        resp = test_client.get("/market/payout/list", params={"user_id": uid}, headers=auth_headers)
        assert resp.json()["success"] is True

        # 使用情况查询
        resp = test_client.get("/market/payout/usage", params={"user_id": uid, "period": self.PERIOD}, headers=auth_headers)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["payout_limit"] == 8000

    def test_payout_cap_and_allowance(self, test_client: TestClient, auth_headers: dict) -> None:
        """发放封顶 + 津贴累计：应发 6000、额度 3000 → 实发 3000、津贴滚存 3000。"""
        uid = _get_user_id(test_client, auth_headers)
        user_h = _login_user(test_client)
        test_client.post("/market/payout/save", json={"user_id": uid, "period": self.PERIOD, "payout_limit": 3000}, headers=auth_headers)

        ttid = _create_task_type(test_client, auth_headers, "pay_tt_1")
        tid = _create_published_task(test_client, auth_headers, "PAY-TASK-1", ttid, self.PERIOD, exec_qty=10, task_kind="quota")
        aid = _assign_and_accept(test_client, auth_headers, user_h, tid, uid)

        # 提交 2 份成果并审核通过 → 应发 3000 × 2 = 6000
        _submit_and_approve(test_client, auth_headers, user_h, aid, "发放医院A")
        _submit_and_approve(test_client, auth_headers, user_h, aid, "发放医院B")

        test_client.post(f"/market/tasks/complete/{tid}", headers=auth_headers)
        resp = test_client.post(f"/market/tasks/settle/{tid}", headers=auth_headers)
        assert resp.json()["success"] is True
        settlements = resp.json()["data"]
        assert len(settlements) == 1
        assert settlements[0]["payable_amount"] == 6000
        assert settlements[0]["paid_amount"] == 3000

        # 津贴余额 = 6000 - 3000 = 3000
        resp = test_client.get("/market/mini/payout", params={"period": self.PERIOD}, headers=user_h)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["allowance_balance"] == 3000
        assert resp.json()["data"]["payout_limit"] == 3000


class TestMiniInstitution:
    def test_mini_institution_list_for_c_end_user(self, test_client: TestClient, auth_headers: dict) -> None:
        """C 端（小程序）用户无需运营端 RBAC 权限即可获取机构列表（返回 items）。"""
        _create_institution(test_client, auth_headers, "小程序机构A")
        user_h = _login_user(test_client)

        resp = test_client.get("/market/mini/institutions", params={"page_no": 1, "page_size": 100}, headers=user_h)
        assert resp.json()["success"] is True
        items = resp.json()["data"]["items"]
        assert isinstance(items, list)
        assert any(item["name"] == "小程序机构A" for item in items)

    def test_mini_institution_list_excludes_disabled(self, test_client: TestClient, auth_headers: dict) -> None:
        """C 端机构列表仅返回启用机构（status=0），停用机构不返回。"""
        test_client.post(
            "/market/institutions/create",
            json={"name": "小程序停用机构", "type": "retail_pharmacy", "status": 1},
            headers=auth_headers,
        )
        user_h = _login_user(test_client)

        resp = test_client.get("/market/mini/institutions", params={"page_no": 1, "page_size": 100}, headers=user_h)
        assert resp.json()["success"] is True
        names = [item["name"] for item in resp.json()["data"]["items"]]
        assert "小程序停用机构" not in names


class TestOpenTaskClaim:
    """公开大厅自行接单流程（定向分派 + 大厅接单两种模式并存）。"""

    PERIOD = "2026-12"  # 独立周期

    def test_open_task_visible_and_claim(self, test_client: TestClient, auth_headers: dict) -> None:
        """公开任务对 C 端用户可见，可自行接单（source=claimed，直接已接收）。"""
        ttid = _create_task_type(test_client, auth_headers, "flow_tt_12")
        tid = _create_published_task(test_client, auth_headers, "FLOW-TASK-13", ttid, self.PERIOD, assign_mode="open", exec_qty=5)
        user_h = _login_user(test_client)

        # 任务大厅应包含该公开任务
        resp = test_client.get("/market/mini/tasks", params={"page_no": 1, "page_size": 100}, headers=user_h)
        assert resp.json()["success"] is True
        task_nos = [t["task_no"] for t in resp.json()["data"]["items"]]
        assert "FLOW-TASK-13" in task_nos

        # 接单成功，直接进入已接收状态，来源标记为大厅接单
        resp = test_client.post(f"/market/mini/tasks/{tid}/claim", headers=user_h)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["status"] == "ACCEPTED"
        assert resp.json()["data"]["source"] == "claimed"

    def test_direct_task_not_in_hall(self, test_client: TestClient, auth_headers: dict) -> None:
        """定向分派任务不出现在任务大厅。"""
        ttid = _create_task_type(test_client, auth_headers, "flow_tt_13")
        _create_published_task(test_client, auth_headers, "FLOW-TASK-14", ttid, self.PERIOD, assign_mode="direct")
        user_h = _login_user(test_client)

        resp = test_client.get("/market/mini/tasks", params={"page_no": 1, "page_size": 100}, headers=user_h)
        assert resp.json()["success"] is True
        task_nos = [t["task_no"] for t in resp.json()["data"]["items"]]
        assert "FLOW-TASK-14" not in task_nos

    def test_claim_duplicate_fails(self, test_client: TestClient, auth_headers: dict) -> None:
        """同一用户对同一公开任务仅可接单一次。"""
        ttid = _create_task_type(test_client, auth_headers, "flow_tt_14")
        tid = _create_published_task(test_client, auth_headers, "FLOW-TASK-15", ttid, self.PERIOD, assign_mode="open", exec_qty=5)
        user_h = _login_user(test_client)

        assert test_client.post(f"/market/mini/tasks/{tid}/claim", headers=user_h).json()["success"] is True
        resp = test_client.post(f"/market/mini/tasks/{tid}/claim", headers=user_h)
        assert resp.json()["success"] is False

    def test_open_task_cannot_be_assigned(self, test_client: TestClient, auth_headers: dict) -> None:
        """公开大厅任务不支持运营端定向分派。"""
        ttid = _create_task_type(test_client, auth_headers, "flow_tt_15")
        tid = _create_published_task(test_client, auth_headers, "FLOW-TASK-16", ttid, self.PERIOD, assign_mode="open", exec_qty=5)
        uid = _get_user_id(test_client, auth_headers)

        resp = test_client.post("/market/assignments/create", json={"task_id": tid, "user_ids": [uid]}, headers=auth_headers)
        assert resp.json()["success"] is False

    def test_quota_task_full_stops_claim(self, test_client: TestClient, auth_headers: dict) -> None:
        """定额任务接单限量：接满 exec_qty 后拒绝后续接单，任务从大厅消失。"""
        ttid = _create_task_type(test_client, auth_headers, "flow_tt_16")
        tid = _create_published_task(test_client, auth_headers, "FLOW-TASK-17", ttid, self.PERIOD, exec_qty=1, assign_mode="open", task_kind="quota")
        user_h = _login_user(test_client)

        # user 接单成功（占满唯一名额）
        resp = test_client.post(f"/market/mini/tasks/{tid}/claim", headers=user_h)
        assert resp.json()["success"] is True

        # 第二个用户接单失败（名额已满）
        user2_h, _uid2 = _create_and_login_user(test_client, auth_headers, "flow_user2")
        resp = test_client.post(f"/market/mini/tasks/{tid}/claim", headers=user2_h)
        assert resp.json()["success"] is False

        # 接满名额后任务从大厅消失
        hall = test_client.get("/market/mini/tasks", params={"page_no": 1, "page_size": 100}, headers=user2_h)
        task_nos = [t["task_no"] for t in hall.json()["data"]["items"]]
        assert "FLOW-TASK-17" not in task_nos

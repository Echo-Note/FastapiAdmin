from datetime import UTC, datetime

from sqlalchemy import false, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.base_schema import AuthSchema, BatchSetAvailable, PageResultSchema
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.utils.common_util import search_to_dict

from .crud import NoticeCRUD
from .model import NoticeModel, NoticeReadModel
from .schema import NoticeCreateSchema, NoticeOutSchema, NoticeQueryParam, NoticeUpdateSchema
from .stream import notice_stream_manager

# 公告状态：以**管理端实际用法**为准 —— 0 启用 / 1 停用（2 归档预留）。
# 模型注释里的「0 草稿 / 1 已发布 / 2 已归档」是历史遗留写法，管理端公告页
# 的下拉与单选项一直是「启用=0 / 停用=1」，运营「发送」出来的公告就是 status=0；
# 若按注释过滤 status=1，C 端会一条都收不到（已实际复现）。
NOTICE_STATUS_ENABLED = 0


async def _broadcast_notice_update() -> None:
    """公告变更后广播轻量信号（尽力而为）：客户端收到后拉取 available 以库为准。

    广播发生在请求事务提交前（db_getter 请求级事务在依赖退出时 commit），
    但变更信号与内容读取解耦，毫秒级窗口内的竞态由客户端拉取兜底。
    """
    try:
        await notice_stream_manager.broadcast({"type": "notice_update"})
    except Exception as e:
        logger.warning("公告变更广播失败（不影响业务）: {}", e)


class NoticeService:
    """公告管理服务

    提供公告 CRUD、状态切换、已启用公告分页查询、Excel 导出等业务能力。
    """

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> NoticeOutSchema:
        """获取公告详情

        参数:
        - id (int): 公告 ID

        返回:
        - NoticeOutSchema: 公告响应模型
        """
        obj = await NoticeCRUD(self.auth, self.db).get_or_404(id=id)
        return NoticeOutSchema.model_validate(obj)

    async def get_list(
        self,
        search: NoticeQueryParam | None = None,
        order_by: list[dict] | None = None,
    ) -> list[NoticeOutSchema]:
        """获取公告列表

        参数:
        - search (NoticeQueryParam | None): 查询参数
        - order_by (list[dict] | None): 排序规则

        返回:
        - list[NoticeOutSchema]: 公告列表
        """
        notice_obj_list = await NoticeCRUD(self.auth, self.db).get_list(search=search_to_dict(search), order_by=order_by)
        return [NoticeOutSchema.model_validate(notice_obj) for notice_obj in notice_obj_list]

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: NoticeQueryParam | None = None,
        order_by: list[dict] | None = None,
    ) -> PageResultSchema[NoticeOutSchema]:
        """分页查询公告

        参数:
        - page_no (int): 当前页码
        - page_size (int): 每页条数
        - search (NoticeQueryParam | None): 查询参数
        - order_by (list[dict] | None): 排序规则

        返回:
        - PageResultSchema[NoticeOutSchema]: 分页结果
        """
        offset = (page_no - 1) * page_size
        return await NoticeCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "asc"}],
            search=search_to_dict(search),
            out_schema=NoticeOutSchema,
        )

    async def available_list(self, limit: int = 10) -> list[NoticeOutSchema]:
        """已发布公告列表（C 端只读公告页 / 首页展示用）

        两个关键点：
        1. **口径以管理端用法为准**：公告状态在管理端是「0 启用 / 1 停用」（2 归档预留），
           运营「发送」出来的公告就是 `status=0`。按模型注释里的「0 草稿 / 1 已发布」过滤，
           会让 C 端一条都收不到（已实际复现）。
        2. **绕过 CRUD 的数据权限**：公告是面向所有人的公开内容，而 `CRUDBase` 会给非超管
           叠加 `created_id = 当前用户` 的数据范围条件——C 端用户据此查询会一条都看不到。
           公开内容必须显式直查，而不是靠用户身份兜底。
        """
        stmt = (
            select(NoticeModel)
            .where(
                NoticeModel.status == NOTICE_STATUS_ENABLED,
                NoticeModel.is_deleted == false(),
            )
            .order_by(NoticeModel.id.desc())
            .limit(limit)
            # NoticeOutSchema 含 created_by/updated_by，必须预加载，否则异步序列化触发 MissingGreenlet
            .options(
                selectinload(NoticeModel.created_by),
                selectinload(NoticeModel.updated_by),
            )
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [NoticeOutSchema.model_validate(row) for row in rows]

    def _enabled_condition(self):
        """C 端可见公告的统一条件：启用(0) 且未删除"""
        return (NoticeModel.status == NOTICE_STATUS_ENABLED, NoticeModel.is_deleted == false())

    async def unread_count(self, user_id: int) -> int:
        """当前用户的未读公告数 = 启用公告总数 − 我读过的（只算仍然启用的）"""
        read_ids = select(NoticeReadModel.notice_id).where(NoticeReadModel.user_id == user_id)
        stmt = select(func.count(NoticeModel.id)).where(*self._enabled_condition(), NoticeModel.id.not_in(read_ids))
        return int((await self.db.scalar(stmt)) or 0)

    async def read_ids(self, user_id: int) -> list[int]:
        """当前用户已读的公告 id 列表（供列表页标未读圆点）"""
        rows = await self.db.scalars(select(NoticeReadModel.notice_id).where(NoticeReadModel.user_id == user_id))
        return [int(x) for x in rows.all()]

    async def mark_read(self, user_id: int, notice_ids: list[int] | None = None) -> int:
        """标记已读（传 None 表示全部启用公告），返回剩余未读数。

        只记录仍然存在的启用公告；重复标记靠唯一约束兜底，已存在就跳过。
        """
        stmt = select(NoticeModel.id).where(*self._enabled_condition())
        if notice_ids:
            stmt = stmt.where(NoticeModel.id.in_(notice_ids))
        target_ids = [int(x) for x in (await self.db.scalars(stmt)).all()]
        if target_ids:
            existing = set(await self.read_ids(user_id))
            now = datetime.now(UTC)
            for notice_id in target_ids:
                if notice_id in existing:
                    continue
                self.db.add(NoticeReadModel(user_id=user_id, notice_id=notice_id, read_at=now))
            await self.db.flush()
        return await self.unread_count(user_id)

    async def create(self, data: NoticeCreateSchema) -> NoticeOutSchema:
        """创建公告

        参数:
        - data (NoticeCreateSchema): 公告创建模型

        返回:
        - NoticeOutSchema: 公告响应模型
        """
        notice = await NoticeCRUD(self.auth, self.db).get(notice_title=data.notice_title)
        if notice:
            raise CustomException(msg="创建失败，该数据已存在")
        notice_obj = await NoticeCRUD(self.auth, self.db).create(data=data)
        await _broadcast_notice_update()
        return await self.detail(id=notice_obj.id)

    async def update(self, id: int, data: NoticeUpdateSchema) -> NoticeOutSchema:
        """更新公告

        参数:
        - id (int): 公告 ID
        - data (NoticeUpdateSchema): 公告更新模型

        返回:
        - NoticeOutSchema: 公告响应模型
        """
        _ = await NoticeCRUD(self.auth, self.db).get_or_404(id=id, msg="更新失败，该数据不存在")
        exist_notice = await NoticeCRUD(self.auth, self.db).get(notice_title=data.notice_title)
        if exist_notice and exist_notice.id != id:
            raise CustomException(msg="更新失败，标题已存在")
        await NoticeCRUD(self.auth, self.db).update(id=id, data=data)
        await _broadcast_notice_update()
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除公告

        参数:
        - ids (list[int]): 公告 ID 列表
        """
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        notices = await NoticeCRUD(self.auth, self.db).get_list(search={"id": ("in", ids)})
        notice_map = {n.id: n for n in notices}
        for nid in ids:
            if nid not in notice_map:
                raise CustomException(msg="删除失败，该数据不存在")
        await NoticeCRUD(self.auth, self.db).delete(ids=ids)

    async def set_available(self, data: BatchSetAvailable) -> None:
        """批量启用/禁用公告

        参数:
        - data (BatchSetAvailable): 批量设置状态模型
        """
        await NoticeCRUD(self.auth, self.db).set(ids=data.ids, status=data.status)
        await _broadcast_notice_update()

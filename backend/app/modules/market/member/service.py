"""C 端成员档案服务层：建档（幂等）、查询、启停。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.utils.common_util import search_to_dict

from ..enums import MemberStatus
from ..numbering import NumberPrefix, next_code
from .brief import load_user_briefs
from .crud import MemberCRUD
from .model import MemberModel
from .schema import MemberCreateSchema, MemberOutSchema, MemberQueryParam, MemberUpdateSchema


class MemberService:
    """C 端成员档案服务。

    「是不是 C 端」的唯一判据是**有没有这条档案**，不看角色：角色是多对多的权限概念，
    一个运营也可能兼有普通角色，用它推断身份会得出模棱两可的结果。
    """

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def ensure_for_user(self, user_id: int) -> MemberModel:
        """幂等建档：已有档案直接返回，没有则分配成员编号并创建。

        并发下两个请求可能同时判定「不存在」，靠 ``user_id`` 唯一约束兜底——捕获冲突后
        回查一次，以拿到档案为准（与第三方登录自动注册同一处理方式）。
        """
        crud = MemberCRUD(self.auth, self.db)
        existing = await crud.get(user_id=user_id)
        if existing:
            return existing
        try:
            # 用 SAVEPOINT 包住建档：并发冲突时只回滚这一步，外层事务仍可用，
            # 否则唯一约束报错会让整个事务进入 aborted 状态，回查档案也会一起失败（500）
            async with self.db.begin_nested():
                return await crud.create(
                    data={
                        "user_id": user_id,
                        "member_no": await next_code(self.db, NumberPrefix.MEMBER),
                        "status": MemberStatus.ACTIVE.value,
                    }
                )
        except Exception:
            # 唯一约束冲突（并发建档）或流水号异常：以库里已有档案为准
            retry = await crud.get(user_id=user_id)
            if retry is None:
                raise
            return retry

    async def ensure_active(self, user_id: int) -> MemberModel:
        """C 端接口入口用：拿到（或创建）档案，并拒绝已停用的成员。"""
        member = await self.ensure_for_user(user_id)
        if member.status != MemberStatus.ACTIVE.value:
            raise CustomException(msg="该 C 端成员已停用，请联系运营")
        return member

    async def detail(self, id: int) -> MemberOutSchema:
        """查询成员档案详情。"""
        member = await MemberCRUD(self.auth, self.db).get_or_404(id=id)
        return await self._attach_user(MemberOutSchema.model_validate(member))

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: MemberQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[MemberOutSchema]:
        """分页查询成员档案（带用户摘要，前端不用自己反查 sys_user）。"""
        offset = (page_no - 1) * page_size
        result = await MemberCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=MemberOutSchema,
        )
        briefs = await load_user_briefs(self.db, [item.user_id for item in result.items])
        for item in result.items:
            item.user = briefs.get(item.user_id)
        return result

    async def create(self, data: MemberCreateSchema) -> MemberOutSchema:
        """运营手动把已有用户纳入 C 端（已建档则直接返回现有档案，视为幂等）。"""
        member = await self.ensure_for_user(user_id=data.user_id)
        if data.status != member.status:
            await MemberCRUD(self.auth, self.db).update(id=member.id, data={"status": data.status.value})
            member = await MemberCRUD(self.auth, self.db).get_or_404(id=member.id)
        return await self._attach_user(MemberOutSchema.model_validate(member))

    async def update(self, id: int, data: MemberUpdateSchema) -> MemberOutSchema:
        """调整成员状态（启用 / 停用）。"""
        await MemberCRUD(self.auth, self.db).get_or_404(id=id)
        await MemberCRUD(self.auth, self.db).update(id=id, data={"status": data.status.value})
        return await self.detail(id=id)

    async def _attach_user(self, member: MemberOutSchema) -> MemberOutSchema:
        briefs = await load_user_briefs(self.db, [member.user_id])
        member.user = briefs.get(member.user_id)
        return member

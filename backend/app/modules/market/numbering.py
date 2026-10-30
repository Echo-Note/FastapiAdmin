"""市场管理域 —— 业务编号生成规则。

所有业务实体的编号统一采用「类型前缀 + 数字」格式：``{PREFIX}-{NNN}``。
序号 ``NNN`` 从 1 起独立递增（至少 4 位，超过 9999 自动扩展位数），
由后端在创建时自动生成，前端不提供输入。前缀与实体映射见 ``NumberPrefix``。

并发与分布式安全：
序号取自 ``market_number_counter`` 计数器表，通过单条
``INSERT ... ON CONFLICT DO UPDATE ... RETURNING`` 原子自增。PostgreSQL 下该语句
依赖主键冲突 + 行级锁保证「读改写」原子性——并发事务与多实例（分布式）场景中，
同一前缀的序号严格递增、不重复；事务回滚时计数一并回滚，序号不产生空洞。
"""

from sqlalchemy import BigInteger, String, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import MappedBase


class NumberPrefix:
    """市场业务实体编号前缀常量。"""

    CATEGORY = "CAT"  # 一级任务分类（market_task_category）
    TEMPLATE = "TPL"  # 二级任务模板（market_task_template）
    ITEM = "ITEM"  # 三级任务（market_task_item）
    COMPANY = "CO"  # 医药公司（market_company）
    PROJECT = "PRJ"  # 项目（market_project）
    TASK = "TK"  # 任务实例流水号（market_task.task_no）
    ARCHIVE = "ARC"  # 成果档案编号（market_submission.archive_no）


class MarketNumberCounterModel(MappedBase):
    """市场业务编号计数器表（每个前缀一行，原子递增）。"""

    __tablename__: str = "market_number_counter"
    __table_args__: dict[str, str] = {"comment": "市场业务编号计数器表"}

    prefix: Mapped[str] = mapped_column(String(16), primary_key=True, comment="编号前缀")
    current_value: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, comment="当前已分配序号")


async def next_code(db: AsyncSession, prefix: str) -> str:
    """原子生成下一个编号 ``{prefix}-{NNN}``。

    用 SQLAlchemy PostgreSQL 方言的 ``INSERT ... ON CONFLICT DO UPDATE ... RETURNING``
    对 ``prefix`` 行做原子自增并返回本次分配的序号，并发与分布式（多实例）场景下
    序号严格递增不重复。

    :param db: 数据库会话
    :param prefix: 编号前缀（见 ``NumberPrefix``）
    :return: 生成的编号字符串，如 ``CAT-0001``
    """
    stmt = (
        pg_insert(MarketNumberCounterModel)
        .values(prefix=prefix, current_value=1)
        .on_conflict_do_update(
            index_elements=[MarketNumberCounterModel.prefix],
            set_={"current_value": MarketNumberCounterModel.current_value + 1},
        )
        .returning(MarketNumberCounterModel.current_value)
    )
    result = await db.execute(stmt)
    seq = result.scalar_one()
    return f"{prefix}-{seq:04d}"


async def sync_counter(db: AsyncSession, prefix: str, seq: int) -> None:
    """同步计数器到至少 ``seq``（不回退）。

    用于 seed 预置编号后对齐计数器，避免后续自动生成的编号与预置编号冲突。
    使用 ``GREATEST`` 保证并发/多实例下计数器只增不减。

    :param db: 数据库会话
    :param prefix: 编号前缀（见 ``NumberPrefix``）
    :param seq: 该前缀已占用的最大序号
    """
    stmt = (
        pg_insert(MarketNumberCounterModel)
        .values(prefix=prefix, current_value=seq)
        .on_conflict_do_update(
            index_elements=[MarketNumberCounterModel.prefix],
            set_={"current_value": func.greatest(MarketNumberCounterModel.current_value, seq)},
        )
    )
    await db.execute(stmt)

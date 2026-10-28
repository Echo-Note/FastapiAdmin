"""初始化 COS 对象存储节点（幂等）。

功能：创建/更新 COS 存储源节点，默认设为默认存储源（同时取消其它默认）。

环境变量：
    COS_SECRET_ID      子账号 SecretId（必填）
    COS_SECRET_KEY     子账号 SecretKey（必填）
    COS_BUCKET         桶名（默认 foxwork-prod-1516998879）
    COS_REGION         区域（默认 ap-chongqing）
    COS_APPID          AppId（默认 1516998879）
    COS_NODE_NAME      存储源节点名（默认「COS 生产存储」）
    COS_DESCRIPTION    存储源节点描述（默认「生产 COS 存储（子账号 foxwork）」）
    COS_AS_DEFAULT     是否设为默认存储源，1/0（默认 1）

执行（后端容器内）：
    COS_SECRET_ID=xxx COS_SECRET_KEY=xxx python init_storage_node.py
"""
import asyncio

from sqlalchemy import select

from app.modules.task.storage.core.base import encrypt_password
from app.modules.task.storage.node.model import StorageNodeModel

from base import async_db_session, env


async def main() -> None:
    node_name = env("COS_NODE_NAME", "COS 生产存储")
    description = env("COS_DESCRIPTION", "生产 COS 存储（子账号 foxwork）")
    secret_id = env("COS_SECRET_ID", "")
    secret_key = env("COS_SECRET_KEY", "")
    bucket = env("COS_BUCKET", "foxwork-prod-1516998879")
    region = env("COS_REGION", "ap-chongqing")
    appid = env("COS_APPID", "1516998879")
    as_default = env("COS_AS_DEFAULT", "1") == "1"

    if not secret_id or not secret_key:
        raise SystemExit("缺少 COS_SECRET_ID / COS_SECRET_KEY 环境变量")

    async with async_db_session() as db:
        node = (
            await db.execute(
                select(StorageNodeModel).where(StorageNodeModel.name == node_name)
            )
        ).scalar_one_or_none()

        if node is None:
            node = StorageNodeModel(
                name=node_name,
                protocol="cos",
                port=443,
                username=secret_id,
                password=encrypt_password(secret_key),
                bucket=bucket,
                region=region,
                is_secure=True,
                scheme="https",
                advanced_config={"appid": appid},
                is_default=False,
                status=0,
                description=description,
            )
            db.add(node)
            print(f"新建存储源节点：{node_name}")
        else:
            node.username = secret_id
            node.password = encrypt_password(secret_key)
            node.bucket = bucket
            node.region = region
            node.advanced_config = {"appid": appid}
            node.status = 0
            print(f"更新已存在存储源节点：{node_name}")

        if as_default:
            # 先取消其它默认，再把本节点设为默认，保证唯一
            for r in (await db.execute(select(StorageNodeModel))).scalars().all():
                if r.is_default:
                    r.is_default = False
            node.is_default = True

        await db.commit()
        await db.refresh(node)
        print(f"存储源节点已就绪：id={node.id} is_default={node.is_default}")


if __name__ == "__main__":
    asyncio.run(main())

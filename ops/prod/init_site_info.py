"""初始化品牌标识与网站信息（幂等）。

根据企业工商信息（玄狐(重庆)人工智能科技有限公司）生成系统参数（sys_param）的
品牌标识与网站信息，覆盖 FastapiAdmin 默认值。

环境变量（.env，可选）：
    SITE_DOMAIN       站点域名（默认 admin.xfoxlab.com.cn）
    COMPANY_NAME      企业全称（默认 玄狐(重庆)人工智能科技有限公司）
    COMPANY_SHORT     企业简称（默认 玄狐）
    COPYRIGHT_YEAR    版权年份（默认 2026）

执行（后端容器内）：
    python init_site_info.py
"""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.system.params.model import ParamsModel

from base import async_db_session, env


def build_params() -> list[tuple[str, str, str, str]]:
    """构建品牌/网站信息参数列表：(config_key, config_name, config_value, description)。"""
    domain = env("SITE_DOMAIN", "admin.xfoxlab.com.cn")
    company = env("COMPANY_NAME", "玄狐(重庆)人工智能科技有限公司")
    short = env("COMPANY_SHORT", "玄狐")
    year = env("COPYRIGHT_YEAR", "2026")
    base = f"https://{domain}/api/v1/static/image"

    return [
        ("sys_name", "系统名称", f"{short}科技", "平台系统名称，用于登录页等界面展示"),
        ("login_title", "登录页标题", "医药市场管理服务平台", "登录页左侧面板主标题文案"),
        ("login_subtitle", "登录页副标题", f"{company} · 项目/任务/成果/结算一体化市场管理平台", "登录页左侧面板副标题文案"),
        ("copyright", "版权信息", f"Copyright © {year} {company} 版权所有", "页面底部版权信息"),
        ("keep_record", "备案号", "", "ICP备案号（未备案时留空）"),
        ("logo_url", "Logo URL", f"{base}/logo.svg", "平台Logo地址"),
        ("favicon", "Favicon 地址", f"{base}/favicon.ico", "浏览器标签栏图标地址"),
        ("login_bg", "登录背景图", f"{base}/background.svg", "登录页面背景图地址"),
        ("help_doc", "帮助文档地址", "", "帮助文档链接地址"),
        ("privacy", "隐私政策地址", "", "隐私政策链接地址"),
        ("clause", "用户协议地址", "", "用户协议链接地址"),
        ("git_code", "源码地址", "", "项目源码仓库地址"),
    ]


async def main() -> None:
    params = build_params()

    async with async_db_session() as db:
        existing = {
            p.config_key: p
            for p in (await db.execute(select(ParamsModel))).scalars().all()
        }
        created = 0
        updated = 0
        for key, name, value, desc in params:
            if key in existing:
                row = existing[key]
                row.config_name = name
                row.config_value = value
                row.description = desc
                row.status = 0
                updated += 1
            else:
                db.add(
                    ParamsModel(
                        config_name=name,
                        config_key=key,
                        config_value=value,
                        config_type=True,
                        status=0,
                        description=desc,
                    )
                )
                created += 1
        await db.commit()
        print(f"品牌/网站信息初始化完成：更新 {updated} 项，新建 {created} 项")


if __name__ == "__main__":
    asyncio.run(main())

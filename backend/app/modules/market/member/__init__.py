"""market 域 —— C 端成员档案。

本包同时承载两件相关但不同的事：

- ``model``：C 端身份来源（``market_member``，存在即 C 端）；
- ``brief``：运营端列表要展示的用户摘要（``{id, name, username, mobile}``），
  全域共享，结算 / 发放等出参都复用它。
"""

from .brief import MarketUserBriefSchema, load_user_briefs
from .model import MemberModel

__all__ = ["MarketUserBriefSchema", "MemberModel", "load_user_briefs"]

# 安全策略（Security Policy）

本文档说明如何报告本项目的安全漏洞，以及哪些版本会收到安全修复。

## 支持的版本

本项目是 [FastapiAdmin](https://github.com/fastapiadmin/FastapiAdmin) v3.0.0（MIT 许可证）的私有二开版本，仅对当前活跃维护的分支提供安全修复：

| 分支 | 支持状态 |
| --- | --- |
| `refactor/xuanhu-v1.1`（当前主开发分支） | ✅ 受支持 |
| `feature/xuanhu` | ✅ 受支持 |
| `master`（上游同步基线） | ⚠️ 仅同步上游，不在本仓库单独修复 |

> 上游基座的安全修复请关注 [fastapiadmin/FastapiAdmin](https://github.com/fastapiadmin/FastapiAdmin)；本仓库会随 `upstream/master` 的合并持续跟进。

## 如何报告安全漏洞

**请不要在公开的 Issue 中披露安全漏洞**，以免被恶意利用。请通过以下私密渠道报告：

1. **GitHub 私有安全通告（推荐）**：仓库 `Security` → `Advisories` → `Report a vulnerability` 提交。
2. **邮箱**：<wadxf@live.com>

报告时请尽量包含以下信息，便于我们快速定位与修复：

- 受影响的分支 / 版本；
- 漏洞描述与复现步骤（含最小复现代码或请求示例）；
- 影响范围与潜在危害；
- 你建议的修复方式（如有）。

## 响应与披露流程

- 收到报告后，我们会尽快确认并评估严重性；
- 修复完成并通过验证后，通过 GitHub 安全通告披露，并同步发布补丁；
- 我们会尽可能在安全通告中致谢报告者（如你愿意公开署名）。

## 免责声明

本项目依据 MIT 许可证「按原样」提供，不附带任何明示或暗示的担保。请自行评估使用本项目可能带来的安全与合规风险。

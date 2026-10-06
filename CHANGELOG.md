## v1.3.2 (2026-10-06)
- **修复**: 静态安全重构 `SkillMemory.query_experience`，彻底消除动态 SQL 拼接，满足 Sourcery-AI 审查规范。
- **强化**: 补全真·原子写入（`tempfile` 写入 + `fsync` 刷盘 + `os.replace` 原子替换），并实现快照备份（`.atomic_bak`）与 `dev_rollback_file` 一键回滚工具。
- **闭环**: 在 `WriteFileTool` 中真正接入 `query_experience` 历史避坑检索，形成前置经验诊断与自愈闭环。
- **修复**: 重构 `FileManager.write_file` 错误返回模型，严格校验底层真实成功状态，杜绝将写入失败误判为成功落库。

## [1.3.0] - 2026-10-06
### 新增特性 (由 日海 & 橙子汐 架构贡献)
- **AST 语法树前置拦截预检** (`utils/safety_ast.py`)：在写代码前进行语法树静态校验，拦截致命语法错误与高危底层调用。
- **SQLite 经验反思库** (`utils/skill_memory.py`)：持久化记录历史调试与迭代特征，避免同一类报错反复试错。
- **原子事务备份与回滚机制**：文件写入前自动创建快照，写入或加载失败时支持秒级还原。

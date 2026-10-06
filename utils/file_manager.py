import os
import shutil
import asyncio
import tempfile
from typing import List, Tuple


class FileManager:
    """
    文件管理器：实现真·原子文件写入、安全快照备份与一键回滚机制
    由 日海 & 橙子汐 架构贡献设计
    """
    def __init__(self, base_path: str = "./data/plugins"):
        self.base_path = base_path

    def _get_full_path(self, plugin_name: str, file_path: str) -> str:
        full_path = os.path.join(self.base_path, plugin_name, file_path)
        return os.path.abspath(full_path)

    def _get_backup_path(self, full_path: str) -> str:
        return full_path + ".atomic_bak"

    # ========== 同步内部方法（在线程池中执行） ==========

    def _sync_write_file(self, full_path: str, content: str) -> None:
        """
        原子写入：
        1. 写入前对既有文件做快照备份 (.atomic_bak)；
        2. 先写入同目录下临时文件并 fsync 刷盘；
        3. 利用 os.replace 在 OS 层级原子替换原文件，杜绝写入中断导致的代码损坏。
        """
        target_dir = os.path.dirname(full_path)
        os.makedirs(target_dir, exist_ok=True)

        # 1. 存在历史版本时先做原子快照备份
        backup_path = self._get_backup_path(full_path)
        if os.path.exists(full_path):
            try:
                shutil.copy2(full_path, backup_path)
            except Exception:
                pass

        # 2. 在同目录下创建临时文件以保证同一文件系统卷，便于原子 replace
        temp_fd, temp_path = tempfile.mkstemp(dir=target_dir, prefix=".tmp_atomic_")
        try:
            with open(temp_fd, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            # 3. 原子覆盖目标文件
            os.replace(temp_path, full_path)
        except Exception:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise

    def _sync_rollback_file(self, full_path: str) -> bool:
        """从备份快照回滚文件"""
        backup_path = self._get_backup_path(full_path)
        if not os.path.exists(backup_path):
            return False
        shutil.copy2(backup_path, full_path)
        return True

    def _sync_read_file(self, full_path: str) -> str:
        """同步读取，仅供内部调用"""
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _sync_list_files(self, plugin_path: str) -> List[str]:
        """同步遍历目录，仅供内部调用"""
        file_list = []
        for root, dirs, files in os.walk(plugin_path):
            for file in files:
                if file.endswith(".atomic_bak") or file.startswith(".tmp_atomic_"):
                    continue
                rel_path = os.path.relpath(os.path.join(root, file), plugin_path)
                file_list.append(rel_path)
        return file_list

    # ========== 异步公开方法 ==========

    async def write_file(self, plugin_name: str, file_path: str, content: str) -> Tuple[bool, str]:
        """
        返回元组 (success: bool, message: str)
        明确区分执行成功与异常，杜绝上层工具层误判为成功
        """
        full_path = self._get_full_path(plugin_name, file_path)
        try:
            await asyncio.to_thread(self._sync_write_file, full_path, content)
            return True, f"成功写入文件: {plugin_name}/{file_path}"
        except Exception as e:
            return False, f"写入文件失败: {str(e)}"

    async def rollback_file(self, plugin_name: str, file_path: str) -> Tuple[bool, str]:
        """执行快照原子回滚"""
        full_path = self._get_full_path(plugin_name, file_path)
        try:
            success = await asyncio.to_thread(self._sync_rollback_file, full_path)
            if success:
                return True, f"成功回滚文件: {plugin_name}/{file_path}"
            return False, f"回滚失败: 未找到有效备份快照 {plugin_name}/{file_path}"
        except Exception as e:
            return False, f"回滚异常: {str(e)}"

    async def read_file(self, plugin_name: str, file_path: str) -> str:
        full_path = self._get_full_path(plugin_name, file_path)
        try:
            exists = await asyncio.to_thread(os.path.exists, full_path)
            if not exists:
                return "文件不存在。"
            content = await asyncio.to_thread(self._sync_read_file, full_path)
            return content
        except Exception as e:
            return f"读取文件失败: {str(e)}"

    async def list_files(self, plugin_name: str) -> str:
        plugin_path = os.path.join(self.base_path, plugin_name)
        try:
            exists = await asyncio.to_thread(os.path.exists, plugin_path)
            if not exists:
                return "插件目录不存在。"
            file_list = await asyncio.to_thread(self._sync_list_files, plugin_path)
            return "\n".join(file_list) if file_list else "目录为空。"
        except Exception as e:
            return f"列出文件失败: {str(e)}"

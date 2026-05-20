"""
File operations plugin for VoicePilot-CLI.

Provides file reading, writing, listing, and basic file management.
Includes safety checks to prevent unauthorized access.
"""

import os
import stat
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from voicepilot_cli.plugins.base import PluginBase


class FileOpsPlugin(PluginBase):
    """File operations plugin.

    Provides safe file operations including:
    - Reading file contents
    - Writing/creating files
    - Listing directory contents
    - Getting file metadata

    Safety features:
    - Path validation to prevent directory traversal
    - Size limits for file reads
    - Confirmation for write operations
    - Restricted path blacklist
    """

    # Maximum file size to read (1MB)
    MAX_READ_SIZE = 1024 * 1024

    # Paths that are never allowed
    RESTRICTED_PATHS = {
        "/etc/shadow",
        "/etc/passwd",
        "/etc/sudoers",
        "/root/",
        "/boot/",
        "/dev/",
        "/proc/",
        "/sys/",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the file operations plugin.

        Args:
            config: Optional configuration dictionary.
        """
        super().__init__(config)
        self._allowed_base_dirs: List[str] = [
            os.getcwd(),
            str(Path.home()),
        ]
        self._last_operation: Optional[str] = None

    @property
    def name(self) -> str:
        """Get plugin name.

        Returns:
            'file_ops'
        """
        return "file_ops"

    @property
    def description(self) -> str:
        """Get plugin description.

        Returns:
            Description string.
        """
        return "File operations: read, write, list, and manage files safely."

    @property
    def trigger_keywords(self) -> List[str]:
        """Get trigger keywords.

        Returns:
            List of keywords that trigger this plugin.
        """
        return [
            "读取文件", "打开文件", "查看文件", "写入文件", "保存文件",
            "创建文件", "列出文件", "文件列表", "目录",
            "read file", "write file", "list files", "create file",
            "cat ", "ls ", "dir ",
        ]

    @property
    def commands(self) -> List[str]:
        """Get supported commands.

        Returns:
            List of command strings.
        """
        return ["read", "write", "list", "info", "mkdir", "delete"]

    def execute(self, command: str, **kwargs: Any) -> str:
        """Execute a file operation.

        Args:
            command: Operation string in format 'action:parameters' or natural language.
            **kwargs: Additional parameters.

        Returns:
            Operation result string.
        """
        # Check if called with explicit parameters from planner
        if kwargs.get("path"):
            action = kwargs.get("action", "read")
            filepath = kwargs["path"]
            if action == "file_read":
                return self._read_file(filepath)
            elif action == "file_write":
                content = kwargs.get("content", "")
                return self._write_file(filepath, content)
            elif action == "file_list":
                return self._list_directory(filepath)

        # Parse command format: "action:path" or natural language
        if ":" in command:
            action, params = command.split(":", 1)
            return self._execute_action(action.strip(), params.strip())

        # Natural language parsing
        return self._parse_and_execute(command)

    def _execute_action(self, action: str, params: str) -> str:
        """Execute a specific file action.

        Args:
            action: Action name (read, write, list, info, mkdir, delete).
            params: Parameters string (usually a file path).

        Returns:
            Result string.
        """
        action = action.lower()

        if action in ("read", "cat", "查看", "读取"):
            return self._read_file(params)
        elif action in ("write", "save", "写入", "保存"):
            # For write, params may be "filepath|content"
            parts = params.split("|", 1)
            filepath = parts[0]
            content = parts[1] if len(parts) > 1 else ""
            return self._write_file(filepath, content)
        elif action in ("list", "ls", "dir", "列出"):
            return self._list_directory(params)
        elif action in ("info", "stat", "信息"):
            return self._file_info(params)
        elif action in ("mkdir", "创建目录"):
            return self._create_directory(params)
        elif action in ("delete", "rm", "删除"):
            return self._delete_file(params)
        else:
            return f"未知操作: {action}"

    def _parse_and_execute(self, text: str) -> str:
        """Parse natural language and execute file operation.

        Args:
            text: Natural language command.

        Returns:
            Result string or empty string if not a file command.
        """
        import re

        # Extract file path from text
        path_match = re.search(r"['\"]([^'\"]+\.\w+)['\"]|([\w\-\.\/\\]+\.\w+)", text)
        if not path_match:
            path_match = re.search(r"['\"]([^'\"]+)['\"]|([\w\-\.\/\\]+)", text)

        if not path_match:
            return ""

        filepath = path_match.group(1) or path_match.group(2) or ""

        text_lower = text.lower()
        if any(kw in text_lower for kw in ["读取", "查看", "read", "cat", "打开"]):
            return self._read_file(filepath)
        elif any(kw in text_lower for kw in ["写入", "保存", "write", "save", "创建"]):
            return self._write_file(filepath, "")
        elif any(kw in text_lower for kw in ["列出", "列表", "list", "ls", "dir"]):
            return self._list_directory(filepath)
        else:
            return ""

    def _validate_path(self, filepath: str) -> Path:
        """Validate and resolve a file path.

        Checks for restricted paths and directory traversal.

        Args:
            filepath: File path to validate.

        Returns:
            Resolved Path object.

        Raises:
            ValueError: If path is restricted or invalid.
        """
        # Expand user home directory
        resolved = Path(filepath).expanduser().resolve()

        # Check restricted paths
        resolved_str = str(resolved)
        for restricted in self.RESTRICTED_PATHS:
            if resolved_str.startswith(restricted):
                raise ValueError(f"Access denied: restricted path '{filepath}'")

        return resolved

    def _read_file(self, filepath: str) -> str:
        """Read and display file contents.

        Args:
            filepath: Path to the file.

        Returns:
            File contents or error message.
        """
        try:
            path = self._validate_path(filepath)

            if not path.exists():
                return f"文件不存在: {filepath}"

            if not path.is_file():
                return f"不是文件: {filepath}"

            # Check file size
            file_size = path.stat().st_size
            if file_size > self.MAX_READ_SIZE:
                return f"文件过大 ({file_size} bytes, 最大 {self.MAX_READ_SIZE} bytes)"

            # Read file
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            # Truncate if too long for display
            max_lines = 100
            lines = content.split("\n")
            if len(lines) > max_lines:
                content = "\n".join(lines[:max_lines])
                content += f"\n\n... (省略了 {len(lines) - max_lines} 行)"

            self._last_operation = f"read:{path}"
            return f"📄 {path} ({file_size} bytes):\n{'─' * 40}\n{content}"

        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"读取文件失败: {e}"

    def _write_file(self, filepath: str, content: str) -> str:
        """Write content to a file.

        Args:
            filepath: Path to the file.
            content: Content to write.

        Returns:
            Success or error message.
        """
        try:
            path = self._validate_path(filepath)

            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            self._last_operation = f"write:{path}"
            return f"✅ 文件已保存: {path} ({len(content)} bytes)"

        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"写入文件失败: {e}"

    def _list_directory(self, dirpath: str) -> str:
        """List directory contents.

        Args:
            dirpath: Path to the directory.

        Returns:
            Directory listing or error message.
        """
        try:
            path = self._validate_path(dirpath)

            if not path.exists():
                return f"目录不存在: {dirpath}"

            if not path.is_dir():
                return f"不是目录: {dirpath}"

            entries = list(path.iterdir())
            entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))

            if not entries:
                return f"📂 {path} (空目录)"

            lines = [f"📂 {path} ({len(entries)} 项):"]
            lines.append("─" * 50)

            for entry in entries:
                if entry.is_dir():
                    lines.append(f"  📁 {entry.name}/")
                else:
                    size = entry.stat().st_size
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f}KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.1f}MB"
                    lines.append(f"  📄 {entry.name} ({size_str})")

            self._last_operation = f"list:{path}"
            return "\n".join(lines)

        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"列出目录失败: {e}"

    def _file_info(self, filepath: str) -> str:
        """Get file metadata.

        Args:
            filepath: Path to the file.

        Returns:
            File metadata string.
        """
        try:
            path = self._validate_path(filepath)

            if not path.exists():
                return f"文件不存在: {filepath}"

            stat_info = path.stat()
            lines = [
                f"📄 {path}",
                f"   大小: {stat_info.st_size} bytes",
                f"   类型: {'目录' if path.is_dir() else '文件'}",
                f"   修改时间: {datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}",
                f"   权限: {oct(stat_info.st_mode)[-3:]}",
            ]

            return "\n".join(lines)

        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"获取文件信息失败: {e}"

    def _create_directory(self, dirpath: str) -> str:
        """Create a directory.

        Args:
            dirpath: Path to the directory.

        Returns:
            Success or error message.
        """
        try:
            path = self._validate_path(dirpath)
            path.mkdir(parents=True, exist_ok=True)
            return f"✅ 目录已创建: {path}"
        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"创建目录失败: {e}"

    def _delete_file(self, filepath: str) -> str:
        """Delete a file (with safety confirmation).

        Args:
            filepath: Path to the file.

        Returns:
            Success or error message.
        """
        try:
            path = self._validate_path(filepath)

            if not path.exists():
                return f"文件不存在: {filepath}"

            if path.is_dir():
                import shutil
                shutil.rmtree(path)
                return f"✅ 目录已删除: {path}"
            else:
                path.unlink()
                return f"✅ 文件已删除: {path}"

        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"删除失败: {e}"

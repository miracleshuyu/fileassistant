from pathlib import Path
import shutil

from langchain_core.tools import tool

from directorytree import scan_directory


@tool
def list_files(folder_path: str):
    """
    查看指定文件夹当前这一层的文件和文件夹。
    不自动进入子文件夹。
    """

    path = Path(folder_path)

    if not path.exists():
        return "文件夹不存在。"

    if not path.is_dir():
        return "指定路径不是文件夹。"

    try:

        items = sorted(
            path.iterdir(),
            key=lambda x: (
                x.is_file(),
                x.name.lower()
            )
        )

        result = []

        for item in items:

            if item.is_dir():

                if item.name in {
                    ".git",
                    ".vscode",
                    "__pycache__"
                }:
                    continue

                result.append(
                    f"[文件夹] {item.name}"
                )

            else:

                result.append(
                    f"[文件] {item.name}"
                )

        if not result:
            return "文件夹为空。"

        return "\n".join(result)

    except OSError as e:

        return f"读取文件夹失败：{e}"


@tool
def read_file(file_path: str):
    """
    读取文本文件内容。
    用于 Agent 内部分析。
    """

    path = Path(file_path)

    if not path.exists():
        return "文件不存在。"

    if not path.is_file():
        return "指定路径不是文件。"

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return f.read()

    except UnicodeDecodeError:

        return "文件不是 UTF-8 文本文件，暂时无法读取。"

    except OSError as e:

        return f"读取文件失败：{e}"


@tool
def move_file(
    file_path: str,
    target_folder: str
):
    """
    将文件移动到指定文件夹。
    只有用户明确确认后才能调用。
    """

    source = Path(file_path)
    target = Path(target_folder)

    if not source.exists():
        return "源文件不存在。"

    if not source.is_file():
        return "源路径不是文件。"

    try:

        target.mkdir(
            parents=True,
            exist_ok=True
        )

        destination = target / source.name

        shutil.move(
            str(source),
            str(destination)
        )

        return (
            f"文件已移动：{source.name} "
            f"→ {target}"
        )

    except OSError as e:

        return f"移动文件失败：{e}"


@tool
def directory_tree(folder_path: str):
    """
    检查指定文件夹的目录结构，
    并利用历史记录判断哪些目录发生了变化。
    """

    return scan_directory(folder_path)
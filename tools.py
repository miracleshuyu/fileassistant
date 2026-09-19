from pathlib import Path
from langchain_core.tools import tool
import shutil


@tool
def list_files(folder_path: str) -> list[str]:
    """查看指定文件夹当前这一层的文件和子文件夹。"""

    folder = Path(folder_path)

    # 文件夹不存在
    if not folder.exists():
        return [f"错误：文件夹不存在：{folder_path}"]

    # 路径不是文件夹
    if not folder.is_dir():
        return [f"错误：这不是一个文件夹：{folder_path}"]

    items = []

    # 只查看当前这一层
    # 不自动进入子文件夹
    for item in folder.iterdir():

        if item.is_file():
            items.append(
                f"[文件] {item.name} | 路径：{item}"
            )

        elif item.is_dir():
            items.append(
                f"[文件夹] {item.name} | 路径：{item}"
            )

    # 文件夹为空
    if not items:
        return ["这个文件夹是空的。"]

    return items


@tool
def read_file(file_path: str) -> str:
    """读取指定文本文件的内容。"""

    file_path = Path(file_path)

    # 文件不存在
    if not file_path.exists():
        return f"错误：文件不存在：{file_path}"

    # 不是文件
    if not file_path.is_file():
        return f"错误：这不是一个文件：{file_path}"

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            content = file.read()

        return content

    except UnicodeDecodeError:

        return (
            f"错误：无法使用 UTF-8 读取文件：{file_path}。"
            "这个文件可能不是 UTF-8 编码的文本文件。"
        )

    except Exception as e:

        return f"读取文件时发生错误：{e}"


@tool
def move_file(file_path: str, target_folder: str) -> str:
    """将指定文件移动到目标文件夹。"""

    file_path = Path(file_path)
    target_folder = Path(target_folder)

    # 源文件不存在
    if not file_path.exists():
        return f"错误：文件不存在：{file_path}"

    # 只能移动文件
    if not file_path.is_file():
        return f"错误：只能移动文件，不能移动文件夹：{file_path}"

    # 创建目标文件夹
    target_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    # 目标路径
    target_path = target_folder / file_path.name

    try:

        shutil.move(
            str(file_path),
            str(target_path)
        )

        return f"文件已移动到：{target_path}"

    except Exception as e:

        return f"移动文件时发生错误：{e}"
from pathlib import Path
import json


# 不参与目录扫描的文件夹
IGNORED_DIRS = {
    ".git",
    ".vscode",
    "__pycache__"
}

# 历史记录文件
HISTORY_FILE = Path("tree.json")


def get_directory_signature(path: Path):
    """
    获取文件夹当前这一层的状态。

    只检查当前层，不递归进入子文件夹。
    """

    items = []

    try:
        children = sorted(
            path.iterdir(),
            key=lambda x: x.name.lower()
        )

        for child in children:

            # 文件夹
            if child.is_dir():

                if child.name in IGNORED_DIRS:
                    continue

                items.append({
                    "name": child.name,
                    "type": "directory"
                })

            # 文件
            else:

                try:
                    items.append({
                        "name": child.name,
                        "type": "file",
                        "size": child.stat().st_size
                    })

                except OSError:
                    pass

    except OSError:
        pass

    return items


def build_tree_data(path: Path):
    """
    递归建立完整目录树。

    第一次扫描，或者某个目录发生变化时使用。
    """

    node = {
        "name": path.name,
        "type": "directory",
        "path": str(path.resolve()),
        "children": []
    }

    try:

        children = sorted(
            path.iterdir(),
            key=lambda x: (x.is_file(), x.name.lower())
        )

        for child in children:

            # 文件夹
            if child.is_dir():

                if child.name in IGNORED_DIRS:
                    continue

                node["children"].append(
                    build_tree_data(child)
                )

            # 文件
            else:

                try:

                    node["children"].append({
                        "type": "file",
                        "path": str(child.resolve()),
                        "size": child.stat().st_size
                    })

                except OSError:
                    pass

    except OSError:
        pass

    return node


def collect_directory_signatures(root: Path):
    """
    收集所有文件夹当前这一层的状态。

    注意：
    这里只检查文件夹的一层，不建立完整目录树。
    """

    signatures = {}

    def scan(current: Path):

        current_path = str(current.resolve())

        signatures[current_path] = get_directory_signature(
            current
        )

        try:

            for child in current.iterdir():

                if child.is_dir():

                    if child.name in IGNORED_DIRS:
                        continue

                    scan(child)

        except OSError:
            pass

    scan(root)

    return signatures


def load_history():
    """
    读取历史记录。
    """

    if not HISTORY_FILE.exists():
        return None

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except (json.JSONDecodeError, OSError):

        return None


def save_history(
    folder_path,
    tree,
    signatures
):
    """
    保存目录树和目录状态历史。
    """

    data = {
        "folder_path": str(
            Path(folder_path).resolve()
        ),
        "tree": tree,
        "directory_signatures": signatures
    }

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


def find_changed_directories(
    old_signatures,
    new_signatures
):
    """
    比较新旧目录状态。

    返回发生变化的文件夹。
    """

    changed = []

    all_paths = (
        set(old_signatures)
        | set(new_signatures)
    )

    for path in all_paths:

        old = old_signatures.get(path)
        new = new_signatures.get(path)

        # 新增文件夹
        if old is None:
            changed.append(path)

        # 删除文件夹
        elif new is None:
            changed.append(path)

        # 当前层内容发生变化
        elif old != new:
            changed.append(path)

    return changed


def find_minimal_changed_directories(
    changed_directories
):
    """
    去掉重复的父目录。

    例如：

    D:\\study
    D:\\study\\python
    D:\\study\\python\\test

    如果三个都发生变化，
    只保留最底层需要重新扫描的目录。
    """

    paths = sorted(
        [Path(x) for x in changed_directories],
        key=lambda x: len(x.parts)
    )

    result = []

    for current in paths:

        is_contained = False

        for parent in result:

            try:

                current.relative_to(parent)

                is_contained = True
                break

            except ValueError:
                pass

        if not is_contained:
            result.append(current)

    return [
        str(path)
        for path in result
    ]


def replace_node(
    tree,
    target_path,
    new_node
):
    """
    在旧目录树中找到指定目录，
    用新的目录节点替换它。
    """

    target_path = str(
        Path(target_path).resolve()
    )

    current_path = str(
        Path(tree["path"]).resolve()
    )

    # 当前节点就是目标
    if current_path == target_path:

        tree.clear()
        tree.update(new_node)

        return True

    # 只有目录才有 children
    for child in tree.get("children", []):

        if child.get("type") != "directory":
            continue

        child_path = str(
            Path(child["path"]).resolve()
        )

        if child_path == target_path:

            index = tree["children"].index(child)

            tree["children"][index] = new_node

            return True

        if replace_node(
            child,
            target_path,
            new_node
        ):

            return True

    return False


def remove_node(
    tree,
    target_path
):
    """
    从目录树中删除指定目录。
    """

    target_path = str(
        Path(target_path).resolve()
    )

    children = tree.get(
        "children",
        []
    )

    for child in children:

        if child.get("type") != "directory":
            continue

        child_path = str(
            Path(child["path"]).resolve()
        )

        if child_path == target_path:

            children.remove(child)

            return True

        if remove_node(
            child,
            target_path
        ):

            return True

    return False


def update_changed_directory(
    tree,
    directory_path
):
    """
    重新扫描一个发生变化的目录。

    如果目录还存在：
        重新建立这个目录的子树。

    如果目录已经删除：
        从历史树中删除它。
    """

    path = Path(directory_path)

    if path.exists() and path.is_dir():

        new_node = build_tree_data(path)

        # 如果就是根目录
        if str(
            Path(tree["path"]).resolve()
        ) == str(path.resolve()):

            tree.clear()
            tree.update(new_node)

        else:

            replace_node(
                tree,
                path,
                new_node
            )

    else:

        remove_node(
            tree,
            path
        )


def scan_directory(folder_path):
    """
    增量扫描目录。

    第一次：
        完整扫描并建立历史。

    后续：
        先检查目录当前层状态。

        没有变化：
            不重新建立完整目录树。

        有变化：
            只重新扫描发生变化的目录。
    """

    root = Path(folder_path).resolve()


    # 基本检查
    # ========

    if not root.exists():

        return {
            "status": "error",
            "message": "文件夹不存在"
        }

    if not root.is_dir():

        return {
            "status": "error",
            "message": "指定路径不是文件夹"
        }

   
    # 读取历史
    # =======

    history = load_history()

    
    # 第一次扫描
    # =========

    if history is None:

        tree = build_tree_data(root)

        signatures = collect_directory_signatures(
            root
        )

        save_history(
            root,
            tree,
            signatures
        )

        return {
            "status": "no_history",
            "message": "没有该文件夹的历史记录",
            "scanned": [
                str(root)
            ]
        }

    
    # 判断是不是同一个文件夹
    # ====================

    old_folder = history.get(
        "folder_path"
    )

    if old_folder != str(root):

        tree = build_tree_data(root)

        signatures = collect_directory_signatures(
            root
        )

        save_history(
            root,
            tree,
            signatures
        )

        return {
            "status": "no_history",
            "message": "没有该文件夹的历史记录",
            "scanned": [
                str(root)
            ]
        }

    
    # 获取历史数据
    # ===========

    old_tree = history.get(
        "tree",
        {}
    )

    old_signatures = history.get(
        "directory_signatures",
        {}
    )

    # 当前目录状态
    # ===========

    new_signatures = collect_directory_signatures(
        root
    )

  
    # 比较目录状态
    # ============

    changed_directories = find_changed_directories(
        old_signatures,
        new_signatures
    )

    
    # 完全没有变化
    # ===========

    if not changed_directories:

        return {
            "status": "unchanged",
            "message": "目录没有发生变化",
            "scanned": []
        }

    
    # 找到最小变化目录
    # ==============

    minimal_changed = find_minimal_changed_directories(
        changed_directories
    )

    
    # 复制历史目录树
    # =============

    tree = old_tree

   
    # 只更新发生变化的目录
    # ===================

    for directory_path in minimal_changed:

        update_changed_directory(
            tree,
            directory_path
        )

   
    # 保存新的历史
    # ============

    save_history(
        root,
        tree,
        new_signatures
    )

   
    # 统计变化
    # ========

    old_files = {}

    new_files = {}

    def collect_files(node, result):

        if node.get("type") == "file":

            result[node["path"]] = node

            return

        for child in node.get(
            "children",
            []
        ):

            collect_files(
                child,
                result
            )

    collect_files(
        old_tree,
        old_files
    )

    collect_files(
        tree,
        new_files
    )

    added = []
    deleted = []
    changed = []

    # 新增
    for path in new_files:

        if path not in old_files:

            added.append(path)

    # 删除
    for path in old_files:

        if path not in new_files:

            deleted.append(path)

    # 大小变化
    for path in old_files:

        if path in new_files:

            old_size = old_files[path].get(
                "size"
            )

            new_size = new_files[path].get(
                "size"
            )

            if old_size != new_size:

                changed.append(path)

    return {
        "status": "changed",
        "added": added,
        "deleted": deleted,
        "changed": changed,
        "changed_directories": minimal_changed,
        "scanned": minimal_changed
    }
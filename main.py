import os
import json

from openai import OpenAI

from tools import (
    list_files,
    read_file,
    move_file,
    directory_tree
)



# 1. 检查 API Key
# ===============

api_key = os.environ.get(
    "DEEPSEEK_API_KEY"
)

if not api_key:

    print(
        "错误：没有检测到 DEEPSEEK_API_KEY。"
    )

    print(
        "请先设置环境变量 DEEPSEEK_API_KEY。"
    )

    exit()



# 2. 创建 DeepSeek 客户端
# ======================

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)



# 3. Agent 工具
# =============

tools = [

    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "查看指定文件夹当前这一层的文件和文件夹，"
                "不会自动进入子文件夹。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "要查看的文件夹路径"
                    }
                },
                "required": [
                    "folder_path"
                ]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "读取文本文件内容，"
                "用于 Agent 内部分析。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径"
                    }
                },
                "required": [
                    "file_path"
                ]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": (
                "将文件移动到指定文件夹。"
                "只有用户明确输入“确定”后才能调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "要移动的文件路径"
                    },
                    "target_folder": {
                        "type": "string",
                        "description": "目标文件夹路径"
                    }
                },
                "required": [
                    "file_path",
                    "target_folder"
                ]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "directory_tree",
            "description": (
                "检查指定文件夹的目录结构，"
                "利用历史记录判断目录是否发生变化。"
                "如果发生变化，只重新扫描变化的目录。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "要检查的文件夹路径"
                    }
                },
                "required": [
                    "folder_path"
                ]
            }
        }
    }
]


# 4. 工具映射
# ==========

tool_map = {
    "list_files": list_files,
    "read_file": read_file,
    "move_file": move_file,
    "directory_tree": directory_tree
}


# 5. 系统提示词
# ============

system_prompt = """
你是一个文件整理助手。

你的任务是帮助用户查看、分析和整理文件。

你可以使用以下工具：

1. list_files
查看指定文件夹当前这一层的文件和文件夹。
不要自动进入子文件夹。

2. read_file
读取文本文件内容，用于内部分析。
除非用户主动要求，否则不要直接输出完整文件内容。

3. directory_tree
检查文件夹目录结构。
系统会保存历史目录状态。
再次检查时，会利用历史记录判断哪些目录发生变化，
没有变化的目录不会重新建立目录树，
发生变化的目录才会重新扫描。

4. move_file
移动文件。
这是一个具有修改文件系统权限的工具。
只有用户明确输入“确定”之后才能调用。

如果用户只是查看、分析或者检查文件，
不要调用 move_file。

如果用户需要整理文件：

先查看文件，
然后分析文件应该放在哪里，
向用户展示整理方案，
等待用户输入“确定”。

只有用户输入“确定”之后，
才能执行移动操作。

回答用户时使用简洁、自然的中文。

不要向用户展示内部 JSON、
工具调用过程或者程序代码。
"""


# ==========================
# 6. 对话历史
# ==========================

messages = [
    {
        "role": "system",
        "content": system_prompt
    }
]


# 7. 移动权限
# ===========

move_authorized = False



# 8. 启动 Agent
# =============

print(
    "助手：您好，我是文件整理助手。"
    "您需要整理哪个文件夹呢？"
)


while True:

    user_input = input("\n您：")

    if user_input.lower() in [
        "exit",
        "quit",
        "退出"
    ]:

        print("助手：再见！")
        break

   
    # 用户是否授权移动
    # ==============

    if user_input.strip() == "确定":

        move_authorized = True

    else:

        move_authorized = False

    messages.append({
        "role": "user",
        "content": user_input
    })

   
    # Agent 多轮工具调用
    # =================

    while True:

        try:

            response = client.chat.completions.create(
                model="deepseek-flash",
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

        except Exception as e:

            print(
                f"助手：调用模型失败：{e}"
            )

            break

        message = response.choices[0].message

        
        # 模型直接回答
        # ===========

        if not message.tool_calls:

            content = message.content or ""

            print(
                f"\n助手：{content}"
            )

            messages.append({
                "role": "assistant",
                "content": content
            })

            break

       
        # 保存 Assistant 工具调用
        # ======================

        assistant_message = {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": []
        }

        for tool_call in message.tool_calls:

            assistant_message[
                "tool_calls"
            ].append({

                "id": tool_call.id,

                "type": "function",

                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments
                }

            })

        messages.append(
            assistant_message
        )

        
        # 执行工具
        # =======

        for tool_call in message.tool_calls:

            tool_name = tool_call.function.name

            try:

                arguments = json.loads(
                    tool_call.function.arguments
                )

            except json.JSONDecodeError:

                result = "工具参数解析失败。"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

                continue

        
            # move 权限控制
            # ============
            if tool_name == "move_file":

                if not move_authorized:

                    result = (
                        "权限不足："
                        "用户还没有明确输入“确定”，"
                        "不能移动文件。"
                    )

                else:

                    try:

                        result = tool_map[
                            tool_name
                        ].invoke(arguments)

                    except Exception as e:

                        result = (
                            f"工具执行失败：{e}"
                        )

                    move_authorized = False

            else:

                try:

                    result = tool_map[
                        tool_name
                    ].invoke(arguments)

                except Exception as e:

                    result = (
                        f"工具执行失败：{e}"
                    )

            
            # Tool 结果
            # =========

            if not isinstance(result, str):

                result = json.dumps(
                    result,
                    ensure_ascii=False
                )

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })
import os
import json

from openai import OpenAI
from tools import list_files, read_file, move_file


# 检查 API Key
api_key = os.environ.get("DEEPSEEK_API_KEY")

if not api_key:
    print("错误：没有检测到 DEEPSEEK_API_KEY。")
    print('请先运行：$env:DEEPSEEK_API_KEY="你的API Key"')
    exit()


# 创建 DeepSeek 客户端
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)


# 定义工具
tools = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "查看指定文件夹当前这一层的文件和子文件夹，不会自动进入子文件夹。",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "要查看的文件夹完整路径"
                    }
                },
                "required": ["folder_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取指定文本文件的内容，用于内部分析，不要主动向用户展示原文。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "要读取的文本文件完整路径"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "将文件移动到目标文件夹。只有用户明确输入“确定”后才能使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "要移动的文件完整路径"
                    },
                    "target_folder": {
                        "type": "string",
                        "description": "目标文件夹完整路径"
                    }
                },
                "required": ["file_path", "target_folder"]
            }
        }
    }
]


# 工具映射
tool_map = {
    "list_files": list_files,
    "read_file": read_file,
    "move_file": move_file
}


# Agent 系统提示词
system_message = """
你是一个自然、简洁的文件整理助手。

你可以使用三个工具：

list_files：
查看指定文件夹当前这一层的文件和子文件夹。
不要自动进入子文件夹。
只有用户明确要求查看某个子文件夹时才进入。

read_file：
读取文本文件内容，用于内部分析。
除非用户明确要求，否则不要向用户展示文件原文。

move_file：
移动文件。
只有系统已经确认用户授权后才能使用。

整理流程：

1. 用户要求整理某个文件夹。
2. 使用 list_files 查看当前这一层。
3. 必要时使用 read_file 分析文本文件。
4. 根据文件名和文件内容制定整理方案。
5. 向用户展示完整整理方案。
6. 明确询问：

“确定吗？确定请输入‘确定’。”

7. 在用户输入“确定”之前，绝对不能调用 move_file。
8. 用户输入“确定”后，可以连续调用多个 move_file。
9. 不需要逐个询问文件。
10. 所有移动完成后，简洁告诉用户整理完成。

重要规则：

- 用户确认的是整个整理方案。
- 一次“确定”授权整个当前整理方案。
- 用户输入其他内容都不能获得移动权限。
- 只有程序确认用户输入完全等于“确定”时，才允许移动。
- 不要自己猜测用户是否确认。
- 不要因为用户说“可以”“好的”“没问题”等就移动文件。
- 如果用户没有输入“确定”，继续正常回答用户的问题。
- 用户可以在确认前修改方案。
- 如果用户要求修改方案，重新分析并展示完整的新方案。
- 修改方案后必须重新要求输入“确定”。
- 用户没有确认时，不得移动任何文件。

文件范围：

- 默认只整理用户指定文件夹当前这一层的文件。
- 不要自动修改已有子文件夹中的文件。
- 不要自动递归进入所有子文件夹。

交互：

- 程序启动后由助手主动询问用户：
“您好，我是文件整理助手。您需要整理哪个文件夹呢？”
- 不要让程序显示“你：”作为第一句话。
- 用户输入后正常进行多轮对话。
- 不要向用户展示工具名称。
- 不要展示工具参数。
- 不要展示工具返回结果。
- 不要展示内部分析过程。
- 不要默认生成复杂表格。
- 回答简洁自然。
"""


# 保存对话历史
messages = [
    {
        "role": "system",
        "content": system_message
    }
]


# 当前是否等待确认
waiting_for_confirmation = False

# 当前是否拥有移动权限
move_authorized = False


# Agent 工具循环
def run_agent():

    global waiting_for_confirmation
    global move_authorized

    while True:

        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=messages,
            tools=tools
        )

        message = response.choices[0].message

        # 保存 Assistant 消息
        messages.append(message)

        # 没有工具调用
        if not message.tool_calls:

            print("\n助手：" + (message.content or ""))
            break

        # 执行工具
        for tool_call in message.tool_calls:

            tool_name = tool_call.function.name

            arguments = json.loads(
                tool_call.function.arguments
            )

            tool = tool_map.get(tool_name)

            # 工具不存在
            if tool is None:

                result = f"错误：不存在工具 {tool_name}"

            # move_file 权限检查
            elif tool_name == "move_file" and not move_authorized:

                result = (
                    "错误：用户还没有输入“确定”，"
                    "不能执行文件移动。"
                )

            # 正常执行工具
            else:

                try:

                    result = tool.invoke(arguments)

                except Exception as e:

                    result = f"工具执行失败：{e}"

            # 返回工具结果
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result)
            })


# 开场
print("\n助手：您好，我是文件整理助手。您需要整理哪个文件夹呢？")


# 主对话循环
while True:

    user_input = input("\n您：").strip()

    # 退出
    if user_input.lower() in ["exit", "quit"]:

        print("\n助手：好的，再见。")
        break

    if not user_input:
        continue


    # 当前正在等待确认
    if waiting_for_confirmation:

        # 只有完全输入“确定”才授权
        if user_input == "确定":

            move_authorized = True
            waiting_for_confirmation = False

            messages.append({
                "role": "user",
                "content": "确定"
            })

            messages.append({
                "role": "system",
                "content": """
用户已经明确输入“确定”。

现在已经获得当前完整整理方案的移动授权。

请立即执行当前方案中的所有 move_file。
不要再次询问确认。
不要逐个询问文件。
"""
            })

            run_agent()

            # 本次整理结束，立即撤销权限
            move_authorized = False

            continue


        # 用户没有输入“确定”
        else:

            # 仍然把用户的问题交给 Agent
            messages.append({
                "role": "user",
                "content": user_input
            })

            run_agent()

            # 如果仍然需要确认，就继续等待
            waiting_for_confirmation = True

            continue


    # 普通用户输入
    messages.append({
        "role": "user",
        "content": user_input
    })

    run_agent()


    # 判断 Agent 是否提出了确认请求
    #
    # 这里不判断具体关键词，
    # 只在 Agent 明确询问用户确认时进入等待状态。
    #
    # 为了避免依赖自然语言，下面使用一个简单的判断。
    last_message = messages[-1]

    if hasattr(last_message, "content"):

        content = last_message.content or ""

        if (
            "确定吗" in content
            or "请输入“确定”" in content
            or '请输入"确定"' in content
        ):
            waiting_for_confirmation = True
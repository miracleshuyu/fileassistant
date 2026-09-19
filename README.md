文件整理助手

基于 DeepSeek API + Tool Calling 实现的文件整理 Agent，用于学习 Agent 的工具调用、数据流和权限控制。

一、主要功能
list_files：查看指定目录当前层级的文件和文件夹
read_file：读取文本文件内容供 Agent 分析
move_file：将文件移动到指定文件夹

二、数据流
用户输入
   ↓
DeepSeek Agent
   ↓
调用 Tool
   ↓
本地文件系统
   ↓
Tool 返回结果
   ↓
Agent 继续分析
   ↓
生成整理方案

Agent 支持根据 Tool 返回结果进行多轮 Tool Calling。


三、权限流

list_files 和 read_file 可以直接调用。

move_file 属于修改文件的操作，需要用户明确输入 “确定” 后才能执行。

整理方案
   ↓
询问用户确认
   ↓
用户输入“确定”
   ↓
获得移动权限
   ↓
执行 move_file
   ↓
整理完成
   ↓
撤销移动权限

一次“确定”授权当前完整整理方案，未确认时不会移动文件。


四、运行

设置 DeepSeek API Key：

$env:DEEPSEEK_API_KEY="你的API Key"

运行：

python main.py

注意：API Key 不要直接写入代码或上传到 GitHub。
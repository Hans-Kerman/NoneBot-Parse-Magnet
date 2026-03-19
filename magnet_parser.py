from pathlib import Path
from datetime import datetime
from typing import TextIO

from nonebot import on_message

from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.rule import Rule

from .parse_mag import extract_magnet_links

current_dir = Path(__file__).parent
magnet_dir = current_dir / "magnet"
if not magnet_dir.exists():
    magnet_dir.mkdir()

def has_forward_msg() -> Rule:
    async def _has_forward_msg(event: PrivateMessageEvent) -> bool:
        # 遍历消息段，查找 type 为 forward 的节点
        for seg in event.message:
            if seg.type == "forward":
                return True
        return False
    return Rule(_has_forward_msg)


message = on_message(rule=has_forward_msg())

@message.handle()
async def handle_forward(bot: Bot, event: PrivateMessageEvent):
    # 找到所有转发段
    forward_segs = [seg for seg in event.message if seg.type == "forward"]

    date_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = magnet_dir / f"{date_str}.txt"

    with open(filename, 'a', encoding='utf-8') as f:
        for seg in forward_segs:
            res_id = seg.data["id"]
            try:
                forward_data = await bot.get_forward_msg(id=res_id)
                await parse_forward_nodes(bot, forward_data.get("messages", []), f)
            except Exception as e:
                print(f"获取外层合并转发消息失败: {e}")
    
    # 防止因未提取到任何磁力链接生成空文件，导致调用 upload_private_file 报错 "rich media transfer failed"
    if filename.stat().st_size == 0:
        filename.unlink()  # 删除空文件
        await bot.send(event, "未在这条合并转发消息中找到任何磁力链接。")
        return

    try:
        await bot.call_api(
            "upload_private_file",
            user_id=event.user_id,
            file=str(filename.resolve()),
            name="test.txt"
        )
    except Exception as e:
        await bot.send(event, f"文件发送失败（可能受到框架/平台限制）：{e}")

async def parse_forward_nodes(bot:Bot, nodes: list, f: TextIO):
    """
    递归解析节点列表
    nodes 结构通常是: [{"content": Message, "sender": {...}}, ...]
    """
    for node in nodes:
        content = node.get("content") or node.get("message")

        if not content:
            continue

        if isinstance(content, str):
            parse_mag(content, f)
            continue
            
        if isinstance(content, dict) or not hasattr(content, '__iter__'):
            content = [content]

        for seg in content:
            if isinstance(seg, dict):
                seg_type = seg.get("type")
                seg_data = seg.get("data", {})
            else:
                seg_type = getattr(seg, "type", None)
                seg_data = getattr(seg, "data", {})

            if seg_type == "forward":
                # 在某些 Onebot 实现中（例如 go-cqhttp、NapCat 等），内层的合并转发消息
                # 不能通过 `get_forward_msg` 再次根据 ID 获取，而是直接附带了完整节点数据
                if "content" in seg_data:
                    # 如果有内层节点的实际数据，通常是一个新的 list
                    inner_content = seg_data["content"]
                    if isinstance(inner_content, list):
                        # 兼容不同实现包装：有些实现直接把节点塞在 content，有些包在 message
                        inner_nodes = [{"message": m} for m in inner_content] if inner_content and not isinstance(inner_content[0], dict) else inner_content
                        # 为了统一递归处理结构，把它包装成 node 列表的样子
                        if inner_content and isinstance(inner_content[0], dict) and "message" not in inner_content[0] and "content" not in inner_content[0] and "type" in inner_content[0]:
                           # 如果直接是 segment list，包装一下
                           inner_nodes = [{"message": inner_content}]
                        await parse_forward_nodes(bot, inner_nodes, f)
                else:
                    # 如果没有数据只有 ID，尝试获取。部分客户端可能会报错 1200，抓取并跳过
                    inner_res_id = seg_data.get("id")
                    if inner_res_id:
                        try:
                            inner_data = await bot.get_forward_msg(id=inner_res_id)
                            await parse_forward_nodes(bot, inner_data.get("messages", []), f)
                        except Exception as e:
                            print(f"获取内层合并转发消息失败: {e}")
            elif seg_type == "text":
                text_data = seg_data.get("text", "")
                if text_data:
                    parse_mag(text_data, f)

def parse_mag(text: str, f: TextIO):
    for mag in extract_magnet_links(text):
        print(mag, file=f)

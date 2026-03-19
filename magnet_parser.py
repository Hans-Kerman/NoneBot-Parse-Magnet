from pathlib import Path
from datetime import datetime
from typing import TextIO

from nonebot import on_message

from nonebot.adapters.onebot.v11 import Bot,Message
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
            forward_data = await bot.get_forward_msg(id=res_id)
            await parse_forward_nodes(bot, forward_data["messages"], f)
    
    await bot.call_api(
        "upload_private_file",
        user_id=event.user_id,
        file=str(filename.resolve()),
        name="test.txt"
    )

async def parse_forward_nodes(bot:Bot, nodes: list, f: TextIO):
    """
    递归解析节点列表
    nodes 结构通常是: [{"content": Message, "sender": {...}}, ...]
    """
    for node in nodes:
        content = node["content"]

        if not isinstance(content, Message):
            content = Message(content)

        for seg in content:
            if seg.type == "forward":
                inner_res_id = seg.data["id"]
                inner_data = await bot.get_forward_msg(id=inner_res_id)
                await parse_forward_nodes(bot, inner_data["messages"], f)
            elif seg.type == "text":
                text_data = seg.data["text"]
                parse_mag(text_data, f)

def parse_mag(text: str, f: TextIO):
    for mag in extract_magnet_links(text):
        print(mag, file=f)

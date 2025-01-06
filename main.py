from __future__ import annotations
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from config import api_id, api_hash
from telethon import TelegramClient
import time
from telethon import errors
from telethon.tl.custom import Message


class Grouped:
    id_: int | None = None
    message: str | None = None
    message_ids: list = []
    files: list = []

    def reset(self):
        self.id_ = None
        self.message = None
        self.message_ids = []
        self.files = []


async def copy_channel(client, source_chat_id, target_chat_id):
    messages = []
    id_map = {}
    grouped = Grouped()

    async for message in client.iter_messages(source_chat_id):
        print(f'\rMessage collecting: {message.id}', end='')
        messages.append(message)

    messages_reversed = list(reversed(messages))

    for message in messages_reversed:
        print(f'\rProcessing message: {message.id}', end='')
        try:
            await process_message(client, target_chat_id, message, grouped, id_map)
        except errors.FloodWaitError as e:
            print(f'Flood wait of {e.seconds} seconds required. Waiting...')
            time.sleep(e.seconds)
        except Exception as e:
            print(f'An error occurred: {e}')


async def process_message(client, target_chat_id, message, grouped, id_map):
    if not isinstance(message, Message):
        return

    if message.grouped_id is None:
        grouped_id_map = await send_grouped_messages(client, target_chat_id, grouped)
        id_map.update(grouped_id_map)
        if message.message == 'То ж репліка':
            pass
        reply_to = id_map.get(message.reply_to_msg_id, None)
        sent_message = await client.send_message(target_chat_id, message, reply_to=reply_to)
        id_map[message.id] = sent_message.id
    elif grouped.id_ == message.grouped_id:
        grouped.files.append(message)
    else:
        reply_to = id_map.get(message.reply_to_msg_id, None)
        await send_grouped_messages(client, target_chat_id, grouped, reply_to)
        grouped.id_ = message.grouped_id
        grouped.message_ids.append(message.id)
        grouped.files.append(message)
        grouped.message = message.message


async def send_grouped_messages(client, target_chat_id, grouped, reply_to=None):
    if grouped.id_ is None:
        return {}
    sent_messages = await client.send_message(target_chat_id, message=grouped.message,
                                              file=grouped.files,
                                              reply_to=reply_to)
    message_ids = [message.id for message in sent_messages]
    id_map = {old_id: new_id for old_id, new_id in zip(grouped.message_ids, message_ids)}
    grouped.reset()
    return id_map

async def get_channel_name_by_id(client, chat_id):
    try:
        full_channel = await client(GetFullChannelRequest(chat_id))
        return full_channel.chats[0].title
    except Exception as e:
        try:
            full_chat = await client(GetFullChatRequest(chat_id))
            return full_chat.chats[0].title
        except Exception as e:
            print(f"Error while getting name: {e}")
            return None




client = TelegramClient('userbot', api_id, api_hash)


async def main():
    while True:
        try:
            source_chat_id = int(input("Input source channel id: "))
            target_chat_id = int(input("Input target channel id: "))

            source_channel_name = await get_channel_name_by_id(client, source_chat_id)
            target_channel_name = await get_channel_name_by_id(client, target_chat_id)

            print(f"Source channel name: {source_channel_name}\n"
                  f"Target channel name: {target_channel_name}")

            if input("Input Y to continue or anything else to input id again: ").lower() == 'y':
                break
        except Exception as e:
            print(f"An exception occurred {e}")

    await copy_channel(client, source_chat_id, target_chat_id)

with client:
    client.loop.run_until_complete(main())

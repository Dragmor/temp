import vk_api
from aiogram import Bot, types
from aiogram.utils import exceptions
import asyncio
import sys
import textwrap
import json
#
import modules.logger as logger

class VKtoTelegram:
    def __init__(self, config):
        try:
            self.vk_token = config['vk_token']
            self.tg_token = config['tg_token']
            self.tg_chat_id = config['tg_chat_id']
            self.vk_group_id = config['vk_group_id']
            self.time_interval = config['interval']
            self.skip_first_post = config['skip_first_post']
            self.refresh_time = config['refresh_time'] # кол-во секунд перед проверкой группы ВК
        except Exception as error:
            logger.error(f"[vk2tg_poster] Error loading config in vk2tg_poster.py: {error}")
            return
        with open(r"modules\vk_to_tg_poster\last_post_date.txt", "r") as file:
            self.last_post_date = int(file.read()) # читаем дату последней публикации


    async def start(self):
        # Авторизуемся в VK
        vk_session = vk_api.VkApi(token=self.vk_token)
        vk = vk_session.get_api()

        while True:
            try:
                # Список всех постов
                all_posts = []

                # Обходим группу и получаем посты

                # если был вставлен полный адрес группы
                if "vk.com/" in self.vk_group_id:
                    self.vk_group_id = self.vk_group_id[self.vk_group_id.find("vk.com/")+7:]
                    if "/" in self.vk_group_id:
                        self.vk_group_id = self.vk_group_id[:self.vk_group_id.find("/")]
                # Получите информацию о группе
                group_info = vk.groups.getById(group_id=self.vk_group_id)
                # Получите ID группы
                group_id = group_info[0]['id']

                # Преобразование ТГ-адреса
                if self.tg_chat_id[0] != "@":
                    if "t.me/" in self.tg_chat_id:
                        self.tg_chat_id = self.tg_chat_id[self.tg_chat_id.find("t.me/")+5:]
                        if "/" in self.tg_chat_id:
                            self.tg_chat_id = self.tg_chat_id[:self.tg_chat_id.find("/")]
                    self.tg_chat_id = f"@{self.tg_chat_id}"

                # Создаем экземпляр бота Telegram
                bot = Bot(token=self.tg_token)

                # Получите информацию о канале по его @адресу
                chat = await bot.get_chat(self.tg_chat_id)

                # Извлеките название канала
                channel_name = chat.title
                channel_id = chat.id

                logger.debug("[vk2tg_poster] Starting grab for VK-group...")
                wall = vk.wall.get(owner_id=f"-{group_id}", count=100)
                post_count = wall["count"]
                all_posts.extend(wall["items"])
                temp_posts = []
                logger.debug("[vk2tg_poster] Last 100 posts grabbing complete!")


                # если нужно пропускать первый пост
                if self.skip_first_post and len(all_posts) > 1:
                    # срезаем первый пост
                    all_posts = all_posts[1:]
                
                counter = 1

                # Постим каждый пост в Telegram, начиная с конца списка
                for post in all_posts:
                    temp_date = post["date"] # когда пост был опубликован (integer)
                    
                    # если пост в вк новее даты поста в файле, то обновляем дату последнего поста
                    if temp_date > self.last_post_date:
                        temp_posts.append(post)

                    # если найден пост, более старый чем тот что в файле, завершаем цикл
                    else:
                        self.last_post_date = all_posts[0]["date"]
                        break

                if all_posts:
                    logger.debug(f"[vk2tg_poster] Start posts sending ({len(temp_posts)}) to TG")
                else:
                    logger.debug("[vk2tg_poster] Not new posts in group finded!")

                for post in reversed(temp_posts):

                    # print(f"{post}\n\n\n") # ДЛЯ ОТЛАДКИ
                    try:
                        text = post["text"]
                        # проверяем, репост-ли это, или публикация
                        if "copy_history" in post:
                            for attachments_search in post.get("copy_history", []):
                                if "attachments" in attachments_search:
                                    attachments = attachments_search.get("attachments", [])

                            if len(post["copy_history"]) > 0:
                                if "text" in post["copy_history"][0]:
                                    if post["copy_history"][0]["text"]:
                                        text += f'\n{post["copy_history"][0]["text"]}'
                        else:
                            attachments = post.get("attachments", [])
                        # print(attachments)
                        media = []
                        # Создаем сообщение с медиафайлами и текстом
                        message = text

                        for attachment in attachments:
                            if attachment["type"] == "photo":
                                sizes = attachment["photo"]["sizes"]
                                photo_url = sizes[-1]["url"]
                                media.append(types.InputMediaPhoto(media=photo_url))

                            elif attachment["type"] == "video":
                                video_url = f'https://vk.com/video_ext.php?oid={attachment["video"]["owner_id"]}&id={attachment["video"]["id"]}&hash={post["hash"]}'
                                text += f'\n📺{video_url} {attachment["video"]["title"]}'
                                # Поиск превью с максимальным разрешением
                                max_resolution = 0
                                for key in attachment["video"]:
                                    if key.startswith('photo_'):
                                        resolution = int(key.split('_')[1])
                                        if resolution > max_resolution:
                                            max_resolution = resolution
                                            max_resolution_url = attachment["video"][f"photo_{resolution}"]
                                if max_resolution_url:
                                    media.append(types.InputMediaPhoto(media=max_resolution_url))
                            elif attachment["type"] == "audio":
                                audio_name = f'\n🎵 {attachment["audio"]["artist"]} - {attachment["audio"]["title"]}'
                                text += f"{audio_name}"
                            # elif attachment
                            elif attachment["type"] == "link":
                                try:
                                    index = 0
                                    max_width = 0
                                    for img in attachment["link"]["photo"]["sizes"]:
                                        if img["width"] > max_width:
                                            max_width = img["width"]
                                            photo_url = attachment["link"]["photo"]["sizes"][index]["url"]
                                        index += 1

                                    media.append(types.InputMediaPhoto(media=photo_url))
                                except:
                                    logger.debug("[vk2tg_poster] Can't find attachment image!")
                                link_url = attachment["link"]["url"]
                                if link_url not in text:
                                    text += f"\n{link_url}"

                        if not text and media == []:
                            logger.debug("[vk2tg_poster] Post without content...")
                            continue
                        first_msg = True
                        # Разбиваем сообщение на несколько частей
                        message_parts = textwrap.wrap(text, width=1024, replace_whitespace=False)
                        # Если не обнаружено текстового сообщения
                        if message_parts == []:
                            for _ in range(50)
                                try:
                                    await bot.send_media_group(chat_id=self.tg_chat_id, media=media)
                                except exceptions.TelegramAPIError as e:
                                    logger.error(f"[vk2tg_poster] TG antispam system. Wait...")
                                    await asyncio.sleep(10)
                                    continue
                                else:
                                    break

                        for part in message_parts:
                            for _ in range(50): # 50 раз пытаемся опубликовать. Если не получилось - пропускаем
                                try:
                                    if first_msg == True and media != []:
                                        # Отправляем все медиа-объекты в одном сообщении
                                        media[0].caption = part
                                        await bot.send_media_group(chat_id=self.tg_chat_id, media=media)
                                        first_msg = False
                                    else:
                                        await bot.send_message(chat_id=self.tg_chat_id, text=part, parse_mode="HTML")
                                    await asyncio.sleep(5)  # Добавляем небольшую задержку между отправкой частей сообщения
                                except exceptions.TelegramAPIError as e:
                                    logger.error(f"[vk2tg_poster] TG antispam system. Wait...")
                                    await asyncio.sleep(10)
                                    continue
                                else:
                                    break

                        # Добавляем задержку
                        logger.info(f"[vk2tg_poster] Published: {counter}/{len(temp_posts)} post")
                        counter+=1
                        await asyncio.sleep(self.time_interval)
                    except Exception as error:
                        logger.error(f"[vk2tg_poster] Cant send post to TG! {error}\nSkip...")

                

                # записываем последкюю дату поста в файл
                with open(r"modules\vk_to_tg_poster\last_post_date.txt", "w") as file:
                    file.write(str(self.last_post_date))

                # dp.stop_polling() # завершаем соединение с ботом ТГ
                await (await bot.get_session()).close()
                


            except Exception as error:
                logger.error(f"[vk2tg_poster] Some error: {error}")
            finally:
                try:
                    await (await bot.get_session()).close()
                except:
                    pass

            # задержка перед повторной проверкой группы
            await asyncio.sleep(self.refresh_time)

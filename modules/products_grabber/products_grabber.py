import vk_api
import asyncio
import time
import multiprocessing
import aiosqlite
#
import modules.logger as logger

async def write_items_to_database(items):
    # async with aiosqlite.connect("/home/dragmor/flask_eshop/database.db") as db: # путь к БД
    async with aiosqlite.connect("database.db") as db:
        await db.execute("DROP TABLE IF EXISTS cards")
        await db.execute("""
            CREATE TABLE cards (
                id INTEGER PRIMARY KEY,
                title TEXT,
                description TEXT,
                price TEXT,
                image_link TEXT,
                link TEXT,
                site_group INTEGER
            )
        """)
        for item in items:
            if "туя" in item['title'].lower():
                group = 1
            elif "можжевельник" in item['title'].lower():
                group = 2
            else:
                group = 3

            await db.execute("INSERT INTO cards (title, description, price, image_link, link, site_group) VALUES (?, ?, ?, ?, ?, ?)",
                             (item['title'], item['description'], item['price'], item['photo_link'], item['link'], group))
        await db.commit()

def get_group_items(group, access_token):
    # Авторизация в ВКонтакте с использованием токена группы
    vk_session = vk_api.VkApi(token=access_token)

    # Получение информации о товарах из группы
    vk = vk_session.get_api()
    # если был вставлен полный адрес группы
    if "vk.com/" in group:
        group = group[group.find("vk.com/")+7:]
        if "/" in group:
            group = group[:group.find("/")]
            
    group_info = vk.groups.getById(group_id=group)
    # Получите ID группы
    group_id = f"-{group_info[0]['id']}"

    albums = vk.market.getAlbums(owner_id=group_id)
    album_ids = [album['id'] for album in albums['items']]
    response = vk.market.get(owner_id=group_id, album_ids=album_ids, extended=1)

    # Обработка полученных данных
    items = []
    for item in response['items']:
        title = item['title']
        description = item['description']
        price = item['price']['text']
        photo_link = item['thumb_photo']
        
        # Добавление ссылки на товар
        link = f"https://vk.com/market{group_id}?w=product{group_id}_{item['id']}"
        item['link'] = link
        
        items.append({'title': title, 'description': description, 'price': price, 'photo_link': photo_link, 'link': link})
        # сохраняем: название товара, описание, цена, ссылка на главную миниатюру, ссылки на все фотки товара, ссылка на товар
    return items



def parser_process(config):
    token = config['vk_token']
    group_id = config['vk_group_id']
    sleep = config['refresh_time']
    logger.debug("[products_grabber] Products_grabber is running!")
    # процесс, который парсит из группы ВК товары, и загружает их в БД
    while True:
        try:
            # парсим из группы вк товары
            try:
                cards = get_group_items(group_id, token)
            except Exception as error:
                logger.error(f"[products_grabber] Parsing product error: {error}")
                time.sleep(300)
                continue
            if not cards:
                logger.error("[products_grabber] Can't find products in VK group!")
                time.sleep(300)
                continue
            # записываем в БД все товары, которые спарсили
            asyncio.run(write_items_to_database(cards))  
        except Exception as error:
            logger.error(f"[products_grabber] Loading products error: {error}")
            time.sleep(300)
        else:
            logger.info("[products_grabber] Ok! Products loading complete!")
            time.sleep(sleep) # ждём час

import getpass
import multiprocessing
import asyncio
import json
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
#
from modules.vk_to_tg_poster.vk2tg_poster import VKtoTelegram
import modules.products_grabber.products_grabber as products_grabber
import modules.logger as logger # модуль для отображения логов с временем и цветом


def vk2tg(vk2tg_obj):
    # запускатор авто-переноса публикаций из ВК в ТГ
    asyncio.run(vk2tg_obj.start())

def load_config(key):
    try:
        with open('settings.json', 'rb') as file:
            file_text = file.read().hex()
        decrypted_json = decrypt(file_text, key)
        json_data = json.loads(decrypted_json)

        return json_data
    except Exception as error:
        logger.error(f"Error loading json-settings: {error}\nMaybe invalid pawsord!")
        return None

def decrypt(encrypted_message, key):
    # Генерируем ключ шифрования из входного ключа
    hashed_key = hashlib.sha256(key.encode()).digest()
    # Создаем объект расшифрования AES с режимом ECB
    cipher = AES.new(hashed_key, AES.MODE_ECB)
    # Расшифровываем зашифрованное сообщение
    decrypted_message = unpad(cipher.decrypt(bytes.fromhex(encrypted_message)), AES.block_size)
    # Возвращаем расшифрованное сообщение в виде строки
    return decrypted_message.decode()

if __name__ == "__main__":
    config = None
    while not config:
        passwd = getpass.getpass() #запрос пароля
        config = load_config(key=passwd)

    # Создаем экземпляр класса vk2tg и запускаем процесс
    vk2tg_obj = VKtoTelegram(config)
    vk2tg_process = multiprocessing.Process(target=vk2tg, args=(vk2tg_obj,))
    # vk2tg_process = multiprocessing.Process(target=lambda: asyncio.run(vk2tg_obj.start()))
    vk2tg_process.start()
    
    # Для авто-переноса товаров из группы ВК в БД
    products_parser = multiprocessing.Process(target=products_grabber.parser_process, args=(config,))
    products_parser.start()


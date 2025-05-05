import requests, base64, json, email, imaplib, email.message, os
from DB.ai_work import connect_to_chroma
from env import *
from loguru import logger
from datetime import datetime
from files_work import clear_folder, save_response_to_excel
from read_email import reading
from extract import extract_json

# openai.api_key = TOKEN  # замените на ваш API ключ
# openai.base_url = "https://api.proxyapi.ru/openai/v1"

API_URL = "https://api.proxyapi.ru/openai/v1/chat/completions"  # Подставь свой URL
API_KEY = TOKEN
 
def encode_image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def query_gpt_via_proxy(text, image_paths):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    images_payload = []
    for path in image_paths:
        images_payload.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{encode_image_to_base64(path)}"
            }
        })

    data = {
        "model": "gpt-4.1-mini", # gpt-4-vision-preview
        "messages": [
            {
                "role": "system",
                "content": '''сейчас я скину тебе информацию которую клиент скинул нам на почту (это может быть спамом, а может быть действительно заявкой или заказом на наш магазин, если эта информация не относится к заявка или заказу то верни мне просто None), предварительно вся информация переведена либо в картинки либо в текст выбери из этой информации товары которые клиент хочет получить от нашего магазина, старайся не повторяться, и товары которые уже встречались выписывать еще раз не надо если эта информация относится к заявке то верни мне ответ только в JSON без лишних слов, потому что я буду это парсить
JSON должен быть в формате
{
    "articles": [], // articles - артикл/код товаров (обычно это какая-то последовательность букв и цифр, не нужно повторять имя товара и не перепутай артикул с характеристиками товара, примеры артикулов: (TR003-1-6W3K-W-W; 25002DEK; 61918; UL-00002418), вообщем артикул не может начинаться с киррилицы и вообще русских букв в нем как правило быть не должно ищи внимательнее, но учти что артикула может не быть, в таком случае оставь поле пустым)
    "names": [], // names - наименования товаров
    "counts": [], // counts - кол-во товаров
    "quantityes": [], // quantityes - единица измерения,
    "manufacturers": [], // производители товаров (например IEK, TDM, ZUBR, Uniel)
    "notes": [], // примечания к товарам (длина этого массива должна быть такой же как длина массива articles, при необходимости заполняй пустыми строками)
    "sender": { 
        "email": "", // почта заказчика (она не может заканчиваться volt-market.com)
        "phones": [], // телефон заказчика (их может быть несколько)
        "fio": "", // ФИО заказчика
        "address": "", // адрес доставки
        "legal_address": "", // юридический адрес
        "official_email": "", // корпоративная почта (если есть или может совпадать с email)
        "INN": "", // ИНН
        "OGRN": "", // ОГРН
        "fio_director": "", // ФИО директора
        "contractor_name": "", // название контрагента пример (ООО "рога и копыта")
        "delivery_time": "", // срок поставки товара
        "terms_of_payment": "", // условия оплаты
        "other": "" // примечание к заказу
    }
}
если каких то данных на товар или на отправителя из этого списка ты не обнаружил оставь пустые скобки, но длина всех массивов относящихся к товару должна быть одинакова это важно!!!, будь внимателен и выбирай товары которые клиент хочет получить от нашего магазина (даже если это запрос цен или что-то подобное, главное это обращение к нам)!!! И ВНИМАТЕЛЬНО ОТВЕЧАЙ ТОЛЬКО JSON ОТВЕТОМ БЕЗ ЛИШНИХ РАЗМЫШЛЕНИЙ'''
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    *images_payload
                ]
            }
        ],
        # "max_tokens": 4096,
        "stream": False
    }
    logger.info("Запрос к GPT по телу письма...")
    response = requests.post(API_URL, headers=headers, json=data)
    logger.success("Запрос успешно обработан!!!")
    
    if response.status_code == 200:
        result = response.json()
        if result["choices"][0]["message"]["content"] == 'None':
            logger.debug("Это письмо было спамом, данные не сохранены...")
            return None
        return result["choices"][0]["message"]["content"]
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")



def main():

    current_path = os.path.dirname(os.path.abspath(__file__))
    mail_pass = EMAILS[1]["pass"]
    username = EMAILS[1]["email"]
    imap_server = "smtp.volt-market.com"
    imap = imaplib.IMAP4_SSL(imap_server)
    logger.info("Подключение к почте...")
    imap.login(username, mail_pass)

    imap.select("INBOX")
    logger.success("Подключение установлено!!!")
    db = connect_to_chroma()
    _, uuids = imap.uid("search", "UNSEEN")
    uuids = uuids[0].split()
    for uuid in uuids:
        try:
            logger.info(f"Обработка письма №{uuid.decode()}...")
            clear_folder(current_path+"\\temp")
            data = reading(imap, uuid)
            if (req := query_gpt_via_proxy("\n".join(data["texts"]), data["images"])) == None:
                continue
            result = ( extract_json(req) )
            logger.success("Данные успешно отформатированы")
            # print(result)
            save_response_to_excel(db, f"{current_path}\\results", uuid.decode(), result)
            # with open(f"temp.json", "w") as f:
            #     json.dump(result, f)
            # print("-"*50)
            logger.success(f"Обработка письма №{uuid.decode()} Завершена!!!")
        except Exception as e:
            print(e)
            logger.warning(f"Обработайте письмо №{uuid.decode()} вручную, с ним возникли ошибки")
    imap.close()


start = datetime.now()
main()
end = datetime.now()
print(end - start)
input("Введите что нибудь для выхода...")

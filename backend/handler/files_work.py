import patoolib, os, shutil, magic, sqlite3
import pandas as pd
from loguru import logger
from DB.ai_work import ai_list2list

def is_archive(filepath: str) -> bool:
    """Проверяет, является ли файл архивом любого формата"""
    if os.path.isdir(filepath): return False
    mime = magic.from_buffer(open(filepath, "rb").read(2048), mime=True)
    return mime.startswith(('application/x-', 'application/')) and any(
        key in mime for key in (
            'zip', 'rar', '7z', 'tar', 'gzip', 'bzip2', 
            'xz', 'lzma', 'lzip', 'lzop', 'arj', 
            'cab', 'iso', 'cpio', 'shar', 'z', 
            'compress', 'dmg', 'wim', 'swm', 'esd'
        )
    )

def pad_dict_list(dict_list, padel): 
    lmax = 0
    for lname in dict_list.keys():
        if lname == "sender": continue
        lmax = max(lmax, len(dict_list[lname]))
    for lname in dict_list.keys():
        if lname == "sender": continue
        ll = len(dict_list[lname])
        if  ll < lmax:
            dict_list[lname] += [padel] * (lmax - ll)
    return dict_list

def save_response_to_excel(db_norm: sqlite3.Cursor, db, path, num, response):
    # Убедиться, что путь существует
    os.makedirs(path, exist_ok=True)
    # Формирование имени файла
    filename = os.path.join(path, f"task_{num}.xlsx")
    response = pad_dict_list(response, '')

    true_names = []
    for i in response.get("articles", [""]):
        db_norm.execute(f"SELECT * FROM base_volt WHERE article='{i}'")
        req = db_norm.fetchone()
        if req: true_names.append(req)
        else: true_names.append(())
    # --- Первый лист: Товары ---
    # names, keywords = names2new_names(response.get("names", [""]))
    logger.info(f"Сохранение в файл '{filename}'...")
    ai_data = ai_list2list(db, response.get("names", [""]))
    ai_names = [(i_t[1] if i_t else i[0]["text"]) for i_t, i in zip(true_names, ai_data)]
    ai_score = [(100 if i_t else round(100*(1 - i[0]["similarity_score"]), 2)) for i_t, i in zip(true_names, ai_data)]
    ai_manufact = [(i_t[3] if i_t else i[0]["metadata"]["manufactor"]) for i_t, i in zip(true_names, ai_data)]
    ai_article = [(i_t[2] if i_t else i[0]["metadata"]["article"]) for i_t, i in zip(true_names, ai_data)]
    method = [("SQL" if i_t else "Vector") for i_t, i in zip(true_names, ai_data)]
    products_data = {
        "Наим. из запроса": response.get("names", [""]),
        "Артикул из запроса": response.get("articles", [""]),
        "Кол-во": response.get("counts", [""]),
        "Ед. изм.": response.get("quantityes", [""]),
        "Примечания": response.get("notes", [""]),
        "Артикул из обработки": ai_article,
        "Наим. из обработки": ai_names,
        "Схожесть %": ai_score,
        # "keyWords": keywords,
        # "Наим. по 1C": names,
        "Производитель": ai_manufact,
        "Метод": method
    }
    for prod in ai_data:
        for i in range(len(prod)):
            if not i: continue
            if f"Аналог{i}" not in products_data:
                products_data[f"Аналог{i}"] = []
            products_data[f"Аналог{i}"].append(prod[i]["text"])
            
    df_products = pd.DataFrame.from_dict(products_data, orient="index")
    df_products = df_products.transpose()

    # --- Второй лист: Заказчик ---
    sender = response.get("sender", {})
    sender_data = {
        "Поле": [
            "Email", "Телефоны", "ФИО", "Адрес доставки", "Юр. адрес",
            "Корпоративная почта", "ИНН", "ОГРН", "ФИО директора",
            "Название контрагента", "Срок поставки", "Условия оплаты", "Примечание к заказу"
        ],
        "Значение": [
            sender.get("email", ""),
            ", ".join(sender.get("phones", [])),
            sender.get("fio", ""),
            sender.get("address", ""),
            sender.get("legal_address", ""),
            sender.get("official_email", ""),
            sender.get("INN", ""),
            sender.get("OGRN", ""),
            sender.get("fio_director", ""),
            sender.get("contractor_name", ""),
            sender.get("delivery_time", ""),
            sender.get("terms_of_payment", ""),
            sender.get("other", "")
        ]
    }
    df_sender = pd.DataFrame(sender_data)

    # --- Сохранение Excel ---
    with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:
        df_products.to_excel(writer, index=False, sheet_name="Товары")
        df_sender.to_excel(writer, index=False, sheet_name="Заказчик")
        logger.success("Данные сохранены!!!")

def work_zip(path):
    for file_path in os.listdir(f"{path}\\temp"):
        file_abs = f"{path}\\temp\\{file_path}"
        if is_archive(file_abs):
            patoolib.extract_archive(file_abs, outdir=f"{path}\\temp")
            os.remove(file_abs)

def clear_folder(path):
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path, exist_ok=True)

work_zip(os.path.dirname(os.path.abspath(__file__)))
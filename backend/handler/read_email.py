from email.header import decode_header
from env import *
from files_work import *
from extract import *
from datetime import datetime
import os, base64, email, imaplib, email.message, locale, email
"""
sale@volt-market.com
KnHI288!m@G89r

Предварительная почта
"""
preferredencoding = locale.getpreferredencoding()


def decoding_header(header,content_charset=None):
    if header is None: return ""
    parts = []
    if content_charset is None:
        content_charset ='utf-8'
    
    def try_decode(decoded_part,charset):
        # пробуем декодировать байты в строку 
        try:
            decoded_part = decoded_part.decode(charset)
        except:
            try:
                # если не получилось - пробуем декодировать байты локальной кодировкой системы
                decoded_part = decoded_part.decode(preferredencoding)
            except:
                # если и здесь не получилось, возвращаем как есть - только в виде строки, а не байт
                decoded_part = str(decoded_part) 
        return decoded_part
    
    # декодируем все части заголовка из base64
    for part in email.header.decode_header(header):
        header_string, charset = part
        
        if charset in ['unknown-8bit',None]:
            charset = content_charset # будем использовать либо кодировку из Content-Type, либо utf-8 
        
        decoded_part = try_decode(header_string,charset)
        parts.append(decoded_part)
    
    return "".join(parts)

def recurs_types(msg_: email.message.Message, current_path, tab=0):
    s = ""
    payload = msg_.get_payload()
    for part in payload:
        if type(part) == str:
            try:
                s_b = base64.b64decode(part)
                s += s_b.decode("utf-8")
            except Exception:
                try:
                    s += part.decode("utf-8") 
                except AttributeError:
                    try:
                        s += part.encode("utf-8")
                    except Exception:
                        s += part
        elif part.get_content_maintype() == 'text' and part.get_content_subtype() == 'plain':
            if part['Content-Transfer-Encoding'] == 'base64':
                try:
                    s_b = base64.b64decode(part.get_payload())
                    s += s_b.decode("utf-8")
                except:
                    print("Ошибка декодирования Base64")
            else:
                s += part.get_payload()

        elif part.get_content_disposition() == 'attachment':
            with open(f"{current_path}\\temp\\{decoding_header(part.get_filename(), part.get_content_charset())}", "wb") as f:
                f.write(part.get_payload(decode=True))
            # with open(f"{current_path}\\temp\\names_volt.txt", "a", encoding="utf-8") as f:
            #     f.write(part.get_filename() + "\n")

        elif part.is_multipart():
            s += recurs_types(part, current_path, tab+1)
    return s

def reading(imap, number=b"2"):
    current_path = os.path.dirname(os.path.abspath(__file__))

    # _, uuids = imap.uid("search", "ALL")
    # uuids = uuids[0].split()
    
    _, msg = imap.uid("fetch", number, '(RFC822)')

    msg = email.message_from_bytes(msg[0][1])

    with open(f"{current_path}\\temp\\desc_volt.txt", "w", encoding="utf-8") as f:
        try:
            q = decode_header(msg["Subject"])[0][0].encode()
        except AttributeError:
            q = decode_header(msg["Subject"])[0][0].decode()
        if type(msg) == str:
            f.write(str(q)+"\n"+msg)
        else: 
            f.write(str(q)+"\n"+recurs_types(msg, current_path))
    # with open(f"{current_path}\\temp\\names_volt.txt", "a", encoding="utf-8") as f:
    #     f.write("desc.volt.txt")

    work_zip(current_path)
    # with open(f"{current_path}\\temp\\RESULT.json", "w", encoding="utf-8") as f:
    #     json.dump(extracting(), f)
    return extracting()

# start = datetime.now()
# main()
# end = datetime.now()

# print(end - start)
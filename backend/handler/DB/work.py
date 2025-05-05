import sqlite3, requests, os, json

PATH = os.path.dirname(os.path.abspath(__file__))
API_URL = "https://api.proxyapi.ru/openai/v1/chat/completions"  # Подставь свой URL
API_KEY = "sk-9rfsKOTg9ThEaqO0Cp4BMJAmFBH8DTLF"


def db_work(cur, query1):
    query = query1.split()

    sql_query = """
    SELECT *
    FROM base_volt
    WHERE 
    """ 
    for i in range(len(query)):
        sql_query += f"(name LIKE '%{query[i]}%' OR article LIKE '%{query[i]}%')"
        sql_query += " AND " if i != len(query)-1 else ";"

    res = cur.execute(sql_query)
    for i in res.fetchall():
        return i[1]
    return ''

def extract_json(text):
    start = text.find('{')
    if start == -1:
        return None

    brace_count = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1

        if brace_count == 0:
            try:
                json_str = text[start:i + 1]
                return json.loads(json_str)
            except json.JSONDecodeError:
                return None
    return None

def names2new_names(names):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4.1-mini", # gpt-4-vision-preview
        "messages": [
            {
                "role": "system",
                "content": 'У тебя есть список строк с названиями товаров. Для каждой строки сформируй краткую строку для поиска по базе данных. Если строка пустая, то результатом тоже должна быть пустая строка. В итоговой строке избегай символов вроде "х", "x", запятых, точек и других лишних знаков — оставляй только текст, нужный для поиска. Верни ответ строго в формате JSON: {"result": [список строк в порядке исходного списка]}.'
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": str(names)},
                ]
            }
        ],
        # "max_tokens": 4096,
        "stream": False
    }
    response = requests.post(API_URL, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        result = extract_json(result["choices"][0]["message"]["content"])
        
        conn = sqlite3.connect(f"{PATH}\\base.db")
        cur = conn.cursor()
        new_res = []
        keywords = []
        for i in result["result"]:
            keywords.append(i)
            if not i: 
                new_res.append(i)
                continue
            new_res.append(db_work(cur, i))
        conn.close()
        for i in range(abs(len(names)-len(new_res))):
            keywords.append('')
            new_res.append('')
        return [new_res, keywords]
    return [names, ["<NetworkError>"]*len(names)]
import re
import json
def parse():
    file_path = r'C:\Users\user\practice1\prac2\Practice05\raw.txt'
    
    with open(file_path, 'r',encoding='utf-8-sig' ) as f:
        text = f.read()

    items = re.findall(r'\d+\.\n(.*?)\n', text)
    prices = re.findall(r'(\d+,\d{2})\nСтоимость', text)
    result = {"items": [{"name": n, "price": p} for n, p in zip(items, prices)]}
    print('\n--- Receipt Data ---')
    print(json.dumps(result, indent=4, ensure_ascii=False))
parse()

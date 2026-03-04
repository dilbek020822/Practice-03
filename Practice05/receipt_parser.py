import re
import json
def parse():
    with open('raw.txt', 'r', encoding='utf-8') as f:
        text = f.read()
    items = re.findall(r'\d+\.\n(.*?)\n', text)
    prices = re.findall(r'(\d+,\d{2})\nСтоимость', text)
    result = {"items": [{"name": n, "price": p} for n, p in zip(items, prices)]}
    print('\n--- Receipt Data ---')
    print(json.dumps(result, indent=4, ensure_ascii=False))
parse()

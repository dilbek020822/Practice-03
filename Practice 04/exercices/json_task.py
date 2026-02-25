import json
import os

path = 'json/sample-data.json'
if os.path.exists(path):
    with open(path) as f:
        data = json.load(f)
    print("Interface Status\n" + "="*80)
    print(f"{'DN':<50} {'Description':<20} {'Speed':<7} {'MTU':<6}")
    for i in data['imdata']:
        a = i['l1PhysIf']['attributes']
        print(f"{a['dn']:<50} {a.get('descr',''):<20} {a['speed']:<7} {a['mtu']:<6}")
else:
    print("Файл sample-data.json не найден в папке json!")
import os
os.makedirs("parent/child", exist_ok=True)
print("Файлдар тізімі:", os.listdir('.'))
py_files = [f for f in os.listdir('.') if f.endswith('.py')]
print("Python файлдары:", py_files)

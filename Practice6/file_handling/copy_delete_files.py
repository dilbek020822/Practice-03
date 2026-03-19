import shutil
import os
shutil.copy("sample.txt", "sample_backup.txt")
print("Файл көшірілді: sample_backup.txt")
if os.path.exists("sample_backup.txt"):
    os.remove("sample_backup.txt")
    print("Көшірме файл қайта жойылды.")

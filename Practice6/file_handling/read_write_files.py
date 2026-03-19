from pathlib import Path
with open("sample.txt", "w", encoding="utf-8") as f:
    f.write("Бұл бірінші жол.\nБұл екінші жол.")
print("--- Файл мазмұны ---")
with open("sample.txt", "r", encoding="utf-8") as f:
    print(f.read())
with open("sample.txt", "a", encoding="utf-8") as f:
    f.write("\nБұл қосылған үшінші жол.")

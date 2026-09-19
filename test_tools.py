from tools import list_files, read_file, move_file


print("===== list_files =====")

result = list_files.invoke({
    "folder_path": "test_files"
})

print(result)


print("===== read_file =====")

result = read_file.invoke({
    "file_path": "test_files/a.txt"
})

print(result)


print("===== move_file =====")

result = move_file.invoke({
    "file_path": "test_files/a.txt",
    "target_folder": "test_files/txt_files"
})

print(result)
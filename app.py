import os


def get_foty_files(root_dir):
    foty_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if os.path.splitext(filename)[1] == '.foty':
                archivo = os.path.join(dirpath, filename)
                foty_files.append((archivo[19:], os.path.getsize(archivo)))
    return foty_files


FOLDER = '//PROPROM/Marketing/'
foty_files = get_foty_files(FOLDER)
sorte_files = sorted(foty_files, key=lambda x: x[1], reverse=True)
for filepath, size in sorte_files:
    print(f"{filepath} - {size} bytes")

print(f' {len(sorte_files)} archivos')

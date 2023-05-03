import os


def get_foty_files(root_dir):
    foty_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if os.path.splitext(filename)[1] == '.foty':
                archivo = os.path.join(dirpath, filename)
                foty_files.append((archivo[19:], os.path.getsize(archivo)))
    return foty_files


def read_affected_files():
    file_path = 'files.tsv'
    foty_files = []
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            lines = content.split("\n")
            for line in lines:
                if '|' in line:
                    filepath, size = line.split("|")
                    foty_files.append((filepath, size))
    return foty_files


def write_affected_files():
    FOLDER = '//PROPROM/Marketing/'
    print('Encontrando archivos afectados en el server.')
    foty_files = get_foty_files(FOLDER)
    print('Ordenando por tamano.')
    sorted_files = sorted(foty_files, key=lambda x: x[1], reverse=True)
    with open('files.tsv', 'w', encoding='utf-8') as file:
        print(f'Escribiendo {len(sorted_files)} archivos.')
        for filepath, size in sorted_files:
            file.write(f"{filepath}|{size}\n")
        print('Terminado.')
    return sorted_files


def main():
    if not os.path.exists('files.tsv'):
        files = write_affected_files()
    else:
        files = read_affected_files()
    print(f'Hay {len(files)} archivos afectados.')


if __name__ == '__main__':
    main()

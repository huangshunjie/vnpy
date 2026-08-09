"""批量修复所有以 image.png 开头的 .py 文件"""
import os

fixed = []
for root, dirs, files in os.walk('vnpy'):
    # skip .git
    if '.git' in dirs:
        dirs.remove('.git')
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(root, f)
        try:
            with open(path, 'rb') as fh:
                data = fh.read()
            if data.startswith(b'image.png'):
                new_data = data[len(b'image.png'):]
                with open(path, 'wb') as fh:
                    fh.write(new_data)
                fixed.append(path)
        except Exception as e:
            print(f'ERROR: {path}: {e}')

for p in fixed:
    print(f'FIXED: {p}')
print(f'\nTotal fixed: {len(fixed)}')
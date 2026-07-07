import shutil, pathlib
src = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\trader\ui\ico\editor.ico")
dst = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\platform_engineering.ico")
shutil.copy2(src, dst)
print("copied:", dst.stat().st_size, "bytes")

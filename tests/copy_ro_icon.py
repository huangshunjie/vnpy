import shutil, pathlib
src = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\trader\ui\ico\editor.ico")
dst = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\research_ops.ico")
shutil.copy2(src, dst)
print("icon copied:", dst.stat().st_size, "bytes")

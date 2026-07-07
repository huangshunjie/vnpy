import pathlib
p = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\tests\smoke_pe_p8_final.py")
txt = p.read_text(encoding="utf-8")
txt = txt.replace("auth_required=False", "auth_required=True", 1)
p.write_text(txt, encoding="utf-8")
print("fixed")

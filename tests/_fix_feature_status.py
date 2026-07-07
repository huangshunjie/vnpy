"""Fix FeatureStatus enum in constant.py"""
import pathlib

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\constant.py"
)
txt = P.read_text(encoding="utf-8")

OLD = (
    'class FeatureStatus(Enum):\n'
    '    ACTIVE      = "active"\n'
    '    DEPRECATED  = "deprecated"\n'
    '    EXPERIMENTAL = "experimental"'
)
NEW = (
    'class FeatureStatus(Enum):\n'
    '    EXPERIMENTAL = "experimental"\n'
    '    REVIEW       = "review"\n'
    '    STABLE       = "stable"\n'
    '    DEPRECATED   = "deprecated"'
)

if OLD in txt:
    P.write_text(txt.replace(OLD, NEW), encoding="utf-8")
    print("patched OK")
else:
    print("NOT FOUND, showing snippet:")
    idx = txt.find("FeatureStatus")
    print(repr(txt[idx:idx+200]))

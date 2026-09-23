#!/usr/bin/env python3
"""Strip dangling drawing references openxlsx leaves in every workbook it saves.

Each sheet gets a relationship to xl/drawings/drawingN.xml that is never
written. openxlsx reads its own output happily, so the defect is invisible from
R -- but openpyxl and other readers raise KeyError on the missing part. Since
these workbooks are the deliverable, they must open anywhere.
"""
import os, re, shutil, sys, zipfile


def fix(path):
    zin = zipfile.ZipFile(path)
    names = zin.namelist()
    missing = set()
    for n in names:
        if n.endswith(".rels"):
            for t in re.findall(r'Target="([^"]*(?:drawing|vmlDrawing)[^"]*)"',
                                zin.read(n).decode("utf-8")):
                p = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(n)), t))
                if p.replace("\\", "/") not in names:
                    missing.add(t)
    if not missing:
        zin.close()
        return 0
    tmp = path + ".fix"
    zout = zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED)
    for n in names:
        d = zin.read(n)
        if n.endswith(".rels"):
            d = re.sub(r'<Relationship[^>]*Target="[^"]*(?:drawing|vmlDrawing)[^"]*"[^>]*/>',
                       "", d.decode("utf-8")).encode("utf-8")
        elif n.startswith("xl/worksheets/sheet") and n.endswith(".xml"):
            d = re.sub(r'<(?:legacy)?[dD]rawing[^>]*/>', "",
                       d.decode("utf-8")).encode("utf-8")
        zout.writestr(n, d)
    zout.close(); zin.close(); shutil.move(tmp, path)
    return len(missing)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(f"  {p}: stripped {fix(p)} dangling references")

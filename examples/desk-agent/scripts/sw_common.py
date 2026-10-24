"""Shared SolidWorks API helpers (pywin32, early binding)."""
import os
import pythoncom
import win32com.client
from win32com.client import VARIANT

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "parts")
os.makedirs(OUT, exist_ok=True)

CREATED = set()  # titles of docs created by this process
NOTHING = None  # early-bound IDispatch params accept None


# set SW_DIR to run against another install, e.g. "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (3)" (2024, has Motion)
SW_DIR = os.environ.get("SW_DIR", r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (2)")


def load_tlb(name):
    """Generate/load early-binding wrappers from a SolidWorks .tlb file."""
    tlb = pythoncom.LoadTypeLib(os.path.join(SW_DIR, name))
    a = tlb.GetLibAttr()
    return win32com.client.gencache.EnsureModule(str(a[0]), a[1], a[3], a[4])


swmod = load_tlb("sldworks.tlb")
swconst = load_tlb("swconst.tlb")


def T(obj, iface, mod=None):
    """Wrap a returned dispatch object in its early-bound interface class."""
    if obj is None:
        return None
    ole = getattr(obj, "_oleobj_", obj)
    return getattr(mod or swmod, iface)(ole.QueryInterface(pythoncom.IID_IDispatch))


def connect():
    raw = pythoncom.GetActiveObject("SldWorks.Application")
    disp = raw.QueryInterface(pythoncom.IID_IDispatch)
    sw = swmod.ISldWorks(disp)
    if not sw.Visible:      # an instance started without a window creates centre rectangles without a centre point
        sw.Visible = True
    return sw


FALLBACK_TEMPLATES = {
    "part": r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2025\templates\Part.prtdot",
    "asm": r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2025\templates\Assembly.ASMDOT",
}


def default_template(sw, kind):
    # swDefaultTemplatePart = 8, swDefaultTemplateAssembly = 9
    tpl = sw.GetUserPreferenceStringValue({"part": 8, "asm": 9}[kind])
    if not os.path.isabs(tpl) or not os.path.exists(tpl):
        tpl = FALLBACK_TEMPLATES[kind]
    if not os.path.exists(tpl):  # other SolidWorks year: take the newest template found
        import glob
        pat = {"part": "Part.prtdot", "asm": "Assembly.asmdot"}[kind]
        hits = sorted(glob.glob(os.path.join(r"C:\ProgramData\SOLIDWORKS", "SOLIDWORKS *", "templates", pat)))
        if hits:
            tpl = hits[-1]
    return tpl


def new_doc(sw, kind):
    tpl = default_template(sw, kind)
    doc = T(sw.NewDocument(tpl, 0, 0, 0), "IModelDoc2")
    if doc is not None:
        CREATED.add(doc.GetTitle())
    if doc is None:
        raise RuntimeError(f"NewDocument failed, template={tpl!r}")
    return doc


def select(doc, name, typ, append=False, mark=0, x=0.0, y=0.0, z=0.0):
    ok = doc.Extension.SelectByID2(name, typ, x, y, z, append, mark, NOTHING, 0)
    if not ok:
        raise RuntimeError(f"SelectByID2 failed: {name!r} ({typ})")
    return ok


def save_as(doc, path):
    # swSaveAsCurrentVersion=0, swSaveAsOptions_Silent=1; in/out ints come back as a tuple
    ok, errs, warns = doc.Extension.SaveAs(path, 0, 1, None, 0, 0)
    if not ok or not os.path.exists(path):
        raise RuntimeError(f"SaveAs failed {path}: err={errs} warn={warns}")
    return path


def close_out_docs(sw):
    """Close docs saved in OUT or created by this process. Never touches other documents."""
    closed = []
    doc = sw.GetFirstDocument()
    docs = []
    while doc is not None:
        d = T(doc, "IModelDoc2")
        docs.append(d)
        doc = d.GetNext()
    for d in docs:
        p = d.GetPathName()
        if (p == "" and d.GetTitle() in CREATED) or os.path.normcase(os.path.dirname(p)) == os.path.normcase(OUT):
            closed.append(d.GetTitle())
            sw.CloseDoc(d.GetTitle())
    return closed


def _close_unsaved_created():
    """On exit (incl. crashes), close unsaved scratch docs this process created."""
    if not CREATED:
        return
    try:
        sw = connect()
        d = sw.GetFirstDocument()
        docs = []
        while d is not None:
            d = T(d, "IModelDoc2")
            docs.append(d)
            d = d.GetNext()
        for d in docs:
            if d.GetPathName() == "" and d.GetTitle() in CREATED:
                sw.CloseDoc(d.GetTitle())
    except Exception:
        pass


import atexit
atexit.register(_close_unsaved_created)

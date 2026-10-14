import subprocess, sys, time, os, uno
from com.sun.star.beans import PropertyValue
src, dst = map(os.path.abspath, sys.argv[1:3])
p = subprocess.Popen(["soffice", "--headless", "--invisible", "--norestore",
                      "--accept=socket,host=127.0.0.1,port=2099;urp;"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
ctx = None
for _ in range(60):
    try:
        local = uno.getComponentContext()
        res = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
        ctx = res.resolve("uno:socket,host=127.0.0.1,port=2099;urp;StarOffice.ComponentContext"); break
    except Exception:
        time.sleep(1)
smgr = ctx.ServiceManager
desk = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
def pv(n, v):
    x = PropertyValue(); x.Name = n; x.Value = v; return x
doc = desk.loadComponentFromURL(uno.systemPathToFileUrl(src), "_blank", 0, (pv("Hidden", True),))
idx = doc.getDocumentIndexes()
for i in range(idx.getCount()):
    idx.getByIndex(i).update()
doc.refresh()
idx = doc.getDocumentIndexes()
for i in range(idx.getCount()):
    idx.getByIndex(i).update()
nb = idx.getCount()
doc.storeToURL(uno.systemPathToFileUrl(dst), (pv("FilterName", "MS Word 2007 XML"),))
doc.close(True)
try: desk.terminate()
except Exception: pass
p.wait(timeout=30)
print("sommaire mis à jour :", nb, "index")

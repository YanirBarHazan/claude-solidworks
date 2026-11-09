"""Pre-run hygiene and stall detection (ROADMAP 8).
prerun(sw, folder): when SolidWorks has no document open, delete stale ~$ lock files of the project (a crashed
instance leaves them and the next open hangs on a modal dialog); prints one line.
Stall: a heartbeat thread - if no beat for `seconds`, writes 'STALL <item> <s>' to the trace file and stdout
(a hung COM call cannot be interrupted from Python; the line tells the operator which item hangs)."""
import os
import threading
import time

from sw_common import T


def open_docs(sw):
    n, d = 0, sw.GetFirstDocument()
    while d is not None:
        n += 1
        d = T(d, "IModelDoc2").GetNext()
    return n


def prerun(sw, folder):
    n = open_docs(sw)
    locks = []
    for root, _, files in os.walk(folder):
        locks += [os.path.join(root, f) for f in files if f.startswith("~$")]
    removed = 0
    if n == 0:
        for f in locks:
            try:
                os.remove(f)
                removed += 1
            except OSError:
                pass
    print(f"prerun: SolidWorks {sw.RevisionNumber()}, open documents {n}, stale locks removed {removed}"
          f"{'' if n == 0 or not locks else f' ({len(locks)} kept: documents are open)'}", flush=True)
    return n, removed


class Stall:
    def __init__(self, trace, seconds=180):
        self.trace, self.seconds = trace, seconds
        self.item, self.t = "start", time.time()
        self._stop = threading.Event()
        self._warned = None
        self.th = threading.Thread(target=self._watch, daemon=True)
        self.th.start()

    def beat(self, item):
        self.item, self.t = item, time.time()
        with open(self.trace, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {item}\n")

    def _watch(self):
        while not self._stop.wait(10):
            idle = time.time() - self.t
            if idle > self.seconds and self._warned != self.item:
                self._warned = self.item
                msg = f"STALL {self.item} {idle:.0f} s without progress (modal dialog in SolidWorks?)"
                with open(self.trace, "a", encoding="utf-8") as f:
                    f.write(msg + "\n")
                print(msg, flush=True)

    def stop(self):
        self._stop.set()

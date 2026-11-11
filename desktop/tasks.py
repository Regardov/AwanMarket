"""Run blocking HTTP work outside the Qt event loop."""

from PyQt6 import sip
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal


class Signals(QObject):
    done = pyqtSignal(object, object)


class Task(QRunnable):
    def __init__(self, work):
        super().__init__()
        self.work = work
        self.signals = Signals()

    def run(self):
        try:
            result, error = self.work(), None
        except Exception as exc:
            result, error = None, exc
        self.signals.done.emit(result, error)


def run_task(owner, work, done):
    task = Task(work)

    def delivered(result, error):
        if not sip.isdeleted(owner):
            done(result, error)

    task.signals.done.connect(delivered)
    QThreadPool.globalInstance().start(task)

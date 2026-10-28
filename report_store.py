"""Ограниченное временное хранилище результатов локального приложения."""

from collections import OrderedDict
from secrets import token_urlsafe
from threading import RLock
from time import monotonic

TTL = 2 * 60 * 60
MAX_REPORTS = 32
_reports = OrderedDict()
_lock = RLock()


def _prune():
    now = monotonic()
    for key, (created, _) in list(_reports.items()):
        if now - created >= TTL:
            del _reports[key]


def save(results):
    with _lock:
        _prune()
        key = token_urlsafe(24)
        _reports[key] = (monotonic(), results)
        while len(_reports) > MAX_REPORTS:
            _reports.popitem(last=False)
        return key


def get(key):
    with _lock:
        _prune()
        return _reports.get(key, (None, []))[1]

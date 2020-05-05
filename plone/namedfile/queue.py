"""Image scaling queue processor thread

This module contains the image scaling queue processor thread.
"""
from App.config import getConfiguration
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import TimeoutError
from plone.namedfile.file import NamedBlobImage
from plone.namedfile.interfaces import IImageScalingQueue
from plone.scale.scale import scaleImage
from plone.scale.storage import AnnotationStorage
from six.moves import queue
from transaction import TransactionManager
from transaction.interfaces import IDataManager
from ZODB.blob import Blob
from zope.component import hooks
from zope.component import queryUtility
from zope.interface import implementer

import atexit
import functools
import logging
import threading
import transaction

logger = logging.getLogger(__name__)

ZODB_CACHE_SIZE = 100
MAX_QUEUE_GET_TIMEOUT = 1
MAX_TASK_RETRY_COUNT = 10


def imageScalingQueueFactory():
    """Create scaling queue processor thread utility instance"""
    thread = ImageScalingQueueProcessorThread()
    thread.start()
    return thread


def scaleImageTask(path, **parameters):
    """Concurrent executor task for scaling image"""
    with open(path, "rb") as fp:
        return scaleImage(fp, **parameters)


def get_queue(context, blob):
    """Get image scaling queue callable for blobs"""

    queue = queryUtility(IImageScalingQueue)
    storage = AnnotationStorage(context)
    storage_oid = getattr(storage.storage, "_p_oid", None)
    data_oid = getattr(blob, "_p_oid", None)

    # Reserve OIDs for new objects
    if storage_oid is None or data_oid is None:
        site = hooks.getSite()
        if storage_oid is None:
            site._p_jar.add(storage.storage)
            storage_oid = storage.storage._p_oid
        if data_oid is None:
            site._p_jar.add(blob)
            data_oid = blob._p_oid

    if all([queue, storage_oid, data_oid]):
        return functools.partial(queue.put, storage_oid, data_oid)

    return None


def queue_scale(context, value, fieldname=None, height=None, width=None,
                direction=None, scale=None, transaction_manager=None,
                **parameters):
    if not isinstance(value, NamedBlobImage) or None in [fieldname, height, width]:
        return

    task_arguments = {
        "klass": value.__class__,
        "context": '/'.join(context.getPhysicalPath()),
        "filename": value.filename,
        "fieldname": fieldname,
        "direction": direction,
        "height": height,
        "width": width,
        "scale": scale,
    }
    task_arguments.update(parameters)
    queue_put = get_queue(context, value._blob)

    if queue_put is not None:
        if transaction_manager:
            transaction_manager.get().join(ImageScalingQueueDataManager(
                functools.partial(queue_put, **task_arguments)
            ))
        else:
            queue_put(**task_arguments)


@implementer(IImageScalingQueue)
class ImageScalingQueueProcessorThread(threading.Thread):
    """This thread is started at execution time once the first scaling has
    been queued.
    """

    _stopped = False

    def __init__(self):
        threading.Thread.__init__(
            self, name="plone.namedfile.queue.ScalingQueueProcessorThread")
        config = getConfiguration()
        self.setDaemon(True)
        self._lock = threading.Lock()
        self._timeout = 0.0
        self._queue = queue.Queue()
        self._retry = queue.Queue()
        self._retries = {}  # must be accessed with lock
        self._retries_lock = threading.Lock()
        self._tm = TransactionManager()
        self._db = config.dbtab.getDatabase("/", is_root=1)
        self._conn = self._db.open(transaction_manager=self._tm)
        self._conn._cache.cache_size = ZODB_CACHE_SIZE  # minimal cache
        self._executor = ProcessPoolExecutor()
        self._futures = []

    def tuple(self, d):
        """Convert dict to sorted (hashable) tuple. Not recursive."""
        return tuple(sorted(d.items()))

    def put(self, storage_oid, data_oid, filename, klass, context, **parameters):
        """Queue asynchronous image scaling into plone.scale annotation storage"""
        # This is public API and is called outside the thread
        task = self.tuple({
            "storage_oid": storage_oid,
            "data_oid": data_oid,
            "filename": filename,
            "klass": klass,
            "context": context,
            "parameters": self.tuple(parameters),
        })
        with self._retries_lock:
            if task not in self._retries:
                self._retries[task] = 0
                self._queue.put(task)

    def _retry_task(self, task, reason):
        """Retry task because of exception or other reason"""
        assert isinstance(task, tuple)
        error = False
        with self._retries_lock:
            if self._retries[task] > MAX_TASK_RETRY_COUNT:
                del self._retries[task]
                error = True
            else:
                self._retry.put(task)
        if error and isinstance(reason, Exception):
            logger.exception(str(reason))
        elif error:
            logger.warning(str(reason))

    def run(self, forever=True):
        atexit.register(self.stop)
        while not self._stopped:

            # check for new results
            for task, future in self._futures:
                assert isinstance(task, tuple)
                try:
                    result = future.result(timeout=0)
                    self._timeout = 0.0
                    self._futures.remove((task, future))
                except TimeoutError:
                    continue
                except Exception as e:  # noqa: never break the loop
                    self._retry_task(task, e)
                    continue
                with self._tm as t:
                    try:
                        self._store_scale_result(task, result, t)
                        with self._retries_lock:
                            del self._retries[task]
                    except Exception as e:  # noqa: never break the loop
                        self._retry_task(task, e)
                        continue

            # check for new task
            try:
                task = self._queue.get(timeout=self._timeout)
                self._timeout = 0.0
                assert isinstance(task, tuple)
            except queue.Empty:
                if self._timeout < MAX_QUEUE_GET_TIMEOUT:
                    self._timeout += 0.1
                # on empty queue, flush retry queue back to main queue
                while self._retry.qsize() > 0:
                    try:
                        self._queue.put(self._retry.get(timeout=self._timeout))
                        self._retry.task_done()
                    except queue.Empty:
                        break
                continue

            # if we are asked to stop while scaling images, do so
            if self._stopped:
                break

            # queue execution of new task
            try:
                with self._tm:
                    future = self._queue_scale_execution(task)
                    if future is not None:
                        self._futures.append((task, future))
            except Exception as e:  # noqa: never break the loop
                self._retry_task(task, e)

            # A testing plug
            if not forever:
                break

    def _queue_scale_execution(self, task):
        assert isinstance(task, tuple)
        task = dict(task)
        storage = self._conn.get(task["storage_oid"])
        data = self._conn.get(task["data_oid"])

        key = dict(task["parameters"])
        key.pop("quality", None)  # not part of key
        key = tuple(sorted(key.items()))

        anon_key = dict(task["parameters"])
        anon_key.pop("scale", None)  # not part of key
        anon_key = tuple(sorted(anon_key.items()))

        matches = [info for info in storage.values()
                   if info.get("key") in [key, anon_key]
                   and info.get("data") is None]
        if matches and isinstance(data, Blob):
            parameters = dict(task["parameters"])
            parameters.pop("fieldname", None)
            parameters.pop("scale", None)
            fp = data.open()
            path = fp.name
            fp.close()
            future = self._executor.submit(scaleImageTask, path, **parameters)
            return future

        self._retry_task(
            task, "Skipped scale without matching key: " + str(task))
        return None

    def _store_scale_result(self, task, result, t):
        assert isinstance(task, tuple)
        task = dict(task)
        storage = self._conn.get(task["storage_oid"])

        key = dict(task["parameters"])
        key.pop("quality", None)  # not part of key
        key = tuple(sorted(key.items()))

        anon_key = dict(task["parameters"])
        anon_key.pop("scale", None)  # not part of key
        anon_key = tuple(sorted(anon_key.items()))

        parameters = dict(task["parameters"])
        fieldname = parameters.pop("fieldname", None)
        scale_name = parameters.pop("scale", None) or ""

        data, format_, dimensions = result
        mimetype = "image/{0}".format(format_.lower())
        value = task["klass"](
            data, contentType=mimetype, filename=task["filename"],
        )
        value.fieldname = fieldname
        for info in [info for info in storage.values()
                     if info.get("key") in [key, anon_key]
                     and info.get("data") is None]:
            info["data"] = value
            storage[info["uid"]] = info
            note = "/".join(filter(bool, [
                task["context"], "@@images", fieldname, scale_name]))
            details = "x".join(filter(bool, [
                str(parameters.get("width") or ""),
                str(parameters.get("height") or ""),
                str(parameters.get("quality") or ""),
            ]))
            logger.debug(" ".join([note, details, info["uid"]]))
            t.note(note)

    def stop(self):
        self._stopped = True
        self._lock.acquire()
        self._lock.release()


@implementer(IDataManager)
class ImageScalingQueueDataManager(object):
    def __init__(self, callable, args=(), vote=None, onAbort=None):
        self.callable = callable
        self.args = args
        self.vote = vote
        self.onAbort = onAbort
        # Use the default thread transaction manager.
        self.transaction_manager = transaction.manager

    def commit(self, txn):
        pass

    def abort(self, txn):
        if self.onAbort:
            self.onAbort()

    def sortKey(self):
        return str(id(self))

    # No subtransaction support.
    def abort_sub(self, txn):
        """This object does not do anything with subtransactions"""
        pass

    commit_sub = abort_sub

    def beforeCompletion(self, txn):
        """This object does not do anything in beforeCompletion"""
        pass

    afterCompletion = beforeCompletion

    def tpc_begin(self, txn, subtransaction=False):
        assert not subtransaction

    def tpc_vote(self, txn):
        if self.vote is not None:
            return self.vote(*self.args)

    def tpc_finish(self, txn):
        try:
            self.callable(*self.args)
        except Exception:
            # Any exceptions here can cause database corruption.
            # Better to protect the data and potentially miss emails than
            # leave a database in an inconsistent state which requires a
            # guru to fix.
            logger.exception("Failed in tpc_finish for %r", self.callable)

    tpc_abort = abort

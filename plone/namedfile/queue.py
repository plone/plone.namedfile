"""Image scaling queue processor thread

This module contains the image scaling queue processor thread.
"""
from App.config import getConfiguration
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import TimeoutError
from plone.namedfile.interfaces import IImageScalingQueue
from plone.scale.scale import scaleImage
from six.moves import queue
from transaction import TransactionManager
from transaction.interfaces import IDataManager
from ZODB.blob import Blob
from zope.interface import implementer

import atexit
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


class SetQueue(queue.Queue):
    """Unordered queue that only holds the same task once"""

    def _init(self, maxsize):
        self.queue = set()  # order does not really matter

    def _put(self, item):
        self.queue.add(item)

    def _get(self):
        return self.queue.pop()


def scaleImageTask(path, **parameters):
    """Concurrent executor task for scaling image"""
    with open(path, "rb") as fp:
        return scaleImage(fp, **parameters)


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
        self._queue = SetQueue()
        self._retry = SetQueue()
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

    def _retry_task(self, task, exception):
        """Retry task because of exception"""
        assert isinstance(task, tuple)
        error = False
        with self._retries_lock:
            if self._retries[task] > MAX_TASK_RETRY_COUNT:
                del self._retries[task]
                error = True
            else:
                self._retry.put(task)
        if error:
            logger.exception(str(exception))

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

        values = [scale for scale in storage.values()
                  if scale.get("key") == key
                  and scale.get("data") is None]
        if values and isinstance(data, Blob):
            parameters = dict(task["parameters"])
            parameters.pop("fieldname", None)
            parameters.pop("scale", None)
            fp = data.open()
            path = fp.name
            fp.close()
            future = self._executor.submit(scaleImageTask, path, **parameters)
            return future
        return None

    def _store_scale_result(self, task, result, t):
        assert isinstance(task, tuple)
        task = dict(task)
        storage = self._conn.get(task["storage_oid"])

        key = dict(task["parameters"])
        key.pop("quality", None)  # not part of key
        key = tuple(sorted(key.items()))

        parameters = dict(task["parameters"])
        fieldname = parameters.pop("fieldname", None)
        scale_name = parameters.pop("scale", None)

        data, format_, dimensions = result
        mimetype = "image/{0}".format(format_.lower())
        value = task["klass"](
            data, contentType=mimetype, filename=task["filename"],
        )
        for scale in [value for value in storage.values()
                      if value.get("key") == key
                      and value.get("data") is None]:
            scale["data"] = value
            storage[scale["uid"]] = scale
            msg = '/'.join(filter(bool, [task["context"],
                                         '@@images', fieldname, scale_name]))
            logger.info(msg)
            t.note(msg)

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

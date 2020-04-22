"""Image scaling queue processor thread

This module contains the image scaling queue processor thread.
"""
from App.config import getConfiguration
from plone.namedfile.interfaces import IImageScalingQueue
from plone.scale.scale import scaleImage
from six.moves import queue
from transaction import TransactionManager
from transaction.interfaces import IDataManager
from zope.interface import implementer

import atexit
import logging
import threading
import transaction

logger = logging.getLogger(__name__)


def imageScalingQueueFactory():
    """Create scaling queue processor thread utility instance"""
    thread = ImageScalingQueueProcessorThread()
    thread.start()
    return thread


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
        self._lock = threading.Lock()
        self.setDaemon(True)
        self.queue = queue.Queue()
        self.retry = queue.Queue()
        self._tm = TransactionManager()
        self._db = config.dbtab.getDatabase("/", is_root=1)
        self._conn = self._db.open(transaction_manager=self._tm)
        self._conn._cache.cache_size = 100  # minimal cache

    def put(self, storage_oid, data, filename, klass, context, **parameters):
        task = {
            "storage_oid": storage_oid,
            "data": data,
            "filename": filename,
            "klass": klass,
            "context": context,
            "parameters": parameters,
        }
        self.queue.put(task)

    def run(self, forever=True):
        atexit.register(self.stop)
        while not self._stopped:
            try:
                task = self.queue.get(timeout=1)
            except queue.Empty:
                # on empty queue, flush retry queue back to main queue
                while self.retry.qsize() > 0:
                    try:
                        self.queue.put(self.retry.get(timeout=0))
                    except queue.Empty:
                        break
                continue
            # if we are asked to stop while scaling images, do so
            if self._stopped:
                break
            # process task
            try:
                with self._tm as t:
                    self._process_one_scale(task, t)
            except Exception as e:  # noqa: never break the loop
                task.setdefault("retry", 0)
                task["retry"] += 1
                if task["retry"] > 10:
                    logger.exception(str(e))
                else:
                    self.retry.put(task)
            # A testing plug
            if not forever:
                break

    def _process_one_scale(self, task, t):
        storage = self._conn.get(task["storage_oid"])
        # build plone.scale storage key
        key = task["parameters"].copy()
        key.pop("quality", None)  # not part of key
        key = tuple(sorted(key.items()))
        values = [v for v in storage.values() if v["key"] == key]
        if values:
            parameters = task["parameters"].copy()
            fieldname = parameters.pop("fieldname", None)
            scale_name = parameters.pop("scale", None)
            with open(task["data"], "rb") as fp:
                data, format_, dimensions = scaleImage(fp, **parameters)
            mimetype = "image/{0}".format(format_.lower())
            value = task["klass"](
                data, contentType=mimetype, filename=task["filename"],
            )
            value.fieldname = fieldname
            for scale in values:
                scale["data"] = value
                storage[scale["uid"]] = scale
            logger.info('/'.join(filter(bool, [task["context"], '@@images', fieldname, scale_name])))
            t.note('/'.join(filter(bool, [task["context"], '@@images', fieldname, scale_name])))

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

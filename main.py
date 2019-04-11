import os
import sys
import logging
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')

from locale import atof, setlocale, LC_NUMERIC
from gi.repository import Notify
from itertools import islice
from subprocess import Popen, PIPE, call, check_output, CalledProcessError
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction


logger = logging.getLogger(__name__)
ext_icon = 'images/icon.png'


class ProcessKillerExtension(Extension):

    def __init__(self):
        super(ProcessKillerExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())
        setlocale(LC_NUMERIC, '')  # set to OS default locale;


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):
        exec_icon = get_theme_icon('application-x-executable', 48)
        return RenderResultListAction(list(islice(self.generate_results(event, exec_icon), 15)))

    def generate_results(self, event, exec_icon):
        for (pid, cpu, cmd) in get_process_list():
            name = '[%s%% CPU] %s' % (cpu, cmd) if cpu > 1 else cmd
            on_enter = {'alt_enter': False, 'pid': pid, 'cmd': cmd}
            on_alt_enter = on_enter.copy()
            on_alt_enter['alt_enter'] = True
            if not event.get_argument() or event.get_argument() in cmd:
                yield ExtensionSmallResultItem(icon=exec_icon,
                                               name=name,
                                               on_enter=ExtensionCustomAction(on_enter),
                                               on_alt_enter=ExtensionCustomAction(on_alt_enter, keep_app_open=True))


class ItemEnterEventListener(EventListener):

    def kill(self, extension, pid, signal, verification_timeout):
        cmd = [sys.executable, 'kill.py', pid, signal, str(verification_timeout)]
        logger.info(' '.join(cmd))

        try:
            call(cmd) == 0
        except Exception as e:
            logger.error('%s: %s' % (type(e).__name__, e.message))
            raise

    def show_signal_options(self, data):
        result_items = []
        options = [('TERM', '15 TERM (default)'), ('KILL', '9 KILL'), ('HUP', '1 HUP')]
        for sig, name in options:
            on_enter = data.copy()
            on_enter['alt_enter'] = False
            on_enter['signal'] = sig
            result_items.append(ExtensionSmallResultItem(icon=ext_icon,
                                                         name=name,
                                                         highlightable=False,
                                                         on_enter=ExtensionCustomAction(on_enter)))
        return RenderResultListAction(result_items)

    def on_event(self, event, extension):
        data = event.get_data()
        timeout = extension.preferences['verification_timeout']
        if data['alt_enter']:
            return self.show_signal_options(data)
        else:
            self.kill(extension, data['pid'], data.get('signal', 'TERM'), timeout)


def get_process_list():
    """
    Returns a list of tuples (PID, %CPU, COMMAND)
    """
    env = os.environ.copy()
    env['COLUMNS'] = '200'
    process = Popen(['top', '-bn1', '-cu', os.getenv('USER')], stdout=PIPE, env=env)
    out = process.communicate()[0]
    for line in out.split('\n'):
        col = line.split()
        try:
            int(col[0])
        except (ValueError, IndexError):
            # not a number
            continue

        pid = col[0]
        cpu = atof(col[8])
        cmd = ' '.join(col[11:])
        if 'top -bn' in cmd:
            continue

        yield (pid, cpu, cmd)

def get_theme_icon(name, size):
    # Run each call in a new throwaway thread to escape Gtk.IconTheme.get_default()'s cache-bug/feature
    getIconCode = "Gtk.IconTheme.get_default().lookup_icon('{}', {}, 0).get_filename()".format(name, size)
    return check_output([sys.executable, '-c', "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk; print({})".format(getIconCode)]).rstrip()

if __name__ == '__main__':
    ProcessKillerExtension().run()

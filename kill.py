import sys
import os
import gi
import subprocess

gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')

from time import sleep
from gi.repository import Gtk, Notify

curr_dir = os.path.dirname(os.path.realpath(__file__))
dead_icon = os.path.join(curr_dir, 'images/dead.png')
[_, pid, signal, timeout] = sys.argv


try:
    timeout = max(float(timeout), 0.0)
except Exception as e:
    # Fallback to default if user has set an invalid timeout (hard-coded for now)
    timeout = 3

def show_dialog(title, message):
    dialog = Gtk.MessageDialog(type=Gtk.MessageType.QUESTION,
                               buttons=Gtk.ButtonsType.YES_NO,
                               message_format=title)
    dialog.format_secondary_text(message)
    yesButton = dialog.get_widget_for_response(response_id=Gtk.ResponseType.YES)
    yesButton.props.has_focus = True
    response = dialog.run()
    dialog.destroy()
    return response

def show_notification(title, text, icon=None, expires=Notify.EXPIRES_DEFAULT, urgency=1):
    Notify.init("KillerExtension")
    message = Notify.Notification.new(title, text, icon)
    message.set_timeout(expires)
    message.set_urgency(urgency)
    message.show()

def kill(signal, pid):
    subprocess.call(['kill', '-s', signal, pid])
    verify(pid)

def verify(pid):
    time = 0
    # Always leave some time to verify, even if user sets this to 0
    verification_timeout = max(timeout, 1)
    while verification_timeout > time:
        try:
            if subprocess.check_output(['ps', '--no-headers', 'q', pid]).strip():
                sleep(0.1)
                time += 0.1
                continue
        except Exception as e:
            # If there's no pid it makes the command exit with non-zero status
            show_notification("Done", "It's dead now", dead_icon)
            sys.exit()

# Try nicely first... (unless signal is KILL)
kill(signal, pid)

# ...then ask again it it's still running (unless disabled in preferences)
if not timeout:
    show_notification("Couldn't stop the process nicely",
                      "You may want to try again with the KILL signal.",
                      urgency=2)
elif signal != 'KILL':
    response = show_dialog("Couldn't stop the process nicely", "Do you want to force it to exit?")

    if response == Gtk.ResponseType.YES:
        kill('KILL', pid)

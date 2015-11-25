# Helper functions and classes to wrap common Sublime Text idioms:
#
import functools
import os

import sublime
import sublime_plugin

def main_thread(callback, *args, **kwargs):

    sublime.set_timeout_async(functools.partial(callback, *args, **kwargs), 0)

class TextCommand(sublime_plugin.TextCommand):

    def get_view_and_window(self, view=None):

        # Find a window to attach any prompts, panels and new views to.
        # If view that was active when the command was run has a window
        # then we can use that:
        #
        if view is None:
            view = self.view

        if view is not None:
            window = view.window()

        # But if the view doesn't have a window, or there is no view at
        # all, then use the active window and view as set in the Sublime
        # module:
        #
        if view is None or window is None:
            window = sublime.active_window()
            view = window.active_view()

        return view, window

    def get_working_dir(self):
        view, window = self.get_view_and_window()
        if view is not None:
            folders = []
            file_name = view.file_name()
            if file_name is not None:
                
                dirname, _ = os.path.split(os.path.abspath(file_name))
                while dirname and len(folders) == 0:
                    dirname , _ = os.path.split(os.path.abspath(dirname))
                    folders = [dirname for f in os.listdir(dirname) if os.path.isfile(os.path.join(dirname, f)) and f == 'build.gradle']

        if len(folders) == 1:
            return folders[0]
        return None

    def get_file_path(self):
        view, window = self.get_view_and_window()
        if view is not None:
            return view.file_name()


    def get_config_dir(self):
        view, window = self.get_view_and_window()
        if view is not None:
             dirname, _ = os.path.split(os.path.abspath(view.file_name()))
             return dirname
        return None



# The command that is executed to insert text into a view:
#
class SublimeHelperInsertTextCommand(sublime_plugin.TextCommand):

    def run(self, edit, pos, msg):

        if msg is not None:
            self.view.insert(edit, pos, msg)


# The command that is executed to erase text in a view:
#
class SublimeHelperEraseTextCommand(sublime_plugin.TextCommand):

    def run(self, edit, a, b):

        self.view.erase(edit, sublime.Region(a, b))


# The command that is executed to clear a buffer:
#
class SublimeHelperClearBufferCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        view.run_command('sublime_helper_erase_text', {'a': 0, 'b': view.size()})


class OutputTarget():

    def __init__(self, window, data_key, command, working_dir, title=None, syntax=None, panel=False, console=None):

        # If a panel has been requested then create one and show it,
        # otherwise create a new buffer, and set its caption:
        #
        if console is not None:
            self.console = console
        else:
            if panel is True:
                self.console = window.get_output_panel('ShellCommand')
                window.run_command('show_panel', {'panel': 'output.ShellCommand'})
            else:
                self.console = window.new_file()
                caption = title if title else '*ShellCommand Output*'
                self.console.set_name(caption)

            # Indicate that this buffer is a scratch buffer:
            #
            self.console.set_scratch(True)
            self.console.set_read_only(True)

            # Set the syntax for the output:
            #
            if syntax is not None:
                resources = sublime.find_resources(syntax + '.tmLanguage')
                self.console.set_syntax_file(resources[0])

            # Set a flag on the view that we can use in key bindings:
            #
            settings = self.console.settings()
            settings.set(data_key, True)

            # Also, save the command and working directory for later,
            # since we may need to refresh the panel/window:
            #
            data = {
            'command': command,
            'working_dir': working_dir
            }
            settings.set(data_key + '_data', data)

            def append_text(self, output, scroll_show_maximum_output=False):

                console = self.console

        # Insert the output into the buffer. If the flag is set to show maximum output
        # then we make the end of the buffer visible:
        #
        console.set_read_only(False)
        console.run_command('sublime_helper_insert_text', {'pos': console.size(), 'msg': output})
        if scroll_show_maximum_output:
            console.run_command('move_to', {'to': 'eof', 'extend': False})
            console.set_read_only(True)

            def set_status(self, tag, message):

                self.console.set_status(tag, message)


# Code largely taken from the nifty class in sublime_package_control:
#
#   https://github.com/wbond/sublime_package_control/blob/master/package_control/thread_progress.py
#
# The minor changes made are simply so that we deal with a view rather than a
# thread, which allows us to relate the status messages more closely with their
# corresponding buffer. It does mean that it's then the caller's responsibility
# to call start() and stop(), though.
#
class ProgressDisplay():
    """
    Animates an indicator, [=   ], in the status area until stopped
    :param view:
    The view that 'owns' the activity
    :param tag:
    The tag to identify the message within sublime
    :param message:
    The message to display next to the activity indicator
    """

    def __init__(self, view, tag, message, heartbeat=None):
        self.view = view
        self.tag = tag
        self.message = message
        self.addend = 1
        self.size = 8
        self.heartbeat = heartbeat if heartbeat is not None else 100
        self.stop()
        sublime.set_timeout(lambda: self.run(), self.heartbeat)

    def start(self):
        self._running = True
        self.counter = 0
        self.run()

    def stop(self):
        self._running = False

    def is_running(self):
        return self._running

    def set_status(self, message):
        self.view.set_status(self.tag, message)

    def set_message(self, message):
        self.message = message

    def run(self):
        if not self.is_running():
            self.set_status('')
            return

        i = self.counter

        before = i % self.size
        after = (self.size - 1) - before

        self.set_status('%s [%s=%s]' % (self.message, ' ' * before, ' ' * after))

        if not after:
            self.addend = -1
        if not before:
            self.addend = 1
        self.counter += self.addend

        sublime.set_timeout(lambda: self.run(), self.heartbeat)

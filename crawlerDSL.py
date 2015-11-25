import sublime
from . import SublimeHelper as SH
import subprocess
import os
import threading
import time


class CrawlerBaseClass(SH.TextCommand):
	window_dict = {}
	def __init__(self, plugin, default_prompt=None, **kwargs):
		SH.TextCommand.__init__(self, plugin, **kwargs)
		if default_prompt is None:
			self.default_prompt = 'CrawlerDSL'
		else:
			self.default_prompt = default_prompt
			self.data_key = 'CrawlerDSL'
			self.output_written = False

	def get_window_dict(self):
		if CrawlerBaseClass.window_dict is None:
			CrawlerBaseClass.window_dict = {}
		return CrawlerBaseClass.window_dict

	def set_status(self, message):
		view, _ = self.get_view_and_window()
		view.set_status("crawler_status", message)

	def set_next_step(self, message):
		view, _ = self.get_view_and_window()
		view.set_status("crawler_next_step", message)


	def get_runner(self):
		print('get_runner')
		_, window = self.get_view_and_window()
		runner = None
		if window.id() in self.get_window_dict() and 'runner' in self.get_window_dict()[window.id()]:
			runner = self.get_window_dict()[window.id()]['runner']
		return runner

	def get_progress(self):
		print('get_progress')
		view, window = self.get_view_and_window()
		progress = None
		if window.id() in self.get_window_dict() and 'progress' in self.get_window_dict()[window.id()]:
			progress = self.get_window_dict()[window.id()]['progress']
		else :
			progress = SH.ProgressDisplay(view, "crawlerDSL_progress", "", 500)
			self.set_progress(progress)
		return progress

	def set_runner(self, runner):
		print('set_runner')
		_, window = self.get_view_and_window()
		if not window.id() in self.get_window_dict() :
			self.get_window_dict()[window.id()] = {}
		self.get_window_dict()[window.id()]['runner'] = runner

	def set_progress(self, progress):
		print('set_progress')
		_, window = self.get_view_and_window()
		if not window.id() in self.get_window_dict() :
			self.get_window_dict()[window.id()] = {}
		self.get_window_dict()[window.id()]['progress'] = progress

	def stop_progress(self):
		progress = self.get_progress()
		if progress:
			progress.stop()

	def start_progress(self):
		progress = self.get_progress()
		if progress:
			progress.start()

	def update_progress(self, message):
		self.get_progress().set_message(message)
		self.get_progress().start()

	def stop_progress(self):
		self.get_progress().stop()

	def run_command(self, command):
		runner = self.get_runner()
		if not runner is None and runner.poll() is None:
			self.set_next_step('')
			self.set_status('')
			self.update_progress(self.default_prompt + ' : running ' + command)
			out, err = runner.communicate(input=command.encode())
			print(out)
			print(err)
		else:
			print('tried to run ' + command + ' but runner is closed or None')

	def stop_runner(self):
		runner = self.get_runner()
		if runner is None:
			print("stop_runner: None runner")
			return
		self.run_command('q')
		return_code = None
		i = 0
		while return_code is None and i < 100:
			i = i + 1
			return_code = runner.poll()
			time.sleep(1/10.0)

		if return_code is None :
			runner.kill()
		self.stop_progress()

	def start_runner(self, start_url):
		runner = self.get_runner()
		view, window = self.get_view_and_window()
		window.set_layout({
			"cols": [0,0.5, 1],
			"rows": [0,0.5,1],
			"cells": [[0,0,1,1],[1,0,2,1],[0,1,1,2],[1,1,2,2]]
			})
		window.focus_group(1)
		result_view = window.open_file(self.get_config_dir()+'/.result.tmp')
		window.focus_group(2)
		result_view = window.open_file(self.get_config_dir()+'/.nextSteps.tmp')
		window.focus_group(3)
		result_view = window.open_file(self.get_config_dir()+'/.current.tmp')
		window.focus_group(0)

		wd = self.get_working_dir()

		
		command = './gradlew runApp -PapplicationArgs="{},{}"'.format(self.get_file_path(), start_url)
		
		bash_env = os.getenv('ENV')

		if bash_env is not None:
			command = '. {} && {}'.format(bash_env, command)

		executable = os.getenv('SHELL')

		self.stop_runner()		
		thr = threading.Thread(target= self.run_in_background, args=(command, executable, wd))
		thr.start()
	
	def run_in_background(self, command, executable, wd, callback=None):
		message = self.default_prompt + ' : starting'
		self.update_progress(message)
		runner = self.get_runner()
		try:
			self.update_progress(message)
			runner = subprocess.Popen( command ,
								shell = True,
								executable=executable,
								stdin = subprocess.PIPE,
								stdout = subprocess.PIPE,
								stderr = subprocess.STDOUT,
								cwd=wd)
			self.set_runner(runner)
			runner_poll = None
			while runner_poll is None:
				runner_poll = runner.poll()
				try:
					data = runner.stdout.readline().decode(encoding='UTF-8')
					if data.startswith('current step'):
						self.stop_progress()
						self.set_status(self.default_prompt + ' : waiting')
						self.set_next_step(data)
					if data.startswith('Exception in thread'):
						self.stop_progress()
						self.set_status(self.default_prompt + data + 'look at the console for more details')
						self.set_next_step('')

					print(data, end ="")
				except Exception as e:
					print(e)
					print("1 process ended...")
					return;
			print("2 process ended...")
			self.stop_progress()
			if callback:
				SH.main_thread(callback, None)
		except OSError as e:
			if e.errno == 2:
				sublime.message_dialog('Command not found\n\nCommand is: %s' % command)
			else:
				raise e
		except:
			raise
		finally:
			print("3 process ended...")
			self.stop_progress()
			if callback:
				SH.main_thread(callback, e.returncode)



class CrawlerRunCommand(CrawlerBaseClass):	
	def run(self, edit):
		print("start runner")
		view, window = self.get_view_and_window()
		def _C(start_url):
			self.start_runner(start_url)
			print("hello3")
		print("hello4")
		window.show_input_panel('Enter start URL', '', _C, None, None)
		print("hello5")

class CrawlerStopCommand(CrawlerBaseClass):
	def run(self, edit):
		print("stop runner")
		self.stop_runner()

class CrawlerNextCommand(CrawlerBaseClass):
	def run(self, edit):
		print("step")
		self.run_command('n')


class CrawlerDeleteCommand(CrawlerBaseClass):
	def run(self, edit):
		print("delete current step")
		self.run_command('d')

class CrawlerRedoCommand(CrawlerBaseClass):
	def run(self, edit):
		print("reload script and redo current step")
		self.run_command('r')

class CrawlerReloadCommand(CrawlerBaseClass):
	def run(self, edit):
		print("reload script")
		self.run_command('rl')


	
		
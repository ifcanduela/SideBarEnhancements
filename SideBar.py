# coding=utf8
import sublime, sublime_plugin
import os
import threading, time
import re

from .SideBarAPI import SideBarItem, SideBarSelection, SideBarProject

global Pref, s, Cache



Pref = {}
s = {}
Cache = {}



def CACHED_SELECTION(paths = []):
	if Cache.cached:
		return Cache.cached
	else:
		return SideBarSelection(paths)



def escapeCMDWindows(string):
	return string.replace('^', '^^')



class Pref():
	def load(self):
		pass



def plugin_loaded():
	global Pref, s
	s = sublime.load_settings('Side Bar.sublime-settings')
	Pref = Pref()
	Pref.load()
	s.clear_on_change('reload')
	s.add_on_change('reload', lambda:Pref.load())



def Window():
	return sublime.active_window()



def expandVars(path):
	for k, v in list(os.environ.items()):
		path = path.replace('%'+k+'%', v).replace('%'+k.lower()+'%', v)
	return path



def window_set_status(key, name =''):
	for window in sublime.windows():
		for view in window.views():
			view.set_status('SideBar-'+key, name)



class Object():
	pass



class Cache():
	pass



Cache = Cache()
Cache.cached = False



class OpenWithListener(sublime_plugin.EventListener):
	def on_load_async(self, view):
		if view and view.file_name() and not view.settings().get('open_with_edit'):
			item = SideBarItem(os.path.join(sublime.packages_path(), 'User', 'SideBarEnhancements', 'Open With', 'Side Bar.sublime-menu'), False)
			if item.exists():
				settings = sublime.decode_value(item.contentUTF8())
				selection = SideBarSelection([view.file_name()])
				for item in settings[0]['children']:
					try:
						if item['open_automatically'] and selection.hasFilesWithExtension(item['args']['extensions']):
							SideBarFilesOpenWithCommand(sublime_plugin.WindowCommand).run([view.file_name()], item['args']['application'], item['args']['extensions'])
							view.window().run_command('close')
							break
					except:
						pass



class aaaaaSideBarCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		pass

	def is_visible(self, paths = []): # <- WORKS AS AN ONPOPUPSHOWING
		Cache.cached = SideBarSelection(paths)
		return False



class SideBarCutCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		s = sublime.load_settings("SideBarEnhancements/Clipboard.sublime-settings")
		items = []
		for item in SideBarSelection(paths).getSelectedItemsWithoutChildItems():
			items.append(item.path())

		if len(items) > 0:
			s.set('cut', "\n".join(items))
			s.set('copy', '')
			if len(items) > 1 :
				sublime.status_message("Items cut")
			else :
				sublime.status_message("Item cut")

	def is_enabled(self, paths = []):
		return CACHED_SELECTION(paths).len() > 0 and CACHED_SELECTION(paths).hasProjectDirectories() == False



class SideBarCopyCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		s = sublime.load_settings("SideBarEnhancements/Clipboard.sublime-settings")
		items = []
		for item in SideBarSelection(paths).getSelectedItemsWithoutChildItems():
			items.append(item.path())

		if len(items) > 0:
			s.set('cut', '')
			s.set('copy', "\n".join(items))
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return CACHED_SELECTION(paths).len() > 0



class SideBarPasteCommand(sublime_plugin.WindowCommand):
	def run(self, paths = [], in_parent = 'False', test = 'True', replace = 'False'):
		key = 'paste-'+str(time.time())
		SideBarPasteThread(paths, in_parent, test, replace, key).start()

	def is_enabled(self, paths = [], in_parent = False):
		s = sublime.load_settings("SideBarEnhancements/Clipboard.sublime-settings")
		return (s.get('cut', '') + s.get('copy', '')) != '' and len(CACHED_SELECTION(paths).getSelectedDirectoriesOrDirnames()) == 1

	def is_visible(self, paths = [], in_parent = False):
		if in_parent == 'True':
			return not s.get('disabled_menuitem_paste_in_parent', False)
		else:
			return True



class SideBarPasteThread(threading.Thread):
	def __init__(self, paths = [], in_parent = 'False', test = 'True', replace = 'False', key = ''):
		self.paths = paths
		self.in_parent = in_parent
		self.test = test
		self.replace = replace
		self.key = key
		threading.Thread.__init__(self)

	def run(self):
		SideBarPasteCommand2(sublime_plugin.WindowCommand).run(self.paths, self.in_parent, self.test, self.replace, self.key)



class SideBarPasteCommand2(sublime_plugin.WindowCommand):
	def run(self, paths = [], in_parent = 'False', test = 'True', replace = 'False', key = ''):
		window_set_status(key, 'Pasting…')

		s = sublime.load_settings("SideBarEnhancements/Clipboard.sublime-settings")

		cut = s.get('cut', '')
		copy = s.get('copy', '')

		already_exists_paths = []

		if SideBarSelection(paths).len() > 0:
			if in_parent == 'False':
				location = SideBarSelection(paths).getSelectedItems()[0].path()
			else:
				location = SideBarSelection(paths).getSelectedDirectoriesOrDirnames()[0].dirname()

			if os.path.isdir(location) == False:
				location = SideBarItem(os.path.dirname(location), True)
			else:
				location = SideBarItem(location, True)

			if cut != '':
				cut = cut.split("\n")
				for path in cut:
					path = SideBarItem(path, os.path.isdir(path))
					new  = os.path.join(location.path(), path.name())
					if test == 'True' and os.path.exists(new):
						already_exists_paths.append(new)
					elif test == 'False':
						if os.path.exists(new) and replace == 'False':
							pass
						else:
							try:
								if not path.move(new, replace == 'True'):
									window_set_status(key, '')
									sublime.error_message("Unable to cut and paste, destination exists.")
									return
							except:
								window_set_status(key, '')
								sublime.error_message("Unable to move:\n\n"+path.path()+"\n\nto\n\n"+new)
								return

			if copy != '':
				copy = copy.split("\n")
				for path in copy:
					path = SideBarItem(path, os.path.isdir(path))
					new  = os.path.join(location.path(), path.name())
					if test == 'True' and os.path.exists(new):
						already_exists_paths.append(new)
					elif test == 'False':
						if os.path.exists(new) and replace == 'False':
							pass
						else:
							try:
								if not path.copy(new, replace == 'True'):
									window_set_status(key, '')
									sublime.error_message("Unable to copy and paste, destination exists.")
									return
							except:
								window_set_status(key, '')
								sublime.error_message("Unable to copy:\n\n"+path.path()+"\n\nto\n\n"+new)
								return

			if test == 'True' and len(already_exists_paths):
				self.confirm(paths, in_parent, already_exists_paths, key)
			elif test == 'True' and not len(already_exists_paths):
				SideBarPasteThread(paths, in_parent, 'False', 'False', key).start();
			elif test == 'False':
				cut = s.set('cut', '')
				SideBarProject().refresh();
				window_set_status(key, '')
		else:
			window_set_status(key, '')

	def confirm(self, paths, in_parent, data, key):
		import functools
		window = sublime.active_window()
		window.show_input_panel("BUG!", '', '', None, None)
		window.run_command('hide_panel');

		yes = []
		yes.append('Yes, Replace the following items:');
		for item in data:
			yes.append(SideBarItem(item, os.path.isdir(item)).pathWithoutProject())

		no = []
		no.append('No');
		no.append('Continue without replacing');

		while len(no) != len(yes):
			no.append('ST3 BUG');

		window.show_quick_panel([yes, no], functools.partial(self.on_done, paths, in_parent, key))

	def on_done(self, paths, in_parent, key, result):
		window_set_status(key, '')
		if result != -1:
			if result == 0:
				SideBarPasteThread(paths, in_parent, 'False', 'True', key).start()
			else:
				SideBarPasteThread(paths, in_parent, 'False', 'False', key).start()



class SideBarDuplicateCommand(sublime_plugin.WindowCommand):
	def run(self, paths = [], new = False):
		import functools
		Window().run_command('hide_panel');
		view = Window().show_input_panel("Duplicate As:", new or SideBarSelection(paths).getSelectedItems()[0].path(), functools.partial(self.on_done, SideBarSelection(paths).getSelectedItems()[0].path()), None, None)
		view.sel().clear()
		view.sel().add(sublime.Region(view.size()-len(SideBarSelection(paths).getSelectedItems()[0].name()), view.size()-len(SideBarSelection(paths).getSelectedItems()[0].extension())))

	def on_done(self, old, new):
		key = 'duplicate-'+str(time.time())
		SideBarDuplicateThread(old, new, key).start()

	def is_enabled(self, paths = []):
		return CACHED_SELECTION(paths).len() == 1 and CACHED_SELECTION(paths).hasProjectDirectories() == False



class SideBarDuplicateThread(threading.Thread):
	def __init__(self, old, new, key):
		self.old = old
		self.new = new
		self.key = key
		threading.Thread.__init__(self)

	def run(self):
		old = self.old
		new = self.new
		key = self.key
		window_set_status(key, 'Duplicating…')

		item = SideBarItem(old, os.path.isdir(old))
		try:
			if not item.copy(new):
				window_set_status(key, '')
				if SideBarItem(new, os.path.isdir(new)).overwrite():
					self.run()
				else:
					SideBarDuplicateCommand(sublime_plugin.WindowCommand).run([old], new)
				return
		except:
			window_set_status(key, '')
			sublime.error_message("Unable to copy:\n\n"+old+"\n\nto\n\n"+new)
			SideBarDuplicateCommand(sublime_plugin.WindowCommand).run([old], new)
			return
		item = SideBarItem(new, os.path.isdir(new))
		if item.isFile():
			item.edit();
		SideBarProject().refresh();
		window_set_status(key, '')



class zzzzzSideBarCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		pass

	def is_visible(self, paths = []): # <- WORKS AS AN ONPOPUPSHOWN
		Cache.cached = False
		return False

import os
import json
import threading


class Db(object):

	def __init__(self, db_file):
		self._db_file = db_file
		self._failed_files = []
		
		if not os.path.exists(db_file):
			self._db_data = {
				'files': {},
				'studios': {},
				'dates': {}
			}
			self.save()
		else:
			with open(db_file) as f:
				self._db_data = json.load(f)

		self._lock = threading.Lock()

	@property
	def studios(self):
		studios = self._db_data['studios']
		if 'done' not in studios:
			studios['done'] = []

		return studios

	@property
	def dates(self):
		dates = self._db_data['dates']
		if 'done' not in dates:
			dates['done'] = []
		if 'spreadsheet' not in dates:
			dates['spreadsheet'] = []

		return dates

	@property
	def files_data(self):
		return self._db_data['files']

	def save(self):
		with open(self._db_file, 'w') as a:
			json.dump(self._db_data, a)

	def update_studio_done(self, studio_id):
		self.studios['done'].append(studio_id)
		self.save()

	def is_studio_done(self, studio_id):
		return studio_id in self.studios['done']

	def file_downloaded(self, file_id, file_path, title, parent_id):
		self._lock.acquire()
		try:
			self._db_data['files'][file_id] = {
				'id': file_id, 
				'title': title, 
				'file_path': file_path, 
				'parent_id': parent_id,
				'converted': None,
				'to_upload': False,
				'uploaded': False}
			self.save()
		finally:
			self._lock.release()

	def was_file_downloaded(self, file_id):
		return file_id in self._db_data['files']

	def file_converted(self, file_id, file_path):
		self._db_data['files'][file_id]['converted'] = file_path
		self._db_data['files'][file_id]['to_upload'] = True
		self.save()

	def was_converted(self, file_id):
		return self.files_data[file_id]['converted'] != None

	def file_uploaded(self, file_id):
		self.files_data[file_id]['uploaded'] = True
		self.files_data[file_id]['to_upload'] = False
		self.save()

	def was_uploaded(self, file_id):
		return self.files_data[file_id]['uploaded']

	def update_date_done(self, date_id):
		self.dates['done'].append(date_id)
		self.save()

	def is_date_done(self, date_id):
		return date_id in self.dates['done']

	def update_date_spreadsheet_done(self, date_id):
		self.dates['spreadsheet'].append(date_id)
		self.save()

	def is_date_spreadsheet_done(self, date_id):
		return date_id in self.dates['spreadsheet']

	def file_failed(self, file_id, parent_id, title, error):
		self._lock.acquire()
		try:
			self._failed_files.append({'id': file_id, 'parent_id': parent_id, 'title': title, 'error': unicode(error)})
			self.save()
		finally:
			self._lock.release()

	def files_failed(self):
		return self._failed_files

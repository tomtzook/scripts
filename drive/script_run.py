# -*- coding: utf-8 -*-

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os
import shutil
from drive import *
import topdf
import update_spreadsheet
import shutil
import sys
from db import Db
from concurrent.futures import ThreadPoolExecutor

THREAD_WORKERS = 4


class ScriptContext(object):

	def __init__(self, drive, db, tmp_folder, root_files, thread_executor):
		self._drive = drive
		self._db = db
		self._tmp_folder = tmp_folder
		self._root_files = root_files
		self._thread_executor = thread_executor

	@property
	def drive(self):
		return self._drive

	@property
	def db(self):
		return self._db

	@property
	def tmp_folder(self):
		return self._tmp_folder

	@property
	def root_files(self):
		return self._root_files
	
	def run_date(self, date_str):
		dateid = get_id_for_date(self.root_files, date_str)
		self._run_date_file_manipulation(dateid, date_str)
		self._run_date_spreadsheet_update(dateid, date_str)

	def _run_date_spreadsheet_update(self, dateid, date_str):
		if self.db.is_date_spreadsheet_done(dateid):
			print 'Done spreadsheet update', date, '...skipping'
			return

		update_spreadsheet.update_spreadsheet_for_date(self.drive, self.root_files, date_str, 
			'spreadsheet_full.{0}.xlsx'.format(date_str))

		self.db.update_spreadsheet_for_date(dateid)	

	def _run_date_file_manipulation(self, dateid, date_str):
		if self.db.is_date_done(dateid):
			print 'Done date', date_str, '...skipping'
			return

		files_in_date = get_files_with_parentid(self.drive, dateid)
		failed_files = []

		for f in files_in_date:
			if f['mimeType'] != u'application/vnd.google-apps.folder':
				continue
			if self.db.is_studio_done(f['id']):
				print 'Done', f['title'], '.. skipping'
				continue

			print 'Download studio', f['title']
			self._download_folder(f['id'])
			print 'Done studio download', f['title']

			print 'Converting'
			self._convert_files()
			print 'Uploading'
			self._upload_files()

			self.db.update_studio_done(f['id'])

		self.db.update_date_done(dateid)

	def _download_folder(self, folder_id):
		files = self._files_from_folder(folder_id)
		it = self._thread_executor.map(self._download_file, files)
		for i in it:
			pass

	def _files_from_folder(self, folder_id):
		file_list = get_files_with_parentid(self.drive, folder_id)

		files = []
		for file_data in file_list:
			if file_data['title'].endswith('.ppt') or file_data['title'].endswith('.pptx'):
				if self.db.was_file_downloaded(file_data['id']):
					print 'Already downloaded', file_data['title']
					continue

				files.append((file_data, folder_id))
			elif file_data['mimeType'] == u'application/vnd.google-apps.folder':
				print 'Sub folder', file_data['title']
				files.extend(self._files_from_folder(file_data['id']))

		return files

	def _download_file(self, data):
		try:
			file_data, parent_id = data

			print 'Downloading', file_data['title']

			local_file = os.path.join(self.tmp_folder, file_data['title'])

			if not os.path.exists(local_file):
				file = self.drive.CreateFile({'id': file_data['id']})
				file.GetContentFile(file_data['title'])
				shutil.move(file_data['title'], local_file)
			else:
				print 'file already exists'

			self.db.file_downloaded(file_data['id'], local_file, file_data['title'], parent_id)
		except Exception as e:
			print 'Error downloading', unicode(e)
			self.db.file_failed(file_data['id'], folder_id, file_data['title'], e)

	def _convert_files(self):
		files_data = [data for data in self.db.files_data.itervalues() if data['converted'] == None]
		source_files = [data['file_path'] for data in files_data]
		converted = topdf.batch_convert_to_pdf(source_files, self.tmp_folder)

		for i in xrange(len(converted)):
			converted_path = converted[i]
			fid = files_data[i]['id']
			self.db.file_converted(fid, converted_path)

	def _upload_files(self):
		to_upload = [file_data for file_data in self.db.files_data.itervalues() if file_data['to_upload'] and not file_data['uploaded']]
		to_upload_count = len(to_upload)
		done = 0

		for file_data in to_upload:
			print 'Uploading', file_data['converted']
			file = self.drive.CreateFile({'id': file_data['id'], 
				'parents': [{'id': file_data['parent_id']}]})
			file.SetContentFile(file_data['converted'])

			file.Upload()
			done += 1
			print 'Done', '({0}/{1})'.format(done, to_upload_count)


def main():
	if len(sys.argv) < 2:
		print 'missing date'
		exit()

	tmp_folder = '/home/tomtzook/storage/drivescript'
	if not os.path.exists(tmp_folder):
		os.mkdir(tmp_folder)

	db = Db('script.db.json')

	gauth = GoogleAuth()
	gauth.LocalWebserverAuth()
	drive = GoogleDrive(gauth)

	root_title = u'ישן'
	rootid = get_root_id(drive, root_title)
	root_files = get_files_with_parentid(drive, rootid)

	with ThreadPoolExecutor(max_workers = THREAD_WORKERS) as executor:
		context = ScriptContext(drive, db, tmp_folder, root_files, executor)

		for i in xrange(1, len(sys.argv)):
			date = sys.argv[i]

			print 'Running date:', date
			context.run_date(date)

main()
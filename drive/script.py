# -*- coding: utf-8 -*-

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from drive import *
import topdf
import update_spreadsheet
import os
import shutil
import json
import sys

REPLACE_UPLOADED = False

class Db(object):

	def __init__(self, db_file):
		self._db_file = db_file
		
		if not os.path.exists(db_file):
			self._db_data = {
				'studios': {},
				'dates': {},
				'failed_files': []
			}
			self.save()
		else:
			with open(db_file) as f:
				self._db_data = json.load(f)

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

		return dates

	def save(self):
		with open(self._db_file, 'w') as a:
			json.dump(self._db_data, a)

	def update_studio_done(self, studio_id):
		self.studios['done'].append(studio_id)
		self.save()

	def is_studio_done(self, studio_id):
		return studio_id in self.studios['done']

	def update_date_done(self, date_id):
		self.dates['done'].append(date_id)
		self.save()

	def is_date_done(self, date_id):
		return date_id in self.dates['done']

	def file_failed(file_id, parent_id, title):
		self._db_data['failed_files'].append({'id': file_id, 'parent_id': parent_id, 'title': title})
		self.save()

	def files_failed():
		return self._db_data['failed_files']


def get_file(drive, file_data, tmp_folder, parent_id):
	local_file = os.path.join(tmp_folder, file_data['title'])

	if not os.path.exists(local_file):
		file = drive.CreateFile({'id': file_data['id']})
		file.GetContentFile(file_data['title'])
		os.rename(file_data['title'], local_file)
	else:
		print 'file already exists'

	return local_file

def convert_file(drive, file_data, tmp_folder, parent_id):
	pdf_path, pdf_name = topdf.convert_to_pdf(local_file)

	file = drive.CreateFile({'title': pdf_name, 'parents': [{'id': parent_id}]})
	file.SetContentFile(pdf_path)
	return file

def convert_files(drive, files, tmp_folder, parent_id):
	converted = topdf.batch_convert_to_pdf(files, tmp_folder)
	for i in xrange(len(converted)):
		pdf_path = converted[i]
		pdf_name = os.path.basename(pdf_path)
		converted[i] = drive.CreateFile({'title': pdf_name, 'parents': [{'id': parent_id}]})
		converted[i].SetContentFile(pdf_path)

	return converted


def reset_tmp(tmp_folder):
	if os.path.exists(tmp_folder):
		shutil.rmtree(tmp_folder)
	os.mkdir(tmp_folder)

def check_uploaded(files_in_folder, file_title):
	expected_name = os.path.splitext(file_title)[0] + '.pdf'
	for f in files_in_folder:
		if f['title'] == expected_name:
			return f['id']
	return None

def do_folder(drive, folder_id, tmp_folder):
	files = get_files_with_parentid(drive, folder_id)
	downloaded_files = []
	converted_files = []
	failed_files = []

	for f in files:
		if f['title'].endswith('.ppt') or f['title'].endswith('.pptx'):
			if REPLACE_UPLOADED:
				upid = check_uploaded(files, f['title'])
				if upid != None:
					print 'Found pdf for', f['title']
					up = drive.CreateFile({'id': upid})
					up.Delete()

			print 'Downloading', f['title']
			try:
				local_file = get_file(drive, f, tmp_folder, folder_id)
				downloaded_files.append(local_file)
			except Exception as e:
				print 'Error'
				failed_files.append((f, e))
		elif f['mimeType'] == u'application/vnd.google-apps.folder':
			print 'Sub folder', f['title']
			conv, failed = do_folder(drive, f['id'], tmp_folder)
			converted_files.extend(conv)
			failed_files.extend(failed)

	print 'Converting', len(downloaded_files), 'files'
	converted_files.extend(convert_files(drive, downloaded_files, tmp_folder, folder_id))

	return converted_files, failed_files


def do_studio_full(drive, studio_id, tmp_folder):
	converted_files, failed_files = do_folder(drive, studio_id, tmp_folder)
	
	for f in converted_files:
		print 'Uploading', f
		f.Upload()
		print 'Done upload'

	return failed_files

def do_full(db, drive, root_files, tmp_folder, date_str):
	date = date_str

	files_in_date = get_files_with_parentid(drive, dateid)
	failed_files = []
	done_studios = [u'']

	for f in files_in_date:
		if f['mimeType'] != u'application/vnd.google-apps.folder':
			continue
		if f['title'] in done_studios or db.is_studio_done(f['id']):
			print 'Done', f['title'], '...skipping'
			continue

		print 'Do studio', f['title']
		failed_files.extend(do_studio_full(drive, f['id'], tmp_folder))
		print 'Done studio', f['title']
		db.update_studio_done(f['id'])

		reset_tmp(tmp_folder)

	print 'Failed files'

	for f, e in failed_files:
		print '\t', f['title'], unicode(e)
		db.file_failed(f['id'], f['parents'][0]['id'], f['title'])



def do_update_spreadsheet(drive, root_files, date_str, path):
	update_spreadsheet.update_spreadsheet_for_date(drive, root_files, date_str, path)

if len(sys.argv) < 2:
	print 'missing date'
	exit()

db = Db('db.json')

gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

#root_title = u'מערכת השידורים'
root_title = u'ישן'
rootid = get_root_id(drive, root_title)
root_files = get_files_with_parentid(drive, rootid)

#if os.path.exists('tmp'):
#	shutil.rmtree('tmp')
#os.mkdir('tmp')

#do_update_spreadsheet(drive, root_files)

for i in xrange(1, len(sys.argv)):
	date = sys.argv[i]

	print 'Running date:', date

	dateid = get_id_for_date(root_files, date)
	if db.is_date_done(dateid):
		print 'Done date', date, '...skipping'
		continue

	do_full(db, drive, root_files, 'tmp', date)
	do_update_spreadsheet(drive, root_files, date, 'full_spreadsheet.{0}.xlsx'.format(date))

	db.update_date_done(dateid)
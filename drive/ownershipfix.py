# -*- coding: utf-8 -*-

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from drive import *
import os
import json
import shutil
import sys
import update_spreadsheet

DOWNLOAD_DIR = '/home/tomtzook/storage/drivefix'

class Db(object):

	def __init__(self, db_file):
		self._db_file = db_file
		
		if not os.path.exists(db_file):
			self._db_data = {
				'files': [],
				'downloaded': [],
				'uploaded': [],
				'studios': {}
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

	def save(self):
		with open(self._db_file, 'w') as a:
			json.dump(self._db_data, a)

	def update_studio_done(self, studio_id):
		self.studios['done'].append(studio_id)
		self.save()

	def is_studio_done(self, studio_id):
		return studio_id in self.studios['done']

	def file_downloaded(self, file_id, file_path, title, parent_id):
		self._db_data['files'].append({'id': file_id, 'title': title, 'file_path': file_path, 'parent_id': parent_id})
		self._db_data['downloaded'].append(file_id)
		self.save()

	def was_file_downloaded(self, file_id):
		return file_id in self._db_data['downloaded']

	def downloaded_files(self):
		return self._db_data['files']

	def file_uploaded(self, file_id):
		self._db_data['uploaded'].append(file_id)
		self.save()

	def was_uploaded(self, file_id):
		return file_id in self._db_data['uploaded']		

	def uploaded_files(self):
		return self._db_data['uploaded']

def check_owner_me(file_data):
	for owner in file_data['owners']:
		if owner['emailAddress'] == 'tomtzook@gmail.com':
			return True
	return False

def get_file(drive, file_data, download_path, parent_id):
	local_file = os.path.join(download_path, file_data['title'])

	if not os.path.exists(local_file):
		file = drive.CreateFile({'id': file_data['id']})
		file.GetContentFile(file_data['title'])
		shutil.move(file_data['title'], local_file)

		file.Delete()
	else:
		print 'file already exists'

	return local_file

def download_folder(db, drive, folder_id, download_path):
	files = get_files_with_parentid(drive, folder_id)
	failed_files = []

	for f in files:
		if f['title'].endswith('.pdf') and check_owner_me(f) and not db.was_file_downloaded(f['id']):
			print 'Downloading', f['title']
			try:
				local_file = get_file(drive, f, download_path, folder_id)
				db.file_downloaded(f['id'], local_file, f['title'], folder_id)
			except Exception as e:
				print 'Error', unicode(e)
				failed_files.append((f, e))
		elif f['mimeType'] == u'application/vnd.google-apps.folder':
			print 'Sub folder', f['title']
			failed = download_folder(db, drive, f['id'], download_path)
			failed_files.extend(failed)

	return failed_files


def download_in_date(db, drive, root_files, download_path, date_str):
	dateid = get_id_for_date(root_files, date_str)
	files_in_date = get_files_with_parentid(drive, dateid)
	failed_files = []

	for f in files_in_date:
		if f['mimeType'] != u'application/vnd.google-apps.folder':
			continue
		if db.is_studio_done(f['id']):
			print 'Done', f['title'], '.. skipping'
			continue

		print 'Do studio', f['title']
		failed_files.extend(download_folder(db, drive, f['id'], download_path))
		print 'Done studio', f['title']
		db.update_studio_done(f['id'])

def upload_all(db, drive):
	uploaded = 0
	total_to_upload = len(db.downloaded_files()) - len(db.uploaded_files())
	print 'Files to upload:', str(total_to_upload)

	for f in db.downloaded_files():
		local_file = f['file_path']
		parent_id = f['parent_id']
		title = f['title']
		last_id = f['id']

		if not os.path.exists(local_file):
			print 'Missing local file', local_file
			total_to_upload -= 1
			continue

		if db.was_uploaded(last_id):
			print 'Already uploaded', f['title']
			uploaded += 1
			continue

		skip = False
		for file_in_drive in drive.ListFile({'q':u"title='{0}'".format(f['title'])}).GetList():
			if not check_owner_me(file_in_drive):
				print 'Found file in drive', f['title']
				uploaded += 1
				db.file_uploaded(last_id)
				skip = True
				break
		if skip:
			continue

		file = drive.CreateFile({'title': title, 'parents': [{'id': parent_id}]})
		file.SetContentFile(local_file)

		print 'Uploading', file
		file.Upload()
		uploaded += 1
		print 'Done uploading', '({0}/{1})'.format(str(uploaded), str(total_to_upload))

		db.file_uploaded(last_id)

#-------------------------------------

if len(sys.argv) < 2:
	print 'missing dates'
	exit()

if not os.path.exists(DOWNLOAD_DIR):
	os.mkdir(DOWNLOAD_DIR)

db = Db('ownershipfix.db.json')

gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

#root_title = u'מערכת השידורים'
root_title = u'ישן'
rootid = get_root_id(drive, root_title)
root_files = get_files_with_parentid(drive, rootid)

for i in xrange(1, len(sys.argv)):
	print 'Downloading date:', sys.argv[i]
	download_in_date(db, drive, root_files, DOWNLOAD_DIR, sys.argv[i])

#-------------------------------------

#gauth = GoogleAuth()
#gauth.LocalWebserverAuth()
#drive = GoogleDrive(gauth)

#root_title = u'מערכת השידורים'
#root_title = u'ישן'
#rootid = get_root_id(drive, root_title)
#root_files = get_files_with_parentid(drive, rootid)

upload_all(db, drive)

for i in xrange(1, len(sys.argv)):
	print 'Spreadsheet update for date:', sys.argv[i]
	update_spreadsheet.update_spreadsheet_for_date(drive, root_files, sys.argv[i], 'ownershipfix.{0}.xlsx'.format(sys.argv[i]))

#do_download(db, DOWNLOAD_DIR, '2.4')
#do_upload(db)

#upload_all(db, drive)
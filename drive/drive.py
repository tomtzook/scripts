

def get_files_with_parentid(drive, parent_id):
	return drive.ListFile({'q': "'{0}' in parents and trashed=false".format(parent_id)}).GetList()

def get_id_from_list_by_title(file_list, title):
	for f in file_list:
		if f['title'] == title:
			return f['id']

	raise ValueError('not found ' + title)

def get_id_from_list_by_shortcut_title(drive, file_list, title):
	for f in file_list:
		if f['title'] == title:
			if f['mimeType'] == u'application/vnd.google-apps.shortcut':
				f = drive.CreateFile({'id': f['id']})
				f.FetchMetadata(fetch_all=True)
				return f['shortcutDetails']['targetId']

			return f['id']

	raise ValueError('not found ' + title)

def get_root_id(drive, title):
	#fl = drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
	#fl = drive.ListFile({'q': "sharedWithMe=true and trashed=false"}).GetList()

	fl = drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
	return get_id_from_list_by_shortcut_title(drive, fl, title)

def get_id_for_date(root_files, date):
	for f in root_files:
		if f['title'].find(date) > 0:
			return f['id']

	raise ValueError('not found ' + date)
# -*- coding: utf-8 -*-

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from drive import *
import update_spreadsheet
import sys


if len(sys.argv) < 2:
	print 'missing dates'
	exit()

gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

#root_title = u'מערכת השידורים'
root_title = u'ישן'
rootid = get_root_id(drive, root_title)
root_files = get_files_with_parentid(drive, rootid)

for i in xrange(1, len(sys.argv)):
	print 'Spreadsheet update for date:', sys.argv[i]
	update_spreadsheet.update_spreadsheet_for_date(drive, root_files, sys.argv[i], 
		'spreadsheet_manual.{0}.xlsx'.format(sys.argv[i]))
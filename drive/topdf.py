import os
import shutil

def convert_to_pdf(source_file):
	pdf_path = os.path.splitext(source_file)[0] + '.pdf'
	pdf_output = os.path.basename(pdf_path)
	
	if not os.path.exists(pdf_path):
		command = u'libreoffice --headless --invisible --convert-to pdf "{}"'.format(source_file)
		#command = u'unoconv -f pdf "{}"'.format(source_file)
		print command

		os.system(command.encode('utf-8'))
		print 'Done command'

		os.rename(pdf_output, pdf_path)

	return pdf_path, pdf_output


def batch_convert_to_pdf(source_files, destination_folder):
	destination_files = [os.path.splitext(source_file)[0] + '.pdf' for source_file in source_files]
	
	non_existing_sources = []
	for i in xrange(len(source_files)):
		if not os.path.exists(destination_files[i]):
			non_existing_sources.append(source_files[i].replace('"', '\\"'))
		else:
			print 'File already converted', source_files[i]

	if len(non_existing_sources) > 0:
		command = u'libreoffice --headless --invisible --convert-to pdf --outdir {0} "{1}"'.format(destination_folder, '" "'.join(non_existing_sources))
		print command

		os.system(command.encode('utf-8'))
		print 'Done command'

	return destination_files
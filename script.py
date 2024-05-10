import inquirer
import glob
import subprocess
import datetime
import time
import sys
import os
import pyodbc
import traceback
from colorama import Fore, Back, Style, init

######### August 16th 2021 ##############
######### Al Hussain    ##############

######### October 27th 2023 ############
######### Updated image path from /home/winsys/ to /media/images#############
######### Al Hussain ###############

## init for colorama
init()
print(Fore.GREEN)

print("OS Programming Tool")
print("--This tool copies an image file to any attached storage using bmap-tools")
print("--Requires an image file and bmap file created using bmap-tools")
print("--files must be in /media/images/ directory\n\n")

print(Style.RESET_ALL)
date = datetime.datetime.now()
print(date)

while True:
	try:
		value = input("Enter Serial Number: ")
		value = value.strip()
		print("YY = ", value[:2])
		print("MM = ", value[2:4])
		if (len(value) == 10) and (int(value[:2]) > 20) and (0 < int(value[2:4]) <= 12):
			sn = value
			break;
		else:
			print("Entered number not recognized - Try Again.")
	except KeyboardInterrupt:
		raise

try:
######### Calls subprocess for getting available physical disks and prepares a list of strings ###########
#####################################################################################################
	call = subprocess.Popen(['hwinfo','--disk','--short'],stdout=subprocess.PIPE)
	#disk_choice = subprocess.check_output(['grep','-v','sda\|disk:'],stdin=call.stdout).decode('ascii')
	disk_choice = subprocess.check_output(['grep','/dev'],stdin=call.stdout).decode('ascii')
	call.wait()
	call.kill()
	disk_choice = disk_choice.split('\n')
	for x in range(len(disk_choice)):
		#disk_choice[x] = disk_choice[x].replace('Disk','')
		disk_choice[x] = disk_choice[x].strip()
		#disk_choice[x] = disk_choice[x].split(' ',1)[0]
	disk_choice = list(filter(None,disk_choice))

######### Returns list of image files #######################################################
#############################################################################################
	ext = ('.img','.bz2','.gz','.tgz')
	files = []
	for z in ext:
		files.extend(glob.glob('/media/images/*'+z))

######### Ask questions for image selection and physical disk ###############################
#############################################################################################
	question = [inquirer.List('imgfile', message = "Select image file: ", choices = files),
		inquirer.List('disk', message = "Select physical disk: ", choices = disk_choice)]
	answer = inquirer.prompt(question)
	answer['disk'] = answer['disk'].split(' ',1)[0]

######## Wipe existing partition table ######################################################
#############################################################################################
	subprocess.run(['wipefs','-a',answer['disk']],capture_output=True,check=True)

######## Calls bmaptool to copy image to disk ###############################################
#############################################################################################
	cmd = ["bmaptool","copy",answer['imgfile'],answer['disk']]
	full_output = ''
	full_error = ''

	popen =  subprocess.Popen(cmd,stdout=sys.stdout,stderr=sys.stderr,universal_newlines=True)
	try:
		outs, errs = popen.communicate()
	except:
		popen.kill()
	if popen.wait():
		raise RuntimeError('FAILURE - Error occurred during bmaptool execution.')



######## Resize last partition #############################################################
############################################################################################

	ntfs = False
	time.sleep(10)
	print("\nChecking if NTFS partition exists...")
	proc1 = subprocess.Popen(['lsblk','-f','-p',answer['disk']],stdout=subprocess.PIPE)
	proc2 = subprocess.Popen(['grep','-c','ntfs'],stdin=proc1.stdout,stdout=subprocess.PIPE)
	outs, errs = proc2.communicate()
	#print(outs)
	ntfs = bool(int(outs.decode('ascii').strip()))
	if ntfs:
		print("Found NTFS partition...")
	proc1.kill()
	try:
		print("Getting Partition Info...\n")
		subprocess.run(['sgdisk','-e',answer['disk']],capture_output=True,check=True)
		subprocess.run(['sgdisk','-v',answer['disk']],capture_output=True,check=True)
		call1 = subprocess.Popen(['parted','-s',answer['disk'],'print'],stdout=subprocess.PIPE)
		call2 = subprocess.Popen(['grep','-o','^ [0-9] '],stdin=call1.stdout,stdout=subprocess.PIPE)
		call1.wait()
		call3 = subprocess.check_output(['tail','-1'],stdin=call2.stdout).decode('ascii')
		call2.wait()
		parted_num = call3.strip()

		print("Partition Number "+parted_num+" on "+answer['disk']+"...")
		print("Resizing Partition...\n")
		popen = subprocess.Popen(['parted','-s',answer['disk'],'resizepart',parted_num,'100%'],stdout=sys.stdout,stderr=sys.stderr,universal_newlines=True)
		try:
			outs, errs = popen.communicate()
		except:
			popen.kill()
		if popen.wait():
			raise RuntimeError('FAILURE - Error occurred during resising partition.')

		call1 = subprocess.Popen(['hwinfo','--partition','--short'],stdout=subprocess.PIPE)
		call2 = subprocess.Popen(['grep','-o',answer['disk']+'.*'+parted_num],stdin=call1.stdout,stdout=subprocess.PIPE)
		call3 = subprocess.check_output(['tail','-1'],stdin=call2.stdout).decode('ascii')
		call1.wait()
		partition = call3.strip()
		print("Resizing File System...\n")

		if ntfs:
			popen = subprocess.Popen(['ntfsresize','-f',partition],stdout=sys.stdout,stderr=sys.stderr,universal_newlines=True)
			try:
				outs, errs = popen.communicate()
			except:
				popen.kill()
			if popen.wait():
				raise RuntimeError('FAILURE - Error occurred during filesystem resize (ntfsresize).')

			#popen = subprocess.Popen(['ntfsfix',partition],stdout=sys.stdout,stderr=sys.stderr,universal_newline=True)
			#try:
			#	outs, errs = popen.communicate()
			#except:
			#	popen.kill()
			#if popen.wait():
			#	raise RuntimeError('FAILURE - Error occurred during filesystem resize (ntfsresize).')
		else:
			popen = subprocess.Popen(['e2fsck','-f','-y','-v','-t',partition],stdout=sys.stdout,stderr=sys.stderr,universal_newlines=True)
			try:
				outs, errs = popen.communicate()
			except:
				popen.kill()
			if popen.wait():
				raise RuntimeError('FAILURE - Error occurred during filesystem resize (e2fsck).')

			popen = subprocess.Popen(['resize2fs','-p',partition],stdout=sys.stdout,stderr=sys.stderr,universal_newlines=True)
			try:
				outs, errs = popen.communicate()
			except:
				popen.kill()
			if popen.wait():
				raise RuntimeError('FAILURE - Error occurred during fileystem resize (resize2fs).')
	except Exception as e:
		raise



######## Log to ARAS Database ##############################################################
############################################################################################


	supdict = {'ws_serial_num':'','Sup_Description':'','Sup_Value':'','time_start':datetime.datetime(1,1,1)}
	supdict ['ws_serial_num'] = sn
	supdict['Sup_Description'] = 'OS Image'
	supdict['Sup_Value'] = answer['imgfile'].split('/')[-1]
	supdict['time_start'] = date

#	print(supdict)

	placeholders = ', '.join(['?'] * len(supdict))
	columns = ', '.join(supdict.keys())
	sql = format("INSERT INTO "+"dbo.WinSys_Test_Support_Data"+" ( "+columns+" ) VALUES ( "+placeholders+" )")
	print('\nUpdating ARAS database...\n')
	conn = pyodbc.connect('DSN=server;Database=TestSuite;UID=TestDevTemp;PWD=TempPass1!;Trusted_Connection=No; Connection Timeout=10')
	cursor = conn.cursor()
	cursor.execute(sql,*supdict.values())
	conn.commit()

######## Present prompt if no exceptions are thrown #######################################
###########################################################################################

	print(Back.GREEN + Fore.WHITE + 'SUCCESS - Press ENTER to shutdown.')
	print(Style.RESET_ALL)

except Exception:
	print(Back.RED + Fore.WHITE)
	traceback.print_exc()
	print("FAILURE - Error occured during process. Press ENTER to shutdown. ")
	print(Style.RESET_ALL)

finally:
	try:
		value = input()
		print("Shutting Down...\n")
		subprocess.run(['shutdown','now'],capture_output=True,check=True)
	except KeyboardInterrupt:
		raise

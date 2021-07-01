import inquirer
import glob
import subprocess
from datetime import date
import sys
import os
import pyodbc
import traceback
from colorama import Fore, Back, Style, init

######### July 1st 2021 ##############
######### Al Hussain    ##############

## init for colorama
init()
print(Fore.GREEN)

print("eMMC Programming Tool")
print("--This tool copies a RAW image file to eMMC storage using bmap-tools")
print("--Requires an image file and bmap file created using bmap-tools")
print("--files must be in /home/winsys/ directory\n\n")

print(Style.RESET_ALL)
date = date.today()
print(date)

while True:
	try:
		value = input("Enter Serial Number: ")
		value = value.strip()
		if len(value) == 10:
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
	disk_choice = subprocess.check_output(['grep','-v','sda\|disk:'],stdin=call.stdout).decode('ascii')
	call.wait()
	disk_choice = disk_choice.split('\n')
	for x in range(len(disk_choice)):
		disk_choice[x] = disk_choice[x].replace('Disk','')
		disk_choice[x] = disk_choice[x].strip()
	disk_choice = list(filter(None,disk_choice))

######### Returns list of image files #######################################################
#############################################################################################
	ext = ('.img','.bz2','.gz','.tar.gz','.tgz','.tar.bz2')
	files = []
	for z in ext:
		files.extend(glob.glob('/home/winsys/*'+z))

######### Ask questions for image selection and physical disk ###############################
#############################################################################################
	question = [inquirer.List('imgfile', message = "Select image file: ", choices = files),
		inquirer.List('disk', message = "Select physical disk: ", choices = disk_choice)]
	answer = inquirer.prompt(question)


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

######## Log to ARAS Database ##############################################################
############################################################################################


	supdict = {'ws_serial_num':'','Sup_Description':'','Sup_Value':'','Test_Date':''}
	supdict ['ws_serial_num'] = sn
	supdict['Sup_Description'] = 'Linux Image'
	supdict['Sup_Value'] = answer['imgfile'].split('/')[-1]
	supdict['Test_Date'] = date.strftime('%-m/%-d/%Y')

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

	print(Back.GREEN + Fore.WHITE + 'SUCCESS - Press ENTER to continue.')
	print(Style.RESET_ALL)
	input()

except Exception:
	print(Back.RED + Fore.WHITE)
	traceback.print_exc()
	print("FAILURE - Error occured during process.")
	print(Style.RESET_ALL)

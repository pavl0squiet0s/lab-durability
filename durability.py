############
#--------------------------------------------------------------------------------------------
#code version B, 01/05/2024 (key change: works with "Bookworm RPiOS ver 12, Python 3.11.2)
#								print statement added ()
#								read_from_TiD1 simplified. Added byte response as a variable (TiD_Off and TiD_On)
#								press_button_reed function added which operates on reed switch with additional timer safety cutout
#code version A, 30/06/2022 (key change: rest time automatically calculated from duty cycle. input duty cycle)
#--------------------------------------------------------------------------------------------
#! Issue to fix: condition to turn TiD1 back on after 5min or 300 sec. Code it differenctly?
#  Maybe start timer? And check timer condition? Or work out exact number. Currently two different
#  numbers for the same condition: 296 and 300.


############

#import RPi.GPIO as GPIO#
import serial
import time
import datetime
import sys
import cursor
from gpiozero import Button

#Pin definitions
#up = 04
#down = 17

#Pin Setup
#GPIO.setmode(GPIO.BCM)
#GPIO.setup(up, GPIO.OUT)
#GPIO.setup(down, GPIO.OUT)

#Initial state for Relays:
#GPIO.output(up, GPIO.HIGH)
#GPIO.output(down, GPIO.HIGH)

key1_pressed = bytes(b'\xE8\xE8\xFF\x01\x01\x00\x00\x00\x00\x00\x00') # UP button
key2_pressed = bytes(b'\xE8\xE8\xFF\x02\x02\x00\x00\x00\x00\x00\x00') # DOWN button
#key3_pressed = bytes(b'\xE8\xE8\xFF\x04\x04\x00\x00\x00\x00\x00\x00') # OUT button
#key4_pressed = bytes(b'\xE8\xE8\xFF\x08\x08\x00\x00\x00\x00\x00\x00') # IN button
key6_pressed = bytes(b'\xE8\xE8\xFF\x20\x20\x00\x00\x00\x00\x00\x00') # POWER ON button

TiD1_On = bytes(b'\xa8\xa8\x15\x15\x15\x15\x00\x00\x00\x00\x00\x00')
TiD1_Off = bytes(b'\xa8\xa8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

# 8000 for full lifecycle, use 1088 at a time for full 7 days running. 
# Perform current measurement after each week.
cycles = 85

reed_switch_up = Button(23)
reed_switch_down = Button(25)

#cycle times
move_up = 20
 # moving up time in seconds
move_down = 15.3
# moving down time in seconds

#move_out = 15.5 # moving out time in seconds
#move_in = 15.5 # moving in time in seconds 

move_up_OCP_delay = 3.25

#input duty cycle as a percentage expressed as decimal. So for 10% duty put 0.1, and for 25% put 0.25
duty_cycle = 0.70
rest_times = ((1-duty_cycle)/(duty_cycle))
cycle_rest = int(round((move_up + move_down)*rest_times)) # do a rest after each 'half-cycle'

command_rest = 1 # rest between issuing commands to control box

#change below by removing '#' and setting quicker rest time than default 10% duty cycle
#cycle_rest = 153

#totaltime = (move_up + move_down) * cycles

# total cycle time will be a little bit longer. Below 2.4 seconds were added to the cycle count, derived over 10 cycles and comparing theoretical finish with actual
#totaltime = (2.4 + move_up*2 + move_down*2 + move_out + move_in + command_rest*6 + cycle_rest*2 + move_up_OCP_delay*2) * cycles

totaltime = (move_up*4 + move_down*4 + command_rest*8 + cycle_rest*4) * cycles


def checktime():
	dd = datetime.datetime.now() + datetime.timedelta(seconds=totaltime)
	#print "dd.weekday " + str(dd.weekday())
	#print "dd.hour " + str (dd.hour)
	if dd.weekday() < 4:
		if dd.hour > 15:
			print(dd.weekday() + dd.hour)
			return False
		else:
			return True
	elif dd.weekday() == 4:
		if dd.hour > 13:
			return False
		else:
			return True

def read_from_TiD1(tempserialport):
	readport = tempserialport.read(size=12)
	return readport

def timestamp():
	return (datetime.datetime.now().strftime("%Y-%b-%d %H:%M:%S.%f"))[:-5]

def press_button(serial_port_temp,key_pressed,move_time,rest_time,ii,ff,descr):
	end_time = time.time() + move_time
	ff.write(timestamp()+"  Cycle [" + str(ii) + "] "+str(descr)+" operation started\n")
	while time.time() < end_time:
		writeport = serial_port_temp.write(key_pressed)
		sys.stdout.write(str("\r--- "+str(descr)+" operation. Time left: " + "%.0f" % (end_time-time.time()) + " "))
		sys.stdout.flush()
	sys.stdout.flush()		
	sys.stdout.write("\r" + timestamp() + "  Cycle [" + str(ii) + "] "+str(descr)+" operation complete\n")
	ff.write(timestamp()+"  Cycle [" + str(ii) + "] "+str(descr)+" operation completed\n")
	time.sleep(rest_time)

def press_button_reed(serial_port_temp,key_pressed,reed_switch,move_time,rest_time,ii,ff,descr):
	ff.write(timestamp()+"  Cycle [" + str(ii) + "] "+str(descr)+" operation started\n")
	t1_start = time.perf_counter()
	t2e_finish = t1_start + move_time
	while reed_switch.is_pressed:
		t2a_finish = time.perf_counter()
		if t2a_finish > t2e_finish:
			break
		writeport = serial_port_temp.write(key_pressed)
		sys.stdout.write(str("\r--- "+str(descr)+" operation. "))
		sys.stdout.flush()
	t2_finish = time.perf_counter()
	sys.stdout.flush()		
	sys.stdout.write("\r" + timestamp() + "  Cycle [" + str(ii) + "] "+str(descr)+" operation complete\n")
	ff.write(timestamp()+"  Cycle [" + str(ii) + "] "+str(descr)+" operation completed\n")
	ff.write(timestamp()+"  Time " + str(descr) + " "+str(t2_finish - t1_start)+" [s]\n")
	time.sleep(rest_time)
	return t2_finish - t1_start
		

def zeal_press_button(pin1,pin2,command_cycle_time,ii,ff,descr):
	#1st pin is always button pressed
	#2nd pin is opposite direction
	
	end_time = time.time() + command_cycle_time
	ff.write(timestamp()+"  Cycle [" + str(ii) + "] "+str(descr)+" operation started\n")
	GPIO.output(pin1, GPIO.LOW)
	GPIO.output(pin2, GPIO.HIGH)
	while time.time() < end_time:
		sys.stdout.write(str("\r---Short moving up operation. Time left: " + "%.0f" % (end_time-time.time()) + " "))
		sys.stdout.flush()
	sys.stdout.flush()		
	sys.stdout.write("\r" + timestamp() + "  Cycle [" + str(ii) + "] "+str(descr)+" operation complete\n")
	ff.write(timestamp()+"  Cycle [" + str(ii) + "] "+str(descr)+" operation completed\n")
	time.sleep(0.5)
	GPIO.output(pin1, GPIO.HIGH)
	GPIO.output(pin2, GPIO.HIGH)
	time.sleep(0.5)

cursor.hide()

f = open(datetime.datetime.now().strftime("%Y-%m-%d--%H%M%S") + ".txt","w+")
print("\n" + timestamp() + "  Starting " + str(cycles) + " loaded only day-cycles with " + str(cycle_rest) + " seconds rest between\n")
f.write(timestamp() + "  " + str(cycles) + " cycles started with " + str(cycle_rest) + " seconds rest between\n")
print(timestamp() + "  Test will finish at  " + \
	((datetime.datetime.now()+datetime.timedelta(seconds=totaltime)).strftime("%Y-%b-%d %H:%M:%S.%f"))[:-5])
f.write(timestamp() + "  Test will finish at  " + \
	((datetime.datetime.now()+datetime.timedelta(seconds=totaltime)).strftime("%Y-%b-%d %H:%M:%S.%f"))[:-5]+'\n')
print("Initiating communication with TiD1...")
f.write(timestamp()+"  Initiating communication with TiD1...\n")

i = 0

checktime2 = True

#if checktime():
if checktime2:
	try:
		while (i < cycles):

			i += 1
			
			condition = True
			serialport = serial.Serial(port='/dev/ttyUSB0',baudrate=9600,bytesize=serial.EIGHTBITS,parity=serial.PARITY_NONE,stopbits=serial.STOPBITS_ONE)
			time.sleep(0.5)

			while condition:
				if not serialport.isOpen():
					serialport.open()
					time.sleep(0.5)
				TiD1status = read_from_TiD1(serialport)
				if (TiD1status == TiD1_Off) or (TiD1status == TiD1_On):
					print("Communication with TiD1 established")
					f.write(timestamp()+"  Reading signal from TiD1: "+str(TiD1status)+"\n")
					f.write(timestamp()+"  Communication with TiD1 established\n")
					condition = False
				else:
					print("Repeating communication attempt...")
					f.write(timestamp()+"  Reading signal from TiD1: "+str(TiD1status)+"\n")
					f.write(timestamp()+"  Repeating communication attempt...\n")
					serialport.close()
					time.sleep(0.1)
			
			if (i == 1):
				TiD1status2 = read_from_TiD1(serialport)
				if (TiD1status2 == TiD1_Off):
					print("Turning TiD1 ON...")
					f.write(timestamp()+"  Turning TiD1 ON...\n")
					end_time2 = time.time() + 1
					while time.time() < end_time2:
						writeport = serialport.write(key6_pressed)
					time.sleep(1)
				
			if (i > 1) and (cycle_rest > 296):
				print("Turning TiD1 ON...")
				f.write(timestamp()+"  Turning TiD1 ON...\n")
				end_time2 = time.time() + 1
				while time.time() < end_time2:
					writeport = serialport.write(key6_pressed)
				time.sleep(1)
				

			#press_button(serialport,key1_pressed,move_up,command_rest,i,f,"moving up")
			time_up = press_button_reed(serialport,key1_pressed,reed_switch_up,move_up,command_rest,i,f,"moving up")
			print("Time moving up: "+str(time_up)+" [s]")
			#time.sleep(move_up_OCP_delay)
			#zeal_press_button(up,down,move_up,i,f,"moving up")
				
			#press_button(serialport,key3_pressed,move_out,command_rest,i,f,"moving out")
				
			#press_button(serialport,key2_pressed,move_down,command_rest,i,f,"moving down")
			#zeal_press_button(down,up,move_down,i,f,"moving down")
			
			#time_down = press_button_reed(serialport,key2_pressed,reed_switch_down,move_down,command_rest,i,f,"moving down")
			#print(str(time_down))
			
			press_button(serialport,key2_pressed,move_down,command_rest,i,f,"moving down")

			
			#if (i != cycles):
			f.write(timestamp()+"  1/4-cycle [" + str(i) + "] rest time started\n")
			for j in range(cycle_rest,0,-1):
				sys.stdout.write("\r---Next quarter-cycle starts in: {:2d}".format(j) + " ")
				sys.stdout.flush()
				time.sleep(1)
			sys.stdout.flush()
			sys.stdout.write("\r" + timestamp() + "  1/4-cycle [" + str(i) + "] complete            \n")
			f.write(timestamp()+"  1/4-cycle [" + str(i) + "] rest time ended. Cycle 25% complete\n")

			if (i > 1) and (cycle_rest > 296):
				print("Turning TiD1 ON...")
				f.write(timestamp()+"  Turning TiD1 ON...\n")
				end_time2 = time.time() + 1
				while time.time() < end_time2:
					writeport = serialport.write(key6_pressed)
				time.sleep(1)
				

			#press_button(serialport,key1_pressed,move_up,command_rest,i,f,"moving up")
			time_up = press_button_reed(serialport,key1_pressed,reed_switch_up,move_up,command_rest,i,f,"moving up")
			print("Time moving up: "+str(time_up)+" [s]")
			#time.sleep(move_up_OCP_delay)
			#zeal_press_button(up,down,move_up,i,f,"moving up")
				
			#press_button(serialport,key3_pressed,move_out,command_rest,i,f,"moving out")
				
			#press_button(serialport,key2_pressed,move_down,command_rest,i,f,"moving down")
			#zeal_press_button(down,up,move_down,i,f,"moving down")
			
			#time_down = press_button_reed(serialport,key2_pressed,reed_switch_down,move_down,command_rest,i,f,"moving down")
			#print(str(time_down))
			
			press_button(serialport,key2_pressed,move_down,command_rest,i,f,"moving down")

			
			#if (i != cycles):
			f.write(timestamp()+"  2/4-cycle [" + str(i) + "] rest time started\n")
			for j in range(cycle_rest,0,-1):
				sys.stdout.write("\r---Next quarter-cycle starts in: {:2d}".format(j) + " ")
				sys.stdout.flush()
				time.sleep(1)
			sys.stdout.flush()
			sys.stdout.write("\r" + timestamp() + "  2/4-cycle [" + str(i) + "] complete            \n")
			f.write(timestamp()+"  2/4-cycle [" + str(i) + "] rest time ended. Cycle 50% complete\n")

			
			if (i > 1) and (cycle_rest > 296):
				print("Turning TiD1 ON...")
				f.write(timestamp()+"  Turning TiD1 ON...\n")
				end_time2 = time.time() + 1
				while time.time() < end_time2:
					writeport = serialport.write(key6_pressed)
				time.sleep(1)
				

			#press_button(serialport,key1_pressed,move_up,command_rest,i,f,"moving up")
			time_up = press_button_reed(serialport,key1_pressed,reed_switch_up,move_up,command_rest,i,f,"moving up")
			print("Time moving up: "+str(time_up)+" [s]")
			#time.sleep(move_up_OCP_delay)
			#zeal_press_button(up,down,move_up,i,f,"moving up")
				
			#press_button(serialport,key3_pressed,move_out,command_rest,i,f,"moving out")
				
			#press_button(serialport,key2_pressed,move_down,command_rest,i,f,"moving down")
			#zeal_press_button(down,up,move_down,i,f,"moving down")
			
			#time_down = press_button_reed(serialport,key2_pressed,reed_switch_down,move_down,command_rest,i,f,"moving down")
			#print(str(time_down))
			
			press_button(serialport,key2_pressed,move_down,command_rest,i,f,"moving down")

			
			#if (i != cycles):
			f.write(timestamp()+"  3/4-cycle [" + str(i) + "] rest time started\n")
			for j in range(cycle_rest,0,-1):
				sys.stdout.write("\r---Next quarter-cycle starts in: {:2d}".format(j) + " ")
				sys.stdout.flush()
				time.sleep(1)
			sys.stdout.flush()
			sys.stdout.write("\r" + timestamp() + "  3/4-cycle [" + str(i) + "] complete            \n")
			f.write(timestamp()+"  3/4-cycle [" + str(i) + "] rest time ended. Cycle 75% complete\n")

			
			if (i > 0) and (cycle_rest > 300):
				print("Turning TiD1 ON...")
				f.write(timestamp()+"  Turning TiD1 ON...\n")
				end_time2 = time.time() + 1
				while time.time() < end_time2:
					writeport = serialport.write(key6_pressed)
				time.sleep(1)
				
			#press_button(serialport,key1_pressed,move_up,command_rest,i,f,"moving up")
			time_up = press_button_reed(serialport,key1_pressed,reed_switch_up,move_up,command_rest,i,f,"moving up")
			print("Time moving up: "+str(time_up)+" [s]")
			#time.sleep(move_up_OCP_delay)
			
			#press_button(serialport,key4_pressed,move_in,command_rest,i,f,"moving in")
			
			#press_button(serialport,key2_pressed,move_down,command_rest,i,f,"moving down")
			
			#time_down = press_button_reed(serialport,key2_pressed,reed_switch_down,move_down,command_rest,i,f,"moving down")
			#print(str(time_down))
			
			press_button(serialport,key2_pressed,move_down,command_rest,i,f,"moving down")
				
			# Cycle rest countdown and rest	
			#if (i != cycles):
			f.write(timestamp()+"  Day-Cycle [" + str(i) + "] rest time started\n")
			for j in range(cycle_rest,0,-1):
				sys.stdout.write("\r---Next day-cycle starts in: {:2d}".format(j) + " ")
				sys.stdout.flush()
				time.sleep(1)
			sys.stdout.flush()
			sys.stdout.write("\r" + timestamp() + "  Day-Cycle [" + str(i) + "] complete            \n")
			f.write(timestamp()+"  Day-Cycle [" + str(i) + "] rest time ended. Cycle 100% complete\n")

	except KeyboardInterrupt:
		print("\nTest interupted by user")
		f.write(timestamp()+"  Test interupted by user")
		serialport.close()
		f.close()
		cursor.show()
		#GPIO.cleanup()

else:
	print("Not enough time in a day to complete the test")
	f.write(timestamp()+"  Not enough time in a day to complete the test")
	

if not f.closed:
	print("\nTest completed sucessfully")
	f.write(timestamp()+"  Test completed sucessfully")
	f.close()
	serialport.close()

cursor.show()
#GPIO.cleanup()

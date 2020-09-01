!/usr/bin/env python3
'''
		Function							Function Call Example
-----------------------------------------------------------------------------------------
	-	Search for all components:			all
	- 	Search components by ID: 			ID22
	-	Search components by parameters:	R, 22, SMD, 0805
	-   Change quantity:					ID10+10
	-	Add a new component:   				PI89:90, 100pcs, R, 22, SMD:add
	-   Remove component:					ID10:rm
	-	Help								help

NOTES:
	-	The program is NOT case sensitive
	-	Parameter order in txt file is NOT important
	-	Commas may only be used to seperate parameters. NOT as part of a paramater.
	- 	Every component MUST have the following parameters:
			An ID (In the format of IDX where X is one or more digits). The same ID number cannot be assigned to multiple components!!
			A PI (In the format of PIX:X where X is one or more digits).
			A quantity (In the format of Xpcs where X is one or more digits)
	
	All other parameters and their format is optional!

'''
import time
import board
import neopixel
import re 	# Import Regex

component_file = "components.txt"	# Load the component text file
LED_NUMB = 420	# Nuber of storage untits in the system
COL_NUMB = 35
data_list = []	# List of lines to convert to data
data_transmitt = [[0,0,0]]*LED_NUMB # List of data to send to the LEDs

color_one = [0,100,0]	# Color for component quantity > 1
color_two = [0,0,100]	# Color for component quantity = 1
color_three = [100,0,0]	# Color for component quantity = 0
LED_PIN = board.D18

leds = neopixel.NeoPixel (
		LED_PIN, LED_NUMB, brightness=0.05, auto_write=False, pixel_orde=neopixel.GRB
)

def main():
	print(check_file()) # Check file for errors

	while 1:
		search_str = input()	# Read user input
		search_str_form = format_line(search_str)	# Remove space and turn to lower case

		all_search = re.search(r"\ball\b$", search_str_form)	# List all components
		help_search = re.search(r"\bhelp\b$", search_str_form)	# List all components
		chg_quant_search = re.search(r"\bid\d+[-+]\d+\b$", search_str_form)	# Subtract quantity from component
		rm_comp_search = re.search(r"\bid\d+:rm\b", search_str_form)	# Remove component from storage
		add_comp_search = re.search(r".*,.*,.*\b:add\b$", search_str)	# Add a new component

		if all_search is not None:	
			list_all()	# List all components
		elif chg_quant_search is not None:
			change_qty(search_str_form)	# Change quantity of component
		elif rm_comp_search is not None:
			rm_component(search_str_form)	# Remove existing component
		elif add_comp_search is not None:
			add_comp(search_str)	# Add new component
		elif help_search is not None:
			help()	
		else:
			comp_search(search_str_form)	# Search for component
		
		create_data()
		del data_list[:]	# Clear list from previous search
		for i in range(0,len(data_transmitt)): # Clear data from previous search
			data_transmitt[i] = [0,0,0]

def list_all():
	with open(component_file, "r") as openfile:
		for component in openfile:
			print(component)
			data_list.append(format_line(component))

def change_qty(search_str_form):
	curr_data = []
	new_line = ""

	search_ID = re.findall(r"id\d+", search_str_form)[0]	# Extract the ID
	search_func = re.findall(r"[+|-]", search_str_form)[0]	# Extract the function symbol
	search_qty = re.findall(r"\d+$", search_str_form)[0]	# Extract the quantity

	with open(component_file, "r") as openfile:
		for line in openfile:
			line = format_line(line)
			for parameter in line.split(','):
				if parameter == search_ID:
					curr_line = line
			curr_data.append(line)

	curr_qty = re.findall(r"\b\d+pcs\b", curr_line)[0]	# Extract the quantity
	int_curr_qty = int(curr_qty[:-3])	# Extract digits from quantity

	if search_func == '+':
		int_new_quant = int_curr_qty + int(search_qty)	# Add to existing quantity
	elif search_func == '-':
		if int_curr_qty - int(search_qty) >= 0:
			int_new_quant = int_curr_qty - int(search_qty)	# Subtract from existing quantity
		else:
			print("Negative quantity is not allowed! Try again")
			return

	# Rebuild line with new parameters
	for parameter in curr_line.split(','):
		if parameter == curr_qty:
			parameter = str(int_new_quant) + "pcs"
			new_line = new_line + ', ' + parameter
		else:
			new_line = new_line + ', ' + parameter

	# Remove first comma
	if new_line[0] is ',':
		new_line = new_line[1:]	# Remove first comma

	# Replace the old line with the new line
	new_data = [ls.replace(curr_line, new_line.lstrip()) for ls in curr_data] 

	# Write new data to file
	wr_to_file(new_data)

	# Print changes
	print("Changed:  " + curr_line.rstrip() + "   ---->   " + new_line.rstrip())

def rm_component(search_str_form):
	curr_data = []
	search_ID = re.findall(r"id\d+", search_str_form)[0]	# Extract the ID

	with open(component_file, "r") as openfile:
		for line in openfile:
			curr_data.append(line)
			line = format_line(line)
			for parameter in line.split(','):
				if search_ID == parameter:
					curr_line = line

	if curr_line is None:
		print(search_ID + " Component not found")
		return

	print("Remove Component: " + curr_line.rstrip() + "?   [Y/N]")
	confirm = input()
	#confirm = raw_input()
	if confirm is not 'Y':	# Confirm removal of component
		return

	for parameter in curr_line.split(','):
		if "pi" in format_line(parameter):
			new_line = "None, " + parameter + "," # Create an "empty" component with position index

	# Remove first comma
	if new_line[0] is ',':
		new_line = new_line[1:]

	# Add a new line
	if new_line[-1] is not "\n":
		new_line = new_line + "\n"

	new_data = [param.replace(curr_line, new_line) for param in curr_data] # Replace the old quantity with the new quantity

	# Write new data to file
	wr_to_file(new_data)

	# Print changes
	print("Changed:  " + curr_line.rstrip() + "   ---->   " + new_line.rstrip())
	return

def add_comp(search_str):
	curr_data = []
	ID_check = [None]*LED_NUMB

	# Check if all the necessary parameters exist
	ID_exists = re.findall(r"\bid\d+\b", search_str)
	PI_exists = re.findall(r"\bpi\d+:\d+\b", search_str)
	qty_exists = re.findall(r"\b\d+pcs\b", search_str)

	if ID_exists:	# ID Check (must NOT exist. Generates automaticaly!)
		print("ID number is generated automaticly. Remove it and try again")
		return
	if not PI_exists:	# Position Index Check (Must exist, be >= 0 & in the form of PIX where X == one or more digits)
		print("Could not find PI parameter. Add PI and try again")
		return
	if not qty_exists:	# Quatity Check (Must exist, be >=0 & in the form of Xpcs where X == one or more digits)
		print("Could not find quantity parameter. Add quantity and try again")
		return

	# Check if PI number already exists
	PI_digits = re.findall(r"\d+", line)


	with open(component_file, "r") as openfile:
		for line in openfile:
			if PI_exists in line:
				
	with open(component_file, "r") as openfile:
		for line in openfile:
			curr_data.append(line)	# Read in existing data from file
			ID_numb = re.findall(r"\bID\d+\b", line)	# Find the ID
			if ID_numb:
				ID_numb = ID_numb[0][2:]	# Extract digits from ID
				ID_check[int(ID_numb)] = 1	# Fill index with 1 if ID exists

	empty_ID = (ID_check.index(None))	# Find the first empty index for assigment to ID
	empty_ID = "id"+str(empty_ID) + ", "	# Create the new ID

	new_line = search_str[:-4] + '\n' # Create the new line
	new_line = empty_ID + new_line	# Add ID to the new line
	curr_data.append(new_line)	# Append new line to exising data

	# Write to file
	wr_to_file(curr_data)

	# Print changes
	print("Added:  	" + new_line.rstrip())	# Print changes

def comp_search(search_str_form):
	components = []
	found_comp = []

	with open(component_file, "r") as openfile:
		for line in openfile:
			match_counter = 0
			components.append(line)
			line = format_line(line)
			for parameter in line.split(","):
				for param in search_str_form.split(","):
					if parameter == param:
						match_counter+=1
			found_comp.append(match_counter)

	max_match = max(found_comp)

	# Find the number of components that match the search string
	if max_match == 0:
		print("No components found")
	else:
		max_matches_index = [i for i in range(len(found_comp)) if found_comp[i] == max_match]
		for match in max_matches_index:
			print(components[match])
			data_list.append(components[match])

# Build the data from user search and .txt file
def create_data():
	color = [[0,0,0]]*LED_NUMB

	for line in data_list:
		if line not in ('\n', '\r\n'):
			PI = re.findall(r"\bpi\d+:\d+\b", line)[0]
			PI_digits = re.findall(r"\d+", PI)
			pcs = re.findall(r"\b\d+pcs\b", line)[0]
			pcs = pcs[:-3]
			
			if "None" in line: 		
					color = [0,0,0]
			else:
				if int(pcs) == 0:
					color = color_three
				elif int(pcs) == 1:
					color = color_two
				else:
					color = color_one

			for led in range(int(PI_digits[0]), int(PI_digits[1])+1):
				data_transmitt[led] = color
	rebuild_data(data_transmitt)

# Rebuild data to match the hardware configuration
def rebuild_data(arr):
	new_arr = []
	rev_arr = arr[::-1] # Reverse data

	for t in range(0, len(rev_arr), COL_NUMB):	# For every other row, reverse the data
		if t%2 == +0:
			new_arr.append(rev_arr[t:t+COL_NUMB])  # Append non-reversed row
		else:
			new_arr.append(rev_arr[t:t+COL_NUMB][::-1]) # Append reversed row
	send_data(new_arr)

# Transmitt the data over serial
def send_data(arr):
	flatten = sum(arr, [])
	flatten = sum(flatten, [])
	for i in range(0, LED_NUMB):
		leds[i] = (flatten[i*3], flatten[i*3+1], flatten[i*3+2])
	leds.show()

def wr_to_file(data):
	with open(component_file, "w") as openfile:
		openfile.writelines(data)

def format_line(line):
	return line.replace(' ', '').lower()	# Remove the spaces and turn to lower case 

def check_file():
	count = 0
	with open(component_file, "r") as openfile:
		for line in openfile:
			if line not in '\n':
				if "None" not in line:
					ID_exists = re.findall(r"\bid\d+\b", format_line(line))
					PI_exists = re.findall(r"\bpi\d+:\d+\b", format_line(line))
					QTY_exists = re.findall(r"\b\d+pcs\b", format_line(line))
					count+=1 

					# Check for all necessary parameters and their format
					if len(ID_exists) is not 1:
						return "[ Line " + str(count) + "] " + " ID parameter format incorrect in: " + line
					elif len(PI_exists) is not 1:
						return "[ Line " + str(count) + "] " + " PI parameter format incorrect in: " + line
					elif len(QTY_exists) is not 1:
						return "[ Line " + str(count) + "] " + " Quantity parameter format incorrect in: " + line
					PI_digits = re.findall(r"\d+", line)

					if PI_digits[0] > PI_digits[1]:
						return "[ Line " + str(count) + "] " + " First PI parameter needs to be smaller than the second parameter" + line		
	return "Data good"

def help():
	print('{:<25} {:<25} {:<25} {:<15}'.format("Command", "Syntax", "Example", "Explanation"))
	print("---------------------------------------------------------------------------------------")
	print('{:<25} {:<25} {:<25} {:<15}'.format("Search all", "all", "all", "Lists all components in the system"))
	print('{:<25} {:<25} {:<25} {:<15}'.format("Search ID", "IDXX...", "ID22", "Lists component with the corresponding ID"))
	print('{:<25} {:<25} {:<25} {:<15}'.format("Search Parameters", "Param1, param2...", "R,220,SMD", "Lists component by parameters"))
	print('{:<25} {:<25} {:<25} {:<15}'.format("Add quantity", "IDX+quantity", "ID20+10", "Add quantity to existing component"))
	print('{:<25} {:<25} {:<25} {:<15}'.format("Sub. quantity", "IDX-quantity", "ID10-10", "Subtract quantity from existing component"))
	print('{:<25} {:<25} {:<25} {:<15}'.format("Add component", "Param1, Param2:add", "R,SMD,PI17:add", "Add new component"))
##################################################################################################################
if __name__ == '__main__':
	main()

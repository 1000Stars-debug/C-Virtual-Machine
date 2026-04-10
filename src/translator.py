#!/usr/bin/python3
import struct
import os
import sys

class BytecodeCompiler:
	def __init__(self):
		self.OPCODES = {
			"PUSH": 0x01,
			"DUP": 0x02,
			"READ_GPIO": 0x10,
			"GET_KEY": 0x12,
			"JMP": 0x20,
			"JZ": 0x21,
			"CMP_EQ": 0x30,
			"AND": 0x3A,
    		"OR": 0x3B,
    		"NOT": 0x3C,
    		"CMP_LT": 0x3D,
    		"CMP_GT": 0x3E,
			"ADD": 0x31,
			"SUB": 0x32,
			"MUL": 0x33,
			"DIV": 0x34,
			"MOD": 0x35,
			"DEBUG_PRINT": 0x36,
			"PRINT_STR": 0x37,
			"STORE": 0x38,
			"LOAD": 0x39,
			"PEEK": 0x42,
			"POKE": 0x43,
			"RAND": 0x45,
			"RAND_SEED": 0x46,
			"CALL": 0x22,
			"RET": 0x23,
            "CLS": 0x50,
			"DRAW_PIXEL": 0x51,
			"DRAW_RECT": 0x52,
			"FLIP": 0x53,
			"DELAY": 0x54,
			"FS_SAVE": 0x60,
			"FS_LOAD": 0x61,
			"HALT": 0xFF
		}
		self.reset()

	def reset(self):
		self.instructions = []
		self.raw_data = {}
		self.bytecode = bytearray()
		self.string_data = bytearray()
		self.labels = {}
		
		# Variable Mapping System
		self.variables = {}
		self.next_var_id = 0

	def compile_file(self, input_filepath, output_filepath):
		self.reset()
		if not os.path.exists(input_filepath):
			print(f"[ERROR] Source file '{input_filepath}' not found.")
			return

		with open(input_filepath, 'r') as f:
			lines = f.readlines()

		# --- PASS 1: Calculate Code Size and Store Data ---
		code_ptr = 0
		current_section = ".CODE"
		
		# FIX: RET removed from this list. It is a 1-byte instruction.
		arg_instructions = ["PUSH", "JMP", "JZ", "STORE", "LOAD", "CALL"]
		
		for line in lines:
			clean = line.split("//")[0].strip()
			if not clean: continue
			if clean == ".DATA": current_section = ".DATA"; continue
			if clean == ".CODE": current_section = ".CODE"; continue

			if current_section == ".DATA":
				if ":" in clean:
					label, value = [p.strip() for p in clean.split(":", 1)]
					self.raw_data[label] = value.strip('"')
			elif current_section == ".CODE":
				if clean.endswith(":"):
					label_name = clean[:-1].strip()
					self.labels[label_name] = code_ptr
				else:
					self.instructions.append(clean)
					cmd = clean.split(" ")[0]
					# Add 3 bytes for instructions with 16-bit args, else 1 byte
					code_ptr += 3 if cmd in arg_instructions else 1

		# --- PASS 2: Map Labels and Build Binary ---
		data_ptr = code_ptr 
		
		for label, text in self.raw_data.items():
			self.labels[label] = data_ptr + len(self.string_data)
			self.string_data.extend(text.encode('utf-8'))
			self.string_data.append(0x00)

		for line_idx, line in enumerate(self.instructions):
			parts = line.split(" ", 1)
			cmd = parts[0]
			arg = parts[1].strip() if len(parts) > 1 else None

			if cmd not in self.OPCODES:
				print(f"[ERROR] Unknown instruction '{cmd}' at instruction index {line_idx}")
				sys.exit(1)

			self.bytecode.append(self.OPCODES[cmd])

			if cmd in arg_instructions:
				# Safety check: ensure an argument actually exists
				if arg is None:
					print(f"[ERROR] Instruction '{cmd}' at index {line_idx} expects an argument but found none.")
					sys.exit(1)

				# Handle variable mapping for STORE and LOAD
				if cmd in ["STORE", "LOAD"]:
					if arg not in self.variables:
						self.variables[arg] = self.next_var_id
						self.next_var_id += 1
					val = self.variables[arg]
					
				# Handle string pointers or numerical arguments
				else:
					try:
						val = self.labels[arg] if arg in self.labels else int(arg)
					except ValueError:
						print(f"[ERROR] Invalid argument '{arg}' for '{cmd}' at index {line_idx}. Must be a label or integer.")
						sys.exit(1)
					
				# Pack as Little-Endian 16-bit unsigned integer
				self.bytecode.extend(struct.pack("<H", val))

		# Final File: [CODE][DATA]
		with open(output_filepath, 'wb') as f:
			f.write(self.bytecode + self.string_data)

		print(f"[SUCCESS] Compiled successfully. Size: {len(self.bytecode + self.string_data)} bytes.")
		if self.variables:
			print(f"[INFO] Variable Map: {self.variables}")

if __name__ == "__main__":
	if len(sys.argv) == 3:
		source_file = sys.argv[1]
		exec_name = None
		if sys.argv[2] == None:
		    exec_name = "main.cvm"
		else:
		    exec_name = str(sys.argv[2])
		BytecodeCompiler().compile_file(str(source_file), exec_name)
	else:
		print("[ERROR] Missing arguments. Usage: python compiler.py <source.cvms> <name.cvm>")

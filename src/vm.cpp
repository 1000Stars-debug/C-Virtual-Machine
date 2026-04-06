#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <cstdint>
#include <cstdlib>
#include <algorithm>

namespace Opcode {
	constexpr uint8_t PUSH        = 0x01;
	constexpr uint8_t DUP         = 0x02;
	constexpr uint8_t READ_GPIO   = 0x10;
	constexpr uint8_t MODULATE    = 0x11;
	constexpr uint8_t JMP         = 0x20;
	constexpr uint8_t JZ          = 0x21;
	constexpr uint8_t CALL        = 0x22;
	constexpr uint8_t RET         = 0x23;
	constexpr uint8_t CMP_EQ      = 0x30;
	constexpr uint8_t ADD         = 0x31;
	constexpr uint8_t SUB         = 0x32;
	constexpr uint8_t MUL         = 0x33;
	constexpr uint8_t DIV         = 0x34;
	constexpr uint8_t MOD         = 0x35;
	constexpr uint8_t DEBUG_PRINT = 0x36;
	constexpr uint8_t PRINT_STR   = 0x37;
	constexpr uint8_t STORE       = 0x38;
	constexpr uint8_t PEEK        = 0x42;
	constexpr uint8_t LOAD        = 0x39;
	constexpr uint8_t POKE        = 0x43;
	constexpr uint8_t AND         = 0x3A; 
	constexpr uint8_t OR          = 0x3B; 
	constexpr uint8_t NOT         = 0x3C; 
	constexpr uint8_t CMP_LT      = 0x3D; 
	constexpr uint8_t CMP_GT      = 0x3E; 
	constexpr uint8_t CREATE_BTN  = 0x40;
	constexpr uint8_t SET_TEXT    = 0x41;
	constexpr uint8_t HALT        = 0xFF;
}

class VirtualMachine {
private:
	std::vector<uint8_t> memory;
	int stack[256];
	int variables[256];
	int call_stack[64];
	int ram[2048];
	
	int sp = 0;
	int csp = 0;
	int pc = 0;
	
	bool is_running = false;
	int next_obj_id = 0;

	inline void push(int val) {
		if (sp < 256) {
			stack[sp++] = val;
		} else {
			std::cerr << "[CRITICAL] Stack Overflow at PC: " << (pc - 1) << "\n";
			is_running = false;
		}
	}

	inline int pop() {
		if (sp > 0) {
			return stack[--sp];
		} else {
			std::cerr << "[CRITICAL] Stack Underflow at PC: " << (pc - 1) << "\n";
			is_running = false;
			return 0;
		}
	}

	inline uint16_t fetch_16bit() {
		if (pc + 1 >= memory.size()) return 0;
		uint16_t value = memory[pc] | (memory[pc + 1] << 8);
		pc += 2;
		return value;
	}

public:
	VirtualMachine() { reset(); }

	void reset() {
		sp = 0;
		csp = 0;
		pc = 0;
		is_running = false;
		next_obj_id = 0;
		memory.clear();
		memory.shrink_to_fit();
		
		std::fill(std::begin(stack), std::end(stack), 0);
		std::fill(std::begin(variables), std::end(variables), 0); 
		std::fill(std::begin(call_stack), std::end(call_stack), 0);
		std::fill(std::begin(ram), std::end(ram), 0); 
	}

	bool load_cartridge(const std::string& filename) {
		reset(); 
		std::ifstream file(filename, std::ios::binary | std::ios::ate);
		if (!file.is_open()) return false;

		std::streamsize size = file.tellg();
		file.seekg(0, std::ios::beg);

		memory.resize(size);
		if (file.read(reinterpret_cast<char*>(memory.data()), size)) {
			std::cout << "[SYSTEM] Loaded binary (" << size << " bytes).\n";
			return true;
		}
		return false;
	}

	void run() {
		is_running = true;
		int instructions_executed = 0;
		const int MAX_INSTRUCTIONS = 50000; 

		std::cout << "[SYSTEM] VM Starting Execution...\n";
		std::cout << "-----------------------------------\n";

		while (is_running && pc < memory.size()) {
			if (instructions_executed++ > MAX_INSTRUCTIONS) {
				std::cerr << "[SYSTEM] Safety limit reached. Infinite loop suspected.\n";
				break;
			}

			uint8_t opcode = memory[pc++]; 

			switch (opcode) {
				// --- CORE MEMORY ---
				case Opcode::PUSH:  push(fetch_16bit()); break;
				case Opcode::DUP:   { int val = pop(); push(val); push(val); break; }
				case Opcode::STORE: {
					uint16_t var_id = fetch_16bit();
					if (var_id < 256) variables[var_id] = pop();
					break;
				}
				case Opcode::LOAD: {
					uint16_t var_id = fetch_16bit();
					if (var_id < 256) push(variables[var_id]);
					break;
				}
				case Opcode::PEEK: {
					int addr = pop();
					if (!is_running) break;
					
					if (addr >= 0 && addr < 2048) {
						push(ram[addr]);
					} else {
						std::cerr << "[CRITICAL] PEEK Access Violation at address: " << addr << "\n";
						is_running = false;
					}
					break;
				}
				case Opcode::POKE: {
					int val = pop();
					int addr = pop();
					if (!is_running) break;
					
					if (addr >= 0 && addr < 2048) {
						ram[addr] = val;
					} else {
						std::cerr << "[CRITICAL] POKE Access Violation at address: " << addr << "\n";
						is_running = false;
					}
					break;
				}

				// --- SUBROUTINES ---
				case Opcode::CALL: {
					uint16_t target = fetch_16bit();
					if (csp < 64) {
						call_stack[csp++] = pc; 
						pc = target;
					} else {
						std::cerr << "[CRITICAL] Call Stack Overflow at PC: " << (pc - 1) << "\n";
						is_running = false;
					}
					break;
				}
				case Opcode::RET:
					if (csp == 0) {
						std::cerr << "[ERROR] RET called with empty call stack at PC: " << (pc-1) << "\n";
						is_running = false;
					} else {
						pc = call_stack[--csp];
					}
					break;

				// --- CONTROL FLOW ---
				case Opcode::JMP: pc = fetch_16bit(); break;
				case Opcode::JZ: {
					uint16_t target = fetch_16bit();
					if (pop() == 0) pc = target;
					break;
				}

				// --- MATH & ARITHMETIC ---
				case Opcode::ADD: { int b = pop(); int a = pop(); push(a + b); break; }
				case Opcode::SUB: { int b = pop(); int a = pop(); push(a - b); break; }
				case Opcode::MUL: { int b = pop(); int a = pop(); push(a * b); break; }
				case Opcode::DIV: { 
					int b = pop(); int a = pop(); 
					if(b == 0) { std::cerr << "[ERROR] Div/0 Error\n"; is_running = false; } 
					else { push(a / b); } 
					break; 
				}
				case Opcode::MOD: { 
					int b = pop(); int a = pop(); 
					if(b == 0) { std::cerr << "[ERROR] Mod/0 Error\n"; is_running = false; } 
					else { push(a % b); } 
					break; 
				}

				// --- COMPARISONS & LOGIC ---
				case Opcode::CMP_EQ: { int b = pop(); int a = pop(); push((a == b) ? 1 : 0); break; }
				case Opcode::CMP_LT: { int b = pop(); int a = pop(); push((a < b) ? 1 : 0); break; }
				case Opcode::CMP_GT: { int b = pop(); int a = pop(); push((a > b) ? 1 : 0); break; }
				case Opcode::AND:    { int b = pop(); int a = pop(); push((a && b) ? 1 : 0); break; }
				case Opcode::OR:     { int b = pop(); int a = pop(); push((a || b) ? 1 : 0); break; }
				case Opcode::NOT:    { int a = pop(); push((a == 0) ? 1 : 0); break; }

				// --- I/O & UI ---
				case Opcode::DEBUG_PRINT: {
					int val = pop();
					if (!is_running) break; 
					std::cout << "[DEBUG] Stack Top: " << val << "\n"; 
					break;
				}
				case Opcode::PRINT_STR: {
					int addr = pop();
					if (!is_running) break; 
					
					if (addr < 0 || addr >= memory.size()) {
						std::cerr << "[CRITICAL] Memory Access Violation at PC: " << (pc-1) << "\n";
						is_running = false;
						break;
					}
					std::cout << "[DEBUG] Text Output: " << reinterpret_cast<char*>(&memory[addr]) << "\n";
					break;
				}
				case Opcode::CREATE_BTN: {
					int x = pop(); int y = pop();
					if (!is_running) break; 
					
					int id = next_obj_id++;
					push(id);
					std::cout << "[UI] Created Button ID " << id << " at X:" << x << ", Y:" << y << "\n";
					break;
				}
				case Opcode::SET_TEXT: {
					int str_addr = pop(); int handle_id = pop();
					if (!is_running) break; 
					
					if (str_addr < 0 || str_addr >= memory.size()) {
						std::cerr << "[CRITICAL] Memory Access Violation at PC: " << (pc-1) << "\n";
						is_running = false;
						break;
					}
					std::cout << "[UI] Set Button " << handle_id << " text -> \"" << reinterpret_cast<char*>(&memory[str_addr]) << "\"\n";
					break;
				}
				case Opcode::READ_GPIO: {
					int pin = pop();
					if (!is_running) break; 
					
					push(rand() % 2); 
					std::cout << "[HARDWARE] Read Pin " << pin << "\n";
					break;
				}
				case Opcode::MODULATE: {
					int duty = pop(); int pin = pop();
					if (!is_running) break; 
					
					std::cout << "[HARDWARE] Modulated Pin " << pin << " @ " << duty << "%\n";
					break;
				}

				// --- SYSTEM ---
				case Opcode::HALT:
					std::cout << "-----------------------------------\n";
					std::cout << "[SYSTEM] HALT instruction reached.\n";
					is_running = false; 
					break;
				
				default:
					std::cerr << "[CRITICAL] Unknown Opcode 0x" << std::hex << (int)opcode << " at PC " << (pc-1) << "\n";
					is_running = false;
					break;
			}
		}

		// Fall-through Warning (Triggered if memory ends before HALT)
		if (is_running) {
			std::cout << "-----------------------------------\n";
			std::cerr << "[WARNING] VM execution ended without a HALT instruction.\n";
			is_running = false;
		}
	}
};

int main() {
	VirtualMachine vm;
	if (vm.load_cartridge("main.cvm")) {
		vm.run();
	}
	return 0;
}
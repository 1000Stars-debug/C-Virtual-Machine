#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <cstdint>
#include <cstdlib>
#include <algorithm>
#include <thread>
#include <chrono>

namespace Opcode {
	constexpr uint8_t PUSH        = 0x01;
	constexpr uint8_t DUP         = 0x02;
	constexpr uint8_t READ_GPIO   = 0x10;
	constexpr uint8_t GET_KEY     = 0x12;
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
	constexpr uint8_t LOAD        = 0x39;
	constexpr uint8_t AND         = 0x3A; 
	constexpr uint8_t OR          = 0x3B; 
	constexpr uint8_t NOT         = 0x3C; 
	constexpr uint8_t CMP_LT      = 0x3D; 
	constexpr uint8_t CMP_GT      = 0x3E; 
	constexpr uint8_t PEEK        = 0x42;
	constexpr uint8_t POKE        = 0x43;
	constexpr uint8_t CLS         = 0x50; 
	constexpr uint8_t DRAW_PIXEL  = 0x51; 
	constexpr uint8_t DRAW_RECT   = 0x52;
	constexpr uint8_t FLIP        = 0x53; 
	constexpr uint8_t DELAY       = 0x54;
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
		if (sp < 256) stack[sp++] = val;
		else { std::cerr << "[CRITICAL] Stack Overflow\n"; is_running = false; }
	}

	inline int pop() {
		if (sp > 0) return stack[--sp];
		else { std::cerr << "[CRITICAL] Stack Underflow\n"; is_running = false; return 0; }
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
		sp = 0; csp = 0; pc = 0; is_running = false; next_obj_id = 0;
		memory.clear(); memory.shrink_to_fit();
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
		return file.read(reinterpret_cast<char*>(memory.data()), size) ? true : false;
	}

	void run() {
		is_running = true;
		int instructions_executed = 0;
		const int MAX_INSTRUCTIONS = 500000; 

		std::cout << "[SYSTEM] CVM Started...\n";

		while (is_running && pc < memory.size()) {
			if (instructions_executed++ > MAX_INSTRUCTIONS) {
				std::cerr << "[SYSTEM] Safety limit reached.\n";
				break;
			}

			uint8_t opcode = memory[pc++]; 

			switch (opcode) {
				case Opcode::PUSH:  push(fetch_16bit()); break;
				case Opcode::DUP:   { int val = pop(); push(val); push(val); break; }
				case Opcode::STORE: variables[fetch_16bit() % 256] = pop(); break;
				case Opcode::LOAD:  push(variables[fetch_16bit() % 256]); break;
				
				case Opcode::CALL: {
					uint16_t target = fetch_16bit();
					if (csp < 64) { call_stack[csp++] = pc; pc = target; }
					else is_running = false;
					break;
				}
				case Opcode::RET:   if (csp > 0) pc = call_stack[--csp]; else is_running = false; break;
				case Opcode::JMP:   pc = fetch_16bit(); break;
				case Opcode::JZ:    { uint16_t target = fetch_16bit(); if (pop() == 0) pc = target; break; }

				case Opcode::ADD:   { int b = pop(); int a = pop(); push(a + b); break; }
				case Opcode::SUB:   { int b = pop(); int a = pop(); push(a - b); break; }
				case Opcode::MUL:   { int b = pop(); int a = pop(); push(a * b); break; }
				case Opcode::DIV:   { int b = pop(); int a = pop(); push(b == 0 ? 0 : a / b); break; }
				case Opcode::MOD:   { int b = pop(); int a = pop(); push(b == 0 ? 0 : a % b); break; }

				case Opcode::CMP_EQ:{ int b = pop(); int a = pop(); push((a == b) ? 1 : 0); break; }
				case Opcode::CMP_LT:{ int b = pop(); int a = pop(); push((a < b) ? 1 : 0); break; }
				case Opcode::CMP_GT:{ int b = pop(); int a = pop(); push((a > b) ? 1 : 0); break; }
				case Opcode::AND:   { int b = pop(); int a = pop(); push((a && b) ? 1 : 0); break; }
				case Opcode::OR:    { int b = pop(); int a = pop(); push((a || b) ? 1 : 0); break; }
				case Opcode::NOT:   { int a = pop(); push((a == 0) ? 1 : 0); break; }

				case Opcode::PEEK:  { int addr = pop(); push((addr >= 0 && addr < 2048) ? ram[addr] : 0); break; }
				case Opcode::POKE:  { int val = pop(); int addr = pop(); if(addr >= 0 && addr < 2048) ram[addr] = val; break; }

				case Opcode::DEBUG_PRINT: if (!is_running) break; std::cout << "[DEBUG] " << pop() << "\n"; break;
				case Opcode::PRINT_STR: {
					int addr = pop();
					if (!is_running) break; 
					if (addr >= 0 && addr < memory.size()) std::cout << reinterpret_cast<char*>(&memory[addr]) << "\n";
					break;
				}

				// --- HARDWARE & TIMING (NATIVE) ---
				case Opcode::DELAY: {
					int ms = pop();
					if (is_running) std::this_thread::sleep_for(std::chrono::milliseconds(ms));
					break;
				}
				case Opcode::GET_KEY: push(0); break;
				case Opcode::READ_GPIO: {int pin = pop();push(0);break;}

				// --- GRAPHICS STUBS---
				case Opcode::CLS:        pop(); break; 
				case Opcode::DRAW_PIXEL: pop(); pop(); pop(); break; 
				case Opcode::DRAW_RECT:  pop(); pop(); pop(); pop(); pop(); break; 
				case Opcode::FLIP:       break;

				case Opcode::HALT: is_running = false;std :: cout<<"[SYSTEM] Virtual Machine HALTS\n";  break;
				default: is_running = false;std::cerr << "[ERROR] Invalid Opcode: 0x" << std::hex << (int)opcode << "\n"; break;
			}
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

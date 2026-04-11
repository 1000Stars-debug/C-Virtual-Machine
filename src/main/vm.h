/*
 ██████╗██╗   ██╗███╗   ███╗
██╔════╝██║   ██║████╗ ████║
██║     ██║   ██║██╔████╔██║
██║     ╚██╗ ██╔╝██║╚██╔╝██║
╚██████╗ ╚████╔╝ ██║ ╚═╝ ██║ v1.0
 ╚═════╝  ╚═══╝  ╚═╝     ╚═╝
                            
Description:Bytecode Interpreted virtual machine
Author:created by Sreeranj@2026
Links:https://github.com/1000Stars-debug/C-Virtual-Machine

*/

#include <vector>
#include <string>
#include <cstdint>
#include <cstdlib>
#include <ctime>
#include <SPI.h>
#include <SD.h>
#include "display.h"




namespace Opcode {
	constexpr uint8_t PUSH        = 0x01;
	constexpr uint8_t DUP         = 0x02;
	constexpr uint8_t READ_GPIO   = 0x10;
	constexpr uint8_t WRITE_GPIO  = 0x11;
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
	constexpr uint8_t RAND 	      = 0x45;
	constexpr uint8_t RAND_SEED   = 0x46;
	constexpr uint8_t CLS         = 0x50; 
	constexpr uint8_t DRAW_PIXEL  = 0x51; 
	constexpr uint8_t DRAW_RECT   = 0x52;
	constexpr uint8_t DRAW_TEXT   = 0x55;
	constexpr uint8_t DRAW_NUM   	= 0x56;
	constexpr uint8_t FLIP        = 0x53; 
	constexpr uint8_t DELAY       = 0x54;
	constexpr uint8_t FS_SAVE     = 0x60;
	constexpr uint8_t FS_LOAD     = 0x61;
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
		else { Serial.println("[CRITICAL] Stack Overflow"); is_running = false; }
	}

	inline int pop() {
		if (sp > 0) return stack[--sp];
		else { Serial.println("[CRITICAL] Stack Underflow"); is_running = false; return 0; }
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
    File file = SD.open(filename.c_str());
    if (!file) {
      Serial.printf("[ERROR] Failed to open %s\n", filename.c_str());
      return false;
	  }
    size_t fileSize = file.size();
    if (fileSize == 0) {
      Serial.println("[ERROR] File is empty!");
      file.close();
      return false;
	  }
    memory.resize(fileSize);
    size_t bytesRead = file.read(memory.data(), fileSize);
    file.close();
    if (bytesRead != fileSize) {
      Serial.println("[ERROR] Failed to read entire file!");
      return false;
	  }
    Serial.printf("[SUCCESS] Loaded %d bytes into VM memory.\n", (int)bytesRead);
    return true;
	}

	void run() {
		is_running = true;
		int instructions_executed = 0;
		const int MAX_INSTRUCTIONS = 500000; 

		Serial.println("[SYSTEM] CVM Started...");

		while (is_running && pc < memory.size()) {
			if (instructions_executed++ > MAX_INSTRUCTIONS) {
				Serial.println("[SYSTEM] Safety limit reached.");
				break;
			}

			uint8_t opcode = memory[pc++]; 

			switch (opcode) {
				//---STACK OPERATIONS---
				case Opcode::PUSH:  push(fetch_16bit()); break;
				case Opcode::DUP:   { int val = pop(); push(val); push(val); break; }
				//---STORE & LOAD---
				case Opcode::STORE: variables[fetch_16bit() % 256] = pop(); break;
				case Opcode::LOAD:  push(variables[fetch_16bit() % 256]); break;
				case Opcode::PEEK:  { int addr = pop(); push((addr >= 0 && addr < 2048) ? ram[addr] : 0); break; }
				case Opcode::POKE:  { int val = pop(); int addr = pop(); if(addr >= 0 && addr < 2048) ram[addr] = val; break; }
				//---FUNCTION---
				case Opcode::CALL: {
					uint16_t target = fetch_16bit();
					if (csp < 64) { call_stack[csp++] = pc; pc = target; }
					else is_running = false;
					break;
				}
				case Opcode::RET:   if (csp > 0) pc = call_stack[--csp]; else is_running = false; break;
				//---JUMP STATEMENTS---
				case Opcode::JMP:   pc = fetch_16bit(); break;
				case Opcode::JZ:    { uint16_t target = fetch_16bit(); if (pop() == 0) pc = target; break; }
				//---MATH & LOGICAL OPERATIONS---
				case Opcode::ADD:   { int b = pop(); int a = pop(); push(a + b); break; }
				case Opcode::SUB:   { int b = pop(); int a = pop(); push(a - b); break; }
				case Opcode::MUL:   { int b = pop(); int a = pop(); push(a * b); break; }
				case Opcode::DIV:   { int b = pop(); int a = pop(); push(b == 0 ? 0 : a / b); break; }
				case Opcode::MOD:   { int b = pop(); int a = pop(); push(b == 0 ? 0 : a % b); break; }
				case Opcode::RAND: {int max = pop();if (max <=0) push(0);else push(rand() % max);break;}
				case Opcode::RAND_SEED: {int seed = pop();srand(seed);break;}

				case Opcode::CMP_EQ:{ int b = pop(); int a = pop(); push((a == b) ? 1 : 0); break; }
				case Opcode::CMP_LT:{ int b = pop(); int a = pop(); push((a < b) ? 1 : 0); break; }
				case Opcode::CMP_GT:{ int b = pop(); int a = pop(); push((a > b) ? 1 : 0); break; }
				case Opcode::AND:   { int b = pop(); int a = pop(); push((a && b) ? 1 : 0); break; }
				case Opcode::OR:    { int b = pop(); int a = pop(); push((a || b) ? 1 : 0); break; }
				case Opcode::NOT:   { int a = pop(); push((a == 0) ? 1 : 0); break; }
				//---OUTPUT & DEBUG---
				case Opcode::DEBUG_PRINT: if (!is_running) break; Serial.printf("[DEBUG] %d\n",pop()); break;
				case Opcode::PRINT_STR: {
					int addr = pop();
					if (!is_running) break; 
					if (addr >= 0 && addr < memory.size()) Serial.println(reinterpret_cast<char*>(&memory[addr]));
					break;
				}

				//---FILE SYSTEM (SAVE & LOAD)---
				case Opcode::FS_SAVE: {
          int slot = pop();
					int value = pop();
					
					
					std::string filename = "/save_slot_" + std::to_string(slot) + ".dat";
					
					File file = SD.open(filename.c_str(), FILE_WRITE);
					
					if (file) {
						
						file.write(reinterpret_cast<uint8_t*>(&value), sizeof(int));
						file.close(); 
						Serial.printf("[FILESYSTEM] Saved %s\n", filename.c_str());
					} else {
						Serial.println("[FILESYSTEM ERROR] Could not write to SD card!");
					}
					break;

				}
				case Opcode::FS_LOAD:{
          int slot = pop();
					int value = 0;

					std::string filename = "/save_slot_" + std::to_string(slot) + ".dat";
					File file = SD.open(filename.c_str());
					
					if (file) {
						file.read(reinterpret_cast<uint8_t*>(&value), sizeof(int));
						file.close(); 
						Serial.printf("[FILESYSTEM] Loaded %s\n", filename.c_str());
					} else {
						Serial.println("[FILESYSTEM ERROR] Save file not found.");
					}
					push(value);
					break;
				}

				// --- HARDWARE & TIMING (NATIVE) ---
				case Opcode::DELAY: {
					int ms = pop();
					delay(ms);
					break;
				}
				case Opcode::READ_GPIO: {int pin = pop();int val = analogRead(pin);push(val);break;}
				case Opcode::WRITE_GPIO: {int value = pop();int pin = pop();analogWrite(pin,value);break;}

				// --- GRAPHICS & FRAMEBUFFER---
				case Opcode::CLS: {
          int color = pop();
          sprite.fillScreen(color);
          break; 
        }
        case Opcode::DRAW_PIXEL: {
          int color = pop(); int y = pop(); int x = pop();
          sprite.drawPixel(x, y, color);
          break; 
        }
        case Opcode::DRAW_RECT: {
          int color = pop(); int h = pop(); int w = pop(); int y = pop(); int x = pop();
          sprite.fillRect(x, y, w, h, color);
          break; 
        }
        case Opcode::DRAW_TEXT: {
          int color = pop(); 
          int y = pop(); 
          int x = pop();
          int addr = pop();
          
          if (!is_running) break;

          String text = "";
          while (addr >= 0 && addr < memory.size() && memory[addr] != 0x00) {
            text += (char)memory[addr];
            addr++;
          }

          sprite.setTextColor(color);
          sprite.setCursor(x, y);
          sprite.print(text);
          break;
        }
				case Opcode::DRAW_NUM: {
					int color = pop();
					int y     = pop();
					int x     = pop();
					int value = pop();

					if (!is_running) break;

					sprite.setTextColor(color);
					sprite.setCursor(x, y);
					sprite.print(value);
					break;
				}
        case Opcode::FLIP: {
					instructions_executed = 0;
					lcd.startWrite();
          sprite.pushSprite(0, 0);
					lcd.endWrite();
          break;
        }
				//---HALT---
				case Opcode::HALT: is_running = false;Serial.println("[SYSTEM] Virtual Machine HALTS");  break;
				default: is_running = false;Serial.printf("[ERROR] Invalid Opcode: 0x%02X\n", opcode); break;
			}
		}
	}
};
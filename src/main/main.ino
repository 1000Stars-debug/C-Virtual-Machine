#include "vm.h"

#define SD_CS 5


void init_sd_card() {
  SPI.begin(10, 4, 11, SD_CS);
  delay(50); 
  if (!SD.begin(SD_CS, SPI, 4000000)) {
    Serial.println("[ERROR] SD Card Mount Failed!");
    while (true) {
      delay(100); 
    }
  }
  
  Serial.println("[SYSTEM] SD Card Initialized.");
}

void list_files() {
  File root = SD.open("/");
  if (!root) {
    Serial.println("[SYSTEM] Failed to open root directory.");
    return;
  }
  
  bool isEmpty = true;
  while (true) {
    File list = root.openNextFile();
    
    if (!list) {
      if (isEmpty) {
        Serial.println("[SYSTEM] Empty Directory.");
      }
      break; 
    }
    
    isEmpty = false;
    
    if (!list.isDirectory()) {
      Serial.println(list.name()); 
    }
    list.close(); 
  }
}

String select_files() {

  while (Serial.available() == 0) {
    delay(10); 
  }
  
  String user_input = Serial.readStringUntil('\n');
  user_input.trim();
  return user_input;
}

VirtualMachine vm;

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("[BOOTING] Operating System");
  Serial.println("[BOOTING] Initializing SD Card");
  
  init_sd_card();
  list_files();
  srand(esp_random());
  
  
  while (true) {
    Serial.println("\n[SYSTEM] Type /<filename> to load:");
    
    String fileToLoad = select_files();
    
    if (fileToLoad == "exit") {
      Serial.println("[OS EXIT] Halting.");
      break; 
    }
		if (fileToLoad == "ls"){
			list_files();
			continue;
		}
    
    if (fileToLoad.length() > 0) {
      if (vm.load_cartridge(fileToLoad.c_str())) {
        vm.run();
      } else {
        Serial.print("[SYSTEM] Can't load: ");
        Serial.println(fileToLoad);
      }
    }
  }
}



void loop() {
  // put your main code here, to run repeatedly:

}

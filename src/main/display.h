#include <LovyanGFX.hpp>

// ==========================================
// CUSTOM DISPLAY DRIVER (ST7735S)
// ==========================================
class LGFX_Custom : public lgfx::LGFX_Device {
  lgfx::Panel_ST7735S _panel_instance; 
  lgfx::Bus_SPI       _bus_instance;
  lgfx::Light_PWM     _light_instance;

public:
  LGFX_Custom(void) {
    // --- SPI BUS CONFIG ---
    auto cfg = _bus_instance.config();
    cfg.spi_host = SPI2_HOST; 
    cfg.spi_mode = 0;
    cfg.freq_write = 27000000; 
    cfg.pin_sclk = 10;         
    cfg.pin_mosi = 11;         
    cfg.pin_miso = -1;         
    cfg.pin_dc   = 12;         
    _bus_instance.config(cfg);
    _panel_instance.setBus(&_bus_instance);

    // --- PANEL CONFIG ---
    auto panel_cfg = _panel_instance.config();
    panel_cfg.pin_cs   = 9;    
    panel_cfg.pin_rst  = 13;   
    panel_cfg.pin_busy = -1;
    panel_cfg.panel_width  = 128; 
    panel_cfg.panel_height = 160; 
    panel_cfg.offset_x = 2;
    panel_cfg.offset_y = 1;
    panel_cfg.rgb_order = true; 
    panel_cfg.invert = false;  
    panel_cfg.bus_shared = true; 
    _panel_instance.config(panel_cfg);

    // --- BACKLIGHT CONFIG ---
    auto light_cfg = _light_instance.config();
    light_cfg.pin_bl = 8;      
    light_cfg.pwm_channel = 0;
    _light_instance.config(light_cfg);
    _panel_instance.setLight(&_light_instance);

    setPanel(&_panel_instance);
  }
};

// ==========================================
// GLOBAL DISPLAY OBJECT DECLARATIONS
// ==========================================

extern LGFX_Custom lcd;
extern LGFX_Sprite sprite;

inline void init_display() {
  lcd.init();
  lcd.setBrightness(128);
  lcd.fillScreen(TFT_BLACK);
  
  sprite.setColorDepth(16);
  sprite.createSprite(128, 160); 
  sprite.setTextSize(1);
}
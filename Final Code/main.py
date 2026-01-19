#main.py
from machine import I2S, Pin, I2C
from ssd1306 import SSD1306_I2C
import math
import time
import array

# --- I2S CONFIGURATION (Microphone) ---
SCK_PIN = 16
WS_PIN = 17
SD_PIN = 18
SAMPLE_RATE = 16000
BITS_PER_SAMPLE = 32
BUFFER_LENGTH = 64
DB_OFFSET = -46.72

audio_in = I2S(
    0, sck=Pin(SCK_PIN), ws=Pin(WS_PIN), sd=Pin(SD_PIN),
    mode=I2S.RX, bits=BITS_PER_SAMPLE, format=I2S.MONO,
    rate=SAMPLE_RATE, ibuf=2048
)
read_buffer = bytearray(BUFFER_LENGTH * 4)

# --- OLED CONFIGURATION (Display) ---
OLED_WIDTH = 128
OLED_HEIGHT = 64
i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)
SMOOTHING_FACTOR = 0.15  
smoothed_db = 0.0
is_first_reading = True

# Peak hold for visual effect
peak_db = 0.0
peak_hold_time = 0
PEAK_HOLD_DURATION = 20

print("Starting Professional Decibel Meter...")

def draw_meter_bar(oled, db_value):
    """Draw a professional-looking meter bar with segments"""
    # Map dB range (30-90 dB) to bar width (0-100 pixels)
    db_min = 30.0
    db_max = 90.0
    
    # Clamp value
    db_clamped = max(db_min, min(db_max, db_value))
    
    # Calculate bar width (100 pixels max)
    bar_width = int((db_clamped - db_min) / (db_max - db_min) * 100)
    
    # Draw border for meter
    oled.rect(0, 28, 102, 14, 1)
    
    # Draw segmented bar (10 segments)
    for seg in range(10):
        seg_start = seg * 10 + 1
        seg_end = seg_start + 8
        
        if bar_width > seg_start:
            # Fill this segment
            fill_width = min(8, bar_width - seg_start)
            oled.fill_rect(seg_start + 1, 30, fill_width, 10, 1)
    
    # Draw level indicators
    for i in range(0, 101, 20):
        oled.vline(i + 1, 42, 3, 1)
    
    # Draw labels
    oled.text("30", 0, 46, 1)
    oled.text("60", 44, 46, 1)
    oled.text("90", 88, 46, 1)

def draw_peak_indicator(oled, peak_value):
    """Draw a small peak hold indicator"""
    db_min = 30.0
    db_max = 90.0
    peak_clamped = max(db_min, min(db_max, peak_value))
    peak_pos = int((peak_clamped - db_min) / (db_max - db_min) * 100)
    
    if peak_pos > 0 and peak_pos <= 100:
        # Draw peak marker
        oled.vline(peak_pos + 1, 29, 12, 1)

while True:
    num_bytes_read = audio_in.readinto(read_buffer)
    samples_read = num_bytes_read // 4
    
    if samples_read > 0:
        mic_samples = array.array('i', read_buffer)
        sum_squares = 0.0
        
        for i in range(samples_read):
            processed_sample = mic_samples[i] >> 8
            sum_squares += processed_sample * processed_sample
            
        rms = math.sqrt(sum_squares / samples_read)
        if rms <= 0:
            rms = 1
            
        db = 20.0 * math.log10(rms)
        final_db = db + DB_OFFSET
        
        if is_first_reading:
            smoothed_db = final_db
            is_first_reading = False
        else:
            smoothed_db = (SMOOTHING_FACTOR * final_db) + ((1 - SMOOTHING_FACTOR) * smoothed_db)
        
        # Peak detection with hold
        if smoothed_db > peak_db:
            peak_db = smoothed_db
            peak_hold_time = PEAK_HOLD_DURATION
        else:
            peak_hold_time -= 1
            if peak_hold_time <= 0:
                # Slowly decay peak
                peak_db = peak_db * 0.95
        
        # Print to Serial Monitor
        print(f"Raw: {final_db:.2f} | Smoothed: {smoothed_db:.2f} | Peak: {peak_db:.2f}")
        
    
        oled.fill(0)  
        
        # Title with box
        oled.rect(0, 0, 128, 12, 1)
        oled.text("dB METER", 35, 2, 1)
        
        # Large dB value display
        db_str = f"{smoothed_db:.1f}"
        oled.text(db_str, 30, 15, 1)
        oled.text("dB", 75, 15, 1)
        
        # Draw meter bar with segments
        draw_meter_bar(oled, smoothed_db)
        
        # Draw peak hold indicator
        draw_peak_indicator(oled, peak_db)
        
        # Status indicator (small dot that blinks)
        if int(time.ticks_ms() / 500) % 2:
            oled.fill_rect(122, 2, 4, 4, 1)
        
        oled.show()  # Update display
    
    time.sleep(0.05)
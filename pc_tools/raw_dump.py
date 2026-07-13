# raw_dump.py — standalone diagnostic, bypasses all parsing logic
import time
import serial

PORT = "COM12"
BAUD = 460800
NUM_BYTES = 3000   # a few full frames worth (~1284 bytes each)

ser = serial.Serial(PORT, BAUD)

print("Waiting for ESP32 to finish booting...")
time.sleep(2.5)
ser.reset_input_buffer()

print("Capturing now — TALK LOUDLY CONTINUOUSLY for the next few seconds...\n")

data = ser.read(NUM_BYTES)

print(f"Received {len(data)} bytes.\n")

for i in range(0, len(data), 16):
    chunk = data[i:i+16]
    hex_str = " ".join(f"{b:02X}" for b in chunk)
    print(f"{i:04d}: {hex_str}")

ser.close()

import os
import time
import shutil

FIRMWARE_DIR = "firmware_latest"
# The right side firmware file
TARGET_FIRMWARE = "corne_right.uf2" 
MOUNT_POINT = "/Volumes/NICENANO"

def flash_right():
    print(f"--- Flashing RIGHT side using {FIRMWARE_DIR} ---")
    print(f"Target: {TARGET_FIRMWARE}")
    print("1. Ensure your RIGHT half is connected.")
    print("2. Double-tap Reset.")
    print("  Waiting for 'NICENANO' drive...")
    
    while not os.path.exists(MOUNT_POINT):
        time.sleep(1)
        
    print("  Drive detected! Flashing...")
    time.sleep(2) # Stabilize
    
    source = os.path.join(FIRMWARE_DIR, TARGET_FIRMWARE)
    destination = os.path.join(MOUNT_POINT, TARGET_FIRMWARE)
    
    try:
        shutil.copy2(source, destination)
        print(f"  Successfully copied {TARGET_FIRMWARE} to keyboard.")
    except Exception as e:
        print(f"  Error: {e}")
        return

    print("  Waiting for reboot...")
    while os.path.exists(MOUNT_POINT):
        time.sleep(1)
    print("  Done! Right side updated.")

if __name__ == "__main__":
    flash_right()

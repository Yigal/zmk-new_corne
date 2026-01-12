import re
import os
from PIL import Image, ImageDraw, ImageFont

# Basic Corne Layout Configuration
KEY_W = 60
KEY_H = 60
GAP = 5
MARGIN = 10

def get_key_coords(index):
    # Index 0-41 (42 keys total) based on ZMK Corne definition:
    # 0-11: Top Row (L0-L5, R0-R5)
    # 12-23: Mid Row (L0-L5, R0-R5)
    # 24-35: Bot Row (L0-L5, R0-R5)
    # 36-41: Thumbs (L0-L2, R0-R2)
    
    row = 0
    col = 0
    
    if index < 12: # Top Row
        r = 0
        c = index
    elif index < 24: # Mid Row
        r = 1
        c = index - 12
    elif index < 36: # Bot Row
        r = 2
        c = index - 24
    else: # Thumbs
        r = 3
        c = index - 36 # 0-5
        
    row_offsets = [0, 15, 20] # Simple stagger y-offsets for rows 0-2 (optional aesthetic)
    if r == 3: row_offsets.append(0) # Thumb row offset handled manually

    final_x = 0
    final_y = 0
    
    # Left Half Width approx: 6 keys
    left_block_w = 6 * (KEY_W + GAP) + 40 # extra space for split
    
    if r < 3:
        if c < 6: # Left Side
            final_x = MARGIN + c * (KEY_W + GAP)
            final_y = MARGIN + r * (KEY_H + GAP) + row_offsets[r]
        else: # Right Side
            c_right = c - 6
            final_x = MARGIN + left_block_w + c_right * (KEY_W + GAP)
            final_y = MARGIN + r * (KEY_H + GAP) + row_offsets[r]
    else: # Thumbs
        # Thumbs are usually offset
        thumb_y = MARGIN + 3 * (KEY_H + GAP) + 10
        if c < 3: # Left (3 indices)
            # Positioned under columns 3,4,5 roughly
            thumb_start_x = MARGIN + 3.5 * (KEY_W + GAP)
            final_x = thumb_start_x + c * (KEY_W + GAP)
            final_y = thumb_y
        else: # Right (3 indices)
            # Positioned under columns 0,1,2 of right side roughly
            # Mirroring left: Left thumbs are inner->outer? No ZMK is usually outer->inner?
            # Actually standard corne: Left Inner is index 38?
            # Let's assume standard visual order: 
            # Left Thumbs: 36, 37, 38 (Left to Right)
            # Right Thumbs: 39, 40, 41 (Left to Right)
            
            c_right = c - 3
            # Right side start
            thumb_start_x_right = MARGIN + left_block_w - 0.5 * (KEY_W + GAP)
            final_x = thumb_start_x_right + c_right * (KEY_W + GAP)
            final_y = thumb_y
            
    return final_x, final_y

def clean_label(keycode):
    k = keycode.strip()
    
    # Define replacements for common parts
    replacements = [
        ("&kp ", ""), 
        ("&trans", ""), 
        ("&none", ""), 
        ("LSHIFT", "Shift"), ("RSHIFT", "Shift"), 
        ("LCTRL", "Ctrl"), ("RCTRL", "Ctrl"),
        ("LALT", "Alt"), ("RALT", "Alt"), 
        ("LGUI", "Gui"), ("RGUI", "Gui"),
        ("BSPC", "Bksp"), ("SPACE", "Spc"), ("RET", "Ent"), ("ESC", "Esc"),
        ("TAB", "Tab"), ("SQT", "'"), ("SEMI", ";"), ("COMMA", ","), ("DOT", "."),
        ("FSLH", "/"), ("BSLH", "\\"), ("LBKT", "["), ("RBKT", "]"),
        ("MINUS", "-"), ("EQUAL", "="), ("GRAVE", "`"), ("TILDE", "~"),
        ("PG_UP", "PgUp"), ("PG_DN", "PgDn"), ("PSCRN", "PrtSc"),
        ("C_VOL_UP", "Vol+"), ("C_VOL_DN", "Vol-"), ("C_MUTE", "Mute"),
        ("C_PP", "Play"), ("C_NEXT", "Next"), ("C_PREV", "Prev"),
        ("&mkp LCLK", "Click L"), ("&mkp RCLK", "Click R"), ("&mkp MCLK", "Click M"),
        ("&msc SCRL_UP", "Scrl ^"), ("&msc SCRL_DOWN", "Scrl v"),
        ("&mmv MOVE_UP", "Ms ^"), ("&mmv MOVE_DOWN", "Ms v"), 
        ("&mmv MOVE_LEFT", "Ms <"), ("&mmv MOVE_RIGHT", "Ms >"),
        ("LC(", "C-"), ("LS(", "S-"), ("LA(", "A-"), ("LG(", "G-"), (")", "")
    ]
    
    # Logic for Layer Taps and Mod Taps
    if k.startswith("&lt "):
        # &lt 1 SPACE
        parts = k.split()
        if len(parts) >= 3:
            layer = parts[1]
            key = parts[2].replace("&kp", "").strip()
            # Recursively clean the key part if complex? simpler to just Map
            for old, new in replacements: key = key.replace(old, new)
            return f"L{layer}\n{key}"
            
    if k.startswith("&mo "):
        return f"L{k.split()[1]}"
        
    if k.startswith("&to "):
        return f"TO {k.split()[1]}"
        
    for old, new in replacements:
        k = k.replace(old, new)
        
    return k.strip()

def draw_layers(keymap_file, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    with open(keymap_file, 'r') as f:
        content = f.read()
        
    # Extract Layers
    pattern = re.compile(r'(layer_[0-9a-zA-Z_]+)\s*\{\s*bindings\s*=\s*<(.*?)>;', re.DOTALL)
    matches = pattern.findall(content)
    
    generated_files = []
    
    for layer_name, bindings_raw in matches:
        # 1. Remove comments
        bindings_clean = re.sub(r'/\*.*?\*/', '', bindings_raw, flags=re.DOTALL)
        
        # 2. Split by '&' to separate bindings (since all ZMK bindings start with &)
        # This approach avoids splitting parameters like "&kp SPACE" into two keys.
        # " &kp A &mo 1 " -> [" ", "kp A ", "mo 1 "]
        raw_tokens = bindings_clean.split('&')
        keys = []
        for t in raw_tokens:
            if not t.strip(): continue
            # Add the '&' back
            keys.append('&' + t.strip())
            
        # 3. Draw
        if len(keys) == 0: continue
        
        img_w = 900
        img_h = 350
        img = Image.new('RGB', (img_w, img_h), color=(30, 30, 30))
        d = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("Arial.ttf", 16)
        except:
            # Try specific paths for Mac/Linux if Arial not found default
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
            except:
                font = ImageFont.load_default()
            
        for i, key in enumerate(keys):
            if i >= 42: break 
            
            x, y = get_key_coords(i)
            label = clean_label(key)
            
            # Key Style
            key_color = (250, 250, 250)
            text_color = (20, 20, 20)
            
            # Highlight modifiers/layers
            if "L" in label and len(label) < 4 and label[1:].isdigit(): # L1, L2...
                 key_color = (200, 200, 255)
            elif "TO" in label:
                 key_color = (255, 200, 200)
            elif label == "" or label == "trans": # &trans
                 key_color = (60, 60, 60)
                 text_color = (100, 100, 100)
                 label = "▽"
            elif label == "X" or label == "&none": # &none
                 key_color = (40, 40, 40)
                 text_color = (80, 80, 80)
                 label = ""
                 
            # shape
            rect = [x, y, x + KEY_W, y + KEY_H]
            d.rectangle(rect, fill=key_color, outline=(100, 100, 100))
            
            # text
            bbox = d.textbbox((0,0), label, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            d.text((x + (KEY_W - text_w)/2, y + (KEY_H - text_h)/2), label, fill=text_color, font=font)
            
        # Draw Layer Title
        d.text((10, 10), layer_name.upper().replace('_', ' '), fill=(255, 255, 255), font=font)
        
        filename = f"{layer_name}.png"
        path = os.path.join(output_folder, filename)
        img.save(path)
        generated_files.append(filename)
        
    return generated_files

if __name__ == "__main__":
    draw_layers("config/corne.keymap", "static/images")

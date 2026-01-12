import re
import os
from PIL import Image, ImageDraw, ImageFont

# Basic Corne Layout Configuration
KEY_W = 60
KEY_H = 60
GAP = 5
MARGIN = 10

# Offsets for staggered split layout (Simulated Corne)
# Left Side
# Rows 0-2: 6 columns
# Thumbs: 3 keys
# Right Side: Mirrored

def get_key_coords(index):
    # Index 0-41 (42 keys total)
    # Left Side: 0-20 (21 keys)
    # Right Side: 21-41 (21 keys)
    
    row = 0
    col = 0
    is_right = False
    
    if index >= 21:
        is_right = True
        idx = index - 21
    else:
        idx = index

    # Specific Corne Mapping (Standard 6-col)
    # Top Row: 0-5
    # Mid Row: 6-11
    # Bot Row: 12-17
    # Thumbs: 18-20
    
    x = 0
    y = 0
    
    # Stagger offsets (approximate for visual)
    row_offsets = [0, 15, 20] # Simple stagger
    
    if idx < 6: # Row 0
        row = 0
        col = idx
        x = MARGIN + col * (KEY_W + GAP)
        y = MARGIN + row * (KEY_H + GAP) + row_offsets[0]
    elif idx < 12: # Row 1
        row = 1
        col = idx - 6
        x = MARGIN + col * (KEY_W + GAP)
        y = MARGIN + row * (KEY_H + GAP) + row_offsets[1]
    elif idx < 18: # Row 2
        row = 2
        col = idx - 12
        x = MARGIN + col * (KEY_W + GAP)
        y = MARGIN + row * (KEY_H + GAP) + row_offsets[2]
    else: # Thumbs
        row = 3
        col = idx - 18
        # Thumbs are usually shifted right on left side
        thumb_offset_x = 3.5 * (KEY_W + GAP) 
        x = MARGIN + thumb_offset_x + col * (KEY_W + GAP)
        y = MARGIN + 3 * (KEY_H + GAP) + 10

    if is_right:
        # Mirror / Shift to right side
        # Total width of left side approx 6 keys
        left_width = 7 * (KEY_W + GAP)
        gap_between_halves = 50
        
        # Mirror column visual? No, usually indices go Left->Right, but physically right side keys go Right->Left in some matrixes. 
        # But ZMK keymap usually lists Left Top Row -> Right Top Row.
        # So Index 6 (Left) is "Y" (Right Top Left).
        # Actually in Corne ZMK default:
        # L0-L5, R0-R5
        # L6-L11, R6-R11
        # ...
        
        # Wait, typical parsing is sequential.
        # Corne 42 keymap usually is:
        # Tab Q W E R T   Y U I O P Bksp
        # So indices 0-5 are Left, 6-11 are Right.
        
        # Let's adjust logic for STANDARD KEYMAP ORDER
        # Row 1: 0-11 (0-5 Left, 6-11 Right)
        # Row 2: 12-23 (12-17 Left, 18-23 Right)
        # Row 3: 24-35 (24-29 Left, 30-35 Right)
        # Thumbs: 36-41 (36-38 Left, 39-41 Right)
        
        # New Logic based on continuous index 0-41
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
            
        # Determine Left/Right based on Column
        # Rows 0-2: Cols 0-5 Left, 6-11 Right
        # Thumbs: 0-2 Left, 3-5 Right
        
        final_x = 0
        final_y = 0
        
        if r < 3:
            if c < 6: # Left Side
                final_x = MARGIN + c * (KEY_W + GAP)
                final_y = MARGIN + r * (KEY_H + GAP) + row_offsets[r]
            else: # Right Side
                c_right = c - 6
                left_w = 6 * (KEY_W + GAP) + 40
                final_x = MARGIN + left_w + c_right * (KEY_W + GAP)
                final_y = MARGIN + r * (KEY_H + GAP) + row_offsets[r]
        else: # Thumbs
            if c < 3: # Left
                thumb_start = 3.5 * (KEY_W + GAP)
                final_x = MARGIN + thumb_start + c * (KEY_W + GAP)
                final_y = MARGIN + 3 * (KEY_H + GAP) + 10
            else: # Right
                c_right = c - 3
                left_w = 6 * (KEY_W + GAP) + 40
                # Right thumbs usually mirror left thumbs: start closer to center
                # Left thumbs: 3.5, 4.5, 5.5 (indices relative to key width)
                # Right thumbs: 0.5, 1.5, 2.5 relative to right start?
                # Actually ZMK Order: Left Inner -> Outer? No, usually L -> R.
                # Left Thumbs: Outer, Mid, Inner (Left to Right).
                # Right Thumbs: Inner, Mid, Outer (Left to Right).
                
                # Visual placement:
                # Left: near column 3,4,5.
                # Right: near column 0,1,2 of right side (which is col 6,7,8 absolute)
                thumb_start_right = -0.5 * (KEY_W + GAP) # Shift left slightly
                final_x = MARGIN + left_w + thumb_start_right + c_right * (KEY_W + GAP)
                final_y = MARGIN + 3 * (KEY_H + GAP) + 10
                
        return final_x, final_y

    return 0,0

def clean_label(keycode):
    # Remove &kp, &mo, etc
    k = keycode.strip()
    # Handle comments
    if "/*" in k:
        k = k.split("/*")[0].strip()
        
    replacements = [
        ("&kp ", ""), ("&mo ", "L"), ("&lt ", "LT"), ("&to ", "TO"),
        ("&mt ", "MT"), ("&mkp ", "Mouse "), ("&msc ", "Scroll "), ("&mmv ", "Move "),
        ("LSHIFT", "Shift"), ("RSHIFT", "Shift"), ("LCTRL", "Ctrl"), ("RCTRL", "Ctrl"),
        ("LALT", "Alt"), ("RALT", "Alt"), ("LGUI", "Gui"), ("RGUI", "Gui"),
        ("BSPC", "Bksp"), ("SPACE", "Spc"), ("RET", "Ent"), ("ESC", "Esc"),
        ("TAB", "Tab"), ("SQT", "'"), ("SEMI", ";"), ("COMMA", ","), ("DOT", "."),
        ("FSLH", "/"), ("BSLH", "\\"), ("LBKT", "["), ("RBKT", "]"),
        ("MINUS", "-"), ("EQUAL", "="), ("GRAVE", "`"), ("TILDE", "~"),
        ("PG_UP", "PgUp"), ("PG_DN", "PgDn"), ("PSCRN", "PrtSc"),
        ("C_VOL_UP", "Vol+"), ("C_VOL_DN", "Vol-"), ("C_MUTE", "Mute"),
        ("C_PP", "Play"), ("C_NEXT", "Next"), ("C_PREV", "Prev"),
        ("&trans", ""), ("&none", "X"), ("&bt BT_SEL", "BT"), ("&bt BT_CLR", "BT CLR")
    ]
    
    for old, new in replacements:
        k = k.replace(old, new)
        
    return k

def draw_layers(keymap_file, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    with open(keymap_file, 'r') as f:
        content = f.read()
        
    # Extract Layers
    # Regex look for layer_N { bindings = < ... >; };
    pattern = re.compile(r'(layer_[0-9a-zA-Z_]+)\s*\{\s*bindings\s*=\s*<(.*?)>;', re.DOTALL)
    matches = pattern.findall(content)
    
    generated_files = []
    
    for layer_name, bindings in matches:
        # Split bindings into keys
        # Clean up newlines and extra spaces
        bindings = bindings.replace('\n', ' ').strip()
        # Regex to split by space but keep params together? 
        # ZMK keys usually space separated: &kp A &mo 1
        # Simple split might work if not using complex macros
        keys = [x for x in bindings.split(' ') if x.strip()]
        
        # Remove comments logic inside split?
        # Better: use regex to find tokens like &[\w\(\)\_]+
        # But comments like /* ... */ break this.
        # Let's clean block comments first
        bindings_clean = re.sub(r'/\*.*?\*/', '', bindings, flags=re.DOTALL)
        keys = [x for x in bindings_clean.split(' ') if x.strip()]
        
        # If 42 keys
        if len(keys) < 42:
            # Pad or warn?
            pass
            
        # Draw Layout
        img_w = 900
        img_h = 350
        img = Image.new('RGB', (img_w, img_h), color=(30, 30, 30))
        d = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("Arial.ttf", 16)
        except:
            font = ImageFont.load_default()
            
        for i, key in enumerate(keys):
            if i >= 42: break # Corne limit
            
            x, y = get_key_coords(i)
            label = clean_label(key)
            
            # Key color
            key_color = (240, 240, 240)
            text_color = (0, 0, 0)
            
            if "Layer" in layer_name.title():
                 # Maybe tint based on layer?
                 pass
                 
            # Special logic for trans/none
            if label == "": # Trans
                 key_color = (60, 60, 60)
                 text_color = (150, 150, 150)
                 label = "▽"
            elif label == "X": # None
                 key_color = (50, 50, 50)
                 text_color = (100, 100, 100)
            
            # Draw Key Rect
            shape = [(x, y), (x + KEY_W, y + KEY_H)]
            d.rectangle(shape, fill=key_color, outline=(100, 100, 100))
            
            # Draw Label
            # Center text
            bbox = d.textbbox((0,0), label, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            text_x = x + (KEY_W - text_w) / 2
            text_y = y + (KEY_H - text_h) / 2
            d.text((text_x, text_y), label, fill=text_color, font=font)
            
        # Draw Layer Name
        d.text((10, 10), layer_name.upper().replace('_', ' '), fill=(255, 255, 255), font=font)
        
        filename = f"{layer_name}.png"
        path = os.path.join(output_folder, filename)
        img.save(path)
        generated_files.append(filename)
        
    return generated_files

if __name__ == "__main__":
    # Test
    draw_layers("config/corne.keymap", "static/images")

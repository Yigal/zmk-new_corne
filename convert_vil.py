
import json
import re

VIL_FILE = "vail_templates/three_layers.vil"
KEYMAP_FILE = "config/corne.keymap"

# Mapping QMK/VIAL keycodes to ZMK
KEY_MAP = {
    "KC_TRNS": "&trans",
    "KC_NO": "&none",
    "KC_ENT": "&kp RET",
    "KC_ENTER": "&kp RET",
    "KC_BSPACE": "&kp BSPC",
    "KC_SPC": "&kp SPACE",
    "KC_SPACE": "&kp SPACE",
    "KC_MINUS": "&kp MINUS",
    "KC_EQUAL": "&kp EQUAL",
    "KC_LBRC": "&kp LBKT",
    "KC_LBRACKET": "&kp LBKT",
    "KC_RBRC": "&kp RBKT",
    "KC_RBRACKET": "&kp RBKT",
    "KC_BSLASH": "&kp BSLH",
    "KC_SCOLON": "&kp SEMI",
    "KC_QUOTE": "&kp SQT",
    "KC_GRAVE": "&kp GRAVE",
    "KC_COMMA": "&kp COMMA",
    "KC_DOT": "&kp DOT",
    "KC_SLASH": "&kp FSLH",
    "KC_CAPS": "&kp CAPS",
    "KC_LCTRL": "&kp LCTRL",
    "KC_LSHIFT": "&kp LSHIFT",
    "KC_LALT": "&kp LALT",
    "KC_LGUI": "&kp LGUI",
    "KC_RCTRL": "&kp RCTRL",
    "KC_RSHIFT": "&kp RSHIFT",
    "KC_RALT": "&kp RALT",
    "KC_RGUI": "&kp RGUI",
    "KC_APP": "&kp K_APP",
    "KC_ESC": "&kp ESC",
    "KC_GESC": "&kp ESC", # Graze ESC
    "KC_TAB": "&kp TAB",
    "KC_UP": "&kp UP",
    "KC_DOWN": "&kp DOWN",
    "KC_LEFT": "&kp LEFT",
    "KC_RIGHT": "&kp RIGHT",
    "KC_PGUP": "&kp PG_UP",
    "KC_PGDOWN": "&kp PG_DN",
    "KC_HOME": "&kp HOME",
    "KC_END": "&kp END",
    "KC_INS": "&kp INS",
    "KC_DEL": "&kp DEL",
    "KC_DELETE": "&kp DEL",
    "KC_PSCR": "&kp PSCRN",
    "KC_SLCK": "&kp SLCK",
    "KC_PAUSE": "&kp PAUSE",
    # Mouse keys
    "KC_BTN1": "&mkp LCLK",
    "KC_BTN2": "&mkp RCLK",
    "KC_BTN3": "&mkp MCLK",
    "KC_WH_U": "&msc SCRL_UP",
    "KC_WH_D": "&msc SCRL_DOWN",
    "KC_WH_L": "&msc SCRL_LEFT",
    "KC_WH_R": "&msc SCRL_RIGHT",
    "KC_MS_U": "&mmv MOVE_UP",
    "KC_MS_D": "&mmv MOVE_DOWN",
    "KC_MS_L": "&mmv MOVE_LEFT",
    "KC_MS_R": "&mmv MOVE_RIGHT",
     # Media
    "KC_MPLY": "&kp C_PP",
    "KC_MUTE": "&kp C_MUTE",
    "KC_VOLD": "&kp C_VOL_DN",
    "KC__VOLDOWN": "&kp C_VOL_DN",
    "KC_VOLU": "&kp C_VOL_UP",
    "KC__VOLUP": "&kp C_VOL_UP",
    "KC_MNXT": "&kp C_NEXT",
    "KC_MPRV": "&kp C_PREV",
    "KC_MSTP": "&kp C_STOP",
    "KC_MFFD": "&kp C_FF",
    "KC_MRWD": "&kp C_RW",
    "KC_BRIU": "&kp C_BRI_UP",
    "KC_BRID": "&kp C_BRI_DN",
    
}

def parse_keycode(qc):
    if isinstance(qc, int):
        if qc == -1: return "" # Skip gaps
        return f"&kp {qc}" # Fallback for raw ints if needed

    # Basic mapping
    if qc in KEY_MAP:
        return KEY_MAP[qc]
    
    # Simple KC_ prefix strip for letters/numbers/F-keys
    if qc.startswith("KC_"):
        suffix = qc[3:]
        if len(suffix) == 1 and suffix.isalnum():
             return f"&kp {suffix}"
        if re.match(r"F\d+", suffix):
             return f"&kp {suffix}"
        if suffix.isdigit():
             return f"&kp N{suffix}"

    # Modifiers: LCTL(KC_X) -> &kp LC(X)
    # ZMK modifiers are: LS(x), LC(x), LA(x), LG(x)
    mod_map = {
        "LCTL": "LC", "RCTL": "RC",
        "LSFT": "LS", "RSFT": "RS",
        "LALT": "LA", "RALT": "RA",
        "LGUI": "LG", "RGUI": "RG"
    }

    match = re.match(r"([A-Z]+)\((.+)\)", qc)
    if match:
        func = match.group(1)
        arg = match.group(2)
        
        # Layer MO(1) -> &mo 1
        if func == "MO":
            return f"&mo {arg}"
        
        # Layer Tap LT2(KC_SPACE) -> &lt 2 SPACE
        if func.startswith("LT"):
            layer = func[2:]
            inner_key = parse_keycode(arg).replace("&kp ", "")
            return f"&lt {layer} {inner_key}"

        # Modifiers
        if func in mod_map:
            zmk_mod = mod_map[func]
            inner_key = parse_keycode(arg).replace("&kp ", "")
            return f"&kp {zmk_mod}({inner_key})"
            
        # Default Layer DF(1) -> &to 1
        if func == "DF":
            return f"&to {arg}"

    return f"&none /* {qc} */"

def convert_layer(layer_data):
    zmk_bindings = []
    
    # Flatten rows to a simple list of keys
    flat_keys = []
    for row in layer_data:
        for k in row:
            if k == -1: continue # Skip visual gaps
            flat_keys.append(k)
            
    # Process 42 keys for Corne
    # The VIL has 4 rows. 
    # Row 0,1,2: 12 keys each (6 left + 6 right) = 36 keys
    # Row 3: Thumb row. Corne has 6 thumbs (3 left + 3 right).
    # VIL Row 3 seems to have gaps or more keys.
    # Let's verify count.
    
    zmk_keys = []
    for k in flat_keys:
        zmk_keys.append(parse_keycode(k))
        
    return zmk_keys

def generate_keymap():
    with open(VIL_FILE, "r") as f:
        data = json.load(f)
        
    layers = data.get("layout", [])
    
    # Header
    output = """/*
 * Copyright (c) 2020 The ZMK Contributors
 *
 * SPDX-License-Identifier: MIT
 */

#include <behaviors.dtsi>
#include <dt-bindings/zmk/keys.h>
#include <dt-bindings/zmk/bt.h>
#include <dt-bindings/zmk/outputs.h>
#include <dt-bindings/zmk/pointing.h>

/ {
        keymap {
                compatible = "zmk,keymap";
"""

    for i, layer in enumerate(layers):
        zmk_keys = convert_layer(layer)
        
        # Format into lines of 12 keys roughly
        # Corne 42 keys: 12, 12, 12, 6
        
        layer_str = f"                layer_{i} {{\n                        bindings = <\n"
        
        # Main rows
        row1 = zmk_keys[0:12]
        row2 = zmk_keys[12:24]
        row3 = zmk_keys[24:36]
        thumbs = zmk_keys[36:]
        
        layer_str += "   " + " ".join(row1) + "\n"
        layer_str += "   " + " ".join(row2) + "\n"
        layer_str += "   " + " ".join(row3) + "\n"
        layer_str += "                    " + " ".join(thumbs) + "\n"
        
        layer_str += "                        >;\n                };\n"
        output += layer_str

    output += "        };\n};\n"
    
    with open(KEYMAP_FILE, "w") as f:
        f.write(output)
        
    print(f"Generated {KEYMAP_FILE} with {len(layers)} layers.")

if __name__ == "__main__":
    generate_keymap()

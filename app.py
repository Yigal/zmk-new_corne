from flask import Flask, render_template, request, redirect, flash, send_file
import os
import json
import re
import subprocess
import shutil
from draw_keymap import draw_layers

app = Flask(__name__)
app.secret_key = 'zmk_secret_key'

UPLOAD_FOLDER = 'vail_templates'
KEYMAP_FILE = 'config/corne.keymap'
FIRMWARE_DIR = 'firmware_latest'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
    "KC_GESC": "&kp ESC", 
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
    "KC_MPLY": "&kp C_PP",
    "KC_MUTE": "&kp C_MUTE",
    "KC_VOLD": "&kp C_VOL_DN",
    "KC_VOLU": "&kp C_VOL_UP",
    "KC_MNXT": "&kp C_NEXT",
    "KC_MPRV": "&kp C_PREV",
    "KC_MSTP": "&kp C_STOP",
    "KC_MFFD": "&kp C_FF",
    "KC_MRWD": "&kp C_RW",
    "KC_BRIU": "&kp C_BRI_UP",
    "KC_BRID": "&kp C_BRI_DN",
    "KC_UNDO": "&kp LC(Z)",
    "KC_CUT": "&kp LC(X)",
    "KC_COPY": "&kp LC(C)",
    "KC_PSTE": "&kp LC(V)",
    "KC_AGIN": "&kp LC(Y)",
    "KC_KP_PLUS": "&kp KP_PLUS",
    "KC_KP_ASTERISK": "&kp KP_MULTIPLY",
    "KC_KP_MINUS": "&kp KP_MINUS",
    "KC_KP_SLASH": "&kp KP_SLASH",
    "KC_KP_EQUAL": "&kp KP_EQUAL",
    "KC_KP_DOT": "&kp KP_DOT",
    "KC_KP_ENTER": "&kp KP_ENTER"
}

def parse_keycode(qc):
    if isinstance(qc, int):
        if qc == -1: return ""
        return f"&kp {qc}"

    if qc in KEY_MAP:
        return KEY_MAP[qc]

    if qc.startswith("KC_"):
        suffix = qc[3:]
        if len(suffix) == 1 and suffix.isalnum(): return f"&kp {suffix}"
        if re.match(r"F\d+", suffix): return f"&kp {suffix}"
        if suffix.isdigit(): return f"&kp N{suffix}"

    mod_map = {
        "LCTL": "LC", "RCTL": "RC", "LSFT": "LS", "RSFT": "RS",
        "LALT": "LA", "RALT": "RA", "LGUI": "LG", "RGUI": "RG"
    }

    match = re.match(r"^([A-Z0-9_]+)\((.+)\)$", qc)
    if match:
        func = match.group(1)
        arg = match.group(2)

        if func == "MO": return f"&mo {arg}"
        if func.startswith("LT"):
            layer = func.replace("LT", "")
            if not layer: layer = parse_keycode(arg).replace("&kp ", "") # Handle LT(layer, key) if formatted differently
            else: # LT1(KC_X)
                 inner_key = parse_keycode(arg).replace("&kp ", "")
                 return f"&lt {layer} {inner_key}"

        if func in mod_map:
            zmk_mod = mod_map[func]
            inner_key = parse_keycode(arg).replace("&kp ", "")
            return f"&kp {zmk_mod}({inner_key})"

        if func == "DF": return f"&to {arg}"

    return f"&none /* {qc} */"

def convert_vil_to_keymap(filepath):
    with open(filepath, "r") as f:
        data = json.load(f)
    layers = data.get("layout", [])
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
        # Flatten and filter -1
        flat_keys = [k for row in layer for k in row if k != -1]
        zmk_keys = [parse_keycode(k) for k in flat_keys]
        
        # Corne Layout assumed 42 keys: 12, 12, 12, 6 (3+3)
        # VIL might have more or fewer, we take first 42 if available
        # But wait, User VIL has 4 rows.
        # Row 3 in VIL often is 12 length with gaps.
        # We will trust the flatten order and split into 12, 12, 12, 6
        
        row1 = zmk_keys[0:12] if len(zmk_keys) >= 12 else zmk_keys
        row2 = zmk_keys[12:24] if len(zmk_keys) >= 24 else zmk_keys[12:]
        row3 = zmk_keys[24:36] if len(zmk_keys) >= 36 else zmk_keys[24:]
        thumbs = zmk_keys[36:] 

        output += f"                layer_{i} {{\n                        bindings = <\n"
        output += "   " + " ".join(row1) + "\n"
        output += "   " + " ".join(row2) + "\n"
        output += "   " + " ".join(row3) + "\n"
        output += "                    " + " ".join(thumbs) + "\n"
        output += "                        >;\n                };\n"

    output += "        };\n};\n"
    with open(KEYMAP_FILE, "w") as f:
        f.write(output)
    
    return len(layers)

@app.route('/')
def index():
    templates = []
    if os.path.exists(UPLOAD_FOLDER):
        templates = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.vil')]
    return render_template('index.html', templates=templates)

@app.route('/upload', methods=['POST'])
def convert_layout():
    # Re-fetch templates for the re-render
    templates = []
    if os.path.exists(UPLOAD_FOLDER):
        templates = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.vil')]

    uploaded_file = request.files.get('vil_file')
    selected_file = request.form.get('existing_file')
    
    filepath = None
    
    if uploaded_file and uploaded_file.filename != '':
        filepath = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
        uploaded_file.save(filepath)
    elif selected_file:
        filepath = os.path.join(UPLOAD_FOLDER, selected_file)
    
    if not filepath or not os.path.exists(filepath):
        flash('No valid file provided')
        return redirect('/')

    conversion_stats = None
    keymap_content = None
    layer_images = []

    try:
        layer_count = convert_vil_to_keymap(filepath)
        filename = os.path.basename(filepath)
        flash(f'Successfully converted {filename}!')
        
        # Generate Images
        layer_images = draw_layers(KEYMAP_FILE, 'static/images')
        
        conversion_stats = f"Source: {filename}\nLayers Found: {layer_count}\nOutput Target: {KEYMAP_FILE}\nImages Generated: {len(layer_images)}"
        
        if os.path.exists(KEYMAP_FILE):
             with open(KEYMAP_FILE, 'r') as f:
                 keymap_content = f.read()
                 
    except Exception as e:
        flash(f'Error converting file: {str(e)}')
        
    return render_template('index.html', templates=templates, conversion_stats=conversion_stats, keymap_content=keymap_content, layer_images=layer_images)

import time

BUILD_LOG_FILE = 'build_progress.log'
build_start_time = None

@app.route('/git_push', methods=['POST'])
def git_push():
    global build_start_time
    build_start_time = time.time()
    
    # Initialize Log
    with open(BUILD_LOG_FILE, 'w') as f:
        f.write("--- Starting Build Process ---\n")

    def log_cmd(args):
        with open(BUILD_LOG_FILE, 'a') as f:
            f.write(f"\n> {' '.join(args)}\n")
        subprocess.run(args, stdout=open(BUILD_LOG_FILE, 'a'), stderr=subprocess.STDOUT, check=False)

    try:
        log_cmd(["git", "add", "."])
        log_cmd(["git", "commit", "--allow-empty", "-m", "Update keymap via Web UI"])
        # Check if push succeeds
        with open(BUILD_LOG_FILE, 'a') as f:
            f.write("\n> git push\n")
        subprocess.run(["git", "push"], stdout=open(BUILD_LOG_FILE, 'a'), stderr=subprocess.STDOUT, check=True)
        
        # Start Watcher (it will append to the same log)
        subprocess.Popen(["nohup", "./watch_build.sh", "&"], shell=False)
        
        return {"status": "success", "message": "Build triggered successfully"}
        
    except Exception as e:
        with open(BUILD_LOG_FILE, 'a') as f:
            f.write(f"\nCRITICAL ERROR: {str(e)}\n")
        return {"status": "error", "message": str(e)}, 500

@app.route('/build_status')
def build_status():
    logs = ""
    duration = 0
    if os.path.exists(BUILD_LOG_FILE):
        with open(BUILD_LOG_FILE, 'r') as f:
            logs = f.read()
    
    if build_start_time:
        duration = int(time.time() - build_start_time)
        
    return {"logs": logs, "duration": duration}

@app.route('/flash/left', methods=['POST'])
def flash_left():
    try:
        subprocess.run(["python3", "flash_left.py"], check=True)
        flash('Left side flashed successfully (if connected).')
    except Exception as e:
        flash(f'Flash Error: {str(e)}')
    return redirect('/')

@app.route('/flash/right', methods=['POST'])
def flash_right():
    try:
        subprocess.run(["python3", "flash_right.py"], check=True)
        flash('Right side flashed successfully (if connected).')
    except Exception as e:
        flash(f'Flash Error: {str(e)}')
    return redirect('/')

if __name__ == '__main__':
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            port = config.get('port', 5000)
    except FileNotFoundError:
        port = 5000
        
    app.run(debug=True, port=port)

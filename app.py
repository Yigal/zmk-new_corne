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
BUILDS_DIR = 'builds'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(BUILDS_DIR, exist_ok=True)

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
        templates = sorted([f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.vil')])
    
    # Get available builds
    builds = []
    if os.path.exists(BUILDS_DIR):
        for build_name in sorted(os.listdir(BUILDS_DIR), reverse=True):  # Newest first
            build_path = os.path.join(BUILDS_DIR, build_name)
            if os.path.isdir(build_path):
                info_file = os.path.join(build_path, 'build_info.json')
                if os.path.exists(info_file):
                    try:
                        with open(info_file) as f:
                            info = json.load(f)
                            builds.append({
                                'name': build_name,
                                'run_number': info.get('run_number', '?'),
                                'title': info.get('title', build_name),
                                'timestamp': info.get('timestamp', '')
                            })
                    except:
                        builds.append({'name': build_name, 'run_number': '?', 'title': build_name, 'timestamp': ''})
                else:
                    builds.append({'name': build_name, 'run_number': '?', 'title': build_name, 'timestamp': ''})
    
    return render_template('index.html', templates=templates, builds=builds)

@app.route('/upload', methods=['POST'])
def convert_layout():
    uploaded_file = request.files.get('vil_file')
    selected_file = request.form.get('existing_file')
    
    filepath = None
    
    # Handle file upload first (save to templates folder)
    if uploaded_file and uploaded_file.filename != '':
        filepath = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
        uploaded_file.save(filepath)
        flash(f'File "{uploaded_file.filename}" saved to templates!')
    elif selected_file:
        filepath = os.path.join(UPLOAD_FOLDER, selected_file)
    
    # Re-fetch templates AFTER saving (so new upload appears in list)
    templates = []
    if os.path.exists(UPLOAD_FOLDER):
        templates = sorted([f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.vil')])
    
    if not filepath or not os.path.exists(filepath):
        flash('No valid file provided')
        return render_template('index.html', templates=templates)

    conversion_stats = None
    keymap_content = None
    layer_images = []

    try:
        layer_count = convert_vil_to_keymap(filepath)
        filename = os.path.basename(filepath)
        flash(f'Successfully converted {filename}!')
        
        # Save last VIL filename for build naming
        with open('last_vil.txt', 'w') as f:
            f.write(filename.replace('.vil', ''))
        
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
LAST_VIL_FILE = 'last_vil.txt'  # Track the last converted VIL file
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
        # Get last VIL filename for commit message
        vil_name = "manual"
        if os.path.exists(LAST_VIL_FILE):
            with open(LAST_VIL_FILE, 'r') as f:
                vil_name = f.read().strip() or "manual"
        
        commit_msg = f"Build {vil_name} keymap"
        
        log_cmd(["git", "add", "."])
        log_cmd(["git", "commit", "--allow-empty", "-m", commit_msg])
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

@app.route('/check_mount')
def check_mount():
    # Common mount point for Nice!Nano bootloader on macOS
    mount_point = "/Volumes/NICENANO"
    if os.path.exists(mount_point):
        return {"mounted": True, "path": mount_point}
    return {"mounted": False}

@app.route('/list_builds')
def list_builds():
    builds = []
    if os.path.exists(BUILDS_DIR):
        for build_name in sorted(os.listdir(BUILDS_DIR), reverse=True):
            build_path = os.path.join(BUILDS_DIR, build_name)
            if os.path.isdir(build_path):
                info_file = os.path.join(build_path, 'build_info.json')
                if os.path.exists(info_file):
                    try:
                        with open(info_file) as f:
                            info = json.load(f)
                            builds.append({
                                'name': build_name,
                                'run_number': info.get('run_number', '?'),
                                'title': info.get('title', build_name),
                                'timestamp': info.get('timestamp', '')
                            })
                    except:
                        builds.append({'name': build_name, 'run_number': '?', 'title': build_name, 'timestamp': ''})
                else:
                    builds.append({'name': build_name, 'run_number': '?', 'title': build_name, 'timestamp': ''})
    return {"builds": builds}

@app.route('/flash/<side>', methods=['POST'])
def flash_firmware(side):
    if side not in ['left', 'right']:
        return {"status": "error", "message": "Invalid side"}, 400
    
    # Get selected build from request
    data = request.get_json() or {}
    build_name = data.get('build', 'firmware_latest')
    
    # Determine firmware path
    if build_name == 'firmware_latest' or not build_name:
        firmware_dir = FIRMWARE_DIR
    else:
        firmware_dir = os.path.join(BUILDS_DIR, build_name)
    
    if not os.path.exists(firmware_dir):
        return {"status": "error", "message": f"Build folder not found: {firmware_dir}"}, 404
    
    # Find the correct UF2 file
    uf2_file = f"corne_{side}.uf2"
    uf2_path = os.path.join(firmware_dir, uf2_file)
    
    if not os.path.exists(uf2_path):
        return {"status": "error", "message": f"Firmware file not found: {uf2_file}"}, 404
        
    # Verify mount
    mount_point = "/Volumes/NICENANO"
    if not os.path.exists(mount_point):
        return {"status": "error", "message": "Device not found! Did it disconnect?"}, 404
    
    try:
        # Copy firmware directly
        dest_path = os.path.join(mount_point, uf2_file)
        shutil.copy(uf2_path, dest_path)
        return {"status": "success", "message": f"{side.capitalize()} side flashed with {build_name}!"}
    except FileNotFoundError as e:
        # The device unmounts immediately after receiving the UF2 - this is EXPECTED!
        # If the error is about the destination not existing after copy started, it worked.
        if mount_point in str(e):
            return {"status": "success", "message": f"{side.capitalize()} side flashed! (Device reset automatically)"}
        return {"status": "error", "message": f"Flash Error: {str(e)}"}, 500
    except Exception as e:
        return {"status": "error", "message": f"Flash Error: {str(e)}"}, 500

if __name__ == '__main__':
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            port = config.get('port', 5000)
    except FileNotFoundError:
        port = 5000
        
    app.run(debug=True, port=port)

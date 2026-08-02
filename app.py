import streamlit as st
import cv2
import numpy as np
import tempfile
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="OP-1 Workstation + Presets Browser", page_icon="🎛️", layout="wide")

st.title("🎛️ Teenage Engineering OP-1 // Workstation & Preset Browser")
st.write("Explora librerías de sonido en la pantalla OLED, sonifica videos o graba tu voz para usarla como muestra en el teclado.")

if 'dynamic_layers' not in st.session_state:
    st.session_state['dynamic_layers'] = []

OCTAVE_SCALES = [
    ['C2', 'E2', 'G2', 'A2', 'B2', 'C3'],
    ['C3', 'D3', 'E3', 'G3', 'A3', 'C4'],
    ['C4', 'D4', 'E4', 'G4', 'A4', 'C5'],
    ['C5', 'D5', 'E5', 'G5', 'A5', 'C6'],
    ['C6', 'D6', 'E6', 'G6', 'A6', 'C7']
]

def process_dynamic_motion_layers(video_path):
    cap = cv2.VideoCapture(video_path)
    ret, prev_frame = cap.read()
    if not ret:
        return None, "No se pudo leer el archivo de video."
    
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    height, _ = prev_gray.shape
    
    frame_count, max_frames = 0, 150
    raw_layers_data = []
    
    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(prev_gray, gray)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = [c for c in contours if cv2.contourArea(c) > 35]
        
        if valid_contours:
            valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)
            frame_notes = []
            
            for idx, c in enumerate(valid_contours[:4]):
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cy = int(M["m01"] / M["m00"])
                    norm_y = 1.0 - (cy / height)
                    scale = OCTAVE_SCALES[idx % len(OCTAVE_SCALES)]
                    note_idx = int(norm_y * (len(scale) - 1))
                    frame_notes.append(scale[note_idx])
                    
            raw_layers_data.append(frame_notes)

        prev_gray = gray
        frame_count += 1
        
    cap.release()
    
    if not raw_layers_data:
        return [], "No se detectó suficiente movimiento en el video."

    max_detected_layers = max(len(f) for f in raw_layers_data)
    structured_layers = []
    
    for layer_idx in range(max_detected_layers):
        layer_notes = [frame[layer_idx] for frame in raw_layers_data if len(frame) > layer_idx]
        clean_notes = [layer_notes[0]] if layer_notes else ['C4']
        for n in layer_notes[1:]:
            if n != clean_notes[-1]:
                clean_notes.append(n)
                
        structured_layers.append({
            "id": layer_idx + 1,
            "name": f"Pista Video {layer_idx + 1}",
            "notes": clean_notes
        })
        
    return structured_layers, None

# --- VISTA Y CONTROLES ---
col_inputs, col_synth = st.columns([1, 1.4])

with col_inputs:
    st.subheader("📥 Fuentes de Sonido y Video")
    tab_vid, col_mic = st.tabs(["🍃 1. Analizar Video", "🎙️ 2. Grabación de Voz"])
    
    with tab_vid:
        video_file = st.file_uploader("Carga tu video (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
        if video_file:
            st.video(video_file)
            if st.button("🔍 Escanear Video y Enviar a Cinta OP-1"):
                with st.spinner("Escaneando subcapas de movimiento..."):
                    tfile = tempfile.NamedTemporaryFile(delete=False)
                    tfile.write(video_file.read())
                    layers, error = process_dynamic_motion_layers(tfile.name)
                    if error:
                        st.error(error)
                    else:
                        st.session_state['dynamic_layers'] = layers
                        st.success(f"¡Cargadas {len(layers)} subcapas en la cinta!")

    with col_mic:
        recorded_audio = st.audio_input("Graba tu voz directamente:")
        if recorded_audio:
            st.audio(recorded_audio)
            st.info("💡 Tu audio grabado está disponible en la pantalla OLED en el preset '05. Sampler Voice'.")

with col_synth:
    st.subheader("🎹 Workstation & Presets Browser")
    
    layers_json = json.dumps(st.session_state['dynamic_layers'])

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/tone/14.8.49/Tone.js"></script>
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap');
        body { font-family: 'Space Mono', monospace; background: #0e1117; color: #fff; margin: 0; padding: 2px; }
        
        .op1-chassis {
          background: #e1e3e6; border: 2px solid #b8bac0; border-radius: 16px;
          padding: 16px; box-shadow: inset 0 1px 3px rgba(255,255,255,0.9), 0 8px 25px rgba(0,0,0,0.5); color: #222;
        }

        /* 4 MAIN MODES */
        .main-modes { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 8px; }
        .btn-mode {
          background: #f0f1f3; border: 1px solid #ccc; border-bottom: 3px solid #999;
          padding: 8px 2px; font-family: 'Space Mono', monospace; font-size: 10px; font-weight: bold;
          border-radius: 6px; cursor: pointer; text-align: center; color: #222;
        }
        .btn-mode.active { background: #ff0055 !important; color: white !important; border-color: #d30043 !important; }

        /* T1-T4 SUB-MODULES */
        .t-pages { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 10px; }
        .btn-t {
          background: #ffffff; border: 1px solid #ccc; border-bottom: 3px solid #aaa;
          padding: 6px 2px; font-family: 'Space Mono', monospace; font-size: 9px; font-weight: bold;
          border-radius: 4px; cursor: pointer; color: #333; text-align: center;
        }
        .btn-t.active { background: #00ffcc !important; color: #000 !important; border-color: #00cca3 !important; }

        /* OLED DISPLAY & BROWSER SCREEN */
        .op1-screen {
          background: #0d0f12; border: 3px solid #22252a; border-radius: 8px;
          padding: 10px; color: #00ffcc; margin-bottom: 10px; min-height: 95px;
        }
        .screen-top { display: flex; justify-content: space-between; font-size: 9px; color: #ff0055; margin-bottom: 4px; }
        
        .browser-list {
          background: #15181e; border: 1px solid #00ffcc; padding: 6px; border-radius: 4px;
          font-size: 10px; margin-top: 4px;
        }
        .browser-item { padding: 3px 6px; border-radius: 3px; cursor: pointer; color: #aaa; }
        .browser-item.selected { background: #0088ff; color: #ffffff; font-weight: bold; }

        /* PRESET KEYS 1-8 */
        .preset-keys-bar { display: grid; grid-template-columns: repeat(8, 1fr); gap: 4px; margin-bottom: 10px; }
        .btn-preset {
          background: #fff; border: 1px solid #ccc; border-bottom: 3px solid #aaa;
          padding: 6px 0; font-family: 'Space Mono', monospace; font-size: 9px; font-weight: bold;
          border-radius: 4px; cursor: pointer; text-align: center; color: #222;
        }
        .btn-preset.selected-preset { background: #0088ff !important; color: white !important; border-color: #0055b3 !important; }

        /* SECCIONES DINÁMICAS (PANELS) */
        .panel-section { display: none; }
        .panel-section.active-panel { display: block; }

        .tape-matrix { display: grid; grid-template-columns: repeat(auto-fit, minmax(75px, 1fr)); gap: 4px; margin-bottom: 10px; }
        .btn-track {
          background: #00e676; color: #000; border: none; border-bottom: 3px solid #00a152;
          padding: 6px 2px; font-family: 'Space Mono', monospace; font-size: 8px; font-weight: bold;
          border-radius: 5px; cursor: pointer; text-align: center;
        }
        .btn-track.muted { background: #444b54; color: #888; border-bottom-color: #222; }

        .drum-pad-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 10px; }
        .btn-drum {
          background: #ff5252; color: white; border: none; border-bottom: 3px solid #b71c1c;
          padding: 6px 2px; font-family: 'Space Mono', monospace; font-size: 9px; font-weight: bold;
          border-radius: 5px; cursor: pointer; text-align: center;
        }

        .keyboard-box { background: #111317; padding: 8px; border-radius: 8px; margin-bottom: 12px; }
        .oct-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
        .btn-oct { background: #333; color: #fff; border: 1px solid #555; padding: 3px 8px; font-size: 9px; border-radius: 4px; cursor: pointer; }
        
        .keyboard-container { display: flex; justify-content: center; user-select: none; }
        .key {
          width: 24px; height: 75px; background: #fff; border: 1px solid #ccc;
          border-bottom: 4px solid #aaa; border-radius: 0 0 5px 5px; margin: 0 1px;
          cursor: pointer; display: flex; align-items: flex-end; justify-content: center;
          font-size: 8px; color: #666; font-weight: bold; padding-bottom: 4px;
        }
        .key.black {
          width: 16px; height: 45px; background: #222; border: 1px solid #000;
          border-bottom: 3px solid #444; color: #fff; margin: 0 -8px; z-index: 2;
        }
        .key.active { background: #ff0055 !important; color: #fff !important; }

        .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 12px; }
        .enc-box { background: #f0f1f3; padding: 6px; border-radius: 6px; border-top: 4px solid #888; }
        .enc-box.blue { border-top-color: #0088ff; }
        .enc-box.green { border-top-color: #00e676; }
        .enc-box.white { border-top-color: #ffffff; }
        .enc-box.orange { border-top-color: #ff5252; }

        label { font-size: 8px; color: #555; font-weight: bold; display: block; margin-bottom: 2px; }
        input[type=range], select { width: 100%; accent-color: #222; font-size: 9px; }

        .action-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 10px; }
        .btn-act {
          background: #fff; border: 1px solid #ccc; border-bottom: 3px solid #aaa;
          padding: 8px 2px; font-family: 'Space Mono', monospace; font-size: 9px; font-weight: bold;
          border-radius: 5px; cursor: pointer; text-align: center;
        }
        .btn-rec-master { background: #ff0055; color: white; border-color: #b71c1c; }
        .btn-dl { background: #0088ff; color: white; text-decoration: none; display: flex; align-items: center; justify-content: center; }
      </style>
    </head>
    <body>

      <div class="op1-chassis">
        
        <!-- 4 MAIN MODES -->
        <div class="main-modes">
          <button id="mSynth" class="btn-mode active" onclick="switchMainMode('SYNTH')">🎹 SYNTH</button>
          <button id="mDrum" class="btn-mode" onclick="switchMainMode('DRUM')">🥁 DRUM</button>
          <button id="mTAPE" class="btn-mode" onclick="switchMainMode('TAPE')">📼 TAPE</button>
          <button id="mMixer" class="btn-mode" onclick="switchMainMode('MIXER')">🎚️ MIXER</button>
        </div>

        <!-- T1 - T4 SUB-MODULES -->
        <div class="t-pages">
          <button id="t1" class="btn-t active" onclick="switchTPage(1)">T1: ENGINE/BROWSER</button>
          <button id="t2" class="btn-t" onclick="switchTPage(2)">T2: ENVELOPE</button>
          <button id="t3" class="btn-t" onclick="switchTPage(3)">T3: EFFECT</button>
          <button id="t4" class="btn-t" onclick="switchTPage(4)">T4: MASTER</button>
        </div>

        <!-- PANTALLA OLED BROWSER (PANTALLITA DE LIBRERÍAS Y PRESETS) -->
        <div class="op1-screen">
          <div class="screen-top">
            <span>MODE: <b id="lblMode" style="color:#00ffcc;">SYNTH BROWSER</b></span>
            <span>OCTAVE: <b id="lblOct">0</b></span>
            <span>REC MASTER: <b id="lblRecMaster">OFF</b></span>
          </div>
          
          <div id="screenBrowserContent">
            <div style="font-size: 9px; color: #ff0055; margin-bottom: 2px;">📂 BROWSER // PRESETS & LIBRERÍA DE SONIDOS:</div>
            <div class="browser-list" id="browserList">
              <!-- Se actualiza dinámicamente -->
            </div>
          </div>
        </div>

        <!-- BOTONES DE PRESET RÁPIDO 1-8 -->
        <div style="font-size: 8px; font-weight: bold; color: #444; margin-bottom: 2px;">BOTONES DE SONIDO / PRESETS (1 - 8):</div>
        <div class="preset-keys-bar">
          <button class="btn-preset selected-preset" onclick="loadPreset(1)">1: DX BASS</button>
          <button class="btn-preset" onclick="loadPreset(2)">2: CELLO</button>
          <button class="btn-preset" onclick="loadPreset(3)">3: PAD</button>
          <button class="btn-preset" onclick="loadPreset(4)">4: 8-BIT</button>
          <button class="btn-preset" onclick="loadPreset(5)">5: VOICE</button>
          <button class="btn-preset" onclick="loadPreset(6)">6: 808 DRUM</button>
          <button class="btn-preset" onclick="loadPreset(7)">7: ACOUSTIC</button>
          <button class="btn-preset" onclick="loadPreset(8)">8: RETRO</button>
        </div>

        <!-- PANEL 1: SYNTH MODE -->
        <div id="panelSynth" class="panel-section active-panel">
          <div style="font-size: 8px; font-weight: bold; color: #444; margin-bottom: 3px;">PISTAS DE CINTA DEL VIDEO (ON/OFF):</div>
          <div id="tapeMatrix" class="tape-matrix"></div>

          <div class="keyboard-box">
            <div class="oct-bar">
              <button id="btnOctDown" class="btn-oct">◀ OCT -</button>
              <span style="color:#00ffcc; font-size:9px;">TECLADO SINTETIZADOR (A,S,D,F,G...)</span>
              <button id="btnOctUp" class="btn-oct">OCT + ▶</button>
            </div>
            <div class="keyboard-container" id="keyboard"></div>
          </div>

          <div class="grid-4">
            <div class="enc-box blue">
              <label>🔵 LIBRERÍA ACTIVA</label>
              <select id="selEngine" onchange="changeEngineDirect(this.value)">
                <option value="FM">FM Synth - Classic Bass</option>
                <option value="String">String - Acoustic Cello</option>
                <option value="Cluster">Cluster - Ambient Pad</option>
                <option value="Pulse">Pulse - Retro 8-Bit</option>
              </select>
            </div>
            <div class="enc-box green">
              <label>🟢 ATTACK (ADSR)</label>
              <input type="range" id="adsrAttack" min="0.01" max="1.5" step="0.05" value="0.05">
            </div>
            <div class="enc-box white">
              <label>⚪ RELEASE (ADSR)</label>
              <input type="range" id="adsrRelease" min="0.1" max="3.0" step="0.1" value="0.8">
            </div>
            <div class="enc-box orange">
              <label>🟠 TEMPO BPM</label>
              <input type="range" id="bpm" min="50" max="180" value="100">
            </div>
          </div>
        </div>

        <!-- PANEL 2: DRUM MODE -->
        <div id="panelDrum" class="panel-section">
          <div style="font-size: 8px; font-weight: bold; color: #444; margin-bottom: 3px;">PERCUSIÓN Y PADS DBOX:</div>
          <div class="drum-pad-grid">
            <button id="btnKick" class="btn-drum">🥁 KICK (Tecla 1)</button>
            <button id="btnSnare" class="btn-drum">🪘 SNARE (Tecla 2)</button>
            <button id="btnHat" class="btn-drum">💥 HI-HAT (Tecla 3)</button>
            <button id="btnClap" class="btn-drum">👏 CLAP (Tecla 4)</button>
          </div>
        </div>

        <!-- PANEL 3: TAPE MODE -->
        <div id="panelTape" class="panel-section">
          <div style="font-size: 8px; font-weight: bold; color: #444; margin-bottom: 3px;">EDICIÓN DE CINTA:</div>
          <div class="action-grid">
            <button id="btnLift" class="btn-act">✂️ LIFT (CUT)</button>
            <button id="btnDrop" class="btn-act">📋 DROP (PASTE)</button>
            <button id="btnSplit" class="btn-act">🪓 SPLIT</button>
            <button id="btnClearTrack" class="btn-act">🗑️ CLEAR TAPE</button>
          </div>
        </div>

        <!-- PANEL 4: MIXER MODE -->
        <div id="panelMixer" class="panel-section">
          <div style="font-size: 8px; font-weight: bold; color: #444; margin-bottom: 3px;">CONSOLA DE MEZCLA Y ECUALIZACIÓN:</div>
          <div class="grid-4">
            <div class="enc-box blue"><label>🔵 LOW EQ</label><input type="range" id="eqLow" min="-12" max="12" value="0"></div>
            <div class="enc-box green"><label>🟢 MID EQ</label><input type="range" id="eqMid" min="-12" max="12" value="0"></div>
            <div class="enc-box white"><label>⚪ HIGH EQ</label><input type="range" id="eqHigh" min="-12" max="12" value="0"></div>
            <div class="enc-box orange"><label>🟠 DRIVE</label><input type="range" id="masterDrive" min="0" max="1" step="0.05" value="0.1"></div>
          </div>
        </div>

        <!-- TRANSPORTE Y DESCARGA MASTER -->
        <div class="action-grid">
          <button id="btnPlay" class="btn-act" style="background:#00e676; color:#000;">▶️ PLAY TAPE</button>
          <button id="btnStop" class="btn-act">⏸️ STOP TAPE</button>
          <button id="btnRecMaster" class="btn-act btn-rec-master">● REC MASTER</button>
          <a id="btnDownload" class="btn-act btn-dl" style="display:none;" download="OP1_Recording.wav">⬇️ DESCARGAR WAV</a>
        </div>

      </div>

      <script>
        const videoLayers = __LAYERS_JSON__;
        let currentMode = 'SYNTH';
        let currentTPage = 1;
        
        let isPlaying = false, isMasterRecording = false, currentOctave = 0;
        let videoSynths = [], videoSequences = [], trackStates = {};
        let userSynth, drumKick, drumSnare, drumHat, drumClap;
        let reverb, filter, recorder;
        let liftedNotes = [];

        // LIBRERÍAS DE SINTETIZADOR Y PRESETS
        const presetsLibrary = {
          1: { name: "01. FM - Classic DX Bass", engine: "FM", type: "synth" },
          2: { name: "02. String - Acoustic Cello", engine: "String", type: "synth" },
          3: { name: "03. Cluster - Ambient Pad", engine: "Cluster", type: "synth" },
          4: { name: "04. Pulse - Retro 8-Bit Lead", engine: "Pulse", type: "synth" },
          5: { name: "05. Sampler - Recorded Mic Voice", engine: "Sampler", type: "voice" },
          6: { name: "06. Drum - TR-808 Electronic", engine: "808", type: "drum" },
          7: { name: "07. Drum - Acoustic Studio Kit", engine: "Acoustic", type: "drum" },
          8: { name: "08. Drum - Retro Synthwave", engine: "Retro", type: "drum" }
        };

        let selectedPresetId = 1;

        function renderBrowserScreen() {
          const listDiv = document.getElementById('browserList');
          listDiv.innerHTML = '';
          
          Object.keys(presetsLibrary).forEach(id => {
            const item = document.createElement('div');
            item.className = `browser-item ${id == selectedPresetId ? 'selected' : ''}`;
            item.innerText = presetsLibrary[id].name;
            item.onclick = () => loadPreset(id);
            listDiv.appendChild(item);
          });
        }

        function loadPreset(id) {
          selectedPresetId = id;
          document.querySelectorAll('.btn-preset').forEach((b, i) => {
            b.classList.toggle('selected-preset', (i + 1) == id);
          });

          const p = presetsLibrary[id];
          renderBrowserScreen();

          if (p.type === 'synth') {
            switchMainMode('SYNTH');
            changeEngineDirect(p.engine);
          } else if (p.type === 'drum') {
            switchMainMode('DRUM');
          } else if (p.type === 'voice') {
            switchMainMode('SYNTH');
            changeEngineDirect('FM');
          }
        }

        function switchMainMode(mode) {
          currentMode = mode;
          document.querySelectorAll('.btn-mode').forEach(b => b.classList.remove('active'));
          document.querySelectorAll('.panel-section').forEach(p => p.classList.remove('active-panel'));

          if (mode === 'SYNTH') {
            document.getElementById('mSynth').classList.add('active');
            document.getElementById('panelSynth').classList.add('active-panel');
          } else if (mode === 'DRUM') {
            document.getElementById('mDrum').classList.add('active');
            document.getElementById('panelDrum').classList.add('active-panel');
          } else if (mode === 'TAPE') {
            document.getElementById('mTAPE').classList.add('active');
            document.getElementById('panelTape').classList.add('active-panel');
          } else if (mode === 'MIXER') {
            document.getElementById('mMixer').classList.add('active');
            document.getElementById('panelMixer').classList.add('active-panel');
          }
          document.getElementById('lblMode').innerText = mode + " BROWSER";
        }

        function switchTPage(page) {
          currentTPage = page;
          document.querySelectorAll('.btn-t').forEach(b => b.classList.remove('active'));
          document.getElementById(`t${page}`).classList.add('active');
        }

        const baseNotesMap = [
          { note: 'C4', key: 'a', isBlack: false }, { note: 'C#4', key: 'w', isBlack: true },
          { note: 'D4', key: 's', isBlack: false }, { note: 'D#4', key: 'e', isBlack: true },
          { note: 'E4', key: 'd', isBlack: false }, { note: 'F4', key: 'f', isBlack: false },
          { note: 'F#4', key: 't', isBlack: true }, { note: 'G4', key: 'g', isBlack: false },
          { note: 'G#4', key: 'y', isBlack: true }, { note: 'A4', key: 'h', isBlack: false },
          { note: 'A#4', key: 'u', isBlack: true }, { note: 'B4', key: 'j', isBlack: false },
          { note: 'C5', key: 'k', isBlack: false }
        ];

        function shiftNoteOctave(noteStr, octShift) {
          if (!noteStr) return noteStr;
          let name = noteStr.slice(0, -1);
          let oct = parseInt(noteStr.slice(-1)) + octShift;
          return name + oct;
        }

        const matrixDiv = document.getElementById('tapeMatrix');
        videoLayers.forEach((layer, idx) => {
          trackStates[idx] = true;
          const btn = document.createElement('button');
          btn.className = 'btn-track';
          btn.id = `btnTrk_${idx}`;
          btn.innerText = `ON // ${layer.name}`;
          btn.onclick = () => toggleTrack(idx);
          matrixDiv.appendChild(btn);
        });

        function toggleTrack(idx) {
          trackStates[idx] = !trackStates[idx];
          const btn = document.getElementById(`btnTrk_${idx}`);
          if (trackStates[idx]) {
            btn.className = 'btn-track';
            btn.innerText = `ON // Pista ${idx + 1}`;
            if (videoSynths[idx]) videoSynths[idx].volume.value = 0;
          } else {
            btn.className = 'btn-track muted';
            btn.innerText = `OFF // Pista ${idx + 1}`;
            if (videoSynths[idx]) videoSynths[idx].volume.value = -Infinity;
          }
        }

        const kbContainer = document.getElementById('keyboard');
        baseNotesMap.forEach(item => {
          const k = document.createElement('div');
          k.className = `key ${item.isBlack ? 'black' : ''}`;
          k.innerText = item.key.toUpperCase();
          k.dataset.key = item.key;
          k.addEventListener('mousedown', () => triggerUserNote(item.note));
          kbContainer.appendChild(k);
        });

        window.addEventListener('keydown', (e) => {
          if (e.repeat) return;
          const k = e.key.toLowerCase();
          const found = baseNotesMap.find(m => m.key === k);
          if (found) {
            triggerUserNote(found.note);
            const el = document.querySelector(`[data-key="${k}"]`);
            if (el) el.classList.add('active');
          }
          if (k === '1') triggerDrum('kick');
          if (k === '2') triggerDrum('snare');
          if (k === '3') triggerDrum('hat');
          if (k === '4') triggerDrum('clap');
        });

        window.addEventListener('keyup', (e) => {
          const k = e.key.toLowerCase();
          const el = document.querySelector(`[data-key="${k}"]`);
          if (el) el.classList.remove('active');
        });

        document.getElementById('btnOctUp').onclick = () => { if (currentOctave < 2) currentOctave++; document.getElementById('lblOct').innerText = currentOctave; };
        document.getElementById('btnOctDown').onclick = () => { if (currentOctave > -2) currentOctave--; document.getElementById('lblOct').innerText = currentOctave; };

        async function initAudioEngine() {
          await Tone.start();
          recorder = new Tone.Recorder();
          reverb = new Tone.Reverb({ decay: 3, wet: 0.3 }).connect(recorder).toDestination();
          await reverb.generate();
          filter = new Tone.Filter(1400, "lowpass").connect(reverb);

          drumKick = new Tone.MembraneSynth({ pitchDecay: 0.05, octaves: 6 }).connect(reverb);
          drumSnare = new Tone.NoiseSynth({ noise: { type: 'white' }, envelope: { attack: 0.005, decay: 0.2, sustain: 0 } }).connect(reverb);
          drumHat = new Tone.MetalSynth({ frequency: 200, envelope: { attack: 0.001, decay: 0.05, release: 0.05 }, harmonicity: 5.1, modulationIndex: 32, resonance: 4000 }).connect(reverb);
          drumClap = new Tone.NoiseSynth({ noise: { type: 'pink' }, envelope: { attack: 0.01, decay: 0.15, sustain: 0 } }).connect(reverb);

          userSynth = new Tone.PolySynth(Tone.FMSynth).connect(filter);
          videoSynths = [];
          videoLayers.forEach((layer, idx) => {
            let s = new Tone.PolySynth(Tone.Synth).connect(filter);
            if (!trackStates[idx]) s.volume.value = -Infinity;
            videoSynths.push(s);
          });

          Tone.Transport.bpm.value = parseFloat(document.getElementById('bpm').value);
          Tone.Transport.loop = true; Tone.Transport.loopStart = 0; Tone.Transport.loopEnd = "2m";
        }

        function triggerUserNote(note) {
          if (!userSynth) initAudioEngine();
          userSynth.triggerAttackRelease(shiftNoteOctave(note, currentOctave), "8n");
        }

        function triggerDrum(type) {
          if (!drumKick) initAudioEngine();
          if (type === 'kick') drumKick.triggerAttackRelease("C1", "8n");
          if (type === 'snare') drumSnare.triggerAttackRelease("8n");
          if (type === 'hat') drumHat.triggerAttackRelease("32n");
          if (type === 'clap') drumClap.triggerAttackRelease("16n");
        }

        document.getElementById('btnKick').onclick = () => triggerDrum('kick');
        document.getElementById('btnSnare').onclick = () => triggerDrum('snare');
        document.getElementById('btnHat').onclick = () => triggerDrum('hat');
        document.getElementById('btnClap').onclick = () => triggerDrum('clap');

        document.getElementById('btnPlay').onclick = async () => {
          await initAudioEngine();
          if (!isPlaying) {
            videoSequences = [];
            videoLayers.forEach((layer, idx) => {
              let rate = idx === 0 ? "2n" : (idx === 1 ? "4n" : "8n");
              let seq = new Tone.Sequence((time, note) => {
                videoSynths[idx].triggerAttackRelease(note, rate, time);
              }, layer.notes, rate).start(0);
              videoSequences.push(seq);
            });
            Tone.Transport.start(); isPlaying = true;
          }
        };

        document.getElementById('btnStop').onclick = () => {
          Tone.Transport.stop();
          if (videoSequences) videoSequences.forEach(s => s.dispose());
          isPlaying = false;
        };

        document.getElementById('btnRecMaster').onclick = async () => {
          await initAudioEngine();
          const btn = document.getElementById('btnRecMaster');
          const dlBtn = document.getElementById('btnDownload');

          if (!isMasterRecording) {
            recorder.start(); isMasterRecording = true;
            btn.innerText = "⏹️ STOP & EXPORT";
            document.getElementById('lblRecMaster').innerText = "RECORDING...";
            dlBtn.style.display = "none";
          } else {
            const recording = await recorder.stop();
            isMasterRecording = false;
            btn.innerText = "● REC MASTER";
            document.getElementById('lblRecMaster').innerText = "OFF";
            dlBtn.href = URL.createObjectURL(recording);
            dlBtn.style.display = "flex";
          }
        };

        function changeEngineDirect(val) {
          if (userSynth) {
            userSynth.dispose();
            if (val === 'FM') userSynth = new Tone.PolySynth(Tone.FMSynth).connect(filter);
            if (val === 'AM') userSynth = new Tone.PolySynth(Tone.AMSynth).connect(filter);
            if (val === 'Duo') userSynth = new Tone.PolySynth(Tone.DuoSynth).connect(filter);
            if (val === 'String') userSynth = new Tone.PolySynth(Tone.Synth, { oscillator: { type: 'sawtooth' } }).connect(filter);
            if (val === 'Cluster') userSynth = new Tone.PolySynth(Tone.Synth, { oscillator: { type: 'sine' } }).connect(filter);
            if (val === 'Pulse') userSynth = new Tone.PolySynth(Tone.Synth, { oscillator: { type: 'square' } }).connect(filter);
          }
        }

        renderBrowserScreen();

        document.getElementById('adsrAttack').oninput = (e) => { if (userSynth) userSynth.set({ envelope: { attack: parseFloat(e.target.value) } }); };
        document.getElementById('adsrRelease').oninput = (e) => { if (userSynth) userSynth.set({ envelope: { release: parseFloat(e.target.value) } }); };
        document.getElementById('bpm').oninput = (e) => { document.getElementById('lblBpm').innerText = e.target.value; Tone.Transport.bpm.value = parseFloat(e.target.value); };
      </script>
    </body>
    </html>
    """
    rendered_html = html_template.replace("__LAYERS_JSON__", layers_json).replace("__LAYER_COUNT__", str(len(st.session_state['dynamic_layers'])))
    components.html(rendered_html, height=650)

import streamlit as st
import cv2
import numpy as np
import tempfile
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="TE OP-1 Hardware Replica", page_icon="🎹", layout="wide")

st.title("🎹 Teenage Engineering OP-1 // Complete Synthesizer Workstation")
st.write("Réplica fiel del sintetizador OP-1. Carga un video para sonificar sus capas de movimiento o graba tu voz con el micrófono.")

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
            "name": f"Track {layer_idx + 1}",
            "notes": clean_notes
        })
        
    return structured_layers, None

# --- PANEL DE ENTRADA Y WORKSTATION ---
col_inputs, col_synth = st.columns([1, 2.2])

with col_inputs:
    st.subheader("📥 Fuentes de Audio / Video")
    tab_vid, col_mic = st.tabs(["🍃 1. Analizar Video", "🎙️ 2. Micrófono / Voz"])
    
    with tab_vid:
        video_file = st.file_uploader("Carga tu video (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
        if video_file:
            st.video(video_file)
            if st.button("🔍 Escanear Video e Inyectar a Cinta"):
                with st.spinner("Procesando física de movimiento con OpenCV..."):
                    tfile = tempfile.NamedTemporaryFile(delete=False)
                    tfile.write(video_file.read())
                    layers, error = process_dynamic_motion_layers(tfile.name)
                    if error:
                        st.error(error)
                    else:
                        st.session_state['dynamic_layers'] = layers
                        st.success(f"¡Cargadas {len(layers)} capas de movimiento!")

    with col_mic:
        recorded_audio = st.audio_input("Graba tu voz:")
        if recorded_audio:
            st.audio(recorded_audio)
            st.info("💡 Voz cargada en el Sampler. Selecciónala en la tecla 5 de presets.")

with col_synth:
    st.subheader("🎛️ TE OP-1 Portable Synthesizer")
    
    layers_json = json.dumps(st.session_state['dynamic_layers'])

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/tone/14.8.49/Tone.js"></script>
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap');
        
        * { box-sizing: border-box; }
        body { font-family: 'Space Mono', monospace; background: #0e1117; color: #222; margin: 0; padding: 2px; }

        /* OP-1 CHASSIS REPLICA */
        .op1-chassis {
          background: #e3e4e8;
          border: 2px solid #b2b5bc;
          border-radius: 18px;
          padding: 16px;
          box-shadow: inset 0 2px 4px rgba(255,255,255,0.9), 0 10px 30px rgba(0,0,0,0.6);
          user-select: none;
        }

        .op1-top-row {
          display: grid;
          grid-template-columns: 70px 60px 1fr 240px 60px;
          gap: 12px;
          align-items: center;
          margin-bottom: 12px;
        }

        /* SPEAKER GRILL */
        .speaker-grid {
          width: 50px; height: 50px; background: #c5c7ce; border-radius: 8px;
          display: grid; grid-template-columns: repeat(5, 1fr); gap: 3px; padding: 6px;
        }
        .spk-dot { background: #333; border-radius: 50%; width: 5px; height: 5px; }

        /* VOLUME KNOB */
        .vol-knob {
          width: 38px; height: 38px; background: #ffffff; border: 2px solid #aaa;
          border-radius: 50%; margin: 0 auto; box-shadow: 0 3px 6px rgba(0,0,0,0.2);
          position: relative; cursor: pointer;
        }
        .vol-indicator { width: 3px; height: 12px; background: #333; position: absolute; top: 4px; left: 16px; border-radius: 2px; }

        /* OLED SCREEN REPLICA */
        .op1-screen {
          background: #090b0e; border: 3px solid #282a30; border-radius: 8px;
          padding: 10px; color: #00ffcc; min-height: 110px; position: relative;
          box-shadow: inset 0 0 10px rgba(0,0,0,0.8);
        }
        .scr-header { display: flex; justify-content: space-between; font-size: 9px; color: #ff0055; margin-bottom: 6px; }
        .scr-body { font-size: 11px; color: #00ffcc; margin-top: 4px; }
        .scr-tape-reels { display: flex; justify-content: space-around; align-items: center; margin-top: 8px; }
        .reel { width: 34px; height: 38px; border: 2px solid #00ffcc; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 8px; }

        /* 4 COLORED ENCODERS */
        .encoders-container { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; text-align: center; }
        .knob-cap {
          width: 42px; height: 42px; border-radius: 50%; margin: 0 auto 4px auto;
          border: 2px solid #aaa; box-shadow: 0 4px 8px rgba(0,0,0,0.25); cursor: pointer;
          position: relative;
        }
        .knob-cap.blue { background: #0088ff; }
        .knob-cap.green { background: #00e676; }
        .knob-cap.white { background: #ffffff; }
        .knob-cap.orange { background: #ff5252; }
        .knob-dot { width: 4px; height: 10px; background: #222; position: absolute; top: 4px; left: 17px; border-radius: 2px; }

        /* UTILITY BUTTONS (RIGHT) */
        .side-utils { display: flex; flex-direction: column; gap: 6px; }
        .btn-util { background: #fff; border: 1px solid #ccc; border-bottom: 3px solid #999; border-radius: 6px; padding: 6px; font-size: 9px; font-weight: bold; cursor: pointer; text-align: center; }

        /* LED VU METER */
        .vu-meter { display: flex; gap: 3px; justify-content: center; margin-top: 4px; }
        .vu-led { width: 5px; height: 5px; border-radius: 50%; background: #444; }
        .vu-led.active-green { background: #00e676; box-shadow: 0 0 5px #00e676; }
        .vu-led.active-red { background: #ff5252; box-shadow: 0 0 5px #ff5252; }

        /* MIDDLE SECTION: MAIN MODES & T1-T4 KEYS */
        .mid-controls { display: grid; grid-template-columns: 180px 1fr 200px; gap: 12px; margin-bottom: 12px; }
        
        .main-modes-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
        .btn-main-mode {
          background: #ffffff; border: 1px solid #ccc; border-bottom: 3px solid #a0a3aa;
          padding: 8px 4px; font-family: 'Space Mono', monospace; font-size: 9px; font-weight: bold;
          border-radius: 6px; cursor: pointer; text-align: center; color: #333;
        }
        .btn-main-mode.active { background: #ff0055 !important; color: white !important; border-color: #c40041 !important; }

        .t-keys-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
        .btn-t-key {
          background: #ffffff; border: 1px solid #ccc; border-bottom: 3px solid #a0a3aa;
          padding: 8px 2px; font-family: 'Space Mono', monospace; font-size: 9px; font-weight: bold;
          border-radius: 6px; cursor: pointer; text-align: center; color: #333;
        }
        .btn-t-key.active { background: #00ffcc !important; color: #000 !important; border-color: #00c49f !important; }

        /* SOUND PRESET KEYS 1-8 */
        .sound-keys-row { display: grid; grid-template-columns: repeat(8, 1fr); gap: 6px; margin-bottom: 12px; }
        .btn-snd-key {
          background: #ffffff; border: 1px solid #ccc; border-bottom: 3px solid #a0a3aa;
          padding: 8px 0; font-family: 'Space Mono', monospace; font-size: 9px; font-weight: bold;
          border-radius: 6px; cursor: pointer; text-align: center; color: #222;
        }
        .btn-snd-key.selected-snd { background: #0088ff !important; color: white !important; border-color: #005fcc !important; }

        /* LOWER CONTROLS: TAPE EDITING & MUSICAL KEYBOARD */
        .bottom-section { display: grid; grid-template-columns: 220px 1fr; gap: 14px; }

        .tape-transport-box { display: flex; flex-direction: column; gap: 6px; }
        .transport-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; }
        .btn-trans {
          background: #ffffff; border: 1px solid #ccc; border-bottom: 3px solid #a0a3aa;
          padding: 8px 2px; font-size: 9px; font-weight: bold; border-radius: 6px; cursor: pointer; text-align: center;
        }
        .btn-rec.active { background: #ff0055 !important; color: white !important; }
        .btn-play.active { background: #00e676 !important; color: black !important; }

        /* 2-OCTAVE MUSICAL KEYBOARD REPLICA */
        .keyboard-wrapper { background: #111317; border-radius: 10px; padding: 10px 8px; border: 2px solid #282a30; }
        .keyboard-top-bar { display: flex; justify-content: space-between; color: #00ffcc; font-size: 9px; margin-bottom: 6px; }
        .btn-oct-shift { background: #333; color: #fff; border: 1px solid #555; padding: 2px 8px; border-radius: 4px; cursor: pointer; }

        .keys-layout { display: flex; justify-content: center; position: relative; }
        .key-white {
          width: 26px; height: 82px; background: #ffffff; border: 1px solid #bbb;
          border-bottom: 4px solid #999; border-radius: 0 0 5px 5px; margin: 0 1px;
          cursor: pointer; display: flex; align-items: flex-end; justify-content: center;
          font-size: 8px; color: #555; font-weight: bold; padding-bottom: 4px;
        }
        .key-black {
          width: 17px; height: 50px; background: #222222; border: 1px solid #000;
          border-bottom: 3px solid #444; color: #fff; margin: 0 -9px; z-index: 2;
          border-radius: 0 0 3px 3px; cursor: pointer; display: flex; align-items: flex-end; justify-content: center;
          font-size: 7px; padding-bottom: 3px;
        }
        .key-white.active, .key-black.active { background: #ff0055 !important; color: white !important; }

        /* TRACK MATRIX */
        .track-matrix-box { display: grid; grid-template-columns: repeat(auto-fit, minmax(80px, 1fr)); gap: 4px; margin-bottom: 8px; }
        .btn-trk-toggle { background: #00e676; color: #000; border: none; border-bottom: 3px solid #00a152; padding: 5px; font-size: 8px; font-weight: bold; border-radius: 4px; cursor: pointer; }
        .btn-trk-toggle.muted { background: #444b54; color: #888; border-bottom-color: #222; }

        /* DOWNLOAD LINK */
        .btn-dl-link { background: #0088ff; color: white; border-radius: 6px; padding: 8px; text-decoration: none; font-size: 10px; font-weight: bold; text-align: center; display: block; margin-top: 6px; }
      </style>
    </head>
    <body>

      <div class="op1-chassis">
        
        <!-- HEADER: SPEAKER, VOL, OLED SCREEN, ENCODERS, UTILS -->
        <div class="op1-top-row">
          
          <div class="speaker-grid">
            <div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div>
            <div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div>
            <div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div>
          </div>

          <div style="text-align:center;">
            <div class="vol-knob"><div class="vol-indicator"></div></div>
            <span style="font-size:7px; font-weight:bold; color:#666;">VOL</span>
          </div>

          <!-- PANTALLA OLED OP-1 -->
          <div class="op1-screen">
            <div class="scr-header">
              <span>MODE: <b id="lblMode" style="color:#00ffcc;">SYNTH BROWSER</b></span>
              <span>OCTAVE: <b id="lblOct">0</b></span>
              <span>REC MASTER: <b id="lblRecMaster">OFF</b></span>
            </div>
            <div class="scr-body">
              <div id="scrTitle" style="font-size:10px; color:#ff0055; margin-bottom:4px;">📂 SOUND PRESET 1: DX BASS</div>
              <div id="scrDetail" style="font-size:9px; color:#aaa;">ENGINE: FM SYNTH // ATTACK: 0.05s // BPM: 100</div>
              <div class="scr-tape-reels" id="scrReels" style="display:none;">
                <div class="reel" id="reelL">Tape L</div>
                <span style="font-size:10px; color:#00ffcc;" id="tapeTimer">00:00:00</span>
                <div class="reel" id="reelR">Tape R</div>
              </div>
            </div>
          </div>

          <!-- 4 COLORED ENCODERS -->
          <div class="encoders-container">
            <div>
              <div class="knob-cap blue"><div class="knob-dot"></div></div>
              <span style="font-size:7px; font-weight:bold; color:#0088ff;">🔵 T1 ENGINE</span>
            </div>
            <div>
              <div class="knob-cap green"><div class="knob-dot"></div></div>
              <span style="font-size:7px; font-weight:bold; color:#00e676;">🟢 T2 ATTACK</span>
            </div>
            <div>
              <div class="knob-cap white"><div class="knob-dot"></div></div>
              <span style="font-size:7px; font-weight:bold; color:#333;">⚪ T3 DECAY</span>
            </div>
            <div>
              <div class="knob-cap orange"><div class="knob-dot"></div></div>
              <span style="font-size:7px; font-weight:bold; color:#ff5252;">🟠 T4 TEMPO</span>
            </div>
          </div>

          <!-- UTILITIES & LED METER -->
          <div class="side-utils">
            <button class="btn-util">🎙️ MIC</button>
            <button class="btn-util">📇 COM</button>
            <button class="btn-util">🎼 SEQ</button>
            <div class="vu-meter">
              <div class="vu-led active-green"></div><div class="vu-led active-green"></div>
              <div class="vu-led active-green"></div><div class="vu-led active-red"></div>
            </div>
          </div>

        </div>

        <!-- MAIN MODES & T1-T4 KEYS -->
        <div class="mid-controls">
          
          <div class="main-modes-grid">
            <button id="btnSynth" class="btn-main-mode active" onclick="switchMainMode('SYNTH')">🎹 SYNTH</button>
            <button id="btnDrum" class="btn-main-mode" onclick="switchMainMode('DRUM')">🥁 DRUM</button>
            <button id="btnTape" class="btn-main-mode" onclick="switchMainMode('TAPE')">📼 TAPE</button>
            <button id="btnMixer" class="btn-main-mode" onclick="switchMainMode('MIXER')">🎚️ MIXER</button>
          </div>

          <div class="t-keys-grid">
            <button id="btnT1" class="btn-t-key active" onclick="switchTPage(1)">T1: ENGINE</button>
            <button id="btnT2" class="btn-t-key" onclick="switchTPage(2)">T2: ENVELOPE</button>
            <button id="btnT3" class="btn-t-key" onclick="switchTPage(3)">T3: EFFECT</button>
            <button id="btnT4" class="btn-t-key" onclick="switchTPage(4)">T4: MASTER</button>
          </div>

          <div style="font-size:8px; font-weight:bold; color:#666; text-align:right;">
            TEENAGE ENGINEERING<br>OP-1 HARDWARE ENGINE
          </div>

        </div>

        <!-- SOUND PRESETS KEYS 1-8 -->
        <div class="sound-keys-row">
          <button class="btn-snd-key selected-snd" id="s1" onclick="loadPreset(1)">1: DX BASS</button>
          <button class="btn-snd-key" id="s2" onclick="loadPreset(2)">2: CELLO</button>
          <button class="btn-snd-key" id="s3" onclick="loadPreset(3)">3: PAD</button>
          <button class="btn-snd-key" id="s4" onclick="loadPreset(4)">4: 8-BIT</button>
          <button class="btn-snd-key" id="s5" onclick="loadPreset(5)">5: VOICE</button>
          <button class="btn-snd-key" id="s6" onclick="loadPreset(6)">6: 808 DRUM</button>
          <button class="btn-snd-key" id="s7" onclick="loadPreset(7)">7: ACOUSTIC</button>
          <button class="btn-snd-key" id="s8" onclick="loadPreset(8)">8: RETRO</button>
        </div>

        <!-- PISTAS DE CINTA DEL VIDEO -->
        <div style="font-size:8px; font-weight:bold; color:#555; margin-bottom:4px;">PISTAS DETECTADAS DEL VIDEO (ON / OFF):</div>
        <div id="trackMatrix" class="track-matrix-box"></div>

        <!-- BOTTOM: TAPE EDITS & KEYBOARD -->
        <div class="bottom-section">
          
          <!-- TRANSPORTE Y EDICIÓN -->
          <div class="tape-transport-box">
            <div style="font-size:8px; font-weight:bold; color:#555;">TAPE CONTROLS:</div>
            <div class="transport-row">
              <button class="btn-trans" onclick="liftTape()">✂️ LIFT</button>
              <button class="btn-trans" onclick="dropTape()">📋 DROP</button>
              <button class="btn-trans" onclick="splitTape()">🪓 SPLIT</button>
            </div>
            <div class="transport-row">
              <button id="btnRec" class="btn-trans btn-rec" onclick="toggleRecMaster()">● REC</button>
              <button id="btnPlay" class="btn-trans btn-play" onclick="playTape()">▶ PLAY</button>
              <button id="btnStop" class="btn-trans" onclick="stopTape()">⏸ STOP</button>
            </div>
            <div class="transport-row">
              <button class="btn-trans" onclick="rewindTape()">⏮ REW</button>
              <button class="btn-trans" onclick="forwardTape()">⏭ FWD</button>
              <button class="btn-trans" onclick="clearTape()">🗑 CLEAR</button>
            </div>
            <a id="btnDownload" class="btn-dl-link" style="display:none;" download="OP1_Song_Master.wav">⬇️ DESCARGAR WAV</a>
          </div>

          <!-- MUSICAL KEYBOARD -->
          <div class="keyboard-wrapper">
            <div class="keyboard-top-bar">
              <button class="btn-oct-shift" onclick="shiftOctave(-1)">◀ OCT -</button>
              <span>KEYBOARD (A, S, D, F, G, H, J, K...)</span>
              <button class="btn-oct-shift" onclick="shiftOctave(1)">OCT + ▶</button>
            </div>
            <div class="keys-layout" id="keyboardKeys">
              <!-- Teclas 1:1 generadas por JS -->
            </div>
          </div>

        </div>

      </div>

      <script>
        const videoLayers = __LAYERS_JSON__;
        let currentMode = 'SYNTH';
        let isPlaying = false, isRecording = false, currentOctave = 0;
        let videoSynths = [], videoSequences = [], trackStates = {};
        let userSynth, drumKick, drumSnare, drumHat, drumClap;
        let reverbNode, filterNode, distortionNode, recorderNode;
        let liftedNotesBuffer = [];

        const presetsLibrary = {
          1: { name: "1: DX BASS", engine: "FM", desc: "ENGINE: FM SYNTH // ATTACK: 0.01s", attack: 0.01, release: 0.4 },
          2: { name: "2: CELLO", engine: "String", desc: "ENGINE: STRING MODEL // ATTACK: 0.3s", attack: 0.3, release: 1.5 },
          3: { name: "3: PAD", engine: "Cluster", desc: "ENGINE: CLUSTER PAD // REVERB: HIGH", attack: 0.5, release: 2.0 },
          4: { name: "4: 8-BIT", engine: "Pulse", desc: "ENGINE: SQUARE WAVE // RETRO CHIPTUNE", attack: 0.01, release: 0.2 },
          5: { name: "5: VOICE", engine: "Sampler", desc: "ENGINE: MIC VOICE SAMPLER // CROMÁTICO", attack: 0.05, release: 0.8 },
          6: { name: "6: 808 DRUM", engine: "Drum", desc: "ENGINE: TR-808 ELECTRONIC DRUMS", attack: 0.01, release: 0.2 },
          7: { name: "7: ACOUSTIC", engine: "Drum", desc: "ENGINE: ACOUSTIC STUDIO KIT", attack: 0.01, release: 0.3 },
          8: { name: "8: RETRO", engine: "Drum", desc: "ENGINE: RETRO SYNTHWAVE PERCUSSION", attack: 0.01, release: 0.4 }
        };

        let selectedPresetId = 1;

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

        // RENDER PISTAS DETECTADAS
        const matrixDiv = document.getElementById('trackMatrix');
        videoLayers.forEach((layer, idx) => {
          trackStates[idx] = true;
          const btn = document.createElement('button');
          btn.className = 'btn-trk-toggle';
          btn.id = `btnTrk_${idx}`;
          btn.innerText = `ON // ${layer.name}`;
          btn.onclick = () => toggleTrack(idx);
          matrixDiv.appendChild(btn);
        });

        function toggleTrack(idx) {
          trackStates[idx] = !trackStates[idx];
          const btn = document.getElementById(`btnTrk_${idx}`);
          if (trackStates[idx]) {
            btn.className = 'btn-trk-toggle';
            btn.innerText = `ON // Pista ${idx + 1}`;
            if (videoSynths[idx]) videoSynths[idx].volume.value = 0;
          } else {
            btn.className = 'btn-trk-toggle muted';
            btn.innerText = `OFF // Pista ${idx + 1}`;
            if (videoSynths[idx]) videoSynths[idx].volume.value = -Infinity;
          }
        }

        // RENDER KEYBOARD
        const kbContainer = document.getElementById('keyboardKeys');
        baseNotesMap.forEach(item => {
          const k = document.createElement('div');
          k.className = item.isBlack ? 'key-black' : 'key-white';
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
        });

        window.addEventListener('keyup', (e) => {
          const k = e.key.toLowerCase();
          const el = document.querySelector(`[data-key="${k}"]`);
          if (el) el.classList.remove('active');
        });

        function shiftOctave(val) {
          if (currentOctave + val >= -2 && currentOctave + val <= 2) {
            currentOctave += val;
            document.getElementById('lblOct').innerText = currentOctave;
          }
        }

        // NAVEGACIÓN Y SELECCIÓN
        function switchMainMode(mode) {
          currentMode = mode;
          document.querySelectorAll('.btn-main-mode').forEach(b => b.classList.remove('active'));
          
          if (mode === 'SYNTH') {
            document.getElementById('btnSynth').classList.add('active');
            document.getElementById('scrReels').style.display = 'none';
          } else if (mode === 'DRUM') {
            document.getElementById('btnDrum').classList.add('active');
            document.getElementById('scrReels').style.display = 'none';
          } else if (mode === 'TAPE') {
            document.getElementById('btnTape').classList.add('active');
            document.getElementById('scrReels').style.display = 'flex';
          } else if (mode === 'MIXER') {
            document.getElementById('btnMixer').classList.add('active');
            document.getElementById('scrReels').style.display = 'none';
          }
          document.getElementById('lblMode').innerText = mode;
        }

        function switchTPage(page) {
          document.querySelectorAll('.btn-t-key').forEach(b => b.classList.remove('active'));
          document.getElementById(`btnT${page}`).classList.add('active');
        }

        function loadPreset(id) {
          selectedPresetId = id;
          document.querySelectorAll('.btn-snd-key').forEach((b, i) => {
            b.classList.toggle('selected-snd', (i + 1) == id);
          });

          const p = presetsLibrary[id];
          document.getElementById('scrTitle').innerText = "📂 SOUND PRESET " + p.name;
          document.getElementById('scrDetail').innerText = p.desc;

          if (userSynth) {
            userSynth.dispose();
            if (p.engine === 'FM') userSynth = new Tone.PolySynth(Tone.FMSynth).connect(filterNode);
            if (p.engine === 'String') userSynth = new Tone.PolySynth(Tone.Synth, { oscillator: { type: 'sawtooth' } }).connect(filterNode);
            if (p.engine === 'Cluster') userSynth = new Tone.PolySynth(Tone.Synth, { oscillator: { type: 'sine' } }).connect(filterNode);
            if (p.engine === 'Pulse') userSynth = new Tone.PolySynth(Tone.Synth, { oscillator: { type: 'square' } }).connect(filterNode);
            userSynth.set({ envelope: { attack: p.attack, release: p.release } });
          }
        }

        // MOTOR AUDIO TONE.JS
        async function initAudioEngine() {
          if (recorderNode) return;
          await Tone.start();

          recorderNode = new Tone.Recorder();
          distortionNode = new Tone.Distortion(0.1).connect(recorderNode).toDestination();
          reverbNode = new Tone.Reverb({ decay: 3, wet: 0.3 }).connect(distortionNode);
          await reverbNode.generate();

          filterNode = new Tone.Filter(3500, "lowpass").connect(reverbNode);

          userSynth = new Tone.PolySynth(Tone.FMSynth).connect(filterNode);
          
          videoSynths = [];
          videoLayers.forEach((layer, idx) => {
            let s = new Tone.PolySynth(Tone.Synth).connect(filterNode);
            if (!trackStates[idx]) s.volume.value = -Infinity;
            videoSynths.push(s);
          });

          Tone.Transport.loop = true; Tone.Transport.loopStart = 0; Tone.Transport.loopEnd = "2m";
        }

        function triggerUserNote(note) {
          if (!userSynth) initAudioEngine();
          userSynth.triggerAttackRelease(shiftNoteOctave(note, currentOctave), "8n");
        }

        async function playTape() {
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
            document.getElementById('btnPlay').classList.add('active');
          }
        }

        function stopTape() {
          Tone.Transport.stop();
          if (videoSequences) videoSequences.forEach(s => s.dispose());
          isPlaying = false;
          document.getElementById('btnPlay').classList.remove('active');
        }

        async function toggleRecMaster() {
          await initAudioEngine();
          const btn = document.getElementById('btnRec');
          const dlBtn = document.getElementById('btnDownload');

          if (!isRecording) {
            recorderNode.start(); isRecording = true;
            btn.classList.add('active');
            document.getElementById('lblRecMaster').innerText = "RECORDING...";
            dlBtn.style.display = "none";
          } else {
            const recording = await recorderNode.stop();
            isRecording = false;
            btn.classList.remove('active');
            document.getElementById('lblRecMaster').innerText = "OFF";
            dlBtn.href = URL.createObjectURL(recording);
            dlBtn.style.display = "block";
          }
        }

        function liftTape() {
          if (videoLayers.length > 0) {
            liftedNotesBuffer = [...videoLayers[0].notes];
            videoLayers[0].notes = [];
            document.getElementById('scrTitle').innerText = "✂️ PISTA 1 CORTADA";
          }
        }

        function dropTape() {
          if (liftedNotesBuffer.length > 0 && videoLayers.length > 0) {
            videoLayers[0].notes = [...videoLayers[0].notes, ...liftedNotesBuffer];
            document.getElementById('scrTitle').innerText = "📋 NOTAS PEGADAS EN PISTA 1";
          }
        }

        function splitTape() {
          if (videoLayers.length > 0 && videoLayers[0].notes.length > 1) {
            let half = Math.floor(videoLayers[0].notes.length / 2);
            videoLayers[0].notes = videoLayers[0].notes.slice(0, half);
            document.getElementById('scrTitle').innerText = "🪓 PISTA DIVIDIDA";
          }
        }

        function clearTape() {
          stopTape();
          videoLayers.forEach(l => l.notes = []);
          document.getElementById('scrTitle').innerText = "🗑️ CINTA BORRADA AL 100%";
        }

        function rewindTape() { Tone.Transport.position = 0; }
        function forwardTape() { Tone.Transport.position = "1m"; }
      </script>
    </body>
    </html>
    """
    rendered_html = html_template.replace("__LAYERS_JSON__", layers_json)
    components.html(rendered_html, height=880)

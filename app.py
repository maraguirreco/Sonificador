import streamlit as st
import cv2
import numpy as np
import tempfile
import json
import base64
import streamlit.components.v1 as components

st.set_page_config(page_title="OP-1 Workstation + Sound Packs", page_icon="🎹", layout="wide")

st.title("🎹 Teenage Engineering OP-1 // Workstation & Sound Pack Engine")
st.write("Explora paquetes de sonido preinstalados o sube tus propios Sound Packs (.aif / .wav) de Teenage Engineering.")

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

# --- ENTRADAS (VIDEO / VOZ / SOUND PACKS) ---
col_inputs, col_synth = st.columns([1, 2.2])

voice_b64 = ""
custom_pack_b64 = ""

with col_inputs:
    st.subheader("📥 Fuentes de Sonido y Video")
    tab_vid, col_mic, col_packs = st.tabs(["🍃 1. Analizar Video", "🎙️ 2. Muestra de Voz", "📦 3. Cargar Sound Pack"])
    
    with tab_vid:
        video_file = st.file_uploader("Carga tu video (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
        if video_file:
            st.video(video_file)
            if st.button("🔍 Escanear Video e Inyectar a Cinta"):
                with st.spinner("Escaneando capas de movimiento con OpenCV..."):
                    tfile = tempfile.NamedTemporaryFile(delete=False)
                    tfile.write(video_file.read())
                    layers, error = process_dynamic_motion_layers(tfile.name)
                    if error:
                        st.error(error)
                    else:
                        st.session_state['dynamic_layers'] = layers
                        st.success(f"¡Cargadas {len(layers)} capas de movimiento!")

    with col_mic:
        recorded_audio = st.audio_input("Graba tu voz para el Sampler:")
        if recorded_audio:
            st.audio(recorded_audio)
            audio_bytes = recorded_audio.read()
            voice_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            st.success("✨ Voz lista. Selecciónala presionando el botón '5: VOICE'.")

    with col_packs:
        st.write("Sube un archivo de muestra de sonido u OP-1 Sound Pack (.aif, .wav, .mp3):")
        soundpack_file = st.file_uploader("Sube un Sound Pack (.aif, .wav, .mp3)", type=["aif", "aiff", "wav", "mp3"])
        if soundpack_file:
            pack_bytes = soundpack_file.read()
            custom_pack_b64 = base64.b64encode(pack_bytes).decode('utf-8')
            st.success("🎉 Sound Pack cargado exitosamente. Se ha añadido al navegador OLED como preset '09. CUSTOM SOUND PACK'.")

with col_synth:
    st.subheader("🎛️ OP-1 Workstation & Sound Pack Engine")
    
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

        .op1-chassis {
          background: #e3e4e8; border: 2px solid #b2b5bc; border-radius: 18px;
          padding: 16px; box-shadow: inset 0 2px 4px rgba(255,255,255,0.9), 0 10px 30px rgba(0,0,0,0.6); user-select: none;
        }

        .op1-top-row {
          display: grid; grid-template-columns: 60px 50px 1fr 240px 60px;
          gap: 10px; align-items: center; margin-bottom: 10px;
        }

        .speaker-grid {
          width: 48px; height: 48px; background: #c5c7ce; border-radius: 8px;
          display: grid; grid-template-columns: repeat(5, 1fr); gap: 3px; padding: 5px;
        }
        .spk-dot { background: #333; border-radius: 50%; width: 5px; height: 5px; }

        .vol-knob {
          width: 36px; height: 36px; background: #ffffff; border: 2px solid #aaa;
          border-radius: 50%; margin: 0 auto; box-shadow: 0 3px 6px rgba(0,0,0,0.2); position: relative; cursor: pointer;
        }
        .vol-indicator { width: 3px; height: 10px; background: #333; position: absolute; top: 4px; left: 15px; border-radius: 2px; }

        /* OLED SCREEN WITH TUTORIAL OVERLAY */
        .op1-screen {
          background: #090b0e; border: 3px solid #282a30; border-radius: 8px;
          padding: 10px; color: #00ffcc; min-height: 110px; position: relative;
        }
        .scr-header { display: flex; justify-content: space-between; font-size: 9px; color: #ff0055; margin-bottom: 4px; }
        .scr-body { font-size: 11px; color: #00ffcc; margin-top: 4px; }
        
        .tutorial-box {
          background: #1c2210; border: 1px dashed #a6e22e; color: #a6e22e;
          padding: 6px; border-radius: 4px; font-size: 9px; margin-top: 4px;
        }

        .encoders-container { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; text-align: center; }
        .knob-cap {
          width: 38px; height: 38px; border-radius: 50%; margin: 0 auto 4px auto;
          border: 2px solid #aaa; box-shadow: 0 4px 8px rgba(0,0,0,0.25); cursor: pointer; position: relative;
        }
        .knob-cap.blue { background: #0088ff; }
        .knob-cap.green { background: #00e676; }
        .knob-cap.white { background: #ffffff; }
        .knob-cap.orange { background: #ff5252; }

        .side-utils { display: flex; flex-direction: column; gap: 4px; }
        .btn-util { background: #fff; border: 1px solid #ccc; border-bottom: 3px solid #999; border-radius: 6px; padding: 5px; font-size: 8px; font-weight: bold; cursor: pointer; text-align: center; }
        .btn-help-mode { background: #a6e22e !important; color: #000 !important; border-color: #72a014 !important; }

        .mid-controls { display: grid; grid-template-columns: 180px 1fr 180px; gap: 10px; margin-bottom: 10px; }
        .main-modes-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }
        .btn-main-mode {
          background: #ffffff; border: 1px solid #ccc; border-bottom: 3px solid #a0a3aa;
          padding: 8px 2px; font-size: 9px; font-weight: bold; border-radius: 6px; cursor: pointer; text-align: center; color: #333;
        }
        .btn-main-mode.active { background: #ff0055 !important; color: white !important; border-color: #c40041 !important; }

        .t-keys-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; }
        .btn-t-key {
          background: #ffffff; border: 1px solid #ccc; border-bottom: 3px solid #a0a3aa;
          padding: 8px 2px; font-size: 9px; font-weight: bold; border-radius: 6px; cursor: pointer; text-align: center; color: #333;
        }
        .btn-t-key.active { background: #00ffcc !important; color: #000 !important; border-color: #00c49f !important; }

        .sound-keys-row { display: grid; grid-template-columns: repeat(8, 1fr); gap: 4px; margin-bottom: 10px; }
        .btn-snd-key {
          background: #ffffff; border: 1px solid #ccc; border-bottom: 3px solid #a0a3aa;
          padding: 8px 0; font-size: 8px; font-weight: bold; border-radius: 6px; cursor: pointer; text-align: center; color: #222;
        }
        .btn-snd-key.selected-snd { background: #0088ff !important; color: white !important; border-color: #005fcc !important; }

        .bottom-section { display: grid; grid-template-columns: 220px 1fr; gap: 12px; }
        .tape-transport-box { display: flex; flex-direction: column; gap: 6px; }
        .transport-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; }
        .btn-trans {
          background: #ffffff; border: 1px solid #ccc; border-bottom: 3px solid #a0a3aa;
          padding: 8px 2px; font-size: 9px; font-weight: bold; border-radius: 6px; cursor: pointer; text-align: center;
        }
        .btn-rec.active { background: #ff0055 !important; color: white !important; }
        .btn-play.active { background: #00e676 !important; color: black !important; }

        .keyboard-wrapper { background: #111317; border-radius: 10px; padding: 10px 8px; border: 2px solid #282a30; }
        .keyboard-top-bar { display: flex; justify-content: space-between; color: #00ffcc; font-size: 9px; margin-bottom: 6px; }
        .btn-oct-shift { background: #333; color: #fff; border: 1px solid #555; padding: 2px 8px; border-radius: 4px; cursor: pointer; }

        .keys-layout { display: flex; justify-content: center; position: relative; }
        .key-white {
          width: 25px; height: 80px; background: #ffffff; border: 1px solid #bbb;
          border-bottom: 4px solid #999; border-radius: 0 0 5px 5px; margin: 0 1px;
          cursor: pointer; display: flex; align-items: flex-end; justify-content: center;
          font-size: 8px; color: #555; font-weight: bold; padding-bottom: 4px;
        }
        .key-black {
          width: 16px; height: 48px; background: #222222; border: 1px solid #000;
          border-bottom: 3px solid #444; color: #fff; margin: 0 -8px; z-index: 2;
          border-radius: 0 0 3px 3px; cursor: pointer; display: flex; align-items: flex-end; justify-content: center;
          font-size: 7px; padding-bottom: 3px;
        }
        .key-white.active, .key-black.active { background: #ff0055 !important; color: white !important; }

        .track-matrix-box { display: grid; grid-template-columns: repeat(auto-fit, minmax(75px, 1fr)); gap: 4px; margin-bottom: 8px; }
        .btn-trk-toggle { background: #00e676; color: #000; border: none; border-bottom: 3px solid #00a152; padding: 5px; font-size: 8px; font-weight: bold; border-radius: 4px; cursor: pointer; }
        .btn-trk-toggle.muted { background: #444b54; color: #888; border-bottom-color: #222; }

        .btn-dl-link { background: #0088ff; color: white; border-radius: 6px; padding: 8px; text-decoration: none; font-size: 9px; font-weight: bold; text-align: center; display: block; margin-top: 4px; }
      </style>
    </head>
    <body>

      <div class="op1-chassis">
        
        <div class="op1-top-row">
          <div class="speaker-grid">
            <div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div>
            <div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div>
            <div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div><div class="spk-dot"></div>
          </div>

          <div style="text-align:center;">
            <div class="vol-knob" onclick="triggerHelp('VOLUME KNOB', 'Ajusta el volumen general del OP-1.', 'Operativo')"><div class="vol-indicator"></div></div>
            <span style="font-size:7px; font-weight:bold; color:#666;">VOL</span>
          </div>

          <!-- PANTALLA OLED -->
          <div class="op1-screen">
            <div class="scr-header">
              <span>MODE: <b id="lblMode" style="color:#00ffcc;">SYNTH</b></span>
              <span>OCTAVE: <b id="lblOct">0</b></span>
              <span>HELP TUTORIAL: <b id="lblHelpStatus" style="color:#a6e22e;">OFF</b></span>
            </div>
            <div class="scr-body">
              <div id="scrTitle" style="font-size:10px; color:#ff0055; margin-bottom:2px;">📂 SOUND PACK 1: DX BASS</div>
              <div id="scrDetail" style="font-size:8px; color:#aaa;">FM ENGINE // ATTACK: 0.01s // TEMPO: 100 BPM</div>
              
              <div id="tutorialBox" class="tutorial-box" style="display:none;">
                <b id="tutTitle">💡 MODO HELP ACTIVADO</b><br>
                <span id="tutDesc">Haz clic en cualquier botón para examinar su función según el manual del OP-1.</span><br>
                <span id="tutStatus" style="color:#fff; font-weight:bold;">ESTADO: OPERATIVO</span>
              </div>
            </div>
          </div>

          <!-- 4 ENCODERS -->
          <div class="encoders-container">
            <div onclick="triggerHelp('🔵 ENCODER AZUL (T1)', 'Controla el Motor Sintetizador o la selección de Sound Pack.', 'Operativo')">
              <div class="knob-cap blue"></div>
              <span style="font-size:7px; font-weight:bold; color:#0088ff;">🔵 T1 ENGINE</span>
            </div>
            <div onclick="triggerHelp('🟢 ENCODER VERDE (T2)', 'Ajusta el tiempo de Ataque (Attack) en la envolvente ADSR.', 'Operativo')">
              <div class="knob-cap green"></div>
              <span style="font-size:7px; font-weight:bold; color:#00e676;">🟢 T2 ATTACK</span>
            </div>
            <div onclick="triggerHelp('⚪ ENCODER BLANCO (T3)', 'Modifica la Liberación (Release) o parámetro de efecto.', 'Operativo')">
              <div class="knob-cap white"></div>
              <span style="font-size:7px; font-weight:bold; color:#333;">⚪ T3 RELEASE</span>
            </div>
            <div onclick="triggerHelp('🟠 ENCODER NARANJA (T4)', 'Ajusta el Tempo Global (BPM) o nivel Master Drive.', 'Operativo')">
              <div class="knob-cap orange"></div>
              <span style="font-size:7px; font-weight:bold; color:#ff5252;">🟠 T4 TEMPO</span>
            </div>
          </div>

          <div class="side-utils">
            <button id="btnHelpToggle" class="btn-util" onclick="toggleHelpMode()">💡 HELP</button>
            <button class="btn-util" onclick="triggerHelp('🎙️ MIC BUTTON', 'Selecciona entrada de micrófono para muestreo.', 'Operativo')">🎙️ MIC</button>
            <button class="btn-util" onclick="triggerHelp('📇 COM BUTTON', 'Modo Disco USB o Controlador MIDI.', 'Operativo')">📇 COM</button>
          </div>
        </div>

        <!-- MAIN MODES Y T1-T4 -->
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
            TEENAGE ENGINEERING<br>SOUND PACK ENGINE
          </div>
        </div>

        <!-- PRESETS Y SOUND PACKS (1 - 8) -->
        <div style="font-size:8px; font-weight:bold; color:#555; margin-bottom:2px;">SELECCIÓN DE SOUND PACKS & PRESETS (1 - 8):</div>
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

        <!-- PISTAS DE VIDEO -->
        <div style="font-size:8px; font-weight:bold; color:#555; margin-bottom:4px;">PISTAS DEL VIDEO DETECTADAS (ON / OFF):</div>
        <div id="trackMatrix" class="track-matrix-box"></div>

        <!-- TRANSPORTE Y TECLADO -->
        <div class="bottom-section">
          <div class="tape-transport-box">
            <div style="font-size:8px; font-weight:bold; color:#555;">EDICIÓN DE CINTA:</div>
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

          <div class="keyboard-wrapper">
            <div class="keyboard-top-bar">
              <button class="btn-oct-shift" onclick="shiftOctave(-1)">◀ OCT -</button>
              <span>KEYBOARD (A, S, D, F, G, H, J, K...)</span>
              <button class="btn-oct-shift" onclick="shiftOctave(1)">OCT + ▶</button>
            </div>
            <div class="keys-layout" id="keyboardKeys"></div>
          </div>
        </div>

      </div>

      <script>
        const videoLayers = __LAYERS_JSON__;
        const voiceAudioB64 = "__VOICE_B64__";
        const customPackB64 = "__CUSTOM_PACK_B64__";

        let currentMode = 'SYNTH';
        let isHelpMode = false;
        let isPlaying = false, isRecording = false, currentOctave = 0;
        let videoSynths = [], videoSequences = [], trackStates = {};
        let userSynth, voiceSampler, customPackSampler;
        let reverbNode, filterNode, distortionNode, recorderNode;
        let liftedNotesBuffer = [];

        // BIBLIOTECA DE SOUND PACKS TEENAGE ENGINEERING
        const presetsLibrary = {
          1: { name: "1: DX BASS", engine: "FM", desc: "SOUND PACK: SYNTH / DX7 BASS", attack: 0.01, release: 0.4 },
          2: { name: "2: CELLO", engine: "String", desc: "SOUND PACK: VINTAGE KEYS / ACOUSTIC CELLO", attack: 0.3, release: 1.5 },
          3: { name: "3: PAD", engine: "Cluster", desc: "SOUND PACK: AMBIENT / ETHEREAL CLUSTER PAD", attack: 0.5, release: 2.0 },
          4: { name: "4: 8-BIT", engine: "Pulse", desc: "SOUND PACK: CHIPTUNE / RETRO SQUARE WAVE", attack: 0.01, release: 0.2 },
          5: { name: "5: VOICE", engine: "Sampler", desc: "SOUND PACK: VOX / MIC SAMPLER CROMÁTICO", attack: 0.05, release: 0.8 },
          6: { name: "6: 808 DRUM", engine: "Drum", desc: "SOUND PACK: DRUMS / TR-808 ELECTRONIC KIT", attack: 0.01, release: 0.2 },
          7: { name: "7: ACOUSTIC", engine: "Drum", desc: "SOUND PACK: DRUMS / ACOUSTIC STUDIO KIT", attack: 0.01, release: 0.3 },
          8: { name: "8: RETRO", engine: "Drum", desc: "SOUND PACK: DRUMS / SYNTHWAVE PERCUSSION", attack: 0.01, release: 0.4 },
          9: { name: "9: CUSTOM PACK", engine: "CustomPack", desc: "SOUND PACK: USER UPLOADED (.AIF / .WAV)", attack: 0.01, release: 0.5 }
        };

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

        function toggleHelpMode() {
          isHelpMode = !isHelpMode;
          const btn = document.getElementById('btnHelpToggle');
          const box = document.getElementById('tutorialBox');
          const lbl = document.getElementById('lblHelpStatus');

          if (isHelpMode) {
            btn.classList.add('btn-help-mode');
            lbl.innerText = "ON";
            box.style.display = "block";
            triggerHelp("MODO HELP ACTIVADO", "Haz clic en cualquier botón para examinar su función según el manual del OP-1.", "LISTO");
          } else {
            btn.classList.remove('btn-help-mode');
            lbl.innerText = "OFF";
            box.style.display = "none";
          }
        }

        function triggerHelp(title, desc, status) {
          if (isHelpMode) {
            document.getElementById('tutTitle').innerText = "💡 " + title;
            document.getElementById('tutDesc').innerText = desc;
            document.getElementById('tutStatus').innerText = "ESTADO TÉCNICO: " + status;
          }
        }

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
            triggerHelp(`PISTA DE VIDEO ${idx + 1}`, `Activa el canal de movimiento ${idx + 1}.`, "ENCENDIDO");
          } else {
            btn.className = 'btn-trk-toggle muted';
            btn.innerText = `OFF // Pista ${idx + 1}`;
            if (videoSynths[idx]) videoSynths[idx].volume.value = -Infinity;
            triggerHelp(`PISTA DE VIDEO ${idx + 1}`, `Silencia la pista ${idx + 1}.`, "SILENCIADO");
          }
        }

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
            triggerHelp('OCTAVE SHIFT', `Transpone el teclado principal ${val > 0 ? '+1 octava' : '-1 octava'}.`, `OCTAVA: ${currentOctave}`);
          }
        }

        async function initAudioEngine() {
          if (recorderNode) return;
          await Tone.start();

          recorderNode = new Tone.Recorder();
          distortionNode = new Tone.Distortion(0.05).connect(recorderNode).toDestination();
          reverbNode = new Tone.Reverb({ decay: 2.5, wet: 0.25 }).connect(distortionNode);
          await reverbNode.generate();

          filterNode = new Tone.Filter(3500, "lowpass").connect(reverbNode);

          userSynth = new Tone.PolySynth(Tone.FMSynth).connect(filterNode);

          // SAMPLER DE VOZ
          if (voiceAudioB64 !== "") {
            try {
              voiceSampler = new Tone.Sampler({
                urls: { C4: "data:audio/wav;base64," + voiceAudioB64 }
              }).connect(filterNode);
            } catch(e) { console.log(e); }
          }

          // SAMPLER DE SOUND PACK PERSONALIZADO (.aif / .wav)
          if (customPackB64 !== "") {
            try {
              customPackSampler = new Tone.Sampler({
                urls: { C4: "data:audio/wav;base64," + customPackB64 }
              }).connect(filterNode);
            } catch(e) { console.log(e); }
          }
          
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
          let targetNote = shiftNoteOctave(note, currentOctave);

          if (selectedPresetId === 5 && voiceSampler) {
            voiceSampler.triggerAttackRelease(targetNote, "8n");
          } else if (selectedPresetId === 9 && customPackSampler) {
            customPackSampler.triggerAttackRelease(targetNote, "8n");
          } else if (userSynth) {
            userSynth.triggerAttackRelease(targetNote, "8n");
          }
          triggerHelp('TECLA MUSICAL ' + targetNote, 'Dispara la nota sobre el Sound Pack activo.', 'NOTA ' + targetNote);
        }

        function switchMainMode(mode) {
          currentMode = mode;
          document.querySelectorAll('.btn-main-mode').forEach(b => b.classList.remove('active'));
          
          if (mode === 'SYNTH') document.getElementById('btnSynth').classList.add('active');
          if (mode === 'DRUM') document.getElementById('btnDrum').classList.add('active');
          if (mode === 'TAPE') document.getElementById('btnTape').classList.add('active');
          if (mode === 'MIXER') document.getElementById('btnMixer').classList.add('active');
          
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
          document.getElementById('scrTitle').innerText = "📂 " + p.desc;
          document.getElementById('scrDetail').innerText = p.name + " // DISPONIBLE EN MEMORIA";

          if (userSynth && id !== 5 && id !== 9) {
            userSynth.dispose();
            if (p.engine === 'FM') userSynth = new Tone.PolySynth(Tone.FMSynth).connect(filterNode);
            if (p.engine === 'String') userSynth = new Tone.PolySynth(Tone.Synth, { oscillator: { type: 'sawtooth' } }).connect(filterNode);
            if (p.engine === 'Cluster') userSynth = new Tone.PolySynth(Tone.Synth, { oscillator: { type: 'sine' } }).connect(filterNode);
            if (p.engine === 'Pulse') userSynth = new Tone.PolySynth(Tone.Synth, { oscillator: { type: 'square' } }).connect(filterNode);
            userSynth.set({ envelope: { attack: p.attack, release: p.release } });
          }
          triggerHelp(`SOUND PACK ${id}: ${p.name}`, `Carga el paquete de sonido ${p.name} en el OP-1.`, 'PACK CARGADO');
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
            triggerHelp('PLAY TRANSPORT', 'Inicia la cinta y reproduce las capas.', 'CINTA GIRANDO');
          }
        }

        function stopTape() {
          Tone.Transport.stop();
          if (videoSequences) videoSequences.forEach(s => s.dispose());
          isPlaying = false;
          document.getElementById('btnPlay').classList.remove('active');
          triggerHelp('STOP TRANSPORT', 'Detiene la cinta.', 'CINTA DETENIDA');
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
            triggerHelp('● REC MASTER', 'Inicia la grabación hacia memoria.', 'GRABANDO MASTER');
          } else {
            const recording = await recorderNode.stop();
            isRecording = false;
            btn.classList.remove('active');
            document.getElementById('lblRecMaster').innerText = "OFF";
            dlBtn.href = URL.createObjectURL(recording);
            dlBtn.style.display = "block";
            triggerHelp('● REC MASTER finalizado', 'Genera enlace de descarga WAV.', 'WAV LISTO');
          }
        }

        function liftTape() {
          if (videoLayers.length > 0) {
            liftedNotesBuffer = [...videoLayers[0].notes];
            videoLayers[0].notes = [];
            triggerHelp('✂️ LIFT', 'Corta el contenido de la pista.', 'CORTADO');
          }
        }

        function dropTape() {
          if (liftedNotesBuffer.length > 0 && videoLayers.length > 0) {
            videoLayers[0].notes = [...videoLayers[0].notes, ...liftedNotesBuffer];
            triggerHelp('📋 DROP', 'Pega las notas guardadas.', 'PEGADO');
          }
        }

        function splitTape() {
          if (videoLayers.length > 0 && videoLayers[0].notes.length > 1) {
            let half = Math.floor(videoLayers[0].notes.length / 2);
            videoLayers[0].notes = videoLayers[0].notes.slice(0, half);
            triggerHelp('🪓 SPLIT', 'Divide la toma activa.', 'DIVIDIDO');
          }
        }

        function clearTape() {
          stopTape();
          videoLayers.forEach(l => l.notes = []);
          triggerHelp('🗑️ CLEAR TAPE', 'Borra el contenido de la cinta.', 'BORRADO');
        }

        function rewindTape() { Tone.Transport.position = 0; triggerHelp('⏮ REWIND', 'Rebobina al inicio.', 'REBOBINADO'); }
        function forwardTape() { Tone.Transport.position = "1m"; triggerHelp('⏭ FAST FORWARD', 'Adelanta un compás.', 'ADELANTADO'); }
      </script>
    </body>
    </html>
    """
    
    rendered_html = html_template.replace("__LAYERS_JSON__", layers_json).replace("__VOICE_B64__", voice_b64).replace("__CUSTOM_PACK_B64__", custom_pack_b64)
    iframe_key = f"op1_widget_{len(st.session_state['dynamic_layers'])}_{hash(voice_b64)}_{hash(custom_pack_b64)}"
    components.html(rendered_html, height=880, key=iframe_key)

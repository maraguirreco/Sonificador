import streamlit as st
import cv2
import numpy as np
import tempfile
import json
import io
import librosa
from collections import Counter
import streamlit.components.v1 as components

st.set_page_config(page_title="Music AI & Video Studio", page_icon="🎵", layout="wide")

# --- MENÚ LATERAL DE NAVEGACIÓN ---
st.sidebar.title("🎛️ Studio Navigation")
modulo = st.sidebar.radio(
    "Selecciona el módulo:",
    ["🎙️ Asistente de Armonía por Voz", "🍃 Sonificador de Video OP-1"]
)

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# ==========================================
# MÓDULO 1: ASISTENTE DE ARMONÍA POR VOZ
# ==========================================
if modulo == "🎙️ Asistente de Armonía por Voz":
    st.title("🎙️ Asistente de Armonía por Voz")
    st.write("Analizamos tu melodía y tu registro vocal para sugerirte acordes cómodos para tu voz.")

    def hz_to_note_info(frequency):
        if frequency <= 0 or np.isnan(frequency):
            return None, None
        midi_number = int(round(69 + 12 * np.log2(frequency / 440.0)))
        note_index = midi_number % 12
        return NOTE_NAMES[note_index], midi_number

    def get_vocal_range(avg_hz):
        if avg_hz < 165:
            return "Grave (Bajo / Contralto)", "🕯️ Tono Cálido / Profundo"
        elif 165 <= avg_hz <= 260:
            return "Medio (Tenor / Mezzosoprano)", "✨ Tono Equilibrado / Natural"
        else:
            return "Agudo (Soprano / Tenor Alto)", "🚀 Tono Brillante / Agudo"

    audio_file = st.file_uploader("Sube un audio (.wav o .mp3)", type=["wav", "mp3"])
    recorded_audio = st.audio_input("O graba tu voz directamente:")
    target_audio = recorded_audio if recorded_audio else audio_file

    if target_audio:
        st.audio(target_audio)
        if st.button("🔍 Analizar Voz y Armonizar"):
            with st.spinner("Analizando tu tono y tesitura vocal..."):
                y, sr = librosa.load(target_audio, sr=None)
                f0, voiced_flag, _ = librosa.pyin(
                    y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C6'), sr=sr
                )
                clean_pitches = [f for f, v in zip(f0, voiced_flag) if v and not np.isnan(f)]

                if clean_pitches:
                    avg_hz = np.mean(clean_pitches)
                    tipo_registro, descripcion = get_vocal_range(avg_hz)
                    note_list = [hz_to_note_info(f)[0] for f in clean_pitches if hz_to_note_info(f)[0]]

                    tonic_note = Counter(note_list).most_common(1)[0][0]
                    
                    st.markdown("---")
                    st.subheader("📊 Análisis Vocal")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.metric("Registro Detectado", tipo_registro)
                        st.caption(f"Frecuencia media: {int(avg_hz)} Hz | {descripcion}")
                    with c2:
                        st.metric("Tonalidad Ideal para tu Voz", f"Tónica en {tonic_note}")

                    idx = NOTE_NAMES.index(tonic_note)
                    dom = NOTE_NAMES[(idx + 7) % 12]
                    rel_m = NOTE_NAMES[(idx + 9) % 12] + "m"
                    sub_d = NOTE_NAMES[(idx + 5) % 12]

                    st.markdown("---")
                    st.markdown("### 🎼 Progresiones Adaptadas")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.subheader("Pop Comercial")
                        st.info(f"**{tonic_note} ➔ {dom} ➔ {rel_m} ➔ {sub_d}**")
                    with col2:
                        st.subheader("Balada / Triste")
                        st.warning(f"**{rel_m} ➔ {sub_d} ➔ {tonic_note} ➔ {dom}**")
                    with col3:
                        st.subheader("Jazzy / Neo-Soul")
                        st.success(f"**{tonic_note}maj7 ➔ {sub_d}maj7 ➔ {rel_m}7 ➔ {dom}7**")

# ==========================================
# MÓDULO 2: SONIFICADOR DE VIDEO OP-1 WORKSTATION
# ==========================================
else:
    st.title("🍃 Motion Synth // TE OP-1 Full Workstation")
    st.write("Sonificación de movimiento en subcapas dinámicas + Sintetizador, Drum Kit, Cinta de 4 Pistas y Grabación WAV.")

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
        if not ret: return None, "No se pudo leer el video."
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        height, _ = prev_gray.shape
        frame_count, max_frames = 0, 150
        raw_layers_data = []
        
        while cap.isOpened() and frame_count < max_frames:
            ret, frame = cap.read()
            if not ret: break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(prev_gray, gray)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            valid_contours = [c for c in contours if cv2.contourArea(c) > 35]
            
            if valid_contours:
                valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)
                frame_notes = []
                for idx, c in enumerate(valid_contours[:5]):
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
        
        if not raw_layers_data: return [], "No se detectó suficiente movimiento."
        max_detected_layers = max(len(f) for f in raw_layers_data)
        structured_layers = []
        for layer_idx in range(max_detected_layers):
            layer_notes = [frame[layer_idx] for frame in raw_layers_data if len(frame) > layer_idx]
            clean_notes = [layer_notes[0]] if layer_notes else ['C4']
            for n in layer_notes[1:]:
                if n != clean_notes[-1]: clean_notes.append(n)
            structured_layers.append({"id": layer_idx + 1, "name": f"Pista {layer_idx + 1} (Video)", "notes": clean_notes})
        return structured_layers, None

    col_vid, col_synth = st.columns([1, 1.4])
    with col_vid:
        video_file = st.file_uploader("Sube tu video (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
        if video_file:
            st.video(video_file)
            if st.button("🔍 Escanear Video y Cargar a la Cinta"):
                with st.spinner("Procesando físicas del movimiento para el OP-1..."):
                    tfile = tempfile.NamedTemporaryFile(delete=False)
                    tfile.write(video_file.read())
                    layers, error = process_dynamic_motion_layers(tfile.name)
                    if error: st.error(error)
                    else:
                        st.session_state['dynamic_layers'] = layers
                        st.success(f"¡Cargadas {len(layers)} capas de movimiento en la cinta!")

    with col_synth:
        if st.session_state['dynamic_layers']:
            layers_json = json.dumps(st.session_state['dynamic_layers'])
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
              <script src="https://cdnjs.cloudflare.com/ajax/libs/tone/14.8.49/Tone.js"></script>
              <style>
                @import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap');
                body { font-family: 'Space Mono', monospace; background: #0e1117; color: #fff; margin: 0; padding: 4px; }
                .op1-chassis { background: #e1e3e6; border: 2px solid #b8bac0; border-radius: 16px; padding: 16px; color: #222; }
                .op1-screen { background: #0d0f12; border: 3px solid #22252a; border-radius: 8px; padding: 10px; color: #00ffcc; margin-bottom: 12px; }
                .screen-top { display: flex; justify-content: space-between; font-size: 9px; color: #ff0055; margin-bottom: 4px; }
                .screen-mid { font-size: 11px; color: #00ffcc; display: flex; justify-content: space-between; }
                .drum-pad-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 12px; }
                .btn-drum { background: #ff5252; color: white; border: none; border-bottom: 3px solid #b71c1c; padding: 8px 2px; font-family: 'Space Mono', monospace; font-size: 9px; font-weight: bold; border-radius: 6px; cursor: pointer; text-align: center; }
                .tape-matrix { display: grid; grid-template-columns: repeat(auto-fit, minmax(80px, 1fr)); gap: 6px; margin-bottom: 12px; }
                .btn-track { background: #00e676; color: #000; border: none; border-bottom: 3px solid #00a152; padding: 6px 2px; font-family: 'Space Mono', monospace; font-size: 9px; font-weight: bold; border-radius: 6px; cursor: pointer; text-align: center; }
                .btn-track.muted { background: #444b54; color: #888; border-bottom-color: #222; }
                .keyboard-box { background: #111317; padding: 8px; border-radius: 8px; margin-bottom: 12px; }
                .oct-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
                .btn-oct { background: #333; color: #fff; border: 1px solid #555; padding: 4px 10px; font-size: 10px; border-radius: 4px; cursor: pointer; }
                .keyboard-container { display: flex; justify-content: center; user-select: none; }
                .key { width: 24px; height: 80px; background: #fff; border: 1px solid #ccc; border-bottom: 4px solid #aaa; border-radius: 0 0 5px 5px; margin: 0 1px; cursor: pointer; display: flex; align-items: flex-end; justify-content: center; font-size: 8px; color: #666; font-weight: bold; padding-bottom: 4px; }
                .key.black { width: 16px; height: 48px; background: #222; border: 1px solid #000; border-bottom: 3px solid #444; color: #fff; margin: 0 -8px; z-index: 2; }
                .key.active { background: #ff0055 !important; color: #fff !important; }
                .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 12px; }
                .enc-box { background: #f0f1f3; padding: 6px; border-radius: 6px; border-top: 4px solid #888; }
                .enc-box.blue { border-top-color: #0088ff; } .enc-box.green { border-top-color: #00e676; } .enc-box.white { border-top-color: #ffffff; } .enc-box.orange { border-top-color: #ff5252; }
                label { font-size: 8px; color: #555; font-weight: bold; display: block; margin-bottom: 2px; }
                input[type=range], select { width: 100%; accent-color: #222; font-size: 9px; }
                .action-grid { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 6px; margin-bottom: 10px; }
                .btn-act { background: #fff; border: 1px solid #ccc; border-bottom: 3px solid #aaa; padding: 8px; font-family: 'Space Mono', monospace; font-size: 10px; font-weight: bold; border-radius: 6px; cursor: pointer; text-align: center; }
                .btn-rec-master { background: #ff0055; color: white; border-color: #b71c1c; }
                .btn-dl { background: #0088ff; color: white; text-decoration: none; display: flex; align-items: center; justify-content: center; }
              </style>
            </head>
            <body>
              <div class="op1-chassis">
                <div style="font-size: 10px; font-weight: bold; color: #666; margin-bottom: 6px;">TE-OP-1 WORKSTATION // FULL ENGINE & TAPE RECORDER</div>
                <div class="op1-screen">
                  <div class="screen-top">
                    <span>STATUS: <b id="lblStatus">READY</b></span>
                    <span>OCTAVE: <b id="lblOct">0</b></span>
                    <span>REC MASTER: <b id="lblRecMaster">OFF</b></span>
                  </div>
                  <div class="screen-mid">
                    <span>ENGINE: <b id="lblEngine">FM SYNTH</b></span>
                    <span>BPM: <b id="lblBpm">100</b></span>
                    <span>TRACKS: __LAYER_COUNT__</span>
                  </div>
                </div>
                <div style="font-size: 8px; font-weight: bold; color: #444; margin-bottom: 3px;">DRUM KIT / PERCUSIÓN:</div>
                <div class="drum-pad-grid">
                  <button id="btnKick" class="btn-drum">🥁 KICK (1)</button>
                  <button id="btnSnare" class="btn-drum">🪘 SNARE (2)</button>
                  <button id="btnHat" class="btn-drum">💥 HI-HAT (3)</button>
                  <button id="btnClap" class="btn-drum">👏 CLAP (4)</button>
                </div>
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
                    <label>🔵 SYNTH ENGINE</label>
                    <select id="selEngine">
                      <option value="FM">FM Synth</option>
                      <option value="AM">AM Synth</option>
                      <option value="Duo">Duo Lead</option>
                      <option value="Mono">Sub Saw</option>
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
                <div class="action-grid">
                  <button id="btnPlay" class="btn-act" style="background:#00e676; color:#000;">▶️ PLAY TAPE</button>
                  <button id="btnRecMaster" class="btn-act btn-rec-master">● REC MASTER</button>
                  <button id="btnCut" class="btn-act">✂️ CUT / CLEAR</button>
                  <a id="btnDownload" class="btn-act btn-dl" style="display:none;" download="OP1_Recording.wav">⬇️ DESCARGAR WAV</a>
                </div>
              </div>

              <script>
                const videoLayers = __LAYERS_JSON__;
                let isPlaying = false, isMasterRecording = false, currentOctave = 0;
                let videoSynths = [], videoSequences = [], trackStates = {};
                let userSynth, drumKick, drumSnare, drumHat, drumClap;
                let reverb, filter, recorder;

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
                    document.getElementById('lblStatus').innerText = "PLAYING";
                    document.getElementById('btnPlay').innerText = "⏸️ PAUSE TAPE";
                  } else {
                    Tone.Transport.stop();
                    videoSequences.forEach(s => s.dispose());
                    isPlaying = false;
                    document.getElementById('lblStatus').innerText = "STOPPED";
                    document.getElementById('btnPlay').innerText = "▶️ PLAY TAPE";
                  }
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

                document.getElementById('btnCut').onclick = () => {
                  if (videoSequences) videoSequences.forEach(s => s.dispose());
                  document.getElementById('lblStatus').innerText = "TAPE CLEARED";
                };

                document.getElementById('selEngine').onchange = (e) => {
                  let val = e.target.value;
                  document.getElementById('lblEngine').innerText = val + " SYNTH";
                  if (userSynth) {
                    userSynth.dispose();
                    if (val === 'FM') userSynth = new Tone.PolySynth(Tone.FMSynth).connect(filter);
                    if (val === 'AM') userSynth = new Tone.PolySynth(Tone.AMSynth).connect(filter);
                    if (val === 'Duo') userSynth = new Tone.PolySynth(Tone.DuoSynth).connect(filter);
                    if (val === 'Mono') userSynth = new Tone.PolySynth(Tone.Synth).connect(filter);
                  }
                };

                document.getElementById('adsrAttack').oninput = (e) => { if (userSynth) userSynth.set({ envelope: { attack: parseFloat(e.target.value) } }); };
                document.getElementById('adsrRelease').oninput = (e) => { if (userSynth) userSynth.set({ envelope: { release: parseFloat(e.target.value) } }); };
                document.getElementById('bpm').oninput = (e) => { document.getElementById('lblBpm').innerText = e.target.value; Tone.Transport.bpm.value = parseFloat(e.target.value); };
              </script>
            </body>
            </html>
            """
            rendered_html = html_template.replace("__LAYERS_JSON__", layers_json).replace("__LAYER_COUNT__", str(len(st.session_state['dynamic_layers'])))
            components.html(rendered_html, height=620)
        else:
            st.info("👈 Carga un video para incrustar sus subcapas dinámicas en el sintetizador OP-1.")

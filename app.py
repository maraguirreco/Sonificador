import streamlit as st
import cv2
import numpy as np
import tempfile
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="OP-1 Full Workstation", page_icon="🎹", layout="wide")

st.title("🍃 Motion Synth // TE OP-1 Full Workstation & Tape Recorder")
st.write("Sintetizador completo e interactivo estilo OP-1. Lee el video en las pistas 1 y 2, y graba tus propias melodías en las pistas 3 y 4.")

if 'dynamic_layers' not in st.session_state:
    st.session_state['dynamic_layers'] = []

SCALES = [
    ['C2', 'E2', 'G2', 'A2', 'B2', 'C3'],            # Capa 1: Bajo
    ['C3', 'D3', 'E3', 'G3', 'A3', 'C4'],            # Capa 2: Armonía Media
    ['C4', 'D4', 'E4', 'G4', 'A4', 'C5'],            # Capa 3: Melodía Principal
    ['C5', 'D5', 'E5', 'G5', 'A5', 'C6']             # Capa 4: Brillos
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
        valid_contours = [c for c in contours if cv2.contourArea(c) > 40]
        
        if valid_contours:
            valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)
            frame_notes = []
            for idx, c in enumerate(valid_contours[:2]): # Mapea a las primeras 2 pistas
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cy = int(M["m01"] / M["m00"])
                    norm_y = 1.0 - (cy / height)
                    scale = SCALES[idx]
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
        layer_notes = []
        for frame in raw_layers_data:
            if len(frame) > layer_idx:
                layer_notes.append(frame[layer_idx])
        
        clean_notes = [layer_notes[0]] if layer_notes else ['C3']
        for n in layer_notes[1:]:
            if n != clean_notes[-1]:
                clean_notes.append(n)
                
        structured_layers.append({
            "id": layer_idx + 1,
            "name": f"Track {layer_idx + 1} (Video)",
            "notes": clean_notes
        })
        
    return structured_layers, None

col_vid, col_synth = st.columns([1, 1.4])

with col_vid:
    video_file = st.file_uploader("Sube un video (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
    if video_file:
        st.video(video_file)
        if st.button("🔍 Escanear y Cargar a Cinta OP-1"):
            with st.spinner("Mapeando movimiento a las Pistas 1 y 2 de la cinta..."):
                tfile = tempfile.NamedTemporaryFile(delete=False)
                tfile.write(video_file.read())
                
                layers, error = process_dynamic_motion_layers(tfile.name)
                if error:
                    st.error(error)
                else:
                    st.session_state['dynamic_layers'] = layers
                    st.success(f"¡Cargado en las pistas del OP-1!")

with col_synth:
    if st.session_state['dynamic_layers']:
        st.markdown("### 🎹 OP-1 Synthesizer & 4-Track Tape Engine")
        
        layers_json = json.dumps(st.session_state['dynamic_layers'])

        # Plantilla HTML/JS pura (sin f-string para evitar conflictos de comillas/llaves)
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
          <script src="https://cdnjs.cloudflare.com/ajax/libs/tone/14.8.49/Tone.js"></script>
          <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap');
            body { font-family: 'Space Mono', monospace; background: #0e1117; color: #fff; margin: 0; padding: 5px; }
            
            .op1-chassis {
              background: #e1e3e6;
              border: 2px solid #b8bac0;
              border-radius: 16px;
              padding: 16px;
              box-shadow: inset 0 1px 3px rgba(255,255,255,0.9), 0 8px 25px rgba(0,0,0,0.5);
              color: #222;
            }

            .op1-screen {
              background: #0d0f12;
              border: 3px solid #22252a;
              border-radius: 8px;
              padding: 10px;
              color: #00ffcc;
              margin-bottom: 12px;
            }

            .track-selector {
              display: grid;
              grid-template-columns: repeat(4, 1fr);
              gap: 6px;
              margin-bottom: 12px;
            }

            .btn-track {
              background: #fff; border: 1px solid #ccc; border-bottom: 3px solid #999;
              padding: 6px; font-family: 'Space Mono', monospace; font-size: 10px; font-weight: bold;
              border-radius: 6px; cursor: pointer; text-align: center; color: #333;
            }
            .btn-track.active { background: #00ffcc; color: #000; border-color: #00cca3; }

            /* TECLADO DE SINTETIZADOR */
            .keyboard-container {
              display: flex;
              justify-content: center;
              background: #111317;
              padding: 10px;
              border-radius: 8px;
              margin-bottom: 12px;
              user-select: none;
            }

            .key {
              width: 28px; height: 90px; background: #fff; border: 1px solid #ccc;
              border-bottom: 4px solid #aaa; border-radius: 0 0 5px 5px; margin: 0 1px;
              cursor: pointer; display: flex; align-items: flex-end; justify-content: center;
              font-size: 8px; color: #666; font-weight: bold; padding-bottom: 4px;
            }
            .key.black {
              width: 18px; height: 55px; background: #222; border: 1px solid #000;
              border-bottom: 3px solid #444; color: #fff; margin: 0 -10px; z-index: 2;
            }
            .key.active { background: #ff0055 !important; color: #fff !important; }

            /* CONTROLES Y ENCODERS */
            .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 12px; }
            .enc-box { background: #f0f1f3; padding: 8px; border-radius: 6px; border-top: 4px solid #888; }
            .enc-box.blue { border-top-color: #0088ff; }
            .enc-box.green { border-top-color: #00e676; }
            .enc-box.white { border-top-color: #ffffff; }
            .enc-box.orange { border-top-color: #ff5252; }

            label { font-size: 8px; color: #555; font-weight: bold; display: block; margin-bottom: 2px; }
            input[type=range], select { width: 100%; accent-color: #222; font-size: 9px; }

            .transport-grid { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 8px; }
            .btn-action {
              background: #ffffff; border: 1px solid #ccc; border-bottom: 3px solid #aaa;
              padding: 10px; font-family: 'Space Mono', monospace; font-size: 11px; font-weight: bold;
              border-radius: 6px; cursor: pointer;
            }
            .btn-rec.active { background: #ff0055; color: white; border-color: #d30043; }
            .btn-play.active { background: #00e676; color: black; }
          </style>
        </head>
        <body>

          <div class="op1-chassis">
            <div style="font-size: 10px; font-weight: bold; color: #777; margin-bottom: 6px;">
              TE-OP-1 SYNTH // 4-TRACK TAPE WORKSTATION
            </div>

            <!-- PANTALLA OLED OP-1 -->
            <div class="op1-screen">
              <div style="display:flex; justify-content:space-between; font-size: 9px; color: #ff0055; margin-bottom:4px;">
                <span>STATUS: <b id="screenStatus">STOPPED</b></span>
                <span>SELECTED TRACK: <b id="screenTrack">TRACK 3 (USER)</b></span>
              </div>
              <div style="font-size: 11px; color: #00ffcc;">
                ENGINE: <span id="screenEngine">FM SYNTH</span> | BPM: <span id="screenBpm">100</span> | REC: <span id="screenRecStatus">OFF</span>
              </div>
            </div>

            <!-- SELECCIÓN DE PISTAS (1 Y 2 VIDEO // 3 Y 4 USUARIO) -->
            <div class="track-selector">
              <button id="trk1" class="btn-track">TRK 1 (VID)</button>
              <button id="trk2" class="btn-track">TRK 2 (VID)</button>
              <button id="trk3" class="btn-track active">TRK 3 (USER)</button>
              <button id="trk4" class="btn-track">TRK 4 (USER)</button>
            </div>

            <!-- TECLADO EN PANTALLA (2 OCTAVAS) -->
            <div class="keyboard-container" id="keyboard">
              <!-- Teclas generadas dinámicamente por JS -->
            </div>

            <!-- CONTROLES Y ENCODERS -->
            <div class="grid-4">
              <div class="enc-box blue">
                <label>🔵 SYNTH ENGINE</label>
                <select id="synthEngine">
                  <option value="FM">FM Synth</option>
                  <option value="Mono">Cluster / Saw</option>
                  <option value="Duo">Duo Lead</option>
                </select>
              </div>
              <div class="enc-box green">
                <label>🟢 CUTOFF HZ</label>
                <input type="range" id="cutoff" min="200" max="4000" value="1200">
              </div>
              <div class="enc-box white">
                <label>⚪ REVERB</label>
                <input type="range" id="reverbWet" min="0" max="0.9" step="0.05" value="0.3">
              </div>
              <div class="enc-box orange">
                <label>🟠 TEMPO BPM</label>
                <input type="range" id="bpm" min="50" max="180" value="100">
              </div>
            </div>

            <!-- BARRA DE TRANSPORTE Y GRABACIÓN -->
            <div class="transport-grid">
              <button id="playBtn" class="btn-action btn-play">▶️ PLAY TAPE</button>
              <button id="recBtn" class="btn-action btn-rec">● REC ARM</button>
              <button id="clearBtn" class="btn-action">🗑️ CLEAR TRK</button>
            </div>
          </div>

          <script>
            const videoLayers = __LAYERS_JSON__;
            
            let isPlaying = false;
            let isRecording = false;
            let activeTrack = 3;
            
            // Pistas de la cinta (1 y 2 pre-cargadas con el video, 3 y 4 libres)
            let tapeTracks = {
              1: videoLayers[0] ? videoLayers[0].notes : [],
              2: videoLayers[1] ? videoLayers[1].notes : [],
              3: [],
              4: []
            };

            let userSynths = {};
            let sequences = {};
            let reverb, filter;

            const notesMap = [
              { note: 'C4', key: 'a', isBlack: false },
              { note: 'C#4', key: 'w', isBlack: true },
              { note: 'D4', key: 's', isBlack: false },
              { note: 'D#4', key: 'e', isBlack: true },
              { note: 'E4', key: 'd', isBlack: false },
              { note: 'F4', key: 'f', isBlack: false },
              { note: 'F#4', key: 't', isBlack: true },
              { note: 'G4', key: 'g', isBlack: false },
              { note: 'G#4', key: 'y', isBlack: true },
              { note: 'A4', key: 'h', isBlack: false },
              { note: 'A#4', key: 'u', isBlack: true },
              { note: 'B4', key: 'j', isBlack: false },
              { note: 'C5', key: 'k', isBlack: false }
            ];

            // RENDERIZAR TECLADO VISUAL
            const kbContainer = document.getElementById('keyboard');
            notesMap.forEach(item => {
              const k = document.createElement('div');
              k.className = `key ${item.isBlack ? 'black' : ''}`;
              k.innerText = item.key.toUpperCase();
              k.dataset.note = item.note;
              
              k.addEventListener('mousedown', () => playLiveNote(item.note));
              kbContainer.appendChild(k);
            });

            // MAPPING DE TECLADO DE COMPUTADOR (A, S, D, F...)
            window.addEventListener('keydown', (e) => {
              if (e.repeat) return;
              const found = notesMap.find(m => m.key === e.key.toLowerCase());
              if (found) {
                playLiveNote(found.note);
                const el = document.querySelector(`[data-note="${found.note}"]`);
                if (el) el.classList.add('active');
              }
            });

            window.addEventListener('keyup', (e) => {
              const found = notesMap.find(m => m.key === e.key.toLowerCase());
              if (found) {
                const el = document.querySelector(`[data-note="${found.note}"]`);
                if (el) el.classList.remove('active');
              }
            });

            // SINTETIZADOR INTERACTIVO EN VIVO
            async function playLiveNote(note) {
              await Tone.start();
              if (!userSynths[activeTrack]) initAudioEngine();

              userSynths[activeTrack].triggerAttackRelease(note, "8n");

              // Si REC está activo, graba la nota en la pista actual
              if (isRecording) {
                tapeTracks[activeTrack].push(note);
                document.getElementById('screenStatus').innerText = `RECORDING TO TRK ${activeTrack}...`;
              }
            }

            async function initAudioEngine() {
              await Tone.start();

              reverb = new Tone.Reverb({ decay: 3, wet: 0.3 }).toDestination();
              await reverb.generate();
              filter = new Tone.Filter(1200, "lowpass").connect(reverb);

              // Crear sintetizadores para las 4 pistas
              [1, 2, 3, 4].forEach(trk => {
                userSynths[trk] = new Tone.PolySynth(Tone.Synth).connect(filter);
              });

              Tone.Transport.bpm.value = parseFloat(document.getElementById('bpm').value);
              Tone.Transport.loop = true;
              Tone.Transport.loopStart = 0;
              Tone.Transport.loopEnd = "2m"; // Bucle de 2 compases
            }

            // CAMBIO DE PISTAS (TRK 1-4)
            [1, 2, 3, 4].forEach(trk => {
              document.getElementById(`trk${trk}`).addEventListener('click', () => {
                document.querySelectorAll('.btn-track').forEach(b => b.classList.remove('active'));
                document.getElementById(`trk${trk}`).classList.add('active');
                activeTrack = trk;
                document.getElementById('screenTrack').innerText = `TRACK ${trk} ${trk <= 2 ? '(VIDEO)' : '(USER)'}`;
              });
            });

            // CONTROLES DE TRANSPORTE
            document.getElementById('playBtn').addEventListener('click', async () => {
              await initAudioEngine();
              
              if (!isPlaying) {
                // Iniciar secuencias grabadas en las 4 pistas
                [1, 2, 3, 4].forEach(trk => {
                  if (tapeTracks[trk].length > 0) {
                    sequences[trk] = new Tone.Sequence((time, note) => {
                      userSynths[trk].triggerAttackRelease(note, "8n", time);
                    }, tapeTracks[trk], "8n").start(0);
                  }
                });

                Tone.Transport.start();
                isPlaying = true;
                document.getElementById('playBtn').classList.add('active');
                document.getElementById('playBtn').innerText = "⏸️ PAUSE TAPE";
                document.getElementById('screenStatus').innerText = "PLAYING TAPE";
              } else {
                Tone.Transport.stop();
                Object.values(sequences).forEach(s => s.dispose());
                isPlaying = false;
                document.getElementById('playBtn').classList.remove('active');
                document.getElementById('playBtn').innerText = "▶️ PLAY TAPE";
                document.getElementById('screenStatus').innerText = "STOPPED";
              }
            });

            // BOTÓN REC
            document.getElementById('recBtn').addEventListener('click', () => {
              isRecording = !isRecording;
              const btn = document.getElementById('recBtn');
              if (isRecording) {
                btn.classList.add('active');
                document.getElementById('screenRecStatus').innerText = "ARMED (PLAY A NOTE)";
              } else {
                btn.classList.remove('active');
                document.getElementById('screenRecStatus').innerText = "OFF";
              }
            });

            // LIMPIAR PISTA ACTUAL
            document.getElementById('clearBtn').addEventListener('click', () => {
              tapeTracks[activeTrack] = [];
              if (sequences[activeTrack]) sequences[activeTrack].dispose();
              document.getElementById('screenStatus').innerText = `CLEARED TRK ${activeTrack}`;
            });

            // CONTROLES EN TIEMPO REAL
            document.getElementById('cutoff').addEventListener('input', (e) => {
              if (filter) filter.frequency.value = parseFloat(e.target.value);
            });
            document.getElementById('reverbWet').addEventListener('input', (e) => {
              if (reverb) reverb.wet.value = parseFloat(e.target.value);
            });
            document.getElementById('bpm').addEventListener('input', (e) => {
              document.getElementById('screenBpm').innerText = e.target.value;
              Tone.Transport.bpm.value = parseFloat(e.target.value);
            });
          </script>
        </body>
        </html>
        """
        
        # Inyección segura del JSON sin interpolación de f-strings
        rendered_html = html_template.replace("__LAYERS_JSON__", layers_json)
        components.html(rendered_html, height=540)
    else:
        st.info("👈 Carga un video para incrustar sus notas en la Cinta 1 y 2 del OP-1.")

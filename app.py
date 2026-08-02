import streamlit as st
import cv2
import numpy as np
import tempfile
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="OP-1 Dynamic Workstation", page_icon="🎹", layout="wide")

st.title("🍃 Motion Synth // Dynamic Layer OP-1 Workstation")
st.write("Escaneo ilimitado de subcapas de movimiento + Matriz Mute/Unmute individual + Sintetizador y Grabador de Cinta.")

if 'dynamic_layers' not in st.session_state:
    st.session_state['dynamic_layers'] = []

# Matriz de escalas pentatónicas por registros (de grave a agudo)
OCTAVE_SCALES = [
    ['C2', 'E2', 'G2', 'A2', 'B2', 'C3'],            # Capa 1: Sub / Bajo Profundo
    ['C3', 'D3', 'E3', 'G3', 'A3', 'C4'],            # Capa 2: Armonía Grave
    ['C4', 'D4', 'E4', 'G4', 'A4', 'C5'],            # Capa 3: Melodía / Lead
    ['C5', 'D5', 'E5', 'G5', 'A5', 'C6'],            # Capa 4: Textura Aguda
    ['C6', 'D6', 'E6', 'G6', 'A6', 'C7'],            # Capa 5: Arpegio Cristalino
    ['C7', 'D7', 'E7', 'G7', 'A7', 'C8']             # Capa 6: Brillo / Micro-movimiento
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
        
        # Detectar todos los grupos de movimiento independientes (contornos)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = [c for c in contours if cv2.contourArea(c) > 30] # Sensibilidad de movimiento
        
        if valid_contours:
            # Ordenar contornos de mayor a menor área
            valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)
            frame_notes = []
            
            # Extraer notas para CADA contorno detectado (sin límite rígido)
            for idx, c in enumerate(valid_contours[:6]): # Hasta 6 capas simultáneas
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cy = int(M["m01"] / M["m00"])
                    norm_y = 1.0 - (cy / height)
                    
                    # Asignar escala según el nivel de profundidad de la capa
                    scale = OCTAVE_SCALES[idx % len(OCTAVE_SCALES)]
                    note_idx = int(norm_y * (len(scale) - 1))
                    frame_notes.append(scale[note_idx])
                    
            raw_layers_data.append(frame_notes)

        prev_gray = gray
        frame_count += 1
        
    cap.release()
    
    if not raw_layers_data:
        return [], "No se detectó suficiente movimiento en el video."

    # Determinar el número REAL de capas encontradas en el video
    max_detected_layers = max(len(f) for f in raw_layers_data)
    
    structured_layers = []
    for layer_idx in range(max_detected_layers):
        layer_notes = []
        for frame in raw_layers_data:
            if len(frame) > layer_idx:
                layer_notes.append(frame[layer_idx])
        
        # Eliminar repeticiones consecutivas para fluidez
        clean_notes = [layer_notes[0]] if layer_notes else ['C4']
        for n in layer_notes[1:]:
            if n != clean_notes[-1]:
                clean_notes.append(n)
                
        structured_layers.append({
            "id": layer_idx + 1,
            "name": f"Capa {layer_idx + 1}",
            "notes": clean_notes
        })
        
    return structured_layers, None

col_vid, col_synth = st.columns([1, 1.4])

with col_vid:
    video_file = st.file_uploader("Sube tu video (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
    if video_file:
        st.video(video_file)
        if st.button("🔍 Escanear Capas de Movimiento Real"):
            with st.spinner("Escaneando físicas y extrayendo subcapas del video..."):
                tfile = tempfile.NamedTemporaryFile(delete=False)
                tfile.write(video_file.read())
                
                layers, error = process_dynamic_motion_layers(tfile.name)
                if error:
                    st.error(error)
                else:
                    st.session_state['dynamic_layers'] = layers
                    st.success(f"¡Éxito! Se detectaron {len(layers)} subcapas independientes en tu video.")

with col_synth:
    if st.session_state['dynamic_layers']:
        st.markdown(f"### 🎹 OP-1 Synth ({len(st.session_state['dynamic_layers'])} Capas Detectadas en el Video)")
        
        layers_json = json.dumps(st.session_state['dynamic_layers'])

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
          <script src="https://cdnjs.cloudflare.com/ajax/libs/tone/14.8.49/Tone.js"></script>
          <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap');
            body { font-family: 'Space Mono', monospace; background: #0e1117; color: #fff; margin: 0; padding: 5px; }
            
            .op1-chassis {
              background: #e1e3e6; border: 2px solid #b8bac0; border-radius: 16px;
              padding: 16px; box-shadow: inset 0 1px 3px rgba(255,255,255,0.9), 0 8px 25px rgba(0,0,0,0.5); color: #222;
            }

            .op1-screen {
              background: #0d0f12; border: 3px solid #22252a; border-radius: 8px;
              padding: 10px; color: #00ffcc; margin-bottom: 12px;
            }

            /* MATRIZ DE CAPAS EN VIVO */
            .layer-matrix {
              display: grid; grid-template-columns: repeat(auto-fit, minmax(95px, 1fr));
              gap: 6px; margin-bottom: 12px;
            }

            .btn-layer-toggle {
              background: #00e676; color: #000; border: none; border-bottom: 3px solid #00a152;
              padding: 8px 2px; font-family: 'Space Mono', monospace; font-size: 9px; font-weight: bold;
              border-radius: 6px; cursor: pointer; text-align: center; transition: all 0.1s;
            }
            .btn-layer-toggle.muted { background: #444b54; color: #888; border-bottom-color: #222; }

            /* TECLADO INTERACTIVO */
            .keyboard-container {
              display: flex; justify-content: center; background: #111317;
              padding: 8px; border-radius: 8px; margin-bottom: 12px; user-select: none;
            }

            .key {
              width: 26px; height: 85px; background: #fff; border: 1px solid #ccc;
              border-bottom: 4px solid #aaa; border-radius: 0 0 5px 5px; margin: 0 1px;
              cursor: pointer; display: flex; align-items: flex-end; justify-content: center;
              font-size: 8px; color: #666; font-weight: bold; padding-bottom: 4px;
            }
            .key.black {
              width: 17px; height: 50px; background: #222; border: 1px solid #000;
              border-bottom: 3px solid #444; color: #fff; margin: 0 -9px; z-index: 2;
            }
            .key.active { background: #ff0055 !important; color: #fff !important; }

            .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 12px; }
            .enc-box { background: #f0f1f3; padding: 8px; border-radius: 6px; border-top: 4px solid #888; }
            .enc-box.blue { border-top-color: #0088ff; }
            .enc-box.green { border-top-color: #00e676; }
            .enc-box.white { border-top-color: #ffffff; }
            .enc-box.orange { border-top-color: #ff5252; }

            label { font-size: 8px; color: #555; font-weight: bold; display: block; margin-bottom: 2px; }
            input[type=range] { width: 100%; accent-color: #222; }

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
              TE-OP-1 WORKSTATION // DYNAMIC MULTI-TRACK MATRIX
            </div>

            <!-- PANTALLA OLED OP-1 -->
            <div class="op1-screen">
              <div style="display:flex; justify-content:space-between; font-size: 9px; color: #ff0055; margin-bottom:4px;">
                <span>STATUS: <b id="screenStatus">STOPPED</b></span>
                <span>REC USER TRK: <b id="screenRecStatus">OFF</b></span>
              </div>
              <div style="font-size: 10px; color: #00ffcc;">
                TOTAL DETECTED LAYERS: __LAYER_COUNT__ | BPM: <span id="screenBpm">100</span>
              </div>
            </div>

            <!-- MATRIZ DE CONTROL MUTE/UNMUTE DYNAMIC -->
            <div style="font-size: 8px; font-weight: bold; color: #555; margin-bottom: 4px;">
              SUBCAPAS DETECTADAS EN EL VIDEO (PRENDER / APAGAR EN VIVO):
            </div>
            <div id="layerMatrix" class="layer-matrix"></div>

            <!-- TECLADO DE SINTETIZADOR INTERACTIVO -->
            <div style="font-size: 8px; font-weight: bold; color: #555; margin-bottom: 4px;">
              PISTA DE USUARIO (TOCA CON MOUSE O TECLAS A,S,D,F,G...):
            </div>
            <div class="keyboard-container" id="keyboard"></div>

            <!-- CONTROLES Y ENCODERS -->
            <div class="grid-4">
              <div class="enc-box blue">
                <label>🔵 VOLUMEN USER</label>
                <input type="range" id="volUser" min="-30" max="6" value="0">
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
              <button id="playBtn" class="btn-action btn-play">▶️ PLAY ALL TRACKS</button>
              <button id="recBtn" class="btn-action btn-rec">● REC USER TRK</button>
              <button id="clearBtn" class="btn-action">🗑️ CLEAR USER</button>
            </div>
          </div>

          <script>
            const videoLayers = __LAYERS_JSON__;
            let isPlaying = false;
            let isRecording = false;

            let layerStates = {}; // Estado ON/OFF dinámico por capa
            let videoSynths = [];
            let videoSequences = [];

            let userSynth;
            let userRecordedNotes = [];
            let userSequence;

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

            // 1. GENERACIÓN DINÁMICA DE BOTONES PARA CADA CAPA DETECTADA
            const matrixDiv = document.getElementById('layerMatrix');
            videoLayers.forEach((layer, idx) => {
              layerStates[idx] = true; // Activas por defecto
              
              const btn = document.createElement('button');
              btn.className = 'btn-layer-toggle';
              btn.id = `btnLayer_${idx}`;
              btn.innerText = `ON // ${layer.name}`;
              btn.onclick = () => toggleLayer(idx);
              matrixDiv.appendChild(btn);
            });

            function toggleLayer(idx) {
              layerStates[idx] = !layerStates[idx];
              const btn = document.getElementById(`btnLayer_${idx}`);
              
              if (layerStates[idx]) {
                btn.className = 'btn-layer-toggle';
                btn.innerText = `ON // Capa ${idx + 1}`;
                if (videoSynths[idx]) videoSynths[idx].volume.value = 0; // Prender
              } else {
                btn.className = 'btn-layer-toggle muted';
                btn.innerText = `OFF // Capa ${idx + 1}`;
                if (videoSynths[idx]) videoSynths[idx].volume.value = -Infinity; // Apagar
              }
            }

            // 2. TECLADO VISUAL
            const kbContainer = document.getElementById('keyboard');
            notesMap.forEach(item => {
              const k = document.createElement('div');
              k.className = `key ${item.isBlack ? 'black' : ''}`;
              k.innerText = item.key.toUpperCase();
              k.dataset.note = item.note;
              k.addEventListener('mousedown', () => playLiveNote(item.note));
              kbContainer.appendChild(k);
            });

            // MAPEO TECLADO FISICO
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

            // 3. REPRODUCIR Y GRABAR NOTAS DEL USUARIO
            async function playLiveNote(note) {
              await Tone.start();
              if (!userSynth) initAudioEngine();

              userSynth.triggerAttackRelease(note, "8n");

              if (isRecording) {
                userRecordedNotes.push(note);
                document.getElementById('screenStatus').innerText = `REC: ${note}`;
              }
            }

            async function initAudioEngine() {
              await Tone.start();

              reverb = new Tone.Reverb({ decay: 3, wet: 0.3 }).toDestination();
              await reverb.generate();
              filter = new Tone.Filter(1200, "lowpass").connect(reverb);

              // Synth Pista Usuario
              userSynth = new Tone.PolySynth(Tone.Synth).connect(filter);

              // Synths Dinámicos (1 por cada capa del video)
              videoSynths = [];
              videoLayers.forEach((layer, idx) => {
                let s = new Tone.PolySynth(Tone.Synth).connect(filter);
                if (!layerStates[idx]) s.volume.value = -Infinity;
                videoSynths.push(s);
              });

              Tone.Transport.bpm.value = parseFloat(document.getElementById('bpm').value);
              Tone.Transport.loop = true;
              Tone.Transport.loopStart = 0;
              Tone.Transport.loopEnd = "2m";
            }

            // CONTROLES DE REPRODUCCIÓN GLOBAL
            document.getElementById('playBtn').addEventListener('click', async () => {
              await initAudioEngine();
              
              if (!isPlaying) {
                // Iniciar secuencias de TODAS las capas de video
                videoSequences = [];
                videoLayers.forEach((layer, idx) => {
                  let rate = idx === 0 ? "2n" : (idx === 1 ? "4n" : "8n");
                  let seq = new Tone.Sequence((time, note) => {
                    videoSynths[idx].triggerAttackRelease(note, rate, time);
                  }, layer.notes, rate).start(0);
                  videoSequences.push(seq);
                });

                // Iniciar secuencia grabada por el usuario
                if (userRecordedNotes.length > 0) {
                  userSequence = new Tone.Sequence((time, note) => {
                    userSynth.triggerAttackRelease(note, "8n", time);
                  }, userRecordedNotes, "8n").start(0);
                }

                Tone.Transport.start();
                isPlaying = true;
                document.getElementById('playBtn').classList.add('active');
                document.getElementById('playBtn').innerText = "⏸️ STOP TAPE";
                document.getElementById('screenStatus').innerText = "PLAYING ALL TRACKS";
              } else {
                Tone.Transport.stop();
                videoSequences.forEach(s => s.dispose());
                if (userSequence) userSequence.dispose();
                isPlaying = false;
                document.getElementById('playBtn').classList.remove('active');
                document.getElementById('playBtn').innerText = "▶️ PLAY ALL TRACKS";
                document.getElementById('screenStatus').innerText = "STOPPED";
              }
            });

            // GRABACIÓN
            document.getElementById('recBtn').addEventListener('click', () => {
              isRecording = !isRecording;
              const btn = document.getElementById('recBtn');
              if (isRecording) {
                btn.classList.add('active');
                document.getElementById('screenRecStatus').innerText = "ARMED";
              } else {
                btn.classList.remove('active');
                document.getElementById('screenRecStatus').innerText = "OFF";
              }
            });

            document.getElementById('clearBtn').addEventListener('click', () => {
              userRecordedNotes = [];
              if (userSequence) userSequence.dispose();
              document.getElementById('screenStatus').innerText = "CLEARED USER TRACK";
            });

            // ENCODERS
            document.getElementById('volUser').addEventListener('input', (e) => {
              if (userSynth) userSynth.volume.value = parseFloat(e.target.value);
            });
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
        
        rendered_html = html_template.replace("__LAYERS_JSON__", layers_json).replace("__LAYER_COUNT__", str(len(st.session_state['dynamic_layers'])))
        components.html(rendered_html, height=550)
    else:
        st.info("👈 Carga un video para que el algoritmo escanee dinámicamente cuántas subcapas de movimiento tiene.")

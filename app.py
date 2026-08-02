import streamlit as st
import cv2
import numpy as np
import tempfile
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="Everyday Motion Sound Studio", page_icon="🌊", layout="wide")

st.title("🌊 Everyday Motion Sound Studio Pro")
st.write("Herramienta de sonificación musical limpia: convierte movimiento en melodías ampliadas de 2 octavas con control total de velocidad y mezcla.")

if 'layers_events' not in st.session_state:
    st.session_state['layers_events'] = []
if 'video_duration' not in st.session_state:
    st.session_state['video_duration'] = 0.0

def extract_organic_motion_positions(video_path):
    cap = cv2.VideoCapture(video_path)
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0 or np.isnan(fps):
        fps = 30.0
        
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration = round(total_frames / fps, 2) if total_frames > 0 else 6.0
    
    ret, prev_frame = cap.read()
    if not ret:
        return None, 0.0, "No se pudo leer el archivo de video."
    
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    height, width = prev_gray.shape
    
    frame_count = 0
    raw_events_by_layer = {}
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(prev_gray, gray)
        _, thresh = cv2.threshold(diff, 16, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = [c for c in contours if cv2.contourArea(c) > 20]
        
        if valid_contours:
            valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)
            timestamp = round(frame_count / fps, 2)
            
            # Detectar hasta 6 capas dinámicas independientes
            for idx, c in enumerate(valid_contours[:6]):
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cy = int(M["m01"] / M["m00"])
                    norm_y = round(1.0 - (cy / height), 3)
                    
                    if idx not in raw_events_by_layer:
                        raw_events_by_layer[idx] = []
                    
                    if not raw_events_by_layer[idx] or (timestamp - raw_events_by_layer[idx][-1]['time']) > 0.10:
                        raw_events_by_layer[idx].append({
                            'time': timestamp,
                            'norm_y': norm_y
                        })

        prev_gray = gray
        frame_count += 1
        
    cap.release()
    
    if not raw_events_by_layer:
        return [], 0.0, "No se detectó suficiente movimiento en el video."

    structured_layers = []
    for layer_idx, events in raw_events_by_layer.items():
        if len(events) > 0:
            structured_layers.append({
                "id": layer_idx + 1,
                "events": events
            })
        
    return structured_layers, video_duration, None

# --- UI STREAMLIT ---
col_vid, col_studio = st.columns([1, 1.4])

with col_vid:
    st.subheader("📹 1. Cargar y Analizar Video")
    video_file = st.file_uploader("Sube tu video (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
    
    if video_file:
        st.video(video_file)
        video_bytes = video_file.getvalue()

        if st.button("✨ Extraer Capas de Movimiento"):
            with st.spinner("Escaneando trayectorias y marcas de tiempo..."):
                tfile = tempfile.NamedTemporaryFile(delete=False)
                tfile.write(video_bytes)
                layers, duration, error = extract_organic_motion_positions(tfile.name)
                if error:
                    st.error(error)
                else:
                    st.session_state['layers_events'] = layers
                    st.session_state['video_duration'] = duration
                    st.success(f"¡Éxito! Detectadas {len(layers)} subcapas únicas. Duración bucle: {duration}s")

with col_studio:
    st.subheader("🎛️ 2. Consola de Producción y Estudio Limpio")
    
    if st.session_state['layers_events']:
        layers_json = json.dumps(st.session_state['layers_events'])
        duration_val = st.session_state['video_duration']

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
          <script src="https://cdnjs.cloudflare.com/ajax/libs/tone/14.8.49/Tone.js"></script>
          <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');
            * { box-sizing: border-box; }
            body { font-family: 'Space Mono', monospace; background: #0e1117; color: #fff; margin: 0; padding: 4px; }
            
            .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 14px; }

            .global-panel {
              display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
              background: #21262d; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px;
            }

            .track-card {
              background: #21262d; border-left: 4px solid #00e676; border-radius: 6px;
              padding: 10px; margin-bottom: 8px; display: grid; grid-template-columns: 90px 1.2fr 1fr 1fr 60px;
              gap: 8px; align-items: center;
            }

            .btn-mute {
              background: #00e676; color: #000; border: none; padding: 6px 4px;
              border-radius: 6px; cursor: pointer; font-size: 10px; font-weight: bold; width: 100%;
            }
            .btn-mute.muted { background: #3f444c; color: #8b949e; }

            label { font-size: 8px; color: #8b949e; font-weight: bold; display: block; margin-bottom: 2px; }
            select, input[type=range] { width: 100%; accent-color: #00e676; font-size: 10px; background: #0d1117; color: #fff; border: 1px solid #30363d; border-radius: 4px; padding: 3px; }

            .btn-action {
              background: #00e676; color: #000; border: none; padding: 12px;
              border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 12px; width: 100%; margin-top: 8px;
            }
            .btn-action.playing { background: #ff5252; color: white; }
            .btn-dl { background: #0088ff; color: white; text-decoration: none; display: flex; align-items: center; justify-content: center; }
          </style>
        </head>
        <body>

          <div class="card">
            
            <!-- MASTER CONTROLS -->
            <div class="global-panel">
              <div>
                <label>🎼 NOTA RAÍZ (ROOT KEY)</label>
                <select id="rootKeySelect" onchange="updateScaleInRealtime()">
                  <option value="C" selected>C (Do)</option>
                  <option value="D">D (Re)</option>
                  <option value="Eb">Eb (Mi bemol)</option>
                  <option value="F">F (Fa)</option>
                  <option value="G">G (Sol)</option>
                  <option value="A">A (La)</option>
                  <option value="Bb">Bb (Si bemol)</option>
                </select>
              </div>

              <div>
                <label>🎨 ESCALA ARMÓNICA (EN VIVO)</label>
                <select id="scaleTypeSelect" onchange="updateScaleInRealtime()">
                  <option value="minor" selected>Sad / Melancólica (Menor)</option>
                  <option value="major">Cálida / Alegre (Mayor)</option>
                  <option value="lydian">Espacial / Ambient (Lidia)</option>
                  <option value="pentatonic">Japonesa / Meditativa</option>
                  <option value="dorian">Funk / Groove (Dórica)</option>
                  <option value="harmonicMinor">Neoclásica / Drama</option>
                </select>
              </div>

              <div>
                <label>⚡ SPEED / VELOCIDAD: <b id="lblSpeed">1.0x</b></label>
                <input type="range" id="speedSlider" min="0.2" max="3.0" step="0.1" value="1.0" oninput="updatePlaybackSpeed(this.value)">
              </div>

              <div>
                <label>🔊 MASTER VOL: <b id="lblMasterVol">-3</b> dB</label>
                <input type="range" id="masterVol" min="-24" max="3" value="-3" oninput="updateMasterVol(this.value)">
              </div>

              <div>
                <label>🌌 REVERB ESPACIAL</label>
                <input type="range" id="reverbWet" min="0" max="0.7" step="0.05" value="0.25" oninput="updateReverb(this.value)">
              </div>

              <div>
                <label>🎚️ LIMITADOR ANTI-DISTORSIÓN</label>
                <span style="font-size:9px; color:#00e676; font-weight:bold;">ACTIVO (-2 dB)</span>
              </div>
            </div>

            <div style="font-size: 9px; font-weight: bold; color: #8b949e; margin-bottom: 6px;">ASIGNACIÓN POR SUBCAPA (DURACIÓN BUCLE: __DURATION__s):</div>
            <div id="tracksContainer"></div>

            <button id="btnPlay" class="btn-action" onclick="togglePlay()">▶️ REPRODUCIR BUCLE LIMPIO</button>
            <button id="btnRec" class="btn-action" style="background:#8957e5; color:white;" onclick="toggleRecord()">● GRABAR ARCHIVO AUDIO (WAV)</button>
            <a id="btnDownload" class="btn-action btn-dl" style="display:none;" download="Motion_Studio_Track.wav">⬇️ DESCARGAR WAV</a>

          </div>

          <script>
            const layers = __LAYERS_JSON__;
            const videoDuration = __DURATION__;

            // FÓRMULAS DE ESCALAS EXTENDIDAS A 2 OCTAVAS COMPLETAS (14 NOTAS)
            const SCALE_INTERVALS = {
              minor: [0, 2, 3, 5, 7, 8, 10, 12, 14, 15, 17, 19, 20, 22],
              major: [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19, 21, 23],
              lydian: [0, 2, 4, 6, 7, 9, 11, 12, 14, 16, 18, 19, 21, 23],
              pentatonic: [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24, 26, 28, 31],
              dorian: [0, 2, 3, 5, 7, 9, 10, 12, 14, 15, 17, 19, 21, 22],
              harmonicMinor: [0, 2, 3, 5, 7, 8, 11, 12, 14, 15, 17, 19, 20, 23]
            };

            const NOTE_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"];

            let currentRootKey = "C";
            let currentScaleType = "minor";
            let currentScaleNotes = [];

            let isPlaying = false, isRecording = false;
            let playbackSpeed = 1.0;
            let synths = [], parts = [], trackStates = {};
            let layerRoles = {}, layerOctaves = {}, layerVolumes = {};
            let reverbNode, masterGainNode, limiterNode, recorderNode;

            // Generador de escala dinámica en tiempo real
            function buildScaleNotes(root, scaleType) {
              let rootIndex = NOTE_NAMES.indexOf(root);
              if (rootIndex === -1) rootIndex = 0;
              let intervals = SCALE_INTERVALS[scaleType] || SCALE_INTERVALS['minor'];
              
              return intervals.map(semitones => {
                let totalMidi = 36 + rootIndex + semitones; // Comienza en Octava 2 (C2)
                let noteName = NOTE_NAMES[totalMidi % 12];
                let octave = Math.floor(totalMidi / 12) - 1;
                return noteName + octave;
              });
            }

            function updateScaleInRealtime() {
              currentRootKey = document.getElementById('rootKeySelect').value;
              currentScaleType = document.getElementById('scaleTypeSelect').value;
              currentScaleNotes = buildScaleNotes(currentRootKey, currentScaleType);
            }

            currentScaleNotes = buildScaleNotes(currentRootKey, currentScaleType);

            function shiftNote(noteStr, octaveOffset) {
              if (!noteStr || octaveOffset === 0) return noteStr;
              let noteName = noteStr.slice(0, -1);
              let oct = parseInt(noteStr.slice(-1));
              let newOct = Math.min(Math.max(oct + octaveOffset, 1), 8);
              return noteName + newOct;
            }

            // MOTORES DE SÍNTESIS CON GAIN STAGING Y FILTROS ANTI-CLIPPING
            function createSynthForRole(roleType) {
              let synth;
              if (roleType === 'bass') {
                synth = new Tone.MonoSynth({
                  oscillator: { type: 'triangle' },
                  envelope: { attack: 0.06, decay: 0.3, sustain: 0.7, release: 0.8 },
                  filter: { Q: 1, type: 'lowpass' },
                  filterEnvelope: { attack: 0.02, decay: 0.2, sustain: 0.4, release: 0.6, baseFrequency: 100, octaves: 2 }
                });
              } else if (roleType === 'lead') {
                synth = new Tone.PolySynth(Tone.Synth, {
                  maxPolyphony: 4,
                  oscillator: { type: 'sine' },
                  envelope: { attack: 0.05, decay: 0.25, sustain: 0.5, release: 0.8 }
                });
              } else if (roleType === 'pad') {
                synth = new Tone.PolySynth(Tone.Synth, {
                  maxPolyphony: 4,
                  oscillator: { type: 'sine' },
                  envelope: { attack: 0.5, decay: 1.0, sustain: 0.8, release: 2.0 }
                });
              } else if (roleType === 'perc') {
                synth = new Tone.PolySynth(Tone.Synth, {
                  maxPolyphony: 4,
                  oscillator: { type: 'triangle' },
                  envelope: { attack: 0.005, decay: 0.12, sustain: 0.0, release: 0.1 }
                });
              } else if (roleType === 'pluck') {
                synth = new Tone.PolySynth(Tone.FMSynth, {
                  maxPolyphony: 4,
                  harmonicity: 1.5,
                  modulationIndex: 0.6,
                  envelope: { attack: 0.01, decay: 0.3, sustain: 0.2, release: 0.8 }
                });
              }

              synth.volume.value = -18; // Ganancia segura atenuada
              return synth.connect(reverbNode);
            }

            const container = document.getElementById('tracksContainer');
            layers.forEach((layer, idx) => {
              trackStates[idx] = true;
              layerRoles[idx] = idx === 0 ? 'bass' : (idx === 1 ? 'lead' : (idx === 2 ? 'pad' : 'pluck'));
              layerOctaves[idx] = 0;
              layerVolumes[idx] = -18;

              const card = document.createElement('div');
              card.className = 'track-card';
              card.innerHTML = `
                <div>
                  <span style="font-size:9px; color:#00e676; font-weight:bold;">CAPA ${layer.id}</span>
                  <div style="font-size:9px; color:#aaa;">${layer.events.length} notas</div>
                </div>
                <div>
                  <label>TIMBRE / ROL</label>
                  <select onchange="changeLayerRole(${idx}, this.value)">
                    <option value="bass" ${idx===0?'selected':''}>🎸 Bajo Cálido (Triangle)</option>
                    <option value="lead" ${idx===1?'selected':''}>🎹 Rhodes / Lead Suave</option>
                    <option value="pad" ${idx===2?'selected':''}>🌌 Textura Ambient (Pad)</option>
                    <option value="pluck" ${idx===3?'selected':''}>🔔 Pluck Cristalino</option>
                    <option value="perc">🥁 Percusión Tonal</option>
                  </select>
                </div>
                <div>
                  <label>TONO / OCTAVA</label>
                  <select onchange="changeLayerOctave(${idx}, parseInt(this.value))">
                    <option value="-2">-2 Octavas (Muy Grave)</option>
                    <option value="-1">-1 Octava (Grave)</option>
                    <option value="0" selected>0 (Tono Real Video)</option>
                    <option value="1">+1 Octava (Agudo)</option>
                    <option value="2">+2 Octavas (Muy Agudo)</option>
                  </select>
                </div>
                <div>
                  <label>VOLUMEN (dB)</label>
                  <input type="range" min="-36" max="0" value="-18" oninput="updateTrackVol(${idx}, this.value)">
                </div>
                <button id="btnMute_${idx}" class="btn-mute" onclick="toggleMute(${idx})">ON</button>
              `;
              container.appendChild(card);
            });

            function changeLayerRole(idx, newRole) {
              layerRoles[idx] = newRole;
              if (synths[idx]) {
                synths[idx].dispose();
                synths[idx] = createSynthForRole(newRole);
                if (!trackStates[idx]) synths[idx].volume.value = -Infinity;
                else synths[idx].volume.value = layerVolumes[idx];
              }
            }

            function changeLayerOctave(idx, newOctave) {
              layerOctaves[idx] = newOctave;
            }

            function toggleMute(idx) {
              trackStates[idx] = !trackStates[idx];
              const btn = document.getElementById(`btnMute_${idx}`);
              if (trackStates[idx]) {
                btn.className = 'btn-mute';
                btn.innerText = 'ON';
                if (synths[idx]) synths[idx].volume.rampTo(layerVolumes[idx], 0.05);
              } else {
                btn.className = 'btn-mute muted';
                btn.innerText = 'MUTE';
                if (synths[idx]) synths[idx].volume.rampTo(-Infinity, 0.05);
              }
            }

            function updateTrackVol(idx, dbVal) {
              layerVolumes[idx] = parseFloat(dbVal);
              if (synths[idx] && trackStates[idx]) {
                synths[idx].volume.rampTo(layerVolumes[idx], 0.05);
              }
            }

            function updateMasterVol(val) {
              Tone.Destination.volume.rampTo(parseFloat(val), 0.05);
            }

            function updateReverb(val) {
              if (reverbNode) reverbNode.wet.rampTo(parseFloat(val), 0.05);
            }

            function updatePlaybackSpeed(val) {
              playbackSpeed = parseFloat(val);
              document.getElementById('lblSpeed').innerText = playbackSpeed.toFixed(1) + 'x';
              Tone.Transport.timeScale = playbackSpeed;
            }

            async function initAudioEngine() {
              if (recorderNode) return;
              await Tone.start();

              recorderNode = new Tone.Recorder();
              limiterNode = new Tone.Limiter(-2).connect(recorderNode).toDestination();
              
              masterGainNode = new Tone.Gain(0.35).connect(limiterNode);
              reverbNode = new Tone.Reverb({ decay: 2.8, wet: 0.25 }).connect(masterGainNode);
              await reverbNode.generate();

              Tone.Destination.volume.value = -3;

              synths = [];
              layers.forEach((layer, idx) => {
                let synth = createSynthForRole(layerRoles[idx]);
                if (!trackStates[idx]) synth.volume.value = -Infinity;
                else synth.volume.value = layerVolumes[idx];
                synths.push(synth);
              });
            }

            async function togglePlay() {
              await initAudioEngine();
              const btn = document.getElementById('btnPlay');

              if (!isPlaying) {
                parts = [];
                
                Tone.Transport.loop = true;
                Tone.Transport.loopStart = 0;
                Tone.Transport.loopEnd = videoDuration;

                layers.forEach((layer, idx) => {
                  let formattedEvents = layer.events.map(e => ({ time: e.time, norm_y: e.norm_y }));
                  
                  let part = new Tone.Part((time, value) => {
                    let noteIdx = Math.floor(value.norm_y * (currentScaleNotes.length - 1));
                    let baseNote = currentScaleNotes[noteIdx];
                    let finalNote = shiftNote(baseNote, layerOctaves[idx]);
                    
                    synths[idx].triggerAttackRelease(finalNote, "8n", time);
                  }, formattedEvents);
                  
                  part.loop = true;
                  part.loopEnd = videoDuration;
                  part.start(0);
                  
                  parts.push(part);
                });

                Tone.Transport.start();
                isPlaying = true;
                btn.className = 'btn-action playing';
                btn.innerText = "⏸️ DETENER BUCLE";
              } else {
                Tone.Transport.stop();
                parts.forEach(p => p.dispose());

                isPlaying = false;
                btn.className = 'btn-action';
                btn.innerText = "▶️ REPRODUCIR BUCLE LIMPIO";
              }
            }

            async function toggleRecord() {
              await initAudioEngine();
              const btn = document.getElementById('btnRec');
              const dlBtn = document.getElementById('btnDownload');

              if (!isRecording) {
                recorderNode.start();
                isRecording = true;
                btn.innerText = "⏹️ DETENER Y GENERAR WAV";
                dlBtn.style.display = "none";
              } else {
                const recording = await recorderNode.stop();
                isRecording = false;
                btn.innerText = "● GRABAR ARCHIVO AUDIO (WAV)";
                dlBtn.href = URL.createObjectURL(recording);
                dlBtn.style.display = "flex";
              }
            }
          </script>
        </body>
        </html>
        """

        rendered_html = html_template.replace("__LAYERS_JSON__", layers_json)\
            .replace("__DURATION__", str(duration_val))
            
        components.html(rendered_html, height=720)
    else:
        st.info("👈 Sube un video y presiona 'Extraer Capas de Movimiento' para comenzar.")

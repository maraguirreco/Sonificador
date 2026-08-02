import streamlit as st
import cv2
import numpy as np
import tempfile
import json
import base64
import streamlit.components.v1 as components

st.set_page_config(page_title="Everyday Motion Sound Studio", page_icon="🌊", layout="wide")

st.title("🌊 Everyday Motion Sound Studio // Precision Tempo & Infinite Loop")
st.write("Sonificación en bucle perfecto sincronizado con video. Controla la velocidad de reproducción y asigna instrumentos por capa.")

if 'layers_events' not in st.session_state:
    st.session_state['layers_events'] = []
if 'video_duration' not in st.session_state:
    st.session_state['video_duration'] = 0.0

SCALES = {
    "Cálida / Orgánica": ['C2', 'G2', 'C3', 'E3', 'G3', 'A3', 'C4', 'E4', 'G4'],
    "Melancólica / Menor": ['A1', 'E2', 'A2', 'C3', 'E3', 'F3', 'A3', 'C4', 'E4'],
    "Espacial / Cristalina": ['D2', 'A2', 'D3', 'F#3', 'A3', 'B3', 'D4', 'F#4', 'A4'],
    "Profunda / Lo-Fi": ['F1', 'C2', 'F2', 'Ab2', 'C3', 'Eb3', 'F3', 'Ab3', 'C4']
}

def extract_organic_motion_events(video_path, selected_scale):
    cap = cv2.VideoCapture(video_path)
    
    # Extraer FPS real del video
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
        _, thresh = cv2.threshold(diff, 18, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = [c for c in contours if cv2.contourArea(c) > 25]
        
        if valid_contours:
            valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)
            timestamp = round(frame_count / fps, 2)
            
            for idx, c in enumerate(valid_contours[:6]):
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cy = int(M["m01"] / M["m00"])
                    norm_y = 1.0 - (cy / height)
                    note_idx = int(norm_y * (len(selected_scale) - 1))
                    note = selected_scale[note_idx]
                    
                    if idx not in raw_events_by_layer:
                        raw_events_by_layer[idx] = []
                    
                    if not raw_events_by_layer[idx] or (timestamp - raw_events_by_layer[idx][-1]['time']) > 0.12:
                        raw_events_by_layer[idx].append({
                            'time': timestamp,
                            'note': note
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
col_vid, col_studio = st.columns([1, 1.3])

video_b64 = ""

with col_vid:
    st.subheader("📹 1. Video de Origen")
    scale_choice = st.selectbox("Escala Armónica Base:", list(SCALES.keys()))
    selected_scale = SCALES[scale_choice]

    video_file = st.file_uploader("Sube un video (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
    if video_file:
        st.video(video_file)
        video_bytes = video_file.getvalue()
        video_b64 = base64.b64encode(video_bytes).decode('utf-8')

        if st.button("✨ Escanear Subcapas y FPS del Video"):
            with st.spinner("Analizando velocidad de fotogramas y marcas de tiempo..."):
                tfile = tempfile.NamedTemporaryFile(delete=False)
                tfile.write(video_bytes)
                layers, duration, error = extract_organic_motion_events(tfile.name, selected_scale)
                if error:
                    st.error(error)
                else:
                    st.session_state['layers_events'] = layers
                    st.session_state['video_duration'] = duration
                    st.success(f"¡Éxito! Detectadas {len(layers)} subcapas. Duración del Bucle: {duration}s")

with col_studio:
    st.subheader("🎛️ 2. Reproducción en Bucle Sincronizado")
    
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

            .video-box {
              width: 100%; border-radius: 8px; overflow: hidden; background: #000;
              margin-bottom: 12px; border: 1px solid #30363d;
            }

            video { width: 100%; max-height: 190px; object-fit: contain; display: block; }

            .track-card {
              background: #21262d; border-left: 4px solid #00e676; border-radius: 6px;
              padding: 10px; margin-bottom: 8px; display: grid; grid-template-columns: 100px 1.2fr 1fr 1fr 65px;
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
            
            <div class="video-box">
              <video id="syncVideo" loop muted playsinline>
                <source src="data:video/mp4;base64,__VIDEO_B64__" type="video/mp4">
              </video>
            </div>

            <!-- CONTROLES MASTER & SPEED -->
            <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:10px; background:#21262d; padding:8px 12px; border-radius:8px; margin-bottom:10px;">
              <div>
                <label>⏱️ VELOCIDAD DE BUCLE</label>
                <select id="speedSelect" onchange="updatePlaybackSpeed(this.value)">
                  <option value="0.5">0.5x (Lento / Ambient)</option>
                  <option value="1.0" selected>1.0x (Tempo Real Video)</option>
                  <option value="1.25">1.25x (Más Rápido)</option>
                  <option value="1.5">1.5x (Urbano / Upbeat)</option>
                </select>
              </div>
              <div>
                <label>🔊 MASTER VOL (dB)</label>
                <input type="range" id="masterVol" min="-30" max="6" value="0" oninput="updateMasterVol(this.value)">
              </div>
              <div>
                <label>🌌 REVERB ESPACIAL</label>
                <input type="range" id="reverbWet" min="0" max="0.8" step="0.05" value="0.25" oninput="updateReverb(this.value)">
              </div>
            </div>

            <div style="font-size: 9px; font-weight: bold; color: #8b949e; margin-bottom: 6px;">ASIGNACIÓN POR SUBCAPA (DURACIÓN BUCLE: __DURATION__s):</div>
            <div id="tracksContainer"></div>

            <button id="btnPlay" class="btn-action" onclick="togglePlay()">▶️ REPRODUCIR EN BUCLE CONTINUO</button>
            <button id="btnRec" class="btn-action" style="background:#8957e5; color:white;" onclick="toggleRecord()">● GRABAR ARCHIVO AUDIO</button>
            <a id="btnDownload" class="btn-action btn-dl" style="display:none;" download="Loop_Motion_Track.wav">⬇️ DESCARGAR WAV</a>

          </div>

          <script>
            const layers = __LAYERS_JSON__;
            const videoDuration = __DURATION__;

            let isPlaying = false, isRecording = false;
            let playbackSpeed = 1.0;
            let synths = [], parts = [], trackStates = {};
            let layerRoles = {}, layerOctaves = {}, layerVolumes = {};
            let reverbNode, limiterNode, recorderNode;
            let loopRepeatScheduleId = null;

            function shiftNote(noteStr, octaveOffset) {
              if (!noteStr || octaveOffset === 0) return noteStr;
              let noteName = noteStr.slice(0, -1);
              let oct = parseInt(noteStr.slice(-1));
              let newOct = Math.min(Math.max(oct + octaveOffset, 1), 8);
              return noteName + newOct;
            }

            function createSynthForRole(roleType) {
              let synth;
              if (roleType === 'bass') {
                synth = new Tone.MonoSynth({
                  oscillator: { type: 'triangle' },
                  envelope: { attack: 0.04, decay: 0.3, sustain: 0.7, release: 0.8 },
                  filterEnvelope: { attack: 0.02, decay: 0.2, sustain: 0.4, release: 0.6, baseFrequency: 150 }
                });
              } else if (roleType === 'lead') {
                synth = new Tone.PolySynth(Tone.Synth, {
                  oscillator: { type: 'sawtooth' },
                  envelope: { attack: 0.02, decay: 0.2, sustain: 0.5, release: 0.6 }
                });
              } else if (roleType === 'pad') {
                synth = new Tone.PolySynth(Tone.Synth, {
                  oscillator: { type: 'sine' },
                  envelope: { attack: 0.4, decay: 0.8, sustain: 0.8, release: 1.8 }
                });
              } else if (roleType === 'perc') {
                synth = new Tone.PolySynth(Tone.Synth, {
                  oscillator: { type: 'square' },
                  envelope: { attack: 0.001, decay: 0.1, sustain: 0.0, release: 0.1 }
                });
              } else if (roleType === 'pluck') {
                synth = new Tone.PolySynth(Tone.FMSynth, {
                  harmonicity: 3,
                  modulationIndex: 2,
                  envelope: { attack: 0.01, decay: 0.4, sustain: 0.2, release: 1.0 }
                });
              }
              return synth.connect(reverbNode);
            }

            const container = document.getElementById('tracksContainer');
            layers.forEach((layer, idx) => {
              trackStates[idx] = true;
              layerRoles[idx] = idx === 0 ? 'bass' : (idx === 1 ? 'lead' : (idx === 2 ? 'pad' : 'pluck'));
              layerOctaves[idx] = 0;
              layerVolumes[idx] = 0;

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
                    <option value="bass" ${idx===0?'selected':''}>🎸 Bajo (Sub-Bass)</option>
                    <option value="lead" ${idx===1?'selected':''}>🎹 Melodía (Lead)</option>
                    <option value="pad" ${idx===2?'selected':''}>🌌 Textura (Pad)</option>
                    <option value="pluck" ${idx===3?'selected':''}>🔔 Campana (Pluck)</option>
                    <option value="perc">🥁 Percusión / Drum</option>
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
                  <input type="range" min="-30" max="6" value="0" oninput="updateTrackVol(${idx}, this.value)">
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
              Tone.Transport.timeScale = playbackSpeed;
              const vid = document.getElementById('syncVideo');
              if (vid) vid.playbackRate = playbackSpeed;
            }

            async function initAudioEngine() {
              if (recorderNode) return;
              await Tone.start();

              recorderNode = new Tone.Recorder();
              limiterNode = new Tone.Limiter(-1).connect(recorderNode).toDestination();
              reverbNode = new Tone.Reverb({ decay: 3.0, wet: 0.25 }).connect(limiterNode);
              await reverbNode.generate();

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
              const vid = document.getElementById('syncVideo');

              if (!isPlaying) {
                parts = [];
                
                // Configurar loop exacto a la duración del video
                Tone.Transport.loop = true;
                Tone.Transport.loopStart = 0;
                Tone.Transport.loopEnd = videoDuration;

                layers.forEach((layer, idx) => {
                  let formattedEvents = layer.events.map(e => ({ time: e.time, note: e.note }));
                  
                  let part = new Tone.Part((time, value) => {
                    let finalNote = shiftNote(value.note, layerOctaves[idx]);
                    synths[idx].triggerAttackRelease(finalNote, "8n", time);
                  }, formattedEvents);
                  
                  part.loop = true;
                  part.loopEnd = videoDuration;
                  part.start(0);
                  
                  parts.push(part);
                });

                if (vid) {
                  vid.currentTime = 0;
                  vid.playbackRate = playbackSpeed;
                  vid.play();
                }

                // Sincronizar reinicio del video cada vez que el transporte de audio da la vuelta
                loopRepeatScheduleId = Tone.Transport.scheduleRepeat((time) => {
                  if (vid) {
                    vid.currentTime = 0;
                    vid.play();
                  }
                }, videoDuration, 0);

                Tone.Transport.start();
                isPlaying = true;
                btn.className = 'btn-action playing';
                btn.innerText = "⏸️ DETENER BUCLE";
              } else {
                Tone.Transport.stop();
                if (loopRepeatScheduleId !== null) Tone.Transport.clear(loopRepeatScheduleId);
                parts.forEach(p => p.dispose());
                if (vid) vid.pause();

                isPlaying = false;
                btn.className = 'btn-action';
                btn.innerText = "▶️ REPRODUCIR EN BUCLE CONTINUO";
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
                btn.innerText = "● GRABAR ARCHIVO AUDIO";
                dlBtn.href = URL.createObjectURL(recording);
                dlBtn.style.display = "flex";
              }
            }
          </script>
        </body>
        </html>
        """

        rendered_html = html_template.replace("__LAYERS_JSON__", layers_json)\
            .replace("__VIDEO_B64__", video_b64)\
            .replace("__DURATION__", str(duration_val))
            
        components.html(rendered_html, height=1000)
    else:
        st.info("👈 Sube un video y presiona 'Escanear Subcapas y FPS del Video' para comenzar.")

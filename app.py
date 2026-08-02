import streamlit as st
import cv2
import numpy as np
import tempfile
import json
import base64
import pandas as pd
import streamlit.components.v1 as components

st.set_page_config(page_title="Everyday Motion Sound Studio", page_icon="🌊", layout="wide")

st.title("🌊 Everyday Motion Sound Studio // Real-Time Vision & Sonification")
st.write("Detección de movimiento transparente: visualiza el rastreo de OpenCV, analiza la gráfica temporal y ajusta la sensibilidad.")

if 'layers_data' not in st.session_state:
    st.session_state['layers_data'] = []
if 'timeline_df' not in st.session_state:
    st.session_state['timeline_df'] = None

MOOD_SCALES = {
    "Sad / Melancólico": ['C3', 'Eb3', 'F3', 'G3', 'Ab3', 'C4', 'Eb4', 'F4'],
    "Espacial / Ambient": ['C3', 'E3', 'F#3', 'G3', 'B3', 'C4', 'E4', 'F#4'],
    "Funk / Groove": ['C2', 'Eb3', 'F3', 'F#3', 'G3', 'Bb3', 'C4', 'Eb4'],
    "Cinematic / Épico": ['C2', 'G2', 'C3', 'Eb3', 'G3', 'C4', 'D4', 'Eb4']
}

LAYER_COLORS = [(0, 255, 0), (255, 0, 0), (0, 255, 255), (255, 0, 255)] # Verde, Azul, Amarillo, Magenta

def process_and_draw_motion(video_path, selected_scale, thresh_val, min_area_val):
    cap = cv2.VideoCapture(video_path)
    ret, prev_frame = cap.read()
    if not ret:
        return None, None, None, "No se pudo leer el archivo de video."
    
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    height, width, _ = prev_frame.shape
    
    # Archivo temporal para guardar el video procesado con las marcas de OpenCV
    out_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_writer = cv2.VideoWriter(out_temp.name, fourcc, 20.0, (width, height))
    
    frame_count, max_frames = 0, 160
    raw_layers_data = []
    timeline_records = []
    
    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(prev_gray, gray)
        _, thresh = cv2.threshold(diff, thresh_val, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = [c for c in contours if cv2.contourArea(c) > min_area_val]
        
        frame_notes = []
        frame_record = {"Frame": frame_count}
        
        if valid_contours:
            valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)
            
            for idx, c in enumerate(valid_contours[:4]):
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    
                    # Dibujar recuadro y punto de rastreo en el marco del video
                    color = LAYER_COLORS[idx % len(LAYER_COLORS)]
                    x, y, w, h = cv2.boundingRect(c)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                    cv2.putText(frame, f"Capa {idx+1}", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    
                    # Mapeo de nota
                    norm_y = 1.0 - (cy / height)
                    note_idx = int(norm_y * (len(selected_scale) - 1))
                    note_name = selected_scale[note_idx]
                    frame_notes.append(note_name)
                    
                    frame_record[f"Capa {idx+1}"] = note_idx
                    
        out_writer.write(frame)
        raw_layers_data.append(frame_notes)
        timeline_records.append(frame_record)

        prev_gray = gray
        frame_count += 1
        
    cap.release()
    out_writer.release()
    
    if not raw_layers_data or all(len(f) == 0 for f in raw_layers_data):
        return None, None, None, "No se detectó movimiento con la sensibilidad actual. Intenta bajar el umbral o el área mínima."

    max_detected_layers = max(len(f) for f in raw_layers_data if len(f) > 0)
    structured_layers = []
    
    roles = ["Bajo (Sub-Bass)", "Melodía Principal (Lead)", "Textura (Atmospheric Pad)", "Arpegiador / Percusión"]
    
    for layer_idx in range(max_detected_layers):
        layer_notes = [frame[layer_idx] for frame in raw_layers_data if len(frame) > layer_idx]
        clean_notes = [layer_notes[0]] if layer_notes else ['C3']
        for n in layer_notes[1:]:
            if n != clean_notes[-1]:
                clean_notes.append(n)
                
        structured_layers.append({
            "id": layer_idx + 1,
            "role": roles[layer_idx % len(roles)],
            "notes": clean_notes
        })
        
    df_timeline = pd.DataFrame(timeline_records).set_index("Frame")
    return structured_layers, out_temp.name, df_timeline, None

# --- PANEL LATERAL DE SENSIBILIDAD ---
st.sidebar.header("🎛️ Sensibilidad de Visión OpenCV")
st.sidebar.write("Ajusta los parámetros para capturar movimientos muy pequeños o grandes:")
thresh_sens = st.sidebar.slider("Sensibilidad de Umbral (Threshold)", 5, 100, 20, help="Valores más bajos capturan movimientos ultra suaves.")
min_area_sens = st.sidebar.slider("Área Mínima de Objeto (Píxeles)", 10, 500, 30, help="Tamaño mínimo del objeto en movimiento a rastrear.")

st.sidebar.markdown("---")
st.sidebar.header("🎨 Sentimiento Musical")
mood_selected = st.sidebar.selectbox("Atmósfera Musical (Mood):", list(MOOD_SCALES.keys()))
scale_notes = MOOD_SCALES[mood_selected]

# --- ESTRUCTURA DE LA PÁGINA ---
col_vid, col_studio = st.columns([1, 1.3])

video_b64 = ""
video_mime = "video/mp4"

with col_vid:
    st.subheader("📹 1. Cargar Video Cotidiano")
    video_file = st.file_uploader("Sube un video (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
    
    if video_file:
        video_bytes = video_file.getvalue()
        if st.button("✨ Procesar y Mostrar Rastreo OpenCV"):
            with st.spinner("Escaneando físicas y dibujando cajas de movimiento..."):
                tfile = tempfile.NamedTemporaryFile(delete=False)
                tfile.write(video_bytes)
                
                layers, processed_video_path, df_timeline, error = process_and_draw_motion(
                    tfile.name, scale_notes, thresh_sens, min_area_sens
                )
                
                if error:
                    st.error(error)
                else:
                    st.session_state['layers_data'] = layers
                    st.session_state['timeline_df'] = df_timeline
                    
                    # Cargar video procesado con rectángulos dibujaos
                    with open(processed_video_path, 'rb') as f:
                        proc_bytes = f.read()
                        video_b64 = base64.b64encode(proc_bytes).decode('utf-8')
                    st.success(f"¡Rastreadas {len(layers)} capas de movimiento con éxito!")

        if st.session_state['timeline_df'] is not None:
            st.markdown("### 📊 Comprobación: Altura de Notas por Frame")
            st.caption("Esta gráfica demuestra qué notas disparó cada objeto detectado a lo largo del tiempo:")
            st.line_chart(st.session_state['timeline_df'])

with col_studio:
    st.subheader("🎛️ 2. Estudio de Sonificación Sincronizado")
    
    if st.session_state['layers_data']:
        layers_json = json.dumps(st.session_state['layers_data'])

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
          <script src="https://cdnjs.cloudflare.com/ajax/libs/tone/14.8.49/Tone.js"></script>
          <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');
            * { box-sizing: border-box; }
            body { font-family: 'Space Mono', monospace; background: #0e1117; color: #fff; margin: 0; padding: 4px; }
            
            .studio-box { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 16px; }

            .sync-video-container {
              width: 100%; border-radius: 8px; overflow: hidden; background: #000;
              margin-bottom: 12px; border: 2px solid #30363d;
            }

            video { width: 100%; max-height: 220px; object-fit: contain; display: block; }

            .global-controls {
              display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
              background: #21262d; border-radius: 8px; padding: 12px; margin-bottom: 14px;
            }

            .track-card {
              background: #21262d; border-left: 4px solid #58a6ff; border-radius: 6px;
              padding: 10px; margin-bottom: 8px; display: grid; grid-template-columns: 1.5fr 1fr 100px;
              gap: 10px; align-items: center;
            }

            .btn-mute {
              background: #238636; color: white; border: none; padding: 6px 10px;
              border-radius: 6px; cursor: pointer; font-size: 10px; font-weight: bold; width: 100%;
            }
            .btn-mute.muted { background: #3f444c; color: #8b949e; }

            label { font-size: 8px; color: #8b949e; font-weight: bold; display: block; margin-bottom: 2px; }
            input[type=range] { width: 100%; accent-color: #58a6ff; }

            .btn-action {
              background: #238636; color: white; border: none; padding: 12px;
              border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 12px; width: 100%; margin-top: 8px;
            }
            .btn-action.playing { background: #da3633; }
            .btn-dl { background: #1f6beb; text-decoration: none; display: flex; align-items: center; justify-content: center; }
          </style>
        </head>
        <body>

          <div class="studio-card">
            
            <div class="sync-video-container">
              <video id="syncVideo" loop muted playsinline>
                <source src="data:video/mp4;base64,__VIDEO_B64__" type="video/mp4">
              </video>
            </div>

            <div class="global-controls">
              <div>
                <label>⏱️ TEMPO: <b id="lblBpm">100</b> BPM</label>
                <input type="range" id="bpm" min="50" max="180" value="100" oninput="updateBpm(this.value)">
              </div>
              <div>
                <label>🔊 MASTER VOL: <b id="lblMasterVol">0</b> dB</label>
                <input type="range" id="masterVol" min="-30" max="6" value="0" oninput="updateMasterVol(this.value)">
              </div>
              <div>
                <label>🌌 REVERB (ESPACIO)</label>
                <input type="range" id="reverbWet" min="0" max="0.9" step="0.05" value="0.3" oninput="updateReverb(this.value)">
              </div>
              <div>
                <label>📻 DELAY / ECO</label>
                <input type="range" id="delayWet" min="0" max="0.8" step="0.05" value="0.2" oninput="updateDelay(this.value)">
              </div>
              <div>
                <label>🔥 DISTORSIÓN / CARÁCTER</label>
                <input type="range" id="distVal" min="0" max="0.8" step="0.05" value="0.05" oninput="updateDistortion(this.value)">
              </div>
              <div>
                <label>📈 ATAQUE ADSR</label>
                <input type="range" id="attackVal" min="0.01" max="1.5" step="0.05" value="0.05" oninput="updateAttack(this.value)">
              </div>
            </div>

            <div style="font-size: 9px; font-weight: bold; color: #8b949e; margin-bottom: 6px;">SUBPISTAS DETECTADAS DEL VIDEO:</div>
            <div id="tracksContainer"></div>

            <button id="btnPlay" class="btn-action" onclick="togglePlay()">▶️ REPRODUCIR VIDEO Y MÚSICA EN SYNC</button>
            <button id="btnRec" class="btn-action" style="background:#8957e5;" onclick="toggleRecord()">● GRABAR MEZCLA MASTER</button>
            <a id="btnDownload" class="btn-action btn-dl" style="display:none;" download="Everyday_Motion_Track.wav">⬇️ DESCARGAR ARCHIVO WAV</a>

          </div>

          <script>
            const layers = __LAYERS_JSON__;

            let isPlaying = false, isRecording = false;
            let synths = [], sequences = [], trackStates = {};
            let reverbNode, delayNode, distNode, recorderNode;

            const container = document.getElementById('tracksContainer');
            layers.forEach((layer, idx) => {
              trackStates[idx] = true;
              const card = document.createElement('div');
              card.className = 'track-card';
              card.innerHTML = `
                <div>
                  <span style="font-size:9px; color:#58a6ff; font-weight:bold;">CAPA ${idx + 1}</span>
                  <div style="font-size:11px; font-weight:bold;">${layer.role}</div>
                </div>
                <div>
                  <label>VOLUMEN</label>
                  <input type="range" min="-30" max="6" value="0" oninput="updateTrackVol(${idx}, this.value)">
                </div>
                <button id="btnMute_${idx}" class="btn-mute" onclick="toggleMute(${idx})">ON</button>
              `;
              container.appendChild(card);
            });

            function toggleMute(idx) {
              trackStates[idx] = !trackStates[idx];
              const btn = document.getElementById(`btnMute_${idx}`);
              if (trackStates[idx]) {
                btn.className = 'btn-mute';
                btn.innerText = 'ON';
                if (synths[idx]) synths[idx].volume.rampTo(0, 0.05);
              } else {
                btn.className = 'btn-mute muted';
                btn.innerText = 'MUTE';
                if (synths[idx]) synths[idx].volume.rampTo(-Infinity, 0.05);
              }
            }

            function updateTrackVol(idx, dbVal) {
              if (synths[idx] && trackStates[idx]) {
                synths[idx].volume.rampTo(parseFloat(dbVal), 0.05);
              }
            }

            function updateBpm(val) {
              document.getElementById('lblBpm').innerText = val;
              Tone.Transport.bpm.rampTo(parseFloat(val), 0.1);
            }

            function updateMasterVol(val) {
              document.getElementById('lblMasterVol').innerText = val;
              Tone.Destination.volume.rampTo(parseFloat(val), 0.05);
            }

            function updateReverb(val) {
              if (reverbNode) reverbNode.wet.rampTo(parseFloat(val), 0.05);
            }

            function updateDelay(val) {
              if (delayNode) delayNode.wet.rampTo(parseFloat(val), 0.05);
            }

            function updateDistortion(val) {
              if (distNode) distNode.distortion = parseFloat(val);
            }

            function updateAttack(val) {
              synths.forEach(s => {
                if (s.set) s.set({ envelope: { attack: parseFloat(val) } });
              });
            }

            async function initAudioEngine() {
              if (recorderNode) return;
              await Tone.start();

              recorderNode = new Tone.Recorder();
              distNode = new Tone.Distortion(0.05).connect(recorderNode).toDestination();
              reverbNode = new Tone.Reverb({ decay: 3.5, wet: 0.3 }).connect(distNode);
              await reverbNode.generate();

              delayNode = new Tone.FeedbackDelay("8n.", 0.2).connect(reverbNode);

              synths = [];
              layers.forEach((layer, idx) => {
                let synth;
                if (idx === 0) {
                  synth = new Tone.MonoSynth({
                    oscillator: { type: 'sawtooth' },
                    envelope: { attack: 0.05, decay: 0.3, sustain: 0.8, release: 0.8 }
                  }).connect(reverbNode);
                } else if (idx === 1) {
                  synth = new Tone.PolySynth(Tone.Synth, {
                    envelope: { attack: 0.05, release: 0.6 }
                  }).connect(delayNode);
                } else {
                  synth = new Tone.PolySynth(Tone.Synth, {
                    oscillator: { type: 'sine' },
                    envelope: { attack: 0.2, release: 1.5 }
                  }).connect(delayNode);
                }

                if (!trackStates[idx]) synth.volume.value = -Infinity;
                synths.push(synth);
              });

              Tone.Transport.loop = true;
              Tone.Transport.loopStart = 0;
              Tone.Transport.loopEnd = "4m";
            }

            async function togglePlay() {
              await initAudioEngine();
              const btn = document.getElementById('btnPlay');
              const vid = document.getElementById('syncVideo');

              if (!isPlaying) {
                sequences = [];
                layers.forEach((layer, idx) => {
                  let rate = idx === 0 ? "2n" : (idx === 1 ? "4n" : "8n");
                  let seq = new Tone.Sequence((time, note) => {
                    synths[idx].triggerAttackRelease(note, rate, time);
                  }, layer.notes, rate).start(0);
                  sequences.push(seq);
                });

                if (vid) {
                  vid.currentTime = 0;
                  vid.play();
                }

                Tone.Transport.start();
                isPlaying = true;
                btn.className = 'btn-action playing';
                btn.innerText = "⏸️ DETENER VIDEO Y MÚSICA";
              } else {
                Tone.Transport.stop();
                sequences.forEach(s => s.dispose());
                
                if (vid) {
                  vid.pause();
                }

                isPlaying = false;
                btn.className = 'btn-action';
                btn.innerText = "▶️ REPRODUCIR VIDEO Y MÚSICA EN SYNC";
              }
            }

            async function toggleRecord() {
              await initAudioEngine();
              const btn = document.getElementById('btnRec');
              const dlBtn = document.getElementById('btnDownload');

              if (!isRecording) {
                recorderNode.start();
                isRecording = true;
                btn.innerText = "⏹️ FINALIZAR GRABACIÓN MASTER";
                dlBtn.style.display = "none";
              } else {
                const recording = await recorderNode.stop();
                isRecording = false;
                btn.innerText = "● GRABAR MEZCLA MASTER";
                dlBtn.href = URL.createObjectURL(recording);
                dlBtn.style.display = "flex";
              }
            }
          </script>
        </body>
        </html>
        """

        rendered_html = html_template.replace("__LAYERS_JSON__", layers_json).replace("__VIDEO_B64__", video_b64)
        components.html(rendered_html, height=780)
    else:
        st.info("👈 Sube un video y presiona 'Procesar y Mostrar Rastreo OpenCV' para extraer tus pistas.")

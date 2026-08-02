import streamlit as st
import cv2
import numpy as np
import tempfile
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="Motion Sound Studio Pro", page_icon="🌊", layout="wide")

st.title("🌊 Everyday Motion Sound Studio")
st.write("Extrae melodías del movimiento cotidiano, ajusta volúmenes y efectos en vivo sin detener la música, y graba tus pistas.")

if 'layers_data' not in st.session_state:
    st.session_state['layers_data'] = []

# Escalas según la atmósfera elegida
MOOD_SCALES = {
    "Sad / Melancólico": ['C3', 'Eb3', 'F3', 'G3', 'Ab3', 'C4', 'Eb4', 'F4'],
    "Espacial / Ambient": ['C3', 'E3', 'F#3', 'G3', 'B3', 'C4', 'E4', 'F#4'],
    "Funk / Groove": ['C2', 'Eb3', 'F3', 'F#3', 'G3', 'Bb3', 'C4', 'Eb4'],
    "Cinematic / Épico": ['C2', 'G2', 'C3', 'Eb3', 'G3', 'C4', 'D4', 'Eb4']
}

def process_video_to_sound_layers(video_path, selected_scale):
    cap = cv2.VideoCapture(video_path)
    ret, prev_frame = cap.read()
    if not ret:
        return None, "No se pudo leer el archivo de video."
    
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    height, _ = prev_gray.shape
    
    frame_count, max_frames = 0, 160
    raw_layers_data = []
    
    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(prev_gray, gray)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = [c for c in contours if cv2.contourArea(c) > 30]
        
        if valid_contours:
            valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)
            frame_notes = []
            
            for idx, c in enumerate(valid_contours[:4]):
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cy = int(M["m01"] / M["m00"])
                    norm_y = 1.0 - (cy / height)
                    note_idx = int(norm_y * (len(selected_scale) - 1))
                    frame_notes.append(selected_scale[note_idx])
                    
            raw_layers_data.append(frame_notes)

        prev_gray = gray
        frame_count += 1
        
    cap.release()
    
    if not raw_layers_data:
        return [], "No se detectó suficiente movimiento en el video."

    max_detected_layers = max(len(f) for f in raw_layers_data)
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
        
    return structured_layers, None

# --- ESTRUCTURA DE LA PÁGINA ---
col_vid, col_studio = st.columns([1, 1.3])

with col_vid:
    st.subheader("📹 1. Cargar Video Cotidiano")
    mood_selected = st.selectbox("Atmósfera Musical (Mood):", list(MOOD_SCALES.keys()))
    scale_notes = MOOD_SCALES[mood_selected]

    video_file = st.file_uploader("Sube un video (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
    if video_file:
        st.video(video_file)
        if st.button("✨ Procesar Movimiento a Música"):
            with st.spinner("Escaneando subcapas de movimiento..."):
                tfile = tempfile.NamedTemporaryFile(delete=False)
                tfile.write(video_file.read())
                layers, error = process_video_to_sound_layers(tfile.name, scale_notes)
                if error:
                    st.error(error)
                else:
                    st.session_state['layers_data'] = layers
                    st.success(f"¡Éxito! Se crearon {len(layers)} capas independientes.")

with col_studio:
    st.subheader("🎛️ 2. Estudio de Sonificación en Vivo")
    
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
            
            .studio-box {
              background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 16px;
            }

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
            .btn-action.recording { background: #8957e5; }
            .btn-dl { background: #1f6beb; text-decoration: none; display: flex; align-items: center; justify-content: center; }
          </style>
        </head>
        <body>

          <div class="studio-card">
            
            <!-- MASTER & EFFECT CONTROLS (CONTINUOS EN VIVO) -->
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

            <!-- CONTROLES POR PISTA -->
            <div style="font-size: 9px; font-weight: bold; color: #8b949e; margin-bottom: 6px;">SUBPISTAS DETECTADAS DEL VIDEO:</div>
            <div id="tracksContainer"></div>

            <!-- BOTONES DE REPRODUCCIÓN Y EXPORTACIÓN -->
            <button id="btnPlay" class="btn-action" onclick="togglePlay()">▶️ REPRODUCIR EN VIVO</button>
            <button id="btnRec" class="btn-action" style="background:#8957e5;" onclick="toggleRecord()">● GRABAR MEZCLA MASTER</button>
            <a id="btnDownload" class="btn-action btn-dl" style="display:none;" download="Everyday_Motion_Track.wav">⬇️ DESCARGAR ARCHIVO WAV</a>

          </div>

          <script>
            const layers = __LAYERS_JSON__;

            let isPlaying = false, isRecording = false;
            let synths = [], sequences = [], trackStates = {};
            let reverbNode, delayNode, distNode, recorderNode;

            // Renderizar UI por pista
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

            // MODIFICACIONES CONTINUAS EN TIEMPO REAL (SIN INTERRUMPIR LA MÚSICA)
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

            // AUDIO ENGINE INICIALIZACIÓN
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
                  // Bajo
                  synth = new Tone.MonoSynth({
                    oscillator: { type: 'sawtooth' },
                    envelope: { attack: 0.05, decay: 0.3, sustain: 0.8, release: 0.8 }
                  }).connect(reverbNode);
                } else if (idx === 1) {
                  // Lead
                  synth = new Tone.PolySynth(Tone.Synth, {
                    envelope: { attack: 0.05, release: 0.6 }
                  }).connect(delayNode);
                } else {
                  // Pad / Textura
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

              if (!isPlaying) {
                sequences = [];
                layers.forEach((layer, idx) => {
                  let rate = idx === 0 ? "2n" : (idx === 1 ? "4n" : "8n");
                  let seq = new Tone.Sequence((time, note) => {
                    synths[idx].triggerAttackRelease(note, rate, time);
                  }, layer.notes, rate).start(0);
                  sequences.push(seq);
                });

                Tone.Transport.start();
                isPlaying = true;
                btn.className = 'btn-action playing';
                btn.innerText = "⏸️ DETENER";
              } else {
                Tone.Transport.stop();
                sequences.forEach(s => s.dispose());
                isPlaying = false;
                btn.className = 'btn-action';
                btn.innerText = "▶️ REPRODUCIR EN VIVO";
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

        rendered_html = html_template.replace("__LAYERS_JSON__", layers_json)
        components.html(rendered_html, height=560)
    else:
        st.info("👈 Sube un video y presiona 'Procesar Movimiento a Música' para generar tus pistas.")

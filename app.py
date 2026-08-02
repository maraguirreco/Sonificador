import streamlit as st
import cv2
import numpy as np
import tempfile
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="Motion Sound Studio", page_icon="🌊", layout="wide")

st.title("🌊 Everyday Motion Sound Studio")
st.write("Convierte movimientos del mundo real en pistas musicales, bajos, baterías y texturas listas para tu producción.")

if 'layers_data' not in st.session_state:
    st.session_state['layers_data'] = []

# --- CONFIGURACIÓN DE ESCALAS SEGÚN EL MOOD ---
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
            
            # Detectar hasta 4 subcapas distintas de movimiento
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
    
    roles = ["Bajo (Sub Bass)", "Melodía Principal", "Textura / Pad", "Percusión / Arpegio"]
    
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

# --- PANEL DE CONTROL SIDEBAR ---
st.sidebar.header("🎨 Ajustes de Sentimiento (Mood)")
mood_selected = st.sidebar.selectbox("Selecciona la atmósfera musical:", list(MOOD_SCALES.keys()))
scale_notes = MOOD_SCALES[mood_selected]

st.sidebar.markdown("---")
st.sidebar.header("🎛️ Controles del Sonido")
bpm = st.sidebar.slider("⏱️ Tempo (BPM)", 50, 180, 100)
reverb_val = st.sidebar.slider("🌌 Reverb (Espacio)", 0.0, 1.0, 0.4, 0.05)
delay_val = st.sidebar.slider("📻 Eco / Delay", 0.0, 0.9, 0.2, 0.05)
distortion_val = st.sidebar.slider("🔥 Distorsión / Carácter", 0.0, 1.0, 0.1, 0.05)
attack_val = st.sidebar.slider("📈 Curva de Ataque (ADSR)", 0.01, 1.5, 0.05, 0.05)

# --- CARGA DE VIDEO ---
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📹 Video de Origen")
    video_file = st.file_uploader("Sube un video cotidiano (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
    if video_file:
        st.video(video_file)
        if st.button("✨ Procesar Movimiento a Música"):
            with st.spinner("Escaneando subcapas y cuantizando notas..."):
                tfile = tempfile.NamedTemporaryFile(delete=False)
                tfile.write(video_file.read())
                layers, error = process_video_to_sound_layers(tfile.name, scale_notes)
                if error:
                    st.error(error)
                else:
                    st.session_state['layers_data'] = layers
                    st.success(f"¡Éxito! Se generaron {len(layers)} capas musicales.")

with col2:
    st.subheader("🎧 Reproductor y Mezclador")
    if st.session_state['layers_data']:
        layers_json = json.dumps(st.session_state['layers_data'])

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
          <script src="https://cdnjs.cloudflare.com/ajax/libs/tone/14.8.49/Tone.js"></script>
          <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');
            body { font-family: 'Space Mono', monospace; background: #0e1117; color: #fff; margin: 0; padding: 10px; }
            
            .studio-card {
              background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 16px;
            }

            .track-row {
              display: flex; align-items: center; justify-content: space-between;
              background: #21262d; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;
            }

            .btn-toggle {
              background: #238636; color: white; border: none; padding: 6px 12px;
              border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 11px;
            }
            .btn-toggle.muted { background: #3f444c; color: #8b949e; }

            .btn-control {
              background: #238636; color: white; border: none; padding: 12px 20px;
              border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 13px; width: 100%; margin-top: 10px;
            }
            .btn-control.stop { background: #da3633; }
            .btn-dl { background: #1f6beb; text-decoration: none; display: flex; align-items: center; justify-content: center; }
          </style>
        </head>
        <body>

          <div class="studio-card">
            <div style="font-size:12px; color:#8b949e; margin-bottom:12px;">
              ATMÓSFERA: <b style="color:#58a6ff;">__MOOD__</b> | TEMPO: <b>__BPM__ BPM</b>
            </div>

            <!-- PISTAS GENERADAS -->
            <div id="tracksContainer"></div>

            <!-- REPRODUCCIÓN Y GRABACIÓN -->
            <button id="btnPlay" class="btn-control" onclick="togglePlay()">▶️ REPRODUCIR PISTAS DEL VIDEO</button>
            <button id="btnRec" class="btn-control" style="background:#8957e5;" onclick="toggleRecord()">● GRABAR MEZCLA EN VIVO</button>
            <a id="btnDownload" class="btn-control btn-dl" style="display:none;" download="Motion_Sonification.wav">⬇️ DESCARGAR ARCHIVO WAV</a>
          </div>

          <script>
            const layers = __LAYERS_JSON__;
            const bpmVal = __BPM__;
            const reverbVal = __REVERB__;
            const delayVal = __DELAY__;
            const distVal = __DISTORTION__;
            const attackVal = __ATTACK__;

            let isPlaying = false, isRecording = false;
            let synths = [], sequences = [], trackStates = {};
            let reverbNode, delayNode, distNode, recorderNode;

            // Renderizar pistas
            const container = document.getElementById('tracksContainer');
            layers.forEach((layer, idx) => {
              trackStates[idx] = true;
              const row = document.createElement('div');
              row.className = 'track-row';
              row.innerHTML = `
                <div>
                  <span style="font-size:11px; color:#58a6ff; font-weight:bold;">CAPA ${idx + 1}</span>
                  <div style="font-size:12px; font-weight:bold;">${layer.role}</div>
                </div>
                <button id="btnMute_${idx}" class="btn-toggle" onclick="toggleMute(${idx})">ACTIVO</button>
              `;
              container.appendChild(row);
            });

            function toggleMute(idx) {
              trackStates[idx] = !trackStates[idx];
              const btn = document.getElementById(`btnMute_${idx}`);
              if (trackStates[idx]) {
                btn.className = 'btn-toggle';
                btn.innerText = 'ACTIVO';
                if (synths[idx]) synths[idx].volume.value = 0;
              } else {
                btn.className = 'btn-toggle muted';
                btn.innerText = 'SILENCIADO';
                if (synths[idx]) synths[idx].volume.value = -Infinity;
              }
            }

            async function initAudioEngine() {
              if (recorderNode) return;
              await Tone.start();

              recorderNode = new Tone.Recorder();
              distNode = new Tone.Distortion(distVal).connect(recorderNode).toDestination();
              reverbNode = new Tone.Reverb({ decay: 3, wet: reverbVal }).connect(distNode);
              await reverbNode.generate();

              delayNode = new Tone.FeedbackDelay("8n.", delayVal).connect(reverbNode);

              synths = [];
              layers.forEach((layer, idx) => {
                let synth;
                if (idx === 0) {
                  // Bajo profundo
                  synth = new Tone.MonoSynth({
                    oscillator: { type: 'sawtooth' },
                    envelope: { attack: 0.05, decay: 0.3, sustain: 0.8, release: 0.8 }
                  }).connect(reverbNode);
                } else if (idx === 1) {
                  // Lead / Melodía
                  synth = new Tone.PolySynth(Tone.Synth, {
                    envelope: { attack: attackVal, release: 0.6 }
                  }).connect(delayNode);
                } else {
                  // Pad / Textura
                  synth = new Tone.PolySynth(Tone.Synth, {
                    oscillator: { type: 'sine' },
                    envelope: { attack: attackVal * 2, release: 1.5 }
                  }).connect(delayNode);
                }

                if (!trackStates[idx]) synth.volume.value = -Infinity;
                synths.push(synth);
              });

              Tone.Transport.bpm.value = bpmVal;
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
                btn.className = 'btn-control stop';
                btn.innerText = "⏸️ DETENER";
              } else {
                Tone.Transport.stop();
                sequences.forEach(s => s.dispose());
                isPlaying = false;
                btn.className = 'btn-control';
                btn.innerText = "▶️ REPRODUCIR PISTAS DEL VIDEO";
              }
            }

            async function toggleRecord() {
              await initAudioEngine();
              const btn = document.getElementById('btnRec');
              const dlBtn = document.getElementById('btnDownload');

              if (!isRecording) {
                recorderNode.start();
                isRecording = true;
                btn.innerText = "⏹️ DETENER Y GENERAR AUDIO";
                dlBtn.style.display = "none";
              } else {
                const recording = await recorderNode.stop();
                isRecording = false;
                btn.innerText = "● GRABAR MEZCLA EN VIVO";
                dlBtn.href = URL.createObjectURL(recording);
                dlBtn.style.display = "flex";
              }
            }
          </script>
        </body>
        </html>
        """

        rendered_html = html_template.replace("__LAYERS_JSON__", layers_json)\
            .replace("__MOOD__", mood_selected)\
            .replace("__BPM__", str(bpm))\
            .replace("__REVERB__", str(reverb_val))\
            .replace("__DELAY__", str(delay_val))\
            .replace("__DISTORTION__", str(distortion_val))\
            .replace("__ATTACK__", str(attack_val))

        components.html(rendered_html, height=520)
    else:
        st.info("👈 Sube un video y presiona 'Procesar Movimiento a Música' para extraer tus pistas.")

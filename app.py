import streamlit as st
import cv2
import numpy as np
import tempfile
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="Sonificador Multicapa", page_icon="🎼", layout="wide")

st.title("🍃 Sonificador de Movimiento Multicapa (Polifónico)")
st.write("Detecta múltiples capas de movimiento simultáneas (fondo y frente) y las convierte en arreglos polifónicos en tiempo real.")

if 'layers_data' not in st.session_state:
    st.session_state['layers_data'] = {"layer1": [], "layer2": []}

BASS_SCALE = ['C2', 'G2', 'A2', 'F2', 'C3', 'G3']
LEAD_SCALE = ['C4', 'D4', 'E4', 'G4', 'A4', 'C5', 'D5', 'E5', 'G5', 'A5']

def process_video_motion_layers(video_path):
    cap = cv2.VideoCapture(video_path)
    ret, prev_frame = cap.read()
    if not ret:
        return None, "No se pudo leer el archivo de video."
    
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    height, _ = prev_gray.shape
    
    layer1_notes = [] # Capa de Bajo / Armonía (Movimiento grande)
    layer2_notes = [] # Capa de Melodía (Movimiento pequeño)
    
    frame_count = 0
    max_frames = 150
    
    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(prev_gray, gray)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        
        # Encontrar contornos/grupos de movimiento independientes
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtrar contornos significativos
        valid_contours = [c for c in contours if cv2.contourArea(c) > 50]
        
        if valid_contours:
            # Ordenar por tamaño de área (mayor a menor)
            valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)
            
            # CAPA 1: El movimiento más grande (Bajo / Fondo)
            c1 = valid_contours[0]
            M1 = cv2.moments(c1)
            if M1["m00"] != 0:
                cy1 = int(M1["m01"] / M1["m00"])
                norm_y1 = 1.0 - (cy1 / height)
                idx1 = int(norm_y1 * (len(BASS_SCALE) - 1))
                layer1_notes.append(BASS_SCALE[idx1])
            
            # CAPA 2: El segundo movimiento detectado (Melodía / Detalle)
            if len(valid_contours) > 1:
                c2 = valid_contours[1]
                M2 = cv2.moments(c2)
                if M2["m00"] != 0:
                    cy2 = int(M2["m01"] / M2["m00"])
                    norm_y2 = 1.0 - (cy2 / height)
                    idx2 = int(norm_y2 * (len(LEAD_SCALE) - 1))
                    layer2_notes.append(LEAD_SCALE[idx2])
            else:
                # Si no hay segunda capa, se genera una variación melódica armónica
                layer2_notes.append(LEAD_SCALE[0])

        prev_gray = gray
        frame_count += 1
        
    cap.release()
    return {"layer1": layer1_notes, "layer2": layer2_notes}, None

col_vid, col_synth = st.columns([1, 1.2])

with col_vid:
    video_file = st.file_uploader("Sube un video (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
    if video_file:
        st.video(video_file)
        if st.button("🔍 Escanear Subcapas de Movimiento"):
            with st.spinner("Analizando capas independientes con OpenCV..."):
                tfile = tempfile.NamedTemporaryFile(delete=False)
                tfile.write(video_file.read())
                
                layers, error = process_video_motion_layers(tfile.name)
                if error:
                    st.error(error)
                else:
                    # Filtrar repeticiones
                    l1 = [layers['layer1'][0]] if layers['layer1'] else ['C2']
                    for n in layers['layer1'][1:]:
                        if n != l1[-1]: l1.append(n)
                        
                    l2 = [layers['layer2'][0]] if layers['layer2'] else ['C4']
                    for n in layers['layer2'][1:]:
                        if n != l2[-1]: l2.append(n)

                    st.session_state['layers_data'] = {"layer1": l1, "layer2": l2}
                    st.success("¡Subcapas extraídas exitosamente!")

with col_synth:
    if st.session_state['layers_data']['layer1']:
        st.markdown("### 🎛️ Mezclador Multicapa en Tiempo Real")
        
        l1_json = json.dumps(st.session_state['layers_data']['layer1'])
        l2_json = json.dumps(st.session_state['layers_data']['layer2'])
        
        st.info(f"**Capa 1 (Bajo / Fondo):** {', '.join(st.session_state['layers_data']['layer1'][:6])}...")
        st.success(f"**Capa 2 (Melodía / Detalle):** {', '.join(st.session_state['layers_data']['layer2'][:8])}...")

        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <script src="https://cdnjs.cloudflare.com/ajax/libs/tone/14.8.49/Tone.js"></script>
          <style>
            body {{ font-family: system-ui, sans-serif; background: #0e1117; color: #fff; margin: 0; padding: 10px; }}
            .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; }}
            .btn-play {{ background: #00c853; color: white; border: none; padding: 14px; font-size: 16px; font-weight: bold; border-radius: 8px; cursor: pointer; width: 100%; margin-bottom: 20px; }}
            .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
            label {{ display: block; font-size: 12px; color: #8b949e; margin-bottom: 4px; font-weight: bold; }}
            input[type=range] {{ width: 100%; background: #0d1117; }}
            .layer-box {{ background: #21262d; padding: 12px; border-radius: 8px; margin-bottom: 15px; }}
          </style>
        </head>
        <body>
          <div class="card">
            <button id="playBtn" class="btn-play">▶️ Reproducir Mezcla Polifónica</button>
            
            <div class="layer-box">
              <span style="color:#58a6ff; font-weight:bold;">🎹 Capa 1: Bajo / Acompañamiento</span>
              <div class="grid" style="margin-top:10px;">
                <div>
                  <label>Volumen Bajo</label>
                  <input type="range" id="volL1" min="-30" max="6" value="0">
                </div>
                <div>
                  <label>Filtro / Calidez</label>
                  <input type="range" id="filterL1" min="100" max="2000" value="600">
                </div>
              </div>
            </div>

            <div class="layer-box">
              <span style="color:#2ea043; font-weight:bold;">🎵 Capa 2: Melodía Principal</span>
              <div class="grid" style="margin-top:10px;">
                <div>
                  <label>Volumen Melodía</label>
                  <input type="range" id="volL2" min="-30" max="6" value="-2">
                </div>
                <div>
                  <label>Reverb Espacial</label>
                  <input type="range" id="reverbL2" min="0" max="0.9" step="0.05" value="0.4">
                </div>
              </div>
            </div>

            <div class="grid">
              <div>
                <label>⏱️ Tempo Global (BPM)</label>
                <input type="range" id="bpm" min="50" max="180" value="100">
              </div>
            </div>
          </div>

          <script>
            const layer1Notes = {l1_json};
            const layer2Notes = {l2_json};
            let isPlaying = false;
            let bassSynth, leadSynth, reverb, filterL1;
            let seq1, seq2;

            async function initAudio() {{
              await Tone.start();

              reverb = new Tone.Reverb({{ decay: 3, wet: 0.4 }}).toDestination();
              await reverb.generate();

              filterL1 = new Tone.Filter(600, "lowpass").toDestination();

              bassSynth = new Tone.MonoSynth({{
                oscillator: {{ type: "sawtooth" }},
                envelope: {{ attack: 0.1, decay: 0.4, sustain: 0.8, release: 1.2 }}
              }}).connect(filterL1);

              leadSynth = new Tone.PolySynth(Tone.Synth, {{
                oscillator: {{ type: "triangle" }},
                envelope: {{ attack: 0.02, decay: 0.2, sustain: 0.2, release: 0.6 }}
              }}).connect(reverb);

              seq1 = new Tone.Sequence((time, note) => {{
                bassSynth.triggerAttackRelease(note, "2n", time);
              }}, layer1Notes, "2n");

              seq2 = new Tone.Sequence((time, note) => {{
                leadSynth.triggerAttackRelease(note, "8n", time);
              }}, layer2Notes, "4n");

              Tone.Transport.bpm.value = parseInt(document.getElementById('bpm').value);
            }}

            document.getElementById('playBtn').addEventListener('click', async () => {{
              if (!isPlaying) {{
                await initAudio();
                Tone.Transport.start();
                seq1.start(0);
                seq2.start(0);
                isPlaying = true;
                document.getElementById('playBtn').innerText = "⏸️ Pausar Mezcla";
                document.getElementById('playBtn').style.background = "#30363d";
              }} else {{
                Tone.Transport.stop();
                if (seq1) seq1.stop();
                if (seq2) seq2.stop();
                isPlaying = false;
                document.getElementById('playBtn').innerText = "▶️ Reproducir Mezcla Polifónica";
                document.getElementById('playBtn').style.background = "#00c853";
              }}
            }});

            document.getElementById('volL1').addEventListener('input', (e) => {{
              if (bassSynth) bassSynth.volume.value = parseFloat(e.target.value);
            }});

            document.getElementById('volL2').addEventListener('input', (e) => {{
              if (leadSynth) leadSynth.volume.value = parseFloat(e.target.value);
            }});

            document.getElementById('filterL1').addEventListener('input', (e) => {{
              if (filterL1) filterL1.frequency.value = parseFloat(e.target.value);
            }});

            document.getElementById('reverbL2').addEventListener('input', (e) => {{
              if (reverb) reverb.wet.value = parseFloat(e.target.value);
            }});

            document.getElementById('bpm').addEventListener('input', (e) => {{
              Tone.Transport.bpm.value = parseFloat(e.target.value);
            }});
          </script>
        </body>
        </html>
        """
        components.html(html_code, height=480)
    else:
        st.info("👈 Carga un video para que OpenCV extraiga los movimientos de fondo y frente.")

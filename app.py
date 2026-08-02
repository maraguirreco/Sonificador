import streamlit as st
import cv2
import numpy as np
import tempfile
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="Sonificador Multicapa Pro", page_icon="🎛️", layout="wide")

st.title("🍃 Sonificador de Movimiento Multicapa + Consola Pro")
st.write("Escanea capas de movimiento y controla la mezcla en tiempo real con barra de transporte y efectos avanzados.")

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
    
    layer1_notes = [] 
    layer2_notes = [] 
    
    frame_count = 0
    max_frames = 150
    
    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(prev_gray, gray)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = [c for c in contours if cv2.contourArea(c) > 50]
        
        if valid_contours:
            valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)
            
            # CAPA 1: Movimiento grande (Fondo)
            c1 = valid_contours[0]
            M1 = cv2.moments(c1)
            if M1["m00"] != 0:
                cy1 = int(M1["m01"] / M1["m00"])
                norm_y1 = 1.0 - (cy1 / height)
                idx1 = int(norm_y1 * (len(BASS_SCALE) - 1))
                layer1_notes.append(BASS_SCALE[idx1])
            
            # CAPA 2: Movimiento pequeño (Detalle)
            if len(valid_contours) > 1:
                c2 = valid_contours[1]
                M2 = cv2.moments(c2)
                if M2["m00"] != 0:
                    cy2 = int(M2["m01"] / M2["m00"])
                    norm_y2 = 1.0 - (cy2 / height)
                    idx2 = int(norm_y2 * (len(LEAD_SCALE) - 1))
                    layer2_notes.append(LEAD_SCALE[idx2])
            else:
                layer2_notes.append(LEAD_SCALE[0])

        prev_gray = gray
        frame_count += 1
        
    cap.release()
    return {"layer1": layer1_notes, "layer2": layer2_notes}, None

col_vid, col_synth = st.columns([1, 1.3])

with col_vid:
    video_file = st.file_uploader("Sube un video (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
    if video_file:
        st.video(video_file)
        if st.button("🔍 Escanear Subcapas de Movimiento"):
            with st.spinner("Analizando física del video en múltiples capas..."):
                tfile = tempfile.NamedTemporaryFile(delete=False)
                tfile.write(video_file.read())
                
                layers, error = process_video_motion_layers(tfile.name)
                if error:
                    st.error(error)
                else:
                    l1 = [layers['layer1'][0]] if layers['layer1'] else ['C2']
                    for n in layers['layer1'][1:]:
                        if n != l1[-1]: l1.append(n)
                        
                    l2 = [layers['layer2'][0]] if layers['layer2'] else ['C4']
                    for n in layers['layer2'][1:]:
                        if n != l2[-1]: l2.append(n)

                    st.session_state['layers_data'] = {"layer1": l1, "layer2": l2}
                    st.success("¡Subcapas analizadas con éxito!")

with col_synth:
    if st.session_state['layers_data']['layer1']:
        st.markdown("### 🎛️ Consola Pro + Reproductor Interactivo")
        
        l1_json = json.dumps(st.session_state['layers_data']['layer1'])
        l2_json = json.dumps(st.session_state['layers_data']['layer2'])

        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <script src="https://cdnjs.cloudflare.com/ajax/libs/tone/14.8.49/Tone.js"></script>
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0e1117; color: #fff; margin: 0; padding: 5px; }}
            .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; }}
            .btn-play {{ background: #00c853; color: white; border: none; padding: 12px; font-size: 15px; font-weight: bold; border-radius: 8px; cursor: pointer; width: 100%; margin-bottom: 12px; transition: 0.2s; }}
            .btn-play:hover {{ background: #00e676; }}
            
            .scrubber-container {{ background: #21262d; border: 1px solid #ff4b4b; padding: 10px 14px; border-radius: 8px; margin-bottom: 15px; }}
            .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }}
            .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
            
            label {{ display: block; font-size: 11px; color: #8b949e; margin-bottom: 4px; font-weight: bold; }}
            input[type=range], select {{ width: 100%; background: #0d1117; color: #fff; border: 1px solid #30363d; padding: 6px; border-radius: 6px; box-sizing: border-box; }}
            .layer-box {{ background: #1c2128; border: 1px solid #2d333b; padding: 12px; border-radius: 8px; margin-bottom: 12px; }}
            .badge {{ float: right; color: #58a6ff; font-weight: bold; }}
          </style>
        </head>
        <body>
          <div class="card">
            <button id="playBtn" class="btn-play">▶️ Iniciar Reproducción en Vivo</button>
            
            <!-- BARRA DE NAVEGACIÓN / PROGRESO (SCRUBBER) -->
            <div class="scrubber-container">
              <label>⏱️ Posición de Audio (Haz clic o arrastra para devolver/adelantar) <span id="progText" class="badge">0%</span></label>
              <input type="range" id="scrubber" min="0" max="1" step="0.001" value="0">
            </div>

            <!-- CAPA 1 -->
            <div class="layer-box">
              <span style="color:#58a6ff; font-weight:bold; font-size: 13px;">🎹 Capa 1: Bajo / Acompañamiento</span>
              <div class="grid-3" style="margin-top:8px;">
                <div>
                  <label>Volumen</label>
                  <input type="range" id="volL1" min="-30" max="6" value="0">
                </div>
                <div>
                  <label>Filtro Paso-Bajo</label>
                  <input type="range" id="filterL1" min="100" max="2500" value="700">
                </div>
                <div>
                  <label>Transposición</label>
                  <input type="range" id="pitchL1" min="-12" max="12" value="0">
                </div>
              </div>
            </div>

            <!-- CAPA 2 -->
            <div class="layer-box">
              <span style="color:#2ea043; font-weight:bold; font-size: 13px;">🎵 Capa 2: Melodía Principal</span>
              <div class="grid-3" style="margin-top:8px;">
                <div>
                  <label>Volumen</label>
                  <input type="range" id="volL2" min="-30" max="6" value="-2">
                </div>
                <div>
                  <label>Panorama (L / R)</label>
                  <input type="range" id="panL2" min="-1" max="1" step="0.1" value="0">
                </div>
                <div>
                  <label>Ataque (Soft/Pluck)</label>
                  <input type="range" id="attackL2" min="0.01" max="0.5" step="0.01" value="0.02">
                </div>
              </div>
            </div>

            <!-- EFECTOS MASTER -->
            <div class="layer-box" style="border-color: #d2a8ff;">
              <span style="color:#d2a8ff; font-weight:bold; font-size: 13px;">✨ Procesador Master de Efectos</span>
              <div class="grid-3" style="margin-top:8px;">
                <div>
                  <label>🌌 Reverb Espacial</label>
                  <input type="range" id="reverbWet" min="0" max="0.9" step="0.05" value="0.3">
                </div>
                <div>
                  <label>📻 Delay / Eco</label>
                  <input type="range" id="delayWet" min="0" max="0.8" step="0.05" value="0.2">
                </div>
                <div>
                  <label>🔥 Distorsión Cálida</label>
                  <input type="range" id="distWet" min="0" max="0.8" step="0.05" value="0">
                </div>
              </div>
            </div>

            <div class="grid-2">
              <div>
                <label>⏱️ Tempo Global (BPM) <span id="bpmVal" class="badge">100</span></label>
                <input type="range" id="bpm" min="50" max="180" value="100">
              </div>
            </div>
          </div>

          <script>
            const layer1Notes = {l1_json};
            const layer2Notes = {l2_json};
            const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

            let isPlaying = false;
            let bassSynth, leadSynth, pannerL2;
            let reverb, delay, distortion, filterL1;
            let seq1, seq2;
            let maxSequenceSteps = Math.max(layer1Notes.length * 2, layer2Notes.length);

            function transposeNote(noteStr, semitones) {{
              if (!noteStr) return noteStr;
              let name = noteStr.slice(0, -1);
              let octave = parseInt(noteStr.slice(-1));
              let idx = noteNames.indexOf(name);
              if (idx === -1) return noteStr;

              let totalMidi = (octave + 1) * 12 + idx + semitones;
              let newOctave = Math.floor(totalMidi / 12) - 1;
              let newIdx = (totalMidi % 12 + 12) % 12;
              return noteNames[newIdx] + newOctave;
            }}

            async function initAudio() {{
              await Tone.start();

              // EFECTOS MASTER
              reverb = new Tone.Reverb({{ decay: 3.5, wet: 0.3 }}).toDestination();
              await reverb.generate();

              delay = new Tone.FeedbackDelay({{ delayTime: "8n.", feedback: 0.3, wet: 0.2 }}).connect(reverb);
              distortion = new Tone.Distortion({{ distortion: 0.4, wet: 0 }}).connect(delay);

              // CANAL CAPA 1
              filterL1 = new Tone.Filter(700, "lowpass").connect(distortion);
              bassSynth = new Tone.MonoSynth({{
                oscillator: {{ type: "sawtooth" }},
                envelope: {{ attack: 0.1, decay: 0.4, sustain: 0.8, release: 1.2 }}
              }}).connect(filterL1);

              // CANAL CAPA 2
              pannerL2 = new Tone.Panner(0).connect(distortion);
              leadSynth = new Tone.PolySynth(Tone.Synth, {{
                oscillator: {{ type: "triangle" }},
                envelope: {{ attack: 0.02, decay: 0.2, sustain: 0.3, release: 0.8 }}
              }}).connect(pannerL2);

              // SECUENCIAS
              seq1 = new Tone.Sequence((time, note) => {{
                let shift = parseInt(document.getElementById('pitchL1').value);
                let shiftedNote = transposeNote(note, shift);
                bassSynth.triggerAttackRelease(shiftedNote, "2n", time);
              }}, layer1Notes, "2n");

              seq2 = new Tone.Sequence((time, note) => {{
                leadSynth.triggerAttackRelease(note, "8n", time);
              }}, layer2Notes, "4n");

              Tone.Transport.bpm.value = parseFloat(document.getElementById('bpm').value);
              
              // BUCLE Y NAVEGACIÓN
              Tone.Transport.loop = true;
              Tone.Transport.loopStart = 0;
              Tone.Transport.loopEnd = Tone.Time("4n").toSeconds() * layer2Notes.length;
            }}

            // ACTUALIZACIÓN DE BARRA DE PROGRESO EN VIVO
            function updateScrubber() {{
              if (isPlaying && Tone.Transport.state === "started") {{
                let progress = Tone.Transport.progress;
                if (!isNaN(progress)) {{
                  document.getElementById('scrubber').value = progress;
                  document.getElementById('progText').innerText = Math.round(progress * 100) + "%";
                }}
              }}
              requestAnimationFrame(updateScrubber);
            }}
            requestAnimationFrame(updateScrubber);

            // CONTROL DEL SCRUBBER (Navegar / Devolver el audio)
            document.getElementById('scrubber').addEventListener('input', (e) => {{
              if (isPlaying) {{
                Tone.Transport.progress = parseFloat(e.target.value);
              }}
            }});

            document.getElementById('playBtn').addEventListener('click', async () => {{
              if (!isPlaying) {{
                await initAudio();
                Tone.Transport.start();
                seq1.start(0);
                seq2.start(0);
                isPlaying = true;
                document.getElementById('playBtn').innerText = "⏸️ Pausar Reproducción";
                document.getElementById('playBtn').style.background = "#30363d";
              }} else {{
                Tone.Transport.stop();
                if (seq1) seq1.stop();
                if (seq2) seq2.stop();
                isPlaying = false;
                document.getElementById('playBtn').innerText = "▶️ Iniciar Reproducción en Vivo";
                document.getElementById('playBtn').style.background = "#00c853";
              }}
            }});

            // CONTROLES EN TIEMPO REAL
            document.getElementById('volL1').addEventListener('input', (e) => {{ if (bassSynth) bassSynth.volume.value = parseFloat(e.target.value); }});
            document.getElementById('filterL1').addEventListener('input', (e) => {{ if (filterL1) filterL1.frequency.value = parseFloat(e.target.value); }});
            document.getElementById('volL2').addEventListener('input', (e) => {{ if (leadSynth) leadSynth.volume.value = parseFloat(e.target.value); }});
            document.getElementById('panL2').addEventListener('input', (e) => {{ if (pannerL2) pannerL2.pan.value = parseFloat(e.target.value); }});
            document.getElementById('attackL2').addEventListener('input', (e) => {{
              if (leadSynth) leadSynth.set({{ envelope: {{ attack: parseFloat(e.target.value) }} }});
            }});

            document.getElementById('reverbWet').addEventListener('input', (e) => {{ if (reverb) reverb.wet.value = parseFloat(e.target.value); }});
            document.getElementById('delayWet').addEventListener('input', (e) => {{ if (delay) delay.wet.value = parseFloat(e.target.value); }});
            document.getElementById('distWet').addEventListener('input', (e) => {{ if (distortion) distortion.wet.value = parseFloat(e.target.value); }});
            document.getElementById('bpm').addEventListener('input', (e) => {{
              document.getElementById('bpmVal').innerText = e.target.value;
              Tone.Transport.bpm.value = parseFloat(e.target.value);
            }});
          </script>
        </body>
        </html>
        """
        components.html(html_code, height=560)
    else:
        st.info("👈 Sube un video y presiona 'Escanear Subcapas' para activar la consola.")

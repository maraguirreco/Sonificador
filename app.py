import streamlit as st
import cv2
import numpy as np
import tempfile
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="OP-1 Dynamic Layers", page_icon="🎼", layout="wide")

st.title("🍃 Motion Synth // Dynamic Layer Engine")
st.write("Detecta automáticamente cuántas capas de movimiento existen en tu video y controla su activación en tiempo real.")

if 'dynamic_layers' not in st.session_state:
    st.session_state['dynamic_layers'] = []

# Registros de notas por capa (de grave a agudo)
SCALES = [
    ['C2', 'E2', 'G2', 'A2', 'B2', 'C3'],            # Capa 1: Bajo / Sub
    ['C3', 'D3', 'E3', 'G3', 'A3', 'C4'],            # Capa 2: Armonía Media
    ['C4', 'D4', 'E4', 'G4', 'A4', 'C5'],            # Capa 3: Melodía Principal
    ['C5', 'D5', 'E5', 'G5', 'A5', 'C6']             # Capa 4: Brillos / Texturas
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
        # Filtrar contornos significativos
        valid_contours = [c for c in contours if cv2.contourArea(c) > 40]
        
        if valid_contours:
            # Ordenar por tamaño de movimiento (mayor a menor)
            valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)
            
            frame_notes = []
            # Procesar hasta un máximo de 4 capas si existen
            for idx, c in enumerate(valid_contours[:4]):
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

    # Determinar cuántas capas máximas se detectaron
    max_detected_layers = max(len(f) for f in raw_layers_data)
    
    # Organizar notas por capas individuales
    structured_layers = []
    for layer_idx in range(max_detected_layers):
        layer_notes = []
        for frame in raw_layers_data:
            if len(frame) > layer_idx:
                layer_notes.append(frame[layer_idx])
        
        # Eliminar duplicados consecutivos
        clean_notes = [layer_notes[0]] if layer_notes else ['C3']
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
    video_file = st.file_uploader("Sube un video (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
    if video_file:
        st.video(video_file)
        if st.button("🔍 Escanear Capas Dinámicas"):
            with st.spinner("Analizando cuántas subcapas de movimiento existen..."):
                tfile = tempfile.NamedTemporaryFile(delete=False)
                tfile.write(video_file.read())
                
                layers, error = process_dynamic_motion_layers(tfile.name)
                if error:
                    st.error(error)
                else:
                    st.session_state['dynamic_layers'] = layers
                    st.success(f"¡Éxito! Se detectaron {len(layers)} subcapas de movimiento.")

with col_synth:
    if st.session_state['dynamic_layers']:
        st.markdown(f"### 🎛️ OP-1 Mixer ({len(st.session_state['dynamic_layers'])} Capas Activas)")
        
        layers_json = json.dumps(st.session_state['dynamic_layers'])

        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <script src="https://cdnjs.cloudflare.com/ajax/libs/tone/14.8.49/Tone.js"></script>
          <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap');
            body {{ font-family: 'Space Mono', monospace; background: #0e1117; color: #fff; margin: 0; padding: 5px; }}
            
            .op1-chassis {{
              background: #e1e3e6;
              border: 2px solid #b8bac0;
              border-radius: 16px;
              padding: 18px;
              box-shadow: inset 0 1px 3px rgba(255,255,255,0.9), 0 8px 25px rgba(0,0,0,0.5);
              color: #222;
            }}

            .op1-screen {{
              background: #0d0f12;
              border: 3px solid #22252a;
              border-radius: 8px;
              padding: 12px;
              color: #00ffcc;
              margin-bottom: 14px;
            }}

            .layer-matrix {{
              display: grid;
              grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
              gap: 8px;
              margin-bottom: 15px;
            }}

            .btn-layer-toggle {{
              background: #00e676;
              color: #000;
              border: none;
              border-bottom: 3px solid #00a152;
              padding: 10px 4px;
              font-family: 'Space Mono', monospace;
              font-size: 10px;
              font-weight: bold;
              border-radius: 6px;
              cursor: pointer;
              text-align: center;
              transition: all 0.1s;
            }}

            .btn-layer-toggle.muted {{
              background: #444b54;
              color: #888;
              border-bottom-color: #222;
            }}

            .btn-action {{
              background: #ffffff;
              border: 1px solid #ccc;
              border-bottom: 3px solid #aaa;
              padding: 12px;
              font-family: 'Space Mono', monospace;
              font-size: 12px;
              font-weight: bold;
              border-radius: 6px;
              cursor: pointer;
              width: 100%;
            }}

            .btn-play-active {{
              background: #ff0055 !important;
              color: white !important;
              border-bottom-color: #990033 !important;
            }}

            .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }}
            label {{ font-size: 9px; color: #555; font-weight: bold; display: block; }}
            input[type=range] {{ width: 100%; accent-color: #222; }}
          </style>
        </head>
        <body>

          <div class="op1-chassis">
            <div style="font-size: 10px; font-weight: bold; color: #777; margin-bottom: 8px;">
              TE-OP-PYTHON // DYNAMIC MULTI-TRACK MATRIX
            </div>

            <!-- PANTALLA OLED -->
            <div class="op1-screen">
              <div style="font-size: 10px; color: #ff0055; margin-bottom: 6px;">
                STATUS: <span id="screenStatus">STOPPED</span> | DETECTED LAYERS: {len(st.session_state['dynamic_layers'])}
              </div>
              <div id="screenLayersDisplay" style="font-size: 11px; color: #00ffcc;">
                [PLAY para iniciar motor de sonido]
              </div>
            </div>

            <!-- MATRIZ DE CONTROL DE CAPAS (MUTE / UNMUTE) -->
            <div style="font-size: 9px; font-weight: bold; color: #444; margin-bottom: 6px;">
              ACTIVAR / DESACTIVAR CAPAS EN VIVO:
            </div>
            <div id="layerMatrix" class="layer-matrix">
              <!-- Se genera dinámicamente según las capas del video -->
            </div>

            <!-- CONTROLES MASTER -->
            <div class="grid-2" style="background:#f0f1f3; padding:10px; border-radius:8px; margin-bottom:15px;">
              <div>
                <label>⏱️ TEMPO (BPM)</label>
                <input type="range" id="bpm" min="50" max="180" value="100">
              </div>
              <div>
                <label>🌌 REVERB MASTER</label>
                <input type="range" id="reverbWet" min="0" max="0.9" step="0.05" value="0.3">
              </div>
            </div>

            <button id="playBtn" class="btn-action">▶️ PLAY MULTI-TRACK TAPE</button>
          </div>

          <script>
            const layersData = {layers_json};
            let isPlaying = false;
            let synths = [];
            let sequences = [];
            let layerStates = {{}}; // <--- ¡AQUÍ ESTABA EL ERROR (CORREGIDO)!
            let reverb;

            // Renderizar botones de la matriz de capas dinámicamente
            const matrixDiv = document.getElementById('layerMatrix');
            layersData.forEach((layer, idx) => {{
              layerStates[idx] = true; // Activas por defecto
              
              const btn = document.createElement('button');
              btn.className = 'btn-layer-toggle';
              btn.id = `btnLayer_${{idx}}`;
              btn.innerText = `ON // ${{layer.name}}`;
              
              btn.onclick = () => toggleLayer(idx);
              matrixDiv.appendChild(btn);
            }});

            function toggleLayer(idx) {{
              layerStates[idx] = !layerStates[idx];
              const btn = document.getElementById(`btnLayer_${{idx}}`);
              
              if (layerStates[idx]) {{
                btn.className = 'btn-layer-toggle';
                btn.innerText = `ON // Capa ${{idx + 1}}`;
                if (synths[idx]) synths[idx].volume.value = 0;
              }} else {{
                btn.className = 'btn-layer-toggle muted';
                btn.innerText = `OFF // Capa ${{idx + 1}}`;
                if (synths[idx]) synths[idx].volume.value = -Infinity; // Silenciar
              }}
              updateScreenDisplay();
            }}

            function updateScreenDisplay() {{
              let activeStr = layersData.map((l, i) => 
                `L${{i+1}}:${{layerStates[i] ? 'ON' : 'OFF'}}`
              ).join(' | ');
              document.getElementById('screenLayersDisplay').innerText = activeStr;
            }}

            async function initAudioEngine() {{
              await Tone.start();

              reverb = new Tone.Reverb({{ decay: 3.5, wet: 0.3 }}).toDestination();
              await reverb.generate();

              synths = [];
              sequences = [];

              layersData.forEach((layer, idx) => {{
                // Asignar timbres diferentes según la profundidad de la capa
                let synth;
                if (idx === 0) {{
                  synth = new Tone.MonoSynth({{
                    oscillator: {{ type: "sawtooth" }},
                    envelope: {{ attack: 0.1, decay: 0.3, sustain: 0.8, release: 1 }}
                  }}).connect(reverb);
                }} else if (idx === 1) {{
                  synth = new Tone.PolySynth(Tone.Synth, {{
                    oscillator: {{ type: "triangle" }}
                  }}).connect(reverb);
                }} else {{
                  synth = new Tone.PolySynth(Tone.Synth, {{
                    oscillator: {{ type: "sine" }},
                    envelope: {{ attack: 0.01, decay: 0.2, sustain: 0.2, release: 0.5 }}
                  }}).connect(reverb);
                }}

                if (!layerStates[idx]) {{
                  synth.volume.value = -Infinity;
                }}

                synths.push(synth);

                let rate = idx === 0 ? "2n" : (idx === 1 ? "4n" : "8n");
                let seq = new Tone.Sequence((time, note) => {{
                  synth.triggerAttackRelease(note, rate, time);
                }}, layer.notes, rate);

                sequences.push(seq);
              }});

              Tone.Transport.bpm.value = parseFloat(document.getElementById('bpm').value);
              Tone.Transport.loop = true;
              Tone.Transport.loopStart = 0;
              Tone.Transport.loopEnd = Tone.Time("2n").toSeconds() * 8;
            }}

            document.getElementById('playBtn').addEventListener('click', async () => {{
              if (!isPlaying) {{
                await initAudioEngine();
                Tone.Transport.start();
                sequences.forEach(s => s.start(0));
                isPlaying = true;
                document.getElementById('playBtn').classList.add('btn-play-active');
                document.getElementById('playBtn').innerText = "⏸️ STOP TAPE";
                document.getElementById('screenStatus').innerText = "PLAYING";
                updateScreenDisplay();
              }} else {{
                Tone.Transport.stop();
                sequences.forEach(s => s.stop());
                isPlaying = false;
                document.getElementById('playBtn').classList.remove('btn-play-active');
                document.getElementById('playBtn').innerText = "▶️ PLAY MULTI-TRACK TAPE";
                document.getElementById('screenStatus').innerText = "STOPPED";
              }}
            }});

            document.getElementById('bpm').addEventListener('input', (e) => {{
              Tone.Transport.bpm.value = parseFloat(e.target.value);
            }});

            document.getElementById('reverbWet').addEventListener('input', (e) => {{
              if (reverb) reverb.wet.value = parseFloat(e.target.value);
            }});
          </script>
        </body>
        </html>
        """
        components.html(html_code, height=480)
    else:
        st.info("👈 Carga un video para que OpenCV extraiga las subcapas dinámicas automáticamente.")

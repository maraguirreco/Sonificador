import streamlit as st
import cv2
import numpy as np
import tempfile
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="Motion OP-1 Synth", page_icon="🎹", layout="wide")

st.title("🍃 Motion Synth // OP-1 Edition")
st.write("Sonificador de movimiento inspirado en la interfaz del sintetizador Teenage Engineering OP-1.")

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
    
    layer1_notes, layer2_notes = [], []
    frame_count, max_frames = 0, 150
    
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
            
            c1 = valid_contours[0]
            M1 = cv2.moments(c1)
            if M1["m00"] != 0:
                cy1 = int(M1["m01"] / M1["m00"])
                norm_y1 = 1.0 - (cy1 / height)
                idx1 = int(norm_y1 * (len(BASS_SCALE) - 1))
                layer1_notes.append(BASS_SCALE[idx1])
            
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
    video_file = st.file_uploader("Carga tu video aquí (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
    if video_file:
        st.video(video_file)
        if st.button("🔍 Mapear Movimiento a OP-1"):
            with st.spinner("Procesando física del video para el motor OP-1..."):
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
                    st.success("¡Datos cargados en la memoria del OP-1!")

with col_synth:
    if st.session_state['layers_data']['layer1']:
        l1_json = json.dumps(st.session_state['layers_data']['layer1'])
        l2_json = json.dumps(st.session_state['layers_data']['layer2'])

        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <script src="https://cdnjs.cloudflare.com/ajax/libs/tone/14.8.49/Tone.js"></script>
          <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap');
            
            body {{
              font-family: 'Space Mono', monospace;
              background: #0e1117;
              color: #222;
              margin: 0;
              padding: 5px;
            }}

            /* OP-1 CHASSIS */
            .op1-chassis {{
              background: #e3e4e6;
              border: 2px solid #c8c9cc;
              border-radius: 16px;
              padding: 20px;
              box-shadow: inset 0 1px 3px rgba(255,255,255,0.8), 0 8px 20px rgba(0,0,0,0.4);
            }}

            .op1-header {{
              display: flex;
              justify-content: space-between;
              align-items: center;
              font-size: 11px;
              font-weight: 700;
              color: #77787b;
              margin-bottom: 12px;
              letter-spacing: 1px;
            }}

            /* OP-1 OLED SCREEN */
            .op1-screen {{
              background: #111317;
              border: 3px solid #2a2d32;
              border-radius: 8px;
              padding: 15px;
              color: #00ffcc;
              margin-bottom: 18px;
              box-shadow: inset 0 0 10px rgba(0,0,0,0.8);
            }}

            .screen-status {{
              display: flex;
              justify-content: space-between;
              font-size: 11px;
              color: #ff0055;
              border-bottom: 1px solid #222;
              padding-bottom: 6px;
              margin-bottom: 10px;
            }}

            .screen-tape {{
              display: flex;
              align-items: center;
              gap: 10px;
              margin-top: 8px;
            }}

            .tape-line {{
              flex-grow: 1;
              height: 4px;
              background: #222;
              border-radius: 2px;
              position: relative;
              overflow: hidden;
            }}

            .tape-fill {{
              height: 100%;
              width: 0%;
              background: #00ffcc;
              box-shadow: 0 0 8px #00ffcc;
            }}

            /* 4 COLORED ENCODERS GRID */
            .encoders-grid {{
              display: grid;
              grid-template-columns: repeat(4, 1fr);
              gap: 12px;
              margin-bottom: 18px;
            }}

            .encoder-card {{
              background: #f0f1f3;
              border-radius: 10px;
              padding: 12px 8px;
              border-top: 6px solid #888;
              box-shadow: 0 2px 5px rgba(0,0,0,0.08);
            }}

            .encoder-card.blue {{ border-top-color: #0088ff; }}
            .encoder-card.green {{ border-top-color: #00e676; }}
            .encoder-card.white {{ border-top-color: #ffffff; }}
            .encoder-card.orange {{ border-top-color: #ff5252; }}

            .encoder-title {{
              font-size: 10px;
              font-weight: bold;
              text-transform: uppercase;
              margin-bottom: 8px;
              color: #444;
            }}

            label {{ display: block; font-size: 9px; color: #666; margin-top: 6px; font-weight: bold; }}
            input[type=range] {{ width: 100%; accent-color: #333; margin: 2px 0; }}

            /* OP-1 BUTTONS */
            .btn-op1 {{
              background: #f7f7f8;
              color: #222;
              border: 1px solid #ccc;
              border-bottom: 4px solid #b5b6b8;
              padding: 12px;
              font-family: 'Space Mono', monospace;
              font-size: 13px;
              font-weight: bold;
              border-radius: 8px;
              cursor: pointer;
              width: 100%;
              transition: all 0.1s;
            }}

            .btn-op1:active {{
              border-bottom: 1px solid #b5b6b8;
              transform: translateY(3px);
            }}

            .btn-play-active {{
              background: #ff5252;
              color: white;
              border-color: #d32f2f;
              border-bottom-color: #9a0007;
            }}
          </style>
        </head>
        <body>

          <div class="op1-chassis">
            <div class="op1-header">
              <span>TE-OP-PYTHON // MOTION SYNTH</span>
              <span>SYNTH • TAPE • FX</span>
            </div>

            <!-- PANTALLA OLED OP-1 -->
            <div class="op1-screen">
              <div class="screen-status">
                <span id="screenMode">STATUS: READY</span>
                <span id="screenBpm">BPM: 100</span>
              </div>
              <div style="font-size: 13px; color: #fff;">
                <span style="color: #0088ff;">L1:</span> <span id="noteL1">C2</span> | 
                <span style="color: #00e676;">L2:</span> <span id="noteL2">C4</span>
              </div>
              <div class="screen-tape">
                <span style="font-size: 9px; color: #888;">TAPE</span>
                <div class="tape-line">
                  <div id="tapeFill" class="tape-fill"></div>
                </div>
                <input type="range" id="scrubber" min="0" max="1" step="0.001" value="0" style="width: 60px;">
              </div>
            </div>

            <!-- BOTÓN PRINCIPAL REPRODUCCIÓN -->
            <button id="playBtn" class="btn-op1" style="margin-bottom: 15px;">▶️ PLAY / REC TAPE</button>

            <!-- 4 CODIFICADORES DE COLORES OP-1 -->
            <div class="encoders-grid">
              
              <!-- 🔵 BLUE ENCODER -->
              <div class="encoder-card blue">
                <div class="encoder-title" style="color: #0088ff;">🔵 TUNE & CUT</div>
                <label>PITCH L1</label>
                <input type="range" id="pitchL1" min="-12" max="12" value="0">
                <label>FILTER HZ</label>
                <input type="range" id="filterL1" min="100" max="3000" value="800">
              </div>

              <!-- 🟢 GREEN ENCODER -->
              <div class="encoder-card green">
                <div class="encoder-title" style="color: #00c853;">🟢 MIX & ATTACK</div>
                <label>VOL L2</label>
                <input type="range" id="volL2" min="-30" max="6" value="-2">
                <label>ATTACK</label>
                <input type="range" id="attackL2" min="0.01" max="0.5" step="0.01" value="0.02">
              </div>

              <!-- ⚪ WHITE ENCODER -->
              <div class="encoder-card white">
                <div class="encoder-title" style="color: #555;">⚪ TAPE & TEMPO</div>
                <label>TEMPO BPM</label>
                <input type="range" id="bpm" min="50" max="180" value="100">
                <label>VOL L1</label>
                <input type="range" id="volL1" min="-30" max="6" value="0">
              </div>

              <!-- 🟠 ORANGE ENCODER -->
              <div class="encoder-card orange">
                <div class="encoder-title" style="color: #ff5252;">🟠 MASTER FX</div>
                <label>REVERB</label>
                <input type="range" id="reverbWet" min="0" max="0.9" step="0.05" value="0.3">
                <label>DELAY</label>
                <input type="range" id="delayWet" min="0" max="0.8" step="0.05" value="0.2">
              </div>

            </div>
          </div>

          <script>
            const layer1Notes = {l1_json};
            const layer2Notes = {l2_json};
            const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

            let isPlaying = false;
            let bassSynth, leadSynth, reverb, delay, filterL1;
            let seq1, seq2;

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

              reverb = new Tone.Reverb({{ decay: 3.5, wet: 0.3 }}).toDestination();
              await reverb.generate();

              delay = new Tone.FeedbackDelay({{ delayTime: "8n.", feedback: 0.3, wet: 0.2 }}).connect(reverb);
              filterL1 = new Tone.Filter(800, "lowpass").connect(delay);

              bassSynth = new Tone.MonoSynth({{
                oscillator: {{ type: "sawtooth" }},
                envelope: {{ attack: 0.1, decay: 0.4, sustain: 0.8, release: 1.2 }}
              }}).connect(filterL1);

              leadSynth = new Tone.PolySynth(Tone.Synth, {{
                oscillator: {{ type: "triangle" }},
                envelope: {{ attack: 0.02, decay: 0.2, sustain: 0.3, release: 0.8 }}
              }}).connect(delay);

              seq1 = new Tone.Sequence((time, note) => {{
                let shift = parseInt(document.getElementById('pitchL1').value);
                let shifted = transposeNote(note, shift);
                bassSynth.triggerAttackRelease(shifted, "2n", time);
                document.getElementById('noteL1').innerText = shifted;
              }}, layer1Notes, "2n");

              seq2 = new Tone.Sequence((time, note) => {{
                leadSynth.triggerAttackRelease(note, "8n", time);
                document.getElementById('noteL2').innerText = note;
              }}, layer2Notes, "4n");

              Tone.Transport.bpm.value = parseFloat(document.getElementById('bpm').value);
              Tone.Transport.loop = true;
              Tone.Transport.loopStart = 0;
              Tone.Transport.loopEnd = Tone.Time("4n").toSeconds() * layer2Notes.length;
            }}

            function updateTapeUI() {{
              if (isPlaying && Tone.Transport.state === "started") {{
                let prog = Tone.Transport.progress;
                if (!isNaN(prog)) {{
                  document.getElementById('tapeFill').style.width = (prog * 100) + "%";
                  document.getElementById('scrubber').value = prog;
                }}
              }}
              requestAnimationFrame(updateTapeUI);
            }}
            requestAnimationFrame(updateTapeUI);

            document.getElementById('scrubber').addEventListener('input', (e) => {{
              if (isPlaying) Tone.Transport.progress = parseFloat(e.target.value);
            }});

            document.getElementById('playBtn').addEventListener('click', async () => {{
              if (!isPlaying) {{
                await initAudio();
                Tone.Transport.start();
                seq1.start(0);
                seq2.start(0);
                isPlaying = true;
                document.getElementById('playBtn').innerText = "⏸️ STOP TAPE";
                document.getElementById('playBtn').classList.add('btn-play-active');
                document.getElementById('screenMode').innerText = "STATUS: PLAYING";
              }} else {{
                Tone.Transport.stop();
                if (seq1) seq1.stop();
                if (seq2) seq2.stop();
                isPlaying = false;
                document.getElementById('playBtn').innerText = "▶️ PLAY / REC TAPE";
                document.getElementById('playBtn').classList.remove('btn-play-active');
                document.getElementById('screenMode').innerText = "STATUS: PAUSED";
              }}
            }});

            // CONTROLES DE ENCODERS
            document.getElementById('pitchL1').addEventListener('input', (e) => {{}});
            document.getElementById('filterL1').addEventListener('input', (e) => {{ if (filterL1) filterL1.frequency.value = parseFloat(e.target.value); }});
            document.getElementById('volL2').addEventListener('input', (e) => {{ if (leadSynth) leadSynth.volume.value = parseFloat(e.target.value); }});
            document.getElementById('attackL2').addEventListener('input', (e) => {{ if (leadSynth) leadSynth.set({{ envelope: {{ attack: parseFloat(e.target.value) }} }}); }});
            document.getElementById('volL1').addEventListener('input', (e) => {{ if (bassSynth) bassSynth.volume.value = parseFloat(e.target.value); }});
            document.getElementById('reverbWet').addEventListener('input', (e) => {{ if (reverb) reverb.wet.value = parseFloat(e.target.value); }});
            document.getElementById('delayWet').addEventListener('input', (e) => {{ if (delay) delay.wet.value = parseFloat(e.target.value); }});
            document.getElementById('bpm').addEventListener('input', (e) => {{
              document.getElementById('screenBpm').innerText = "BPM: " + e.target.value;
              Tone.Transport.bpm.value = parseFloat(e.target.value);
            }});
          </script>
        </body>
        </html>
        """
        components.html(html_code, height=480)
    else:
        st.info("👈 Sube un video para enviar los datos de movimiento al motor OP-1.")

import streamlit as st
import cv2
import numpy as np
import tempfile
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="Sonificador en Tiempo Real", page_icon="🎛️", layout="wide")

st.title("🍃 Sonificador de Movimiento + Sintetizador en Tiempo Real")
st.write("Sube un video para extraer su melodía y modula el sonido en tiempo real mientras el bucle está sonando.")

# Inicializar estado para guardar la melodía analizada
if 'melody_notes' not in st.session_state:
    st.session_state['melody_notes'] = []

# Escala Pentatónica Mayor de Do
PENTATONIC_SCALE = ['C4', 'D4', 'E4', 'G4', 'A4', 'C5', 'D5', 'E5', 'G5', 'A5', 'C6']

def process_video_motion(video_path):
    cap = cv2.VideoCapture(video_path)
    ret, prev_frame = cap.read()
    if not ret:
        return None, "No se pudo leer el archivo de video."
    
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    height, _ = prev_gray.shape
    
    detected_events = []
    frame_count = 0
    max_frames = 150  # Analiza aprox. 5 segundos
    
    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(prev_gray, gray)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        moving_pixels = np.where(thresh > 0)
        
        if len(moving_pixels[0]) > 40:
            avg_y = np.mean(moving_pixels[0])
            norm_y = 1.0 - (avg_y / height)
            scale_idx = int(norm_y * (len(PENTATONIC_SCALE) - 1))
            detected_events.append(PENTATONIC_SCALE[scale_idx])
            
        prev_gray = gray
        frame_count += 1
        
    cap.release()
    return detected_events, None

col_vid, col_synth = st.columns([1, 1.2])

with col_vid:
    video_file = st.file_uploader("Sube un video corto (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
    if video_file:
        st.video(video_file)
        if st.button("🔍 Extraer Melodía del Video"):
            with st.spinner("Analizando física del movimiento..."):
                tfile = tempfile.NamedTemporaryFile(delete=False)
                tfile.write(video_file.read())
                
                notes, error = process_video_motion(tfile.name)
                if error:
                    st.error(error)
                elif notes:
                    # Limpiar repeticiones consecutivas
                    melody = [notes[0]]
                    for n in notes[1:]:
                        if n != melody[-1]:
                            melody.append(n)
                    st.session_state['melody_notes'] = melody
                    st.success("¡Melodía extraída correctamente!")

with col_synth:
    if st.session_state['melody_notes']:
        st.markdown("### 🎛️ Sintetizador Interactivo")
        
        notes_js = json.dumps(st.session_state['melody_notes'])
        first_note_base = st.session_state['melody_notes'][0][0]
        
        st.info(f"**Notas extraídas:** {', '.join(st.session_state['melody_notes'])}")
        st.success(f"**Progresión armónica sugerida:** `{first_note_base}maj7` ➔ `{first_note_base}/F` ➔ `G6` ➔ `{first_note_base}`")

        # HTML + JS Web Audio API Component (Tone.js)
        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <script src="https://cdnjs.cloudflare.com/ajax/libs/tone/14.8.49/Tone.js"></script>
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0e1117; color: #ffffff; margin: 0; padding: 10px; }}
            .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; }}
            .btn-play {{ background: #ff4b4b; color: white; border: none; padding: 14px 20px; font-size: 16px; font-weight: bold; border-radius: 8px; cursor: pointer; width: 100%; margin-bottom: 20px; transition: 0.2s; }}
            .btn-play:hover {{ background: #e03e3e; }}
            .control-group {{ margin-bottom: 15px; }}
            label {{ display: block; font-size: 13px; color: #8b949e; margin-bottom: 6px; font-weight: 600; }}
            input[type=range], select {{ width: 100%; background: #0d1117; color: #fff; border: 1px solid #30363d; padding: 10px; border-radius: 6px; box-sizing: border-box; }}
            .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
            .val-badge {{ float: right; color: #58a6ff; font-weight: bold; }}
          </style>
        </head>
        <body>
          <div class="card">
            <button id="playBtn" class="btn-play">▶️ Iniciar Bucle en Tiempo Real</button>
            <div class="grid">
              <div class="control-group">
                <label>🎹 Timbre / Instrumento</label>
                <select id="synthType">
                  <option value="Synth">Marimba / Sintetizador</option>
                  <option value="AMSynth">Folk / Órgano Cálido</option>
                  <option value="FMSynth">Cristalino / Metálico</option>
                  <option value="DuoSynth">Lead / Cósmico</option>
                </select>
              </div>
              <div class="control-group">
                <label>⏱️ Tempo (BPM) <span id="bpmVal" class="val-badge">120</span></label>
                <input type="range" id="bpm" min="50" max="220" value="120">
              </div>
              <div class="control-group">
                <label>🎵 Transposición (Semitonos) <span id="pitchVal" class="val-badge">0</span></label>
                <input type="range" id="pitch" min="-12" max="12" value="0">
              </div>
              <div class="control-group">
                <label>✨ Brillo (Filtro Hz) <span id="filterVal" class="val-badge">3000</span></label>
                <input type="range" id="filter" min="300" max="8000" value="3000">
              </div>
              <div class="control-group" style="grid-column: span 2;">
                <label>🌌 Reverb / Espacialidad <span id="reverbVal" class="val-badge">30%</span></label>
                <input type="range" id="reverb" min="0" max="0.9" step="0.05" value="0.3">
              </div>
            </div>
          </div>

          <script>
            const notes = {notes_js};
            let isPlaying = false;
            let currentSynth, filterNode, reverbNode, sequence;

            const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

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

              filterNode = new Tone.Filter(3000, "lowpass").toDestination();
              reverbNode = new Tone.Reverb({{ decay: 3, wet: 0.3 }}).connect(filterNode);
              await reverbNode.generate();

              createSynth('Synth');

              sequence = new Tone.Sequence((time, note) => {{
                let shift = parseInt(document.getElementById('pitch').value);
                let shiftedNote = transposeNote(note, shift);
                if (currentSynth) {{
                  currentSynth.triggerAttackRelease(shiftedNote, "8n", time);
                }}
              }}, notes, "4n");

              Tone.Transport.bpm.value = parseInt(document.getElementById('bpm').value);
            }}

            function createSynth(type) {{
              if (currentSynth) currentSynth.dispose();

              if (type === 'AMSynth') currentSynth = new Tone.AMSynth().connect(reverbNode);
              else if (type === 'FMSynth') currentSynth = new Tone.FMSynth().connect(reverbNode);
              else if (type === 'DuoSynth') currentSynth = new Tone.DuoSynth().connect(reverbNode);
              else currentSynth = new Tone.Synth({{ envelope: {{ attack: 0.02, decay: 0.3, sustain: 0.2, release: 0.8 }} }}).connect(reverbNode);
            }}

            document.getElementById('playBtn').addEventListener('click', async () => {{
              if (!isPlaying) {{
                await initAudio();
                Tone.Transport.start();
                sequence.start(0);
                isPlaying = true;
                document.getElementById('playBtn').innerText = "⏸️ Pausar Bucle";
                document.getElementById('playBtn').style.background = "#30363d";
              }} else {{
                Tone.Transport.stop();
                if (sequence) sequence.stop();
                isPlaying = false;
                document.getElementById('playBtn').innerText = "▶️ Iniciar Bucle en Tiempo Real";
                document.getElementById('playBtn').style.background = "#ff4b4b";
              }}
            }});

            document.getElementById('synthType').addEventListener('change', (e) => {{
              createSynth(e.target.value);
            }});

            document.getElementById('bpm').addEventListener('input', (e) => {{
              document.getElementById('bpmVal').innerText = e.target.value;
              Tone.Transport.bpm.value = parseFloat(e.target.value);
            }});

            document.getElementById('pitch').addEventListener('input', (e) => {{
              document.getElementById('pitchVal').innerText = e.target.value;
            }});

            document.getElementById('filter').addEventListener('input', (e) => {{
              document.getElementById('filterVal').innerText = e.target.value;
              if (filterNode) filterNode.frequency.value = parseFloat(e.target.value);
            }});

            document.getElementById('reverb').addEventListener('input', (e) => {{
              document.getElementById('reverbVal').innerText = Math.round(e.target.value * 100) + "%";
              if (reverbNode) reverbNode.wet.value = parseFloat(e.target.value);
            }});
          </script>
        </body>
        </html>
        """
        components.html(html_code, height=450)
    else:
        st.info("👈 Carga un video y presiona 'Extraer Melodía del Video' para activar el sintetizador en tiempo real.")

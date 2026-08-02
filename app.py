import streamlit as st
import cv2
import numpy as np
import tempfile
import io
from scipy.io import wavfile

st.set_page_config(page_title="Sonificador de Video", page_icon="🍃")

st.title("🍃 Sonificador de Movimiento en Video")
st.write("Sube un video de la naturaleza (hojas moviéndose, agua, sombras) para traducirlo a melodías y escucharlas al instante.")

video_file = st.file_uploader("Sube un video corto (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])

# Frecuencias en Hertz de la Escala Pentatónica Mayor de Do
NOTE_FREQS = {
    'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'G4': 392.00, 'A4': 440.00,
    'C5': 523.25, 'D5': 587.33, 'E5': 659.25, 'G5': 783.99, 'A5': 880.00,
    'C6': 1046.50
}
PENTATONIC_SCALE = list(NOTE_FREQS.keys())

def synthesize_melody(notes, duration_per_note=0.3, sample_rate=44100):
    """Sintetiza una secuencia de notas en un archivo de audio .wav en memoria."""
    full_wave = []
    
    for note in notes:
        freq = NOTE_FREQS.get(note, 440.0)
        t = np.linspace(0, duration_per_note, int(sample_rate * duration_per_note), False)
        
        # Generación de onda con armónicos (sonido cálido tipo marimba/synth)
        wave = (0.6 * np.sin(2 * np.pi * freq * t) + 
                0.3 * np.sin(2 * np.pi * 2 * freq * t) + 
                0.1 * np.sin(2 * np.pi * 3 * freq * t))
        
        # Envolvente de decaimiento (fade-out suave)
        envelope = np.exp(-4 * t)
        wave = wave * envelope
        
        full_wave.extend(wave)
        
    full_wave = np.array(full_wave)
    # Normalización de audio a 16 bits PCM
    max_val = np.max(np.abs(full_wave))
    if max_val > 0:
        full_wave = (full_wave / max_val * 32767).astype(np.int16)
        
    buffer = io.BytesIO()
    wavfile.write(buffer, sample_rate, full_wave)
    buffer.seek(0)
    return buffer

def process_video_motion(video_path):
    cap = cv2.VideoCapture(video_path)
    ret, prev_frame = cap.read()
    if not ret:
        return None, "No se pudo leer el archivo de video."
    
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    height, width = prev_gray.shape
    
    detected_events = []
    frame_count = 0
    max_frames = 150  # Analiza aprox. 5 segundos de movimiento
    
    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Aislamiento de movimiento
        diff = cv2.absdiff(prev_gray, gray)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        
        moving_pixels = np.where(thresh > 0)
        
        if len(moving_pixels[0]) > 40:
            avg_y = np.mean(moving_pixels[0])
            norm_y = 1.0 - (avg_y / height)
            
            scale_idx = int(norm_y * (len(PENTATONIC_SCALE) - 1))
            note = PENTATONIC_SCALE[scale_idx]
            
            detected_events.append(note)
            
        prev_gray = gray
        frame_count += 1
        
    cap.release()
    return detected_events, None

if video_file:
    st.video(video_file)
    
    if st.button("🎼 Traducir Movimiento a Sonido Directo"):
        with st.spinner("Procesando fotogramas y sintetizando las notas musicales..."):
            tfile = tempfile.NamedTemporaryFile(delete=False)
            tfile.write(video_file.read())
            
            notes, error = process_video_motion(tfile.name)
            
            if error:
                st.error(error)
            elif notes:
                # Filtrar repeticiones consecutivas para una melodía más fluida
                melody_sequence = [notes[0]]
                for n in notes[1:]:
                    if n != melody_sequence[-1]:
                        melody_sequence.append(n)
                
                st.markdown("---")
                st.success("¡Melodía generada con éxito a partir del movimiento!")
                
                # SINTETIZAR AUDIO
                audio_buffer = synthesize_melody(melody_sequence)
                
                st.markdown("### 🔊 Escucha el Resultado Sonoro")
                st.audio(audio_buffer, format="audio/wav")
                
                st.markdown("### 🎹 Secuencia de Notas Traducidas")
                st.info(f"**Notas:** {', '.join(melody_sequence)}")
                
                # Sugerencia de Acordes
                first_note_base = melody_sequence[0][0]
                st.markdown("### 🎶 Progresión Armónica Recomendada")
                st.success(f"`{first_note_base}maj7` ➔ `{first_note_base}/F` ➔ `G6` ➔ `{first_note_base}`")
            else:
                st.warning("No se detectó suficiente movimiento en el video para generar notas.")

import streamlit as st
import cv2
import numpy as np
import tempfile
import io
from scipy.io import wavfile
from scipy.signal import butter, lfilter

st.set_page_config(page_title="Sonificador Interactivo", page_icon="🎛️", layout="wide")

st.title("🍃 Sonificador de Movimiento + Sintetizador")
st.write("Convierte el movimiento de tus videos en música y moldea el sonido con el panel de efectos.")

# --- PANEL DE CONTROL / BARRA LATERAL ---
st.sidebar.header("🎛️ Panel de Efectos de Audio")

timbre_option = st.sidebar.selectbox(
    "🎹 Tipo de Instrumento / Timbre",
    ["Marimba Orgánica", "Teclado Suave", "Synth Retro 8-Bit", "Campanas Místicas"]
)

pitch_shift = st.sidebar.slider("🎵 Transposición de Tono (Semitonos)", -12, 12, 0)
note_duration = st.sidebar.slider("⏱️ Duración por Nota (Segundos)", 0.1, 0.8, 0.3, step=0.05)
reverb_amount = st.sidebar.slider("🌌 Reverb / Espacialidad", 0.0, 0.8, 0.3, step=0.05)
brightness = st.sidebar.slider("✨ Brillo del Sonido (Filtro Hz)", 800, 10000, 4500, step=200)

# Frecuencias en Hertz de la Escala Pentatónica Mayor de Do
NOTE_FREQS = {
    'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'G4': 392.00, 'A4': 440.00,
    'C5': 523.25, 'D5': 587.33, 'E5': 659.25, 'G5': 783.99, 'A5': 880.00,
    'C6': 1046.50
}
PENTATONIC_SCALE = list(NOTE_FREQS.keys())

# --- FUNCIONES DSP (PROCESAMIENTO DIGITAL DE SEÑALES) ---

def apply_lowpass_filter(data, cutoff, fs=44100):
    """Filtro paso-bajo para ajustar el brillo."""
    nyq = 0.5 * fs
    normal_cutoff = min(cutoff / nyq, 0.99)
    b, a = butter(2, normal_cutoff, btype='low', analog=False)
    return lfilter(b, a, data)

def apply_reverb(signal, amount, sample_rate=44100):
    """Efecto de resonancia espacial / eco sintético."""
    if amount <= 0:
        return signal
    delay_samples = int(sample_rate * 0.15)  # Retardo de 150ms
    output = np.copy(signal).astype(np.float32)
    
    for i in range(delay_samples, len(output)):
        output[i] += output[i - delay_samples] * (amount * 0.6)
        
    return output

def synthesize_melody(notes, pitch_shift=0, duration=0.3, timbre="Marimba Orgánica", 
                      reverb=0.3, cutoff_hz=4500, sample_rate=44100):
    """Genera la onda sonora procesada con los controladores elegidos."""
    full_wave = []
    
    for note in notes:
        base_freq = NOTE_FREQS.get(note, 440.0)
        # Aplicar Transposición de Tono: Frecuencia = f * 2^(semitonos/12)
        freq = base_freq * (2 ** (pitch_shift / 12.0))
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Generación según el Timbre seleccionado
        if timbre == "Marimba Orgánica":
            wave = (0.6 * np.sin(2 * np.pi * freq * t) + 
                    0.3 * np.sin(2 * np.pi * 2 * freq * t) + 
                    0.1 * np.sin(2 * np.pi * 3 * freq * t))
            envelope = np.exp(-5 * t)
        elif timbre == "Teclado Suave":
            wave = np.sin(2 * np.pi * freq * t)
            envelope = np.sin(np.pi * t / duration)
        elif timbre == "Synth Retro 8-Bit":
            wave = np.sign(np.sin(2 * np.pi * freq * t))  # Onda cuadrada
            envelope = np.exp(-3 * t)
        elif timbre == "Campanas Místicas":
            wave = (0.5 * np.sin(2 * np.pi * freq * t) + 
                    0.3 * np.sin(2 * np.pi * 2.76 * freq * t) + 
                    0.2 * np.sin(2 * np.pi * 5.4 * freq * t))
            envelope = np.exp(-3 * t)
        else:
            wave = np.sin(2 * np.pi * freq * t)
            envelope = np.exp(-4 * t)
            
        full_wave.extend(wave * envelope)
        
    full_wave = np.array(full_wave, dtype=np.float32)
    
    # 1. Aplicar Reverb
    if reverb > 0:
        full_wave = apply_reverb(full_wave, reverb, sample_rate)
        
    # 2. Aplicar Filtro de Brillo
    full_wave = apply_lowpass_filter(full_wave, cutoff_hz, sample_rate)
    
    # Normalización PCM 16-bit
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
        return None, "No se pudo leer el video."
    
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    height, _ = prev_gray.shape
    
    detected_events = []
    frame_count = 0
    max_frames = 150
    
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

# --- ESTRUCTURA DE LA APP ---
col_vid, col_res = st.columns([1, 1])

with col_vid:
    video_file = st.file_uploader("Sube un video corto (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])
    if video_file:
        st.video(video_file)

with col_res:
    if video_file and st.button("🎼 Traducir Movimiento y Procesar Sonido"):
        with st.spinner("Escaneando física del video y sintetizando audio..."):
            tfile = tempfile.NamedTemporaryFile(delete=False)
            tfile.write(video_file.read())
            
            notes, error = process_video_motion(tfile.name)
            
            if error:
                st.error(error)
            elif notes:
                melody_sequence = [notes[0]]
                for n in notes[1:]:
                    if n != melody_sequence[-1]:
                        melody_sequence.append(n)
                
                # SINTETIZAR AUDIO CON LOS CONTROLES DE LA BARRA LATERAL
                audio_buffer = synthesize_melody(
                    melody_sequence, 
                    pitch_shift=pitch_shift,
                    duration=note_duration,
                    timbre=timbre_option,
                    reverb=reverb_amount,
                    cutoff_hz=brightness
                )
                
                st.success("¡Audio procesado correctamente!")
                st.markdown("### 🔊 Reproductor con Efectos Aplicados")
                st.audio(audio_buffer, format="audio/wav")
                
                st.markdown("### 🎹 Notas Extraídas")
                st.info(f"**Secuencia:** {', '.join(melody_sequence)}")
                
                first_note_base = melody_sequence[0][0]
                st.markdown("### 🎶 Progresión Armónica Sugerida")
                st.success(f"`{first_note_base}maj7` ➔ `{first_note_base}/F` ➔ `G6` ➔ `{first_note_base}`")

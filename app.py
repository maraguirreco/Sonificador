import streamlit as st
import cv2
import numpy as np
import tempfile

st.set_page_config(page_title="Sonificador de Video", page_icon="🍃")

st.title("🍃 Sonificador de Movimiento en Video")
st.write("Sube un video de la naturaleza (hojas moviéndose, agua, sombras) para traducirlo a melodías y acordes.")

# Carga de archivo de video
video_file = st.file_uploader("Sube un video corto (.mp4, .mov, .avi)", type=["mp4", "mov", "avi"])

# Escala Pentatónica Mayor de Do (Garantiza que todas las notas combinen perfectamente)
PENTATONIC_SCALE = ['C4', 'D4', 'E4', 'G4', 'A4', 'C5', 'D5', 'E5', 'G5', 'A5', 'C6']

def process_video_motion(video_path):
    cap = cv2.VideoCapture(video_path)
    ret, prev_frame = cap.read()
    if not ret:
        return None, "No se pudo leer el archivo de video."
    
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    height, width = prev_gray.shape
    
    detected_events = []
    frame_count = 0
    max_frames = 180  # Procesa aprox. 6 segundos a 30fps para máxima velocidad
    
    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Diferencia de fotogramas para aislar el movimiento
        diff = cv2.absdiff(prev_gray, gray)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        
        # Obtener coordenadas de los píxeles en movimiento
        moving_pixels = np.where(thresh > 0)
        
        if len(moving_pixels[0]) > 40:  # Umbral mínimo de movimiento
            # Altura promedio del movimiento (Inversa: 0 arriba es agudo, 1 abajo es grave)
            avg_y = np.mean(moving_pixels[0])
            norm_y = 1.0 - (avg_y / height)
            
            # Asignar nota de la escala
            scale_idx = int(norm_y * (len(PENTATONIC_SCALE) - 1))
            note = PENTATONIC_SCALE[scale_idx]
            
            # Cantidad de píxeles moviéndose (densidad del viento/movimiento)
            density = len(moving_pixels[0])
            
            detected_events.append({
                "frame": frame_count,
                "note": note,
                "density": density
            })
            
        prev_gray = gray
        frame_count += 1
        
    cap.release()
    return detected_events, None

if video_file:
    st.video(video_file)
    
    if st.button("🎼 Traducir Movimiento a Melodía"):
        with st.spinner("Analizando la física del movimiento fotograma a fotograma..."):
            # Crear archivo temporal para leer con OpenCV
            tfile = tempfile.NamedTemporaryFile(delete=False)
            tfile.write(video_file.read())
            
            events, error = process_video_motion(tfile.name)
            
            if error:
                st.error(error)
            elif events:
                # Secuencia de notas sin repeticiones continuas
                melody_sequence = []
                for ev in events:
                    if not melody_sequence or melody_sequence[-1] != ev['note']:
                        melody_sequence.append(ev['note'])
                
                # Densidad promedio de movimiento
                avg_density = np.mean([ev['density'] for ev in events])
                
                st.markdown("---")
                st.subheader("📊 Análisis del Movimiento")
                
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Puntos de Movimiento", f"{len(events)} fotogramas")
                with c2:
                    dinamica = "Suave / Sutil" if avg_density < 1000 else "Dinámica / Vigorosa"
                    st.metric("Sensación del Movimiento", dinamica)
                
                st.markdown("### 🎹 Melodía Generada por las Hojas")
                st.info(f"**Secuencia de notas:** {', '.join(melody_sequence[:12])}...")
                
                # Progresión armónica basada en la primera nota
                first_note_base = melody_sequence[0][0]  # Extrae 'C', 'D', 'E', etc.
                st.markdown("### 🎶 Progresión de Acordes Sugerida")
                
                st.success(
                    f"**Progresión Orgánica / Ambiental:**\n\n"
                    f"`{first_note_base}maj7` ➔ `{first_note_base} / F` ➔ `G6` ➔ `{first_note_base}`"
                )
            else:
                st.warning("No se detectó un movimiento significativo en el video. Intenta con un video donde el movimiento sea más claro.")

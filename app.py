from flask import Flask, render_template, request
import numpy as np
from PIL import Image
import os
import tflite_runtime.interpreter as tflite

app = Flask(__name__)

# Configurar e iniciar el intérprete de TFLite (Ultra ligero)
interpreter = tflite.Interpreter(model_path="detecworm_model.tflite")
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# clases
classes = ["algo_danado", "danado", "sano"]

# recomendaciones
def recomendaciones(label):
    if label == "sano":
        return [
            "Mantén un riego adecuado y constante.",
            "Realiza monitoreo periódico del cultivo.",
            "Mantén control preventivo de plagas."
        ]
    elif label == "algo_danado":
        return [
            "Inspecciona las hojas afectadas.",
            "Aplica tratamiento preventivo.",
            "Monitorea el avance del daño."
        ]
    else:
        return [
            "Aplica tratamiento inmediato contra plagas.",
            "Retira hojas gravemente dañadas.",
            "Consulta apoyo técnico agrícola."
        ]

@app.route("/", methods=["GET", "POST"])
def index():
    prediction = None
    confidence = None
    recomendaciones_list = []

    if request.method == "POST":
        file = request.files["file"]
        if file:
            filepath = os.path.join("static", file.filename)
            file.save(filepath)

            # Procesar imagen usando Pillow (más rápido y ligero en ARM)
            img = Image.open(filepath).convert('RGB')
            img = img.resize((224, 224)) # Tamaño target que usas
            
            # Convertir a array de numpy y normalizar
            img_array = np.array(img, dtype=np.float32)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = img_array / 255.0

            # --- INFERENCIA CON TFLITE ---
            interpreter.set_tensor(input_details[0]['index'], img_array)
            interpreter.invoke()
            pred = interpreter.get_tensor(output_details[0]['index'])[0]
            # ------------------------------

            idx = np.argmax(pred)
            prediction = classes[idx]
            confidence = round(float(pred[idx]) * 100, 2)
            recomendaciones_list = recomendaciones(prediction)

    return render_template(
        "index.html",
        prediction=prediction,
        confidence=confidence,
        recomendaciones=recomendaciones_list
    )

if __name__ == "__main__":
    # debug=False para producción en la placa centinela
    app.run(host="0.0.0.0", port=5000, debug=False)
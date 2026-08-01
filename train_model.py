import os
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2

# 1. Configuración de parámetros y directorios
IMG_SIZE = (224, 224)
BATCH_SIZE = 8  # Lotes pequeños para adaptarse mejor al tamaño reducido del dataset
DATASET_DIR = "./dataset"

print("--- Cargando y dividiendo el dataset ---")
train_ds = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR,
    validation_split=0.2,
    subset="training",
    seed=123,
    image_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    label_mode="categorical"
)

val_ds = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR,
    validation_split=0.2,
    subset="validation",
    seed=123,
    image_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    label_mode="categorical"
)

class_names = train_ds.class_names
print(f"Clases identificadas automáticamente: {class_names}")

# 2. Pipeline de Data Augmentation (Ingeniería para datasets pequeños)
data_augmentation = models.Sequential([
    layers.RandomFlip("horizontal_and_vertical"),
    layers.RandomRotation(0.25),
    layers.RandomZoom(0.2),
    layers.RandomContrast(0.2),
    layers.RandomBrightness(0.2),
])

# 3. Construcción del modelo con Transfer Learning (MobileNetV2)
base_model = MobileNetV2(
    input_shape=(224, 224, 3),
    include_top=False,
    weights="imagenet"
)
base_model.trainable = False  # Congelamos los pesos base para evitar overfitting

inputs = tf.keras.Input(shape=(224, 224, 3))
x = data_augmentation(inputs)
x = tf.keras.applications.mobilenet_v2.preprocess_input(x)
x = base_model(x, training=False)
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dropout(0.4)(x)  # Regularización alta para evitar sobreajuste
outputs = layers.Dense(len(class_names), activation="softmax")(x)

model = models.Model(inputs, outputs)

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.0008),
    loss="categorical_crossentropy",
    metrics=["accuracy"]
)

# 4. Entrenamiento del modelo
print("\n--- Iniciando entrenamiento de la red neuronal ---")
history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=20
)

# 5. Exportación del archivo TensorFlow Lite
print("\n--- Convirtiendo y exportando a detecworm_model.tflite ---")
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()

tflite_path = "detecworm_model.tflite"
with open(tflite_path, "wb") as f:
    f.write(tflite_model)

print(f"\n¡Entrenamiento completado! Modelo generado exitosamente en: '{tflite_path}'")
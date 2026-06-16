import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Input

def generate_synthetic_data(samples=1000, sequence_length=10):
    # Healthy track vibration data (low amplitude, mostly noise)
    healthy_data = np.random.normal(loc=0.1, scale=0.05, size=(samples, sequence_length))
    return healthy_data

def train_autoencoder():
    print("Generating synthetic vibration data for training...")
    X_train = generate_synthetic_data()
    
    # Autoencoder architecture
    model = Sequential([
        Input(shape=(10,)),
        Dense(8, activation='relu'),
        Dense(4, activation='relu'), # Bottleneck
        Dense(8, activation='relu'),
        Dense(10, activation='linear')
    ])
    
    model.compile(optimizer='adam', loss='mse')
    
    print("Training Anomaly Detection Autoencoder...")
    # Train the model to reconstruct healthy data
    model.fit(X_train, X_train, epochs=10, batch_size=32, validation_split=0.1, verbose=1)
    
    model.save('rail_anomaly_model.keras')
    print("Model saved to rail_anomaly_model.keras")

if __name__ == "__main__":
    train_autoencoder()

import requests
import random
import time

# URL de l'API FastAPI
api_url = "http://192.168.209.244:8000/verifier"

def generate_random_sensor_data():
    return {
        "water_level": random.uniform(71, 100.0),  # Valeur entre 70 et 110
        "caustic_soda_level": random.uniform(0.6, 2),  # Valeur entre 0.5 et 2.5
        "water_temperature": random.uniform(31, 88),  # Valeur entre 30 et 90
        "caustic_soda_temperature": random.uniform(32, 88),  # Valeur entre 30 et 90
        "voltage": random.uniform(6, 12)  # Valeur entre 5 et 15
    }

def send_sensor_data():
    while True:
        data = generate_random_sensor_data()
        response = requests.post(api_url, json=data)
        if response.status_code == 200:
            print(f"Data sent successfully: {data}")
        else:
            print(f"Failed to send data: {response.status_code}, {response.text}")
        
        time.sleep(4)  # Attendre 4 secondes avant d'envoyer les prochaines données

if __name__ == "__main__":
    send_sensor_data()

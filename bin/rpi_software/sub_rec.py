import subprocess
import configparser
import os
from typing import Optional
from datetime import datetime, timedelta
import re


def get_filename_with_timestamp(mission_name, base_name="video", extension="h264"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = os.path.join("/home/uwos/DATA", mission_name)
    os.makedirs(folder, exist_ok=True)

    video_filename = f"{base_name}_{timestamp}.{extension}"
    log_filename = f"{base_name}_{timestamp}.log"

    video_path = os.path.join(folder, video_filename)
    log_path = os.path.join(folder, log_filename)

    return video_path, log_path

def disable_display():
    """
    Désactive l'affichage graphique pour libérer des ressources CPU/GPU.
    """
    print("Désactivation de l'affichage...")
    subprocess.run(["sudo", "systemctl", "stop", "lightdm"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def enable_display():
    """
    Réactive l'affichage graphique après l'enregistrement.
    """
    print("Réactivation de l'affichage...")
    subprocess.run(["sudo", "systemctl", "start", "lightdm"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    
def record_video(output_file, duration, width, height, framerate, codec, bitrate, nopreview, disable_display_flag):
    """
    Enregistre une vidéo avec libcamera-vid en utilisant les paramètres fournis.
    """
    if disable_display_flag:
        disable_display()

    command = [
        "libcamera-vid",
        "-t", str(duration),
        "--width", str(width),
        "--height", str(height),
        "--framerate", str(framerate),
        "--codec", codec,
        "--bitrate", str(bitrate),
        "-o", output_file
    ]
    
    if nopreview:
        command.append("--nopreview")

    print(f"Enregistrement en cours : {output_file} ({width}x{height}, {duration/1000}s, {framerate} FPS, {bitrate} bps, codec {codec})")

    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Erreur lors de l'enregistrement : {result.stderr}")
        else:
            print("Enregistrement terminé avec succès.")
    except FileNotFoundError:
        print("Erreur : libcamera-vid n'est pas installé ou introuvable.")
    except Exception as e:
        print(f"Erreur inattendue : {e}")
    finally:
        if disable_display_flag:
            enable_display()
            
def read_config(config_file="/home/uwos/bin/config.txt"):
    """
    Lit le fichier de configuration et récupère les paramètres.
    """
    config = configparser.ConfigParser()
    
    if not os.path.exists(config_file):
        print(f"Fichier de configuration {config_file} introuvable, utilisation des valeurs par défaut.")
        return "video", "h264", 5000, 1920, 1080, 15, "h264", 25000000, False, False

    config.read(config_file)

    base_name = config.get("Settings_UWOS", "output_file", fallback="video").split('.')[0]
    extension = config.get("Settings_UWOS", "output_file", fallback="video.h264").split('.')[-1]
    width = config.getint("Settings_UWOS", "width", fallback=1920)
    height = config.getint("Settings_UWOS", "height", fallback=1080)
    framerate = config.getint("Settings_UWOS", "framerate", fallback=30)
    codec = config.get("Settings_UWOS", "codec", fallback="h264")
    bitrate = config.getint("Settings_UWOS", "bitrate", fallback=25000000)
    nopreview = config.getboolean("Settings_UWOS", "nopreview", fallback=False)
    disable_display_flag = config.getboolean("Settings_UWOS", "disable_display", fallback=False)
    mission_name = config.get("Settings_UWOS", "mission_name", fallback="/home/uwos/DATA/noname")

    shutdown_duration = config.getint("Settings_QHB", "Shutdown_Duration", fallback=50)
    preparing_duration = config.getint("Settings_QHB", "Preparing_Duration", fallback=20)
    recording_duration = config.getint("Settings_QHB", "Recording_Duration", fallback=60)
    stopping_duration = config.getint("Settings_QHB", "Stopping_Duration", fallback=10)

    return base_name, extension, width, height, framerate, codec, bitrate, nopreview, disable_display_flag, mission_name, shutdown_duration, preparing_duration, recording_duration, stopping_duration



def write_log(log_file: str, key: str, value):
    """
    Écrit ou ajoute une ligne dans un fichier log au format : KEY: VALUE
    - Si le fichier n'existe pas, il est créé
    - Si la clé existe déjà, elle n'est pas écrasée
    """
    lines = {}
    
    # Lire les lignes existantes
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            for line in f:
                if ":" in line:
                    k, v = line.strip().split(":", 1)
                    lines[k.strip()] = v.strip()

    # N'ajoute la clé que si elle n'est pas déjà présente
    if key not in lines:
        # Si value est un datetime, formater proprement
        if isinstance(value, datetime):
            value = value.strftime("%Y-%m-%d %H:%M:%S.%f")
        lines[key] = str(value)

        # Réécrire le fichier entier (dans l’ordre d’apparition)
        with open(log_file, "w") as f:
            for k, v in lines.items():
                f.write(f"{k}: {v}\n")

### main code ###

if __name__ == "__main__":
    reception_time = datetime.utcnow()  # 🕒 Heure UTC de réception UART (appelé par l'autre script)

    base_name, extension, duration, width, height, framerate, codec, bitrate, nopreview, disable_display_flag, mission_name = read_config()

    output_file = get_filename_with_timestamp(mission_name, base_name, extension)
    
    record_start_time = datetime.utcnow()  # 🕒 Heure UTC du lancement effectif de libcamera-vid

    record_video(output_file, duration, width, height, framerate, codec, bitrate, nopreview, disable_display_flag)

    # 🔧 Écriture du fichier .log associé
    log_file = output_file.rsplit(".", 1)[0] + ".log"
    with open(log_file, "w") as log:
        log.write(f"MISSION: {mission_name}\n")
        log.write(f"RECEPTION_UART_UTC: {reception_time.strftime('%Y-%m-%d %H:%M:%S.%f')}\n")
        log.write(f"DEBUT_ENREGISTREMENT_UTC: {record_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')}\n")
        log.write(f"DUREE_MS: {duration}\n")
        log.write(f"FICHIER_VIDEO: {os.path.basename(output_file)}\n")

    print(f"📄 Log sauvegardé : {log_file}")

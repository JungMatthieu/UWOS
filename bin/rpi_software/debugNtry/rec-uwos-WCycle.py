import subprocess
import configparser
import os
from typing import Optional
from datetime import datetime, timedelta
import re


#### Definition des fonction ####

def get_filename_with_timestamp(mission_name, base_name="video", extension="h264"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = os.path.join("/home/uwos/DATA", mission_name)  # Dossier de stockage des vidéos
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{base_name}_{timestamp}.{extension}")


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
    



def get_duration_ms(log_path: str) -> Optional[int]:
    """
    Retourne la duree d'enregistrement, en faisant la date.prochain.shutdown - date.now (depuis le fichier schedule.log).

    Args:
        log_path (str): Chemin vers le fichier log.

    Returns:
        int: Durée en millisecondes.
        None: Si aucune paire shutdown/startup n'est trouvée.
    """
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            print("Contenu du log récupéré automatiquement:")
            print("".join(lines[-10:]))

        shutdown_time = None
        startup_time = None

        for line in reversed(lines):
            if "Schedule next startup at:" in line and not startup_time:
                parts = line.strip().split("at:")
                if len(parts) == 2:
                    startup_time = parts[1].strip()
                    print(f"Startup détecté : {startup_time}")
            elif "Schedule next shutdown at:" in line and not shutdown_time:
                parts = line.strip().split("at:")
                if len(parts) == 2:
                    shutdown_time = parts[1].strip()
                    print(f"Shutdown détecté : {shutdown_time}")
            if shutdown_time and startup_time:
                break

        if shutdown_time and startup_time:
            fmt = "%Y-%m-%d %H:%M:%S"
            shutdown_dt = datetime.strptime(shutdown_time, fmt)
            now = datetime.now()
            delta = shutdown_dt - now
            print(f"Durée calculée jusqu'au shutdown : {delta}")

            if delta.total_seconds() < 10:
                print("Durée < 10s, on force à 10s")
                return 10000
            else:
                return int(delta.total_seconds() * 1000) - 4000
        else:
            print("Impossible de déterminer la durée, fallback 10s")
            return 10000

    except Exception as e:
        print(f"Erreur lors de la lecture de la durée : {e}")
        return 10000



    

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
            
            


def read_config(config_file="/home/uwos/config.txt"):
    """
    Lit le fichier de configuration et récupère les paramètres.
    """
    config = configparser.ConfigParser()
    
    if not os.path.exists(config_file):
        print(f"Fichier de configuration {config_file} introuvable, utilisation des valeurs par défaut.")
        return "video", "h264", 5000, 1920, 1080, 15, "h264", 25000000, False, False

    config.read(config_file)

    base_name = config.get("Settings", "output_file", fallback="video").split('.')[0]
    extension = config.get("Settings", "output_file", fallback="video.h264").split('.')[-1]
    #duration = config.getint("Settings", "duration", fallback=5000) # Duree definie par le fichier de configuration
    duration = get_duration_ms("/home/uwos/wittypi/schedule.log") #duree definie par le temps jusqua la prochaine exinction avec une marge de 2s
    width = config.getint("Settings", "width", fallback=1920)
    height = config.getint("Settings", "height", fallback=1080)
    framerate = config.getint("Settings", "framerate", fallback=30)
    codec = config.get("Settings", "codec", fallback="h264")
    bitrate = config.getint("Settings", "bitrate", fallback=25000000)
    nopreview = config.getboolean("Settings", "nopreview", fallback=False)
    disable_display_flag = config.getboolean("Settings", "disable_display", fallback=False)
    mission_name = config.get("Settings", "mission_name", fallback="DATA/none")

    return base_name, extension, duration, width, height, framerate, codec, bitrate, nopreview, disable_display_flag, mission_name


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


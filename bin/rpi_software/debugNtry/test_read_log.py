from datetime import datetime, timedelta
from typing import Optional

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
            print("".join(lines[-10:]))  # affiche les 10 dernières lignes


        shutdown_time = None
        startup_time = None

        for line in reversed(lines):
            if "Schedule next startup at:" in line:
                startup_time = line.strip().split("at:")[1].strip()  #recuperation startup
                print(startup_time )
            elif "Schedule next shutdown at:" in line:
                shutdown_time = line.strip().split("at:")[1].strip() #recuperation shutdown
                print(shutdown_time)
                break

        if shutdown_time and startup_time:
            fmt = "%Y-%m-%d %H:%M:%S" #format date dans le fichier log
            shutdown_dt = datetime.strptime(shutdown_time, fmt) #prochain shutdown
            startup_dt = datetime.strptime(startup_time, fmt) #prochain startup
            now = datetime.now() #recupere la date actuelle
            delta = shutdown_dt - now
            print(delta)
            if delta.total_seconds() < 0 :
                print("Pas de shutdown prevu, rec de 1s")
                return int(1000)
            if delta.total_seconds() < 10000 :
                print("rec de moins de 10s, donc fixe a 1s")
                return int(1000)
            return (int(delta.total_seconds() * 1000)- 10000)  # Convertir en millisecondes
        else:
            return int(1000)

    except FileNotFoundError:
        print(f"Fichier non trouvé : {log_path}")
        return None

duree=get_duration_ms("/home/uwos/wittypi/schedule.log")
print(duree)

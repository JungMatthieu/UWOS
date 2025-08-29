import subprocess
from datetime import datetime, timedelta

def schedule_shutdown(day, hour, minute, second):
    bash_command = f"""
    source /home/uwos/wittypi/utilities.sh
    set_shutdown_time {day} {hour} {minute} {second}
    """

    try:
        subprocess.run(['bash', '-c', bash_command], check=True)
        print(f"⏱️ Extinction programmée pour le {day:02}/{datetime.now().month:02} à {hour:02}:{minute:02}:{second:02}")
    except subprocess.CalledProcessError as e:
        print("❌ Erreur lors de l'exécution de set_shutdown_time :")
        print(e)
        
def schedule_startup(day, hour, minute, second):
    minute+=1
    bash_command = f"""
    source /home/uwos/wittypi/utilities.sh
    set_startup_time {day} {hour} {minute} {second}
    """

    try:
        subprocess.run(['bash', '-c', bash_command], check=True)
        print(f"⏱️ Extinction programmée pour le {day:02}/{datetime.now().month:02} à {hour:02}:{minute:02}:{second:02}")
    except subprocess.CalledProcessError as e:
        print("❌ Erreur lors de l'exécution de set_shutdown_time :")
        print(e)
        
        
        

if __name__ == "__main__":
    # Planifie l’extinction 2 minutes après l’heure actuelle
    future = datetime.now() + timedelta(minutes=2)
    schedule_shutdown(day=future.day, hour=future.hour, minute=future.minute, second=future.second)
    schedule_startup(day=future.day, hour=future.hour, minute=future.minute, second=future.second)
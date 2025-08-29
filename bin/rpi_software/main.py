import serial
import time
import subprocess
from datetime import datetime, timedelta
from sub_rec import read_config, get_filename_with_timestamp, write_log
import os

# === Configuration UART ===
ser = serial.Serial(
    '/dev/ttyAMA0',
    baudrate=115200,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
)

# === Lecture Fichier de Configuration === #

base_name, extension, width, height, framerate, codec, bitrate, nopreview, disable_display_flag, mission_name, shutdown_duration, preparing_duration, recording_duration, stopping_duration = read_config()

# === Configuration time === #

total_off = shutdown_duration - preparing_duration - stopping_duration
total_on = recording_duration + stopping_duration
safe_duration = 2 #duree de securite pour assurer l'overlap de lenregistrement video
recording_duration_UWOS = (recording_duration+preparing_duration+safe_duration)*1000 #voir documentation

# === Configuration script === #
# === Nouveau flag === 
preparing_recu = False
recording_en_cours = False
next_shutdown_done = False
next_startup_done = False


# === Dictionnaire de statuts connus ===
STATUTS = {
    0x00: "SHUTDOWN_En_Cours",
    0x01: "PREPARING_En_Cours",
    0x02: "RECORDING_En_Cours",
    
    0x03: "STOPPING_En_Cours",
    0x04: "CNN_DETECTION_En_Cours",
    0x05: "DATA_SEND_En_Cours",
    0x06: "Preparing_For_DATA_SEND",
    0x07: "DATA_SEND_Finished",
    0x08: "IDLE_En_Cours"
}

# === Fonctions ===
def calcul_checksum(trame_bytes):
    checksum = 0
    for b in trame_bytes:
        checksum ^= b
    return checksum

def print_log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def action_sur_payload(payload):
    global recording_en_cours, preparing_recu #FLAG
    global next_shutdown_done, next_startup_done #FLAG
    global total_off, total_on
    global log_file, output_file
    global recording_duration, recording_duration_UWOS
    global base_name, extension, width, height, framerate, codec, bitrate, nopreview, disable_display_flag, mission_name #CONFIG UWOS
    

    if len(payload) != 1:
        return

    status = payload[0]
    label = STATUTS.get(status, f"Inconnu (0x{status:02X})")
    print_log(f"📥 Statut reçu : {label}")

    if status == 0x01:  # PREPARING_En_Cours
        preparing_recu = True
        if not recording_en_cours:
            reception_time = datetime.utcnow()
            output_file, log_file = get_filename_with_timestamp(mission_name, base_name, extension)
            record_start_time = datetime.utcnow()
            print_log("🚀 Lancement de l'enregistrement → rec-uwos.py")
            subprocess.Popen([
                'python3',
                '/home/uwos/bin/rec.py',
                '--output_file', output_file,
                '--duration', str(recording_duration_UWOS),
                '--width', str(width),
                '--height', str(height),
                '--framerate', str(framerate),
                '--codec', codec,
                '--bitrate', str(bitrate),
                '--nopreview', str(nopreview),
                '--disable_display_flag', str(disable_display_flag)
            ])
            write_log(log_file, "RECEPTION_UART_UTC", reception_time)
            write_log(log_file, "START_REC_UWOS", record_start_time)
            recording_en_cours = True
        else:
            #print_log("⏱️ Enregistrement déjà lancé, trame ignorée")
            print_log("...")
            
    if status == 0x02: #Rec_en_Cours
        time_rec_qhb = datetime.utcnow()
        time_shutdown = datetime.now()+ timedelta(seconds=total_on) #on doit laisser on pendant au moins le temps de l'enregistrement + quelques seconde soit total_on
        time_startup = time_shutdown + timedelta(seconds=total_off) #on doit laisser off le temps de total_off apres le total_on
        if not preparing_recu:
            print_log("⚠️ Rejet de 0x02 : aucun 0x01 reçu avant (désynchronisation possible)")
            return
        else :
            write_log(log_file, "START_REC_QHB", time_rec_qhb)
            if not next_shutdown_done:
                print_log("⚡ Cycle WittyPi non encore lancé, lancement du script.")
                try :
                    schedule_shutdown(day=time_shutdown.day, hour=time_shutdown.hour, minute=time_shutdown.minute, second=time_shutdown.second)
                    next_shutdown_done = True
                    schedule_startup(day=time_startup.day, hour=time_startup.hour, minute=time_startup.minute, second=time_startup.second)
                    next_startup_done = True
                    print_log("✅ Cycle WittyPi lancé et flag enregistré")
                except Exception as e:
                    print_log(f"❌ Erreur lors du lancement du cycle WittyPi : {e}")
            else :
                print_log("...")
                
    if status == 0x03: #Rec_en_Cours
        if recording_en_cours:
            time_stop_rec_qhb = datetime.utcnow()
            write_log(log_file, "STOP_REC_QHB", time_stop_rec_qhb)
            print_log("Fin de l'enregistrement QHB")
        else :
            print_log("Fin de l'enregistrement QHB, mais pas d'enregistrement UWOS")
    
    elif status == 0x00:  # IDLE_En_Cours → Fin de cycle
        print_log("💤 Exctinction de la QHB")
        recording_en_cours = False
        next_shutdown_done = False
        next_startup_done = False
    

# === Fonction gestion de puissance === #
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
    bash_command = f"""
    source /home/uwos/wittypi/utilities.sh
    set_startup_time {day} {hour} {minute} {second}
    """

    try:
        subprocess.run(['bash', '-c', bash_command], check=True)
        print(f"⏱️ Allumage programmée pour le {day:02}/{datetime.now().month:02} à {hour:02}:{minute:02}:{second:02}")
    except subprocess.CalledProcessError as e:
        print("❌ Erreur lors de l'exécution de set_shutdown_time :")
        print(e)


# === Boucle principale ===
print_log("📡 En attente de trames UART (format variable)")

try:
    while True:
        byte = ser.read(1)
        if not byte or byte[0] != 0xFE:
            continue  # Attente SoF (0xFE)

        header = ser.read(4)
        if len(header) < 4:
            print_log("❌ Header incomplet")
            continue

        msb_cmd, lsb_cmd, msb_len, lsb_len = header
        data_length = (msb_len << 8) | lsb_len

        payload = ser.read(data_length)
        if len(payload) < data_length:
            print_log("⚠️ Payload incomplet")
            continue

        checksum_byte = ser.read(1)
        if len(checksum_byte) < 1:
            print_log("❌ Checksum manquant")
            continue
        checksum = checksum_byte[0]

        full_trame = [0xFE] + list(header) + list(payload)
        expected_checksum = calcul_checksum(full_trame)

        print_log(f"📦 Trame reçue → CMD: {msb_cmd:02X}{lsb_cmd:02X}, Payload: {payload.hex()}, Checksum: {checksum:02X}")

        if checksum == expected_checksum:
            print_log("✅ Checksum correct")
            action_sur_payload(payload)
        else:
            print_log(f"❌ Checksum incorrect (attendu: {expected_checksum:02X})")

        time.sleep(0.05)

except KeyboardInterrupt:
    print_log("🛑 Interruption manuelle")

finally:
    ser.close()
    print_log("🔌 Port série fermé.")

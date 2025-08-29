import serial
import time
import subprocess
from datetime import datetime

# === Configuration UART ===
ser = serial.Serial(
    '/dev/ttyAMA0',
    baudrate=115200,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
)

recording_en_cours = False

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
    global recording_en_cours

    if len(payload) != 1:
        return

    status = payload[0]
    label = STATUTS.get(status, f"Inconnu (0x{status:02X})")
    print_log(f"📥 Statut reçu : {label}")

    if status == 0x01:  # PREPARING_En_Cours
        if not recording_en_cours:
            print_log("🚀 Lancement de l'enregistrement → rec-uwos.py")
            #subprocess.Popen(['python3', 'rec-uwos.py'])
            recording_en_cours = True
        else:
            print_log("⏱️ Enregistrement déjà lancé, trame ignorée")

    elif status == 0x00:  # IDLE_En_Cours → Fin de cycle
        print_log("💤 Exctinction de la QHB")
        recording_en_cours = False


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

import serial
import time

# Configuration UART
ser = serial.Serial('/dev/ttyAMA0', baudrate=115200, timeout=1)

def construire_trame(cmd_id, payload_bytes):
    msb_cmd = (cmd_id >> 8) & 0xFF
    lsb_cmd = cmd_id & 0xFF
    data_len = len(payload_bytes)
    msb_len = (data_len >> 8) & 0xFF
    lsb_len = data_len & 0xFF

    trame = [0xFE, msb_cmd, lsb_cmd, msb_len, lsb_len] + payload_bytes
    checksum = 0
    for b in trame:
        checksum ^= b
    trame.append(checksum)
    return bytes(trame)

cmd_id = 0x0201
temps_rec = 10         # enregistrement : 10s
temps_pause = 60       # pause : 60s

try:
    print("🔁 Démarrage de la simulation QHB UART (rec + pause)")

    while True:
        # --- Phase enregistrement (10s) ---
        for t in range(temps_rec):
            if t == 0:
                payload = [0x01]  # Start
            elif t == temps_rec - 1:
                payload = [0x03]  # End
            else:
                payload = [0x02]  # In progress

            trame = construire_trame(cmd_id, payload)
            ser.write(trame)
            print(f"🎙️ [REC] Trame {t+1}/{temps_rec} : {trame.hex(' ').upper()}")
            time.sleep(1)

        # --- Phase pause (60s) ---
        for t in range(temps_pause):
            payload = [0x00]  # Standby
            trame = construire_trame(cmd_id, payload)
            ser.write(trame)
            print(f"💤 [PAUSE] Trame {t+1}/{temps_pause} : {trame.hex(' ').upper()}")
            time.sleep(1)

except KeyboardInterrupt:
    print("\n⏹️ Simulation interrompue")

finally:
    ser.close()
    print("🔌 Port série fermé.")

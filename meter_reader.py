"""
SDM630 Modbus RTU - Enerji Sayacı Okuyucu
==========================================
Bağlantı: USB-RS485 dönüştürücü → COM port (Windows) veya /dev/ttyUSB0 (Linux/Pi)
Protokol: Modbus RTU, FC04, Float32 Big-endian
Sayaç: Eastron SDM630-Modbus V2

Kurulum:
    pip install minimalmodbus
"""

import minimalmodbus
import time
import sys

# ─── Ayarlar ─────────────────────────────────────────────────────────────────

PORT         = "COM6"       # Windows: "COM6" | Linux/Pi: "/dev/ttyUSB0"
SLAVE_ID     = 1
BAUDRATE     = 9600
TIMEOUT      = 1.0          # saniye

# ─── SDM630 Register Haritası (FC04, Float32 Big-endian) ─────────────────────
# Her parametre 2 register kaplar (32-bit float)

REGISTERS = {
    # Faz gerilimleri (V)
    "L1_Voltage":          0x0000,
    "L2_Voltage":          0x0002,
    "L3_Voltage":          0x0004,

    # Faz akımları (A)
    "L1_Current":          0x0006,
    "L2_Current":          0x0008,
    "L3_Current":          0x000A,

    # Aktif güç (W)
    "L1_Power":            0x000C,
    "L2_Power":            0x000E,
    "L3_Power":            0x0010,
    "Total_Power":         0x0034,

    # Güç faktörü
    "L1_PF":               0x001E,
    "L2_PF":               0x0020,
    "L3_PF":               0x0022,
    "Total_PF":            0x003E,

    # Frekans (Hz)
    "Frequency":           0x0046,

    # Enerji (kWh) — en önemli değerler
    "Total_Import_kWh":    0x0156,   # Toplam çekilen enerji (import)
    "Total_Export_kWh":    0x0158,   # Toplam verilen enerji (export)
    "Total_kWh":           0x0180,   # Toplam aktif enerji
}

# ─── Sayaç bağlantısı ────────────────────────────────────────────────────────

def connect(port=PORT, slave_id=SLAVE_ID):
    inst = minimalmodbus.Instrument(port, slave_id)
    inst.serial.baudrate = BAUDRATE
    inst.serial.bytesize = 8
    inst.serial.parity   = minimalmodbus.serial.PARITY_NONE
    inst.serial.stopbits = 1
    inst.serial.timeout  = TIMEOUT
    inst.mode            = minimalmodbus.MODE_RTU
    return inst

# ─── Tek değer oku ───────────────────────────────────────────────────────────

def read_value(inst, register_address):
    """Float32 Big-endian, FC04 ile tek parametre oku."""
    try:
        value = inst.read_float(
            registeraddress=register_address,
            functioncode=4,
            number_of_registers=2
        )
        return round(value, 3)
    except Exception as e:
        return None

# ─── Tüm parametreleri oku ───────────────────────────────────────────────────

def read_all(inst):
    """Tüm register'ları okuyup dict olarak döndür."""
    result = {}
    for name, addr in REGISTERS.items():
        val = read_value(inst, addr)
        result[name] = val
    return result

# ─── OCPP entegrasyonu için tek fonksiyon ────────────────────────────────────

def read_energy_wh(inst):
    """
    sim1.py'e entegrasyon için:
    Toplam import enerjisini Wh cinsinden döndürür.
    meter_wh değişkenini beslemek için kullan.
    """
    kwh = read_value(inst, REGISTERS["Total_Import_kWh"])
    if kwh is not None:
        return int(kwh * 1000)  # kWh → Wh
    return None

def read_power_w(inst):
    """Anlık toplam aktif güç (W)"""
    return read_value(inst, REGISTERS["Total_Power"])

# ─── Test / Demo ─────────────────────────────────────────────────────────────

def main():
    print(f"SDM630 bağlanıyor → {PORT}, Slave: {SLAVE_ID}")
    print("-" * 50)

    try:
        inst = connect()
        print("Bağlantı başarılı!\n")
    except Exception as e:
        print(f"Bağlantı hatası: {e}")
        print(f"Port doğru mu? Şu an: {PORT}")
        sys.exit(1)

    # Sürekli okuma döngüsü
    while True:
        try:
            print(f"\n{'='*50}")
            print(f"  Zaman: {time.strftime('%H:%M:%S')}")
            print(f"{'='*50}")

            # Gerilimler
            v1 = read_value(inst, REGISTERS["L1_Voltage"])
            v2 = read_value(inst, REGISTERS["L2_Voltage"])
            v3 = read_value(inst, REGISTERS["L3_Voltage"])
            print(f"  Gerilim  →  L1: {v1} V  |  L2: {v2} V  |  L3: {v3} V")

            # Akımlar
            a1 = read_value(inst, REGISTERS["L1_Current"])
            a2 = read_value(inst, REGISTERS["L2_Current"])
            a3 = read_value(inst, REGISTERS["L3_Current"])
            print(f"  Akım     →  L1: {a1} A  |  L2: {a2} A  |  L3: {a3} A")

            # Güç
            p_total = read_value(inst, REGISTERS["Total_Power"])
            print(f"  Güç      →  Toplam: {p_total} W")

            # Frekans
            freq = read_value(inst, REGISTERS["Frequency"])
            print(f"  Frekans  →  {freq} Hz")

            # Güç faktörü
            pf = read_value(inst, REGISTERS["Total_PF"])
            print(f"  PF       →  {pf}")

            # Enerji — en önemli
            kwh_import = read_value(inst, REGISTERS["Total_Import_kWh"])
            kwh_export = read_value(inst, REGISTERS["Total_Export_kWh"])
            wh_import  = int(kwh_import * 1000) if kwh_import else None
            print(f"\n  ⚡ Enerji (Import): {kwh_import} kWh  →  {wh_import} Wh")
            print(f"  ⚡ Enerji (Export): {kwh_export} kWh")

        except KeyboardInterrupt:
            print("\nDurduruldu.")
            break
        except Exception as e:
            print(f"Okuma hatası: {e}")

        time.sleep(2)

if __name__ == "__main__":
    main()

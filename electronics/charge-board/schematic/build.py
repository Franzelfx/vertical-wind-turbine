#!/usr/bin/env python3
"""Schematic of the charge board, as code (ADR-002, ADR-006). Generates charge-board.kicad_sch.

    uv run python electronics/charge-board/schematic/build.py

Do not edit the generated .kicad_sch files; change this file and rerun. Each pin names a net or NC:
silence is an error. Values come from `vawt.spec` where they cross into another domain, otherwise
from the datasheets named beside them (BQ25798: datasheets/bq25798-SLUSDV2C.pdf).
"""

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOARD = HERE.parent
ROOT = BOARD.parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src")]

from schgen import NC, Sheet, write_project  # noqa: E402
from vawt.spec import BATTERY, CHARGER, PROTECTION  # noqa: E402

ROOT_UUID = "6e0d9a54-3f2b-4a3e-9d27-5f1c7b0a4e11"
KICAD_CLI = shutil.which("kicad-cli") or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
EXTRA_LIBS = {"vawt": ROOT / "electronics" / "lib" / "symbols" / "vawt.kicad_sym"}
PDF = ROOT / "docs" / "images" / "charge-board-schematic.pdf"

GND = "GND"
R0603 = "Resistor_SMD:R_0603_1608Metric"
R1206 = "Resistor_SMD:R_1206_3216Metric"
R_AXIAL = "Resistor_THT:R_Axial_DIN0516_L15.5mm_D5.0mm_P20.32mm_Horizontal"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
C1206 = "Capacitor_SMD:C_1206_3216Metric"
SMC = "Diode_SMD:D_SMC"
SMB = "Diode_SMD:D_SMB"
SOD = "Diode_SMD:D_SOD-123F"
SOT23 = "Package_TO_SOT_SMD:SOT-23"
LED = "LED_SMD:LED_0603_1608Metric"
BLOCK2 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal"
BLOCK3 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3-5.08_1x03_P5.08mm_Horizontal"
XH2 = "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"
FUSE = "Fuse:Fuse_Blade_Mini_directSolder"
RELAY = "Relay_THT:Relay_SPDT_SANYOU_SRD_Series_Form_C"


def R(s, value, a, b, fp=R0603):
    return s.part("Device:R", "R", value, fp, {"1": a, "2": b})


def C(s, value, a, b=GND, fp=C0603):
    return s.part("Device:C", "C", value, fp, {"1": a, "2": b})


def caps(s, count, value, net, fp):
    for _ in range(count):
        C(s, value, net, GND, fp)


def nfet(s, value, g, d, src):
    return s.part("Transistor_FET:AO3400A", "Q", value, SOT23, {"G": g, "D": d, "S": src})


def schottky(s, value, anode, cathode, fp=SMC):
    return s.part("Device:D_Schottky", "D", value, fp, {"A": anode, "K": cathode})


def zener(s, value, anode, cathode, fp=SOD):
    return s.part("Device:D_Zener", "D", value, fp, {"A": anode, "K": cathode})


def input_stage() -> Sheet:
    s = Sheet("Input stage", "input_stage")
    s.note(
        "ADR-006: at 30 m/s the free-running generator reaches about 70 V; the charger takes 30 V."
    )
    s.note("K1 is normally closed and powered from the bus: above about 23 V it opens by itself.")
    s.note("Everything left of K1 sees the full open-circuit voltage: rate it for 100 V.")

    s.section("Generator, three-phase bridge (100 V Schottky)")
    s.part(
        "Connector_Generic:Conn_01x03",
        "J",
        "GENERATOR",
        BLOCK3,
        {"Pin_1": "PH_A", "Pin_2": "PH_B", "Pin_3": "PH_C"},
    )
    for phase in ("PH_A", "PH_B", "PH_C"):
        schottky(s, "SS510", phase, "BUS_RAW")
        schottky(s, "SS510", GND, phase)
    C(s, "100n 100V", "BUS_RAW", GND, C1206)

    s.section("Self-powered disconnect relay: no battery or firmware needed to protect the charger")
    relay = s.part(
        "Relay:SANYOU_SRD_Form_C",
        "K",
        "SRD-12VDC-SL-C",
        RELAY,
        {
            "1": "BUS_RAW",  # common
            "4": "VBUS_IN",  # normally closed: the contact the symbol draws at rest (checked, B2)
            "3": NC,  # normally open
            "2": "COIL_P",
            "5": "COIL_N",
        },
    )
    _ = relay
    for _ in range(3):  # parallel: spec.PROTECTION.relay_series_ohm and relay_series_watt
        R(
            s,
            f"{3 * PROTECTION.relay_series_ohm / 1000:.1f}k "
            f"{PROTECTION.relay_series_watt / 3:.0f}W",
            "BUS_RAW",
            "COIL_P",
            R_AXIAL,
        )
    zener(s, "12V 3W SMBJ", "COIL_N", "COIL_P", SMB)  # clamps the coil, also its flyback path
    s.part(
        "Transistor_FET:BSS123", "Q", "BSS123", SOT23, {"G": "REL_G", "D": "COIL_N", "S": GND}
    )  # 100 V: sees the whole bus when off
    R(s, "1M", "BUS_RAW", "REL_G")
    zener(s, "10V", GND, "REL_G")
    nfet(s, "AO3400A", "RELAY_RELEASE", "REL_G", GND)  # MCU pulses this to re-close K1
    R(s, "100k", "RELAY_RELEASE", GND)

    s.section("Charger side of the relay")
    s.part("Device:D_TVS", "D", "SMBJ26A", SMB, {"A1": GND, "A2": "VBUS_IN"})

    s.section("Brake: panel switch and resistor, off the board, only for parking in light wind")
    s.part("Connector_Generic:Conn_01x02", "J", "BRAKE", BLOCK2, {"Pin_1": "BUS_RAW", "Pin_2": GND})

    s.section("Sensing for the MCU (ADR-007): bus voltage and rotor speed")
    R(s, "1M", "BUS_RAW", "BUS_SENSE")
    R(s, "33k", "BUS_SENSE", GND)
    C(s, "100n", "BUS_SENSE")
    R(s, "1M", "PH_A", "TACH")
    R(s, "47k", "TACH", GND)
    zener(s, "3V0", GND, "TACH")
    return s


def charger() -> Sheet:
    s = Sheet("Charger", "charger")
    s.note("BQ25798 in buck-boost: 3.6-24 V in, 3S out. Without firmware it charges at its POR")
    s.note("defaults, 1 A to 12.6 V (Table 7-2), and the input follows the 3.6 V default VINDPM.")

    s.section("BQ25798 with the datasheet's capacitors (Table 5-1)")
    s.part(
        "vawt:BQ25798RQMR",
        "U",
        "BQ25798",
        "vawt:QFN-29_L4.0-W4.0-P0.40-TL-BQ25792RQMR",
        {
            "VBUS": "VBUS_IN",
            "VAC1": "VBUS_IN",
            "VAC2": "VBUS_IN",
            "ACDRV1": GND,
            "ACDRV2": GND,  # no input FETs (Table 5-1)
            "PMID": "PMID",
            "SW1": "SW1",
            "SW2": "SW2",
            "BTST1": "BTST1",
            "BTST2": "BTST2",
            "REGN": "REGN",
            "SYS": "SYS",
            "BAT": "BAT",
            "BATP": "BATP",
            "SDRV": "SDRV",
            "ILIM_HIZ": "REGN",  # Table 5-1: the maximum, firmware sets the real limit
            "TS": "TS",
            "PROG": "PROG",
            "D+": "DPDM",
            "D-": "DPDM",
            "SCL": "SCL",
            "SDA": "SDA",
            "~{INT}": "CHG_INT",
            "~{CE}": "CHG_DISABLE",
            "~{QON}": NC,
            "STAT": "CHG_STAT",
            "GND": GND,
        },
    )
    s.part("Device:L", "L", "2u2 8A", "Inductor_SMD:L_Sunlord_MWSA0518S", {"1": "SW1", "2": "SW2"})
    C(s, "47n", "BTST1", "SW1")
    C(s, "47n", "BTST2", "SW2")
    C(s, "4u7", "REGN")
    caps(s, 2, "10u 35V", "VBUS_IN", C1206)  # Table 5-1: 2 x 10 uF; 35 V for the 26 V clamp
    C(s, "100n 50V", "VBUS_IN")
    caps(s, 3, "10u 35V", "PMID", C1206)
    C(s, "100n 50V", "PMID")
    caps(s, 5, "10u 25V", "SYS", C0805)
    C(s, "100n 50V", "SYS")
    caps(s, 2, "10u 25V", "BAT", C0805)
    R(s, "100R", "BATP", "BAT")  # Table 5-1
    C(s, "1n 50V", "SDRV")  # Table 5-1, ship FET not used
    R(s, f"{CHARGER.prog_ohm / 1000:.1f}k", "PROG", GND)  # Table 7-1: 750 kHz, 3S

    s.section("Battery temperature (TS, 103AT-2 class NTC on the pack)")
    s.note(
        f"Charging stops outside {BATTERY.charge_temp_min_c:.0f}-"
        f"{BATTERY.charge_temp_max_c:.0f} degC: Li-ion must not charge below freezing."
    )
    R(s, "5.23k", "REGN", "TS")
    R(s, "30.1k", "TS", GND)
    s.part("Connector_Generic:Conn_01x02", "J", "PACK_NTC", XH2, {"Pin_1": "TS", "Pin_2": GND})

    s.section("Status and control lines")
    R(
        s, "10k", "CHG_DISABLE", GND
    )  # charges with the MCU asleep or absent; MCU drives high to stop
    R(s, "10k", "CHG_INT", "+3V3")
    R(s, "10k", "SCL", "+3V3")
    R(s, "10k", "SDA", "+3V3")
    R(s, "1k", "+3V3", "CHG_LED")
    s.part("Device:LED", "D", "green", LED, {"A": "CHG_LED", "K": "CHG_STAT"})

    s.section("Pack and load, each behind its own blade fuse")
    s.part("Connector_Generic:Conn_01x02", "J", "PACK", BLOCK2, {"Pin_1": "PACK_P", "Pin_2": GND})
    s.part("Device:Fuse", "F", f"{BATTERY.fuse_a}A mini blade", FUSE, {"1": "PACK_P", "2": "BAT"})
    s.part("Connector_Generic:Conn_01x02", "J", "LOAD", BLOCK2, {"Pin_1": "LOAD_P", "Pin_2": GND})
    s.part("Device:Fuse", "F", "5A mini blade", FUSE, {"1": "BAT", "2": "LOAD_P"})
    return s


def controller() -> Sheet:
    s = Sheet("Controller", "controller")
    s.note(
        "ESP32-C3: tracks the best input voltage by writing VINDPM (ADR-007), reports over Wi-Fi."
    )
    s.note("Deep sleep whenever the rotor stands: the charger's INT wakes it, on a GPIO 0-5 pin.")

    s.section("3.3 V from SYS (AP63203: 3.8-32 V, 22 uA no load)")
    s.part(
        "Regulator_Switching:AP63203WU",
        "U",
        "AP63203WU",
        "Package_TO_SOT_SMD:TSOT-23-6",
        {
            "IN": "SYS",
            "EN": "SYS",
            "GND": GND,
            "FB": "+3V3",
            "SW": "BUCK_SW",
            "BST": "BUCK_BST",
        },
    )
    C(s, "100n", "BUCK_BST", "BUCK_SW")
    s.part(
        "Device:L", "L", "4u7 2A", "Inductor_SMD:L_Sunlord_MWSA0402S", {"1": "BUCK_SW", "2": "+3V3"}
    )
    caps(s, 2, "10u 25V", "SYS", C0805)
    caps(s, 2, "22u", "+3V3", C0805)

    s.section("ESP32-C3 module")
    s.part(
        "RF_Module:ESP32-C3-WROOM-02",
        "U",
        "ESP32-C3-WROOM-02",
        "RF_Module:ESP32-C3-WROOM-02",
        {
            "3V3": "+3V3",
            "GND": GND,
            "EN": "MCU_EN",
            "IO0": "BUS_SENSE",  # ADC1
            "IO1": "TACH",
            "IO2": "STRAP2",
            "IO3": "CHG_INT",  # wake source, deep sleep only wakes on GPIO 0-5
            "IO4": "SDA",
            "IO5": "SCL",
            "IO6": NC,
            "IO7": "CHG_DISABLE",
            "IO8": "STRAP8",
            "IO9": "BOOT",
            "IO10": "RELAY_RELEASE",
            "IO18": "USB_DM",
            "IO19": "USB_DP",
            "IO20/RXD": NC,
            "IO21/TXD": NC,
        },
    )
    R(s, "10k", "MCU_EN", "+3V3")
    C(s, "1u", "MCU_EN")
    R(s, "10k", "STRAP2", "+3V3")
    R(s, "10k", "STRAP8", "+3V3")
    R(s, "10k", "BOOT", "+3V3")
    caps(s, 1, "10u 25V", "+3V3", C0805)
    C(s, "100n", "+3V3")
    s.part(
        "Switch:SW_Push",
        "SW",
        "BOOT",
        "Button_Switch_SMD:SW_SPST_PTS645Sx43SMTR92",
        {"1": "BOOT", "2": GND},
    )

    s.section("USB-C for flashing with the lid off: the board stays powered from the pack")
    s.part(
        "Connector:USB_C_Receptacle_USB2.0_16P",
        "J",
        "USB-C",
        "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
        {
            "VBUS": NC,
            "GND": GND,
            "CC1": "USB_CC1",
            "CC2": "USB_CC2",
            "D+": "USB_DP",
            "D-": "USB_DM",
            "SBU1": NC,
            "SBU2": NC,
            "SHIELD": GND,
        },
    )
    R(s, "5.1k", "USB_CC1", GND)
    R(s, "5.1k", "USB_CC2", GND)

    s.section("Mounting")
    for _ in range(4):
        s.part(
            "Mechanical:MountingHole",
            "H",
            "M3",
            "MountingHole:MountingHole_3.2mm_M3",
            {},
            bom=False,
        )
    return s


def all_sheets() -> list[Sheet]:
    return [input_stage(), charger(), controller()]


def main() -> None:
    files = write_project(
        BOARD / "charge-board.kicad_sch", ROOT_UUID, "charge-board", all_sheets(), EXTRA_LIBS
    )
    for path in files:
        print("wrote", path.relative_to(ROOT))
    PDF.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [KICAD_CLI, "sch", "export", "pdf", "-o", str(PDF), str(BOARD / "charge-board.kicad_sch")],
        check=True,
        capture_output=True,
    )
    print("wrote", PDF.relative_to(ROOT))


if __name__ == "__main__":
    main()

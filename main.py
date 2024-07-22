import os
import csv
import time
import subprocess
import sys
import select
import pyperclip

# Predefined list of schools
schools = {
    "1": "Akkarfjord oppvekstsenter",
    "2": "Baksalen skole",
    "3": "Breilia skole",
    "4": "Fjordtun skole",
    "5": "Forsøl skole",
    "6": "Fuglenes skole",
    "7": "Kokelv oppvekstsenter",
    "8": "Kvalsund skole",
    "9": "Reindalen skole",
    "10": "Voksenopplæringa",
    "11": "Barnehager",
    "12": "Ukjent",

}

# Predefined list of statuses
statuses = {
    "1": "Visuelt ok",
    "2": "Sprekk",
    "3": "USB feil",
    "4": "Knust"
}

# Default values for status and school
current_status = None
current_school = None

def load_agreements(folder_path):
    agreements = {}
    total_devices = 0
    total_confirmed = 0
    for filename in os.listdir(folder_path):
        if filename.endswith(".csv"):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, mode='r', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    serial_number = row['serial_number']
                    agreements[serial_number] = {
                        'file': file_path,
                        'row': row
                    }
                    total_devices += 1
                    if row.get('confirmed') and row['confirmed'].lower() == 'true':
                        total_confirmed += 1
    print(f"Loaded agreements for {total_devices} devices.")
    print(f"Total confirmed devices: {total_confirmed}")
    return agreements

def get_connected_devices():
    try:
        output = subprocess.check_output(['idevice_id', '-l'], text=True)
        device_udids = output.strip().split('\n')
        return [udid for udid in device_udids if udid]
    except subprocess.CalledProcessError as e:
        print(f"Error executing idevice_id: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    return []

def process_serial_number(serial_number, agreements):
    if serial_number:
        pyperclip.copy(serial_number)
        print(f"Found matching iPad with serial number: {serial_number}")
        agreement = agreements.get(serial_number)
        if agreement:
            if agreement['row'].get('confirmed') and agreement['row']['confirmed'].lower() == 'true':
                if not prompt_for_update():
                    return
            status = prompt_for_status()
            school = prompt_for_school()
            update_csv(agreement['file'], serial_number, status, school)
            print(f"Updated CSV for iPad with serial number: {serial_number}")
        else:
            print(f"No agreement found for iPad with serial number: {serial_number}")
    else:
        print(f"Could not retrieve serial number.")

def get_device_info(udid, retries=3, delay=5):
    while retries > 0:
        try:
            output = subprocess.check_output(['ideviceinfo', '-u', udid], text=True)
            for line in output.split('\n'):
                if line.startswith("SerialNumber:"):
                    serial_number = line.split(":")[1].strip().upper()
                    return serial_number
        except subprocess.CalledProcessError as e:
            print(f"Error executing ideviceinfo for {udid}: {e}")
            if "Pairing dialog response pending" in str(e):
                print("Please unlock the device and confirm the 'Trust This Computer' prompt.")
            else:
                print("Could not connect to the device. Retrying...")
        except Exception as e:
            print(f"Unexpected error: {e}")
        
        retries -= 1
        if retries > 0:
            print(f"Retrying in {delay} seconds... ({retries} retries left)")
            time.sleep(delay)
    return None

def update_csv(file_path, serial_number, status, school):
    rows = []
    with open(file_path, mode='r', newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['serial_number'] == serial_number:
                row['confirmed'] = 'True'
                row['status'] = status
                row['school'] = school
            rows.append(row)

    with open(file_path, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

def prompt_for_update():
    while True:
        update = input("Device already confirmed. Do you want to update it again? (yes/no) [default: no]: ").strip().lower()
        if update == 'yes':
            return True
        elif update == 'no' or update == '':
            return False
        else:
            print("Please enter 'yes' or 'no'.")

def prompt_for_manual_serial():
    serial_number = input("Enter the serial number: ").strip().upper()
    return serial_number

def prompt_for_status():
    global current_status
    print("Select status:")
    for key, value in statuses.items():
        print(f"{key}: {value}")
    status_input = input(f"Enter status number [Current: {current_status}]: ")
    if status_input and status_input in statuses:
        current_status = statuses[status_input]
    return current_status

def prompt_for_school():
    global current_school
    print("Select school:")
    for key, value in schools.items():
        print(f"{key}: {value}")
    school_input = input(f"Enter school number [Current: {current_school}]: ")
    if school_input and school_input in schools:
        current_school = schools[school_input]
    return current_school

def main(folder_path):
    agreements = load_agreements(folder_path)

    while True:
        device_udids = get_connected_devices()
        if not device_udids:
            print("No iPads found. Press 'M' to manually enter a serial number.")
            # Wait for a few seconds to allow user to press 'M'
            input_ready, _, _ = select.select([sys.stdin], [], [], 3)
            if input_ready:
                user_input = sys.stdin.readline().strip().lower()
                if user_input == 'm':
                    serial_number = prompt_for_manual_serial()
                    process_serial_number(serial_number, agreements)

        else:
            for udid in device_udids:
                print(f"Checking device with UDID: {udid}")
                serial_number = get_device_info(udid)
                process_serial_number(serial_number, agreements)

        print("Waiting for new device...")
        time.sleep(5)


if __name__ == "__main__":
    folder_path = "agreements"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    try:
        main(folder_path)
    except KeyboardInterrupt:
        print("\nExiting...")


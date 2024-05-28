#!/usr/bin/env python

import sys
import serial
import time
from jinja2 import Template
import credentials

def send_command(serial_connection, command, delay=1):
    """
    Send a command to the Cisco device via the serial connection and print the response.
    
    Args:
        serial_connection (serial.Serial): The serial connection to the device.
        command (str): The command to send.
        delay (int): Delay in seconds after sending the command (default: 1).
    """
    # Write the command to the serial connection
    serial_connection.write(command.encode('utf-8') + b'\r')
    
    # Wait for the command to be processed
    time.sleep(delay)
    
    # Read the response
    response = serial_connection.read_all().decode('utf-8')
    
    return response

def read_template_to_list(template_path):
    """
    Read a Jinja2 template file and return its content as a list of lines.
    
    Args:
        template_path (str): The file path of the Jinja2 template.
        
    Returns:
        list: A list of lines from the template file.
    """
    try:
        # Open the template file and read its content
        with open(template_path, 'r') as file:
            lines = file.readlines()
        
        # Strip newline characters from each line
        lines = [line.strip() for line in lines]
        
        return lines
    
    except FileNotFoundError:
        print(f"Error: The file at {template_path} was not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []
    

def deploy_onboarding_configuration(console, configuration):
    """
    Deploy the onboarding configuration via console.

    Args:
        console: The active console connection
        configuration (list): Configuration commands saved in a list.

    Returns:
        Nothing.
    """
    print("Enabling configuration mode.")
    send_command(console, "")
    response = send_command(console, "config-transaction", 5)
    
    if "Router(config)#" in response:
        print("Configuration mode enabled.")
        print("Sending the onboarding configuration.")
        send_command(console, "")
        for line in configuration:
            print(f"Sending command: {line}")
            send_command(console, line, 2)
        print("All configuration sent.")

    else:
        print("Check if the device has already been configured. If not, try again.")
        sys.exit(0)

def stop_pnpa_service(console):
    """
    """
    # Stop the PnP service if required so that onboarding configuration can be applied.
    #!!! When the system is ready it produces "All daemons up" message
    print("Detecting if PnP service must be stopped.")
    send_command(console, "")
    response = send_command(console, "show sdwan tenant-summary", 3)

    if "terminate PnP with the following command" in response:
        print("PnP service is running. Stopping it now!")
        print("Waiting for 180 seconds.")
        send_command(console, "")
        response = send_command(console, "pnpa service discovery stop", 180)
    else:
        print("PnP service is not running. Moving to apply the onboarding template.")

def disable_console_logging(console):
    """
    Disable console logging to avoid broken configuration lines and console congestion.

    Args:
        console: The active console connection.

    Returns:
        Nothing.
    """
    # Disabling logging to the console to improve accuracy of responses.
    print("Disabling console logging.")
    send_command(console, "")
    commands = ["config-transaction", "no logging console", "commit", "exit"]
    for command in commands:
        print(f"Sending command: {command}")
        send_command(console, command, 3)

def run_configuration_audit(console, configuration):
    """
    """
    # Verify that all onboarding configuration was committed.
    send_command(console, "term length 0")
    send_command(console, "show sdwan running-config")
    time.sleep(15)
    confirm_configuration = console.readlines()
    
    # Cleaning the configuration to include only critical configuration lines.
    clean_configuration = list(filter(lambda line: "!" not in line, configuration))
    clean_configuration = list(filter(lambda line: "exit" not in line, clean_configuration))
    clean_configuration = list(filter(lambda line: "request" not in line, clean_configuration))
    clean_configuration = list(filter(lambda line: "commit" not in line, clean_configuration))
    clean_configuration = list(filter(lambda line: "no shutdown" not in line, clean_configuration))

    audit_results = []
    for config_line in clean_configuration:
        for output_line in confirm_configuration:
            # Normalizing the format of expected and observed value by removing whitespaces and 
            # quote marks. 
            expected_value = config_line.replace(" ", "")
            expected_value = expected_value.replace('"', '')
            observed_value = output_line.decode("utf-8").replace(" ", "")

            if expected_value in observed_value:
                if config_line not in audit_results:
                    audit_results.append(config_line)

    if audit_results.sort() == clean_configuration.sort():
        print("Configuration audit passed!")
        send_command(console, "term length 24")
        console.close()
    else:
        print("Configuration audit not passing.")
        send_command(console, "term length 24")
        console.close()

def install_root_ca_cert(console):
    """
    """
    try:
        command = "request platform software sdwan root-cert-chain install usb0:ca.crt"
        send_command(console, command, 10)
        print("Certificate installed.")
    except Exception as e:
        print("Error: Certificate installation failed. Correct the issue.")

def access_prompt(console, startup_screen):
    """
    """
    try: 
        if "Username" in startup_screen:
            print("User Access Verification required!")
            print("Entering username.")
            response = send_command(console, credentials.username)
            if "Password:" in response:
                print("Entering password.")
                response = send_command(console, credentials.password)
                if "Enter new password:" in response:
                    print("Applying new password.")
                    response = send_command(console, credentials.new_password)
                    print("Confirming the new password.")
                    response = send_command(console, credentials.new_password)
        
        # If loging isn't required determine the current prompt. 

        elif "Router#" in startup_screen:
            print("User logged in and in exec mode.")

        elif "Router(config)#" in startup_screen:
            print("User logged in and in configuration mode.")

        else:
            print("Error: Can't determine the state of the console", 
                    "Please try again or check if the device has been onboarded already.")
            sys.exit(0)

    except IndexError as e:
        print("Error: Can't determine the state of the console", 
                "Please try again or check if the device has been onboarded already.")
        sys.exit(0)


def main():
    # Read the template    
    template_path = './templates/sdwan_router_onboarding.j2'
    configuration = read_template_to_list(template_path)

    # Provide the COM port or device as an argument.
    try:
        port = sys.argv[1]
    except IndexError as e:
        print("Error: Provide the COM port or serial device as an argument.",
              "For example: ./blue.py /dev/tty.usbserial-1432320")
        sys.exit(0)

    try:
        # Login to the device via console.
        
        console = serial.Serial(port=port, baudrate=9600, timeout=1)
        if not console.is_open:
            print("Console is not open.")
            sys.exit(0)
        print("Console connection is open.")
        print("Waking up the console.")
        send_command(console, "\x03")
        startup_screen = send_command(console, "")

        access_prompt(console, startup_screen)
        stop_pnpa_service(console)
        disable_console_logging(console)
        deploy_onboarding_configuration(console, configuration)
        run_configuration_audit(console, configuration)


    except OSError as e:
        print("Error: Console connection is busy. Unplug and re-plug the cable.")

if __name__ == "__main__":
    main()

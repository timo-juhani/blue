#!/usr/bin/env python

"""
Blue - Automate Onboarding via Console Cable
"""

__author__ = "Timo-Juhani Karjalainen (@timo-juhani)"
__copyright__ = "Copyright (c) 2024 Timo-Juhani Karjalainen"
__license__ = "MIT"
__version__ = "0.0.1"
__email__ = "tkarjala@cisco.com"
__status__ = "Prototype"

# IMPORTS

import sys
import serial
import time
from jinja2 import Template
import pyfiglet
import termcolor
import credentials
import argparse
import logging

# FUNCTION DEFINITIONS

def create_banner():
    """
    Create a banner to show when the program is executed.
    """
    banner = pyfiglet.figlet_format("Blue", font="speed")
    print("\n")
    print(termcolor.colored(banner, "blue", attrs=["bold"]))
    print("Conf-t and here we go again!")
    print("v."+__version__)
    print("\n")


def create_parser():
    """
    Create a parser that the user can use to provide program arguments.
    Returns the parser.
    """
    parser = argparse.ArgumentParser(description="Device onboarding via Cisco console.")
    parser.add_argument("-s", "--serial", type=str, help="Serial port.")
    return parser


class CustomFormatter(logging.Formatter):
    """
    Formatter class for setting the message formats and colors used by the logger. 
    """
    grey = '\x1b[38;21m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'
    log_format = "%(asctime)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + log_format + reset,
        logging.INFO: grey + log_format + reset,
        logging.WARNING: yellow + log_format + reset,
        logging.ERROR: red + log_format + reset,
        logging.CRITICAL: bold_red + log_format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

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
        logging.error(f"The file at {template_path} was not found.")
        return []
    except Exception as e:
        logging.error(f"An error occurred: {e}")
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
    logging.info("Enabling configuration mode.")
    send_command(console, "")
    response = send_command(console, "config-transaction", 5)
    
    if "Router(config)#" in response:
        logging.info("Configuration mode enabled.")
        logging.info("Sending the onboarding configuration.")
        send_command(console, "")
        for line in configuration:
            logging.info(f"Sending command: {line}")
            send_command(console, line, 2)
        logging.info("All configuration sent.")

    else:
        logging.warning("Check if the device has already been configured. If not, try again.")
        sys.exit(0)

def stop_pnpa_service(console):
    """
    """
    # Stop the PnP service if required so that onboarding configuration can be applied.
    #!!! When the system is ready it produces "All daemons up" message
    logging.info("Detecting if PnP service must be stopped.")
    send_command(console, "")
    response = send_command(console, "show sdwan tenant-summary", 3)

    if "terminate PnP with the following command" in response:
        logging.info("PnP service is running. Stopping it now!")
        logging.info("Waiting for 180 seconds.")
        send_command(console, "")
        response = send_command(console, "pnpa service discovery stop", 180)
    else:
        logging.info("PnP service is not running. Moving to apply the onboarding template.")

def disable_console_logging(console):
    """
    Disable console logging to avoid broken configuration lines and console congestion.

    Args:
        console: The active console connection.

    Returns:
        Nothing.
    """
    # Disabling logging to the console to improve accuracy of responses.
    logging.info("Disabling console logging.")
    send_command(console, "")
    commands = ["config-transaction", "no logging console", "commit", "exit"]
    for command in commands:
        logging.info(f"Sending command: {command}")
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
        logging.info("Configuration audit passed!")
        send_command(console, "term length 24")
    else:
        logging.warning("Configuration audit not passing.")
        send_command(console, "term length 24")

def install_root_ca_cert(console):
    """
    """
    try:
        command = "request platform software sdwan root-cert-chain install usb0:ca.crt"
        send_command(console, command, 10)
        logging.info("Certificate installed.")
    except Exception as e:
        logging.error("Certificate installation failed. Correct the issue.")

def access_prompt(console, startup_screen):
    """
    """
    try: 
        if "Username" in startup_screen:
            logging.info("User Access Verification required!")
            logging.info("Entering username.")
            response = send_command(console, credentials.username)
            if "Password:" in response:
                logging.info("Entering password.")
                response = send_command(console, credentials.password)
                if "Enter new password:" in response:
                    logging.info("Applying new password.")
                    response = send_command(console, credentials.new_password)
                    logging.info("Confirming the new password.")
                    response = send_command(console, credentials.new_password)
        
        # If loging isn't required determine the current prompt. 

        elif "Router#" in startup_screen:
            logging.info("User logged in and in exec mode.")

        elif "Router(config)#" in startup_screen:
            logging.info("User logged in and in configuration mode.")

        else:
            logging.error("Can't determine the state of the console", 
                    "Please try again or check if the device has been onboarded already.")
            sys.exit(0)

    except IndexError as e:
        msg = "Can't determine the state of the console. Please try again or check if the device has been onboarded already."
        logging.error(msg)
        sys.exit(0)

# MAIN FUNCTION DEFINITION

def main():
    # Print the welcome banner.
    create_banner()

    # Create the command parser.
    parser = create_parser()
    args = parser.parse_args()

    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.setFormatter(CustomFormatter())
    handlers = [stdout_handler]

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s - %(message)s',
        handlers=handlers
    )

    logging.getLogger("application")

    # Read the template    
    template_path = './templates/sdwan_router_onboarding.j2'
    configuration = read_template_to_list(template_path)

    # Provide the COM port or device as an argument.
    try:
        port = args.serial
    except IndexError as e:
        logging.error("Provide the COM port or serial device as an argument.",
              "For example: ./blue.py /dev/tty.usbserial-1432320")
        sys.exit(0)

    try:
        # Login to the device via console.
        # Initiate the connection by sending CTRL+C and ENTER.
        console = serial.Serial(port=port, baudrate=9600, timeout=1)
        if not console.is_open:
            logging.error("Console is not open.")
            sys.exit(0)
        logging.info("Console connection is open.")
        logging.info("Waking up the console.")
        send_command(console, "\x03")
        startup_screen = send_command(console, "")

        # Access the prompt show in console currently.
        # Make sure the execution starts from exec mode.
        access_prompt(console, startup_screen)

        # Stopping pnpa service so that the device can be configured manually.
        stop_pnpa_service(console)

        # Disabling console logging to avoid potential issues caused by colliding commands and log
        # messages.
        disable_console_logging(console)

        # Deploy the configuration based on the onboarding template.
        deploy_onboarding_configuration(console, configuration)

        # Run an audit to make sure all key commands were saved to the running device configuration.
        run_configuration_audit(console, configuration)

        # Install the root certificate so that the device can connect to controller(s).
        install_root_ca_cert(console)

        console.close()

    except OSError as e:
        logging.error("Console connection is busy. Unplug and re-plug the cable.")

# EXECUTE MAIN FUNCTION

if __name__ == "__main__":
    main()

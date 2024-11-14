#   Authors:        Aidan Whitman, Noah Herron
#   Date:           11/09/2024
#   Professor:      Professor Shannigrahi
#   Assignment:     Program 3
#   Description:    This program is the server for the detection system.

#Imports
import argparse
import socket
import sys
import threading
import json
import RPi.GPIO as GPIO
import time

#Constants
LED_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

def blink_led(duration, num_blinks):
    #Blinking the LED
    print("Blinking LED")
    for _ in range(num_blinks):
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(duration)

def handle_client(data, addr, log_location, udp_socket):
    print("Entered handle_client")
    try:
        #Decodes the data and parse the JSON file
        headerLength = 12

        if len(data) < headerLength:
            raise ValueError("Data is too short for JSON")

        header = data[:headerLength]
        json_payload = data[headerLength:]

        message = json_payload.decode('utf-8')
        parsed_data = json.loads(message)

        #Prints
        print(f"Received message from {addr}: {message}")

        #Logs
        with open(log_location, 'a') as log_file:
            log_file.write(f"Received from {addr[0]}: {data.decode()}\n")

        #Process based on message type
        if parsed_data.get("type") == "HELLO":
            print("Received HELLO")
            response = json.dumps({"status": "200 OK", "message": "Hello received"})
        elif parsed_data.get("type") == "DATA":
            #Extract the data
            print("Received DATA")
            duration = parsed_data.get("duration")
            num_blinks = parsed_data.get("num_blinks")

            if duration is not None and num_blinks is not None:
                #Acknowledge the data
                response = json.dumps({"status": "200 OK", "message": "Data received"})

                with open(log_location, 'a') as log_file:
                    log_file.write(f"Acknowledged data from {addr[0]}: {duration}, {num_blinks}\n")

            else:
                response = json.dumps({"status": "400 Bad Request", "message": "Missing duration or num_blinks"})
        
        elif parsed_data.get("type") == "MOTION":
            #Handle motion data
            print("Motion detected")
            with open(log_location, 'a') as log_file:
                log_file.write(f"Motion Detected\n")

            #Blink the LED
            blink_times = parsed_data.get("num_blinks", 5)
            blink_duration = parsed_data.get("duration", 0.5)
            blink_led(blink_duration, blink_times)

            response = json.dumps({"status": "200 OK", "message": "Motion data received"})

        else:
            response = json.dumps({"status": "400 Bad Request", "message": "Invalid message type"})

        #Send the response
        udp_socket.sendto(response.encode(), addr)
        print(f"Sent response to {addr}: {response}")

    except json.JSONDecodeError:
        #Handle JSON decode error
        print("Invalid JSON")
        error_response = json.dumps({"status": "400 Bad Request", "message": "Invalid JSON"})
        udp_socket.sendto(error_response.encode(), addr)

    except UnicodeDecodeError as e:
        print(f"UnicodeDecodeError: {e}")
    
#Main Function
def main():
    #Parse the arguments
    parser = argparse.ArgumentParser(description='Light Server')

    #Define the arguments
    parser.add_argument('port', type=int, help='Port to connect to')
    parser.add_argument('log_location', type=str, help='Location to store logs')

    #Parse the arguments
    args = parser.parse_args()

    #Retrieve the arguments
    port = args.port
    log_location = args.log_location

    #Print the arguments
    print(f"Port: {port}")
    print(f"Log Location: {log_location}")

    #Validate the port number
    if not (1 <= port <= 65535):
        print("Error: Port number must be between 1 and 65535.")
        sys.exit(1)

    #Set up the UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('0.0.0.0', port))

    print(f"UDP server is listening on port {port}...")
    
    #Main loop
    try:
        while True:
            #Handle the clients
            print('Waiting for a client...')
            data, addr = udp_socket.recvfrom(1024)
            print('Client connected:', addr)
            client_thread = threading.Thread(target=handle_client, args=(data, addr, log_location, udp_socket))
            client_thread.start()

    except KeyboardInterrupt:
        print("Keyboard Interrupt")

    finally:
        #Close the socket
        print("Closing the socket...")
        udp_socket.close()
        GPIO.cleanup()

#Run the main function
if __name__ == '__main__':
    main()
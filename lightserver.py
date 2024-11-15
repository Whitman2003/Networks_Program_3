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
import struct

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

def create_header(sequence_number, ack_number, flags):
    header = struct.pack('!II I', sequence_number, ack_number, flags)
    return header

def handle_client(data, addr, log_location, udp_socket):
    print("Entered handle_client")
    try:
        #Decodes the data and parse the JSON file
        headerLength = 12

        if len(data) < headerLength:
            raise ValueError("Data is too short for JSON")

        header = data[:headerLength]
        flags_field = struct.unpack('!I', header[8:12])[0] & 0b111

        print(f"Check flags: {flags_field}")

        #SYN
        if flags_field == 0b001:
            print(f"Received SYN from {addr}. Sending SYN|ACK...")
            sequence_number = struct.unpack('!I', header[:4])[0]
            ack_number = struct.unpack('!I', header[4:8])[0] + 1
            syn_ack_packet = create_header(sequence_number+1, ack_number, 0b011)
            udp_socket.sendto(syn_ack_packet, addr)

        #ACK
        elif flags_field == 0b010:
            print(f"Received ACK from {addr}. Handshake complete.")
            print("Connection established.")

            print(f"Length of data: {len(data)}")
            if len(data) > headerLength:
                json_payload = data[headerLength:]

                #Decode
                try:
                    message = json.loads(json_payload.decode('utf-8'))
                    print(f"Received message: {message}")

                    with open(log_location, 'a') as log_file:
                        log_file.write(f"Received message: {message}\n")

                    print(f"Message type: {message.get('type')}")
                    if message.get("type") == "MOTION":
                        print("Motion Detected.")
                        with open(log_location, 'a') as log_file:
                            log_file.write(f"Motion detected at {time.strftime('%Y-%m-%d-%H:%M:%S')}\n")

                        #Blink the LED
                        blink_times = message.get("num_blinks", 5)
                        blink_duration = message.get("duration", 0.5)
                        blink_led(blink_duration, blink_times)

                        response = json.dumps({"status": "200 OK", "message": "Motion Detected"})

                    elif message.get("type") == "DATA":
                        print("Received data.")
                        duration = message.get("duration")
                        num_blinks = message.get("num_blinks")
                    
                        if duration is not None and num_blinks is not None:
                            response = json.dumps({"status": "200 OK", "message": "LED blinked."})
                            with open(log_location, 'a') as log_file:
                                log_file.write(f"LED blinked {num_blinks} times for {duration} seconds.\n")
                        else:
                            response = json.dumps({"status": "400 Bad Request", "message": "Invalid message type."})
                
                    else:
                        response = json.dumps({"status": "400 Bad Request", "message": "Invalid message type."})

                    udp_socket.sendto(response.encode('utf-8'), addr)
                    print(f"Sent response to {addr}: {response}")

                except json.JSONDecodeError:
                    print("Invalid JSON data.")
                    error_response = json.dumps({"status": "400 Bad Request", "message": "Invalid JSON data."})
                    udp_socket.sendto(error_response.encode('utf-8'), addr)

            else:
                print(f"Received unexpected flags.")

    except Exception as e:
        print(f"Error handling client: {e}")
        
    
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
            handle_client(data, addr, log_location, udp_socket)

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
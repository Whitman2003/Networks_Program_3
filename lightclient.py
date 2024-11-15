#   Authors:        Aidan Whitman, Noah Herron
#   Date:           11/09/2024
#   Professor:      Professor Shannigrahi
#   Assignment:     Program 3
#   Description:    This program is the client for the detection system.

#Imports
import argparse
import socket
import sys
import json
import struct
import time
import RPi.GPIO as GPIO

#Set the GPIO mode
GPIO.setmode(GPIO.BCM)
PIR_PIN = 17

#Set the GPIO pin
GPIO.setup(PIR_PIN, GPIO.IN)

#Send the motion signal
def send_motion(server_ip, server_port, log_location, sock):
    #Set variables
    sequence_number = 1000
    ack_number = 1001
    motion_data = {"type": "MOTION", "message": "MOTION"}

    #Log the motion
    with open(log_location, 'a') as log_file:
        log_file.write(f"Motion detected at {time.strftime('%Y-%m-%d-%H:%M:%S')}\n")

    #Set the message
    message = json.dumps(motion_data).encode('utf-8')
    flags = 0b010
    header = create_header(sequence_number, ack_number, flags)
    full_message = header + message

    #Send the motion data
    if sock.fileno() != -1:
        try:
            print("Sending motion data...")
            sock.sendto(full_message, (server_ip, server_port))
            print("Motion data sent.")
        except Exception as e:
            print("Error sending motion data. {e}")
    else:
        print("Socket is invalid.")
        return

#Wait for the motion
def wait(server_ip, server_port, log_location, sock):
    print("Waiting for motion...")
    while True:
        #Send when motion is detected
        if GPIO.input(PIR_PIN):
            send_motion(server_ip, server_port, log_location, sock)
            time.sleep(2)
        time.sleep(0.1)

#Payload Handling
def create_header(sequence_number, ack_number, flags):
    #Set the flags: 29 unused, 1 ACK, 1 SYN, and 1 FIN
    flags_field = (0 << 3) | (flags & 0b111)

    #Pack the values into a 12-byte structure
    header = struct.pack('!II I', sequence_number, ack_number, flags_field)

    #Display
    return header

#Send the packet
def send_packet(sock, payload, server_ip, server_port):
    print("Sending packet...")
    sock.sendto(payload, (server_ip, server_port))

#Create the payload
def create_payload(duration, num_blinks, sequence_number, ack_number):
    #Create the header
    header = create_header(sequence_number, ack_number, flags=0b010)

    #Create the data
    data = {"duration": duration, "num_blinks": num_blinks}

    #Convert to a JSON string and encode
    payload_data = json.dumps(data).encode('utf-8')

    #Combine the header and payload
    full_payload = header + payload_data
    print("Payload created.")
    return full_payload

#Initialize the handshake
def initiate_handshake(server_ip, server_port, duration, num_blinks):
    #Create the socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    #SYN or Initial
    sequence_number = 1000
    ack_number = 1001
    syn_packet = create_header(sequence_number, ack_number, flags=0b001)
    print("Sending SYN...")
    send_packet(sock, syn_packet, server_ip, server_port)

    #Wait for SYN|ACK
    sock.settimeout(5)
    try:
        data, addr = sock.recvfrom(1024)
        print("Received SYN|ACK...")

        #Check if there are flags
        response_flags = struct.unpack('!I', data[8:12])[0] & 0b111
        if response_flags == 0b011:
            print("SYN|ACK received")

            #ACK
            ack_number = struct.unpack('!I', data[4:8])[0] + 1
            ack_packet = create_header(sequence_number + 1, ack_number, flags=0b010)
            send_packet(sock, ack_packet, server_ip, server_port)
            print("The handshake is complete and the last ACK has been sent.")

    except socket.timeout:
        print("The connection timed out.")
        sock.close()
        return
    
    #Close the socket
    sock.close()

#FIN packet
def send_fin(sock, server_ip, server_port, sequence_number, ack_number):
    fin_packet = create_header(sequence_number, ack_number, flags=0b100)
    send_packet(sock, fin_packet, server_ip, server_port)
    print("FIN packet sent.")

#Main function
def main():
    #Parse the arguments
    parser = argparse.ArgumentParser(description='Light Client')

    #Define the arguments
    parser.add_argument('server_ip', type=str, help='IP address of the server')
    parser.add_argument('port', type=int, help='Port to connect to')
    parser.add_argument('log_location', type=str, help='Location to store logs')
    duration = 5
    num_blinks = 5

    #Parse the arguments
    args = parser.parse_args()

    ip = args.server_ip
    port = args.port
    log_location = args.log_location

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    #Use
    initiate_handshake(ip, port, duration, num_blinks)
    print("Handshake complete.")

    try:
        #Start the motion detection
        print("Starting motion detection...")
        wait(ip, port, log_location, sock)

    except KeyboardInterrupt:
        print("Exiting...")

    finally:
        #Send the FIN packet
        print("Sending FIN packet...")
        send_fin(sock, ip, port, 1002, 3)

        #Close the socket
        GPIO.cleanup()
        sock.close()
        sys.exit()

if __name__ == '__main__':
    main()
import threading
import socket
import os



port = 4352
host_v6 = socket.getaddrinfo('localhost', port, family=socket.AF_INET6)[0][4]
host_v4 = socket.gethostbyname(socket.gethostname())
ty = input("WHAT KIND OF CONNECTION WOULD YOU LIKE?(IPV6/IPV4)?  ")
if ty.lower() == "ipv6":
    client = socket.socket(socket.AF_INET6,socket.SOCK_STREAM)
    client.setsockopt(socket.IPPROTO_IPV6,socket.IPV6_V6ONLY,0)
    client.connect(host_v6)

else:
    client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        client.connect((host_v4,port))
    except:
        print("Connection failed!")
username = input("ENTER USERNAME: ")


def recieve():
    while True:
        try:
            message = client.recv(1024).decode()
            if message == 'USERN':
                client.send(username.encode())  #send to server
            else:
                print(message)
        except:
            client.close()
            break

def write_msg():
    ACTIVE = True
    while ACTIVE:
        message = f'{username}: {input("")}' #getting messages from user
        con = message[len(username)+2:]
        if "direct-" in con:
            content = message.split(": ")[2] #get actual message
            reciever = message.split(": ")[1].split("-")[1] #get the client that recieves
            client.send(f'DIR~{reciever}:{content}'.encode())

        elif "group-" in con: #create a group
            content = message.split("-")[1].split(":")
            group_id = content[0]
            group_members = content[1]
            client.send(f"GRP~{group_id}:{group_members}".encode())
        elif "offline" in con:
            client.send("OFF".encode())
        elif "online" in con:
            client.send("ON".encode())
        else:
            client.send(message.encode())

    

thread1 = threading.Thread(target=recieve)
thread1.start()

thread2 = threading.Thread(target=write_msg)
thread2.start()
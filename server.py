import threading
import socket
from datetime import datetime
import queue


host = "" 
port = 4352
addr = (host,port)




server = socket.create_server(addr, family=socket.AF_INET6,dualstack_ipv6=True)  #TCP over ipv6
server.listen()
print(f"server listening on {host} {port}")

group_dict = {}  #dictionary with group_id -> clients_lists
clients =[] #all clients
usernames = []  #all usernames

clients_messages = {} #{username -> (client,status , msg_queue)}


def broadcast(message):
    for client in clients:
        us = usernames[clients.index(client)]
        if us in clients_messages and clients_messages[us][1]:
            client.send(message)
        else:
            clients_messages[us][2].append(message)  #enqueue messages if offline 

def handle(client):
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    client_index = clients.index(client)
    name = usernames[client_index]
    ACTIVE = True
    while ACTIVE:
        message = client.recv(1024).decode() #recieve a message from the client
        group_id = message.split(': ')

        #direct messages to clients
        if message.startswith("DIR"):
            index_sender = clients.index(client)
            #sender = usernames[index_sender]
            recieved_message = message.split('~')
            reciever_username = recieved_message[1].split(":")[0]
            index_to_recieve = usernames.index(reciever_username)
            reciever = clients[index_to_recieve]
            actual_msg = f'[DIRECT][{time_now}]{name}: {recieved_message[1].split(":")[1]}'

            if clients_messages[reciever_username][1]:
                reciever.send(actual_msg.encode())
            else:
                client.send(f"{reciever_username} is offline".encode())
                clients_messages[reciever_username][2].append(actual_msg.encode())

        elif message.startswith("GRP"):
         
            group_id = message.split('~')[1].split(':')[0]
            if group_id in group_dict:
                index_sender = clients.index(client)
                sender = usernames[index_sender]
                text_to_group = message.split("~")[1].split(":")[1]


                #leaving the group chat
                if text_to_group == "/leave":
                    username_to_leave_ind = clients.index(client)
                    user_leaving = usernames[username_to_leave_ind]
                    group_dict[group_id].remove((name,client,True))
                    for (u,c,o) in group_dict[group_id]:
                        c.send(f'[{group_id}][{time_now}]{user_leaving} left the chat'.encode())
                
               
                #kicking members from chat
                if "/kick" in text_to_group:
                    user_to_kick = text_to_group.split()[1]
                    group_dict[group_id].remove((user_to_kick,clients[usernames.index(user_to_kick)],True))
                    for (u,c,o) in group_dict[group_id]:
                        c.send(f'[{group_id}][{time_now}]{user_to_kick} was kicked'.encode())

                #adding members from group
                elif "/add" in text_to_group:
                    user_to_add = text_to_group.split()[1]
                    c_id = clients[usernames.index(user_to_add)] #client info for member to add
                    if (user_to_add,c_id,True) not in group_dict[group_id]:
                        group_dict[group_id].append((user_to_add,c_id,True)) #adding only if not a member
                        for (u,c,o) in group_dict[group_id]:
                            c.send(f'[{group_id}][{time_now}]{user_to_add} was added'.encode())
                    else:
                        client.send("Cannot add existing members".encode())

                
                elif text_to_group == "/gooffline":
                    if (name,client,True) in group_dict[group_id]:
                        time_left = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        group_dict[group_id].remove((name,client,True))
                        group_dict[group_id].append((name,client,False))
                        for (u,c,o) in group_dict[group_id]:
                            c.send(f"[{time_left}]{name} went offline".encode())
                
                elif text_to_group == "/goonline":
                    if (name,client,False) in group_dict[group_id]:
                        time_join = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        group_dict[group_id].remove((name,client,False))
                        group_dict[group_id].append((name,client,True))
                        for (u,c,o) in group_dict[group_id]:
                            c.send(f"[{time_join}]{name} is back online".encode())

                            
                #just send messages
                else:
                    if (name,client,True) in group_dict[group_id]:
                        for (u,c,online) in group_dict[group_id]:
                            if online:
                                if c!= client:
                                    c.send(f'[{group_id}][{time_now}]{sender}: {text_to_group} '.encode())
                                    client.send(f"[Message recieved by {u}]".encode())
                    else:
                        client.send("YOU ARE NOT PART OF THIS GROUP".encode())   #only members can send messages

            #creating the group
            else:
                client_group = []   #creating a tuple indicating whethere online ie. (username,client,Bool)
                client_group.append((usernames[client_index],client,True)) #adding the current (username,client,Bool)
                group_members = message.split("~")[1].split(":")[1].split(",")
                for u in group_members:
                    if u in usernames:
                        c_ind = usernames.index(u)   #index of client to be added
                        client_group.append((u,clients[c_ind],True))
                    else:
                        client.send("Enter valid member names".encode())
                        break
                for t in client_group:
                    if t[1] != client:
                        t[1].send(f"YOU WERE ADDED TO GROUP: {group_id}".encode())
                        t[1].send(f"GROUP ADMIN IS: {usernames[clients.index(client)]}".encode())
                group_dict[group_id] = client_group
                client.send(f"[FROM SERVER]YOU CREATED GROUP {group_id}".encode())
               
        elif message.startswith("OFF"):
            clients_messages[name][1] = False  #set to offline
            last_online = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for (c,o,q) in clients_messages.values():
                if o:
                    c.send(f"{name} was online at {last_online}".encode())

            #ACTIVE = False
        elif message.startswith("ON"):
            clients_messages[name][1] = True
            msg_q = clients_messages[name][2]
            if msg_q != []:
                for m in msg_q:
                    client.send(m)
        else:
            msg = f'[TO ALL][{time_now}]{message}'
            broadcast(msg.encode())
               
            if usernames != []:
                for user in usernames:
                    if user != name:
                        client.send(f"[MESSAGE RECIEVED BY {user}]".encode())

       
def recieve():
    while True:
        client, addr = server.accept() #accept new connections
        client.send("USERN".encode()) # send a code to client to input nickname

        username = client.recv(1024).decode()
        # if username in usernames:
        #     clients_messages[username] = [client,True,queue.Queue()]
    
        usernames.append(username)
        clients.append(client)
        clients_messages[username] = [client,True,[]]

        broadcast(f'{username} JOINED THE SERVER'.encode())
      

 

        print(f"USER: {username} WITH {addr} Successfully connected to server".upper())
        client.send("SUCCESSFULY CONNECTED TO SERVER".encode())


        thread = threading.Thread(target=handle,args=(client,))
        thread.start()


recieve()


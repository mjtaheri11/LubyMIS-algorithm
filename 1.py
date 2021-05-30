import json
import socket
import time
from threading import Thread
import random


def listen(node):
    while True:
        c, addr = node.server.accept()
        byte_array = c.recv(1024)
        kwargs = json.loads(byte_array, encoding='utf-8')

        try:
            if node.round == 1:
                print(f"node {node.index} received from node {kwargs['index']}: number {kwargs['val']}")
                node.received_vals.append(kwargs['val'])
            if node.round == 2:
                if kwargs['status'] == 'winner':
                    print(f"node {node.index} received from node {kwargs['index']}: winner")
                    node.status = 'looser'
                else:
                    raise Exception("Something went wrong")
            if node.round == 3:
                if kwargs['status'] == 'looser':
                    print(f"node {node.index} received from node {kwargs['index']}: looser")
                    for neighbor in node.neighbors:
                        if neighbor.index == kwargs['index']:
                            node.neighbors.remove(neighbor)
                            break
                else:
                    raise Exception("Something went wrong")
        except Exception as e:
            print(f"-------- node {node.__dict__} kwargs {kwargs}")


def perform(node):
    node.perform()


class NeighborInfo:
    def __init__(self, *args, **kwargs):
        self.index = kwargs['index']
        self.address = kwargs['address']
        self.port = kwargs['port']
        self.delay = kwargs['delay']

class Node:
    def __init__(self, *args, **kwargs):
        self.status = 'unknown'
        self.round = 1
        self.received_vals = []
        self.val = kwargs['val']
        self.round_delay = kwargs['round_delay']
        self.index = kwargs['index']
        self.address = kwargs['address']
        self.port = kwargs['port']
        self.queue_size = 10
        self.neighbors = []

        self._init_server()


    def _init_server(self):
        s = socket.socket()
        s.bind((self.address, self.port))
        s.listen(self.queue_size)
        self.server = s

    def _send_with_delay(self, byte_array, destination):
        connection = socket.socket()
        connection.bind((self.address, 0))
        connection.connect((destination.address, destination.port))

        time.sleep(destination.delay)

        connection.send(byte_array)
        connection.close()

    def add_neighbor(self, *args, **kwargs):
        self.neighbors.append(
            NeighborInfo(**kwargs)
        )

    def perform(self):
        # ROUND 1
        self.received_vals = []
        start_time = time.time()
        self.round = 1
        for neighbor in self.neighbors:
            message = {
                'index': self.index,
                'val': self.val,
            }
            byte_array = json.dumps(message).encode('utf-8')
            self._send_with_delay(byte_array, neighbor)
        while time.time() - start_time < self.round_delay:
            time.sleep(0.1)
        
        new_status = 'winner'
        for val in self.received_vals:
            if val > self.val:
                new_status = 'unknown'
        self.status = new_status

        # ROUND 2
        start_time = time.time()
        self.round = 2
        if self.status == 'winner':
            for neighbor in self.neighbors:
                message = {
                    'index': self.index,
                    'status': 'winner',
                }
                byte_array = json.dumps(message).encode('utf-8')
                self._send_with_delay(byte_array, neighbor)
        while time.time() - start_time < self.round_delay:
            time.sleep(0.1)
        
        # ROUND 3
        start_time = time.time()
        self.round = 3
        if self.status == 'looser':
            for neighbor in self.neighbors:
                message = {
                    'index': self.index,
                    'status': 'looser',
                }
                byte_array = json.dumps(message).encode('utf-8')
                self._send_with_delay(byte_array, neighbor)
        while time.time() - start_time < self.round_delay:
            time.sleep(0.1)
        
        if self.status == 'unknown':
            self.perform()
        else:
            print(f"node {self.index}: {self.status}")



def get_node(nodes, index):
    for node in nodes:
        if node.index == index:
            return node
    return None

def create_or_get(nodes, index, n, round_delay, base_port):
    node = get_node(nodes, index)
    if node is not None:
        return node
    
    new_node = Node(
        val=random.randint(1, n**4),
        round_delay=round_delay,
        index=index,
        address='localhost',
        port=base_port + index,
    )
    nodes.append(new_node)
    return new_node


if __name__ == '__main__':
    base_port = 40000

    round_delay = int(input())
    n = int(input())
    nodes = []
    for i in range(n):
        info_line = list(map(int, input().split()))
        node0 = create_or_get(nodes, info_line[0], n, round_delay, base_port)
        node1 = create_or_get(nodes, info_line[1], n, round_delay, base_port)
        node0.add_neighbor(
            index= node1.index,
            address= node1.address,
            port= node1.port,
            delay= info_line[2],
        )
        node1.add_neighbor(
            index= node0.index,
            address= node0.address,
            port= node0.port,
            delay= info_line[2],
        )
    
    for node in nodes:
        listen_thread = Thread(target=listen, args=(node,))
        listen_thread.start()
    
    for node in nodes:
        perform_thread = Thread(target=perform, args=(node,))
        perform_thread.start()
        
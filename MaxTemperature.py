from random import randrange

from pymote.algorithm import NodeAlgorithm
from pymote.message import Message


class MaxTemperature(NodeAlgorithm):
    default_params = {'neighborsKey': 'Neighbors', 'temperatureKey': "T"}

    def initializer(self):
        ini_nodes = []
        max_temp = 0

        for node in self.network.nodes():
            node.memory[self.neighborsKey] = \
                node.compositeSensor.read()['Neighbors']
            node.memory[self.temperatureKey] = randrange(100)
            max_temp = max(max_temp, node.memory[self.temperatureKey])
            node.status = 'INITIATOR'
            ini_nodes.append(node)

        print("Max generated temperature is %d" % max_temp)

        for ini_node in ini_nodes:
            self.network.outbox.insert(0, Message(header=NodeAlgorithm.INI,
                                                  destination=ini_node))

    def initiator(self, node, message):
        if message.header == NodeAlgorithm.INI:
            # default destination: send to every neighbor
            node.send(Message(header='Temperature',
                              data=node.memory[self.temperatureKey]))
            node.status = 'IDLE'

    def idle(self, node, message):
        if message.header == 'Temperature':
            if node.memory[self.temperatureKey] < message.data:
                node.memory[self.temperatureKey] = message.data
                destination_nodes = list(node.memory[self.neighborsKey])
                # send to every neighbor-sender
                destination_nodes.remove(message.source)
                if destination_nodes:
                    node.send(Message(destination=destination_nodes,
                                      header='Temperature',
                                      data=message.data))

    STATUS = {
              'INITIATOR': initiator,
              'IDLE': idle,
    }

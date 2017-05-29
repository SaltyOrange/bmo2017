from random import choice

from pymote.algorithm import NodeAlgorithm
from pymote.message import Message


class SpanningTree(NodeAlgorithm):
    default_params = {'neighborsKey': 'Neighbors', 'rootKey': 'Root',
                      'treeNeighborsKey': 'TreeNeighbors',
                      'counterKey': 'Counter', 'parentKey': 'Parent'}

    def initializer(self):
        ini_nodes = []
        for node in self.network.nodes():
            node.memory[self.neighborsKey] = \
                node.compositeSensor.read()['Neighbors']
            node.status = 'IDLE'

        ini_node = choice(self.network.nodes())
        ini_node.status = 'INITIATOR'
        ini_nodes.append(ini_node)

        print(ini_nodes)

        for node in ini_nodes:
            self.network.outbox.insert(0, Message(header=NodeAlgorithm.INI,
                                       destination=node))

    def initiator(self, node, message):
        if message.header == NodeAlgorithm.INI:
            node.memory[self.rootKey] = True
            node.memory[self.treeNeighborsKey] = []
            node.memory[self.counterKey] = 0

            node.send(Message(header='Query'))

            node.status = 'ACTIVE'

    def idle(self, node, message):
        if message.header == 'Query':
            node.memory[self.rootKey] = False
            node.memory[self.parentKey] = message.source
            node.memory[self.treeNeighborsKey] = [message.source]

            node.send(Message(destination=message.source, header='Yes'))

            node.memory[self.counterKey] = 1

            if node.memory[self.counterKey] == len(node.memory[self.neighborsKey]):
                node.status = 'DONE'
            else:
                destination_nodes = list(node.memory[self.neighborsKey])
                # send to every neighbor-sender
                destination_nodes.remove(message.source)
                if destination_nodes:
                    node.send(Message(destination=destination_nodes,
                                      header='Query'))

                node.status = 'ACTIVE'

    def active(self, node, message):
        if message.header == 'Query':
            node.memory[self.counterKey] += 1
            if node.memory[self.counterKey] == len(node.memory[self.neighborsKey]):
                node.status = 'DONE'

        elif message.header == 'Yes':
            node.memory[self.treeNeighborsKey].append(message.source)
            node.memory[self.counterKey] += 1
            if node.memory[self.counterKey] == len(node.memory[self.neighborsKey]):
                node.status = 'DONE'

    def done(self, node, message):
        pass

    STATUS = {
              'INITIATOR': initiator,
              'IDLE': idle,
              'ACTIVE': active,
              'DONE': done
    }

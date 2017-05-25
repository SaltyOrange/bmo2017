from random import choice

from pymote.algorithm import NodeAlgorithm
from pymote.message import Message


class SetupYoYo(NodeAlgorithm):
    default_params = {'neighborsKey': 'Neighbors',
                      'inNeighborsKey': 'InNeighbors',
                      'outNeighborsKey': 'OutNeighbors'}

    ID_KEY = 'id'

    def initializer(self):
        for i, node in enumerate(self.network.nodes(), start=1):

            node.memory[self.ID_KEY] = i
            node.memory[self.neighborsKey] = \
                node.compositeSensor.read()['Neighbors']
            node.status = 'INITIATOR'

            self.network.outbox.insert(0, Message(header=NodeAlgorithm.INI,
                                       destination=node))

    def initiator(self, node, message):
        if message.header == NodeAlgorithm.INI:
            node.memory[self.inNeighborsKey] = []
            node.memory[self.outNeighborsKey] = []

            # If node has no neighbors set its status to SOURCE
            if not node.memory[self.neighborsKey]:
                node.status = 'SOURCE'
                return

            # default destination: send to every neighbor
            node.send(Message(header='id',
                              data=node.memory[self.ID_KEY]))

            node.status = 'IDLE'

    def idle(self, node, message):
        if message.header == 'id':
            if message.data < node.memory[self.ID_KEY]:
                node.memory[self.inNeighborsKey].append(message.source)
            else:
                node.memory[self.outNeighborsKey].append(message.source)

        num_of_in_neighbors = len(node.memory[self.inNeighborsKey])
        num_of_out_neighbors = len(node.memory[self.outNeighborsKey])

        if num_of_in_neighbors + num_of_out_neighbors >= \
                len(node.memory[self.neighborsKey]):

            if num_of_in_neighbors:
                node.status = 'SINK'

            if num_of_out_neighbors:
                node.status = 'SOURCE'

            if num_of_in_neighbors and num_of_out_neighbors:
                node.status = 'INTERMEDIATE'

    def source(self, node, message):
        pass

    def intermediate(self, node, message):
        pass

    def sink(self, node, message):
        pass

    STATUS = {
              'INITIATOR': initiator,
              'IDLE': idle,
              'SOURCE': source,
              'INTERMEDIATE': intermediate,
              'SINK': sink
    }

from pymote.algorithm import NodeAlgorithm
from pymote.message import Message


class YoYo(NodeAlgorithm):
    default_params = {'neighborsKey': 'Neighbors',
                      'inNeighborsKey': 'InNeighbors',
                      'outNeighborsKey': 'OutNeighbors'}

    # TODO: Move to param
    ID_KEY = 'id'

    # I'll use a dict {id_value: [source_nodes]}
    RECEIVED_IDS_KEY = 'received_ids'

    # I'll use a dict {response_value: [source_nodes]}
    RECEIVED_RESPONSES_KEY = 'received_responses'

    # Store nodes that requested pruning
    REQUESTED_PRUNING_KEY = 'requested_pruning'

    # Store that sink pruned itself, used for LEADER status change
    SINK_PRUNED_KEY = 'sink_pruned'

    # TODO: Maybe add message headers??
    YES_RESPONSE = 'yes'
    NO_RESPONSE = 'no'
    PRUNE_RESPONSE = 'prune'

    def reset_runtime_memory(self, node):
        node.memory[self.RECEIVED_IDS_KEY] = {}
        node.memory[self.RECEIVED_RESPONSES_KEY] = {}
        node.memory[self.REQUESTED_PRUNING_KEY] = []
        node.memory[self.SINK_PRUNED_KEY] = False

    def remove_in_neighbors(self, node, nodes_to_remove):
        for node_to_remove in nodes_to_remove:
            node.memory[self.inNeighborsKey].remove(node_to_remove)

    def remove_out_neighbors(self, node, nodes_to_remove):
        for node_to_remove in nodes_to_remove:
            node.memory[self.outNeighborsKey].remove(node_to_remove)

    def reverse_nodes_prune_and_modify_status(self, node, nodes_to_reverse):
        for node_to_prune in node.memory[self.REQUESTED_PRUNING_KEY]:
            node.memory[self.outNeighborsKey].remove(node_to_prune)

        for node_to_reverse in nodes_to_reverse:
            if node_to_reverse in node.memory[self.inNeighborsKey]:
                node.memory[self.inNeighborsKey].remove(node_to_reverse)
                node.memory[self.outNeighborsKey].append(node_to_reverse)
            elif node_to_reverse in node.memory[self.outNeighborsKey]:
                node.memory[self.outNeighborsKey].remove(node_to_reverse)
                node.memory[self.inNeighborsKey].append(node_to_reverse)

        if len(node.memory[self.inNeighborsKey]) == 0 and \
                not node.memory[self.SINK_PRUNED_KEY]:
            if len(node.memory[self.outNeighborsKey]) == 0:
                node.status = 'LEADER'
            else:
                node.status = 'SOURCE'

                # Should this be timer triggered ???
                node.send(
                    Message(destination=node.memory[self.outNeighborsKey],
                            header='id',
                            data=node.memory[self.ID_KEY])
                )
        elif len(node.memory[self.outNeighborsKey]) == 0:
            if len(node.memory[self.inNeighborsKey]) == 0:
                node.status = 'PRUNED'
            else:
                node.status = 'SINK'
        else:
            node.status = 'INTERMEDIATE'

        self.reset_runtime_memory(node)

    def respond_to_in_neighbors(self, node, min_id, all_no=False):
        # This method returns a list of nodes that will receive a NO response

        ret = []
        for key in node.memory[self.RECEIVED_IDS_KEY]:
            send_to = node.memory[self.RECEIVED_IDS_KEY][key]
            if key == min_id and not all_no:
                response = self.YES_RESPONSE
            else:
                response = self.NO_RESPONSE
                ret.append(send_to[0])

            if len(node.memory[self.inNeighborsKey]) == 1 and node.status == 'SINK':
                # Only one id was received because only one in-neghbor exists
                # and this SINK is useless (it's a LEAF SINK),
                # so send a prune request with the first response as well
                node.send(
                    Message(destination=send_to[0],
                            header='response',
                            data=(response, self.PRUNE_RESPONSE))
                )
                self.remove_in_neighbors(node, [send_to[0]])
                node.memory[self.SINK_PRUNED_KEY] = True
            else:
                node.send(
                    Message(destination=send_to[0],
                            header='response',
                            data=(response, ))
                )
            # Request pruning from duplicate nodes for this id
            if send_to[1:]:
                node.send(
                    Message(destination=send_to[1:],
                            header='response',
                            data=(response, self.PRUNE_RESPONSE))
                )
                self.remove_in_neighbors(node, send_to[1:])

        return ret

    def receive_and_handle_id(self, node, message):
        if message.data in node.memory[self.RECEIVED_IDS_KEY]:
            node.memory[self.RECEIVED_IDS_KEY][message.data].append(message.source)
        else:
            node.memory[self.RECEIVED_IDS_KEY][message.data] = [message.source]

        num_of_received_ids = sum(
            [len(node.memory[self.RECEIVED_IDS_KEY][k])
             for k in node.memory[self.RECEIVED_IDS_KEY]]
        )
        num_of_in_neighbors = len(node.memory[self.inNeighborsKey])
        if num_of_received_ids >= num_of_in_neighbors:
            min_id = min(node.memory[self.RECEIVED_IDS_KEY].keys())
            if node.status == 'INTERMEDIATE':
                node.send(
                    Message(destination=node.memory[self.outNeighborsKey],
                            header='id',
                            data=min_id)
                )

            elif node.status == 'SINK':
                no_responses = self.respond_to_in_neighbors(node, min_id)
                self.reverse_nodes_prune_and_modify_status(node, no_responses)

    def receive_and_handle_response(self, node, message):
        if self.PRUNE_RESPONSE in message.data:
            node.memory[self.REQUESTED_PRUNING_KEY].append(message.source)

        response = self.YES_RESPONSE if self.YES_RESPONSE in message.data \
            else self.NO_RESPONSE

        if response in node.memory[self.RECEIVED_RESPONSES_KEY]:
            node.memory[self.RECEIVED_RESPONSES_KEY][response].append(message.source)
        else:
            node.memory[self.RECEIVED_RESPONSES_KEY][response] = [message.source]

        num_of_received_responses = sum(
            [len(node.memory[self.RECEIVED_RESPONSES_KEY][k])
             for k in node.memory[self.RECEIVED_RESPONSES_KEY]]
        )
        num_of_out_neighbors = len(node.memory[self.outNeighborsKey])
        if num_of_received_responses >= num_of_out_neighbors:
            if self.NO_RESPONSE in node.memory[self.RECEIVED_RESPONSES_KEY]:
                no_nodes = node.memory[self.RECEIVED_RESPONSES_KEY][self.NO_RESPONSE]
            else:
                no_nodes = []

            if node.status == 'INTERMEDIATE':
                min_id = min(node.memory[self.RECEIVED_IDS_KEY].keys())
                no_responses = self.respond_to_in_neighbors(
                    node, min_id, all_no=len(no_nodes) > 0
                )
                no_nodes.extend(no_responses)

                self.reverse_nodes_prune_and_modify_status(node, no_nodes)

            elif node.status == 'SOURCE':
                self.reverse_nodes_prune_and_modify_status(node, no_nodes)

    def initializer(self):
        for node in self.network.nodes():
            self.reset_runtime_memory(node)
            if node.status == 'SOURCE':
                self.network.outbox.insert(0, Message(header=NodeAlgorithm.INI,
                                           destination=node))

    def source(self, node, message):
        if message.header == NodeAlgorithm.INI:
            node.send(Message(destination=node.memory[self.outNeighborsKey],
                              header='id',
                              data=node.memory[self.ID_KEY]))

        elif message.header == 'response':
            self.receive_and_handle_response(node, message)


    def intermediate(self, node, message):
        if message.header == 'id':
            self.receive_and_handle_id(node, message)

        elif message.header == 'response':
            self.receive_and_handle_response(node, message)

    def sink(self, node, message):
        if message.header == 'id':
            self.receive_and_handle_id(node, message)

    def pruned(self, node, message):
        pass

    def leader(self, node, message):
        pass

    STATUS = {
              'SOURCE': source,
              'INTERMEDIATE': intermediate,
              'SINK': sink,
              'PRUNED': pruned,
              'LEADER': leader
    }

# Echo server program
import socket
import pickle
import numpy as np
import collections

from proposer import Proposer
from acceptor import Acceptor
from learner import Learner
from messenger import print_message
from state_backup import load_state, save_state

crash_rate = 0

def server(server_id, num_server, f = None):

    server_id = int(server_id) 
    num_server = int(num_server)

    # host_name = 'bigdata.eecs.umich.edu'
    host_name = 'localhost'
    servers_list = {idx:{'host': host_name, 'port': 50050+idx} for idx in range(num_server)}

    #Ideally, quorum should be  len(servers_list)/2 + 1
    #I choose len(servers_list)/2, because the current process only send message to other processes
    #thus quorum assumes that itself has already been included 
    quorum = len(servers_list)/2

    # load state
    state = load_state(server_id)

    proposer = Proposer(server_id, servers_list)
    acceptor = Acceptor(server_id, servers_list, state['promised_proposal_id'], state['accepted_proposal_id'],
                        state['accepted_proposal_val'], state['accepted_client_info'])
    learner = Learner(server_id, quorum, state['decided_log'])

    view = 0
    num_acceptors = len(servers_list)

    HOST = servers_list[server_id]['host']  # Symbolic name meaning all available interfaces
    PORT = servers_list[server_id]['port']  # Arbitrary non-privileged port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(100)
 
    request_val_queue = collections.deque()
    client_info_queue = collections.deque()

    while True:
        
        #try to crash
        if view%num_acceptors == server_id:
           server_crash(server_id, crash_rate)

        print_message("wait for connection")
        conn, addr = s.accept()
        print_message('Connection by '+str(addr))
        data = conn.recv(4096*2)
        msg = pickle.loads(data)      
        print_message('Connection received '+str(msg))

        if msg['type'] == 'request':
           if msg['resend_idx'] != 0 or forceViewChange(msg):
              #if this is an resent message, triger view change
              view += 1
              proposer.need_prepare = True
              print_message("change to view %s"%(str(view)))
           if view%num_acceptors == server_id:
                #this is leader
                request_val_queue.append( msg['request_val'] )
                client_info_queue.append( msg['client_info'] )
                if proposer.need_prepare is True:
                    proposer.prepare(view)
                    #proposer.need_prepare = False
        
                else: #directly propose without prepare stage
                    proposal_pack = {}
                    print_message("no need to prepare")
                    print_message(request_val_queue)
                    for _ in range(len(request_val_queue)):
                        request_val = request_val_queue.popleft()
                        client_info = client_info_queue.popleft()
                        proposal_pack = proposer.addNewRequest(proposal_pack, request_val, client_info)
                    proposer.propose(proposal_pack, without_prepare = True)

                """
                election_result, proposer_val  = proposer.tryGetElected()
                if election_result is True:
                    #get elected
                    if proposer_val is None:
                        proposer_val = msg["proposer_val"]
                    #proposer a value
                    proposer.propose(proposer_val)
                """

        elif msg['type'] == 'prepare':
            acceptor.promise(msg)

        elif msg['type'] == 'promise':
             proposer.addVote(msg)
             if proposer.checkQuorumSatisfied() is True:
                if proposer.need_prepare is True:
                    proposal_pack = proposer.getProposalPackForHoles(learner.getDecidedLog())
                    for _ in range(len(request_val_queue)):
                        request_val = request_val_queue.popleft()
                        client_info = client_info_queue.popleft()
                        proposal_pack = proposer.addNewRequest(proposal_pack, request_val, client_info)  
                    proposer.propose(proposal_pack)
                proposer.need_prepare = False

        elif msg['type'] == 'propose':
            acceptor.accept(msg)

        elif msg['type'] == 'accept':
            slot_idx = msg['slot_idx']
            learner.addVote(msg, slot_idx)
            if learner.checkQuorumSatisfied(slot_idx) is True:
                learner.decide(slot_idx)
                      
        conn.close()

def server_crash(server_id, crash_rate):
    if np.random.rand() < crash_rate:
       print_message("!!!!!!!!!!!!!!!!server id %s crashes"%(str(server_id)))
       exit()

def forceViewChange(msg):
    client_info = msg['client_info']
    if client_info['client_id'] == 0 and client_info['clt_seq_num'] == 3:
       return True
    else:
       return False


if __name__ == "__main__":
    from optparse import OptionParser, OptionGroup

    parser = OptionParser(usage = "Usage!")
    options, args = parser.parse_args()
    options = dict(options.__dict__)

    server(*args, **options)


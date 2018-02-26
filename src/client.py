# Echo client program
import socket
import pickle
import yaml

from messenger import sendMsg
from messenger import print_message

timeout = 20

def client(client_idx, config_file_server = None):

    host_name = 'bigdata.eecs.umich.edu'
    clients_list = {idx:{'host': host_name, 'port': 40000+idx} for idx in range(5)} 

    if config_file_server is not None:
        with open(config_file_server, 'r') as config_handler:
            config = yaml.load(config_handler)
        f = int(config['f']) #the number of failure that can be tolerated
        num_server = 2*f + 1
        servers_list = { server_idx: config['servers_list'][server_idx] for server_idx in range(num_server)}
    else:
        servers_list = {idx:{'host': host_name, 'port': 50000+idx} for idx in range(50)}
      
    client_idx = int(client_idx)
    client_host = clients_list[client_idx]['host']
    client_port = clients_list[client_idx]['port']

    request_size = 5
    request_list = ['client, seq: (%s, %s)'%(str(client_idx), str(request_idx) ) for request_idx in range(request_size) ]
    
    for request_idx in range(len(request_list)):
        clt_seq_num = request_idx
        val = request_list[request_idx]
        resend_idx = 0
        while True:
            client_info = { 'clt_seq_num': clt_seq_num, 'client_id': client_idx, 'client_host': client_host, 'client_port': client_port }
            msg = {'type': 'request', 'request_val': val, 'resend_idx': resend_idx, 'client_info': client_info}
            for server_id in servers_list:
                host = servers_list[server_id]['host']
                port = servers_list[server_id]['port']
    
                sendMsg(host, port, msg) 
            
            if waitForAck(client_host, client_port, timeout, clt_seq_num) is True:
               break
            #elif resend_idx == resend_max-1:
            #   print_message('give up on request_idx %s due to timeout on max resend times'%(str(request_idx)))
            resend_idx += 1

def waitForAck(client_host, client_port, timeout, clt_seq_num):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((client_host, client_port))
    s.listen(100)
    

    while True:
       print_message('set timeout for %s s'%str(timeout))
       s.settimeout(timeout)
       print_message("wwwwwwwwwwwwwwwait for ack")
       try: 
          conn, addr = s.accept()
       except socket.timeout:
          print_message("timeout on ack")
          return False
       print_message('Connected by '+str( addr))
       data = conn.recv(4096*2)
       msg = pickle.loads(data)
       print_message('RCVD: '+str(msg))
       conn.close()

       #wait for the right clt_seq_num
       if msg['type'] == 'ack' and msg['client_info']['clt_seq_num'] == clt_seq_num:
           print_message('client %s received ack for request (clt seq num) %s'%(str(msg['client_info']['client_id']), str(msg['client_info']['clt_seq_num'])) )
           return True


    



    """
    note that the ack might means the committed value is different from its requested value
    need to make sure how to handle this
    """
    #if msg['type'] == 'ack' and msg['client_info']['clt_seq_num'] == clt_seq_num:
    #   print_message('client %s received ack for request (clt seq num) %s'%(str(msg['client_info']['client_id']), str(msg['client_info']['clt_seq_num'])) )
    #   return True
    #else:
    #   return False


if __name__ == "__main__":
    #client(0)

    from optparse import OptionParser, OptionGroup

    parser = OptionParser(usage = "Usage!")
    options, args = parser.parse_args()
    options = dict(options.__dict__)

    client(*args, **options)




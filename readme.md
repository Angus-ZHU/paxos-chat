# Multi-Paxos-Chat

## Components

### config.py & generate_test_config.py
+ The config.py define the structure of the paxos cluster config
+ You can generate a default config by using generate_test_config.py
    + Parameters
        + -f, the number of tolerating failures, this will indicate the correct cluster size which is 2 * f + 1
        + -c, the config filename, no need to change in must cases
        + -loss, the message loss ratio, this will be shared by all the replica and client as if it is the network loss
        + -timeout, the message timeout setting

### server.py
+ This is the script of both master and replica
    + Description
        + The server 0 will automatically became master at first
        + The master support multiple propose in parallel
        + The replica detects master dies when heartbeat is not responded
        + Need to start the master first then all the replica, otherwise the replica will decide the master has died and started view change
    + Parameters
        + -c, the config filename, no need to change in must cases
        + -uid, assign the server's uid
        + -skip_slots, skip slots in the form of 1,2,3,4; this will only be used by the initial master which is always server 0
        
### server_state.py
+ This is where all the state transfer happens
    + Description
        + This part is separated from server.py to make serve.py "stateless" in order to support persistent state storage and crash recovery 
        + Although the crash recovery is not implemented due to limited time, you can see the architectural design

### client.py
+ This is the script of client
    + Description
        + Each client will continuously send message one after another
        + Each message has a unique id generated randomly
        + The message body can be generated randomly or input manually, decided by the -manual parameter
    + Parameters 
        + -c, the config filename, no need to change in must cases
        + -manual, weather you want manually input each message body or have them generated

### error.py
+ This defined several error raised during view change
+ The view change implementation utilize the python error handling scheme

### message.py
+ This defines all the structured massages that are passed through the network

### run.py
+ The all-in-one script for script mode
+ It will trigger from config generation, start the master, start the replica and put all the clients in auto mode
    + Parameters
        + -f, the number of tolerating failures, this will indicate the correct cluster size which is 2 * f + 1
        + -c, the config filename, no need to change in must cases
        + -skip_slots, skip slots in the form of 1,2,3,4; this will only be used by the initial master which is always server 0
        + -client_n, the number of clients
        + -loss, the message loss ratio, this will be shared by all the replica and client as if it is the network loss
        + -timeout, the message timeout setting

## Running Directions

### Script Mode

+  Use run.py for this mode
    + Every parameter has a default ready to run and everything is taken care of
    + For specify a certain parameter see the description of `run.py` in the first section or run `python run.py -h`

### Manual Mode (Recommend)
1. Get generate config file
    + Use the `generate_test_config.py` script 
    + You can also manually modify `config.json` following the scheme, but not recommended
1. If the servers and clients are running on different server, make sure they have access to the same version of `config.json`
1. Run the servers using `server.py`
1. Run the client using `client.py`

Here is an example to go through the manual mode for better testing. After generating config file `config.json` using`-f 1 -c config.json` . We run `python server.py -uid 0`,  `python server.py -uid 1`, and `python server.py -uid 2` in 3 different tabs in terminal(which will read `config.json` by default). Now you could see the master is already elected. Then we run `python client.py` . To launch a client process and it will constantly send messages to masters after receiving message. By inspecting each of these processes' log, you could easily test the behaviors.

## Test Cases

1. Normal operation

    + You could check this test cases in either manual mode or script mode. Manual mode is recommended for readable logs in each terminal tab. By comparing the last log in each of the replicas, they will remain consistent for arbitrary `f` and client number.

1. The primary dies.

    + You could check this test case in script mode, in which you could easily kill a server. After killing the primary, you could see some messages indicating the view change and some other primary is elected. Then it will continuously receive messages from client and output the consistent logs.

1. The primary dies for f times.

    + You could check this test case in script mode by killing f servers and see the view change will happen f times.

1. The skipped slot.

    + To test this test case, manual mode is also recommended. You could set the skip slots when initiate the primary. Notice that only primary is allowed to set skip slots! After launch all of your servers and clients, you could then kill the primary. And another primary will see the empty slot in everyone's log and send none-op to every one. And after that, you could notice every server's log will contain a none message for this skipped slot. 

1. Message loss.

    + You can test this case by setting some small values of p when starting our system in either manual mode or script mode. The system will remain live.  




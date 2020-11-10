## Multi-Paxos-Chat

#### Config Generation

Before running this system, you could run `generate_test_config.py ` to generate server's config(including server's port, id, heartbeat port, etc.) by setting the tolerate failures and output config's file name. Run `python generate_test_config.py -h` for detailed instructions to use. We've already generate the default config file `config.json`, which includes `5` random generated servers' config by setting `f = 2`.  

#### Script Mode

This script mode includes the above config generation step by setting `f` and `c`.

Run `python run.py -h` for instructions to use this script mode and description of each parameter. by default, we will use `-f 2 -c config.json -skip_slots None -client_n 10 -client_timeout 10 -client_loss 0` to run this mode. Using these parameters above, we will launch 10 client process which will send messages to master constantly and 5 servers which will handle the requests from clients. You can check replica's log consistency by checking the output sanity-check hash value or read each server's log file and compare them. 

#### Manual Mode *recommend

After running the config generation, our manual mode will let servers and clients read the generated config file. By launch a server, open a new terminal tab and run `server.py` . You could follow the instructions by running `server.py -h`. Running a client will also follow these steps by changing `server.py` to `client.py`. 

Here is an example to go through the manual mode for better testing. After generating config file `config.json` using`-f 1 -c config.json` . We run `python server.py -uid 0`,  `python server.py -uid 1`, and `python server.py -uid 2` in 3 different tabs in terminal(which will read `config.json` by default). Now you could see the master is already elected. Then we run `python client.py` . To launch a client process and it will constantly send messages to masters after receiving message. By inspecting each of these processes' log, you could easily test the behaviors.

#### Test Cases

1.  Normal operation

You could check this test cases in either manual mode or script mode. Manual mode is recommended for readable logs in each terminal tab. By comparing the last log in each of the replicas, they will remain consistent for arbitrary `f` and client number.

2. The primary dies.

You could check this test case in script mode, in which you could easily kill a server. After killing the primary, you could see some messages indicating the view change and some other primary is elected. Then it will continuously receive messages from client and output the consistent logs.

3.  The primary dies for f times.

You could check this test case in script mode by killing f servers and see the view change will happen f times.

4. The skipped slot.

To test this test case, manual mode is also recommended. You could set the skip slots when initiate the primary. Notice that only primary is allowed to set skip slots! After launch all of your servers and clients, you could then kill the primary. And another primary will see the empty slot in everyone's log and send none-op to every one. And after that, you could notice every server's log will contain a none message for this skipped slot. 

5. Message loss.

You can test this case by setting some small values of p when starting our system in either manual mode or script mode. The system will remain live.  




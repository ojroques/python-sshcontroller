# python-sshcontroller

This package implements a simple interface to communicate and exchange data
with remote hosts via SSH. At its core, it is a wrapper around the extensive
SSH library [paramiko](https://github.com/paramiko/paramiko/).

## Installation
Run:
```
pip3 install --user sshcontroller-oroques
```

Note that the package has been exclusively tested on Python 3+.

## Usage

The code snippets can also be found at [demo.py](./examples/demo.py).

#### 1. Create a new SSH controller from a SSH key
```python
import sshcontroller

HOST_IP = "93.184.216.34"  # an IPv4 or IPv6 address
KEY_PWD = "password"

ssh_controller = sshcontroller.SSHController(
    host=HOST_IP,
    user="olivier",
    key_path="~/.ssh/id_rsa",  # if omitted, look in agent and in ~/.ssh
    key_password=KEY_PWD,      # optional
    key_type="rsa",            # rsa (default), dsa, ecdsa or ed25519
    port=22,                   # 22 is the default
)
```

#### 2. Connect to remote host
```python
ssh_controller.connect()
```

#### 3. Run a command
```python
return_code, output = ssh_controller.run(
    command="echo 'Hello world!' > /tmp/hello.txt",
    display=True,          # display output, false by default
    combine_stderr=False,  # combine stderr and stdout, false by default
    capture_output=True,   # return output, false by default
    timeout=10,            # command timeout in seconds, 600s by default
)
logging.info(f"return code: {return_code}, output: {output}")
```

#### 4. Transfer data with SFTP
All functions from paramiko's `SFTPClient` are available through the
`SSHController` object. Check
[paramiko's documentation](http://docs.paramiko.org/en/stable/api/sftp.html#paramiko.sftp_client.SFTPClient)
for a complete list.

In addition, the package adds new methods:
* `exists(path)`: check that a file or a directory exists on the remote host
* `list_dirs(path)`: return the list of directories present in `path`
* `list_dirs(path)`: return the list of files present in `path`

```python
print(f"hello.txt exists: {ssh_controller.exists('/tmp/hello.txt')}")
print(f"bonjour.txt exists: {ssh_controller.exists('/tmp/bonjour.txt')}")

ssh_controller.get("/tmp/hello.txt", "/tmp/bonjour.txt")

with open("/tmp/bonjour.txt", 'r') as bonjour:
    for line in bonjour:
        print(line, end='')
```

#### 5. Disconnect
```python
ssh_controller.disconnect()
```

#### 6. Use SSH password instead
```python
import sshcontroller

HOST_IP = "93.184.216.34"  # an IPv4 or IPv6 address
SSH_PWD = ""

ssh_controller = sshcontroller.SSHController(
    host=HOST_IP,
    user="root",
    ssh_password=SSH_PWD
)
ssh_controller.connect()
```

#### 7. Run a command until an event is set
If the argument `stop_event` is set when calling `run()`, the controller waits
for the given event to be triggered before stopping. This is especially useful
when using threads.

The example below starts two threads with an event attached to each one:
one is pinging localhost, the other sleeps for 10s. When the sleeping threads
has finished, we trigger the events to also stop the pinging thread.

```python
import logging
import queue
import sshcontroller
import threading
import time

output = queue.Queue()  # a queue to store the ping command output
stop_event_sleep = threading.Event()
stop_event_ping = threading.Event()

kwargs_sleep = {
    "command": "echo 'thread sleep: sleeping for 10s' && sleep 10s",
    "display": True,
    "stop_event": stop_event_sleep,
}
kwargs_ping = {
    "command": "echo 'thread ping: starting ping' && ping localhost",
    "display": True,
    "capture_output": True,
    "stop_event": stop_event_ping,
}

# call run() and store the command output in the queue
def wrapper(kwargs):
    return output.put(ssh_controller.run(**kwargs))

thread_sleep = threading.Thread(
    target=ssh_controller.run, name="thread_sleep", kwargs=kwargs_sleep)
thread_ping = threading.Thread(
    target=wrapper, name="thread_ping", args=(kwargs_ping, ))

thread_ping.start()
thread_sleep.start()

try:
    thread_sleep.join()
except KeyboardInterrupt:
    logging.info("KeyboardInterrupt")
finally:
    logging.info("Stopping threads")
    stop_event_sleep.set()
    stop_event_ping.set()
    time.sleep(2)

return_code, ping_output = output.get()
logging.info(f"thread ping return code: {return_code}")
logging.info(f"thread ping output length: {len(ping_output)}")

ssh_controller.disconnect()
```

## License
[GNU Lesser General Public License v2.1](LICENSE)

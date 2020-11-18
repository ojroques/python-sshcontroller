#!/usr/bin/python3
import logging
import queue
import sshcontroller
import threading
import time

logging.basicConfig(format="[%(levelname)s] %(message)s", level=logging.INFO)

HOST_IP = "93.184.216.34"  # an IPv4 or IPv6 address
KEY_PWD = ""
SSH_PWD = ""


def demo_key():
    ssh_controller = sshcontroller.SSHController(
        host=HOST_IP,
        user="olivier",
        key_path="~/.ssh/id_rsa",  # if omitted, look for keys in SSH agent and in ~/.ssh/
        key_password=KEY_PWD,      # optional
        key_type="rsa",            # rsa (default), dsa, ecdsa or ed25519
        port=22,                   # 22 is the default
    )

    ssh_controller.connect()

    return_code, output = ssh_controller.run(
        command="echo 'Hello world!' > /tmp/hello.txt",
        display=True,          # display output, false by default
        capture_output=True,   # return output, false by default
        combine_stderr=False,  # combine stderr and stdout, false by default
        timeout=10,            # command timeout in seconds, 600s by default
    )
    logging.info(f"return code: {return_code}, output: {output}")

    print(f"hello.txt exists: {ssh_controller.exists('/tmp/hello.txt')}")
    print(f"bonjour.txt exists: {ssh_controller.exists('/tmp/bonjour.txt')}")

    ssh_controller.get("/tmp/hello.txt", "/tmp/bonjour.txt")

    with open("/tmp/bonjour.txt", 'r') as bonjour:
        for line in bonjour:
            print(line, end='')

    ssh_controller.disconnect()


def demo_pwd():
    ssh_controller = sshcontroller.SSHController(
        host=HOST_IP,
        user="olivier",
        ssh_password=SSH_PWD
    )
    ssh_controller.connect()

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


demo_key()
demo_pwd()

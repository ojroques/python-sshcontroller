import errno
import logging
import paramiko
import socket
from os import path
from stat import S_ISDIR, S_ISREG

_KEY_TYPES = {
    "dsa": paramiko.DSSKey,
    "rsa": paramiko.RSAKey,
    "ecdsa": paramiko.ECDSAKey,
    "ed25519": paramiko.Ed25519Key,
}


class SFTPController(paramiko.SFTPClient):
    def __init__(self, sock):
        super().__init__(sock)

    def exists(self, path):
        try:
            self.stat(path)
        except IOError as e:
            return e.errno != errno.ENOENT
        return True

    def list_dirs(self, path):
        return [
            d.filename for d in self.listdir_attr(path) if S_ISDIR(d.st_mode)
        ]

    def list_files(self, path):
        return [
            f.filename for f in self.listdir_attr(path) if S_ISREG(f.st_mode)
        ]

    @classmethod
    def from_transport(cls, t):
        chan = t.open_session()
        chan.invoke_subsystem("sftp")
        return cls(chan)


class SSHController:
    def __init__(
        self,
        host,
        user,
        key_path=None,
        key_password=None,
        key_type="rsa",
        ssh_password=None,
        port=22,
    ):
        self.host = host
        self.user = user
        self.ssh_password = ssh_password if key_path is None else None
        self.port = port
        self.nb_bytes = 1024
        self.keys, self.transport = [], None
        key_type = key_type.lower()

        if key_path:
            self.keys.append(
                _KEY_TYPES[key_type].from_private_key(
                    open(path.expanduser(key_path), 'r'),
                    key_password,
                )
            )
        elif ssh_password is None:
            self.keys = paramiko.Agent().get_keys()

            try:
                key_file = _KEY_TYPES[key_type].from_private_key(
                    open(path.expanduser(f"~/.ssh/id_{key_type}"), 'r'),
                    key_password
                )
            except Exception:
                pass
            else:
                self.keys.insert(
                    len(self.keys) if key_password is None else 0, key_file
                )

            if not self.keys:
                logging.error("No valid key found")

    def connect(self):
        try:
            ssh_socket = socket.create_connection((self.host, self.port))
        except OSError as e:
            logging.error(f"Connection failed: {e.strerror}")
            return 1

        self.transport = paramiko.Transport(ssh_socket)

        if self.ssh_password is not None:
            try:
                self.transport.connect(
                    username=self.user,
                    password=self.ssh_password,
                )
            except paramiko.SSHException:
                pass
        else:
            for key in self.keys:
                try:
                    self.transport.connect(username=self.user, pkey=key)
                except paramiko.SSHException:
                    continue
                break

        if not self.transport.is_authenticated():
            logging.error("SSH negotiation failed")
            return 1

        logging.info(f"Successfully connected to {self.user}@{self.host}")
        return 0

    def __run_until_event(
        self,
        command,
        stop_event,
        display=True,
        combine_stderr=False,
        capture_output=False,
    ):
        channel = self.transport.open_session()
        output = ""
        timeout = 2

        channel.settimeout(timeout)
        channel.set_combine_stderr(combine_stderr)
        channel.get_pty()
        channel.exec_command(command)

        if not display and not capture_output:
            stop_event.wait()
        else:
            while True:
                try:
                    raw_data = channel.recv(self.nb_bytes)
                except socket.timeout:
                    if stop_event.is_set():
                        break
                    continue

                if not len(raw_data):
                    break

                data = raw_data.decode("utf-8")

                if display:
                    print(data, end='')

                if capture_output:
                    output += data

                if stop_event.is_set():
                    break

        channel.close()
        return (channel.exit_status_ready(), output.splitlines())

    def __run_until_exit(
        self,
        command,
        timeout,
        display=True,
        combine_stderr=False,
        capture_output=False,
    ):
        channel = self.transport.open_session()
        output = ""

        channel.settimeout(timeout)
        channel.set_combine_stderr(combine_stderr)
        channel.get_pty()
        channel.exec_command(command)

        try:
            if not display and not capture_output:
                return (channel.recv_exit_status(), output.splitlines())
            else:
                while True:
                    raw_data = channel.recv(self.nb_bytes)

                    if not len(raw_data):
                        break

                    data = raw_data.decode("utf-8")

                    if display:
                        print(data, end='')

                    if capture_output:
                        output += data
        except socket.timeout:
            logging.warning(f"Timeout after {timeout}s")
            return (1, output.splitlines())
        except KeyboardInterrupt:
            logging.info("KeyboardInterrupt")
            return (0, output.splitlines())
        finally:
            channel.close()

        return (channel.recv_exit_status(), output.splitlines())

    def run(
        self,
        command,
        display=False,
        combine_stderr=False,
        capture_output=False,
        stop_event=None,
        timeout=600,
    ):
        if stop_event:
            return self.__run_until_event(
                command,
                stop_event,
                display=display,
                combine_stderr=combine_stderr,
                capture_output=capture_output,
            )
        else:
            return self.__run_until_exit(
                command,
                timeout,
                display=display,
                combine_stderr=combine_stderr,
                capture_output=capture_output,
            )

    def disconnect(self):
        if self.transport:
            self.transport.close()

    def __getattr__(self, target):
        def wrapper(*args, **kwargs):
            if not self.transport.is_authenticated():
                logging.error("SSH session is not ready")
                return 1
            sftp_channel = SFTPController.from_transport(self.transport)
            r = getattr(sftp_channel, target)(*args, **kwargs)
            sftp_channel.close()
            return r
        return wrapper

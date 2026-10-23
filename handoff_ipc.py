"""Small per-user local command channel; it can only open the handoff UI."""
import getpass,hashlib
from PySide6.QtNetwork import QLocalServer,QLocalSocket
SERVER='BilalAI.handoff.'+hashlib.sha256(getpass.getuser().encode()).hexdigest()[:16]


def request_handoff(server_name=SERVER):
    socket=QLocalSocket();socket.connectToServer(server_name)
    if not socket.waitForConnected(1500):return False
    socket.write(b'HANDOFF\n');socket.flush()
    ready=socket.bytesAvailable()>0 or socket.waitForReadyRead(1500)
    accepted=ready and bytes(socket.readAll()).strip()==b'OK'
    socket.disconnectFromServer();return accepted


class HandoffServer:
    def __init__(self,callback,parent=None,server_name=SERVER):
        self.callback=callback;self.server=QLocalServer(parent);self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption);self.clients=[]
        if not self.server.listen(server_name):raise RuntimeError('Could not start the local handoff command channel.')
        self.server.newConnection.connect(self.connected)
    def connected(self):
        while self.server.hasPendingConnections():
            client=self.server.nextPendingConnection();self.clients.append(client);client.setReadBufferSize(64);client.readyRead.connect(lambda c=client:self.read(c))
            client.disconnected.connect(lambda c=client:self.cleanup(c))
            if client.bytesAvailable():self.read(client)
    def read(self,client):
        if not client.canReadLine():return
        command=bytes(client.readLine(64)).strip()
        if command==b'HANDOFF':
            self.callback();client.write(b'OK\n');client.flush()
        client.disconnectFromServer()
    def cleanup(self,client):
        if client in self.clients:self.clients.remove(client)
        client.deleteLater()
    def close(self):
        for client in list(self.clients):client.abort()
        self.server.close()

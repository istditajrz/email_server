from datetime import datetime
import string, hashlib, sqlite3, base64, os, json, aiosmtpd.controller, uuid, traceback, smtplib
from aiosmtpd.smtp import SMTP, Session, Envelope

"""SQL SCHEMA:
CREATE TABLE MAIL(
    ID          TEXT PRIMARY KEY    NOT NULL,
    FROMS       TEXT                NOT NULL,
    RCPT_TOS    TEXT                NOT NULL,
    TIMESTAMP   REAL                NOT NULL
);"""

class handler:
    CHARS = list(string.ascii_letters + string.digits)
    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        if address.split('@')[0] not in self._get_users():
            return f'450 <{address}>: Recipient address rejected: Domain not found'
        envelope.rcpt_tos.append(address)
        return b'250 OK'
    
    async def handle_DATA(self, server: SMTP, session: Session, envelope: Envelope):
        time = datetime.utcnow().timestamp()
        for address in envelope.rcpt_tos:
            while True:
                guid = uuid.uuid4()
                user = hashlib.sha1(address.split('@')[0].encode()).hexdigest()
                for file in os.listdir(f".\\users\\{user}"):
                    if file == str(guid) + ".mail":
                        continue
                break
            with open(f".\\users\\{user}\\{guid}.mail", "w") as file:
                content = envelope.content.decode("utf-8")
                headers = {"from": envelope.mail_from, "to": envelope.rcpt_tos}
                file.write(base64.b64encode(json.dumps({"content": content, "headers": headers, "timestamp": time}).encode("utf-8")).decode('utf-8'))
            conn = sqlite3.connect(f".\\users\\{user}\\manifest.db")
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO MAIL(ID, FROMS, RCPT_TOS, TIMESTAMP) VALUES(:id, :froms, :tos, :timestamp)", 
                {"id": str(guid), "froms": ",".join(envelope.mail_from) if type(envelope.mail_from) == list else envelope.mail_from, "tos": ",".join(envelope.rcpt_tos)if type(envelope.rcpt_tos) == list else envelope.rcpt_tos, "timestamp": time}
            )
            conn.commit()
            conn.close()
        return b'250 OK'
    
    def handle_exception(self, err):
        traceback.print_exc(2)
        return '542 Internal Server Error'

    @staticmethod
    def _get_users() -> list[str]:
        curr = sqlite3.connect('.\\accounts.db').cursor()
        return {i[0] for i in curr.execute("SELECT USER FROM ACCOUNTS")}

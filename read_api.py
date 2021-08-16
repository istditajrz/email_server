
import sqlite3, os, hashlib, uuid
from base64 import b64decode
from json import loads
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

"""
CREATE TABLE ACCOUNTS(
    USERID TEXT PRIMARY KEY NOT NULL,
    USER TEXT NOT NULL,
    PASS TEXT NOT NULL
);
"""

@dataclass(order=True)
class email:
    id: uuid.UUID
    froms: list[str]
    tos: list[str]
    timestamp: float
    content: str
    def __init__(self, id: uuid.UUID, froms: list[str], tos: list[str], timestamp: float, content: str) -> None:
        if type(id) == uuid.UUID: self.id = id
        else: self.id = uuid.UUID(id)
        self.froms = froms
        self.tos = tos
        self.timestamp = timestamp
        self.content = self._trim_content(content)
    
    @staticmethod
    def _trim_content(content: str):
        content = content.splitlines()
        if content[0].startswith("FROM: "):
            while not content[0].startswith('BODY:'):
                content = content[1:]
            content[0] = content[0][5:].strip()
        content = '\n'.join(content)
        return content

    def __eq__(self, o: object) -> bool:
        return self.timestamp == o
    
    def __hash__(self) -> int:
        return self.id
    
    def __str__(self) -> str:
        print(repr(self))
        return "FROM: {}\nTO: {}\nTIME: {}\nCONTENT: {}\n\n\nUUID: {}".format(", ".join(self.froms), ", ".join(self.tos), datetime.fromtimestamp(self.timestamp), self.content,self.id)
    

class client:
    def __init__(self, user: str, password: str) -> None:
        self.user_hash = hashlib.sha1(user.encode('utf-8')).hexdigest()
        self.database = sqlite3.connect(f'.\\users\\{self.user_hash}\manifest.db')
        self._authenticate(self.user_hash, hashlib.sha512(password.encode('utf-8')).hexdigest())
    
    class NewAccountError(Exception):
        """Raised if account creation failed"""

    @classmethod
    def new_account(cls, user: str, password: str):
        curr = sqlite3.connect(".\\accounts.db").cursor()
        cls.user_hash = hashlib.sha1(user.encode('utf-8')).hexdigest()
        if cls.user_hash in {i[0] for i in curr.execute("SELECT USERID FROM ACCOUNTS").fetchall()}:
            raise cls.NewAccountError('Username in use')
        os.mkdir(f".\\users\\{cls.user_hash}")
        manifest = sqlite3.connect(f".\\users\\{cls.user_hash}\\manifest.db").cursor()
        manifest.execute("""CREATE TABLE MAIL(
            ID          TEXT PRIMARY KEY    NOT NULL,
            FROMS       TEXT                NOT NULL,
            RCPT_TOS    TEXT                NOT NULL,
            TIMESTAMP   REAL                NOT NULL
        );""")
        manifest.connection.commit()
        password = hashlib.sha512(password.encode('utf-8')).hexdigest()
        curr.execute("INSERT INTO ACCOUNTS VALUES (:id, :user, :pass", {"id": cls.user_hash, "user": user, "pass": password})
        curr.connection.commit()
        cls.database = sqlite3.connect(f'.\\users\\{cls.user_hash}\manifest.db')
        cls._authenticate(cls.user_hash, password)
        

    class AuthError(Exception):
        """Raised when authentication failed"""
        pass

    def _authenticate(self, user: str, password: str) -> bool:
        curr = sqlite3.connect(".\\accounts.db").cursor()
        res = curr.execute("""SELECT * FROM ACCOUNTS WHERE USERID =:user AND PASS=:password""", {"user": user, "password": password}).fetchone()
        if not res:
            raise self.AuthError("Username or password incorrect")
        curr.close()

    def read_inbox(self, n: Optional[int] = None) -> list[email]:
        curr = self.database.cursor()
        statement = curr.execute('SELECT * FROM MAIL')
        if not n:
            n = statement.arraysize
        ret = []
        for _ in range(n):
            row = tuple(statement.fetchone())
            with open(f".\\users\\{self.user_hash}\\{row[0]}.mail", "r") as f:
                file_content = loads(b64decode(f.read()).decode('utf-8'))
            ret.append(email(row[0], row[1].split(','), row[2].split(','), row[3], file_content['content']))
        return ret
    
    def delete_email(self, email: email):
        return self.delete_guid(email.id)

    def delete_guid(self, guid: uuid.UUID):
        database = self.database.cursor()
        database.execute("DELETE FROM MAIL WHERE id=:uuid", {"uuid": str(guid)})
        os.remove(os.path.join(f".\\users\\{self.user_hash}\\{guid}.mail"))
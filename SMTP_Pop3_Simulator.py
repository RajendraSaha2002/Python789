

from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from enum import Enum, auto


# -------------------------------------------------------------------
# Shared helpers
# -------------------------------------------------------------------

def hmac_sign(secret_key: str, text: str) -> str:
    return hmac.new(
        secret_key.encode("utf-8"),
        text.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def hmac_verify(secret_key: str, text: str, signature: str) -> bool:
    expected = hmac_sign(secret_key, text)
    return hmac.compare_digest(expected, signature)


def b64_encode(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def b64_decode(value: str) -> str:
    return base64.b64decode(value.encode("ascii")).decode("utf-8")


# -------------------------------------------------------------------
# Email message and mailbox
# -------------------------------------------------------------------

@dataclass
class StoredMail:
    sender: str
    recipients: list[str]
    subject: str
    body: str
    raw_message: str
    signature: str
    deleted: bool = False

    @property
    def size(self) -> int:
        return len(self.raw_message.encode("utf-8"))


@dataclass
class Mailbox:
    users: dict[str, str] = field(default_factory=dict)
    messages: dict[str, list[StoredMail]] = field(default_factory=dict)

    def add_user(self, username: str, password: str) -> None:
        self.users[username] = password
        self.messages.setdefault(username, [])

    def valid_user(self, username: str, password: str) -> bool:
        return self.users.get(username) == password

    def deliver(self, recipient: str, message: StoredMail) -> bool:
        if recipient not in self.users:
            return False

        self.messages[recipient].append(message)
        return True

    def visible_messages(self, username: str) -> list[StoredMail]:
        return [mail for mail in self.messages.get(username, []) if not mail.deleted]

    def commit_deletions(self, username: str) -> None:
        self.messages[username] = [
            mail for mail in self.messages.get(username, [])
            if not mail.deleted
        ]


# -------------------------------------------------------------------
# SMTP server state machine
# -------------------------------------------------------------------

class SMTPState(Enum):
    CONNECTED = auto()
    EHLO_DONE = auto()
    AUTH_USERNAME = auto()
    AUTH_PASSWORD = auto()
    AUTHENTICATED = auto()
    MAIL_FROM_SET = auto()
    RCPT_TO_SET = auto()
    DATA_MODE = auto()
    CLOSED = auto()


class SMTPServer:
    def __init__(self, mailbox: Mailbox, signing_key: str) -> None:
        self.mailbox = mailbox
        self.signing_key = signing_key
        self.reset()

    def reset(self) -> None:
        self.state = SMTPState.CONNECTED
        self.username = ""
        self.mail_from = ""
        self.recipients: list[str] = []
        self.data_lines: list[str] = []

    def greeting(self) -> str:
        return "220 smtp.simulator.local ESMTP Ready"

    def command(self, client_input: str) -> list[str]:
        client_input = client_input.rstrip("\r\n")

        if self.state == SMTPState.CLOSED:
            return ["421 Connection already closed"]

        if self.state == SMTPState.AUTH_USERNAME:
            return self._auth_username(client_input)

        if self.state == SMTPState.AUTH_PASSWORD:
            return self._auth_password(client_input)

        if self.state == SMTPState.DATA_MODE:
            return self._data_input(client_input)

        if not client_input:
            return ["500 Empty command"]

        parts = client_input.split(" ", 1)
        command = parts[0].upper()
        argument = parts[1] if len(parts) > 1 else ""

        if command in ("EHLO", "HELO"):
            return self._ehlo(argument)

        if command == "AUTH":
            return self._auth(argument)

        if command == "MAIL":
            return self._mail_from(argument)

        if command == "RCPT":
            return self._rcpt_to(argument)

        if command == "DATA":
            return self._data()

        if command == "RSET":
            self.reset()
            return ["250 Message transaction reset"]

        if command == "NOOP":
            return ["250 OK"]

        if command == "QUIT":
            self.state = SMTPState.CLOSED
            return ["221 Bye"]

        return ["500 Command not recognized"]

    def _ehlo(self, hostname: str) -> list[str]:
        if not hostname.strip():
            return ["501 EHLO requires a hostname"]

        self.state = SMTPState.EHLO_DONE
        return [
            "250-smtp.simulator.local",
            "250-AUTH LOGIN",
            "250-SIZE 10485760",
            "250 8BITMIME",
        ]

    def _auth(self, argument: str) -> list[str]:
        if self.state not in (SMTPState.EHLO_DONE, SMTPState.AUTHENTICATED):
            return ["503 Send EHLO before AUTH"]

        if argument.upper() != "LOGIN":
            return ["504 Only AUTH LOGIN is implemented in this simulator"]

        self.state = SMTPState.AUTH_USERNAME
        return ["334 VXNlcm5hbWU6"]  # "Username:"

    def _auth_username(self, value: str) -> list[str]:
        try:
            self.username = b64_decode(value.strip())
        except Exception:
            self.state = SMTPState.EHLO_DONE
            return ["501 Invalid Base64 username"]

        self.state = SMTPState.AUTH_PASSWORD
        return ["334 UGFzc3dvcmQ6"]  # "Password:"

    def _auth_password(self, value: str) -> list[str]:
        try:
            password = b64_decode(value.strip())
        except Exception:
            self.state = SMTPState.EHLO_DONE
            return ["501 Invalid Base64 password"]

        if not self.mailbox.valid_user(self.username, password):
            self.username = ""
            self.state = SMTPState.EHLO_DONE
            return ["535 Authentication failed"]

        self.state = SMTPState.AUTHENTICATED
        return ["235 Authentication successful"]

    def _mail_from(self, argument: str) -> list[str]:
        if self.state != SMTPState.AUTHENTICATED:
            return ["530 Authentication required"]

        if not argument.upper().startswith("FROM:"):
            return ["501 Expected MAIL FROM:<address>"]

        address = argument[5:].strip().strip("<>")

        if "@" not in address:
            return ["501 Invalid sender address"]

        self.mail_from = address
        self.recipients = []
        self.state = SMTPState.MAIL_FROM_SET
        return ["250 Sender accepted"]

    def _rcpt_to(self, argument: str) -> list[str]:
        if self.state not in (SMTPState.MAIL_FROM_SET, SMTPState.RCPT_TO_SET):
            return ["503 Send MAIL FROM before RCPT TO"]

        if not argument.upper().startswith("TO:"):
            return ["501 Expected RCPT TO:<address>"]

        address = argument[3:].strip().strip("<>")

        if address not in self.mailbox.users:
            return ["550 Recipient does not exist on this server"]

        self.recipients.append(address)
        self.state = SMTPState.RCPT_TO_SET
        return ["250 Recipient accepted"]

    def _data(self) -> list[str]:
        if self.state != SMTPState.RCPT_TO_SET or not self.recipients:
            return ["503 Send RCPT TO before DATA"]

        self.data_lines = []
        self.state = SMTPState.DATA_MODE
        return ["354 End email data with <CRLF>.<CRLF>"]

    def _data_input(self, line: str) -> list[str]:
        if line != ".":
            # SMTP dot unstuffing
            if line.startswith(".."):
                line = line[1:]
            self.data_lines.append(line)
            return []

        raw_message = "\r\n".join(self.data_lines)
        message = self._create_message(raw_message)

        delivered = 0
        for recipient in self.recipients:
            if self.mailbox.deliver(recipient, message):
                delivered += 1

        self.mail_from = ""
        self.recipients = []
        self.data_lines = []
        self.state = SMTPState.AUTHENTICATED

        return [f"250 Message accepted and delivered to {delivered} mailbox(es)"]

    def _create_message(self, raw_message: str) -> StoredMail:
        parsed = EmailMessage()
        parsed.set_content("")

        subject = "(No subject)"
        body = raw_message

        if "\r\n\r\n" in raw_message:
            headers, body = raw_message.split("\r\n\r\n", 1)
            for header in headers.split("\r\n"):
                if header.lower().startswith("subject:"):
                    subject = header.split(":", 1)[1].strip()

        canonical_text = (
            f"From:{self.mail_from}\n"
            f"To:{','.join(self.recipients)}\n"
            f"Subject:{subject}\n"
            f"Body:{body}"
        )

        signature = hmac_sign(self.signing_key, canonical_text)

        signed_raw = (
            raw_message
            + "\r\nX-Demo-DKIM-Algorithm: hmac-sha256"
            + "\r\nX-Demo-DKIM-Signature: "
            + signature
        )

        return StoredMail(
            sender=self.mail_from,
            recipients=list(self.recipients),
            subject=subject,
            body=body,
            raw_message=signed_raw,
            signature=signature,
        )


# -------------------------------------------------------------------
# POP3 server state machine
# -------------------------------------------------------------------

class POP3State(Enum):
    AUTHORIZATION = auto()
    TRANSACTION = auto()
    CLOSED = auto()


class POP3Server:
    def __init__(self, mailbox: Mailbox, signing_key: str) -> None:
        self.mailbox = mailbox
        self.signing_key = signing_key
        self.state = POP3State.AUTHORIZATION
        self.pending_user = ""
        self.username = ""

    def greeting(self) -> str:
        return "+OK POP3 server ready"

    def command(self, client_input: str) -> list[str]:
        client_input = client_input.strip()

        if self.state == POP3State.CLOSED:
            return ["-ERR Connection closed"]

        if not client_input:
            return ["-ERR Empty command"]

        parts = client_input.split(" ", 1)
        command = parts[0].upper()
        argument = parts[1].strip() if len(parts) > 1 else ""

        if command == "QUIT":
            if self.state == POP3State.TRANSACTION and self.username:
                self.mailbox.commit_deletions(self.username)

            self.state = POP3State.CLOSED
            return ["+OK Goodbye"]

        if self.state == POP3State.AUTHORIZATION:
            return self._authorization(command, argument)

        if self.state == POP3State.TRANSACTION:
            return self._transaction(command, argument)

        return ["-ERR Invalid state"]

    def _authorization(self, command: str, argument: str) -> list[str]:
        if command == "USER":
            if argument not in self.mailbox.users:
                return ["-ERR Unknown user"]

            self.pending_user = argument
            return ["+OK User accepted"]

        if command == "PASS":
            if not self.pending_user:
                return ["-ERR Send USER before PASS"]

            if not self.mailbox.valid_user(self.pending_user, argument):
                self.pending_user = ""
                return ["-ERR Authentication failed"]

            self.username = self.pending_user
            self.pending_user = ""
            self.state = POP3State.TRANSACTION
            return ["+OK Mailbox locked and ready"]

        return ["-ERR Authenticate with USER and PASS first"]

    def _transaction(self, command: str, argument: str) -> list[str]:
        messages = self.mailbox.visible_messages(self.username)

        if command == "STAT":
            total_size = sum(message.size for message in messages)
            return [f"+OK {len(messages)} {total_size}"]

        if command == "LIST":
            if argument:
                return self._list_one(messages, argument)

            response = [f"+OK {len(messages)} messages"]
            for index, message in enumerate(messages, start=1):
                response.append(f"{index} {message.size}")
            response.append(".")
            return response

        if command == "RETR":
            return self._retrieve(messages, argument)

        if command == "DELE":
            return self._delete(messages, argument)

        if command == "NOOP":
            return ["+OK"]

        return ["-ERR Unsupported POP3 command"]

    def _list_one(self, messages: list[StoredMail], argument: str) -> list[str]:
        try:
            number = int(argument)
        except ValueError:
            return ["-ERR Message number must be an integer"]

        if number < 1 or number > len(messages):
            return ["-ERR No such message"]

        return [f"+OK {number} {messages[number - 1].size}"]

    def _retrieve(self, messages: list[StoredMail], argument: str) -> list[str]:
        try:
            number = int(argument)
        except ValueError:
            return ["-ERR Message number must be an integer"]

        if number < 1 or number > len(messages):
            return ["-ERR No such message"]

        message = messages[number - 1]
        valid = self._verify_message(message)

        response = [
            f"+OK {message.size} octets",
            message.raw_message,
            f"X-Demo-DKIM-Verification: {'PASS' if valid else 'FAIL'}",
            ".",
        ]
        return response

    def _delete(self, messages: list[StoredMail], argument: str) -> list[str]:
        try:
            number = int(argument)
        except ValueError:
            return ["-ERR Message number must be an integer"]

        if number < 1 or number > len(messages):
            return ["-ERR No such message"]

        messages[number - 1].deleted = True
        return [f"+OK Message {number} marked for deletion"]

    def _verify_message(self, message: StoredMail) -> bool:
        canonical_text = (
            f"From:{message.sender}\n"
            f"To:{','.join(message.recipients)}\n"
            f"Subject:{message.subject}\n"
            f"Body:{message.body}"
        )
        return hmac_verify(self.signing_key, canonical_text, message.signature)


# -------------------------------------------------------------------
# Client simulator
# -------------------------------------------------------------------

class ProtocolSimulator:
    def __init__(self) -> None:
        self.key = "private-demo-signing-key-2026"

        self.mailbox = Mailbox()
        self.mailbox.add_user("alice@example.com", "alice123")
        self.mailbox.add_user("bob@example.com", "bob123")

        self.smtp = SMTPServer(self.mailbox, self.key)
        self.pop3 = POP3Server(self.mailbox, self.key)

    @staticmethod
    def show(client: str, message: str) -> None:
        print(f"\n{client}: {message}")

    @staticmethod
    def show_responses(responses: list[str]) -> None:
        for response in responses:
            print(f"SERVER: {response}")

    def smtp_send(self, command: str) -> None:
        self.show("SMTP CLIENT", command)
        self.show_responses(self.smtp.command(command))

    def pop3_send(self, command: str) -> None:
        self.show("POP3 CLIENT", command)
        self.show_responses(self.pop3.command(command))

    def run_smtp_demo(self) -> None:
        print("\n" + "=" * 70)
        print("SMTP TWO-PARTY EMAIL TRANSFER SIMULATION")
        print("=" * 70)

        print(f"SERVER: {self.smtp.greeting()}")

        self.smtp_send("EHLO client.example.com")
        self.smtp_send("AUTH LOGIN")
        self.smtp_send(b64_encode("alice@example.com"))
        self.smtp_send(b64_encode("alice123"))
        self.smtp_send("MAIL FROM:<alice@example.com>")
        self.smtp_send("RCPT TO:<bob@example.com>")
        self.smtp_send("DATA")

        self.smtp_send("From: Alice <alice@example.com>")
        self.smtp_send("To: Bob <bob@example.com>")
        self.smtp_send("Subject: SMTP Protocol Simulator Test")
        self.smtp_send("")
        self.smtp_send("Hello Bob,")
        self.smtp_send("This email was sent through the simulated SMTP server.")
        self.smtp_send("The message has an HMAC-SHA256 demo signature.")
        self.smtp_send(".")
        self.smtp_send("QUIT")

    def run_pop3_demo(self) -> None:
        print("\n" + "=" * 70)
        print("POP3 TWO-PARTY EMAIL RETRIEVAL SIMULATION")
        print("=" * 70)

        print(f"SERVER: {self.pop3.greeting()}")

        self.pop3_send("USER bob@example.com")
        self.pop3_send("PASS bob123")
        self.pop3_send("STAT")
        self.pop3_send("LIST")
        self.pop3_send("RETR 1")
        self.pop3_send("QUIT")

    def run(self) -> None:
        self.run_smtp_demo()
        self.run_pop3_demo()

        print("\n" + "=" * 70)
        print("SIMULATION FINISHED SUCCESSFULLY")
        print("=" * 70)


def main() -> None:
    try:
        simulator = ProtocolSimulator()
        simulator.run()

    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")

    except Exception as error:
        print(f"\nHandled error: {type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
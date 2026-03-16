from __future__ import annotations

import shlex
from pathlib import Path

import pexpect


class SshClient:
    def __init__(self, user: str, password: str, host: str):
        self.user = user
        self.password = password
        self.host = host

    def _expect_password(self, child: pexpect.spawn, timeout: int = 30) -> None:
        while True:
            idx = child.expect(
                [
                    r"Are you sure you want to continue connecting \(yes/no/\[fingerprint\]\)\?",
                    r"[Pp]assword:",
                    pexpect.EOF,
                    pexpect.TIMEOUT,
                ],
                timeout=timeout,
            )
            if idx == 0:
                child.sendline("yes")
                continue
            if idx == 1:
                child.sendline(self.password)
                return
            if idx == 2:
                return
            raise TimeoutError(child.before)

    def copy_file(self, local_path: Path, remote_path: str) -> None:
        cmd = (
            f"scp -o StrictHostKeyChecking=no {shlex.quote(str(local_path))} "
            f"{shlex.quote(self.user)}@{shlex.quote(self.host)}:{shlex.quote(remote_path)}"
        )
        child = pexpect.spawn(cmd, encoding="utf-8")
        self._expect_password(child)
        child.expect(pexpect.EOF, timeout=120)
        if child.exitstatus not in (0, None):
            raise RuntimeError(child.before)

    def run(self, remote_cmd: str, timeout: int = 120) -> str:
        status, output = self.run_with_status(remote_cmd, timeout=timeout)
        if status not in (0, None):
            raise RuntimeError(output.strip() or f"ssh remote command failed with exit status {status}")
        return output

    def run_with_status(self, remote_cmd: str, timeout: int = 120) -> tuple[int | None, str]:
        cmd = f"ssh -o StrictHostKeyChecking=no {shlex.quote(self.user)}@{shlex.quote(self.host)} {shlex.quote(remote_cmd)}"
        child = pexpect.spawn(cmd, encoding="utf-8")
        self._expect_password(child, timeout=timeout)
        child.expect(pexpect.EOF, timeout=timeout)
        return child.exitstatus, child.before or ""

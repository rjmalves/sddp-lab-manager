import asyncio
from typing import List, Optional, Tuple

TIMEOUT_DEFAULT = 24 * 3600


async def run_terminal(
    cmds: List[str], timeout: float = TIMEOUT_DEFAULT
) -> Tuple[Optional[int], str]:
    """
    Runs a command on the terminal and returns.

    :param cmds: Commands and args to be executed
    :param timeout: Timeout for giving up on the command
    :return: Return code and outputs
    :rtype: Tuple[int, str]
    """
    cmd = " ".join(cmds)
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    if stdout:
        return proc.returncode, stdout.decode("utf-8")
    if stderr:
        return proc.returncode, stderr.decode("utf-8")

    return 0, ""

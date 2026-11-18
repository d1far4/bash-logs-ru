"""Проверка: запускает все решения из README.md и сверяет вывод с ожидаемым.

Запуск:  python check.py
Нужен Python 3.8+ (только стандартная библиотека) и bash. Для каждого блока
<details> берётся первый блок ```bash и следующий за ним блок ```text. Код
выполняется через bash из корня репозитория с LC_ALL=C, вывод (stdout) сравнивается
с ожидаемым: пробелы в конце строк и пустые строки в конце игнорируются.
Если README показывает только начало длинного вывода, полный ожидаемый вывод
лежит в expected/taskNN.txt, и сравнение идёт с ним.
Код возврата 1, если хотя бы одно решение не совпало или задач не 15.
"""
import difflib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED_TASKS = 15

DETAILS = re.compile(r"<details>.*?</details>", re.S)
BASH_BLOCK = re.compile(r"```bash\s*\n(.*?)```", re.S)
TEXT_BLOCK = re.compile(r"```text\s*\n(.*?)```", re.S)
TITLE = re.compile(r"^###\s+(Задача\s+(\d+)[^\n]*)$", re.M)

GIT_BASH_CANDIDATES = [
    r"C:\Program Files\Git\usr\bin\bash.exe",
    r"C:\Program Files (x86)\Git\usr\bin\bash.exe",
]


def find_bash():
    """Путь к bash. В Windows игнорируем лаунчер WSL (System32, WindowsApps)."""
    found = shutil.which("bash")
    if os.name != "nt":
        return found
    if found and not re.search(r"(?i)system32|windowsapps", found):
        return found
    for cand in GIT_BASH_CANDIDATES:
        if os.path.exists(cand):
            return cand
    return None


def build_env(bash):
    env = dict(os.environ)
    env["LC_ALL"] = "C"
    if os.name == "nt":
        extra = []
        for cand in GIT_BASH_CANDIDATES:
            if os.path.isdir(os.path.dirname(cand)):
                extra.append(os.path.dirname(cand))
        parent = os.path.dirname(bash)
        if parent not in extra:
            extra.append(parent)
        env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    return env


def run_code(bash, env, code):
    """Выполняет код в bash из корня репозитория. Возвращает (код, stdout, stderr)."""
    fd, path = tempfile.mkstemp(suffix=".sh")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(code + "\n")
        proc = subprocess.run(
            [bash, path], cwd=str(HERE), env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=60,
        )
    finally:
        os.unlink(path)
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    return proc.returncode, out, err


def normalize(text):
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return lines


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    bash = find_bash()
    if not bash:
        print("bash не найден: установите Git for Windows или используйте WSL/Linux/macOS")
        return 1
    env = build_env(bash)
    readme = (HERE / "README.md").read_text(encoding="utf-8")
    titles = [(m.start(), m.group(1).strip(), int(m.group(2))) for m in TITLE.finditer(readme)]

    solved = failed = 0
    for m in DETAILS.finditer(readme):
        block = m.group(0)
        code_m = BASH_BLOCK.search(block)
        if not code_m:
            continue
        text_m = TEXT_BLOCK.search(block, code_m.end())
        title, num = "?", 0
        for pos, t, n in titles:
            if pos < m.start():
                title, num = t, n
        solved += 1
        if not text_m:
            print("FAIL  %s: нет блока с ожидаемым выводом" % title[:50])
            failed += 1
            continue

        shown = normalize(text_m.group(1))
        expected = shown
        full = HERE / "expected" / ("task%02d.txt" % num)
        problem = None
        if full.exists():
            expected = normalize(full.read_text(encoding="utf-8"))
            if expected[:len(shown)] != shown:
                problem = "начало вывода в README не совпадает с %s" % full.name

        try:
            rc, out, err = run_code(bash, env, code_m.group(1))
        except subprocess.TimeoutExpired:
            print("FAIL  %s: превышено время выполнения" % title[:50])
            failed += 1
            continue
        actual = normalize(out)
        if problem is None and rc != 0:
            problem = "код возврата %d: %s" % (rc, err.strip()[:200])
        if problem is None and actual != expected:
            problem = "вывод не совпал"
        if problem is None:
            print("ok    %-52s строк: %d" % (title[:52], len(actual)))
        else:
            failed += 1
            print("FAIL  %s: %s" % (title[:52], problem))
            for ln in list(difflib.unified_diff(expected, actual, "ожидалось", "получено",
                                                lineterm="", n=1))[:20]:
                print("      " + ln)

    print("\nзадач проверено: %d, ok: %d, FAIL: %d" % (solved, solved - failed, failed))
    if solved != EXPECTED_TASKS:
        print("ожидалось %d задач, найдено %d" % (EXPECTED_TASKS, solved))
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

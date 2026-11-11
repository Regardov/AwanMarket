"""Exercise the launcher with fake Docker and health checks, without changing user data."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class LocalLauncherTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="awanmarket launcher ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / "shop with spaces"
        (self.project / "scripts").mkdir(parents=True)
        source = Path(__file__).resolve().parent.parent
        for name in [".env.example", "docker-compose.yml"]:
            shutil.copyfile(source / name, self.project / name)
        shutil.copyfile(source / "scripts/local-site.ps1", self.project / "scripts/local-site.ps1")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "docker.jsonl"
        fake = self.bin / "fake_docker.py"
        fake.write_text('''import json, os, sys
with open(os.environ['MOCK_DOCKER_LOG'], 'a') as f: f.write(json.dumps(sys.argv[1:]) + '\\n')
if sys.argv[1] == 'info': print('linux')
if 'up' in sys.argv and os.environ.get('MOCK_BUILD_FAIL') == '1':
    print('Build failed', file=sys.stderr)
    sys.exit(17)
''', encoding="utf-8")
        if os.name == "nt":
            (self.bin / "docker.cmd").write_text(
                f'@"{sys.executable}" "{fake}" %*\r\n@exit /b %errorlevel%\r\n',
                encoding="utf-8",
            )
        else:
            docker = self.bin / "docker"
            docker.write_text(f'#!{sys.executable}\nexec(compile(open({str(fake)!r}).read(), {str(fake)!r}, "exec"))\n')
            docker.chmod(0o755)
        self.browser_log = self.root / "browser.txt"
        self.wrapper = self.root / "run.ps1"
        self.wrapper.write_text('''param([string]$Launcher, [switch]$Stop, [switch]$NoBrowser)
function global:Invoke-RestMethod { return @{ status = 'ok'; service = 'awanmarket' } }
function global:Start-Process { param([string]$FilePath) [IO.File]::WriteAllText($env:MOCK_BROWSER_LOG, $FilePath) }
& $Launcher -Stop:$Stop -NoBrowser:$NoBrowser
exit $LASTEXITCODE
''', encoding="utf-8")
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        MOCK_DOCKER_LOG=str(self.log), MOCK_BROWSER_LOG=str(self.browser_log))

    def launch(self, *args, fail=False):
        env = dict(self.env)
        if fail:
            env["MOCK_BUILD_FAIL"] = "1"
        shell = os.getenv("POWERSHELL_EXE", "powershell.exe" if os.name == "nt" else "pwsh")
        return subprocess.run([shell, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
                               "-File", str(self.wrapper), "-Launcher",
                               str(self.project / "scripts/local-site.ps1"), *args],
                              env=env, capture_output=True, text=True, timeout=30)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_first_launch_generates_env_and_opens_site(self):
        result = self.launch()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        env = (self.project / ".env").read_text(encoding="utf-8")
        secret = next(line for line in env.splitlines() if line.startswith("SECRET_KEY="))
        self.assertRegex(secret, r"^SECRET_KEY=[a-f0-9]{64}$")
        up = next(call for call in self.calls() if "up" in call)
        self.assertTrue(os.path.samefile(up[up.index("--file") + 1], self.project / "docker-compose.yml"))
        self.assertIn("--wait", up)
        self.assertIn("--build", up)
        self.assertEqual(self.browser_log.read_text(), "http://localhost:8080")

    def test_relaunch_preserves_env_and_can_skip_browser(self):
        original = b"SECRET_KEY=my-existing-key\nADMIN_PASSWORD=keep-me\n"
        (self.project / ".env").write_bytes(original)
        result = self.launch("-NoBrowser")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.project / ".env").read_bytes(), original)
        self.assertFalse(self.browser_log.exists())

    def test_build_failure_does_not_open_browser(self):
        result = self.launch(fail=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("17", result.stdout)
        self.assertFalse(self.browser_log.exists())

    def test_stop_preserves_database_and_does_not_create_env(self):
        result = self.launch("-Stop")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.calls()
        self.assertEqual(calls[-1][-1], "stop")
        self.assertFalse(any("down" in call or "--volumes" in call for call in calls))
        self.assertFalse((self.project / ".env").exists())
        self.assertFalse(self.browser_log.exists())


if __name__ == "__main__":
    unittest.main()

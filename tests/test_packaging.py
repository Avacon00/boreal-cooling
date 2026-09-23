import hashlib
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_versions_and_arch_dependency_bounds_match(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())
        self.assertEqual(project["project"]["version"], "0.2.5")
        self.assertIn("Pillow>=10.2,<13", project["project"]["dependencies"])
        self.assertIn("liquidctl>=1.16,<1.17", project["project"]["dependencies"])
        template = (ROOT / "packaging/arch/PKGBUILD.in").read_text()
        self.assertIn("url='https://github.com/Avacon00/boreal-cooling'", template)
        for value in ("python>=3.12", "python-pillow>=10.2", "python-pillow<13",
                      "liquidctl>=1.16", "liquidctl<1.17"):
            self.assertIn(value, template)

    def test_release_archive_is_reproducible_and_clean(self):
        script = ROOT / "tools/build-arch-release.py"
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            subprocess.run([sys.executable, script, "--output", first], check=True,
                           stdout=subprocess.DEVNULL)
            subprocess.run([sys.executable, script, "--output", second], check=True,
                           stdout=subprocess.DEVNULL)
            one = Path(first) / "boreal-cooling-0.2.5.tar.gz"
            two = Path(second) / "boreal-cooling-0.2.5.tar.gz"
            self.assertEqual(hashlib.sha256(one.read_bytes()).digest(),
                             hashlib.sha256(two.read_bytes()).digest())
            pkgbuild = (Path(first) / "PKGBUILD").read_text()
            self.assertNotIn("@VERSION@", pkgbuild)
            self.assertNotIn("@SHA256@", pkgbuild)
            self.assertIn(hashlib.sha256(one.read_bytes()).hexdigest(), pkgbuild)

    def test_package_install_does_not_enable_services(self):
        install_script = (ROOT / "packaging/arch/boreal-cooling.install").read_text()
        self.assertNotIn("systemctl --user enable", install_script)
        self.assertNotIn("systemctl --user start", install_script)
        self.assertNotIn("rm -rf", install_script)


if __name__ == "__main__":
    unittest.main()

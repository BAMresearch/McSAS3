from pathlib import Path
from setuptools import setup, find_packages
import sys
import versioneer

min_version = (3, 8)
if sys.version_info < min_version:
    error = """
pyscicat does not support Python {0}.{1}.
Python {2}.{3} and above is required. Check your Python version like so:

python3 --version

This may be due to an out-of-date pip. Make sure you have pip >= 9.0.1.
Upgrade pip like so:

pip install --upgrade pip
""".format(
        *(sys.version_info[:2] + min_version)
    )
    sys.exit(error)

here = Path(__file__).absolute()

with open(here.with_name("README.md"), encoding="utf-8") as readme_file:
    readme = readme_file.read()


def read_requirements_from_here(here: Path, filename: str) -> list:
    assert here.with_name(
        filename
    ).exists(), f"requirements filename {filename} does not exist"
    with open(here.with_name(filename)) as requirements_file:
        # Parse requirements.txt, ignoring any commented-out lines.
        requirements = [
            line
            for line in requirements_file.read().splitlines()
            if not line.startswith("#")
        ]
    return requirements


extras_require = {}
extras_require["base"] = read_requirements_from_here(here, "requirements.txt")
# extras_require["h5tools"] = read_requirements_from_here(here, "requirements-hdf5.txt")

setup(
    name="McSAS3",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="McSAS3 Refactored McSAS for analysis of X-ray and Neutron scattering data",
    long_description=readme,
    author="Brian R. Pauw",
    author_email="brian.pauw@bam.de",
    url="https://github.com/bamresearch/mcsas3",
    python_requires=">={}".format(".".join(str(n) for n in min_version)),
    packages=find_packages(exclude=["docs", "tests"]),
    include_package_data=True,
    extras_require=extras_require,
    install_requires=extras_require["base"],
    license="GPL V3",
    classifiers=[
        "Development Status :: 4-Beta",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
    ],
)

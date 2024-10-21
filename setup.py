from setuptools import find_packages, setup

from app import __version__

long_description = "sddp_lab_manager"

requirements = []
with open("requirements.txt", "r") as fh:
    requirements = fh.readlines()

setup(
    name="sddp_lab_manager",
    version=__version__,
    author="Rogerio Alves",
    author_email="rogerioalves.ee@gmail.com",
    description="sddp_lab_manager",
    long_description=long_description,
    packages=find_packages(),
    py_modules=["main", "sintetizador"],
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
    ],
    entry_points="""
        [console_scripts]
        sddp-lab-manager=main:main
    """,
    python_requires=">=3.10",
    install_requires=requirements,
)

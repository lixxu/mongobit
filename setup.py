"""
MongoBit
--------

Simple pymongo orm
"""
from setuptools import setup

setup(
    name="MongoBit",
    version="0.7.2",
    url="https://github.com/lixxu/mongobit",
    license="BSD",
    author="Lix Xu",
    author_email="xuzenglin@gmail.com",
    description="Simple pymongo orm",
    long_description=__doc__,
    packages=["mongobit"],
    zip_safe=False,
    platforms="any",
    install_requires=["pymongo", "six"],
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)

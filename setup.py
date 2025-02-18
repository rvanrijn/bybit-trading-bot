from setuptools import setup, find_packages

setup(
    name="bybit-trading-bot",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'pybit>=5.5.0',
        'websocket-client>=1.7.0',
        'pandas>=2.2.0',
        'numpy>=1.26.4',
        'pyyaml>=6.0.1',
        'python-dotenv>=1.0.1',
        'matplotlib>=3.8.2'
    ],
)
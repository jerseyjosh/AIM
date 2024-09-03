from setuptools import setup, find_packages

setup(
    name='aim_tools',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'streamlit',
        'aiohttp',
        'beautifulsoup4',
        'selenium-driverless',
        'python-dotenv',
        'elevenlabs',
        'aiolimiter',
        'tqdm',
        'python-dotenv',
    ],
)

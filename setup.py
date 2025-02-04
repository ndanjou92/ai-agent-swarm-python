from setuptools import setup, find_packages

setup(
    name='ai_agent_swarm',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        # Add your required dependencies here
        'autoGen',
        'azure-openai',
        'sailpoint-python-sdk'
    ],
    entry_points={
        'console_scripts': [
            'ai-agent-swarm=main:main',
        ],
    },
)

# REQUIREMENTS

This file covers aspects of hardware and software requirements for our testing tool Keeper (located in `testing_tool` folder) and its IDE plugin (located in `ide_plugin` folder) we developed.

## Hardware environment

Processor: 2 gigahertz (GHz) or faster processor; Should be intel chip.

Memory: 4G RAM or higher

Disk: 1GB disk space

Network connection: Required

In our paper, all experiments were done on MacBook with intel chip. Our tool also supports Linux environment. Note that our tool does not support M1 chip due to CVC4 constraint solver.

## Software environment

### System enviornment
Linux/Unix operating system
Visual Studio Code >= 1.61
Node.js >= 14.17
CVC4 constraint solver == 1.6

### Python
Python 3.8 with following packages

numpy==1.17.3
psutil==5.7.3 
pillow==8.3.0
google-cloud-language==1.3.0
google-cloud-vision==1.0.0
google-cloud-speech==2.0.0
pyttsx3==2.9.0
pyaudio==0.2.11
wave==0.0.2
pandas==0.23.4
nltk==3.3
icrawler==0.6.3
bs4==0.0.1
scikit-learn==0.22
Wikidata==0.7.0
jedi==0.17.0
tensorflow==2.5.0
transformers==4.4.2
wikipedia===1.4.0


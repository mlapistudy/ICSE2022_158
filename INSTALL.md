# INSTALL



## Python packages

### Install Python and pip

Our testing tool Keeper is implemented in Python3.8. It can be installed with

```
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.8
```

and verfied with

```
python3.8 --version
```

Then install package management tool pip with

```
sudo apt install python3-pip
```

and verfied with

```
pip3 --version
```

or

```
/usr/bin/python3.8 -m pip --version
```

Please make sure `python3.8` is a valid command.

### Install Google Cloud AI

`Tools/API_wrappers` folder includes wrapper functions for Google Cloud AI Services.

To install these packages:

```
/usr/bin/python3.8 -m pip install google-cloud-language==1.3.0 --user
/usr/bin/python3.8 -m pip install google-cloud-vision==1.0.0 --user
/usr/bin/python3.8 -m pip install google-cloud-speech==2.0.0 --user
/usr/bin/python3.8 -m pip install google-cloud-texttospeech==2.2.0 --user
/usr/bin/python3.8 -m pip install google-api-python-client==1.10.0 --user
/usr/bin/python3.8 -m pip install google-auth-httplib2==0.0.4 --user
/usr/bin/python3.8 -m pip install google-auth-oauthlib --user
```

To enable APIs in Google account and create credentials, please following Google official document

1. Vision: https://cloud.google.com/vision/docs/setup
2. Speech-to-Text: https://cloud.google.com/speech-to-text/docs/quickstart-client-libraries
3. Language: https://cloud.google.com/natural-language/docs/setup

Everytime before executing, run `export GOOGLE_APPLICATION_CREDENTIALS=path/to/your/credential.json`

### Install other packages

For other packages:

```
python3.8 -m pip install numpy==1.17.3 --user
python3.8 -m pip install psutil==5.7.3 --user
python3.8 -m pip install pillow==8.3.0 --user
python3.8 -m pip install pyttsx3==2.9.0 --user
python3.8 -m pip install pip install pyaudio --user
python3.8 -m pip install wave==0.0.2 --user
python3.8 -m pip install pandas==0.23.4 --user
python3.8 -m pip install nltk==3.3 --user
python3.8 -m pip install icrawler==0.6.3 --user
python3.8 -m pip install bs4==0.0.1 --user
python3.8 -m pip install scikit-learn==0.22 --user
python3.8 -m pip install Wikidata==0.7.0 --user
python3.8 -m pip install jedi==0.17.0 --user
python3.8 -m pip install z3-solver==4.8.12.0 --user
python3.8 -m pip install tensorflow==2.5.0 --user
python3.8 -m pip install transformers==4.4.2 --user
python3.8 -m pip install wikipedia===1.4.0 --user
python3.8 -m pip install anytree==2.5.0 --user
python3.8 -m pip install jinja2==4.4.2 --user
python3.8 -m pip install typing==1.4.0 --user
```

## CVC4 constraint solver
It requires CVC4 (version 1.6) to do constrainint solving. Instructions are at `https://github.com/CVC4/CVC4/issues/1533`. The compiling might take over 10 minutes. Specifically,

On Linux,
```bash
git clone https://github.com/CVC4/CVC4.git CVC4_python
cd CVC4_python
git checkout 1.6.x
export LC_ALL="en_US.UTF-8"
export LC_CTYPE="en_US.UTF-8"
export PYTHON_CONFIG=/usr/bin/python3.8-config   # Not needed in conda env
export PYTHON_VERSION=3.8                        # Not needed in conda env
contrib/get-antlr-3.4
./autogen.sh
./configure ANTLR=`pwd`/antlr-3.4/bin/antlr3 --enable-language-bindings=python --prefix `pwd`/out_dir
echo "python_cpp_SWIGFLAGS = -py3" >> src/bindings/Makefile.am
autoreconf
make && make install
cd out_dir/share/pyshared/
ln -s ../../lib/pyshared/CVC4.so _CVC4.so

cd /path/to/cvc4/CVC4_python
export PYTHONPATH=/path/to/cvc4/CVC4_python/out_dir/share/pyshared/
# a test to see wether the install is sucess or not
python3.8 examples/SimpleVC.py                   # python if running default python
```


On Mac
```bash
brew update
brew install wget
brew install autoconf
brew install automake
brew install libtool
brew install boost
brew install gmp
brew install gcc
brew install swig
brew install coreutils

git clone https://github.com/CVC4/CVC4.git CVC4_python
cd CVC4_python
git checkout 1.6.x
export PYTHON_CONFIG=/usr/local/bin/python3.8-config
export PYTHON_VERSION=3.8
contrib/get-antlr-3.4
brew install autoconf
brew install automake
./autogen.sh
./configure --enable-optimized --with-antlr-dir=`pwd`/antlr-3.4 ANTLR=`pwd`/antlr-3.4/bin/antlr3 --enable-language-bindings=python
echo "python_cpp_SWIGFLAGS = -py3" >> src/bindings/Makefile.am
autoreconf
make && make install
export PYTHONPATH=/usr/local/share/pyshared/
cd /usr/local/share/pyshared/
ln -s ../../lib/pyshared/CVC4.so _CVC4.so
# a test to see wether the install is sucess or not
python3.8 examples/SimpleVC.py
```

Everytime before executing, run `export PYTHONPATH=/usr/local/share/pyshared/`


## Node.js
Our IDE plugin is for VS Code. So it is implemented with Node.js.

Install [VSCode](https://code.visualstudio.com).

Install Node.js and `npm install -g yo generator-code`, following [VSCode official document](https://code.visualstudio.com/api/get-started/your-first-extension)

Install other packages:

```bash
cd ide_plugin
npm install @types/node
```


## How to run Keeper

The IDE plugin of Keeper is in `ide_plugin` folder. Please follow the `ide_plugin/readme.md` file.
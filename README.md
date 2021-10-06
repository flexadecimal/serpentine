```
-----------------------------------------------------------------------------------
  ██████ ▓█████  ██▀███   ██▓███  ▓█████  ███▄    █ ▄▄▄█████▓ ██▓ ███▄    █ ▓█████ 
▒██    ▒ ▓█   ▀ ▓██ ▒ ██▒▓██░  ██▒▓█   ▀  ██ ▀█   █ ▓  ██▒ ▓▒▓██▒ ██ ▀█   █ ▓█   ▀ 
░ ▓██▄   ▒███   ▓██ ░▄█ ▒▓██░ ██▓▒▒███   ▓██  ▀█ ██▒▒ ▓██░ ▒░▒██▒▓██  ▀█ ██▒▒███   
  ▒   ██▒▒▓█  ▄ ▒██▀▀█▄  ▒██▄█▓▒ ▒▒▓█  ▄ ▓██▒  ▐▌██▒░ ▓██▓ ░ ░██░▓██▒  ▐▌██▒▒▓█  ▄ 
▒██████▒▒░▒████▒░██▓ ▒██▒▒██▒ ░  ░░▒████▒▒██░   ▓██░  ▒██▒ ░ ░██░▒██░   ▓██░░▒████▒
▒ ▒▓▒ ▒ ░░░ ▒░ ░░ ▒▓ ░▒▓░▒▓▒░ ░  ░░░ ▒░ ░░ ▒░   ▒ ▒   ▒ ░░   ░▓  ░ ▒░   ▒ ▒ ░░ ▒░ ░
░ ░▒  ░ ░ ░ ░  ░  ░▒ ░ ▒░░▒ ░      ░ ░  ░░ ░░   ░ ▒░    ░     ▒ ░░ ░░   ░ ▒░ ░ ░  ░
░  ░  ░     ░     ░░   ░ ░░          ░      ░   ░ ░   ░       ▒ ░   ░   ░ ░    ░   
------░-----░--░---░-----------------░--░---------░-----------░-----------░----░--░
                e f i      c h i p t u n i n g      s o l u t i o n
-----------------------------------------------------------------------------------
```
Serpentine is a modern, browser-based chiptuning solution that implements the
binary description XDF/ADX formats used in [TunerPro](https://tunerpro.net/).
Effectively, this means you can use Serpentine to tune any TunerPro-supported stock
ECU. 

Testing and development was done using the author's car, a 1998 Volvo V70R using
Bosch Motronic 4.4 fuel injection - many thanks to the [M44 Wiki](https://m44.fandom.com/wiki/M44_Wiki) for example XDF/ADX/BIN files.

## Requirements
Built for Python 3.9 and later.

## Supported Features
- XDF parameter editing

## Getting started
    pipenv install
    pipenv shell
    python xdf_parse.py

## Unit tests
    python -m unittest core.test.simpleTest

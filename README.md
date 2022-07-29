```
====================================================================
▓█████  ▄████▄   █    ██   ██████  ██░ ██  ▄▄▄       ██▀███   ██ ▄█▀
▓█   ▀ ▒██▀ ▀█   ██  ▓██▒▒██    ▒ ▓██░ ██▒▒████▄    ▓██ ▒ ██▒ ██▄█▒ 
▒███   ▒▓█    ▄ ▓██  ▒██░░ ▓██▄   ▒██▀▀██░▒██  ▀█▄  ▓██ ░▄█ ▒▓███▄░ 
▒▓█  ▄ ▒▓▓▄ ▄██▒▓▓█  ░██░  ▒   ██▒░▓█ ░██ ░██▄▄▄▄██ ▒██▀▀█▄  ▓██ █▄ 
░▒████▒▒ ▓███▀ ░▒▒█████▓ ▒██████▒▒░▓█▒░██▓ ▓█   ▓██▒░██▓ ▒██▒▒██▒ █▄
=░=▒░=░░=░▒=▒==░░▒▓▒=▒=▒=▒=▒▓▒=▒=░=▒=░░▒░▒=▒▒===▓▒█░░=▒▓=░▒▓░▒=▒▒=▓▒
            e f i  c h i p t u n i n g  s o l u t i o n            
====================================================================
```
`ecushark` is a modern, browser-based chiptuning solution that implements the
binary description XDF/ADX formats used in [TunerPro](https://tunerpro.net/).
Effectively, this means you can use `ecushark` to tune any TunerPro-supported stock
ECU. 

Thanks to:
- Mark Mansur's [TunerPro](https://tunerpro.net/) for creating the XDF/ADX format
- [M44 Wiki](https://m44.fandom.com/wiki/M44_Wiki) for example XDF/ADX/BIN files
- [OpenEEC](https://github.com/OpenEEC-Project) for reverse-engineering Ford EEC

## Requirements
Built for Python 3.10 and later.

## Supported Features
- XDF parameter editing

## Getting started

    pipenv install
    pipenv shell
    python3 <todo.py> <somearg1> <somearg2>
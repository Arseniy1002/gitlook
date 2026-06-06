# gitlook
i have mass projects in ~/code and i kept mass forgetting to push stuff before shutting down my laptop. then next day at work "where tf is my code" so i wrote this

it scans a folder, finds all git repos inside and shows you a table: whats dirty, whats not pushed, whats behind remote, stashes, etc

## usage

python gitlook.py ~/projects

## example


![img](https://i.postimg.cc/k5pLZ8Jt/61489413-039F-4A33-8063-7626B716E009.png)


## install

git clone https://github.com/Arseniy1002/gitlook cd gitlook python gitlook.py ~/your/projects/folder

if you want to call it from anywhere:
ln -s $(pwd)/gitlook.py ~/.local/bin/gitlook

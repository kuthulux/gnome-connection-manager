# Gnome Connection Manager or GCM
 
Gnome Connection Manager or GCM is a tabbed ssh connection manager for gtk+ environments.
Starting with version 1.2.0 it **only** supports python3 and GTK 3 so it should run fine on any modern desktop environment.

If you can't update to python/gtk 3 and only have python2/gtk2, then keep using GCM version v1.1.0 from [kuthulu.com](http://kuthulu.com/gcm/download.html)

## Installation

### From binary package
The easiest way to install GCM is to download the deb or rpm package from [releases](https://github.com/kuthulux/gnome-connection-manager/releases) or from [kuthulu.com](http://kuthulu.com/gcm/download.html) and install it using the package manager

#### Debian/Ubuntu
`sudo dpkg -i gnome-connection-manager_1.2.0_all.deb`

#### Fedora/Redhat
`sudo yum install gnome-connection-manager-1.2.0.noarch.rpm`

#### Windows
Install Latest Visual C++ Redistributor

python -m pip install --upgrade pip

python -m pip install pycairo pygobject PyGtk 

### From Sources
Download or clone the repository and execute the file `gnome_connection_manager.py`


``` 
git clone git://github.com/kuthulux/gnome-connection-manager
cd gnome-connection-manager
./gnome_connection_manager.py
```

#### Dependencies:
* expect
* python3
* python3-gi and gir1.2-vte-2.91 (debian) / python3-gobject (fedora)

---

## Language
GCM should use the default OS language, but if for any reason you want to use another language, then start GCM this way:
 
```bash
LANG=en_US.UTF.8 ./gnome_connection_manager.py
```
replace en_US.UTF-8 with the language of your choice.

---

## Packaging

To create a deb or rpm package from source you have to follow these steps:

1. install basic tools

Debian/Ubuntu
```
sudo apt install git ruby ruby-dev build-essential gettext
sudo gem install fpm
```
Fedora/Redhat
```bash
sudo yum install git ruby ruby-devel make gcc gcc-c++ redhat-rpm-config getext rpm-build 
sudo gem install fpm
```

2. download or clone the respository

```bash 
git clone git://github.com/kuthulux/gnome-connection-manager
cd gnome-connection-manager
```

3. make the desired package:
```bash 
#make deb and rpm
make

#make deb package only
make deb

#make rpm package only
make rpm
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.


## License
[GPLv3](https://www.gnu.org/licenses/gpl-3.0.html)

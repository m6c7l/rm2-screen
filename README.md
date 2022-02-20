# reMarkable Screen Share

![](canvas.png)

This is a web-based and very minimalistic screen share tool for the reMarkable device for creating interactive presentations, slides, simple sketches, flip books, and whatever else comes to your mind. This tool provides at least some of the functionality as introduced with the native *Screen Share* [1] from reMarkable, but does not need a subscription nor an online account to work. The repository *Awesome reMarkable* [2] lists many options and approaches to avoid the need for a paid subscription when it comes to screen share, e.g. *reStream* [3]. However, *Pipes and Papers* [4] seemed to be the most promising one, thus this work is heavily inspired by that one.

> * tested with reMarkable 2, Version 2.12.1.527
> * no subscription nor account for Connect needed
> * after installation the feature-rich screen share frontend is accessible in a web browser

## Features

* dark and bright page theme (toggle with **TAB**)
* landscape and portrait view (toggle with **ENTER**)
* different pen colors (set with letter keys: **W**hite, **R**ed, **G**reen, blac**K**, **Y**ellow, **C**yan, **B**lue, **M**agenta)
* clear current page (with **SPACE**)
* navigate between pages (**PAGE_UP** goes back to previous page, and **PAGE_DOWN** jumps to next page or creates a new one)
* undo and redo on current page (press **LEFT_ARROW** to undo, and **RIGHT_ARROW** to redo)

## Installation

### Preparation

1. Clone this repository or get the screen share service files from this repository (`canvas.py`, `canvas.service`, `canvas.html`) and download the archive (`python-3.9.9-armhf.tar.xz`) from releases.
2. Note the IP address and password for your reMarkable device as shown under Menu - Settings - Help - Copyright and licenses.
3. Open a terminal for execution of the subsequent commands.

> Make sure that your device does not go to sleep while doing the rest of the installation.

### Python
 
1. Copy the archive to your device:
   `scp -oHostKeyAlgorithms=+ssh-rsa python-3.9.9-armhf.tar.xz root@remarkable:/home/root`
2. Extract the archive on the device:
   `ssh -oHostKeyAlgorithms=+ssh-rsa root@remarkable "tar xvf ~/python-3.9.9-armhf.tar.xz"`
3. Create a link on your device to the Python runtime environment and delete the archive:
   `ssh -oHostKeyAlgorithms=+ssh-rsa root@remarkable "ln -s python-3.9.9 python3 && rm ~/python-3.9.9-armhf.tar.xz"`

> The Python runtime environment has been compiled on a RPi 4 and includes a little more modules than needed for this particular service - perhaps a good starting point for further development of server-side features - check it out.

### Service

7. Create a directory to host the screen share files on your device:
   `ssh -oHostKeyAlgorithms=+ssh-rsa root@remarkable "mkdir ~/canvas"`
8. Copy the screen share files to your device:
   `scp -oHostKeyAlgorithms=+ssh-rsa canvas.* root@remarkable:/home/root/canvas`
9. Add the screen share service to systemd to make it available after reboot:
   `ssh -oHostKeyAlgorithms=+ssh-rsa root@remarkable "cp ~/canvas/canvas.service /etc/systemd/system && systemctl enable canvas && systemctl start canvas"`

> The service file cannot be linked (and thus needs to be copied) as the root and home partitions are separate.

## Usage

Make sure your reMarkable is not sleeping. Open a web browser on your computer and request the service on `{IP address}:12345`. If your computer is in your local home network and your router hosts a DHCP server, you should be even able to access the service on `remarkable:12345`. If the service is up and running on your reMarkable is accessible from your computer, you will see a canvas in your browser which reflects the pen of your reMarkable.

## References

* [[1](https://support.remarkable.com/hc/en-us/articles/4403721327377)] Original reMarkable Screen Share - A subscription feature of Connect.
* [[2](https://github.com/reHackable/awesome-reMarkable)] Awesome reMarkable - A curated list of projects related to the reMarkable tablet.
* [[3](https://github.com/rien/reStream)] reStream - Stream your reMarkable screen over SSH. 
* [[4](https://gitlab.com/afandian/pipes-and-paper)] Pipes and Papers - Experiment to reproduce the ReMarkable tablet screen on the desktop for white-boarding.

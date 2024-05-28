# py_mouse_ball
## 1.Install dependencies
~~~
conda create -n mouseball python=3.9
conda activate mouseball
pip install pyqt5 pyusb numpy matplotlib
~~~

## 2.Install mouse driver
Download [Zadig](https://zadig.akeo.ie/), which is a Windows application that installs generic USB drivers. Then install libusb driver for the mouse following the steps below.
~~~
1. Options > List all devices
2. Choose the mouse used for ball tracking
3. Choose libusb-win32 driver
4. Install driver
~~~
<div align="center">
<img src="image1.png" width="600">
</div>

If the driver is successfully installed, you'll be able to find in Device Manager that the mouse has now become a libusb-win32 device (and it's unable to control the cursor on your screen now).
<div align="center">
<img src="image2.png" width="600">
</div>

## 3.Use
...

## 4.Test 
~~~
python test.py
~~~

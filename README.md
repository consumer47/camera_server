to install the service, symlink or copy it:
ln -s /home/pi/kamen-street-pi/camera/raspi-cam-picam-only.service /etc/systemd/system/raspi-cam.service
cp /home/pi/kamen-street-pi/camera/raspi-cam-picam-only.service /etc/systemd/system/raspi-cam.service

created venv with system-site-packages
python -m venv --system-site-packages my-venv

i needed to install on a pi:
sudo apt-get install libpcap-dev
